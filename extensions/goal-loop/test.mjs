/**
 * Tests for goal-loop. The judge module is the only piece with non-trivial
 * branching, so it's the focus. The loop driver is a thin fs+hook wrapper
 * around judge + sendUserMessage, which is covered by the e2e (real RPC).
 */

const judgeMod = await import("./judge.ts");

let failed = 0;
function assert(cond, msg) {
	if (!cond) { failed += 1; console.error(`✗ ${msg}`); }
	else console.log(`✓ ${msg}`);
}

// ─── judge parser ──────────────────────────────────────────────────────

let p = judgeMod.parseJudgeReply("");
assert(p.parse_failed === true && p.reason.includes("empty"), "empty reply -> parse_failed");

p = judgeMod.parseJudgeReply("not json at all");
assert(p.parse_failed === true, "prose -> parse_failed");

p = judgeMod.parseJudgeReply('{"done": true, "reason": "ok"}');
assert(p.done === true && p.reason === "ok" && !p.parse_failed, "clean JSON done=true");

p = judgeMod.parseJudgeReply('{"done": false, "reason": "still going"}');
assert(p.done === false && p.reason === "still going", "clean JSON done=false");

p = judgeMod.parseJudgeReply('noise before {"done":"yes","reason":"yep"} and after');
assert(p.done === true && p.reason === "yep", "extracts embedded JSON, yes string");

p = judgeMod.parseJudgeReply('{"done":"1","reason":"x"}');
assert(p.done === true, "string '1' -> true");

p = judgeMod.parseJudgeReply('{"done":"","reason":""}');
assert(p.done === false && p.reason === "no reason provided", "missing reason -> default");

p = judgeMod.parseJudgeReply('```json\n{"done": true, "reason": "ok"}\n```');
assert(p.done === true && p.reason === "ok", "strip markdown code fence");

p = judgeMod.parseJudgeReply('{"done":true,"reason":"' + "a very long reason ".repeat(50) + 'end"}');
assert(p.parse_failed === false && p.reason.length > 100, "long reason still parses");

// ─── judgeGoal network / config paths ──────────────────────────────────

let r = await judgeMod.judgeGoal({ goal: "", lastResponse: "x" }, {
	url: "https://x", model: "m", apiKey: "k", timeoutMs: 1, maxTokens: 1,
});
assert(r.verdict === "skipped", "empty goal -> skipped");

r = await judgeMod.judgeGoal({ goal: "g", lastResponse: "" }, {
	url: "https://x", model: "m", apiKey: "k", timeoutMs: 1, maxTokens: 1,
});
assert(r.verdict === "continue", "empty response -> continue");

r = await judgeMod.judgeGoal({ goal: "g", lastResponse: "x" }, {
	url: "", model: "", apiKey: "", timeoutMs: 1, maxTokens: 1,
});
assert(r.verdict === "continue" && r.reason.includes("not configured"), "no cfg -> continue, not parse_failed");

r = await judgeMod.judgeGoal({ goal: "g", lastResponse: "x" }, {
	url: "http://127.0.0.1:1", model: "m", apiKey: "k", timeoutMs: 50, maxTokens: 1,
});
assert(r.verdict === "continue" && !r.parse_failed, "network error -> continue, NOT parse_failed (transport != parse)");

// Truncation
const big = "x".repeat(5000);
r = await judgeMod.judgeGoal({ goal: "g", lastResponse: big }, {
	url: "http://127.0.0.1:1", model: "m", apiKey: "k", timeoutMs: 50, maxTokens: 1,
});
assert(r.verdict === "continue", "long response -> still judges (transport fail-open)");

// System prompt contract test
assert(judgeMod.JUDGE_SYSTEM_PROMPT.includes('{"done"'), "system prompt contains JSON example");
assert(judgeMod.JUDGE_SYSTEM_PROMPT.includes("Reply ONLY"), "system prompt requires one-line JSON");

if (failed > 0) {
	console.error(`\n${failed} assertion(s) failed`);
	process.exit(1);
}
console.log("\nAll judge assertions passed.");
