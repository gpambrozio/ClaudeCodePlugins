#!/usr/bin/env python3
"""
Run tests for an Xcode project or workspace.

Usage:
    xc-test.py --project <path> --scheme <name> [options]
    xc-test.py --workspace <path> --scheme <name> [options]

Options:
    --project <path>         Path to .xcodeproj
    --workspace <path>       Path to .xcworkspace
    --scheme <name>          Scheme name with tests
    --destination <dest>     Test destination
    --configuration <cfg>    Build configuration (Debug/Release, default: Debug)
    --only-testing <spec>    Run only specific tests (e.g., 'MyTests/TestClass/testMethod')
    --skip-testing <spec>    Skip specific tests
    --parallel               Run tests in parallel
    --retry-count <n>        Number of test retries on failure
    --result-bundle <path>   Path to save result bundle
    --quiet                  Less verbose output

Output:
    JSON object with test results, pass/fail counts, errors
"""

import json
import sys
import argparse
import os
import re

from xc_utils import run_xcodebuild, parse_build_output, success_response, error_response


def parse_test_output(stdout: str, stderr: str) -> dict:
    """Parse xcodebuild test output to extract test results."""
    combined = stdout + '\n' + stderr

    # Parse test results
    test_results = {
        'passed': [],
        'failed': [],
        'skipped': [],
    }

    # Test case patterns
    # Test Case '-[MyTests testExample]' passed (0.001 seconds).
    # Test Case '-[MyTests testExample]' failed (0.001 seconds).
    passed_pattern = re.compile(r"Test Case '([^']+)' passed")
    failed_pattern = re.compile(r"Test Case '([^']+)' failed")
    skipped_pattern = re.compile(r"Test Case '([^']+)' skipped")

    for match in passed_pattern.finditer(combined):
        test_results['passed'].append(match.group(1))

    for match in failed_pattern.finditer(combined):
        test_results['failed'].append(match.group(1))

    for match in skipped_pattern.finditer(combined):
        test_results['skipped'].append(match.group(1))

    # Extract failure details
    failure_details = []
    failure_pattern = re.compile(
        r'(.+?):(\d+): error: ([^\n]+)',
        re.MULTILINE
    )
    for match in failure_pattern.finditer(combined):
        failure_details.append({
            'file': match.group(1),
            'line': int(match.group(2)),
            'message': match.group(3)
        })

    # Check for test summary
    test_succeeded = '** TEST SUCCEEDED **' in combined
    test_failed = '** TEST FAILED **' in combined

    # Extract execution time if available
    time_match = re.search(r'Test session results: (.+?) passed in (\d+\.\d+)', combined)
    execution_time = float(time_match.group(2)) if time_match else None

    return {
        'test_succeeded': test_succeeded,
        'test_failed': test_failed,
        'passed': test_results['passed'],
        'failed': test_results['failed'],
        'skipped': test_results['skipped'],
        'passed_count': len(test_results['passed']),
        'failed_count': len(test_results['failed']),
        'skipped_count': len(test_results['skipped']),
        'failure_details': failure_details,
        'execution_time': execution_time
    }


def main():
    parser = argparse.ArgumentParser(description='Run Xcode tests')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--project', help='Path to .xcodeproj')
    group.add_argument('--workspace', help='Path to .xcworkspace')
    parser.add_argument('--scheme', required=True, help='Scheme name')
    parser.add_argument('--destination', help='Test destination')
    parser.add_argument('--configuration', default='Debug', help='Build configuration')
    parser.add_argument('--only-testing', action='append', help='Run only specific tests')
    parser.add_argument('--skip-testing', action='append', help='Skip specific tests')
    parser.add_argument('--parallel', action='store_true', help='Run tests in parallel')
    parser.add_argument('--retry-count', type=int, help='Number of test retries')
    parser.add_argument('--result-bundle', help='Path to save result bundle')
    parser.add_argument('--quiet', action='store_true', help='Less verbose output')
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

    # Add recommended flags
    cmd_args.extend(['-skipMacroValidation', '-skipPackagePluginValidation'])

    if args.only_testing:
        for test in args.only_testing:
            cmd_args.extend(['-only-testing', test])

    if args.skip_testing:
        for test in args.skip_testing:
            cmd_args.extend(['-skip-testing', test])

    if args.parallel:
        cmd_args.append('-parallel-testing-enabled')
        cmd_args.append('YES')

    if args.retry_count:
        cmd_args.extend(['-retry-tests-on-failure', '-test-iterations', str(args.retry_count)])

    if args.result_bundle:
        cmd_args.extend(['-resultBundlePath', os.path.abspath(args.result_bundle)])

    if args.quiet:
        cmd_args.append('-quiet')

    cmd_args.append('test')

    # Run tests
    success, stdout, stderr = run_xcodebuild(*cmd_args, timeout=1800)  # 30 min timeout

    # Parse results
    test_results = parse_test_output(stdout, stderr)
    build_results = parse_build_output(stdout, stderr)

    if test_results['test_succeeded']:
        response = success_response(
            f"Tests passed: {test_results['passed_count']} passed, {test_results['failed_count']} failed, {test_results['skipped_count']} skipped",
            scheme=args.scheme,
            passed_count=test_results['passed_count'],
            failed_count=test_results['failed_count'],
            skipped_count=test_results['skipped_count'],
            execution_time=test_results['execution_time'],
            passed=test_results['passed'] if len(test_results['passed']) <= 20 else None,
            skipped=test_results['skipped'] if test_results['skipped'] else None,
        )

        # Remove None values
        response = {k: v for k, v in response.items() if v is not None}

        print(json.dumps(response, indent=2))
    else:
        response = error_response(
            f"Tests failed: {test_results['passed_count']} passed, {test_results['failed_count']} failed",
            scheme=args.scheme,
            passed_count=test_results['passed_count'],
            failed_count=test_results['failed_count'],
            skipped_count=test_results['skipped_count'],
            failed=test_results['failed'],
            failure_details=test_results['failure_details'] if test_results['failure_details'] else None,
            build_errors=build_results['errors'] if build_results['errors'] else None
        )

        # Remove None values
        response = {k: v for k, v in response.items() if v is not None}

        # Add output tail if no structured results
        if not test_results['failed'] and not test_results['failure_details']:
            combined = stdout + '\n' + stderr
            lines = combined.strip().split('\n')
            response['output_tail'] = '\n'.join(lines[-50:])

        print(json.dumps(response, indent=2))
        sys.exit(1)


if __name__ == '__main__':
    main()
