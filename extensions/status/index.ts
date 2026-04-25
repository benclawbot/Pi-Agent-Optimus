/**
 * Status Dashboard Extension
 *
 * Provides a unified status view via /status showing:
 * - Open todos
 * - Uncommitted changes
 * - Pending PRs
 * - CI status
 *
 * Usage:
 *   Add "+extensions/status/index.ts" to settings.json extensions array
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { exec } from "node:child_process";
import { promisify } from "node:util";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import os from "node:os";

const execAsync = promisify(exec);

interface StatusData {
	todos: {
		total: number;
		open: number;
		assigned: number;
	};
	git: {
		dirty: boolean;
		modified: number;
		staged: number;
		untracked: number;
		currentBranch: string;
	};
	prs: {
		total: number;
		pending: number;
	};
	ci: {
		failing: number;
		running: number;
	};
}

function getTodosDir(cwd: string): string {
	const agentDir = process.env.PI_AGENT_DIR ?? path.join(os.homedir(), ".pi", "agent");
	return agentDir;
}

function countOpenTodos(todosDir: string): { total: number; open: number; assigned: number } {
	try {
		const entries = readdirSync(todosDir).filter(e => e.endsWith(".md"));
		let open = 0;
		let assigned = 0;

		for (const entry of entries) {
			try {
				const content = readFileSync(path.join(todosDir, entry), "utf8");
				const jsonStart = content.indexOf("{");
				const jsonEnd = content.indexOf("}");
				if (jsonStart === -1 || jsonEnd === -1) continue;

				const json = JSON.parse(content.slice(jsonStart, jsonEnd + 1));
				const status = (json.status || "open").toLowerCase();
				if (status !== "closed" && status !== "done") {
					open++;
				}
				if (json.assigned_to_session) {
					assigned++;
				}
			} catch {
				// skip
			}
		}

		return { total: entries.length, open, assigned };
	} catch {
		return { total: 0, open: 0, assigned: 0 };
	}
}

async function getGitStatus(cwd: string): Promise<{
	dirty: boolean;
	modified: number;
	staged: number;
	untracked: number;
	currentBranch: string;
}> {
	try {
		const { stdout: current } = await execAsync("git branch --show-current", { cwd, encoding: "utf8" });
		const currentBranch = current.trim();

		const { stdout } = await execAsync("git status --porcelain", { cwd, encoding: "utf8" });
		const lines = stdout.split("\n").filter(Boolean);

		let staged = 0, modified = 0, untracked = 0;
		for (const line of lines) {
			if (line.startsWith("??")) untracked++;
			else if (line.startsWith(" ") && !line.startsWith("  ")) staged++;
			else modified++;
		}

		return {
			dirty: lines.length > 0,
			modified,
			staged,
			untracked,
			currentBranch,
		};
	} catch {
		return {
			dirty: false,
			modified: 0,
			staged: 0,
			untracked: 0,
			currentBranch: "unknown",
		};
	}
}

async function getGitHubPRs(): Promise<{ total: number; pending: number }> {
	try {
		const { stdout } = await execAsync("gh pr list --state open --json number,title,isDraft --jq '.'", {
			encoding: "utf8",
		});
		const prs = JSON.parse(stdout || "[]");
		return {
			total: prs.length,
			pending: prs.filter((pr: any) => !pr.isDraft).length,
		};
	} catch {
		return { total: 0, pending: 0 };
	}
}

async function getCIStatus(): Promise<{ failing: number; running: number }> {
	try {
		const { stdout } = await execAsync(
			"gh run list --limit 10 --json name,status,conclusion --jq '.[] | select(.status != null)'",
			{ encoding: "utf8" }
		);
		const runs = JSON.parse(stdout || "[]");
		return {
			failing: runs.filter((r: any) => r.conclusion === "failure").length,
			running: runs.filter((r: any) => r.status === "in_progress" || r.status === "queued").length,
		};
	} catch {
		return { failing: 0, running: 0 };
	}
}

async function getStatus(cwd: string): Promise<StatusData> {
	const [git, prs, ci] = await Promise.all([getGitStatus(cwd), getGitHubPRs(), getCIStatus()]);
	const todos = countOpenTodos(getTodosDir(cwd));

	return { todos, git, prs, ci };
}

export default function statusExtension(pi: ExtensionAPI) {
	pi.registerTool({
		name: "status",
		label: "Status",
		description:
			"Show project health status: open todos, uncommitted changes, pending PRs, and CI status. Use when 'status', 'health', 'dashboard', 'overview', or checking project state.",
		parameters: {
			type: "object",
			properties: {},
		},
		async execute(_toolCallId, _params, _signal, _onUpdate, ctx) {
			const data = await getStatus(ctx.cwd);

			const sections: string[] = [];

			// Header
			sections.push(`## Status: ${ctx.cwd}`);
			sections.push("");

			// Todos
			const todoIcon = data.todos.open === 0 ? "✓" : "●";
			const todoColor = data.todos.open === 0 ? "success" : "warning";
			sections.push(
				`${todoIcon} **Todos:** ${data.todos.open} open / ${data.todos.total} total`
			);
			if (data.todos.assigned > 0) {
				sections.push(`   └ ${data.todos.assigned} assigned to this session`);
			}

			// Git
			sections.push("");
			if (data.git.dirty) {
				sections.push(`⚠ **Git:** ${data.git.currentBranch} (${data.git.modified} modified, ${data.git.staged} staged, ${data.git.untracked} untracked)`);
			} else {
				sections.push(`✓ **Git:** ${data.git.currentBranch} (clean)`);
			}

			// PRs
			sections.push("");
			if (data.prs.total === 0) {
				sections.push(`✓ **PRs:** none pending`);
			} else {
				sections.push(`● **PRs:** ${data.prs.pending} pending / ${data.prs.total} total`);
			}

			// CI
			sections.push("");
			if (data.ci.failing > 0) {
				sections.push(`✗ **CI:** ${data.ci.failing} failing`);
			} else if (data.ci.running > 0) {
				sections.push(`○ **CI:** ${data.ci.running} running`);
			} else {
				sections.push(`✓ **CI:** all passing`);
			}

			sections.push("");
			sections.push("---");
			sections.push("Run `/status` to refresh.");

			return {
				content: [{ type: "text", text: sections.join("\n") }],
				details: data,
			};
		}
	});
}
