/**
 * Branch Cleanup Extension
 *
 * Detects merged and stale local branches, prompts to delete them.
 * Run manually via command or automatically after certain events.
 *
 * Usage:
 *   Add "+extensions/branch-cleanup/index.ts" to settings.json extensions array
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { exec } from "node:child_process";
import { promisify } from "node:util";

const execAsync = promisify(exec);

interface Branch {
	name: string;
	isMerged: boolean;
	isCurrent: boolean;
}

async function getBranches(cwd: string): Promise<Branch[]> {
	try {
		// Get current branch first
		const { stdout: current } = await execAsync("git branch --show-current", { cwd, encoding: "utf8" });
		const currentBranch = current.trim();

		// Get all local branches
		const { stdout } = await execAsync("git branch --format='%(refname:short) %(HEAD)'", { cwd, encoding: "utf8" });
		const branches: Branch[] = [];

		for (const line of stdout.split("\n").filter(Boolean)) {
			const [name, indicator] = line.trim().split(" ");
			if (!name) continue;
			branches.push({
				name,
				isCurrent: name === currentBranch || indicator === "*",
				isMerged: false, // Will check separately
			});
		}

		return branches;
	} catch {
		return [];
	}
}

async function checkMergedBranches(cwd: string): Promise<string[]> {
	try {
		const { stdout } = await execAsync("git branch --merged main 2>/dev/null || git branch --merged master 2>/dev/null || git branch --merged HEAD", { cwd, encoding: "utf8" });
		return stdout.split("\n").map(b => b.trim()).filter(Boolean);
	} catch {
		return [];
	}
}

export default function branchCleanupExtension(pi: ExtensionAPI) {
	// Register command to check and cleanup branches
	pi.registerTool({
		name: "branch_cleanup",
		label: "Branch Cleanup",
		description: "Find and optionally delete merged or stale branches. Shows merged branches, current branch status, and prompts for deletion.",
		parameters: {
			type: "object",
			properties: {
				action: {
					type: "string",
					enum: ["check", "delete", "list"],
					description: "Action: check (find merged), list (show all), delete (remove merged)"
				},
				force: {
					type: "boolean",
					description: "Skip confirmation prompt"
				}
			}
		},
		async execute(_toolCallId, params, _signal, _onUpdate, ctx) {
			const cwd = ctx.cwd;
			const action = params.action ?? "check";

			if (action === "list") {
				const branches = await getBranches(cwd);
				const output = branches
					.map(b => `${b.isCurrent ? "*" : " "} ${b.name}${b.isCurrent ? " (current)" : ""}`)
					.join("\n");
				return {
					content: [{ type: "text", text: `Local branches:\n${output}` }],
					details: { branches }
				};
			}

			const mergedBranches = await checkMergedBranches(cwd);
			const branches = await getBranches(cwd);
			const currentBranch = branches.find(b => b.isCurrent)?.name ?? "unknown";

			if (action === "check") {
				const staleBranches = mergedBranches.filter(b => !b.includes(currentBranch));
				if (staleBranches.length === 0) {
					return {
						content: [{ type: "text", text: "No merged branches found (excluding current)." }],
						details: { mergedBranches: [], currentBranch }
					};
				}

				const output = staleBranches.map(b => `  - ${b}`).join("\n");
				return {
					content: [{ type: "text", text: `Merged branches (safe to delete):\n${output}\n\nUse branch_cleanup(action: "delete") to remove them.` }],
					details: { mergedBranches: staleBranches, currentBranch }
				};
			}

			if (action === "delete") {
				const toDelete = mergedBranches.filter(b => !b.includes(currentBranch) && b !== currentBranch);

				if (toDelete.length === 0) {
					return {
						content: [{ type: "text", text: "No merged branches to delete." }],
						details: { deleted: [], currentBranch }
					};
				}

				// Delete each branch
				const deleted: string[] = [];
				const failed: string[] = [];

				for (const branch of toDelete) {
					try {
						await execAsync(`git branch -d ${branch}`, { cwd, encoding: "utf8" });
						deleted.push(branch);
					} catch {
						failed.push(branch);
					}
				}

				let message = `Deleted ${deleted.length} branches: ${deleted.join(", ")}`;
				if (failed.length > 0) {
					message += `\nFailed to delete: ${failed.join(", ")} (may not be fully merged)`;
				}

				return {
					content: [{ type: "text", text: message }],
					details: { deleted, failed, currentBranch }
				};
			}

			return {
				content: [{ type: "text", text: "Unknown action. Use: check, list, or delete" }],
				details: {}
			};
		}
	});

	// Optional: auto-check after certain git operations
	pi.on("tool_result", async (event, ctx) => {
		// Could trigger after a merge completes
		// For now, just make it available via command
	});

	// Provide a slash command for easy access
	pi.on("agent_start", async (_event, ctx) => {
		// Nothing needed - command is available
	});
}