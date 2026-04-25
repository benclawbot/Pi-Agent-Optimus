/**
 * Session Notes Extension
 *
 * Automatically summarizes the session at the end and saves to a notes file.
 * Creates session summaries with: date, duration, tasks done, files changed.
 *
 * Usage:
 *   Add "+extensions/session-notes/index.ts" to settings.json extensions array
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { existsSync, readFileSync, appendFileSync, mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import os from "node:os";

interface SessionSummary {
	startTime: Date;
	endTime: Date;
	tasks: string[];
	filesChanged: string[];
	commits: number;
	errors: string[];
	notes: string;
}

function getSessionNotesDir(): string {
	return path.join(os.homedir(), ".pi", "sessions", "notes");
}

function ensureNotesDir(): void {
	const dir = getSessionNotesDir();
	if (!existsSync(dir)) {
		mkdirSync(dir, { recursive: true });
	}
}

function formatDate(date: Date): string {
	return date.toISOString().split("T")[0];
}

function formatDuration(start: Date, end: Date): string {
	const ms = end.getTime() - start.getTime();
	const minutes = Math.floor(ms / 60000);
	if (minutes < 1) return "<1 min";
	if (minutes < 60) return `${minutes} min`;
	const hours = Math.floor(minutes / 60);
	const remainingMins = minutes % 60;
	return `${hours}h ${remainingMins}m`;
}

async function getFilesChanged(cwd: string): Promise<string[]> {
	const { exec } = await import("node:child_process");
	const { promisify } = await import("node:util");
	const execAsync = promisify(exec);

	try {
		const { stdout } = await execAsync("git diff --name-only HEAD 2>/dev/null || git status --porcelain", { cwd, encoding: "utf8" });
		return stdout.split("\n").map(f => f.trim()).filter(Boolean);
	} catch {
		return [];
	}
}

async function getCommitCount(cwd: string): Promise<number> {
	const { exec } = await import("node:child_process");
	const { promisify } = await import("node:util");
	const execAsync = promisify(exec);

	try {
		const { stdout } = await execAsync("git log --oneline HEAD...HEAD~10 2>/dev/null | wc -l || echo 0", { cwd, encoding: "utf8" });
		return parseInt(stdout.trim(), 10) || 0;
	} catch {
		return 0;
	}
}

function formatSessionSummary(summary: SessionSummary): string {
	const date = formatDate(summary.startTime);
	const duration = formatDuration(summary.startTime, summary.endTime);

	const lines: string[] = [
		`# Session Notes - ${date}`,
		"",
		`**Time:** ${summary.startTime.toLocaleTimeString()} - ${summary.endTime.toLocaleTimeString()} (${duration})`,
	];

	if (summary.tasks.length > 0) {
		lines.push("", "## Tasks");
		summary.tasks.forEach(task => {
			lines.push(`- ${task}`);
		});
	}

	if (summary.filesChanged.length > 0) {
		lines.push("", "## Files Changed");
		summary.filesChanged.forEach(file => {
			lines.push(`- ${file}`);
		});
	}

	if (summary.commits > 0) {
		lines.push("", `**Commits:** ${summary.commits}`);
	}

	if (summary.notes) {
		lines.push("", "## Notes");
		lines.push(summary.notes);
	}

	if (summary.errors.length > 0) {
		lines.push("", "## Errors");
		summary.errors.forEach(err => {
			lines.push(`- ${err}`);
		});
	}

	lines.push("", "---");
	return lines.join("\n");
}

export default function sessionNotesExtension(pi: ExtensionAPI) {
	const sessionStart = new Date();
	const errors: string[] = [];
	const tasks: string[] = [];

	// Track task completions from tool results
	pi.on("tool_result", async (event, ctx) => {
		const result = event?.result as any;
		if (!result?.content?.[0]?.text) return;

		const text = result.content[0].text;
		// Detect task completion signals
		if (text.includes("✓") || text.includes("completed") || text.includes("Created") || text.includes("Updated")) {
			// Extract a brief summary from the text
			const firstLine = text.split("\n")[0].trim();
			if (firstLine.length > 0 && firstLine.length < 100) {
				tasks.push(firstLine);
			}
		}
	});

	// Track errors
	pi.on("tool_error", async (event, ctx) => {
		const error = event?.error as string;
		if (error) {
			errors.push(error.substring(0, 200));
		}
	});

	// At session end, write summary
	pi.on("agent_end", async (_event, ctx) => {
		const sessionEnd = new Date();
		ensureNotesDir();

		const filesChanged = await getFilesChanged(ctx.cwd);
		const commits = await getCommitCount(ctx.cwd);

		const summary: SessionSummary = {
			startTime: sessionStart,
			endTime: sessionEnd,
			tasks: tasks.slice(0, 10), // Max 10 tasks
			filesChanged: filesChanged.slice(0, 20), // Max 20 files
			commits,
			errors: errors.slice(0, 5), // Max 5 errors
			notes: "",
		};

		const formatted = formatSessionSummary(summary);
		const dateStr = formatDate(sessionStart);
		const filename = `${dateStr}-${sessionStart.getTime()}.md`;
		const filepath = path.join(getSessionNotesDir(), filename);

		try {
			appendFileSync(filepath, formatted + "\n\n", "utf8");

			// Also update a daily summary
			const dailyFile = path.join(getSessionNotesDir(), `${dateStr}-summary.md`);
			const dailyContent = existsSync(dailyFile) ? readFileSync(dailyFile, "utf8") : `# Daily Notes - ${dateStr}\n\n`;

			const entry = `## ${sessionStart.toLocaleTimeString()} (${formatDuration(sessionStart, sessionEnd)})\n` +
				summary.tasks.map(t => `- ${t}`).join("\n") + "\n\n";

			writeFileSync(dailyFile, dailyContent + entry, "utf8");

			if (ctx.hasUI) {
				ctx.ui.notify(`Session notes saved: ${filename}`, "info", { duration: 3000 });
			}
		} catch (err) {
			console.error("Failed to write session notes:", err);
		}
	});
}