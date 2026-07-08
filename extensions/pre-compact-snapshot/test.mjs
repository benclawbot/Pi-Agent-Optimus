// ponytail: minimal verification harness - mocks ctx, fires hooks, asserts on disk + return value
import { existsSync, readFileSync, writeFileSync, mkdtempSync, mkdirSync, readdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const ext = await import("./index.ts");

const PASS = "\x1b[32m✓\x1b[0m";
const FAIL = "\x1b[31m✗\x1b[0m";
let passed = 0;
let failed = 0;
const failures = [];

function assert(cond, msg) {
	if (cond) {
		console.log(`${PASS} ${msg}`);
		passed++;
	} else {
		console.log(`${FAIL} ${msg}`);
		failed++;
		failures.push(msg);
	}
}

// ─── Test harness ─────────────────────────────────────────────────────────────

function makeCtx({ cwd, sessionDir, branch, sessionFile, modelId = "google/gemini-2.5-flash", tokensBefore = 50000 } = {}) {
	const uiCalls = { notify: [] };
	const events = {};
	const pi = {
		on(name, handler) {
			events[name] = handler;
		},
		registerCommand() {},
	};
	const ctx = {
		cwd,
		hasUI: true,
		mode: "tui",
		model: modelId ? { provider: modelId.split("/")[0], id: modelId.split("/")[1] } : undefined,
		ui: {
			notify(msg, type, opts) {
				uiCalls.notify.push({ msg, type, opts });
			},
		},
		sessionManager: {
			getSessionId: () => "test-session-1234",
			getSessionFile: () => sessionFile,
			getSessionDir: () => sessionDir,
			getBranch: () => branch,
			getEntries: () => branch,
		},
		getContextUsage: () => ({ tokens: tokensBefore, contextWindow: 200000, percent: tokensBefore / 200000 }),
		getThinkingLevel: () => "medium",
	};
	return { pi, ctx, uiCalls, events };
}

function makeBranch() {
	const now = Date.now();
	const id = (i) => `entry-${i}`;
	return [
		{
			type: "message",
			id: id(0),
			parentId: null,
			timestamp: now - 5000,
			message: { role: "user", content: "Build a CLI todo app with persistence" },
		},
		{
			type: "message",
			id: id(1),
			parentId: id(0),
			timestamp: now - 4000,
			message: {
				role: "assistant",
				content: [
					{ type: "thinking", thinking: "Plan: scaffold, then storage, then CLI." },
					{ type: "text", text: "I'll scaffold the project first." },
					{ type: "toolCall", name: "read", input: { path: "/tmp/seed.ts" } },
					{ type: "toolCall", name: "write", input: { path: "/tmp/out.ts", content: "// new" } },
				],
			},
		},
		{
			type: "message",
			id: id(2),
			parentId: id(1),
			timestamp: now - 3000,
			message: {
				role: "assistant",
				content: [
					{ type: "text", text: "Now adding tests." },
					{ type: "toolCall", name: "edit", input: { file_path: "/tmp/out.ts", newText: "// v2" } },
				],
			},
		},
	];
}

function makeEvent({ tokensBefore = 50000 } = {}) {
	return {
		type: "session_before_compact",
		preparation: {
			firstKeptEntryId: "entry-2",
			tokensBefore,
			messagesToSummarize: [],
			turnPrefixMessages: [],
			previousSummary: undefined,
			fileOps: { readFiles: ["/tmp/seed.ts"], modifiedFiles: ["/tmp/out.ts"] },
			settings: { enabled: true, reserveTokens: 16384, keepRecentTokens: 20000 },
		},
		branchEntries: [],
		signal: new AbortController().signal,
	};
}

// ─── Tests ────────────────────────────────────────────────────────────────────

async function testSessionBeforeCompact() {
	const tmpDir = mkdtempSync(join(tmpdir(), "pcsnap-"));
	const sessionDir = join(tmpDir, "session");
	mkdirSync(sessionDir, { recursive: true });
	const branch = makeBranch();
	const { pi, ctx, uiCalls, events } = makeCtx({
		cwd: tmpDir,
		sessionDir,
		branch,
		sessionFile: join(sessionDir, "test.jsonl"),
	});
	const event = makeEvent();

	ext.default(pi);
	const handler = events["session_before_compact"];
	assert(typeof handler === "function", "extension registers session_before_compact handler");

	const result = await handler(event, ctx);
	assert(result && typeof result === "object", "handler returns a result object");
	assert(result.compaction, "result.compaction is present");

	const summary = result.compaction.summary;
	assert(summary.includes("<snapshot-ref"), "summary contains <snapshot-ref tag");
	assert(summary.includes('id="snap-'), "summary snapshot id is set");
	assert(summary.includes("tokens="), "summary includes token count");

	const details = result.compaction.details;
	assert(details && details.snapshotPath, "details.snapshotPath is set");
	assert(details.snapshotId, "details.snapshotId is set");
	assert(existsSync(details.snapshotPath), `snapshot file written to disk: ${details.snapshotPath}`);

	const snap = JSON.parse(readFileSync(details.snapshotPath, "utf8"));
	assert(snap.cwd === tmpDir, "snapshot.cwd matches ctx.cwd");
	assert(snap.tokensBefore === 50000, "snapshot.tokensBefore matches event");
	assert(snap.trigger === "before-compact", "snapshot.trigger is before-compact");
	assert(snap.model === "google/gemini-2.5-flash", "snapshot.model captured");
	assert(snap.activeGoal === "Build a CLI todo app with persistence", "snapshot.activeGoal is last user message");
	assert(snap.recentFiles.read.includes("/tmp/seed.ts"), "snapshot.recentFiles.read captures read tool calls");
	assert(snap.recentFiles.modified.includes("/tmp/out.ts"), "snapshot.recentFiles.modified captures write/edit tool calls");
	assert(snap.id === details.snapshotId, "snapshot.id matches details.snapshotId");
	assert(typeof snap.takenAt === "string", "snapshot.takenAt is ISO string");
	assert(Array.isArray(snap.openTodos), "snapshot.openTodos is an array");
	assert(Array.isArray(snap.projectConventions), "snapshot.projectConventions is an array");

	const notify = uiCalls.notify.find((n) => n.msg.startsWith("Snapshot "));
	assert(notify && notify.type === "info", "ui.notify called with info on snapshot");
}

async function testSessionStartResume() {
	const tmpDir = mkdtempSync(join(tmpdir(), "pcsnap-"));
	const sessionDir = join(tmpDir, "session");
	mkdirSync(sessionDir, { recursive: true });
	const snapPath = join(sessionDir, "snap-test.json");
	writeFileSync(snapPath, JSON.stringify({
		id: "snap-test",
		takenAt: new Date().toISOString(),
		cwd: tmpDir,
		trigger: "before-compact",
		model: "google/gemini-2.5-flash",
		tokensBefore: 99999,
		recentFiles: { read: [], modified: [] },
		openTodos: [],
		projectConventions: [],
	}));

	const branch = [
		{
			type: "compaction",
			id: "cmp-1",
			parentId: null,
			timestamp: Date.now(),
			summary: "x",
			firstKeptEntryId: "e1",
			tokensBefore: 99999,
			details: {
				snapshotPath: snapPath,
				snapshotId: "snap-test",
				takenAt: new Date().toISOString(),
				model: "google/gemini-2.5-flash",
				tokensBefore: 99999,
			},
		},
	];

	const { pi, ctx, uiCalls, events } = makeCtx({
		cwd: tmpDir,
		sessionDir,
		branch,
		sessionFile: join(sessionDir, "test.jsonl"),
	});

	ext.default(pi);
	const handler = events["session_start"];
	assert(typeof handler === "function", "extension registers session_start handler");

	// Test reload: should notify
	const uiCallsBefore = uiCalls.notify.length;
	await handler({ type: "session_start", reason: "reload" }, ctx);
	const reloadNotifies = uiCalls.notify.slice(uiCallsBefore);
	const resumeNotify = reloadNotifies.find((n) => n.msg.includes("Resumed with snapshot"));
	assert(resumeNotify, "session_start on reload notifies about recovered snapshot");
	assert(resumeNotify.msg.includes("snap-test"), "resume notify includes snapshot id");

	// Test startup with empty branch (no snapshot to recover): should NOT notify
	const uiCallsBeforeStartup = uiCalls.notify.length;
	await handler({ type: "session_start", reason: "startup" }, { ...ctx, sessionManager: { ...ctx.sessionManager, getEntries: () => [] } });
	const newNotifies = uiCalls.notify.slice(uiCallsBeforeStartup);
	const startupResume = newNotifies.find((n) => n.msg.includes("Resumed with snapshot"));
	assert(!startupResume, "session_start on startup with no snapshot does NOT fire resume notify");
}

async function testManualSnapshotCommand() {
	const tmpDir = mkdtempSync(join(tmpdir(), "pcsnap-"));
	const sessionDir = join(tmpDir, "session");
	mkdirSync(sessionDir, { recursive: true });
	const branch = makeBranch();
	const { pi, ctx, uiCalls } = makeCtx({
		cwd: tmpDir,
		sessionDir,
		branch,
		sessionFile: join(sessionDir, "test.jsonl"),
		tokensBefore: 12345,
	});

	let commandHandler;
	pi.registerCommand = (name, def) => {
		if (name === "snapshot") commandHandler = def.handler;
	};
	ext.default(pi);

	await commandHandler("", ctx);
	const notify = uiCalls.notify.find((n) => n.msg.includes("Manual snapshot"));
	assert(notify, "/snapshot command fires ui.notify with manual snapshot message");
	if (notify) {
		const tok = (12345).toLocaleString();
		assert(
			notify.msg.includes(`${tok} tok`) || notify.msg.includes("12345 tok"),
			`manual snapshot notify includes token count (msg: ${notify.msg.slice(0, 80)}...)`,
		);
	}
}

async function testPruning() {
	const tmpDir = mkdtempSync(join(tmpdir(), "pcsnap-"));
	const sessionDir = join(tmpDir, "session");
	mkdirSync(sessionDir, { recursive: true });
	const branch = makeBranch();

	const { pi, ctx, events } = makeCtx({ cwd: tmpDir, sessionDir, branch, sessionFile: join(sessionDir, "test.jsonl") });
	ext.default(pi);
	const handler = events["session_before_compact"];

	for (let i = 0; i < 8; i++) {
		await handler(makeEvent({ tokensBefore: 1000 * (i + 1) }), ctx);
	}

	const dir = join(sessionDir, "snapshots");
	const remaining = readdirSync(dir).filter((f) => f.endsWith(".json"));
	assert(remaining.length === 5, `prune keeps exactly 5 snapshots (got ${remaining.length})`);
}

// ─── Run ──────────────────────────────────────────────────────────────────────

console.log("\n=== pre-compact-snapshot tests ===\n");
try {
	await testSessionBeforeCompact();
	await testSessionStartResume();
	await testManualSnapshotCommand();
	await testPruning();
} catch (err) {
	console.error("\nFATAL:", err);
	process.exit(1);
}

console.log(`\n${passed} passed, ${failed} failed`);
if (failed > 0) {
	console.log("\nFailures:");
	for (const m of failures) console.log(`  - ${m}`);
}
process.exit(failed > 0 ? 1 : 0);