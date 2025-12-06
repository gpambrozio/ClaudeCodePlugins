#!/usr/bin/env python3
"""
List available schemes in an Xcode project or workspace.

Usage:
    xc-schemes.py --project <path>
    xc-schemes.py --workspace <path>

Options:
    --project <path>     Path to .xcodeproj
    --workspace <path>   Path to .xcworkspace

Output:
    JSON object with list of available schemes
"""

import json
import sys
import argparse
import os

from xc_utils import run_xcodebuild, parse_schemes_output, success_response, error_response


def main():
    parser = argparse.ArgumentParser(description='List Xcode schemes')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--project', help='Path to .xcodeproj')
    group.add_argument('--workspace', help='Path to .xcworkspace')
    args = parser.parse_args()

    # Build xcodebuild command
    cmd_args = ['-list']

    if args.project:
        path = os.path.abspath(args.project)
        if not os.path.exists(path):
            print(json.dumps(error_response(f'Project not found: {path}')))
            sys.exit(1)
        cmd_args.extend(['-project', path])
        target_type = 'project'
        target_path = path
    else:
        path = os.path.abspath(args.workspace)
        if not os.path.exists(path):
            print(json.dumps(error_response(f'Workspace not found: {path}')))
            sys.exit(1)
        cmd_args.extend(['-workspace', path])
        target_type = 'workspace'
        target_path = path

    success, stdout, stderr = run_xcodebuild(*cmd_args)

    if not success:
        print(json.dumps(error_response(
            f'Failed to list schemes: {stderr.strip()}',
            command=f'xcodebuild {" ".join(cmd_args)}'
        )))
        sys.exit(1)

    schemes = parse_schemes_output(stdout)

    if not schemes:
        print(json.dumps(success_response(
            'No schemes found',
            target_type=target_type,
            path=target_path,
            schemes=[],
            raw_output=stdout
        )))
        return

    response = success_response(
        f'Found {len(schemes)} scheme(s)',
        target_type=target_type,
        path=target_path,
        schemes=schemes
    )

    print(json.dumps(response, indent=2))


if __name__ == '__main__':
    main()
