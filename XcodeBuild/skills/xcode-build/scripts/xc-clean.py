#!/usr/bin/env python3
"""
Clean Xcode build products and DerivedData.

Usage:
    xc-clean.py --project <path> --scheme <name>
    xc-clean.py --workspace <path> --scheme <name>
    xc-clean.py --derived-data [--all]

Options:
    --project <path>         Path to .xcodeproj
    --workspace <path>       Path to .xcworkspace
    --scheme <name>          Scheme name to clean
    --derived-data           Clean DerivedData folder
    --all                    Clean all DerivedData (use with --derived-data)
    --path <path>            Specific DerivedData path to clean

Output:
    JSON object with clean operation results
"""

import json
import sys
import argparse
import os
import shutil

from xc_utils import run_xcodebuild, get_derived_data_path, success_response, error_response


def clean_derived_data(path: str = None, all_data: bool = False) -> dict:
    """Clean DerivedData folder."""
    derived_data_path = path or get_derived_data_path()

    if not os.path.exists(derived_data_path):
        return success_response(
            'DerivedData folder does not exist',
            path=derived_data_path
        )

    if all_data:
        # Remove everything in DerivedData
        try:
            # Get size before cleaning
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(derived_data_path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    try:
                        total_size += os.path.getsize(fp)
                    except (OSError, IOError):
                        pass

            # Remove contents
            for item in os.listdir(derived_data_path):
                item_path = os.path.join(derived_data_path, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)

            size_mb = total_size / (1024 * 1024)
            return success_response(
                f'Cleaned all DerivedData ({size_mb:.1f} MB freed)',
                path=derived_data_path,
                bytes_freed=total_size
            )
        except Exception as e:
            return error_response(f'Failed to clean DerivedData: {e}')
    else:
        # Just report what's there
        items = []
        total_size = 0
        try:
            for item in os.listdir(derived_data_path):
                item_path = os.path.join(derived_data_path, item)
                if os.path.isdir(item_path):
                    # Get folder size
                    size = 0
                    for dirpath, dirnames, filenames in os.walk(item_path):
                        for f in filenames:
                            fp = os.path.join(dirpath, f)
                            try:
                                size += os.path.getsize(fp)
                            except (OSError, IOError):
                                pass
                    total_size += size
                    items.append({
                        'name': item,
                        'size_bytes': size,
                        'size_mb': round(size / (1024 * 1024), 1)
                    })
        except Exception as e:
            return error_response(f'Failed to scan DerivedData: {e}')

        return success_response(
            f'DerivedData contains {len(items)} items ({total_size / (1024 * 1024):.1f} MB)',
            path=derived_data_path,
            items=items,
            total_size_bytes=total_size,
            hint='Use --all to clean all DerivedData'
        )


def main():
    parser = argparse.ArgumentParser(description='Clean Xcode build products')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--project', help='Path to .xcodeproj')
    group.add_argument('--workspace', help='Path to .xcworkspace')
    group.add_argument('--derived-data', action='store_true', help='Clean DerivedData folder')
    parser.add_argument('--scheme', help='Scheme name to clean')
    parser.add_argument('--all', action='store_true', help='Clean all DerivedData')
    parser.add_argument('--path', help='Specific DerivedData path')
    args = parser.parse_args()

    # Handle DerivedData cleaning
    if args.derived_data:
        result = clean_derived_data(args.path, args.all)
        print(json.dumps(result, indent=2))
        if not result.get('success'):
            sys.exit(1)
        return

    # Handle project/workspace cleaning
    if not args.project and not args.workspace:
        print(json.dumps(error_response(
            'Either --project, --workspace, or --derived-data is required'
        )))
        sys.exit(1)

    if not args.scheme:
        print(json.dumps(error_response('--scheme is required for project/workspace cleaning')))
        sys.exit(1)

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
    cmd_args.append('clean')

    # Run clean
    success, stdout, stderr = run_xcodebuild(*cmd_args)

    if success:
        print(json.dumps(success_response(
            'Clean succeeded',
            scheme=args.scheme
        ), indent=2))
    else:
        print(json.dumps(error_response(
            f'Clean failed: {stderr.strip()}',
            scheme=args.scheme
        ), indent=2))
        sys.exit(1)


if __name__ == '__main__':
    main()
