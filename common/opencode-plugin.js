import { spawn } from "node:child_process";
import { createHash, randomUUID } from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SAFE_ID_RE = /^[A-Za-z0-9_-]+$/;
const MCP_PLACEHOLDER_RE = /\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}/g;
const MCP_COMPATIBILITY_ENVIRONMENT_KEYS = new Set([
  "CLAUDE_PLUGIN_ROOT",
  "CLAUDE_PLUGIN_DATA",
  "CLAUDE_PROJECT_DIR",
]);
const UUID_V4_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const PROCESS_START_OUTPUT_MAX_CHARS = 256;
const PROCESS_START_TIMEOUT_MS = 5_000;
const PROCESS_TERMINATION_GRACE_MS = 250;
const XCODE_MCP_CACHE_TTL_MS = 30_000;
const XCRUN_OPTIONS_WITH_VALUE = new Set([
  "--sdk",
  "-sdk",
  "--toolchain",
  "-toolchain",
]);
const XCRUN_OPTIONS_WITHOUT_VALUE = new Set([
  "-h",
  "--help",
  "--version",
  "-v",
  "--verbose",
  "-l",
  "--log",
  "-f",
  "--find",
  "-r",
  "--run",
  "-n",
  "--no-cache",
  "-k",
  "--kill-cache",
  "--show-sdk-path",
  "--show-sdk-version",
  "--show-sdk-build-version",
  "--show-sdk-platform-path",
  "--show-sdk-platform-version",
  "--show-toolchain-path",
]);
const XCODE_SANDBOX_DIR = "opencode-xcodebuildtools-sandbox";
const XCODE_SANDBOX_MODE = 0o700;
const XCODE_SANDBOX_OWNER_GRACE_MS = 60_000;
const XCODE_SANDBOX_OWNER_LOCK = ".owner.lock";
const XCODE_SANDBOX_QUARANTINE_RE =
  /^\.quarantine-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const XCODE_SANDBOX_PENDING_CLEANUPS_KEY = Symbol.for(
  "opencode.xcodebuildtools.pending-cleanups",
);
const pendingSandboxCleanups =
  globalThis[XCODE_SANDBOX_PENDING_CLEANUPS_KEY] instanceof Set
    ? globalThis[XCODE_SANDBOX_PENDING_CLEANUPS_KEY]
    : new Set();
globalThis[XCODE_SANDBOX_PENDING_CLEANUPS_KEY] = pendingSandboxCleanups;

export function createOpenCodePlugin(pluginRootUrl) {
  const pluginRoot = normalizePluginRoot(pluginRootUrl);
  return async (input = {}) => {
    const state = {
      pluginJson: null,
      infoJson: null,
      pluginData: null,
      config: null,
      instanceID: randomUUID(),
      processStartToken: null,
      deniedOnce: new Set(),
      xcodeMcpCache: new Map(),
      xcodeMcpApprovalSessions: new Set(),
      sandboxRoot: null,
      ownedSandboxes: new Map(),
      ownedSandboxIdentities: new Map(),
      deletedSandboxSessions: new Set(),
      sandboxSweepDone: false,
      disposed: false,
    };
    const mcpContext = {
      pluginRoot,
      pluginData: () => pluginDataDirectory(pluginRoot, state),
      projectDir: input?.worktree || input?.directory,
    };

    return {
      config: async (config) => {
        loadMetadata(pluginRoot, state);
        registerSkills(config, pluginRoot);
        registerMcpServers(config, pluginRoot, mcpContext);
        state.config = config;
      },

      "experimental.chat.system.transform": async (input, output) => {
        try {
          loadMetadata(pluginRoot, state);
          await appendSystemContext(pluginRoot, state, input, output);
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
          await configureShellEnvironment(pluginRoot, state, input, output);
        } catch {
          // Fail open. Shell commands should still run if setup is unavailable.
        }
      },

      event: async ({ event }) => {
        await handlePluginEvent(state, event);
      },

      dispose: async () => {
        await detachOwnedSandboxes(state);
      },
    };
  };
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

function pluginDataDirectory(pluginRoot, state) {
  if (state.pluginData) return state.pluginData;

  loadMetadata(pluginRoot, state);
  const pluginName = state.pluginJson.name || path.basename(pluginRoot) || "plugin";
  const pluginID = String(pluginName).replace(/[^A-Za-z0-9_-]/g, "-");
  const dataHome = process.env.XDG_DATA_HOME || path.join(os.homedir(), ".local", "share");
  const pluginData = path.resolve(dataHome, "opencode", "plugin-data", pluginID);
  fs.mkdirSync(pluginData, { recursive: true });
  state.pluginData = pluginData;
  return pluginData;
}

function registerSkills(config, pluginRoot) {
  const skillsDir = path.join(pluginRoot, "skills");
  if (!hasSkillDirectories(skillsDir)) return;

  if (!isObject(config.skills)) config.skills = {};
  if (!Array.isArray(config.skills.paths)) config.skills.paths = [];
  if (!config.skills.paths.includes(skillsDir)) config.skills.paths.push(skillsDir);
}

function registerMcpServers(config, pluginRoot, context) {
  const mcpConfig = readJsonFile(path.join(pluginRoot, ".mcp.json"));
  const servers = mcpConfig?.mcpServers;
  if (!isObject(servers)) return;

  if (!isObject(config.mcp)) config.mcp = {};

  for (const [name, server] of Object.entries(servers)) {
    if (!isObject(server) || config.mcp[name]) continue;

    const translated = translateMcpServer(server, context);
    if (translated && !hasMcpEndpoint(config.mcp, translated)) {
      config.mcp[name] = translated;
    }
  }
}

function hasMcpEndpoint(servers, candidate) {
  return Object.values(servers).some((server) => {
    if (!isObject(server) || server.type !== candidate.type) return false;
    if (candidate.type === "remote") return server.url === candidate.url;
    if (candidate.type !== "local") return false;
    if (!Array.isArray(server.command) || !Array.isArray(candidate.command)) return false;
    return (
      server.command.length === candidate.command.length &&
      server.command.every((item, index) => item === candidate.command[index]) &&
      server.cwd === candidate.cwd &&
      mcpEnvironmentMatches(server.environment, candidate.environment)
    );
  });
}

function mcpEnvironmentMatches(left, right) {
  const leftEntries = comparableMcpEnvironment(left);
  const rightEntries = comparableMcpEnvironment(right);
  if (!leftEntries || !rightEntries || leftEntries.length !== rightEntries.length) {
    return false;
  }
  return leftEntries.every(([key, value], index) => {
    const [rightKey, rightValue] = rightEntries[index];
    return key === rightKey && value === rightValue;
  });
}

function comparableMcpEnvironment(environment) {
  if (environment === undefined) return [];
  if (!isObject(environment)) return null;
  return Object.entries(environment)
    .filter(([key]) => !MCP_COMPATIBILITY_ENVIRONMENT_KEYS.has(key))
    .sort(([left], [right]) => left.localeCompare(right));
}

function translateMcpServer(server, context) {
  if (typeof server.url === "string") {
    const translated = {
      type: "remote",
      url: expandMcpString(server.url, context),
    };
    copyOptionalFields(server, translated, ["enabled", "headers", "timeout"], context);
    const oauth = translateMcpOAuth(server.oauth);
    if (oauth !== undefined) translated.oauth = oauth;
    return translated;
  }

  const command = normalizeCommand(server.command, server.args, context);
  if (!command) return null;

  const translated = {
    type: "local",
    command,
  };
  copyOptionalFields(server, translated, ["cwd", "enabled", "timeout"], context);

  const environment = isObject(server.environment) ? server.environment : server.env;
  translated.environment = {
    ...(isObject(environment) ? expandMcpRecord(environment, context) : {}),
    ...expandMcpRecord(
      {
        CLAUDE_PLUGIN_ROOT: "${CLAUDE_PLUGIN_ROOT}",
        CLAUDE_PLUGIN_DATA: "${CLAUDE_PLUGIN_DATA}",
        CLAUDE_PROJECT_DIR: "${CLAUDE_PROJECT_DIR}",
      },
      context,
    ),
  };

  return translated;
}

function translateMcpOAuth(oauth) {
  if (oauth === false) return false;
  if (!isObject(oauth)) return undefined;

  const translated = {};
  for (const key of ["clientId", "clientSecret", "redirectUri"]) {
    if (typeof oauth[key] === "string") translated[key] = oauth[key];
  }

  if (
    Number.isInteger(oauth.callbackPort) &&
    oauth.callbackPort >= 1 &&
    oauth.callbackPort <= 65_535
  ) {
    translated.callbackPort = oauth.callbackPort;
  }

  if (typeof oauth.scopes === "string") {
    translated.scope = oauth.scopes;
  } else if (typeof oauth.scope === "string") {
    translated.scope = oauth.scope;
  }

  return translated;
}

function normalizeCommand(command, args, context) {
  if (Array.isArray(command) && command.every((item) => typeof item === "string")) {
    return command.map((item) => expandMcpString(item, context));
  }

  if (typeof command !== "string") return null;

  if (Array.isArray(args)) {
    if (!args.every((arg) => typeof arg === "string")) return null;
    return [command, ...args].map((item) => expandMcpString(item, context));
  }
  return [expandMcpString(command, context)];
}

function copyOptionalFields(source, target, keys, context) {
  for (const key of keys) {
    if (source[key] === undefined) continue;
    if (key === "headers" && isObject(source[key])) {
      target[key] = expandMcpRecord(source[key], context);
    } else if (key === "cwd" && typeof source[key] === "string") {
      target[key] = expandMcpString(source[key], context);
    } else {
      target[key] = source[key];
    }
  }
}

function expandMcpRecord(value, context) {
  return Object.fromEntries(
    Object.entries(stringifyRecord(value)).map(([key, item]) => [
      key,
      expandMcpString(item, context),
    ]),
  );
}

function expandMcpString(value, context) {
  return value.replace(MCP_PLACEHOLDER_RE, (_, name, defaultValue) => {
    const resolved = mcpVariable(name, context);
    if (defaultValue !== undefined && (resolved === undefined || resolved === "")) {
      return defaultValue;
    }
    if (resolved === undefined) {
      throw new Error(`MCP configuration references unset variable: ${name}`);
    }
    return resolved;
  });
}

function mcpVariable(name, context) {
  if (name === "CLAUDE_PLUGIN_ROOT") return context.pluginRoot;
  if (name === "CLAUDE_PLUGIN_DATA") return context.pluginData();
  if (name === "CLAUDE_PROJECT_DIR") return context.projectDir;
  return process.env[name];
}

async function appendSystemContext(pluginRoot, state, input, output) {
  if (!Array.isArray(output.system)) output.system = [];

  const pluginName = state.pluginJson.name ?? path.basename(pluginRoot);
  const welcomeMessage = typeof state.infoJson.welcomeMessage === "string" ? state.infoJson.welcomeMessage : "";
  const sessionID = safeSessionID(input?.sessionID ?? "global");
  const xcodeMcpLikely = await getXcodeMcpLikely(pluginName, state, sessionID);
  if (xcodeMcpLikely) startXcodeMcpApproval(pluginRoot, state, sessionID);
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

async function getXcodeMcpLikely(pluginName, state, sessionID) {
  if (pluginName !== "XcodeBuildTools") return false;
  if (!hasConfiguredMcpbridge(state.config)) {
    state.xcodeMcpCache.delete(sessionID);
    return false;
  }

  const now = Date.now();
  const cached = state.xcodeMcpCache.get(sessionID);
  if (cached && now - cached.checkedAt < XCODE_MCP_CACHE_TTL_MS) return cached.value;

  const installed = await commandSucceeds("xcrun", ["--find", "mcpbridge"], 5000);
  if (!installed) {
    state.xcodeMcpCache.set(sessionID, { checkedAt: now, value: false });
    return false;
  }

  const xcodeRunning = await commandSucceeds("pgrep", ["-x", "Xcode"], 3000);
  const bridgeRunning = await commandSucceeds("pgrep", ["-f", "mcpbridge"], 3000);
  const value = xcodeRunning || bridgeRunning;
  state.xcodeMcpCache.set(sessionID, { checkedAt: now, value });
  return value;
}

function hasConfiguredMcpbridge(config) {
  if (!isObject(config?.mcp)) return false;

  return Object.values(config.mcp).some((server) => {
    if (!isObject(server) || server.enabled === false || server.type !== "local") return false;

    const command = Array.isArray(server.command) ? server.command : [server.command];
    const executable = commandBasename(command[0]);
    if (executable === "mcpbridge") return true;
    if (executable !== "xcrun") return false;
    return xcrunToolBasename(command.slice(1)) === "mcpbridge";
  });
}

function commandBasename(value) {
  const commandPart = normalizedCommandPart(value);
  return commandPart ? path.basename(commandPart) : "";
}

function normalizedCommandPart(value) {
  if (typeof value !== "string") return "";
  return value.trim().replace(/^['"]|['"]$/g, "");
}

function xcrunToolBasename(args) {
  for (let index = 0; index < args.length; index += 1) {
    const argument = normalizedCommandPart(args[index]);
    if (!argument) return "";
    if (argument === "--") {
      return commandBasename(args[index + 1]);
    }
    if (XCRUN_OPTIONS_WITH_VALUE.has(argument)) {
      index += 1;
      continue;
    }
    if (/^(?:--?sdk|--?toolchain)=/.test(argument)) continue;
    if (XCRUN_OPTIONS_WITHOUT_VALUE.has(argument)) continue;
    if (argument.startsWith("-")) return "";
    return path.basename(argument);
  }
  return "";
}

function startXcodeMcpApproval(pluginRoot, state, sessionID) {
  if (state.xcodeMcpApprovalSessions.has(sessionID)) return;

  const runner = path.join(pluginRoot, "hooks", "run-background.sh");
  const target = path.join("hooks", "approve-xcode-mcp.sh");
  if (!fs.existsSync(runner)) return;

  try {
    state.xcodeMcpApprovalSessions.add(sessionID);
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
    child.on("error", () => state.xcodeMcpApprovalSessions.delete(sessionID));
    child.unref();
  } catch {
    state.xcodeMcpApprovalSessions.delete(sessionID);
    // Auto-approval is best-effort; users can still approve Xcode manually.
  }
}

function commandSucceeds(command, args, timeoutMs) {
  return new Promise((resolve) => {
    let settled = false;
    let timedOut = false;
    let timeoutTimer;
    let forceKillTimer;
    let child;

    try {
      child = spawn(command, args, { stdio: "ignore" });
    } catch {
      resolve(false);
      return;
    }

    const onError = () => finish(false);
    const onExit = (code) => finish(!timedOut && code === 0);
    child.on("error", onError);
    child.on("exit", onExit);
    timeoutTimer = setTimeout(beginTermination, timeoutMs);

    function beginTermination() {
      if (settled) return;
      timedOut = true;
      forceKillTimer = terminateChildAfterGrace(
        child,
        () => !settled,
        () => finish(false),
      );
    }

    function finish(result) {
      if (settled) return;
      settled = true;
      clearTimeout(timeoutTimer);
      clearTimeout(forceKillTimer);
      child.removeListener?.("error", onError);
      child.removeListener?.("exit", onExit);
      resolve(result);
    }
  });
}

function terminateChildAfterGrace(child, isPending, onForcedTermination) {
  try {
    child.kill("SIGTERM");
  } catch {
    // Continue to forced termination so the timed-out child is detached.
  }
  if (!isPending()) return undefined;

  return setTimeout(() => {
    if (!isPending()) return;
    try {
      child.kill("SIGKILL");
    } catch {
      // The process may have exited between the grace timer and this call.
    }
    try {
      child.stdout?.destroy?.();
      child.stderr?.destroy?.();
    } catch {
      // Detaching the child still allows the parent to continue.
    }
    try {
      child.unref();
    } catch {
      // Resolving the caller is more important than detaching a broken shim.
    }
    onForcedTermination();
  }, PROCESS_TERMINATION_GRACE_MS);
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

async function configureShellEnvironment(pluginRoot, state, input, output) {
  if (!isObject(output.env)) output.env = {};

  const binDir = path.join(pluginRoot, "bin");
  if (fs.existsSync(binDir)) {
    output.env.PATH = prependPath(binDir, output.env.PATH ?? process.env.PATH ?? "");
  }

  if (state.pluginJson.name !== "XcodeBuildTools") return;

  const sessionID = safeSessionID(input.sessionID ?? input.cwd ?? "default");
  if (state.disposed || state.deletedSandboxSessions.has(sessionID)) return;
  const sandboxRoot = secureSandboxRoot(state);
  // Plugin instances never reuse a sandbox path, so an older instance cannot
  // delete a replacement instance's active sandbox after an ownership check.
  const sandboxBase = path.join(sandboxRoot.path, `${sessionID}-${state.instanceID}`);
  state.ownedSandboxes.set(sessionID, sandboxBase);

  if (!state.processStartToken) {
    state.processStartToken = await readProcessStartToken(process.pid);
  }
  if (sandboxSetupIsCancelled(state, sessionID, sandboxBase)) return;

  if (!state.sandboxSweepDone) {
    await sweepStaleSandboxes(sandboxRoot);
    state.sandboxSweepDone = true;
  }
  if (sandboxSetupIsCancelled(state, sessionID, sandboxBase)) return;

  const buildDir = path.join(sandboxBase, "build");
  const packagesDir = path.join(sandboxBase, "packages");

  const sandboxIdentity = secureSandboxDirectory(sandboxBase, sandboxRoot);
  state.ownedSandboxIdentities.set(sessionID, sandboxIdentity);
  if (sandboxSetupIsCancelled(state, sessionID, sandboxBase)) return;
  secureSandboxDirectory(buildDir, sandboxIdentity);
  secureSandboxDirectory(packagesDir, sandboxIdentity);
  writeSandboxOwner(
    sandboxIdentity,
    state.processStartToken,
    state.instanceID,
  );

  output.env.SANDBOX_DERIVED_DATA = buildDir;
  output.env.SANDBOX_PACKAGES = packagesDir;
}

function secureSandboxRoot(state) {
  if (state.sandboxRoot) {
    revalidateSandboxDirectory(state.sandboxRoot);
    return state.sandboxRoot;
  }

  const temporaryDirectory = path.resolve(os.tmpdir());
  const canonicalTemporaryDirectory = canonicalPath(temporaryDirectory);
  const sandboxRoot = path.join(temporaryDirectory, XCODE_SANDBOX_DIR);
  const expectedCanonicalPath = path.join(
    canonicalTemporaryDirectory,
    XCODE_SANDBOX_DIR,
  );

  createDirectoryNonRecursively(sandboxRoot);
  const identity = inspectSandboxDirectory(
    sandboxRoot,
    expectedCanonicalPath,
    null,
  );
  state.sandboxRoot = identity;
  return identity;
}

function secureSandboxDirectory(directoryPath, parentIdentity) {
  revalidateSandboxDirectory(parentIdentity);

  const candidate = path.resolve(directoryPath);
  const parentPath = path.resolve(parentIdentity.path);
  if (path.dirname(candidate) !== parentPath) {
    throw new Error("Sandbox directory must be a direct child of its trusted parent");
  }

  const name = path.basename(candidate);
  if (!SAFE_ID_RE.test(name)) {
    throw new Error("Sandbox directory has an unsafe name");
  }

  createDirectoryNonRecursively(candidate);
  return inspectSandboxDirectory(
    candidate,
    path.join(parentIdentity.canonicalPath, name),
    parentIdentity,
  );
}

function createDirectoryNonRecursively(directoryPath) {
  try {
    fs.mkdirSync(directoryPath, { mode: XCODE_SANDBOX_MODE });
  } catch (error) {
    if (error?.code !== "EEXIST") throw error;
  }
}

function inspectSandboxDirectory(directoryPath, expectedCanonicalPath, parentIdentity) {
  if (typeof process.getuid !== "function") {
    throw new Error("Xcode sandbox setup requires POSIX ownership checks");
  }

  const directoryFlags =
    fs.constants.O_RDONLY |
    (fs.constants.O_DIRECTORY ?? 0) |
    (fs.constants.O_NOFOLLOW ?? 0);
  const descriptor = fs.openSync(directoryPath, directoryFlags);
  try {
    const before = fs.fstatSync(descriptor);
    if (!before.isDirectory() || before.uid !== process.getuid()) {
      throw new Error("Sandbox directory is not owned by the current user");
    }

    fs.fchmodSync(descriptor, XCODE_SANDBOX_MODE);
    const after = fs.fstatSync(descriptor);
    const link = fs.lstatSync(directoryPath);
    if (
      !after.isDirectory() ||
      !link.isDirectory() ||
      link.isSymbolicLink() ||
      after.uid !== process.getuid() ||
      link.uid !== process.getuid() ||
      after.dev !== link.dev ||
      after.ino !== link.ino ||
      (after.mode & 0o777) !== XCODE_SANDBOX_MODE
    ) {
      throw new Error("Sandbox directory identity changed during validation");
    }

    const resolved = canonicalPath(directoryPath);
    if (resolved !== path.resolve(expectedCanonicalPath)) {
      throw new Error("Sandbox directory escaped its trusted parent");
    }

    return {
      path: path.resolve(directoryPath),
      canonicalPath: resolved,
      dev: after.dev,
      ino: after.ino,
      uid: after.uid,
      parent: parentIdentity,
    };
  } finally {
    fs.closeSync(descriptor);
  }
}

function revalidateSandboxDirectory(identity) {
  if (!identity) throw new Error("Sandbox directory identity is unavailable");
  if (identity.parent) revalidateSandboxDirectory(identity.parent);

  const current = inspectSandboxDirectory(
    identity.path,
    identity.canonicalPath,
    identity.parent,
  );
  if (
    current.dev !== identity.dev ||
    current.ino !== identity.ino ||
    current.uid !== identity.uid
  ) {
    throw new Error("Sandbox directory was replaced");
  }
  return current;
}

function canonicalPath(filePath) {
  return fs.realpathSync.native?.(filePath) ?? fs.realpathSync(filePath);
}

function sandboxSetupIsCancelled(state, sessionID, sandboxBase) {
  return (
    state.disposed ||
    state.deletedSandboxSessions.has(sessionID) ||
    state.ownedSandboxes.get(sessionID) !== sandboxBase
  );
}

function writeSandboxOwner(sandboxIdentity, processStartToken, instanceID) {
  revalidateSandboxDirectory(sandboxIdentity);
  const sandboxBase = sandboxIdentity.path;
  const ownerPath = path.join(sandboxBase, "owner.pid");
  const temporaryPath = path.join(sandboxBase, `owner.pid.${instanceID}.tmp`);
  const content = `${process.pid}\n${process.argv[0] ?? "opencode"}\n${processStartToken}\n${instanceID}\n`;
  const ownerLock = acquireSandboxOwnerLock(
    sandboxBase,
    sandboxIdentity.parent,
    sandboxIdentity,
  );
  if (!ownerLock) throw new Error("Sandbox owner is being updated or removed");

  try {
    fs.writeFileSync(temporaryPath, content, {
      encoding: "utf8",
      flag: "wx",
      mode: 0o600,
    });
    if (!sandboxOwnerLockIsHeld(ownerLock)) {
      throw new Error("Sandbox owner lock changed during update");
    }
    fs.renameSync(temporaryPath, ownerPath);
  } catch (error) {
    try {
      fs.unlinkSync(temporaryPath);
    } catch {
      // The stale-sandbox sweep handles any temporary file left behind.
    }
    throw error;
  } finally {
    releaseSandboxOwnerLock(ownerLock);
  }
}

function markSandboxCleanupPending(sandboxBase, instanceID, ownerLock) {
  const ownerPath = path.join(sandboxBase, "owner.pid");
  const temporaryPath = path.join(sandboxBase, `owner.pid.${instanceID}.cleanup.tmp`);
  const content = `${process.pid}\ncleanup-pending\n\n${instanceID}\ncleanup-pending\n`;

  try {
    fs.writeFileSync(temporaryPath, content, {
      encoding: "utf8",
      flag: "wx",
      mode: 0o600,
    });
    if (!sandboxOwnerLockIsHeld(ownerLock)) return false;
    fs.renameSync(temporaryPath, ownerPath);
    return true;
  } catch {
    return false;
  } finally {
    try {
      fs.unlinkSync(temporaryPath);
    } catch {
      // A successful rename removes the temporary path.
    }
  }
}

function acquireSandboxOwnerLock(
  sandboxBase,
  sandboxRootIdentity = null,
  expectedSandboxIdentity = null,
) {
  let sandboxIdentity = null;
  if (sandboxRootIdentity) {
    sandboxIdentity = secureExistingManagedSandbox(
      sandboxBase,
      sandboxRootIdentity,
      expectedSandboxIdentity,
    );
    if (!sandboxIdentity) return null;
  }

  const lockPath = path.join(sandboxBase, XCODE_SANDBOX_OWNER_LOCK);
  const token = randomUUID();
  const createdLock = createSandboxOwnerLock(lockPath, token);
  if (createdLock) {
    return attachSandboxIdentityToLock(
      createdLock,
      sandboxRootIdentity,
      sandboxIdentity,
    );
  }

  const observedLock = readSandboxOwnerLock(lockPath);
  if (!observedLock) return null;
  if (Date.now() - observedLock.mtimeMs < XCODE_SANDBOX_OWNER_GRACE_MS) return null;

  const claimedPath = `${lockPath}.${token}.stale`;
  try {
    fs.renameSync(lockPath, claimedPath);
  } catch {
    return null;
  }

  const claimedLock = readSandboxOwnerLock(claimedPath);
  if (!sameSandboxOwnerLock(observedLock, claimedLock)) {
    restoreClaimedSandboxOwnerLock(claimedPath, lockPath);
    return null;
  }

  try {
    fs.unlinkSync(claimedPath);
  } catch {
    restoreClaimedSandboxOwnerLock(claimedPath, lockPath);
    return null;
  }

  return attachSandboxIdentityToLock(
    createSandboxOwnerLock(lockPath, token),
    sandboxRootIdentity,
    sandboxIdentity,
  );
}

function attachSandboxIdentityToLock(ownerLock, sandboxRootIdentity, sandboxIdentity) {
  if (!ownerLock || !sandboxRootIdentity || !sandboxIdentity) return ownerLock;
  return { ...ownerLock, sandboxRootIdentity, sandboxIdentity };
}

function createSandboxOwnerLock(lockPath, token) {
  try {
    fs.writeFileSync(lockPath, `${token}\n`, { encoding: "utf8", flag: "wx" });
  } catch {
    return null;
  }

  const ownerLock = readSandboxOwnerLock(lockPath);
  if (!ownerLock || ownerLock.token !== token) return null;
  return ownerLock;
}

function readSandboxOwnerLock(lockPath) {
  try {
    const before = fs.statSync(lockPath);
    if (!before.isFile()) return null;
    const beforeToken = fs.readFileSync(lockPath, "utf8").trim();
    const after = fs.statSync(lockPath);
    const afterToken = fs.readFileSync(lockPath, "utf8").trim();
    if (!sameSandboxOwnerLockVersion(before, after) || beforeToken !== afterToken) return null;

    return {
      path: lockPath,
      token: afterToken,
      dev: after.dev,
      ino: after.ino,
      mtimeMs: after.mtimeMs,
    };
  } catch {
    return null;
  }
}

function sameSandboxOwnerLockVersion(left, right) {
  return (
    left.dev === right.dev &&
    left.ino === right.ino &&
    left.size === right.size &&
    left.mtimeMs === right.mtimeMs &&
    left.ctimeMs === right.ctimeMs
  );
}

function sameSandboxOwnerLock(left, right) {
  return Boolean(
    left &&
      right &&
      left.dev === right.dev &&
      left.ino === right.ino &&
      left.token === right.token,
  );
}

function sandboxOwnerLockIsHeld(ownerLock) {
  if (
    ownerLock?.sandboxRootIdentity &&
    !secureExistingManagedSandbox(
      ownerLock.sandboxIdentity.path,
      ownerLock.sandboxRootIdentity,
      ownerLock.sandboxIdentity,
    )
  ) {
    return false;
  }
  return sameSandboxOwnerLock(ownerLock, readSandboxOwnerLock(ownerLock.path));
}

function restoreClaimedSandboxOwnerLock(claimedPath, lockPath) {
  try {
    // A hard link restores the claimed inode only when the lock path is still
    // absent, without overwriting a lock another actor acquired meanwhile.
    fs.linkSync(claimedPath, lockPath);
    fs.unlinkSync(claimedPath);
  } catch {
    // Leave the uniquely named claim in place if ownership cannot be restored.
  }
}

function releaseSandboxOwnerLock(ownerLock) {
  if (!sandboxOwnerLockIsHeld(ownerLock)) return;

  const claimedPath = `${ownerLock.path}.${randomUUID()}.release`;
  try {
    fs.renameSync(ownerLock.path, claimedPath);
  } catch {
    return;
  }

  const claimedLock = readSandboxOwnerLock(claimedPath);
  if (!sameSandboxOwnerLock(ownerLock, claimedLock)) {
    restoreClaimedSandboxOwnerLock(claimedPath, ownerLock.path);
    return;
  }

  try {
    fs.unlinkSync(claimedPath);
  } catch {
    // The sandbox may already have been removed with the lock inside it.
  }
}

async function handlePluginEvent(state, event) {
  if (event?.type !== "session.deleted") return;

  const sessionID = event.properties?.info?.id;
  if (typeof sessionID !== "string" || !sessionID) return;

  const safeID = safeSessionID(sessionID);
  state.deletedSandboxSessions.add(safeID);
  state.xcodeMcpCache.delete(safeID);
  state.xcodeMcpApprovalSessions.delete(safeID);
  await removeOwnedSandbox(state, safeID);
}

async function removeOwnedSandbox(state, sessionID) {
  const sandboxPath = state.ownedSandboxes.get(sessionID);
  if (!sandboxPath) return;

  const sandboxIdentity = state.ownedSandboxIdentities.get(sessionID);
  markPendingSandboxCleanup(sandboxPath);
  state.ownedSandboxes.delete(sessionID);
  state.ownedSandboxIdentities.delete(sessionID);
  if (!state.sandboxRoot || !sandboxIdentity) return;

  const quarantinedPath = await quarantineOwnedSandbox(
    sandboxPath,
    state.instanceID,
    state.sandboxRoot,
    sandboxIdentity,
  );
  const cleanupIdentity = quarantinedPath
    ? relocatedSandboxIdentity(sandboxIdentity, quarantinedPath)
    : sandboxIdentity;
  await removeManagedSandbox(
    quarantinedPath || sandboxPath,
    quarantinedPath ? "" : state.instanceID,
    state.sandboxRoot,
    cleanupIdentity,
  );
}

async function detachOwnedSandboxes(state) {
  state.disposed = true;
  const sandboxes = [...state.ownedSandboxes.entries()].map(([sessionID, sandboxPath]) => ({
    sandboxPath,
    sandboxIdentity: state.ownedSandboxIdentities.get(sessionID),
  }));
  const sandboxPaths = [...new Set(sandboxes.map(({ sandboxPath }) => sandboxPath))];
  for (const sandboxPath of sandboxPaths) markPendingSandboxCleanup(sandboxPath);
  state.ownedSandboxes.clear();
  state.ownedSandboxIdentities.clear();
  state.xcodeMcpCache.clear();
  state.xcodeMcpApprovalSessions.clear();
  const cleanupTargets = await Promise.all(
    sandboxes.map(async ({ sandboxPath, sandboxIdentity }) => {
      if (!state.sandboxRoot || !sandboxIdentity) return null;
      const quarantinedPath = await quarantineOwnedSandbox(
        sandboxPath,
        state.instanceID,
        state.sandboxRoot,
        sandboxIdentity,
      );
      return {
        path: quarantinedPath || sandboxPath,
        expectedInstanceID: quarantinedPath ? "" : state.instanceID,
        identity: quarantinedPath
          ? relocatedSandboxIdentity(sandboxIdentity, quarantinedPath)
          : sandboxIdentity,
      };
    }),
  );
  await Promise.all(
    cleanupTargets.filter(Boolean).map(({ path: sandboxPath, expectedInstanceID, identity }) =>
      detachManagedSandbox(
        sandboxPath,
        expectedInstanceID,
        state.sandboxRoot,
        identity,
      ),
    ),
  );
}

async function sweepStaleSandboxes(sandboxRootIdentity) {
  let entries;
  try {
    revalidateSandboxDirectory(sandboxRootIdentity);
    entries = await fs.promises.readdir(sandboxRootIdentity.path, {
      withFileTypes: true,
    });
  } catch {
    return;
  }

  await Promise.all(
    entries.map(async (entry) => {
      const isQuarantine = XCODE_SANDBOX_QUARANTINE_RE.test(entry.name);
      if (!entry.isDirectory() || (!SAFE_ID_RE.test(entry.name) && !isQuarantine)) return;

      const sandboxPath = path.join(sandboxRootIdentity.path, entry.name);
      const sandboxIdentity = secureExistingManagedSandbox(
        sandboxPath,
        sandboxRootIdentity,
      );
      if (!sandboxIdentity) return;
      const owner = await readSandboxOwner(sandboxPath);
      const cleanupPending = owner?.cleanupPending || sandboxCleanupIsPending(sandboxPath);
      if (!owner || cleanupPending) {
        if (!cleanupPending && !isQuarantine && !(await sandboxIsPastOwnerGracePeriod(sandboxPath))) {
          return;
        }

        const ownerLock = acquireSandboxOwnerLock(
          sandboxPath,
          sandboxRootIdentity,
          sandboxIdentity,
        );
        if (!ownerLock) return;
        let releaseLock = ownerLock;
        try {
          // A writer may have published an owner after the initial read or
          // stale-stat snapshot. Only remove while the publication lock is
          // held and the marker is still invalid.
          const currentOwner = await readSandboxOwner(sandboxPath);
          const currentCleanupPending =
            currentOwner?.cleanupPending || sandboxCleanupIsPending(sandboxPath);
          if (
            (!currentOwner || currentCleanupPending) &&
            sandboxOwnerLockIsHeld(ownerLock)
          ) {
            const quarantined = await quarantineManagedSandbox(
              sandboxPath,
              ownerLock,
              sandboxRootIdentity,
              sandboxIdentity,
            );
            releaseLock = quarantined.ownerLock;
            if (quarantined.path) {
              await removeManagedSandbox(
                quarantined.path,
                "",
                sandboxRootIdentity,
                relocatedSandboxIdentity(sandboxIdentity, quarantined.path),
              );
            }
          }
        } finally {
          releaseSandboxOwnerLock(releaseLock);
        }
        return;
      }
      if (await sandboxOwnerIsActive(owner)) return;

      await removeManagedSandbox(
        sandboxPath,
        "",
        sandboxRootIdentity,
        sandboxIdentity,
      );
    }),
  );
}

async function readSandboxOwner(sandboxPath) {
  try {
    const content = await fs.promises.readFile(path.join(sandboxPath, "owner.pid"), "utf8");
    const lines = content.split(/\r?\n/);
    const firstLine = lines[0];
    if (!/^\d+$/.test(firstLine)) return null;

    const pid = Number(firstLine);
    if (!Number.isSafeInteger(pid) || pid <= 0) return null;

    const instanceID = lines[3] ?? "";
    if (!UUID_V4_RE.test(instanceID)) return null;

    return {
      pid,
      processStartToken: lines[2] ?? "",
      instanceID,
      cleanupPending: lines[4] === "cleanup-pending",
    };
  } catch {
    return null;
  }
}

async function sandboxIsPastOwnerGracePeriod(sandboxPath) {
  try {
    const stat = await fs.promises.stat(sandboxPath);
    return Date.now() - stat.mtimeMs >= XCODE_SANDBOX_OWNER_GRACE_MS;
  } catch {
    return false;
  }
}

function processExists(pid) {
  try {
    process.kill(pid, 0);
    return true;
  } catch (error) {
    return error?.code === "EPERM";
  }
}

async function sandboxOwnerIsActive(owner) {
  if (!processExists(owner.pid)) return false;
  if (!owner.processStartToken) return true;

  const currentStartToken = await readProcessStartToken(owner.pid);
  if (!currentStartToken) return true;
  return currentStartToken === owner.processStartToken;
}

function readProcessStartToken(pid) {
  return new Promise((resolve) => {
    let settled = false;
    let timedOut = false;
    let stdout = "";
    let child;
    let timeoutTimer;
    let forceKillTimer;

    try {
      child = spawn("/bin/ps", ["-p", String(pid), "-o", "lstart="], {
        env: {
          ...process.env,
          LC_ALL: "C",
          LANG: "C",
          TZ: "UTC",
        },
        stdio: ["ignore", "pipe", "ignore"],
      });
    } catch {
      resolve("");
      return;
    }

    const onData = (chunk) => {
      const remaining = PROCESS_START_OUTPUT_MAX_CHARS - stdout.length;
      if (remaining > 0) stdout += String(chunk).slice(0, remaining);
    };
    const onError = () => finish("");
    const onClose = (code) => {
      const firstLine = stdout.trim().split(/\r?\n/, 1)[0] ?? "";
      finish(!timedOut && code === 0 ? firstLine : "");
    };

    child.stdout?.setEncoding?.("utf8");
    child.stdout?.on?.("data", onData);
    child.on("error", onError);
    child.on("close", onClose);
    timeoutTimer = setTimeout(() => {
      if (settled) return;
      timedOut = true;
      forceKillTimer = terminateChildAfterGrace(
        child,
        () => !settled,
        () => finish(""),
      );
    }, PROCESS_START_TIMEOUT_MS);

    function finish(value) {
      if (settled) return;
      settled = true;
      clearTimeout(timeoutTimer);
      clearTimeout(forceKillTimer);
      child.stdout?.removeListener?.("data", onData);
      child.removeListener?.("error", onError);
      child.removeListener?.("close", onClose);
      resolve(value);
    }
  });
}

async function removeManagedSandbox(
  sandboxPath,
  expectedInstanceID = "",
  sandboxRootIdentity = null,
  expectedSandboxIdentity = null,
) {
  const candidate = managedSandboxCandidate(sandboxPath);
  if (!candidate) return false;
  if (
    !sandboxRootIdentity ||
    !secureExistingManagedSandbox(
      candidate,
      sandboxRootIdentity,
      expectedSandboxIdentity,
    )
  ) {
    return false;
  }

  if (expectedInstanceID) {
    const owner = await readSandboxOwner(candidate);
    if (!owner || owner.instanceID !== expectedInstanceID) return false;
  }

  try {
    await fs.promises.rm(candidate, { recursive: true, force: true, maxRetries: 3, retryDelay: 100 });
    clearPendingSandboxCleanup(candidate);
    return true;
  } catch {
    // Best-effort cleanup; the next plugin instance will retry through the stale-owner sweep.
    return false;
  }
}

async function quarantineOwnedSandbox(
  sandboxPath,
  expectedInstanceID,
  sandboxRootIdentity,
  expectedSandboxIdentity,
) {
  const candidate = managedSandboxCandidate(sandboxPath);
  if (!candidate) return "";
  const sandboxIdentity = secureExistingManagedSandbox(
    candidate,
    sandboxRootIdentity,
    expectedSandboxIdentity,
  );
  if (!sandboxIdentity) return "";

  const ownerLock = acquireSandboxOwnerLock(
    candidate,
    sandboxRootIdentity,
    sandboxIdentity,
  );
  if (!ownerLock) return "";
  let releaseLock = ownerLock;

  try {
    const currentOwner = await readSandboxOwner(candidate);
    if (!currentOwner || currentOwner.instanceID !== expectedInstanceID) return "";
    if (!markSandboxCleanupPending(candidate, expectedInstanceID, ownerLock)) return "";

    const quarantinePath = path.join(path.dirname(candidate), `.quarantine-${randomUUID()}`);
    if (!managedSandboxCandidate(quarantinePath)) return "";

    try {
      fs.renameSync(candidate, quarantinePath);
      movePendingSandboxCleanup(candidate, quarantinePath);
    } catch {
      return "";
    }

    releaseLock = {
      ...ownerLock,
      path: path.join(quarantinePath, XCODE_SANDBOX_OWNER_LOCK),
      sandboxIdentity: relocatedSandboxIdentity(sandboxIdentity, quarantinePath),
    };
    if (
      !secureExistingManagedSandbox(
        quarantinePath,
        sandboxRootIdentity,
        releaseLock.sandboxIdentity,
      )
    ) {
      if (restoreQuarantinedSandbox(quarantinePath, candidate)) {
        movePendingSandboxCleanup(quarantinePath, candidate);
        releaseLock = ownerLock;
      }
      return "";
    }
    const relocatedOwner = await readSandboxOwner(quarantinePath);
    if (
      !sandboxOwnerLockIsHeld(releaseLock) ||
      !relocatedOwner ||
      relocatedOwner.instanceID !== expectedInstanceID ||
      !relocatedOwner.cleanupPending
    ) {
      if (restoreQuarantinedSandbox(quarantinePath, candidate)) {
        movePendingSandboxCleanup(quarantinePath, candidate);
        releaseLock = ownerLock;
      }
      return "";
    }

    const ownerPath = path.join(quarantinePath, "owner.pid");
    const retiredOwnerPath = path.join(quarantinePath, `owner.pid.retired-${randomUUID()}`);
    try {
      fs.renameSync(ownerPath, retiredOwnerPath);
    } catch (error) {
      if (error?.code !== "ENOENT") return quarantinePath;
    }

    return quarantinePath;
  } finally {
    releaseSandboxOwnerLock(releaseLock);
  }
}

async function quarantineManagedSandbox(
  sandboxPath,
  ownerLock,
  sandboxRootIdentity,
  expectedSandboxIdentity,
) {
  const candidate = managedSandboxCandidate(sandboxPath);
  const sandboxIdentity = candidate
    ? secureExistingManagedSandbox(
        candidate,
        sandboxRootIdentity,
        expectedSandboxIdentity,
      )
    : null;
  if (!candidate || !sandboxIdentity || !sandboxOwnerLockIsHeld(ownerLock)) {
    return { path: "", ownerLock };
  }

  const quarantinePath = path.join(path.dirname(candidate), `.quarantine-${randomUUID()}`);
  if (!managedSandboxCandidate(quarantinePath)) return { path: "", ownerLock };

  try {
    fs.renameSync(candidate, quarantinePath);
    movePendingSandboxCleanup(candidate, quarantinePath);
  } catch {
    return { path: "", ownerLock };
  }

  const relocatedLock = {
    ...ownerLock,
    path: path.join(quarantinePath, XCODE_SANDBOX_OWNER_LOCK),
    sandboxIdentity: relocatedSandboxIdentity(sandboxIdentity, quarantinePath),
  };
  if (
    !secureExistingManagedSandbox(
      quarantinePath,
      sandboxRootIdentity,
      relocatedLock.sandboxIdentity,
    )
  ) {
    if (restoreQuarantinedSandbox(quarantinePath, candidate)) {
      movePendingSandboxCleanup(quarantinePath, candidate);
      return { path: "", ownerLock };
    }
    return { path: "", ownerLock: relocatedLock };
  }
  const publishedOwner = await readSandboxOwner(quarantinePath);
  const cleanupPending =
    publishedOwner?.cleanupPending || sandboxCleanupIsPending(quarantinePath);
  if (
    !sandboxOwnerLockIsHeld(relocatedLock) ||
    (publishedOwner && !cleanupPending)
  ) {
    if (restoreQuarantinedSandbox(quarantinePath, candidate)) {
      movePendingSandboxCleanup(quarantinePath, candidate);
      return { path: "", ownerLock };
    }
    // Preserve the quarantine when the original path has already been reused.
    return { path: "", ownerLock: relocatedLock };
  }

  return { path: quarantinePath, ownerLock: relocatedLock };
}

function restoreQuarantinedSandbox(quarantinePath, originalPath) {
  try {
    fs.renameSync(quarantinePath, originalPath);
    return true;
  } catch {
    return false;
  }
}

async function detachManagedSandbox(
  sandboxPath,
  expectedInstanceID = "",
  sandboxRootIdentity = null,
  expectedSandboxIdentity = null,
) {
  const candidate = managedSandboxCandidate(sandboxPath);
  if (!candidate) return;
  if (
    !sandboxRootIdentity ||
    !secureExistingManagedSandbox(
      candidate,
      sandboxRootIdentity,
      expectedSandboxIdentity,
    )
  ) {
    return;
  }

  if (expectedInstanceID) {
    const owner = await readSandboxOwner(candidate);
    if (!owner || owner.instanceID !== expectedInstanceID) return;
  }

  try {
    const child = spawn("/bin/rm", ["-rf", candidate], {
      detached: true,
      stdio: "ignore",
    });
    child.on("error", () => {});
    child.on("exit", (code) => {
      if (code === 0) clearPendingSandboxCleanup(candidate);
    });
    child.unref();
  } catch {
    // Best-effort cleanup; the next plugin instance will retry through the stale-owner sweep.
  }
}

function managedSandboxCandidate(sandboxPath) {
  const sandboxRoot = path.resolve(os.tmpdir(), XCODE_SANDBOX_DIR);
  const candidate = path.resolve(sandboxPath);
  const relative = path.relative(sandboxRoot, candidate);
  if (!relative || relative.startsWith("..") || path.isAbsolute(relative) || relative.includes(path.sep)) return "";
  return candidate;
}

function secureExistingManagedSandbox(
  sandboxPath,
  sandboxRootIdentity,
  expectedSandboxIdentity = null,
) {
  try {
    revalidateSandboxDirectory(sandboxRootIdentity);
    const candidate = managedSandboxCandidate(sandboxPath);
    if (!candidate || path.dirname(candidate) !== sandboxRootIdentity.path) return null;

    const name = path.basename(candidate);
    if (!SAFE_ID_RE.test(name) && !XCODE_SANDBOX_QUARANTINE_RE.test(name)) {
      return null;
    }

    const current = inspectSandboxDirectory(
      candidate,
      path.join(sandboxRootIdentity.canonicalPath, name),
      sandboxRootIdentity,
    );
    if (
      expectedSandboxIdentity &&
      (current.dev !== expectedSandboxIdentity.dev ||
        current.ino !== expectedSandboxIdentity.ino ||
        current.uid !== expectedSandboxIdentity.uid)
    ) {
      return null;
    }
    return current;
  } catch {
    return null;
  }
}

function relocatedSandboxIdentity(identity, destinationPath) {
  const name = path.basename(destinationPath);
  return {
    ...identity,
    path: path.resolve(destinationPath),
    canonicalPath: path.join(identity.parent.canonicalPath, name),
  };
}

function markPendingSandboxCleanup(sandboxPath) {
  const candidate = managedSandboxCandidate(sandboxPath);
  if (candidate) pendingSandboxCleanups.add(candidate);
}

function clearPendingSandboxCleanup(sandboxPath) {
  const candidate = managedSandboxCandidate(sandboxPath);
  if (candidate) pendingSandboxCleanups.delete(candidate);
}

function movePendingSandboxCleanup(sourcePath, destinationPath) {
  const source = managedSandboxCandidate(sourcePath);
  const destination = managedSandboxCandidate(destinationPath);
  if (!source || !destination || !pendingSandboxCleanups.delete(source)) return;
  pendingSandboxCleanups.add(destination);
}

function sandboxCleanupIsPending(sandboxPath) {
  const candidate = managedSandboxCandidate(sandboxPath);
  return Boolean(candidate && pendingSandboxCleanups.has(candidate));
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
