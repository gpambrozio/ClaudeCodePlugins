#!/usr/bin/env python3
"""Detect whether Xcode's native MCP server is available."""

import subprocess


def detect_xcode_mcp() -> dict:
    """Check if Xcode MCP bridge is installed and likely active.

    Returns dict with:
        xcode_mcp_installed: xcrun --find mcpbridge succeeds
        xcode_running: Xcode process is running
        mcpbridge_running: mcpbridge process is running
        xcode_mcp_likely: installed AND (xcode OR bridge running)
    """
    result = {
        "xcode_mcp_installed": False,
        "xcode_running": False,
        "mcpbridge_running": False,
        "xcode_mcp_likely": False,
    }

    # Check if mcpbridge binary exists (Xcode 26.3+)
    try:
        subprocess.run(
            ["xcrun", "--find", "mcpbridge"],
            capture_output=True, timeout=5
        ).returncode == 0 and result.update({"xcode_mcp_installed": True})
    except Exception:
        pass

    if not result["xcode_mcp_installed"]:
        return result

    # Check if Xcode is running
    try:
        if subprocess.run(
            ["pgrep", "-x", "Xcode"],
            capture_output=True, timeout=3
        ).returncode == 0:
            result["xcode_running"] = True
    except Exception:
        pass

    # Check if mcpbridge is running
    try:
        if subprocess.run(
            ["pgrep", "-f", "mcpbridge"],
            capture_output=True, timeout=3
        ).returncode == 0:
            result["mcpbridge_running"] = True
    except Exception:
        pass

    result["xcode_mcp_likely"] = (
        result["xcode_running"] or result["mcpbridge_running"]
    )
    return result
