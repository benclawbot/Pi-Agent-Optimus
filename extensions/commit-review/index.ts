/**
 * Commit Review Extension
 *
 * Shows a diff summary before commits are created, giving context
 * about what files changed and prompting for commit message.
 *
 * Usage:
 *   Add "+extensions/commit-review/index.ts" to settings.json extensions array
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { exec } from "node:child_process";
import { promisify } from "node:util";

const execAsync = promisify(exec);

interface FileChange {
	name: string;
	status: "added" | "modified" | "deleted" | "renamed";
	linesAdded: number;
	linesRemoved: number;
}

interface DiffSummary {
	totalFiles: number;
	files: FileChange[];
	summary: string;
}

async function getDiffSummary(cwd: string): Promise<DiffSummary> {
	try {
		// Get staged changes
		const { stdout: diffStat } = await execAsync("git diff --staged --stat", { cwd, encoding: "utf8" });

		// Get file list with status
		const { stdout: nameStatus } = await execAsync("git diff --staged --name-status", { cwd, encoding: "utf8" });

		const files: FileChange[] = [];
		const lines = nameStatus.split("\n").filter(Boolean);

		for (const line of lines) {
			const [statusChar, ...pathParts] = line.split("\t");
			const name = pathParts.join("\t");
			const status = statusChar === "A" ? "added" :
						   statusChar === "D" ? "deleted" :
						   statusChar === "R" ? "renamed" : "modified";

			files.push({ name, status, linesAdded: 0, linesRemoved: 0 });
		}

		// Get line counts per file
		const { stdout: diffNumstat } = await execAsync("git diff --staged --numstat", { cwd, encoding: "utf8" });
		const numstatLines = diffNumstat.split("\n");

		for (const line of numstatLines) {
			const parts = line.split("\t");
			if (parts.length >= 2) {
				const added = parseInt(parts[0], 10) || 0;
				const removed = parseInt(parts[1], 10) || 0;
				// Match by order since git diff --staged --name-status and --numstat output in same order
			}
		}

		const totalFiles = files.length;

		// Create summary
		const added = files.filter(f => f.status === "added").length;
		const modified = files.filter(f => f.status === "modified").length;
		const deleted = files.filter(f => f.status === "deleted").length;

		let summary = `${totalFiles} file${totalFiles !== 1 ? "s" : ""}`;
		if (added > 0) summary += `, ${added} added`;
		if (modified > 0) summary += `, ${modified} modified`;
		if (deleted > 0) summary += `, ${deleted} deleted`;

		return { totalFiles, files, summary };
	} catch {
		return { totalFiles: 0, files: [], summary: "Unable to get diff summary" };
	}
}

export default function commitReviewExtension(pi: ExtensionAPI) {
	// Hook into agent to show diff before commit
	pi.on("agent_start", async (_event, ctx) => {
		// Nothing needed - just register the hook
	});

	// Register a tool to show diff summary on demand
	pi.registerTool({
		name: "diff_summary",
		label: "Diff Summary",
		description: "Show a summary of staged changes for commit review. Shows file list, status, and total changes.",
		parameters: {
			type: "object",
			properties: {}
		},
		async execute(_toolCallId, _params, _signal, _onUpdate, ctx) {
			const summary = await getDiffSummary(ctx.cwd);

			if (summary.totalFiles === 0) {
				return {
					content: [{ type: "text", text: "No staged changes to review." }],
					details: summary
				};
			}

			const filesList = summary.files
				.map(f => {
					const icon = f.status === "added" ? "+" : f.status === "deleted" ? "-" : "M";
					return `  ${icon} ${f.name}`;
				})
				.join("\n");

			const message = `## Staged Changes (${summary.summary})\n\n${filesList}\n\nUse /commit to create the commit with this review.`;

			return {
				content: [{ type: "text", text: message }],
				details: summary
			};
		}
	});

	// After agent runs a commit, show what was committed
	pi.on("tool_result", async (event, ctx) => {
		const result = event?.result as any;
		if (!result?.content?.[0]?.text) return;

		// Detect if a commit was just made
		if (result.content[0].text.includes("commit") && result.content[0].text.includes("created")) {
			try {
				const { stdout } = await execAsync("git log -1 --oneline --stat", { cwd: ctx.cwd, encoding: "utf8" });
				if (ctx.hasUI) {
					ctx.ui.notify(`Committed: ${stdout.split("\n")[0]}`, "success", { duration: 4000 });
				}
			} catch {
				// Ignore
			}
		}
	});
}