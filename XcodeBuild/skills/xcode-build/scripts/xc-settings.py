#!/usr/bin/env python3
"""
Show build settings for an Xcode scheme.

Usage:
    xc-settings.py --project <path> --scheme <name> [--filter <pattern>]
    xc-settings.py --workspace <path> --scheme <name> [--filter <pattern>]

Options:
    --project <path>     Path to .xcodeproj
    --workspace <path>   Path to .xcworkspace
    --scheme <name>      Scheme name
    --filter <pattern>   Filter settings by pattern (case-insensitive)
    --json               Output raw settings as JSON (default: formatted)

Output:
    JSON object with build settings
"""

import json
import sys
import argparse
import os
import re

from xc_utils import run_xcodebuild, parse_build_settings, success_response, error_response


def main():
    parser = argparse.ArgumentParser(description='Show Xcode build settings')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--project', help='Path to .xcodeproj')
    group.add_argument('--workspace', help='Path to .xcworkspace')
    parser.add_argument('--scheme', required=True, help='Scheme name')
    parser.add_argument('--filter', help='Filter settings by pattern')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    args = parser.parse_args()

    # Build xcodebuild command
    cmd_args = ['-showBuildSettings']

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

    success, stdout, stderr = run_xcodebuild(*cmd_args)

    if not success:
        print(json.dumps(error_response(
            f'Failed to get build settings: {stderr.strip()}',
            hint='Check that the scheme name is correct. Use xc-schemes.py to list available schemes.'
        )))
        sys.exit(1)

    settings = parse_build_settings(stdout)

    if not settings:
        print(json.dumps(error_response('No build settings found')))
        sys.exit(1)

    # Filter if requested
    if args.filter:
        pattern = re.compile(args.filter, re.IGNORECASE)
        settings = {k: v for k, v in settings.items() if pattern.search(k)}

    # Extract key settings for summary
    key_settings = {
        'PRODUCT_NAME': settings.get('PRODUCT_NAME'),
        'PRODUCT_BUNDLE_IDENTIFIER': settings.get('PRODUCT_BUNDLE_IDENTIFIER'),
        'INFOPLIST_FILE': settings.get('INFOPLIST_FILE'),
        'SWIFT_VERSION': settings.get('SWIFT_VERSION'),
        'IPHONEOS_DEPLOYMENT_TARGET': settings.get('IPHONEOS_DEPLOYMENT_TARGET'),
        'MACOSX_DEPLOYMENT_TARGET': settings.get('MACOSX_DEPLOYMENT_TARGET'),
        'SDKROOT': settings.get('SDKROOT'),
        'BUILD_DIR': settings.get('BUILD_DIR'),
        'DERIVED_DATA_DIR': settings.get('DERIVED_DATA_DIR'),
        'CODE_SIGN_IDENTITY': settings.get('CODE_SIGN_IDENTITY'),
        'DEVELOPMENT_TEAM': settings.get('DEVELOPMENT_TEAM'),
    }

    # Remove None values
    key_settings = {k: v for k, v in key_settings.items() if v is not None}

    response = success_response(
        f'Retrieved {len(settings)} build settings',
        scheme=args.scheme,
        key_settings=key_settings,
        all_settings=settings if args.json or args.filter else None,
        settings_count=len(settings)
    )

    # Remove None values from response
    response = {k: v for k, v in response.items() if v is not None}

    print(json.dumps(response, indent=2))


if __name__ == '__main__':
    main()
