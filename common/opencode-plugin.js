import { spawn } from "node:child_process";
import { createHash, randomUUID } from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SAFE_ID_RE = /^[A-Za-z0-9_-]+$/;
const MCP_PLACEHOLDER_RE = /\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}/g;
const UUID_V4_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const PROCESS_START_OUTPUT_MAX_CHARS = 256;
const PROCESS_START_TIMEOUT_MS = 5_000;
const XCODE_MCP_CACHE_TTL_MS = 30_000;
const XCODE_SANDBOX_DIR = "opencode-xcodebuildtools-sandbox";
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
    const mcpContext = {
      pluginRoot,
      projectDir: input?.worktree || input?.directory,
    };
    const state = {
      pluginJson: null,
      infoJson: null,
      config: null,
      instanceID: randomUUID(),
      processStartToken: null,
      deniedOnce: new Set(),
      xcodeMcpCache: new Map(),
      xcodeMcpApprovalSessions: new Set(),
      ownedSandboxes: new Map(),
      deletedSandboxSessions: new Set(),
      sandboxSweepDone: false,
      disposed: false,
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
    if (translated) config.mcp[name] = translated;
  }
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
  if (isObject(environment)) translated.environment = expandMcpRecord(environment, context);

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
    return command.some((part) => {
      if (typeof part !== "string") return false;
      return part
        .trim()
        .split(/\s+/)
        .some((token) => path.basename(token.replace(/^['"]|['"]$/g, "")) === "mcpbridge");
    });
  });
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

async function configureShellEnvironment(pluginRoot, state, input, output) {
  if (!isObject(output.env)) output.env = {};

  const binDir = path.join(pluginRoot, "bin");
  if (fs.existsSync(binDir)) {
    output.env.PATH = prependPath(binDir, output.env.PATH ?? process.env.PATH ?? "");
  }

  if (state.pluginJson.name !== "XcodeBuildTools") return;

  const sessionID = safeSessionID(input.sessionID ?? input.cwd ?? "default");
  if (state.disposed || state.deletedSandboxSessions.has(sessionID)) return;
  const sandboxRoot = path.join(os.tmpdir(), XCODE_SANDBOX_DIR);
  // Plugin instances never reuse a sandbox path, so an older instance cannot
  // delete a replacement instance's active sandbox after an ownership check.
  const sandboxBase = path.join(sandboxRoot, `${sessionID}-${state.instanceID}`);
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

  fs.mkdirSync(buildDir, { recursive: true });
  fs.mkdirSync(packagesDir, { recursive: true });
  writeSandboxOwner(sandboxBase, state.processStartToken, state.instanceID);

  output.env.SANDBOX_DERIVED_DATA = buildDir;
  output.env.SANDBOX_PACKAGES = packagesDir;
}

function sandboxSetupIsCancelled(state, sessionID, sandboxBase) {
  return (
    state.disposed ||
    state.deletedSandboxSessions.has(sessionID) ||
    state.ownedSandboxes.get(sessionID) !== sandboxBase
  );
}

function writeSandboxOwner(sandboxBase, processStartToken, instanceID) {
  const ownerPath = path.join(sandboxBase, "owner.pid");
  const temporaryPath = path.join(sandboxBase, `owner.pid.${instanceID}.tmp`);
  const content = `${process.pid}\n${process.argv[0] ?? "opencode"}\n${processStartToken}\n${instanceID}\n`;
  const ownerLock = acquireSandboxOwnerLock(sandboxBase);
  if (!ownerLock) throw new Error("Sandbox owner is being updated or removed");

  try {
    fs.writeFileSync(temporaryPath, content, "utf8");
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
    fs.writeFileSync(temporaryPath, content, "utf8");
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

function acquireSandboxOwnerLock(sandboxBase) {
  const lockPath = path.join(sandboxBase, XCODE_SANDBOX_OWNER_LOCK);
  const token = randomUUID();
  const createdLock = createSandboxOwnerLock(lockPath, token);
  if (createdLock) return createdLock;

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

  return createSandboxOwnerLock(lockPath, token);
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

  markPendingSandboxCleanup(sandboxPath);
  state.ownedSandboxes.delete(sessionID);
  const quarantinedPath = await quarantineOwnedSandbox(sandboxPath, state.instanceID);
  await removeManagedSandbox(
    quarantinedPath || sandboxPath,
    quarantinedPath ? "" : state.instanceID,
  );
}

async function detachOwnedSandboxes(state) {
  state.disposed = true;
  const sandboxPaths = [...new Set(state.ownedSandboxes.values())];
  for (const sandboxPath of sandboxPaths) markPendingSandboxCleanup(sandboxPath);
  state.ownedSandboxes.clear();
  state.xcodeMcpCache.clear();
  state.xcodeMcpApprovalSessions.clear();
  const cleanupTargets = await Promise.all(
    sandboxPaths.map(async (sandboxPath) => {
      const quarantinedPath = await quarantineOwnedSandbox(sandboxPath, state.instanceID);
      return {
        path: quarantinedPath || sandboxPath,
        expectedInstanceID: quarantinedPath ? "" : state.instanceID,
      };
    }),
  );
  await Promise.all(
    cleanupTargets.map(({ path: sandboxPath, expectedInstanceID }) =>
      detachManagedSandbox(sandboxPath, expectedInstanceID),
    ),
  );
}

async function sweepStaleSandboxes(sandboxRoot) {
  let entries;
  try {
    entries = await fs.promises.readdir(sandboxRoot, { withFileTypes: true });
  } catch {
    return;
  }

  await Promise.all(
    entries.map(async (entry) => {
      const isQuarantine = XCODE_SANDBOX_QUARANTINE_RE.test(entry.name);
      if (!entry.isDirectory() || (!SAFE_ID_RE.test(entry.name) && !isQuarantine)) return;

      const sandboxPath = path.join(sandboxRoot, entry.name);
      const owner = await readSandboxOwner(sandboxPath);
      const cleanupPending = owner?.cleanupPending || sandboxCleanupIsPending(sandboxPath);
      if (!owner || cleanupPending) {
        if (!cleanupPending && !isQuarantine && !(await sandboxIsPastOwnerGracePeriod(sandboxPath))) {
          return;
        }

        const ownerLock = acquireSandboxOwnerLock(sandboxPath);
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
            const quarantined = await quarantineManagedSandbox(sandboxPath, ownerLock);
            releaseLock = quarantined.ownerLock;
            if (quarantined.path) {
              await removeManagedSandbox(quarantined.path);
            }
          }
        } finally {
          releaseSandboxOwnerLock(releaseLock);
        }
        return;
      }
      if (await sandboxOwnerIsActive(owner)) return;

      await removeManagedSandbox(sandboxPath);
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
    let stdout = "";
    let child;
    let timer;

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

    child.stdout?.setEncoding?.("utf8");
    child.stdout?.on?.("data", (chunk) => {
      const remaining = PROCESS_START_OUTPUT_MAX_CHARS - stdout.length;
      if (remaining > 0) stdout += String(chunk).slice(0, remaining);
    });
    child.on("error", () => finish(""));
    child.on("close", (code) => {
      const firstLine = stdout.trim().split(/\r?\n/, 1)[0] ?? "";
      finish(code === 0 ? firstLine : "");
    });
    timer = setTimeout(() => {
      try {
        child.kill?.("SIGTERM");
      } catch {
        // Resolving the hook is more important than terminating a broken ps shim.
      }
      finish("");
    }, PROCESS_START_TIMEOUT_MS);

    function finish(value) {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(value);
    }
  });
}

async function removeManagedSandbox(sandboxPath, expectedInstanceID = "") {
  const candidate = managedSandboxCandidate(sandboxPath);
  if (!candidate) return false;

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

async function quarantineOwnedSandbox(sandboxPath, expectedInstanceID) {
  const candidate = managedSandboxCandidate(sandboxPath);
  if (!candidate) return "";

  const ownerLock = acquireSandboxOwnerLock(candidate);
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
    };
    const relocatedOwner = await readSandboxOwner(quarantinePath);
    if (
      !sandboxOwnerLockIsHeld(releaseLock) ||
      !relocatedOwner ||
      relocatedOwner.instanceID !== expectedInstanceID ||
      !relocatedOwner.cleanupPending
    ) {
      if (restoreQuarantinedSandbox(quarantinePath, candidate)) {
        movePendingSandboxCleanup(quarantinePath, candidate);
        releaseLock = { ...releaseLock, path: ownerLock.path };
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

async function quarantineManagedSandbox(sandboxPath, ownerLock) {
  const candidate = managedSandboxCandidate(sandboxPath);
  if (!candidate || !sandboxOwnerLockIsHeld(ownerLock)) {
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
  };
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

async function detachManagedSandbox(sandboxPath, expectedInstanceID = "") {
  const candidate = managedSandboxCandidate(sandboxPath);
  if (!candidate) return;

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
