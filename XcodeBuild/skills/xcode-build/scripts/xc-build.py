#!/usr/bin/env python3
"""
Build an Xcode project or workspace for a specific destination.

Usage:
    xc-build.py --project <path> --scheme <name> [options]
    xc-build.py --workspace <path> --scheme <name> [options]

Options:
    --project <path>         Path to .xcodeproj
    --workspace <path>       Path to .xcworkspace
    --scheme <name>          Scheme name to build
    --destination <dest>     Build destination (see examples below)
    --configuration <cfg>    Build configuration (Debug/Release, default: Debug)
    --derived-data <path>    Custom DerivedData path
    --clean                  Clean before building
    --quiet                  Less verbose output
    --extra-args <args>      Additional xcodebuild arguments

Destination Examples:
    Simulator: 'platform=iOS Simulator,name=iPhone 15'
    Simulator by ID: 'id=XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX'
    Device: 'platform=iOS,id=DEVICE-UDID'
    macOS: 'platform=macOS'
    Any iOS Simulator: 'generic/platform=iOS Simulator'
    Any iOS Device: 'generic/platform=iOS'

Output:
    JSON object with build results, errors, and warnings
"""

import json
import sys
import argparse
import os

from xc_utils import (
    run_xcodebuild, parse_build_output, success_response, error_response
)


def main():
    parser = argparse.ArgumentParser(description='Build Xcode project')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--project', help='Path to .xcodeproj')
    group.add_argument('--workspace', help='Path to .xcworkspace')
    parser.add_argument('--scheme', required=True, help='Scheme name')
    parser.add_argument('--destination', help='Build destination')
    parser.add_argument('--configuration', default='Debug', help='Build configuration')
    parser.add_argument('--derived-data', help='Custom DerivedData path')
    parser.add_argument('--clean', action='store_true', help='Clean before building')
    parser.add_argument('--quiet', action='store_true', help='Less verbose output')
    parser.add_argument('--extra-args', nargs='*', help='Additional xcodebuild arguments')
    args = parser.parse_args()

    # Build xcodebuild command
    cmd_args = []

    if args.project:
        path = os.path.abspath(args.project)
        if not os.path.exists(path):
            print(json.dumps(error_response(f'Project not found: {path}')))
            sys.exit(1)
        cmd_args.extend(['-project', path])
    else:
        path = os.path.abspath(args.workspace)
        if not os.path.exists(path):
            print(json.dumps(error_response(f'Workspace not found: {path}')))
            sys.exit(1)
        cmd_args.extend(['-workspace', path])

    cmd_args.extend(['-scheme', args.scheme])
    cmd_args.extend(['-configuration', args.configuration])

    if args.destination:
        cmd_args.extend(['-destination', args.destination])

    if args.derived_data:
        cmd_args.extend(['-derivedDataPath', os.path.abspath(args.derived_data)])

    # Add recommended flags to avoid common issues
    cmd_args.extend(['-skipMacroValidation', '-skipPackagePluginValidation'])

    if args.quiet:
        cmd_args.append('-quiet')

    if args.extra_args:
        cmd_args.extend(args.extra_args)

    # Determine action
    if args.clean:
        cmd_args.extend(['clean', 'build'])
    else:
        cmd_args.append('build')

    # Run build
    success, stdout, stderr = run_xcodebuild(*cmd_args)

    # Parse output
    parsed = parse_build_output(stdout, stderr)

    if success and parsed['build_succeeded']:
        response = success_response(
            'Build succeeded',
            scheme=args.scheme,
            configuration=args.configuration,
            destination=args.destination,
            warnings=parsed['warnings'] if parsed['warnings'] else None,
            warning_count=parsed['warning_count']
        )

        # Remove None values
        response = {k: v for k, v in response.items() if v is not None}

        print(json.dumps(response, indent=2))
    else:
        response = error_response(
            'Build failed',
            scheme=args.scheme,
            configuration=args.configuration,
            destination=args.destination,
            errors=parsed['errors'],
            warnings=parsed['warnings'] if parsed['warnings'] else None,
            error_count=parsed['error_count'],
            warning_count=parsed['warning_count']
        )

        # Add raw output if no structured errors found
        if not parsed['errors']:
            # Get last 50 lines of output for context
            combined = stdout + '\n' + stderr
            lines = combined.strip().split('\n')
            response['output_tail'] = '\n'.join(lines[-50:])

        # Remove None values
        response = {k: v for k, v in response.items() if v is not None}

        print(json.dumps(response, indent=2))
        sys.exit(1)


if __name__ == '__main__':
    main()
