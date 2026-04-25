/**
 * Auto-Commit Extension
 *
 * After a work session completes, detects uncommitted changes and prompts
 * the user to create a commit using the commit skill.
 *
 * Usage:
 *   Add "+extensions/auto-commit/index.ts" to settings.json extensions array
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { exec } from "node:child_process";
import { promisify } from "node:util";

const execAsync = promisify(exec);

interface GitStatus {
	modified: string[];
	staged: string[];
	untracked: string[];
	dirty: boolean;
}

async function getGitStatus(cwd: string): Promise<GitStatus> {
	try {
		const { stdout } = await execAsync("git status --porcelain", { cwd, encoding: "utf8" });
		const lines = stdout.split("\n").filter(Boolean);
		const result: GitStatus = { modified: [], staged: [], untracked: [], dirty: false };

		for (const line of lines) {
			const staged = line.startsWith(" ");
			const isNew = line.startsWith("?");
			const statusOrName = line.slice(2);
			const name = statusOrName.split(" -> ").pop() ?? statusOrName;

			if (isNew) {
				result.untracked.push(name);
			} else if (staged) {
				result.modified.push(name);
			} else {
				result.staged.push(name);
			}
			result.dirty = true;
		}

		return result;
	} catch {
		return { modified: [], staged: [], untracked: [], dirty: false };
	}
}

function formatFiles(files: string[]): string {
	if (files.length === 0) return "none";
	if (files.length <= 5) return files.join(", ");
	return `${files.slice(0, 3).join(", ")} and ${files.length - 3} more`;
}

export default function autoCommitExtension(pi: ExtensionAPI) {
	pi.on("agent_end", async (_event, ctx) => {
		if (!ctx.hasUI) return;

		const status = await getGitStatus(ctx.cwd);
		if (!status.dirty) return;

		const hasStaged = status.staged.length > 0;
		const modifiedCount = status.modified.length + status.untracked.length;
		const totalCount = status.staged.length + modifiedCount;

		let message: string;
		if (hasStaged) {
			const staged = formatFiles(status.staged);
			const modified = formatFiles([...status.modified, ...status.untracked]);
			message = `Commit staged: ${staged}`;
			if (modified !== "none") {
				message += `\nUnstaged: ${modified}`;
			}
		} else {
			message = `Uncommitted changes (${totalCount} files): ${formatFiles([...status.modified, ...status.untracked])}`;
		}

		ctx.ui.notify(message, "info", { duration: 8000 });

		// Queue /commit for the user to trigger
		const { execute } = await import("@mariozechner/pi-coding-agent");
		pi.sendUserMessage("/commit", { deliverAs: "steer" });
	});

	// Also listen for specific patterns that indicate work is done
	// This allows users to signal completion via tool results
	pi.on("tool_result", async (event, ctx) => {
		if (!ctx.hasUI) return;
		const result = event?.result as any;
		if (!result?.content?.[0]?.text) return;

		const text = result.content[0].text;
		// Detect completion patterns
		const isDone =
			text.includes("✓") ||
			text.includes("done") ||
			text.includes("completed") ||
			text.includes("success");

		if (isDone) {
			const status = await getGitStatus(ctx.cwd);
			if (status.dirty) {
				ctx.ui.notify("Work detected. Consider running /commit", "info", { duration: 5000 });
			}
		}
	});
}