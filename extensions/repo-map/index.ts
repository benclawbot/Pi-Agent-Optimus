/**
 * repo_map Tool
 *
 * Build a lightweight file→symbol graph of the current repo and return
 * the highest-signal symbols for a given seed file or query. Implements
 * Aider's "repo map" pattern: the model "sees" the codebase without
 * reading it. No LLM in the loop — pure TypeScript parsing of JS/TS/Py
 * plus import-graph ranking.
 *
 * Strategy:
 *  1. Walk cwd, skip node_modules, .git, dist, build, coverage
 *  2. Extract imports/requires + exported symbols per file
 *  3. Build undirected dependency graph
 *  4. For a seed file: BFS-expand with decay (closer = higher weight)
 *  5. For a query string: text-match on path or symbol name
 *  6. Render top-N symbols in `path | export | sig` format
 *
 * Cost: ~100-300ms for a 1000-file repo. No subprocess.
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { readFileSync, readdirSync, statSync, existsSync } from "node:fs";
import { join, relative, sep, basename, extname, dirname } from "node:path";

const SKIP_DIRS = new Set([
	"node_modules",
	".git",
	"dist",
	"build",
	"coverage",
	".next",
	".nuxt",
	".cache",
	".pi",
	".agents",
	"__pycache__",
	".venv",
	"venv",
	".tox",
	"target",
	"vendor",
]);

const CODE_EXTS = new Set([
	".ts",
	".tsx",
	".js",
	".jsx",
	".mjs",
	".cjs",
	".py",
	".go",
	".rs",
	".java",
	".rb",
]);

interface FileNode {
	path: string; // relative
	imports: Set<string>; // relative imports
	exports: string[]; // top-level exported symbols
	hashes: Set<string>; // imported relative paths
}

interface Graph {
	files: Map<string, FileNode>;
	bySymbol: Map<string, string[]>; // symbol name → files exporting it
}

function walkFiles(root: string, maxFiles = 5000): string[] {
	const out: string[] = [];
	const stack: string[] = [root];
	while (stack.length && out.length < maxFiles) {
		const dir = stack.pop()!;
		let entries: string[];
		try {
			entries = readdirSync(dir);
		} catch {
			continue;
		}
		for (const e of entries) {
			if (SKIP_DIRS.has(e)) continue;
			const full = join(dir, e);
			let isDir = false;
			let isFile = false;
			try {
				const s = statSync(full);
				isDir = s.isDirectory();
				isFile = s.isFile();
			} catch {
				continue;
			}
			if (isDir) {
				stack.push(full);
			} else if (isFile && CODE_EXTS.has(extname(e))) {
				out.push(relative(root, full).split(sep).join("/"));
			}
		}
	}
	return out;
}

function extractImports(content: string, ext: string, relPath: string): string[] {
	const out = new Set<string>();
	// Strip line comments to avoid matching commented-out imports
	const clean = content
		.replace(/\/\/[^\n]*/g, "")
		.replace(/\/\*[\s\S]*?\*\//g, "");
	const dir = dirname(relPath);
	if (ext === ".ts" || ext === ".tsx" || ext === ".js" || ext === ".jsx" || ext === ".mjs" || ext === ".cjs") {
		// import ... from "..."
		const reImport = /(?:^|\n)\s*(?:import\s+(?:[^'"`;]+\s+from\s+)?|export\s+(?:[^'"`;]+\s+from\s+)?|require\(\s*\))\s*['"]([^'"]+)['"]/g;
		let m: RegExpExecArray | null;
		while ((m = reImport.exec(clean))) {
			const spec = m[1];
			if (spec.startsWith(".")) {
				for (const abs of normalizeImport(spec, dir)) out.add(abs);
			}
		}
		// dynamic import()
		const reDyn = /import\(\s*['"]([^'"]+)['"]\s*\)/g;
		while ((m = reDyn.exec(clean))) {
			if (m[1].startsWith(".")) {
				for (const abs of normalizeImport(m[1], dir)) out.add(abs);
			}
		}
	} else if (ext === ".py") {
		const reFrom = /^\s*from\s+([.\w]+)\s+import\s+/gm;
		let m: RegExpExecArray | null;
		while ((m = reFrom.exec(clean))) {
			const spec = m[1];
			if (spec.startsWith(".")) {
				for (const abs of normalizeImport(spec.replace(/\./g, "/"), dir)) out.add(abs);
			}
		}
		const reImp = /^\s*import\s+([.\w]+)/gm;
		while ((m = reImp.exec(clean))) {
			if (m[1].startsWith(".")) {
				for (const abs of normalizeImport(m[1].replace(/\./g, "/"), dir)) out.add(abs);
			}
		}
	}
	return [...out];
}

function normalizeImport(spec: string, fromDir: string): string[] {
	// strip query/hash, build candidate paths
	const clean = spec.split("?")[0].split("#")[0];
	const candidates: string[] = [];
	if (clean.endsWith("/")) {
		for (const ext of [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".py"]) {
			candidates.push(clean + "index" + ext);
		}
	} else {
		for (const ext of [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".py", ""]) {
			candidates.push(clean + ext);
		}
	}
	// Resolve against fromDir, normalize to forward slashes
	return candidates.map((c) => join(fromDir, c).split(sep).join("/"));
}

function extractExports(content: string, ext: string): string[] {
	const out: string[] = [];
	// Strip comments to avoid matching `// export class Foo` etc.
	const clean = content
		.replace(/\/\/[^\n]*/g, "")
		.replace(/\/\*[\s\S]*?\*\//g, "");
	if (ext === ".ts" || ext === ".tsx" || ext === ".js" || ext === ".jsx" || ext === ".mjs" || ext === ".cjs") {
		// export class Foo / function foo / const foo / interface Foo / type Foo
		const re = /export\s+(?:default\s+)?(?:async\s+)?(?:class|function|const|let|var|interface|type|enum)\s+([A-Za-z_$][\w$]*)/g;
		let m: RegExpExecArray | null;
		while ((m = re.exec(clean))) {
			out.push(m[1]);
		}
		// export { a, b, c }
		const reNamed = /export\s*\{([^}]+)\}/g;
		while ((m = reNamed.exec(clean))) {
			for (const sym of m[1].split(",")) {
				const name = sym.trim().split(/\s+as\s+/)[0];
				if (name && /^[A-Za-z_$]/.test(name)) out.push(name);
			}
		}
	} else if (ext === ".py") {
		const re = /^def\s+([A-Za-z_]\w*)|^class\s+([A-Za-z_]\w*)/gm;
		let m: RegExpExecArray | null;
		while ((m = re.exec(clean))) {
			out.push(m[1] || m[2]);
		}
	}
	return [...new Set(out)];
}

function buildGraph(root: string, files: string[]): Graph {
	const g: Graph = { files: new Map(), bySymbol: new Map() };
	// Normalize file paths to forward slashes so they match import resolutions
	const filesNorm = files.map((f) => f.split(sep).join("/"));
	const fileSet = new Set(filesNorm);

	// First pass: imports + exports
	for (const rel of files) {
		const ext = extname(rel);
		const full = join(root, rel);
		let content: string;
		try {
			content = readFileSync(full, "utf8");
		} catch {
			continue;
		}
		if (content.length > 1_000_000) continue; // skip huge files
		const imports = extractImports(content, ext, rel);
		const exports = extractExports(content, ext);
		const node: FileNode = {
			path: rel,
			imports: new Set(imports),
			exports,
			hashes: new Set(),
		};
		g.files.set(rel, node);
		for (const sym of exports) {
			const list = g.bySymbol.get(sym) ?? [];
			list.push(rel);
			g.bySymbol.set(sym, list);
		}
	}

	// Second pass: resolve imports to actual file paths
	for (const [rel, node] of g.files) {
		for (const imp of node.imports) {
			// imp is forward-slash-normalized and may already be in the file set
			// (since extractImports uses join(dir, spec) which is relative to root).
			let resolved: string | null = null;
			// Direct hit
			if (fileSet.has(imp)) {
				resolved = imp;
			} else {
				// Try without/with extensions
				for (const ext of [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".py"]) {
					if (fileSet.has(imp + ext)) {
						resolved = imp + ext;
						break;
					}
				}
				// Try index
				if (!resolved) {
					for (const ext of [".ts", ".tsx", ".js", ".jsx"]) {
						if (fileSet.has(imp + "/index" + ext)) {
							resolved = imp + "/index" + ext;
							break;
						}
					}
				}
			}
			if (resolved) node.hashes.add(resolved);
		}
	}

	return g;
}

interface RankedFile {
	path: string;
	score: number;
	exports: string[];
	imports: number;
}

function rankBySeed(g: Graph, seed: string, depth = 2, decay = 0.5): RankedFile[] {
	const scores = new Map<string, number>();
	const visited = new Set<string>();
	const queue: Array<{ path: string; d: number }> = [{ path: seed, d: 0 }];
	while (queue.length) {
		const { path, d } = queue.shift()!;
		if (visited.has(path) || d > depth) continue;
		visited.add(path);
		const weight = Math.pow(decay, d);
		scores.set(path, (scores.get(path) ?? 0) + weight);
		const node = g.files.get(path);
		if (!node) continue;
		for (const imp of node.hashes) {
			if (!visited.has(imp)) queue.push({ path: imp, d: d + 1 });
		}
		// Backlinks (files that import this one)
		for (const [other, otherNode] of g.files) {
			if (otherNode.hashes.has(path) && !visited.has(other)) {
				queue.push({ path: other, d: d + 1 });
			}
		}
	}
	return scoresToRanked(g, scores);
}

function rankBySymbol(g: Graph, query: string, limit = 50): RankedFile[] {
	const q = query.toLowerCase();
	const scores = new Map<string, number>();
	// Match by symbol name
	for (const [sym, files] of g.bySymbol) {
		if (sym.toLowerCase().includes(q)) {
			for (const f of files) {
				scores.set(f, (scores.get(f) ?? 0) + 2.0);
			}
		}
	}
	// Match by path
	for (const path of g.files.keys()) {
		if (path.toLowerCase().includes(q)) {
			scores.set(path, (scores.get(path) ?? 0) + 1.0);
		}
	}
	return scoresToRanked(g, scores).slice(0, limit);
}

function scoresToRanked(g: Graph, scores: Map<string, number>): RankedFile[] {
	const out: RankedFile[] = [];
	for (const [path, score] of scores) {
		const node = g.files.get(path)!;
		out.push({
			path,
			score,
			exports: node.exports.slice(0, 6),
			imports: node.hashes.size,
		});
	}
	out.sort((a, b) => b.score - a.score || a.path.localeCompare(b.path));
	return out;
}

function renderRepoMap(root: string, files: string[], ranked: RankedFile[], total: number): string {
	const lines: string[] = [];
	lines.push(`# Repo Map: ${root} (${total} source files, top ${ranked.length} shown)`);
	lines.push("");
	lines.push("```");
	lines.push("path | exports | imports");
	for (const r of ranked) {
		const ex = r.exports.length ? r.exports.join(", ") : "—";
		lines.push(`${r.path} | ${ex} | in:${r.imports}`);
	}
	lines.push("```");
	return lines.join("\n");
}

export default function repoMapExtension(pi: ExtensionAPI) {
	pi.registerTool({
		name: "repo_map",
		label: "Repo Map",
		description:
			"Build a dependency-graph 'repo map' of the current project and return the highest-signal files for a given seed or query. Implements Aider's repo-map pattern: gives the model the most relevant ~1-2k tokens of a codebase without reading the whole thing. Use this BEFORE reading files when you need to understand an unfamiliar codebase, or when the user asks you to find where something is defined.",
		promptSnippet: "repo_map(seed?, query?, limit?) — get the highest-signal files of the project",
		promptGuidelines: [
			"Call repo_map at the start of any task in an unfamiliar codebase.",
			"Use seed=<relative_file_path> to expand around a file you already know.",
			"Use query=<symbol_or_path_substring> to search across the project.",
			"Use limit=N to control output size (default 30, max 100).",
			"After repo_map, read only the top-ranked files, not the whole tree.",
		],
		parameters: Type.Object({
			seed: Type.Optional(
				Type.String({
					description: "Relative file path to expand the graph around (e.g., 'src/index.ts').",
				}),
			),
			query: Type.Optional(
				Type.String({
					description: "Substring to match against symbol names and file paths (case-insensitive).",
				}),
			),
			limit: Type.Optional(
				Type.Number({
					description: "Max files to return (default 30, max 100).",
					default: 30,
				}),
			),
			max_files: Type.Optional(
				Type.Number({
					description: "Cap on files walked (default 2000).",
					default: 2000,
				}),
			),
		}),
		async execute(_toolCallId, params) {
			const root = process.cwd();
			const maxFiles = params.max_files ?? 2000;
			const limit = Math.min(100, Math.max(1, params.limit ?? 30));

			const files = walkFiles(root, maxFiles);
			if (files.length === 0) {
				return {
					content: [{ type: "text", text: `No source files found under ${root}.` }],
					details: { files: 0 },
				};
			}

			const t0 = Date.now();
			const g = buildGraph(root, files);
			const buildMs = Date.now() - t0;

			let ranked: RankedFile[];
			if (params.seed) {
				const seed = params.seed.replace(/^[/\\]/, "").split(sep).join("/");
				if (!g.files.has(seed)) {
					return {
						content: [{ type: "text", text: `Seed file not found: ${seed}\n\nDid you mean one of:\n${files.slice(0, 10).map((f) => "  " + f).join("\n")}` }],
						details: { files: files.length, seed, found: false },
					};
				}
				ranked = rankBySeed(g, seed, 2, 0.5).slice(0, limit);
			} else if (params.query) {
				ranked = rankBySymbol(g, params.query, limit);
			} else {
				// No seed, no query → return by graph centrality (most-imported files)
				const scores = new Map<string, number>();
				for (const [path, node] of g.files) {
					scores.set(path, 0);
					for (const imp of node.hashes) {
						scores.set(imp, (scores.get(imp) ?? 0) + 1);
					}
				}
				ranked = scoresToRanked(g, scores).slice(0, limit);
			}

			const text = renderRepoMap(root, files, ranked, files.length);
			return {
				content: [{ type: "text", text }],
				details: {
					files: files.length,
					ranked: ranked.length,
					buildMs,
					seed: params.seed ?? null,
					query: params.query ?? null,
				},
			};
		},
	});
}
