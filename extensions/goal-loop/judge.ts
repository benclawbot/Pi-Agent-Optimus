/**
 * Judge — auxiliary LLM call that decides if a standing goal is satisfied.
 *
 * Mirrors Hermes `hermes_cli/goals.py:judge_goal` line by line:
 *   - strict JSON system prompt -> {"done": bool, "reason": str}
 *   - fail-OPEN on transport/parse errors (verdict = "continue")
 *   - returns (verdict, reason, parse_failed) so caller can auto-pause
 *     after N consecutive parse failures (weak judge model guard)
 *
 * HTTP transport: OpenAI-compatible `POST {url}/chat/completions`.
 * Works with OpenAI, OpenRouter, Moonshot, local vLLM, etc.
 *
 * Ponytail: zero deps. Stdlib `fetch` (Node 18+), no SDK.
 */

export type JudgeVerdict = "done" | "continue" | "skipped";

export interface JudgeResult {
	verdict: JudgeVerdict;
	reason: string;
	parse_failed: boolean;
}

export interface JudgeConfig {
	url: string;
	model: string;
	apiKey: string;
	timeoutMs: number;
	maxTokens: number;
	format?: "openai" | "anthropic";
}

export interface JudgeInput {
	goal: string;
	lastResponse: string;
	now?: Date;
}

export const DEFAULT_JUDGE_TIMEOUT_MS = 30_000;
export const DEFAULT_JUDGE_MAX_TOKENS = 4096;
const RESPONSE_SNIPPET_CHARS = 4000;
const GOAL_SNIPPET_CHARS = 2000;

export const JUDGE_SYSTEM_PROMPT = [
	"You are a strict judge evaluating whether an autonomous agent has",
	"achieved a user's stated goal. You receive the goal text and the",
	"agent's most recent response. Your only job is to decide whether",
	"the goal is fully satisfied based on that response.",
	"",
	"A goal is DONE only when:",
	"- The response explicitly confirms the goal was completed, OR",
	"- The response clearly shows the final deliverable was produced, OR",
	"- The response explains the goal is unachievable / blocked / needs",
	"  user input (treat this as DONE with reason describing the block).",
	"",
	"Otherwise the goal is NOT done — CONTINUE.",
	"",
	'Reply ONLY with a single JSON object on one line:',
	'{"done": <true|false>, "reason": "<one-sentence rationale>"}',
].join("\n");

function buildUserPrompt(input: JudgeInput): string {
	const { goal, lastResponse, now = new Date() } = input;
	const truncatedGoal = truncate(goal, GOAL_SNIPPET_CHARS);
	const truncatedResponse = truncate(lastResponse, RESPONSE_SNIPPET_CHARS);
	const timeStr = now.toISOString().replace("T", " ").slice(0, 19);
	return [
		"Goal:",
		truncatedGoal,
		"",
		"Agent's most recent response:",
		truncatedResponse,
		"",
		`Current time: ${timeStr}`,
		"",
		"Is the goal satisfied?",
	].join("\n");
}

function truncate(text: string, limit: number): string {
	if (!text) return "";
	if (text.length <= limit) return text;
	return text.slice(0, limit) + "… [truncated]";
}

const JSON_OBJECT_RE = /\{[\s\S]*?\}/;

export function parseJudgeReply(raw: string): { done: boolean; reason: string; parse_failed: boolean } {
	if (!raw || !raw.trim()) {
		return { done: false, reason: "judge returned empty response", parse_failed: true };
	}
	let text = raw.trim();
	if (text.startsWith("```")) {
		text = text.replace(/^```[a-zA-Z]*\n?/, "").replace(/```$/, "").trim();
	}

	let data: unknown = null;
	try {
		data = JSON.parse(text);
	} catch {
		const match = JSON_OBJECT_RE.exec(text);
		if (match) {
			try {
				data = JSON.parse(match[0]);
			} catch {
				data = null;
			}
		}
	}

	if (!data || typeof data !== "object") {
		return {
			done: false,
			reason: `judge reply was not JSON: ${truncate(raw, 200)}`,
			parse_failed: true,
		};
	}

	const obj = data as Record<string, unknown>;
	const doneVal = obj.done;
	const done = typeof doneVal === "string"
		? ["true", "yes", "1", "done"].includes(doneVal.trim().toLowerCase())
		: Boolean(doneVal);
	const reason = String(obj.reason ?? "").trim() || "no reason provided";
	return { done, reason, parse_failed: false };
}

export async function judgeGoal(input: JudgeInput, cfg: JudgeConfig): Promise<JudgeResult> {
	const goal = (input.goal ?? "").trim();
	const lastResponse = (input.lastResponse ?? "").trim();

	if (!goal) return { verdict: "skipped", reason: "empty goal", parse_failed: false };
	if (!lastResponse) return { verdict: "continue", reason: "empty response (nothing to evaluate)", parse_failed: false };

	if (!cfg.url || !cfg.model || !cfg.apiKey) {
		return { verdict: "continue", reason: "judge not configured", parse_failed: false };
	}

	const format = cfg.format ?? (cfg.url.includes("anthropic") ? "anthropic" : "openai");
	const url = format === "anthropic"
		? `${cfg.url.replace(/\/$/, "")}/v1/messages`
		: `${cfg.url.replace(/\/$/, "")}/chat/completions`;
	const headers: Record<string, string> = format === "anthropic"
		? { "content-type": "application/json", "x-api-key": cfg.apiKey, "anthropic-version": "2023-06-01" }
		: { "content-type": "application/json", authorization: `Bearer ${cfg.apiKey}` };
	const body = format === "anthropic"
		? {
			model: cfg.model,
			max_tokens: cfg.maxTokens,
			system: JUDGE_SYSTEM_PROMPT,
			messages: [{ role: "user", content: buildUserPrompt(input) }],
		}
		: {
			model: cfg.model,
			messages: [
				{ role: "system", content: JUDGE_SYSTEM_PROMPT },
				{ role: "user", content: buildUserPrompt(input) },
			],
			temperature: 0,
			max_tokens: cfg.maxTokens,
		};

	const controller = new AbortController();
	const timer = setTimeout(() => controller.abort(), cfg.timeoutMs);
	try {
		const res = await fetch(url, {
			method: "POST",
			headers,
			body: JSON.stringify(body),
			signal: controller.signal,
		});
		if (!res.ok) {
			return { verdict: "continue", reason: `judge HTTP ${res.status}`, parse_failed: false };
		}
		const payload = (await res.json()) as Record<string, unknown>;
		const raw = format === "anthropic"
			? extractAnthropicText(payload)
			: extractOpenAIText(payload);
		const parsed = parseJudgeReply(raw);
		return {
			verdict: parsed.done ? "done" : "continue",
			reason: parsed.reason,
			parse_failed: parsed.parse_failed,
		};
	} catch (err) {
		return { verdict: "continue", reason: `judge error: ${(err as Error).name}`, parse_failed: false };
	} finally {
		clearTimeout(timer);
	}
}

function extractOpenAIText(payload: Record<string, unknown>): string {
	const choices = payload.choices as Array<{ message?: { content?: string } }> | undefined;
	return choices?.[0]?.message?.content ?? "";
}

function extractAnthropicText(payload: Record<string, unknown>): string {
	const content = payload.content as Array<{ type?: string; text?: string }> | undefined;
	if (!Array.isArray(content)) return "";
	const parts: string[] = [];
	for (const block of content) {
		if (block?.type === "text" && typeof block.text === "string") parts.push(block.text);
	}
	return parts.join("");
}
