import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SAFE_ID_RE = /^[A-Za-z0-9_-]+$/;

export function createOpenCodePlugin(pluginRootUrl) {
  const pluginRoot = normalizePluginRoot(pluginRootUrl);
  const state = {
    pluginJson: null,
    infoJson: null,
    deniedOnce: new Set(),
    xcodeMcpLikely: undefined,
    xcodeMcpApprovalStarted: false,
  };

  return async () => ({
    config: async (config) => {
      loadMetadata(pluginRoot, state);
      registerSkills(config, pluginRoot);
      registerMcpServers(config, pluginRoot);
    },

    "experimental.chat.system.transform": async (_input, output) => {
      try {
        loadMetadata(pluginRoot, state);
        await appendSystemContext(pluginRoot, state, output);
      } catch {
        // Fail open. Plugin context should never block a chat request.
      }
    },

    "tool.execute.before": async (input, output) => {
      loadMetadata(pluginRoot, state);
      applyPreToolUseRules(state, input, output);
    },

    "shell.env": async (input, output) => {
      try {
        loadMetadata(pluginRoot, state);
        configureShellEnvironment(pluginRoot, state, input, output);
      } catch {
        // Fail open. Shell commands should still run if setup is unavailable.
      }
    },
  });
}

function normalizePluginRoot(pluginRootUrl) {
  if (pluginRootUrl instanceof URL) {
    return path.resolve(fileURLToPath(pluginRootUrl));
  }

  if (typeof pluginRootUrl === "string" && pluginRootUrl.startsWith("file:")) {
    return path.resolve(fileURLToPath(pluginRootUrl));
  }

  return path.resolve(String(pluginRootUrl));
}

function loadMetadata(pluginRoot, state) {
  if (!state.pluginJson) {
    state.pluginJson = readJsonFile(path.join(pluginRoot, ".claude-plugin", "plugin.json")) ?? {};
  }
  if (!state.infoJson) {
    state.infoJson = readJsonFile(path.join(pluginRoot, "info.json")) ?? {};
  }
}

function registerSkills(config, pluginRoot) {
  const skillsDir = path.join(pluginRoot, "skills");
  if (!hasSkillDirectories(skillsDir)) return;

  if (!isObject(config.skills)) config.skills = {};
  if (!Array.isArray(config.skills.paths)) config.skills.paths = [];
  if (!config.skills.paths.includes(skillsDir)) config.skills.paths.push(skillsDir);
}

function registerMcpServers(config, pluginRoot) {
  const mcpConfig = readJsonFile(path.join(pluginRoot, ".mcp.json"));
  const servers = mcpConfig?.mcpServers;
  if (!isObject(servers)) return;

  if (!isObject(config.mcp)) config.mcp = {};

  for (const [name, server] of Object.entries(servers)) {
    if (!isObject(server) || config.mcp[name]) continue;

    const translated = translateMcpServer(server);
    if (translated) config.mcp[name] = translated;
  }
}

function translateMcpServer(server) {
  if (typeof server.url === "string") {
    const translated = {
      type: "remote",
      url: server.url,
    };
    copyOptionalFields(server, translated, ["enabled", "headers", "timeout"]);
    return translated;
  }

  const command = normalizeCommand(server.command, server.args);
  if (!command) return null;

  const translated = {
    type: "local",
    command,
  };
  copyOptionalFields(server, translated, ["cwd", "enabled", "timeout"]);

  const environment = isObject(server.environment) ? server.environment : server.env;
  if (isObject(environment)) translated.environment = stringifyRecord(environment);

  return translated;
}

function normalizeCommand(command, args) {
  if (Array.isArray(command) && command.every((item) => typeof item === "string")) {
    return command;
  }

  if (typeof command !== "string") return null;

  const result = [command];
  if (Array.isArray(args)) {
    for (const arg of args) {
      if (typeof arg !== "string") return null;
      result.push(arg);
    }
  }
  return result;
}

function copyOptionalFields(source, target, keys) {
  for (const key of keys) {
    if (source[key] === undefined) continue;
    target[key] = key === "headers" && isObject(source[key]) ? stringifyRecord(source[key]) : source[key];
  }
}

async function appendSystemContext(pluginRoot, state, output) {
  if (!Array.isArray(output.system)) output.system = [];

  const pluginName = state.pluginJson.name ?? path.basename(pluginRoot);
  const welcomeMessage = typeof state.infoJson.welcomeMessage === "string" ? state.infoJson.welcomeMessage : "";
  const xcodeMcpLikely = await getXcodeMcpLikely(pluginName, state);
  if (xcodeMcpLikely) startXcodeMcpApproval(pluginRoot, state);
  const sessionStart = renderSessionStart(pluginRoot, xcodeMcpLikely);

  let systemMessage = `The ${pluginName} plugin is loaded and ready.`;
  if (xcodeMcpLikely) systemMessage += " Xcode MCP server detected.";
  if (welcomeMessage) systemMessage += ` ${welcomeMessage}`;

  output.system.push([systemMessage, sessionStart].filter(Boolean).join("\n\n"));
}

function renderSessionStart(pluginRoot, xcodeMcpLikely) {
  const sessionStartPath = path.join(pluginRoot, "session-start.md");
  const content = readTextFile(sessionStartPath);
  if (!content) return "";
  return processConditionalBlocks(content, xcodeMcpLikely);
}

function processConditionalBlocks(content, xcodeMcpLikely) {
  if (xcodeMcpLikely) {
    return content
      .replace(/<!-- IF_XCODE_MCP -->\n?/g, "")
      .replace(/<!-- END_XCODE_MCP -->\n?/g, "")
      .replace(/<!-- IF_NO_XCODE_MCP -->[\s\S]*?<!-- END_NO_XCODE_MCP -->\n?/g, "");
  }

  return content
    .replace(/<!-- IF_NO_XCODE_MCP -->\n?/g, "")
    .replace(/<!-- END_NO_XCODE_MCP -->\n?/g, "")
    .replace(/<!-- IF_XCODE_MCP -->[\s\S]*?<!-- END_XCODE_MCP -->\n?/g, "");
}

async function getXcodeMcpLikely(pluginName, state) {
  if (pluginName !== "XcodeBuildTools") return false;
  if (state.xcodeMcpLikely !== undefined) return state.xcodeMcpLikely;

  const installed = await commandSucceeds("xcrun", ["--find", "mcpbridge"], 5000);
  if (!installed) {
    state.xcodeMcpLikely = false;
    return state.xcodeMcpLikely;
  }

  const xcodeRunning = await commandSucceeds("pgrep", ["-x", "Xcode"], 3000);
  const bridgeRunning = await commandSucceeds("pgrep", ["-f", "mcpbridge"], 3000);
  state.xcodeMcpLikely = xcodeRunning || bridgeRunning;
  return state.xcodeMcpLikely;
}

function startXcodeMcpApproval(pluginRoot, state) {
  if (state.xcodeMcpApprovalStarted) return;
  state.xcodeMcpApprovalStarted = true;

  const runner = path.join(pluginRoot, "hooks", "run-background.sh");
  const target = path.join("hooks", "approve-xcode-mcp.sh");
  if (!fs.existsSync(runner)) return;

  try {
    const child = spawn(runner, [target], {
      cwd: pluginRoot,
      detached: true,
      env: {
        ...process.env,
        CLAUDE_HOOK_OWNER_PID: String(process.pid),
        CLAUDE_PLUGIN_ROOT: pluginRoot,
      },
      stdio: "ignore",
    });
    child.on("error", () => {});
    child.unref();
  } catch {
    // Auto-approval is best-effort; users can still approve Xcode manually.
  }
}

function commandSucceeds(command, args, timeoutMs) {
  return new Promise((resolve) => {
    let settled = false;
    const child = spawn(command, args, { stdio: "ignore" });
    const timer = setTimeout(() => {
      child.kill("SIGTERM");
      finish(false);
    }, timeoutMs);

    child.on("error", () => finish(false));
    child.on("exit", (code) => finish(code === 0));

    function finish(result) {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(result);
    }
  });
}

function applyPreToolUseRules(state, input, output) {
  const tool = String(input.tool ?? "").toLowerCase();
  if (tool !== "bash") return;

  const command = output?.args?.command;
  if (typeof command !== "string" || !command) return;

  const rules = Array.isArray(state.infoJson["pre-tool-use-rules"])
    ? state.infoJson["pre-tool-use-rules"]
    : [];

  for (const rule of rules) {
    if (!isObject(rule)) continue;

    const matchPattern = rule.match;
    if (typeof matchPattern !== "string" || !regexMatches(matchPattern, command)) continue;

    const notMatchPattern = rule.not_match;
    if (typeof notMatchPattern === "string" && regexMatches(notMatchPattern, command)) continue;

    const decision = rule.decision ?? "deny";
    if (decision === "allow") return;

    const message = typeof rule.message === "string" ? rule.message : "Command denied by plugin rule";
    if (decision === "deny") throw new Error(message);

    const ruleName = typeof rule.name === "string" && rule.name ? rule.name : matchPattern;
    const key = `${safeSessionID(input.sessionID ?? "global")}:${ruleName}`;
    if (state.deniedOnce.has(key)) continue;

    state.deniedOnce.add(key);
    throw new Error(message);
  }
}

function configureShellEnvironment(pluginRoot, state, input, output) {
  if (!isObject(output.env)) output.env = {};

  const binDir = path.join(pluginRoot, "bin");
  if (fs.existsSync(binDir)) {
    output.env.PATH = prependPath(binDir, output.env.PATH ?? process.env.PATH ?? "");
  }

  if (state.pluginJson.name !== "XcodeBuildTools") return;

  const sessionID = safeSessionID(input.sessionID ?? input.cwd ?? "default");
  const sandboxBase = path.join(os.tmpdir(), "opencode-xcodebuildtools-sandbox", sessionID);
  const buildDir = path.join(sandboxBase, "build");
  const packagesDir = path.join(sandboxBase, "packages");

  fs.mkdirSync(buildDir, { recursive: true });
  fs.mkdirSync(packagesDir, { recursive: true });
  fs.writeFileSync(
    path.join(sandboxBase, "owner.pid"),
    `${process.pid}\n${process.argv[0] ?? "opencode"}\n`,
    "utf8",
  );

  output.env.SANDBOX_DERIVED_DATA = buildDir;
  output.env.SANDBOX_PACKAGES = packagesDir;
}

function prependPath(entry, current) {
  const parts = current.split(path.delimiter).filter(Boolean).filter((part) => part !== entry);
  return [entry, ...parts].join(path.delimiter);
}

function safeSessionID(value) {
  const raw = String(value ?? "");
  if (SAFE_ID_RE.test(raw)) return raw;

  const hash = createHash("sha256").update(raw || "default").digest("hex").slice(0, 16);
  return `opencode-${hash}`;
}

function regexMatches(pattern, value) {
  try {
    return new RegExp(pattern).test(value);
  } catch {
    return false;
  }
}

function hasSkillDirectories(skillsDir) {
  try {
    return fs.readdirSync(skillsDir, { withFileTypes: true }).some((entry) => {
      return entry.isDirectory() && fs.existsSync(path.join(skillsDir, entry.name, "SKILL.md"));
    });
  } catch {
    return false;
  }
}

function readJsonFile(filePath) {
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch {
    return null;
  }
}

function readTextFile(filePath) {
  try {
    return fs.readFileSync(filePath, "utf8");
  } catch {
    return "";
  }
}

function stringifyRecord(value) {
  return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, String(item)]));
}

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}
