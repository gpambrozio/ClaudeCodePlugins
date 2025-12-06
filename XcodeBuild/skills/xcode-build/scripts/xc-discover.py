#!/usr/bin/env python3
"""
Discover Xcode projects and workspaces in a directory.

Usage:
    xc-discover.py [--path <path>] [--max-depth <n>]

Options:
    --path <path>      Directory to search (default: current directory)
    --max-depth <n>    Maximum search depth (default: 5)

Output:
    JSON object with lists of discovered projects and workspaces
"""

import json
import sys
import argparse
import os

from xc_utils import find_projects, success_response, error_response


def main():
    parser = argparse.ArgumentParser(description='Discover Xcode projects and workspaces')
    parser.add_argument('--path', default='.', help='Directory to search (default: current)')
    parser.add_argument('--max-depth', type=int, default=5, help='Maximum search depth (default: 5)')
    args = parser.parse_args()

    search_path = os.path.abspath(args.path)

    if not os.path.isdir(search_path):
        print(json.dumps(error_response(f'Directory not found: {search_path}')))
        sys.exit(1)

    result = find_projects(search_path, args.max_depth)

    total = len(result['projects']) + len(result['workspaces'])

    if total == 0:
        print(json.dumps(success_response(
            'No Xcode projects or workspaces found',
            search_path=search_path,
            projects=[],
            workspaces=[]
        )))
        return

    response = success_response(
        f'Found {len(result["workspaces"])} workspace(s) and {len(result["projects"])} project(s)',
        search_path=search_path,
        workspaces=result['workspaces'],
        projects=result['projects'],
        total_count=total
    )

    # Add recommendation
    if result['workspaces']:
        response['recommendation'] = 'Use a workspace (-workspace) when available, as it includes all dependencies'

    print(json.dumps(response, indent=2))


if __name__ == '__main__':
    main()
