#!/usr/bin/env python3
"""session-start.py — XcodeBuildTools SessionStart context router.

Projects opt in to "Xcode MCP first" routing with the environment variable
XCODEBUILDTOOLS_PREFER_MCP=1. The usual place is the committed project file
`.claude/settings.json`:

    {"env": {"XCODEBUILDTOOLS_PREFER_MCP": "1"}}

The hook reads the variable from its own environment first, then from the
project's `.claude/settings.local.json` and `.claude/settings.json`, so the
setting works even when the host does not pass settings `env` to hooks.
`XCODEBUILDTOOLS_PREFER_MCP=0` in the local file or the environment turns it
off again for one checkout.

* Not opted in: exec the shared common/session-start.py, so the context is
  exactly what earlier versions produced.
* Opted in and the Xcode MCP is usable (Xcode 27 headless server enabled, or
  the windowed Xcode 26.3+ bridge with Xcode running): render
  session-start-mcp-first.md with this worktree's workspace path and the
  approval commands the owner may need.
* Opted in but the MCP is unusable: render the default skills-first context
  with a notice that says why and what the owner can run.

The hook never runs sudo, enables the server or approves anything. It only
prints the commands the owner has to run.
"""

import json
import os
import re
import subprocess
import sys

PREFER_MCP_ENV = "XCODEBUILDTOOLS_PREFER_MCP"
TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off", ""}
SKIPPED_SEARCH_DIRS = {
    "Pods",
    "Carthage",
    "DerivedData",
    "build",
    "node_modules",
}
STATUS_TIMEOUT_SECONDS = 5


# --- Opt-in setting -------------------------------------------------------


def parse_flag(value):
    """Return True/False for a recognised flag value, None otherwise."""
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    return None


def settings_env_value(settings_path, name):
    try:
        with open(settings_path, "r", encoding="utf-8") as handle:
            settings = json.load(handle)
    except (OSError, ValueError):
        return None
    env = settings.get("env") if isinstance(settings, dict) else None
    if not isinstance(env, dict) or name not in env:
        return None
    return env[name]


def prefers_mcp(project_dir, environ):
    """Resolve the opt-in: environment, then settings.local.json, then settings.json."""
    flag = parse_flag(environ.get(PREFER_MCP_ENV))
    if flag is not None:
        return flag
    for filename in ("settings.local.json", "settings.json"):
        path = os.path.join(project_dir, ".claude", filename)
        flag = parse_flag(settings_env_value(path, PREFER_MCP_ENV))
        if flag is not None:
            return flag
    return False


# --- Paths ------------------------------------------------------------------


def git_toplevel(directory, run=subprocess.run):
    try:
        result = run(
            ["git", "-C", directory, "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=STATUS_TIMEOUT_SECONDS,
        )
    except Exception:
        return None
    if result.returncode != 0:
        return None
    toplevel = result.stdout.strip()
    return toplevel or None


def find_workspaces(root):
    """Absolute paths of the workspaces an agent should open for this checkout.

    Prefers .xcworkspace over .xcodeproj, the checkout root over its direct
    subdirectories, and falls back to a root Package.swift folder.
    """

    def entries_with_suffix(directory, suffix):
        try:
            names = sorted(os.listdir(directory))
        except OSError:
            return []
        return [
            os.path.join(directory, name)
            for name in names
            if name.endswith(suffix) and os.path.isdir(os.path.join(directory, name))
        ]

    def subdirectories(directory):
        try:
            names = sorted(os.listdir(directory))
        except OSError:
            return []
        return [
            os.path.join(directory, name)
            for name in names
            if not name.startswith(".")
            and name not in SKIPPED_SEARCH_DIRS
            and not name.endswith((".xcworkspace", ".xcodeproj"))
            and os.path.isdir(os.path.join(directory, name))
        ]

    for suffix in (".xcworkspace", ".xcodeproj"):
        found = entries_with_suffix(root, suffix)
        if found:
            return found
        nested = []
        for child in subdirectories(root):
            nested.extend(entries_with_suffix(child, suffix))
        if nested:
            return nested

    if os.path.isfile(os.path.join(root, "Package.swift")):
        return [root]
    return []


# --- Xcode MCP detection ----------------------------------------------------


def command_succeeds(args, run, timeout):
    try:
        return run(args, capture_output=True, timeout=timeout).returncode == 0
    except Exception:
        return False


def request_subject(entry, kind):
    """Read kind, label, path and signing from one pending request entry.

    Shape seen in Xcode 27.2's `xcrun mcp-server status --format json`:
        {"id": "...", "status": "pending",
         "subject": {"agent": {"_0": {"name": "...", "trust": {"unsigned": {...}}}}}}
        {"id": "...", "status": "pending",
         "subject": {"folder": {"_0": {"projectName": "...", "subtreeRoot": "/path"}}}}
    """
    subject = entry.get("subject")
    subject = subject if isinstance(subject, dict) else {}
    for subject_kind in ("agent", "folder"):
        inner = subject.get(subject_kind)
        if isinstance(inner, dict):
            kind = subject_kind
            details = inner.get("_0") if isinstance(inner.get("_0"), dict) else inner
            break
    else:
        details = entry

    trust = details.get("trust")
    path = details.get("subtreeRoot") or details.get("path") or ""
    label = details.get("name") or details.get("projectName") or path or ""
    return {
        "kind": kind,
        "label": label if isinstance(label, str) else "",
        "path": path if isinstance(path, str) else "",
        "signed": not (isinstance(trust, dict) and "unsigned" in trust),
    }


def pending_requests(status):
    """Collect pending approval requests from `xcrun mcp-server status --format json`.

    Xcode 27.2 lists them under permission.pendingAgentApprovals and
    permission.pendingFolderApprovals. Apple has not documented the format, so
    any list under a key that mentions "pending" is read the same way.
    """
    requests = []

    def visit(value):
        if isinstance(value, dict):
            for key, child in value.items():
                lowered = key.lower()
                if "pending" in lowered and isinstance(child, list):
                    kind = "agent" if "agent" in lowered else "folder" if "folder" in lowered else "request"
                    for entry in child:
                        if not isinstance(entry, dict) or entry.get("id") in (None, ""):
                            continue
                        request = {"id": str(entry["id"])}
                        request.update(request_subject(entry, kind))
                        requests.append(request)
                else:
                    visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(status)
    return requests


def path_overlaps(first, second):
    first = os.path.realpath(first).rstrip("/") + "/"
    second = os.path.realpath(second).rstrip("/") + "/"
    return first.startswith(second) or second.startswith(first)


def relevant_requests(requests, root):
    """Agent requests (any may be this agent) and folder requests about this checkout."""
    return [
        request for request in requests
        if request["kind"] != "folder" or not request["path"] or path_overlaps(request["path"], root)
    ]


def approve_command(request):
    # `--always` is accepted only for signed agents and for folders.
    duration = "--for-24-hours" if request["kind"] == "agent" and not request["signed"] else "--always"
    return f"sudo xcrun mcp-server approve {request['id']} {duration}"


def detect_xcode_mcp(run=subprocess.run):
    """Describe how this Mac's Xcode MCP can be reached.

    Returns a dict with:
        installed: `xcrun --find mcpbridge` succeeds (Xcode 26.3+)
        headless_supported: `xcrun mcp-server status --format json` answered (Xcode 27+)
        headless_enabled: the headless server's permission.enabled is true
        allow_all_agents: permission.unsafeAlwaysAllowAllAgents is true
        pending: pending approval requests, as [{"id", "kind", "label", "path", "signed"}]
        xcode_running: the Xcode app is running (windowed mode)
        mode: "headless", "windowed" or "unavailable"
    """
    result = {
        "installed": False,
        "headless_supported": False,
        "headless_enabled": False,
        "allow_all_agents": False,
        "pending": [],
        "xcode_running": False,
        "mode": "unavailable",
    }

    result["installed"] = command_succeeds(
        ["xcrun", "--find", "mcpbridge"], run, STATUS_TIMEOUT_SECONDS)
    if not result["installed"]:
        return result

    try:
        status_run = run(
            ["xcrun", "mcp-server", "status", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=STATUS_TIMEOUT_SECONDS,
        )
        status = json.loads(status_run.stdout) if status_run.returncode == 0 else None
    except Exception:
        status = None

    if isinstance(status, dict):
        permission = status.get("permission")
        permission = permission if isinstance(permission, dict) else {}
        result["headless_supported"] = True
        result["headless_enabled"] = permission.get("enabled") is True
        result["allow_all_agents"] = permission.get("unsafeAlwaysAllowAllAgents") is True
        result["pending"] = pending_requests(status)

    result["xcode_running"] = command_succeeds(["pgrep", "-x", "Xcode"], run, 3)

    if result["headless_enabled"]:
        result["mode"] = "headless"
    elif result["xcode_running"]:
        result["mode"] = "windowed"
    return result


# --- Rendering --------------------------------------------------------------


def strip_conditional_blocks(content, xcode_mcp_likely):
    keep, drop = ("XCODE_MCP", "NO_XCODE_MCP") if xcode_mcp_likely else ("NO_XCODE_MCP", "XCODE_MCP")
    content = re.sub(rf"<!-- IF_{drop} -->.*?<!-- END_{drop} -->\n?", "", content, flags=re.DOTALL)
    content = re.sub(rf"<!-- IF_{keep} -->\n?", "", content)
    return re.sub(rf"<!-- END_{keep} -->\n?", "", content)


def unavailable_reason(detection):
    if not detection["installed"]:
        return (
            "`xcrun --find mcpbridge` found no Xcode MCP bridge. It ships with Xcode 26.3 and later; "
            "check `xcode-select -p` points at that Xcode."
        )
    if detection["headless_supported"]:
        return (
            "Xcode's headless MCP server is turned off and the Xcode app is not running. "
            "The owner can turn headless mode on once with `sudo xcrun mcp-server enable`, "
            "or open this workspace in Xcode with Settings › Intelligence › "
            "\"Allow external agents to use Xcode tools\" switched on."
        )
    return (
        "the Xcode app is not running. This Xcode has only the windowed MCP bridge, which needs "
        "the workspace open in Xcode with Settings › Intelligence › "
        "\"Allow external agents to use Xcode tools\" switched on."
    )


def workspace_section(root, workspaces):
    if len(workspaces) == 1:
        return f"Workspace for this checkout: `{workspaces[0]}`"
    if workspaces:
        listed = "\n".join(f"- `{path}`" for path in workspaces)
        return (
            "This checkout has several workspaces; pick the one the task is about and keep using it:\n"
            + listed
        )
    return (
        f"No `.xcworkspace`, `.xcodeproj` or `Package.swift` was found near `{root}`. "
        "Use the absolute path of this checkout's workspace."
    )


def approval_section(detection, root):
    if detection["mode"] == "windowed":
        return (
            "Windowed mode (Xcode's headless server is not enabled): the tools reach the workspaces open "
            "in the running Xcode app. Xcode asks for approval in its own window the first time an agent "
            "connects; the plugin's helper clicks \"Allow\" when the terminal has Accessibility access, "
            "otherwise the owner clicks it. If this checkout's workspace is not open in Xcode, use the "
            "XcodeBuildTools skills instead of opening windows yourself."
        )

    lines = []
    if detection["allow_all_agents"]:
        lines.append(
            "Headless mode is enabled and set to allow every agent, so no approval is needed."
        )
    else:
        lines.append(
            "Headless mode: opening a workspace is what asks the owner to approve this agent and the "
            "workspace's folder. If a tool answers that this agent isn't approved, or that the folder "
            "is not permitted, stop using the Xcode MCP for this session, continue with the "
            "XcodeBuildTools skills, and tell the owner to run these once (never run sudo, enable the "
            "server or approve anything yourself):"
        )
        lines.append("")
        lines.append("```bash")
        lines.append("xcrun mcp-server status   # lists the pending request id")
        lines.append("sudo xcrun mcp-server approve <id> --always   # signed agents; otherwise --for-24-hours")
        lines.append(
            f"sudo xcrun mcp-server allow-folder {shell_quote(root)} --always   "
            "# a parent folder covers every worktree under it"
        )
        lines.append("```")
    pending = relevant_requests(detection["pending"], root)
    if pending:
        lines.append("")
        lines.append("Pending requests right now (an agent request may belong to another session):")
        for request in pending:
            label = f" {request['label']}" if request["label"] else ""
            lines.append(f"- {request['kind']}{label}: `{approve_command(request)}`")
    return "\n".join(lines)


def shell_quote(path):
    if re.fullmatch(r"[A-Za-z0-9_./@%+=:,-]+", path):
        return path
    return "'" + path.replace("'", "'\\''") + "'"


def render_mcp_first(template, detection, root, workspaces):
    mode_label = "headless server" if detection["mode"] == "headless" else "windowed bridge"
    replacements = {
        "{{MCP_MODE}}": mode_label,
        "{{WORKSPACE}}": workspace_section(root, workspaces),
        "{{APPROVAL}}": approval_section(detection, root),
    }
    for placeholder, value in replacements.items():
        template = template.replace(placeholder, value)
    return template


def render_unavailable(default_content, detection):
    notice = (
        "## Xcode MCP unavailable\n\n"
        f"This project prefers the Xcode MCP (`{PREFER_MCP_ENV}`), but {unavailable_reason(detection)} "
        "Use the XcodeBuildTools skills below for this whole session.\n\n"
    )
    body = strip_conditional_blocks(default_content, xcode_mcp_likely=False)
    marker = "## Building, Testing & Compilation"
    if marker in body:
        return body.replace(marker, notice + marker, 1)
    return notice + body


def system_message_for(plugin_name, detection, root):
    message = f"The {plugin_name} plugin is loaded and ready."
    if detection["mode"] == "unavailable":
        return message + (
            " Xcode MCP first is on for this project, but the Xcode MCP is unavailable;"
            " using XcodeBuildTools skills."
        )
    message += f" Xcode MCP first ({detection['mode']})."
    pending = relevant_requests(detection["pending"], root) if detection["mode"] == "headless" else []
    if pending:
        commands = "; ".join(f"`{approve_command(request)}`" for request in pending)
        message += f" Pending Xcode MCP approvals (some may be other sessions'): {commands}."
    return message


# --- Entry point ------------------------------------------------------------


def load_text(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def changelog_for(plugin_dir, plugin_name):
    common_dir = os.path.join(plugin_dir, "common")
    if common_dir not in sys.path:
        sys.path.insert(0, common_dir)
    from version_tracker import check_for_updates  # noqa: E402

    name = plugin_name.replace(" ", "")
    config_filename = (name[0].lower() + name[1:] + ".json") if name else "plugin.json"
    changelog, _ = check_for_updates(
        plugin_dir=plugin_dir,
        config_filename=config_filename,
        plugin_name=plugin_name,
    )
    return changelog or ""


def build_response(plugin_dir, project_dir, detection, run=subprocess.run):
    plugin_name = "XcodeBuildTools"
    try:
        with open(os.path.join(plugin_dir, ".claude-plugin", "plugin.json"), "r", encoding="utf-8") as handle:
            plugin_name = json.load(handle).get("name", plugin_name)
    except (OSError, ValueError):
        pass

    root = git_toplevel(project_dir, run=run) or project_dir
    if detection["mode"] == "unavailable":
        context = render_unavailable(load_text(os.path.join(plugin_dir, "session-start.md")), detection)
    else:
        template = load_text(os.path.join(plugin_dir, "session-start-mcp-first.md"))
        context = render_mcp_first(template, detection, root, find_workspaces(root))

    return {
        "systemMessage": system_message_for(plugin_name, detection, root) + changelog_for(plugin_dir, plugin_name),
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        },
    }


def resolve_project_dir(payload, environ):
    for candidate in (environ.get("CLAUDE_PROJECT_DIR"), payload.get("cwd"), os.getcwd()):
        if isinstance(candidate, str) and candidate and os.path.isdir(candidate):
            return os.path.abspath(candidate)
    return os.getcwd()


def exec_default_session_start(plugin_dir, stdin_text):
    """Hand over to the shared common/session-start.py, unchanged behaviour."""
    script = os.path.join(plugin_dir, "common", "session-start.py")
    result = subprocess.run(
        [sys.executable, script, *sys.argv[1:]],
        input=stdin_text,
        text=True,
        capture_output=True,
    )
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    sys.exit(0)


def main():
    plugin_dir = os.environ.get("CLAUDE_PLUGIN_ROOT", "") or os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))
    stdin_text = sys.stdin.read() if not sys.stdin.isatty() else ""
    try:
        payload = json.loads(stdin_text) if stdin_text.strip() else {}
        if not isinstance(payload, dict):
            payload = {}
    except ValueError:
        payload = {}

    try:
        project_dir = resolve_project_dir(payload, os.environ)
        opted_in = prefers_mcp(project_dir, os.environ)
    except Exception as error:
        sys.stderr.write(f"Hook error: {error}\n")
        opted_in = False

    if not opted_in:
        exec_default_session_start(plugin_dir, stdin_text)

    try:
        response = build_response(plugin_dir, project_dir, detect_xcode_mcp())
    except Exception as error:
        # Fail open to today's behaviour rather than leaving the agent without routing.
        sys.stderr.write(f"Hook error: {error}\n")
        exec_default_session_start(plugin_dir, stdin_text)

    print(json.dumps(response))
    sys.exit(0)


if __name__ == "__main__":
    main()
