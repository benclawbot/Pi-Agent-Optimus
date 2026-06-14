/**
 * Skill Auto-Evolve Extension
 *
 * On agent_end, detects multi-tool problem-solving turns and
 * appends patterns/lessons to .pi/skill-memory.json via the
 * existing skill-evolution skill scripts.
 *
 * Heuristics:
 *   - Turn used >= 3 tool calls AND
 *   - Tools were a mix of read/edit/exec (not just chat) AND
 *   - First user message in turn was a substantive problem
 *
 * Skip: simple Q&A, tool errors only, /reload spam.
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { spawnSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

const HOME = process.env.USERPROFILE || process.env.HOME || "";
const MEMORY = join(HOME, ".pi", "skill-memory.json");
const SKILL_MEMORY_PY = join(HOME, ".pi", "agent", "skills", "skill-evolution", "scripts", "skill-memory.py");

const SPAM_PATTERNS = [/^\s*\/reload\s*$/i, /^\s*\/skill:/i];

interface ToolCall {
	name: string;
	arguments?: any;
}

interface Message {
	role: string;
	content?: any[];
	toolCalls?: ToolCall[];
}

function isProblemPrompt(text: string): boolean {
	if (!text || text.length < 20) return false;
	if (SPAM_PATTERNS.some((p) => p.test(text))) return false;
	return true;
}

function classifyTools(toolNames: string[]): string[] {
	const set = new Set(toolNames);
	const kinds: string[] = [];
	if ([...set].some((n) => /^read$/i.test(n))) kinds.push("read");
	if ([...set].some((n) => /^(write|edit|create)$/i.test(n))) kinds.push("write");
	if ([...set].some((n) => /^(bash|exec|execute_command)$/i.test(n))) kinds.push("exec");
	if ([...set].some((n) => /^(grep|search|find)$/i.test(n))) kinds.push("search");
	return kinds;
}

function extractProblemSummary(messages: Message[]): string {
	// First substantive user message in this turn
	for (const m of messages) {
		if (m.role !== "user") continue;
		const text = m.content
			?.filter((c: any) => c.type === "text")
			?.map((c: any) => c.text)
			?.join(" ")
			?.trim();
		if (isProblemPrompt(text || "")) {
			return (text || "").slice(0, 200);
		}
	}
	return "";
}

function detectToolCategories(toolNames: string[]): string[] {
	const out: string[] = [];
	if (toolNames.includes("read") || toolNames.includes("bash")) out.push("investigation");
	if (toolNames.includes("write") || toolNames.includes("edit") || toolNames.includes("Edit")) out.push("edit");
	if (toolNames.includes("execute_command") || toolNames.includes("bash")) out.push("execution");
	return out;
}

function addMemoryEntry(category: "lessons" | "patterns", skill: string, content: string, context?: string): boolean {
	if (!existsSync(SKILL_MEMORY_PY)) return false;
	// skill-memory.py add <category> <skill> <content> — no --context flag.
	// Fold context into content if provided.
	const finalContent = context ? `${content} [ctx: ${context}]` : content;
	const result = spawnSync("python", [SKILL_MEMORY_PY, "add", category, skill, finalContent], {
		encoding: "utf8",
		timeout: 5000,
	});
	return result.status === 0;
}

let signatureCache: Set<string> | null = null;
let cacheLoadedAt = 0;
const CACHE_TTL_MS = 60_000;

function loadSignatureCache(): Set<string> {
	const now = Date.now();
	if (signatureCache && now - cacheLoadedAt < CACHE_TTL_MS) return signatureCache;
	signatureCache = new Set();
	if (existsSync(MEMORY)) {
		try {
			const mem = JSON.parse(readFileSync(MEMORY, "utf8"));
			const all = [...(mem.lessons || []), ...(mem.patterns || [])];
			for (const e of all) {
				const sig = (e.pattern || "").toLowerCase().slice(0, 60);
				if (sig) signatureCache.add(sig);
			}
		} catch {
			// ignore
		}
	}
	cacheLoadedAt = now;
	return signatureCache;
}

function alreadyCaptured(text: string): boolean {
	const cache = loadSignatureCache();
	const sig = text.toLowerCase().slice(0, 60);
	if (cache.has(sig)) return true;
	// Not in cache — add it tentatively so we don't re-check this turn
	cache.add(sig);
	return false;
}

export default function skillAutoEvolveExtension(pi: ExtensionAPI) {
	pi.on("agent_end", async (event: any, ctx) => {
		try {
			const messages: Message[] = event.messages || [];
			if (!messages.length) return;

			// Collect tool calls
			const toolCalls: ToolCall[] = [];
			for (const m of messages) {
				if (m.toolCalls) toolCalls.push(...m.toolCalls);
				if (m.content) {
					for (const c of m.content) {
						if (c?.type === "toolCall") toolCalls.push(c);
					}
				}
			}

			if (toolCalls.length < 3) return; // trivial turn, skip

			const toolNames = toolCalls.map((t) => t.name);
			const categories = detectToolCategories(toolNames);
			if (categories.length < 2) return; // single-mode (just reads, just chats), skip

			const problem = extractProblemSummary(messages);
			if (!problem) return;

			// Heuristic: was this a "hard problem solved"? Edit/exec + read + multi-tool = yes.
			const hadEdit = categories.includes("edit") || categories.includes("execution");
			if (!hadEdit) return;

			// Build a pattern statement
			const toolSig = [...new Set(toolNames)].sort().join("+");
			const pattern = `Multi-tool solve (${toolSig.slice(0, 80)}) for: ${problem.slice(0, 120)}`;
			const context = `Categories: ${categories.join(", ")}. Tool count: ${toolCalls.length}.`;

			if (alreadyCaptured(pattern)) return;

			const ok = addMemoryEntry("patterns", "general", pattern, context);
			if (ok) {
				// Silent unless interactive UI is available; then short flash.
				const ui = (ctx as any)?.ui;
				if (ui && typeof ui.notify === "function") {
					ui.notify(`Captured pattern: ${problem.slice(0, 60)}`, "info", { duration: 1500 });
				}
			}
		} catch {
			// Never break the session on extension error
		}
	});
}
