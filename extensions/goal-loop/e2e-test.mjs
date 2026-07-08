/**
 * E2E for goal-loop. Verifies:
 *   1. Extension loads clean (no init errors).
 *   2. The existing /goal extension still loads and runs (no breakage).
 *   3. The goal-loop extension registers no slash commands (no name collision).
 *   4. No command conflict — the existing /goal is the only /goal.
 *   5. goal.json (the user's real one) is unchanged after a round-trip.
 *
 * Full judge-driven loop end-to-end (judge + sendUserMessage) requires
 * real LLM calls and is left as a manual smoke test.
 */

import { spawn } from "node:child_process";
import { mkdtempSync, readFileSync, existsSync, rmSync, mkdirSync } from "node:fs";
import { tmpdir, homedir } from "node:os";
import { join } from "node:path";

const workDir = mkdtempSync(join(tmpdir(), "goal-loop-e2e-"));
mkdirSync(workDir, { recursive: true });

const extPath = join(homedir(), ".pi", "agent", "extensions", "goal-loop", "index.ts");

const proc = spawn("pi", [
	"--mode", "rpc",
	"--no-session",
	"-e", extPath,
	"--provider", "minimax",
	"--model", "MiniMax/M2.5",
], { stdio: ["pipe", "pipe", "pipe"] });

let stderrBuf = "";
proc.stderr.on("data", (c) => { stderrBuf += c.toString(); });

const events = [];
let buf = "";
proc.stdout.on("data", (c) => {
	buf += c.toString();
	const lines = buf.split("\n");
	buf = lines.pop() ?? "";
	for (const line of lines) {
		if (!line.trim()) continue;
		try { events.push(JSON.parse(line)); } catch {}
	}
});

const wait = (ms) => new Promise((r) => setTimeout(r, ms));
let nextId = 1;
function send(obj) {
	const id = nextId++;
	proc.stdin.write(JSON.stringify({ id, ...obj }) + "\n");
	return id;
}
function waitForResponse(id, timeoutMs = 10_000) {
	return new Promise((resolve, reject) => {
		const deadline = Date.now() + timeoutMs;
		const tick = () => {
			const found = events.find((e) => e.type === "response" && e.id === id);
			if (found) return resolve(found);
			if (Date.now() > deadline) return reject(new Error(`timeout waiting for response id=${id}; events: ${events.map((e) => e.type).join(",")}`));
			setTimeout(tick, 50);
		};
		tick();
	});
}

let failed = 0;
function assert(cond, msg) {
	if (!cond) { failed += 1; console.error(`✗ ${msg}`); }
	else console.log(`✓ ${msg}`);
}

// Capture the user's real goal.json before the test so we can verify no mutation.
const realGoalFile = join(homedir(), ".pi", "agent", "goal.json");
const goalBefore = existsSync(realGoalFile) ? readFileSync(realGoalFile, "utf8") : null;

try {
	await wait(2000);

	// 1. clean startup — the only stderr should be goal-loop's own warning
	//    when judge is unconfigured. Nothing else.
	const extErr = events.filter((e) => e.type === "extension_error");
	assert(extErr.length === 0, `no extension_error events (got ${extErr.length}; stderr tail: ${stderrBuf.slice(-200)})`);

	const loadedMarker = stderrBuf.includes("goal-loop") || events.some((e) => e.type === "extension_loaded");
	assert(loadedMarker, `goal-loop extension loaded (stderr includes 'goal-loop' or extension_loaded event present)`);

	// 2. get_commands — the existing /goal should be present, my extension
	//    registers no slash commands (no collision).
	const cmdsResp = await waitForResponse(send({ type: "get_commands" }));
	const cmds = cmdsResp.data?.commands ?? [];
	const cmdNames = cmds.map((c) => c.name);
	const goalCount = cmdNames.filter((n) => n === "goal").length;
	assert(goalCount === 1, `exactly one /goal command (got ${goalCount}: ${cmdNames.filter((n) => n === "goal" || n.startsWith("goal")).join(", ")})`);

	// 3. /goal still works
	const goalResp = await waitForResponse(send({ type: "prompt", message: "/goal" }));
	assert(goalResp.success === true, `/goal (status only) responded success`);
	const goalNotif = events.find((e) => e.type === "extension_ui_request" && (e.message || "").includes("Goal:"));
	assert(goalNotif !== undefined, `/goal emitted a notification with the current goal`);

	// 4. extension added no command — its surface area is just the turn_end hook.
	//    Look for any command whose sourceInfo.path points at goal-loop.
	const goalLoopCmds = cmds.filter((c) => (c.sourceInfo?.path ?? "").includes("goal-loop"));
	assert(goalLoopCmds.length === 0, `goal-loop registers no slash commands (got ${goalLoopCmds.length})`);

	// 5. goal.json was NOT mutated by extension load.
	const goalAfter = existsSync(realGoalFile) ? readFileSync(realGoalFile, "utf8") : null;
	assert(goalAfter === goalBefore, `~/.pi/agent/goal.json unchanged after extension load + /goal invocation`);
} catch (err) {
	console.error("e2e threw:", err.message);
	console.error("stderr tail:", stderrBuf.slice(-500));
	console.error("events tail:", events.slice(-5).map((e) => JSON.stringify(e).slice(0, 200)).join("\n"));
	failed += 1;
} finally {
	proc.kill();
	await wait(200);
	try { rmSync(workDir, { recursive: true, force: true }); } catch {}
}

if (failed > 0) {
	console.error(`\n${failed} e2e assertion(s) failed`);
	process.exit(1);
}
console.log("\nE2E passed.");
