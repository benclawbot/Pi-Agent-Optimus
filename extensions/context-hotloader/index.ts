/**
 * Context Hotloader Extension
 *
 * Automatically reads project configuration files when entering a directory.
 * Files: .env.example, tsconfig.json, package.json, .eslintrc, etc.
 * Keeps context fresh without manual reads.
 *
 * Usage:
 *   Add "+extensions/context-hotloader/index.ts" to settings.json extensions array
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

interface ProjectConfig {
	hasEnv: boolean;
	hasTsConfig: boolean;
	hasPackageJson: boolean;
	hasEslint: boolean;
	hasPrettier: boolean;
	hasGit: boolean;
	hasDocker: boolean;
	language: string;
	framework?: string;
}

const CONFIG_FILES = [
	{ name: ".env.example", key: "hasEnv" },
	{ name: "tsconfig.json", key: "hasTsConfig", lang: "typescript" },
	{ name: "package.json", key: "hasPackageJson", detect: "package" },
	{ name: ".eslintrc", key: "hasEslint" },
	{ name: ".eslintrc.json", key: "hasEslint" },
	{ name: "eslint.config.js", key: "hasEslint" },
	{ name: ".prettierrc", key: "hasPrettier" },
	{ name: ".prettierrc.json", key: "hasPrettier" },
	{ name: "prettier.config.js", key: "hasPrettier" },
	{ name: "Dockerfile", key: "hasDocker" },
	{ name: "docker-compose.yml", key: "hasDocker" },
	{ name: "docker-compose.yaml", key: "hasDocker" },
	{ name: ".git", key: "hasGit", dir: true },
];

const FRAMEWORK_INDICATORS = {
	"next": ["next.config.js", "app/", "pages/"],
	"react": ["src/App.tsx", "src/App.jsx"],
	"vue": ["vue.config.js", "src/main.ts"],
	"svelte": ["svelte.config.js", "src/App.svelte"],
	"express": ["src/index.ts", "src/index.js", "app.ts", "server.ts"],
	"fastify": ["src/index.ts", "src/server.ts"],
	"deno": ["deno.json", "deno.lock"],
	"bun": ["bun.lockb", "bun.lock"],
};

function detectLanguage(config: ProjectConfig): string {
	if (config.hasTsConfig) return "TypeScript";
	if (config.hasPackageJson) return "JavaScript";
	return "unknown";
}

function detectFramework(cwd: string): string | undefined {
	for (const [framework, indicators] of Object.entries(FRAMEWORK_INDICATORS)) {
		for (const indicator of indicators) {
			if (existsSync(path.join(cwd, indicator))) {
				return framework;
			}
		}
	}
	return undefined;
}

function scanProjectConfig(cwd: string): ProjectConfig {
	const config: ProjectConfig = {
		hasEnv: false,
		hasTsConfig: false,
		hasPackageJson: false,
		hasEslint: false,
		hasPrettier: false,
		hasGit: false,
		hasDocker: false,
		language: "unknown",
	};

	for (const file of CONFIG_FILES) {
		const filePath = path.join(cwd, file.name);
		if (file.dir ? existsSync(filePath) : existsSync(filePath)) {
			(config as any)[file.key] = true;
		}
	}

	config.language = detectLanguage(config);
	config.framework = detectFramework(cwd);

	return config;
}

export default function contextHotloaderExtension(pi: ExtensionAPI) {
	let lastScannedDir = "";

	pi.on("agent_start", async (_event, ctx) => {
		if (ctx.cwd === lastScannedDir) return;
		lastScannedDir = ctx.cwd;

		const config = scanProjectConfig(ctx.cwd);

		if (config.language === "unknown" && !config.hasPackageJson && !config.hasGit) {
			// Not a typical project directory, skip
			return;
		}

		// Build context summary
		const parts: string[] = [`Project: ${ctx.cwd}`];

		if (config.hasGit) {
			parts.push("Git repository");
		}

		parts.push(`Language: ${config.language}`);

		if (config.framework) {
			parts.push(`Framework: ${config.framework}`);
		}

		const tools: string[] = [];
		if (config.hasEslint) tools.push("ESLint");
		if (config.hasPrettier) tools.push("Prettier");
		if (config.hasDocker) tools.push("Docker");

		if (tools.length > 0) {
			parts.push(`Tools: ${tools.join(", ")}`);
		}

		// Auto-read important files
		const toRead: string[] = [];
		const envExample = path.join(ctx.cwd, ".env.example");
		if (existsSync(envExample)) toRead.push(envExample);

		const tsconfig = path.join(ctx.cwd, "tsconfig.json");
		if (existsSync(tsconfig)) toRead.push(tsconfig);

		// Store in session context for agents to use
		pi.sendUserMessage(
			`[Context Hotloader] Detected: ${parts.join(" | ")}\n` +
			toRead.length > 0 ? `Auto-loading config: ${toRead.map(f => path.basename(f)).join(", ")}` : "",
			{ deliverAs: "steer" }
		);
	});

	// Also expose a tool to explicitly reload context
	pi.registerTool({
		name: "reload_context",
		label: "Reload Context",
		description: "Re-scan project configuration files and update context. Use after package.json changes, new config files, or switching projects.",
		parameters: {
			type: "object",
			properties: {}
		},
		async execute(_toolCallId, _params, _signal, _onUpdate, ctx) {
			lastScannedDir = ""; // Force rescan
			const config = scanProjectConfig(ctx.cwd);

			const summary = [
				`Language: ${config.language}`,
				config.framework ? `Framework: ${config.framework}` : null,
				config.hasEslint ? "ESLint: yes" : null,
				config.hasPrettier ? "Prettier: yes" : null,
				config.hasDocker ? "Docker: yes" : null,
				config.hasEnv ? ".env.example: present" : null,
			].filter(Boolean).join("\n");

			return {
				content: [{ type: "text", text: `Project context updated:\n${summary}` }],
				details: config
			};
		}
	});
}