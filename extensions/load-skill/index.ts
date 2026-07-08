/**
 * load_skill Tool
 *
 * On-demand progressive skill loading. Skills are listed in the system
 * prompt by description only (saves tokens). When the model needs the
 * full body, it calls this tool.
 *
 * Implements the "Agent Skills" pattern (Anthropic, Oct 2025): procedural
 * knowledge as files, discovered and loaded on demand.
 *
 * Usage from the agent:
 *   load_skill({ name: "verify-done" })
 *   load_skill({ name: "deep-research" })
 *   list_skills({ tag: "verification" })  // optional filter
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { getAgentDir } from "@earendil-works/pi-coding-agent";
import { readFileSync, readdirSync, existsSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { homedir } from "node:os";
import { Type } from "typebox";

interface SkillMeta {
	name: string;
	description: string;
	path: string;
	source: "user" | "shared" | "project";
	bodyChars: number;
}

const SKILL_SEARCH_DIRS = [
	() => join(getAgentDir(), "skills"),
	() => join(homedir(), ".agents", "skills"),
	() => join(process.cwd(), ".pi", "skills"),
];

function expandTilde(p: string): string {
	return p.replace(/^~(?=[/\\])/, homedir());
}

function readSkillMeta(skillDir: string, source: SkillMeta["source"]): SkillMeta | null {
	const skillPath = join(skillDir, "SKILL.md");
	if (!existsSync(skillPath)) return null;
	const text = readFileSync(skillPath, "utf8");
	const fmMatch = text.match(/^---\n([\s\S]*?)\n---\n?/);
	if (!fmMatch) return null;
	const fm: Record<string, string> = {};
	for (const line of fmMatch[1].split("\n")) {
		const m = line.match(/^(\w+):\s*"?(.+?)"?\s*$/);
		if (m) fm[m[1]] = m[2];
	}
	if (!fm.name) return null;
	return {
		name: fm.name,
		description: fm.description || "",
		path: skillPath,
		source,
		bodyChars: text.length,
	};
}

function listAllSkills(): SkillMeta[] {
	const out: SkillMeta[] = [];
	for (const dirFn of SKILL_SEARCH_DIRS) {
		const dir = dirFn();
		if (!existsSync(dir)) continue;
		const source: SkillMeta["source"] = dir.includes(getAgentDir())
			? "user"
			: dir.includes(homedir())
			? "shared"
			: "project";
		let entries: string[];
		try {
			entries = readdirSync(dir);
		} catch {
			continue;
		}
		for (const e of entries) {
			const skillDir = join(dir, e);
			try {
				if (!statSync(skillDir).isDirectory()) continue;
			} catch {
				continue;
			}
			const meta = readSkillMeta(skillDir, source);
			if (meta) out.push(meta);
		}
	}
	// Dedup by name (first wins = user dir takes priority)
	const seen = new Set<string>();
	return out.filter((s) => {
		if (seen.has(s.name)) return false;
		seen.add(s.name);
		return true;
	});
}

function findSkill(name: string): SkillMeta | null {
	return listAllSkills().find((s) => s.name === name) ?? null;
}

export default function loadSkillExtension(pi: ExtensionAPI) {
	pi.registerTool({
		name: "load_skill",
		label: "Load Skill",
		description:
			"Load the full body of a skill by name. Skills are listed in the system prompt by description only to save tokens. Call this tool when the description matches your task and you need the full procedure, checklist, or template.",
		promptSnippet: "load_skill(name) — fetch full body of a named skill on demand",
		promptGuidelines: [
			"Use load_skill when a task matches a skill's description and you need step-by-step instructions.",
			"Prefer load_skill over re-reading skills/ directories via grep/read — this is the canonical lookup path.",
			"Do not call load_skill for skills you've already loaded this session — your context already has the body.",
		],
		parameters: Type.Object({
			name: Type.String({
				description: "The skill name as it appears in the system prompt (e.g., 'verify-done', 'deep-research', 'commit').",
			}),
		}),
		async execute(_toolCallId, params) {
			const skill = findSkill(params.name);
			if (!skill) {
				const available = listAllSkills()
					.map((s) => s.name)
					.sort()
					.join(", ");
				return {
					content: [
						{
							type: "text",
							text: `Skill "${params.name}" not found. Available skills: ${available || "(none)"}`,
						},
					],
					details: { found: false, requested: params.name },
				};
			}
			const text = readFileSync(skill.path, "utf8");
			return {
				content: [
					{
						type: "text",
						text: `# Skill: ${skill.name}\n\nSource: ${skill.source}\nPath: ${skill.path}\n\n${text}`,
					},
				],
				details: { found: true, path: skill.path, source: skill.source, chars: text.length },
			};
		},
	});

	pi.registerTool({
		name: "list_skills",
		label: "List Skills",
		description:
			"List all available skills (name + description). Use this if the system prompt is missing the skill list, or to discover skills by tag/keyword via grep.",
		promptSnippet: "list_skills(filter?) — enumerate all available skills",
		parameters: Type.Object({
			filter: Type.Optional(
				Type.String({
					description: "Optional substring filter (case-insensitive, matches name or description).",
				}),
			),
		}),
		async execute(_toolCallId, params) {
			const all = listAllSkills().sort((a, b) => a.name.localeCompare(b.name));
			const filter = params.filter?.toLowerCase();
			const matched = filter
				? all.filter((s) => s.name.toLowerCase().includes(filter) || s.description.toLowerCase().includes(filter))
				: all;
			const text = matched.length
				? matched
						.map((s) => `- **${s.name}** (${s.source}, ${s.bodyChars}c) — ${s.description}`)
						.join("\n")
				: "No skills matched.";
			return {
				content: [{ type: "text", text: `${matched.length} skill(s):\n\n${text}` }],
				details: { count: matched.length, total: all.length, filter: filter ?? null },
			};
		},
	});
}
