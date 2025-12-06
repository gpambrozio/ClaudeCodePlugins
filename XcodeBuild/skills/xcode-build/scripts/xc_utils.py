#!/usr/bin/env python3
"""
Shared utilities for Xcode build scripts.

This module contains common functions used across multiple xc-*.py scripts
to reduce code duplication and ensure consistent behavior.
"""

import subprocess
import json
import os
import re
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any


def run_command(cmd: List[str], cwd: Optional[str] = None,
                timeout: Optional[int] = None) -> Tuple[bool, str, str]:
    """
    Run a command and return result.

    Args:
        cmd: Command and arguments as a list
        cwd: Working directory for the command
        timeout: Timeout in seconds

    Returns:
        Tuple of (success: bool, stdout: str, stderr: str)
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, '', f'Command timed out after {timeout} seconds'
    except FileNotFoundError:
        return False, '', f'Command not found: {cmd[0]}'
    except Exception as e:
        return False, '', str(e)


def run_xcodebuild(*args, cwd: Optional[str] = None,
                   timeout: Optional[int] = 600) -> Tuple[bool, str, str]:
    """
    Run xcodebuild command and return result.

    Args:
        *args: Arguments to pass to xcodebuild
        cwd: Working directory
        timeout: Timeout in seconds (default 10 minutes)

    Returns:
        Tuple of (success: bool, stdout: str, stderr: str)
    """
    cmd = ['xcodebuild'] + list(args)
    return run_command(cmd, cwd=cwd, timeout=timeout)


def run_xcrun(*args, cwd: Optional[str] = None) -> Tuple[bool, str, str]:
    """
    Run xcrun command and return result.

    Args:
        *args: Arguments to pass to xcrun
        cwd: Working directory

    Returns:
        Tuple of (success: bool, stdout: str, stderr: str)
    """
    cmd = ['xcrun'] + list(args)
    return run_command(cmd, cwd=cwd)


def get_xcode_path() -> Optional[str]:
    """Get the path to the active Xcode installation."""
    success, stdout, _ = run_command(['xcode-select', '-p'])
    if success:
        return stdout.strip()
    return None


def get_xcode_version() -> Optional[Dict[str, str]]:
    """Get Xcode version information."""
    success, stdout, _ = run_command(['xcodebuild', '-version'])
    if not success:
        return None

    lines = stdout.strip().split('\n')
    version_info = {}

    for line in lines:
        if line.startswith('Xcode'):
            version_info['xcode'] = line.replace('Xcode ', '').strip()
        elif line.startswith('Build version'):
            version_info['build'] = line.replace('Build version ', '').strip()

    return version_info if version_info else None


def get_macos_version() -> Dict[str, str]:
    """Get macOS version information."""
    success, stdout, _ = run_command(['sw_vers'])
    if not success:
        return {}

    version_info = {}
    for line in stdout.strip().split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            version_info[key.strip().lower().replace(' ', '_')] = value.strip()

    return version_info


def find_projects(root_path: str, max_depth: int = 5) -> Dict[str, List[str]]:
    """
    Find Xcode projects and workspaces in a directory.

    Args:
        root_path: Root directory to search
        max_depth: Maximum directory depth to search

    Returns:
        Dict with 'projects' and 'workspaces' lists
    """
    projects = []
    workspaces = []

    root = Path(root_path).resolve()

    # Directories to skip
    skip_dirs = {
        'build', 'DerivedData', 'Pods', '.git', 'node_modules',
        'Carthage', '.build', '.swiftpm', 'xcuserdata'
    }

    def search(path: Path, depth: int):
        if depth > max_depth:
            return

        try:
            for entry in path.iterdir():
                if entry.is_symlink():
                    continue

                if entry.is_dir():
                    name = entry.name

                    if name in skip_dirs:
                        continue

                    if name.endswith('.xcodeproj'):
                        projects.append(str(entry))
                    elif name.endswith('.xcworkspace'):
                        # Skip workspace inside xcodeproj
                        if not str(entry.parent).endswith('.xcodeproj'):
                            workspaces.append(str(entry))
                    else:
                        search(entry, depth + 1)
        except PermissionError:
            pass

    search(root, 0)

    return {
        'projects': sorted(projects),
        'workspaces': sorted(workspaces)
    }


def parse_schemes_output(stdout: str) -> List[str]:
    """
    Parse xcodebuild -list output to extract schemes.

    Args:
        stdout: Output from xcodebuild -list

    Returns:
        List of scheme names
    """
    schemes = []
    in_schemes_section = False

    for line in stdout.split('\n'):
        line = line.strip()

        if line == 'Schemes:':
            in_schemes_section = True
            continue

        if in_schemes_section:
            if not line or line.endswith(':'):
                break
            schemes.append(line)

    return schemes


def parse_build_settings(stdout: str) -> Dict[str, str]:
    """
    Parse xcodebuild -showBuildSettings output.

    Args:
        stdout: Output from xcodebuild -showBuildSettings

    Returns:
        Dict of build settings
    """
    settings = {}

    for line in stdout.split('\n'):
        line = line.strip()
        if ' = ' in line:
            key, value = line.split(' = ', 1)
            settings[key.strip()] = value.strip()

    return settings


def parse_build_output(stdout: str, stderr: str) -> Dict[str, Any]:
    """
    Parse xcodebuild output to extract errors, warnings, and results.

    Args:
        stdout: Standard output from xcodebuild
        stderr: Standard error from xcodebuild

    Returns:
        Dict with parsed build information
    """
    combined = stdout + '\n' + stderr

    errors = []
    warnings = []

    # Error patterns
    error_pattern = re.compile(r'^(.+?):(\d+):(\d+): error: (.+)$', re.MULTILINE)
    warning_pattern = re.compile(r'^(.+?):(\d+):(\d+): warning: (.+)$', re.MULTILINE)

    for match in error_pattern.finditer(combined):
        errors.append({
            'file': match.group(1),
            'line': int(match.group(2)),
            'column': int(match.group(3)),
            'message': match.group(4)
        })

    for match in warning_pattern.finditer(combined):
        warnings.append({
            'file': match.group(1),
            'line': int(match.group(2)),
            'column': int(match.group(3)),
            'message': match.group(4)
        })

    # Check for build succeeded/failed
    build_succeeded = '** BUILD SUCCEEDED **' in combined
    build_failed = '** BUILD FAILED **' in combined
    test_succeeded = '** TEST SUCCEEDED **' in combined
    test_failed = '** TEST FAILED **' in combined

    return {
        'errors': errors,
        'warnings': warnings,
        'error_count': len(errors),
        'warning_count': len(warnings),
        'build_succeeded': build_succeeded,
        'build_failed': build_failed,
        'test_succeeded': test_succeeded,
        'test_failed': test_failed
    }


def get_derived_data_path() -> str:
    """Get the default DerivedData path."""
    return os.path.expanduser('~/Library/Developer/Xcode/DerivedData')


def get_available_platforms() -> List[str]:
    """Get list of available SDK platforms."""
    success, stdout, _ = run_xcodebuild('-showsdks')
    if not success:
        return []

    platforms = set()
    for line in stdout.split('\n'):
        # Look for SDK names like "iOS 17.0", "macOS 14.0", etc.
        for platform in ['iOS', 'macOS', 'watchOS', 'tvOS', 'visionOS']:
            if platform.lower() in line.lower():
                platforms.add(platform)

    return sorted(platforms)


# Common error messages and hints
BUILD_ERROR_HINTS = {
    'Signing for': 'Configure code signing in Xcode or add CODE_SIGN_IDENTITY="" CODE_SIGNING_REQUIRED=NO',
    'No account for team': 'Sign in to your Apple Developer account in Xcode',
    'No profiles for': 'Create a provisioning profile in Apple Developer portal',
    'module not found': 'Run pod install or swift package resolve',
    'No such module': 'Missing dependency - check Package.swift or Podfile',
    'Command PhaseScriptExecution failed': 'A build phase script failed - check the build logs',
    'Unable to find a destination': 'Specify a valid destination with -destination',
}


def get_error_hint(error_message: str) -> Optional[str]:
    """Get a helpful hint for a known error message."""
    for pattern, hint in BUILD_ERROR_HINTS.items():
        if pattern.lower() in error_message.lower():
            return hint
    return None


def json_output(data: Dict[str, Any], indent: int = 2) -> str:
    """Format data as JSON string."""
    return json.dumps(data, indent=indent)


def success_response(message: str, **kwargs) -> Dict[str, Any]:
    """Create a standard success response."""
    return {'success': True, 'message': message, **kwargs}


def error_response(error: str, **kwargs) -> Dict[str, Any]:
    """Create a standard error response."""
    hint = get_error_hint(error)
    response = {'success': False, 'error': error, **kwargs}
    if hint:
        response['hint'] = hint
    return response
