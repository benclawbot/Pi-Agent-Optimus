/**
 * subagent Tool
 *
 * Delegated execution primitive. Spawns a child `pi -p` process with a
 * restricted tool set, a clean context, and an isolated cwd. Use for
 * read-heavy parallel work (the multi-agent "when and why" rule from
 * LangChain's 2025 synthesis).
 *
 * Read-heavy tasks (research, review, find, list) → safe to parallelize.
 * Write-heavy tasks (refactor, generate, edit) → keep on the lead agent.
 *
 * Returns the final assistant text. If the child fails, returns the
 * stderr tail so the lead agent can decide whether to retry.
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { join, dirname } from "node:path";

const READ_HEAVY_TOOLS = "read,grep,find,ls";
const READ_AND_WRITE_TOOLS = "read,grep,find,ls,bash,edit,write";

/**
 * Resolve the absolute path to the `pi` CLI entry script.
 * The `pi` shim is a shell wrapper, so spawning it directly fails on Windows
 * without the .cmd suffix. We bypass the shim and spawn node with the actual
 * CLI script from the global node_modules.
 */
function resolvePiEntry(): { command: string; prefixArgs: string[] } | null {
	const candidates = [
		// Global install: ~/AppData/Roaming/npm/node_modules/@earendil-works/pi-coding-agent/dist/cli.js
		join(process.env.APPDATA || "", "npm", "node_modules", "@earendil-works", "pi-coding-agent", "dist", "cli.js"),
		// Bun install location fallback
		join(process.env.HOME || "", ".bun", "install", "global", "node_modules", "@earendil-works", "pi-coding-agent", "dist", "cli.js"),
		// Cwd-local
		join(process.cwd(), "node_modules", "@earendil-works", "pi-coding-agent", "dist", "cli.js"),
	];
	for (const c of candidates) {
		if (c && existsSync(c)) {
			return { command: process.execPath, prefixArgs: [c] };
		}
	}
	return null;
}

interface SubagentResult {
	stdout: string;
	stderr: string;
	exitCode: number;
	durationMs: number;
	model: string;
}

function runSubagent(args: {
	prompt: string;
	cwd: string;
	model: string;
	mode: "read" | "read-write";
	thinking: "off" | "low" | "medium" | "high";
	maxDurationMs: number;
}): Promise<SubagentResult> {
	const start = Date.now();
	return new Promise((resolve, reject) => {
		const tools = args.mode === "read" ? READ_HEAVY_TOOLS : READ_AND_WRITE_TOOLS;

		// Resolve the pi entry point. Falls back to PATH lookup on Linux/macOS.
		const resolved = resolvePiEntry();
		let command: string;
		let subArgs: string[];
		if (resolved) {
			command = resolved.command;
			subArgs = [
				...resolved.prefixArgs,
				"-p",
				args.prompt,
				"--model",
				args.model,
				"--thinking",
				args.thinking,
				"--tools",
				tools,
				"--no-session",
			];
		} else {
			command = "pi";
			subArgs = [
				"-p",
				args.prompt,
				"--model",
				args.model,
				"--thinking",
				args.thinking,
				"--tools",
				tools,
				"--no-session",
			];
		}

		const child = spawn(command, subArgs, {
			cwd: args.cwd,
			windowsHide: true,
			stdio: ["ignore", "pipe", "pipe"],
		});

		let stdout = "";
		let stderr = "";
		let killed = false;

		const killTimer = setTimeout(() => {
			killed = true;
			child.kill("SIGTERM");
			setTimeout(() => child.kill("SIGKILL"), 2000);
		}, args.maxDurationMs);

		child.stdout.on("data", (chunk: Buffer) => {
			stdout += chunk.toString("utf8");
			// Cap stdout to avoid OOM
			if (stdout.length > 500_000) stdout = stdout.slice(-500_000);
		});
		child.stderr.on("data", (chunk: Buffer) => {
			stderr += chunk.toString("utf8");
			if (stderr.length > 50_000) stderr = stderr.slice(-50_000);
		});

		child.on("error", (err) => {
			clearTimeout(killTimer);
			reject(err);
		});
		child.on("close", (code) => {
			clearTimeout(killTimer);
			resolve({
				stdout,
				stderr,
				exitCode: code ?? -1,
				durationMs: Date.now() - start,
				model: args.model,
			});
			// `killed` is captured in stderr already; nothing else to do
		});
	});
}

function truncate(s: string, n: number): string {
	if (s.length <= n) return s;
	return s.slice(0, n - 100) + `\n\n… [truncated ${s.length - n + 100} chars] …\n` + s.slice(-100);
}

export default function subagentExtension(pi: ExtensionAPI) {
	pi.registerTool({
		name: "subagent",
		label: "Run Subagent",
		description:
			"Delegate a task to a child pi process with an isolated context and a restricted tool set. Use for read-heavy parallel work (research, code review, file enumeration, dependency audit). For write-heavy work, keep the keyboard on the lead agent and use this only for the read-only preparation step. The child cannot see the parent's context — pass everything it needs in the prompt.",
		promptSnippet: "subagent(goal, cwd?, mode?, model?) — delegated execution in a child process",
		promptGuidelines: [
			"Read-heavy work (research, review, search, find) → safe to call subagent.",
			"Write-heavy work (refactor, multi-file edit, generate) → do it on the lead, not in a subagent.",
			"Pass the full task in `goal`. The subagent has no memory of the parent session.",
			"Use mode='read' for analysis (default), mode='read-write' when the subagent must edit files.",
			"Results are truncated to ~50k chars. Ask the subagent to summarize, not dump.",
		],
		parameters: Type.Object({
			goal: Type.String({
				description: "Complete, self-contained task description. The subagent has no parent context.",
			}),
			cwd: Type.Optional(
				Type.String({
					description: "Working directory for the subagent. Defaults to current cwd.",
				}),
			),
			mode: Type.Optional(
				Type.String({
					description: "'read' (default; read-only tools) or 'read-write' (adds edit,write).",
					default: "read",
				}),
			),
			model: Type.Optional(
				Type.String({
					description: "Model pattern. Defaults to parent's model.",
				}),
			),
			thinking: Type.Optional(
				Type.String({
					description: "Thinking level: off, low, medium, high. Defaults to off for speed.",
					default: "off",
				}),
			),
			max_duration_ms: Type.Optional(
				Type.Number({
					description: "Hard timeout in ms. Defaults to 120000 (2 min).",
					default: 120000,
				}),
			),
		}),
		async execute(_toolCallId, params, _signal, _onUpdate, ctx) {
			const mode = (params.mode === "read-write" ? "read-write" : "read") as "read" | "read-write";
			const cwd = params.cwd || process.cwd();
			const model = params.model || ctx.model?.id || "minimax/MiniMax-M2.7";
			const thinking = (params.thinking || "off") as "off" | "low" | "medium" | "high";
			const maxDurationMs = Math.min(600_000, Math.max(1_000, params.max_duration_ms ?? 120_000));

			try {
				const result = await runSubagent({
					prompt: params.goal,
					cwd,
					model,
					mode,
					thinking,
					maxDurationMs,
				});

				const summary = [
					`[subagent done in ${(result.durationMs / 1000).toFixed(1)}s, model=${result.model}, mode=${mode}, exit=${result.exitCode}]`,
					"",
					truncate(result.stdout.trim(), 30_000),
				].join("\n");

				const footer = result.exitCode === 0
					? ""
					: `\n\n[stderr tail]\n${truncate(result.stderr, 2000)}`;

				return {
					content: [{ type: "text", text: summary + footer }],
					details: {
						exitCode: result.exitCode,
						durationMs: result.durationMs,
						model: result.model,
						mode,
						stdoutChars: result.stdout.length,
						stderrChars: result.stderr.length,
					},
				};
			} catch (err) {
				const msg = err instanceof Error ? err.message : String(err);
				return {
					content: [{ type: "text", text: `subagent failed to spawn: ${msg}` }],
					details: { error: msg, cwd, model },
				};
			}
		},
	});
}
