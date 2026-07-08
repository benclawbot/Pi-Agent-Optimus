// End-to-end: spawn pi in RPC mode, send a prompt, send compact, verify snapshot on disk
import { spawn } from "node:child_process";
import { existsSync, readFileSync, rmSync, mkdirSync, readdirSync } from "node:fs";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const tmpDir = mkdtempSync(join(tmpdir(), "pcsnap-e2e-"));
process.chdir(tmpDir);
console.log("Workdir:", tmpDir);

const extPath = "C:/Users/thoma/.pi/agent/extensions/pre-compact-snapshot/index.ts";
const proc = spawn(
	"pi",
	["--mode", "rpc", "--no-session", "-e", extPath, "--provider", "google", "--model", "gemini-2.5-flash"],
	{ stdio: ["pipe", "pipe", "pipe"] },
);

const events = [];
let compactResponse = null;
let buffer = "";
proc.stdout.on("data", (chunk) => {
	buffer += chunk.toString("utf8");
	const lines = buffer.split("\n");
	buffer = lines.pop() ?? "";
	for (const line of lines) {
		if (!line.trim()) continue;
		try {
			const obj = JSON.parse(line);
			events.push(obj);
			if (obj.type === "response" && obj.command === "compact") compactResponse = obj;
		} catch (e) {
			console.log("RAW:", line);
		}
	}
});
proc.stderr.on("data", (chunk) => {
	console.log("STDERR:", chunk.toString("utf8").trim());
});

function send(obj) {
	proc.stdin.write(JSON.stringify(obj) + "\n");
}

function wait(ms) {
	return new Promise((r) => setTimeout(r, ms));
}

async function waitFor(predicate, timeoutMs = 5000) {
	const start = Date.now();
	while (Date.now() - start < timeoutMs) {
		if (predicate()) return true;
		await wait(50);
	}
	return false;
}

(async () => {
	// Wait for pi to be ready (it emits initial events)
	await wait(800);

	// Send a prompt
	send({ id: "p1", type: "prompt", message: "Hello" });

	// Wait a bit for prompt to be accepted
	await wait(500);

	// Manually trigger compaction
	console.log("Sending compact command...");
	send({ id: "c1", type: "compact" });

	const ok = await waitFor(() => compactResponse !== null, 5000);
	if (!ok) {
		console.error("FAIL: no compact response received");
		console.error("Events seen:", events.map((e) => e.type).join(", "));
		proc.kill();
		process.exit(1);
	}

	console.log("Compact response:", JSON.stringify(compactResponse, null, 2));

	// Look for the snapshot directory
	await wait(300);
	const fallbackDir = join(tmpDir, ".pre-compact-snapshots");
	console.log("Checking fallback dir:", fallbackDir);

	if (!existsSync(fallbackDir)) {
		console.error("FAIL: snapshot dir was not created at", fallbackDir);
		proc.kill();
		process.exit(1);
	}

	const files = readdirSync(fallbackDir).filter((f) => f.endsWith(".json"));
	if (files.length === 0) {
		console.error("FAIL: no snapshot files written");
		proc.kill();
		process.exit(1);
	}

	const snapPath = join(fallbackDir, files[0]);
	const snap = JSON.parse(readFileSync(snapPath, "utf8"));
	console.log("Snapshot content (first 500 chars):", JSON.stringify(snap, null, 2).slice(0, 500));

	const checks = [
		[snap.id && snap.id.startsWith("snap-"), "snapshot.id starts with snap-"],
		[!!snap.takenAt, "snapshot.takenAt set"],
		[!!snap.cwd, "snapshot.cwd set"],
		[snap.trigger === "before-compact", "snapshot.trigger === 'before-compact'"],
		[Array.isArray(snap.recentFiles?.read), "snapshot.recentFiles.read is array"],
		[Array.isArray(snap.recentFiles?.modified), "snapshot.recentFiles.modified is array"],
		[Array.isArray(snap.openTodos), "snapshot.openTodos is array"],
		[Array.isArray(snap.projectConventions), "snapshot.projectConventions is array"],
	];

	let allPass = true;
	for (const [cond, msg] of checks) {
		console.log(cond ? `\x1b[32m✓\x1b[0m ${msg}` : `\x1b[31m✗\x1b[0m ${msg}`);
		if (!cond) allPass = false;
	}

	proc.kill();
	process.exit(allPass ? 0 : 1);
})();