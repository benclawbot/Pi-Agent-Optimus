---
name: pi-extension-build
description: Build a pi coding-agent extension in TypeScript with verified hooks. Use when asked to "build a pi extension", "write a pi extension", "create a pi hook", "extend pi", "add a slash command to pi", "subscribe to pi lifecycle events". Covers extension API, auto-discovery, three-layer verification (typecheck → mocked tests → real RPC e2e), and common gotchas.
---

# Build a pi Extension

Write a TypeScript module that hooks into the pi coding agent's lifecycle, then verify it fires on real events before declaring done.

## Step 1: Find the Hook

Map user intent to a pi lifecycle event. Read the installed types — they're authoritative:

```bash
grep -n "interface.*Event\|registerCommand\|registerTool\|ExtensionAPI" \
  "$PI_HOME/node_modules/@earendil-works/pi-coding-agent/dist/core/extensions/types.d.ts"
```

Common hook choices:

| User wants | Use |
|------------|-----|
| Snapshot/transform context before compaction | `session_before_compact` |
| React to session load/resume/fork | `session_start` (check `event.reason`) |
| Add `/mycommand` | `registerCommand("mycommand", ...)` |
| Give the LLM a new tool | `registerTool({ name, parameters, execute })` |
| Block/modify tool calls | `tool_call` (return `{ block: true, reason }`) |
| Inject context into system prompt | `before_agent_start` |

Read the event type and its `Result` companion — return shape is precise. Example for `session_before_compact`:

```ts
pi.on("session_before_compact", async (event, ctx) => {
  // event.preparation: { tokensBefore, firstKeptEntryId, messagesToSummarize, ... }
  // return either { cancel: true } OR { compaction: { summary, firstKeptEntryId, tokensBefore, details } }
});
```

## Step 2: Place the File

Auto-discovery rules (pi loader walks `~/.pi/agent/extensions/`):

1. `extensions/foo.ts` → load as `foo`
2. `extensions/foo/index.ts` → load as `foo`
3. `extensions/foo/package.json` with `"pi"` field → load declared files

Use option 2 when the extension has multiple files (extension + tests + assets). Directory layout:

```
~/.pi/agent/extensions/<name>/
├── index.ts        # default export: (pi: ExtensionAPI) => void
└── test.mjs        # optional: mocked unit tests
```

## Step 3: Write the Extension

Minimal skeleton:

```ts
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export default function (pi: ExtensionAPI) {
  pi.on("session_start", async (event, ctx) => {
    if (event.reason !== "reload") return; // narrow to fires you care about
    ctx.ui.notify("Loaded!", "info");
  });

  pi.registerCommand("mycommand", {
    description: "Does a thing",
    handler: async (args, ctx) => {
      ctx.ui.notify(`got: ${args}`, "info");
    },
  });
}
```

`ctx` shape (ExtensionContext) — memorize these:

- `ctx.cwd`, `ctx.hasUI`, `ctx.mode` (`"tui" | "rpc" | "json" | "print"`)
- `ctx.model` — `{ provider, id }` or undefined
- `ctx.sessionManager` — `getBranch()`, `getEntries()`, `getSessionFile()`, `getSessionDir()`
- `ctx.ui` — `notify(msg, type)`, `editor(title, prefill)`, `select/confirm/input/custom(...)`
- `ctx.getContextUsage()`, `ctx.getThinkingLevel()`, `ctx.compact()`, `ctx.getSystemPrompt()`
- `ctx.abort()`, `ctx.shutdown()`, `ctx.signal` (AbortSignal during streaming)

ExtensionAPI surface:
- `pi.on(eventName, handler)` — see Step 1 table
- `pi.registerCommand(name, { description, handler })`
- `pi.registerTool({ name, label, description, parameters, execute })` — parameters is a TypeBox schema
- `pi.registerShortcut(keyId, { description, handler })`
- `pi.registerFlag(name, { description, type, default })`
- `pi.sendMessage(...)`, `pi.sendUserMessage(...)`, `pi.appendEntry(customType, data)`

TypeBox import: `import { Type } from "typebox"`.

## Step 4: Verify — Three Layers

Never skip layers. The mocked test proves the handler runs; the e2e proves pi calls it.

### Layer 1: Type-check

```bash
bun build --target=bun --no-bundle --typecheck \
  ~/.pi/agent/extensions/<name>/index.ts \
  --outfile=/tmp/check.js
```

Must exit clean. Type errors in `index.ts` mean pi will crash at extension load.

### Layer 2: Mocked Unit Test

Bun loads TS directly. Mock `ctx` with the fields your handler reads, fire the event, assert:

```js
// ~/.pi/agent/extensions/<name>/test.mjs
import { existsSync, readFileSync, mkdtempSync, mkdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const ext = await import("./index.ts");

function makeCtx({ cwd, branch = [], modelId }) {
  const uiCalls = { notify: [] };
  const events = {};
  const pi = {
    on(name, handler) { events[name] = handler; },
    registerCommand() {},
  };
  const ctx = {
    cwd, hasUI: true, mode: "tui",
    model: modelId ? { provider: modelId.split("/")[0], id: modelId.split("/")[1] } : undefined,
    ui: { notify: (msg, type) => uiCalls.notify.push({ msg, type }) },
    sessionManager: {
      getBranch: () => branch, getEntries: () => branch,
      getSessionFile: () => undefined, getSessionDir: () => undefined, getSessionId: () => "test",
    },
    getContextUsage: () => ({ tokens: 50000, contextWindow: 200000, percent: 0.25 }),
    getThinkingLevel: () => "medium",
  };
  return { pi, ctx, uiCalls, events };
}

const { pi, ctx, uiCalls, events } = makeCtx({ cwd: "/tmp", branch: [], modelId: "google/gemini-2.5-flash" });
ext.default(pi);

const handler = events["session_start"];
if (typeof handler !== "function") throw new Error("hook not registered");

await handler({ type: "session_start", reason: "reload" }, ctx);
// assertions on uiCalls, file system, return value
```

Run: `bun test.mjs`. Aim for 20+ assertions covering: hook registration, branch walking, file writes, return values, notify text.

### Layer 3: Real pi E2E via RPC

Spawn `pi --mode rpc`, send the actual command, check disk. Use RPC because it has explicit `compact`, `set_auto_compaction`, etc. — TUI hides whether the hook fired.

```js
// e2e-test.mjs
import { spawn } from "node:child_process";
import { mkdtempSync, mkdirSync, readdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const tmpDir = mkdtempSync(join(tmpdir(), "ext-e2e-"));
process.chdir(tmpDir);

const extPath = "/absolute/path/to/index.ts"; // don't use relative — chdir changes cwd
const proc = spawn("pi", [
  "--mode", "rpc", "--no-session",
  "-e", extPath,
  "--provider", "google", "--model", "gemini-2.5-flash",
], { stdio: ["pipe", "pipe", "pipe"] });

const events = [];
let resp = null;
let buf = "";
proc.stdout.on("data", (c) => {
  buf += c.toString();
  const lines = buf.split("\n");
  buf = lines.pop() ?? "";
  for (const line of lines) {
    if (!line.trim()) continue;
    try {
      const obj = JSON.parse(line);
      events.push(obj);
      if (obj.type === "response" && obj.command === "compact") resp = obj;
    } catch {}
  }
});

const wait = (ms) => new Promise((r) => setTimeout(r, ms));
await wait(800);
proc.stdin.write(JSON.stringify({ id: "c1", type: "compact" }) + "\n");

const ok = await (async () => {
  for (let i = 0; i < 100; i++) { if (resp) return true; await wait(50); }
  return false;
})();

if (!ok) { console.error("no response", events.map(e => e.type)); proc.kill(); process.exit(1); }
console.log("response:", JSON.stringify(resp.data, null, 2));
proc.kill();
```

Run: `bun e2e-test.mjs`. Verify the snapshot file the extension wrote exists, has the expected shape, and the response includes whatever data the extension returned.

### Layer 3b: Auto-Discovery Check

Re-run layer 3 WITHOUT the `-e` flag. If the extension lives at `~/.pi/agent/extensions/<name>/index.ts`, pi picks it up automatically:

```bash
pi --mode rpc --no-session --provider google --model gemini-2.5-flash \
  < <(sleep 1; echo '{"id":"c1","type":"compact"}'; sleep 2) \
  | grep snapshot
```

If no output → discovery is broken. Common cause: file in subdir without `index.ts`.

## Step 5: Common Gotchas

| Symptom | Cause | Fix |
|---------|-------|-----|
| Hook fires but summary appears twice | Helper prepends tag, then caller prepends again | Remove manual prepend; let one helper own it |
| `pi.list` doesn't show your extension | That command lists packages, not local extensions | Auto-discovery still works; check via real run |
| `ctx.model` is undefined | No model selected yet (startup phase) | Guard: `if (!ctx.model) return` |
| `ctx.ui.editor` returns `undefined` | User cancelled | Treat as no-op, not error |
| Test pass but TUI doesn't fire hook | Extension file in wrong location or wrong name | Run layer 3b |
| `signal` is undefined | Not currently streaming | Guard: `ctx.signal?.aborted` |
| Compaction hook returns summary but it's ignored | Returned without `details` | Set `details` for any structured recovery data |

## Step 6: Done Criteria

All four must hold:

- [ ] Layer 1 typecheck: clean exit
- [ ] Layer 2 unit tests: 20+ assertions, all green
- [ ] Layer 3 e2e: real `pi --mode rpc` invocation produces expected file/state
- [ ] Layer 3b auto-discovery: same e2e without `-e` flag also passes

Then `ctx.ui.notify` success message appears, snapshot/file exists on disk, and pi doesn't crash on `/reload`. Ship.

## Reference Pointers

- Compaction event surface: `dist/core/extensions/types.d.ts` lines ~425-475
- ExtensionContext fields: lines ~208-245
- CompactionPreparation shape: `dist/core/compaction/compaction.d.ts` line ~95
- Worked example (custom compaction): `dist/examples/extensions/custom-compaction.ts`
- Discovery rules: `dist/core/extensions/loader.js` line ~400