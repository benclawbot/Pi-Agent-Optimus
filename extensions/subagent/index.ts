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
import { dirname } from "node:path";
import { resolvePiEntry } from "../_shared/pi-resolve";

const READ_HEAVY_TOOLS = "read,grep,find,ls";
const READ_AND_WRITE_TOOLS = "read,grep,find,ls,bash,edit,write";

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

		const STDOUT_MAX = 500_000;
		const STDERR_MAX = 50_000;
		let stdoutHead = 0;
		let stderrHead = 0;
		const stdoutRing: string[] = [];
		const stderrRing: string[] = [];
		let stdoutSize = 0;
		let stderrSize = 0;
		let killed = false;

		const killTimer = setTimeout(() => {
			killed = true;
			child.kill("SIGTERM");
			setTimeout(() => child.kill("SIGKILL"), 2000);
		}, args.maxDurationMs);

		child.stdout.on("data", (chunk: Buffer) => {
			const s = chunk.toString("utf8");
			stdoutRing.push(s);
			stdoutSize += s.length;
			while (stdoutSize > STDOUT_MAX && stdoutRing.length > 0) {
				const evicted = stdoutRing.shift()!;
				stdoutSize -= evicted.length;
				stdoutHead += evicted.length;
			}
		});
		child.stderr.on("data", (chunk: Buffer) => {
			const s = chunk.toString("utf8");
			stderrRing.push(s);
			stderrSize += s.length;
			while (stderrSize > STDERR_MAX && stderrRing.length > 0) {
				const evicted = stderrRing.shift()!;
				stderrSize -= evicted.length;
				stderrHead += evicted.length;
			}
		});

		const assemble = (ring: string[], size: number): string => ring.join("");

		child.on("error", (err) => {
			clearTimeout(killTimer);
			reject(err);
		});
		child.on("close", (code) => {
			clearTimeout(killTimer);
			const stdout = assemble(stdoutRing, stdoutSize);
			const stderr = assemble(stderrRing, stderrSize);
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
			"mode='read-write' grants bash access. Only use with trusted goals. Prefer read-only mode for untrusted or external-project tasks.",
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
