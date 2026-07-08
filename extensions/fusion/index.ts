import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { spawn } from "node:child_process";
import { resolvePiEntry } from "../_shared/pi-resolve";

interface ModelResult {
	model: string;
	role: string;
	content: string;
	durationMs: number;
	exitCode: number;
}

const LITE_PANEL = [
	{ model: "minimax/MiniMax-M2.7", role: "independent coding analyst" },
	{ model: "minimax/MiniMax-M3", role: "adversarial coding critic" },
] as const;
const FULL_PANEL = [
	{ model: "minimax/MiniMax-M2.7", role: "independent analyst" },
	{ model: "minimax/MiniMax-M2.7", role: "adversarial critic" },
	{ model: "minimax/MiniMax-M3", role: "systems thinker" },
] as const;
const JUDGE_MODEL = "minimax/MiniMax-M3";

function truncate(value: string, max = 20_000): string {
	return value.length <= max ? value : `${value.slice(0, max)}\n[truncated]`;
}

function runModel(args: {
	model: string;
	role: string;
	prompt?: string;
	messages?: Array<{ role: string; content: string }>;
	cwd: string;
	maxDurationMs: number;
	signal?: AbortSignal;
}): Promise<ModelResult> {
	return new Promise((resolve, reject) => {
		const resolved = resolvePiEntry();
		const command = resolved?.command ?? (process.platform === "win32" ? "pi.cmd" : "pi");
		const cliArgs = [
			...(resolved?.prefixArgs ?? []),
			"--model",
			args.model,
			"--thinking",
			"off",
			"--no-session",
			"--no-extensions",
			"--no-skills",
			"--tools",
			"read,grep,find,ls",
		];
		cliArgs.push("--print", "-p");
		if (args.messages) {
			// First message is system, rest are user turns — use --system-prompt for system
			const systemMsg = args.messages.find((m) => m.role === "system");
			const userMsg = args.messages.find((m) => m.role === "user");
			if (systemMsg) cliArgs.push("--system-prompt", systemMsg.content);
			if (userMsg) cliArgs.push(userMsg.content);
		} else {
			cliArgs.push(args.prompt ?? "");
		}
		const started = Date.now();
		const child = spawn(command, cliArgs, {
			cwd: args.cwd,
			windowsHide: true,
			stdio: ["ignore", "pipe", "pipe"],
		});
		let stdout = "";
		let stderr = "";
		child.stdout.on("data", (chunk) => { stdout += chunk.toString(); });
		child.stderr.on("data", (chunk) => { stderr += chunk.toString(); });
		const timer = setTimeout(() => child.kill(), args.maxDurationMs);
		const cleanup = () => { clearTimeout(timer); };
		if (args.signal) {
			args.signal.addEventListener("abort", () => {
				cleanup();
				child.kill("SIGTERM");
				setTimeout(() => child.kill("SIGKILL"), 2000);
			});
		}
		child.on("error", (err) => { cleanup(); reject(err); });
		child.on("close", (code) => {
			cleanup();
			resolve({
				model: args.model,
				role: args.role,
				content: truncate(stdout.trim() || stderr.trim()),
				durationMs: Date.now() - started,
				exitCode: code ?? 1,
			});
		});
	});
}

function panelistMessages(question: string, role: string): Array<{ role: string; content: string }> {
	return [
		{
			role: "system",
			content: [
				`You are the ${role} in a multi-model deliberation panel.`,
				"Analyze independently. Do not assume another panelist will catch your mistakes.",
				"Be concrete, identify uncertainty, and include actionable recommendations.",
			].join("\n"),
		},
		{
			role: "user",
			content: `Question:\n${question}`,
		},
	];
}

function judgePrompt(question: string, responses: ModelResult[]): string {
	const panelText = responses.map((response, index) => [
		`## Panel ${index + 1}`,
		response.content,
	].join("\n")).join("\n\n");
	return [
		"You are the judge in a bounded multi-model deliberation.",
		"Compare the panel responses. Do not merely summarize or majority-vote.",
		"Return concise Markdown with exactly these sections:",
		"## Consensus",
		"## Contradictions",
		"## Partial Coverage",
		"## Unique Insights",
		"## Blind Spots",
		"## Recommended Synthesis",
		"",
		`Original question:\n${question}`,
		"",
		panelText,
	].join("\n");
}

export default function fusionExtension(pi: ExtensionAPI) {
	pi.registerTool({
		name: "fusion",
		label: "MiniMax Fusion",
		description: "Run a bounded M2.7/M3 coding deliberation panel in parallel, then use M3 to judge consensus, contradictions, unique insights, and blind spots. Use for architecture, difficult debugging, risky migrations, security analysis, and high-stakes review. Avoid for simple edits.",
		promptSnippet: "fusion(question, profile='lite', max_duration_ms?) — parallel MiniMax coding panel plus M3 judge",
		parameters: Type.Object({
			question: Type.String({ description: "Self-contained question or task for the panel" }),
			profile: Type.Optional(Type.String({
				description: "'lite' (default: M2.7 + M3) or 'full' (M2.7 twice + M3)",
				default: "lite",
			})),
			max_duration_ms: Type.Optional(Type.Number({
				description: "Per-stage hard timeout in milliseconds; defaults to 180000",
				default: 180000,
			})),
		}),
		async execute(_toolCallId, params, _signal, _onUpdate, ctx) {
			const maxDurationMs = Math.min(600_000, Math.max(10_000, params.max_duration_ms ?? 180_000));
			const panel = params.profile === "full" ? FULL_PANEL : LITE_PANEL;
			const settled = await Promise.allSettled(panel.map((panelist) => runModel({
				...panelist,
				messages: panelistMessages(params.question, panelist.role),
				cwd: ctx.cwd,
				maxDurationMs,
				signal: ctx.signal,
			})));
			const responses: ModelResult[] = settled
				.map((result): ModelResult | null => {
					if (result.status === "rejected") return null;
					return result.value;
				})
				.filter((r): r is ModelResult => r !== null && !!r.content.trim());
			if (responses.length === 0) {
				return { content: [{ type: "text", text: "Fusion failed: every panelist failed." }] };
			}
			// Judge gets 1.5x the panelist timeout since synthesis takes longer
			const judgeTimeout = Math.min(600_000, Math.floor(maxDurationMs * 1.5));
			const judge = await runModel({
				model: JUDGE_MODEL,
				role: "judge",
				prompt: judgePrompt(params.question, responses),
				cwd: ctx.cwd,
				maxDurationMs: judgeTimeout,
			});
			const raw = responses.map((response) =>
				`### Panel (${(response.durationMs / 1000).toFixed(1)}s)\n${response.content}`,
			).join("\n\n");
			const output = [
				`# MiniMax Fusion ${params.profile === "full" ? "full" : "lite"} (${responses.length}/${panel.length} panelists succeeded)`,
				"",
				judge.content || "Judge failed; use the raw panel responses below.",
				"",
				"<details><summary>Raw panel responses</summary>",
				"",
				raw,
				"",
				"</details>",
			].join("\n");
			return { content: [{ type: "text", text: truncate(output, 50_000) }] };
		},
	});
}
