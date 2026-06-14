/**
 * Collector runner — run on every machine.
 *
 * Usage:
 *   node collect-all.mjs              ← all detected collectors
 *   node collect-all.mjs --source pi   ← specific collector only
 *   node collect-all.mjs --dry-run    ← show what would be collected
 *
 * Output: ~/.memory/exports/{source}/{source}_{timestamp}.jsonl
 * Manifest: ~/.memory/exports/manifest_{device}_{timestamp}.json
 */
import path from "node:path";
import os from "node:os";
import fs from "node:fs/promises";
import { getDeviceId, getPlatform } from "./base/platform.mjs";
import { PiCollector } from "./ai/pi.mjs";
import { HermesCollector } from "./ai/hermes.mjs";
import { ClaudeCliCollector } from "./ai/claude-cli.mjs";
import { CodexCollector } from "./ai/codex.mjs";

// ── Collector registry ─────────────────────────────────────────────────────

const collectors = [
	{
		name: "pi",
		create: () => new PiCollector(),
	},
	{
		name: "hermes",
		create: () => new HermesCollector(),
	},
	{
		name: "claude-cli",
		create: () => new ClaudeCliCollector(),
	},
	{
		name: "codex",
		create: () => new CodexCollector(),
	},
	// Add new collectors here:
	// { name: "jcode", create: () => new JcodeCollector() },
	// { name: "kilocode", create: () => new KilocodeCollector() },
];

// ── CLI args ─────────────────────────────────────────────────────────────────

const args = process.argv.slice(2);
const onlySource = args.includes("--source") ? args[args.indexOf("--source") + 1] : null;
const dryRun = args.includes("--dry-run");

// ── Main ─────────────────────────────────────────────────────────────────────

async function main() {
	const deviceId = getDeviceId();
	const platform = getPlatform();
	const homeDir = os.homedir();

	console.log(`\n[memory-collector] device=${deviceId} platform=${platform} home=${homeDir}`);

	const toRun = onlySource
		? collectors.filter((c) => c.name === onlySource)
		: collectors;

	if (onlySource && toRun.length === 0) {
		console.error(`Unknown source: ${onlySource}. Available: ${collectors.map((c) => c.name).join(", ")}`);
		process.exit(1);
	}

	const results = [];

	for (const { name, create } of toRun) {
		console.log(`\n[${name}] scanning...`);
		try {
			const collector = create();
			const sessionFiles = await collector.probe();
			console.log(`[${name}] found ${sessionFiles.length} session files`);

			if (dryRun) {
				for (const f of sessionFiles.slice(0, 5)) {
					console.log(`[${name}]   ${f}`);
				}
				if (sessionFiles.length > 5) {
					console.log(`[${name}]   ... +${sessionFiles.length - 5} more`);
				}
				continue;
			}

			const { collected, newFiles, exportFile } = await collector.run();
			console.log(`[${name}] ${collected} events from ${newFiles} new files → ${exportFile}`);
			results.push({ source: name, collected, exportFile });
		} catch (err) {
			console.error(`[${name}] ERROR: ${err?.message ?? err}`);
		}
	}

	// Summary
	console.log("\n=== Summary ===");
	const total = results.reduce((sum, r) => sum + r.collected, 0);
	if (dryRun) {
		console.log(`Would collect from ${toRun.length} collectors`);
	} else {
		for (const r of results) {
			console.log(`  ${r.source}: ${r.collected} events`);
		}
		console.log(`  total: ${total} events`);
	}

	// Write manifest for hub
	if (!dryRun && total > 0) {
		const manifest = {
			device_id: deviceId,
			platform,
			timestamp: Date.now(),
			exports: results.map((r) => ({
				source: r.source,
				events: r.collected,
				file: r.exportFile,
			})),
		};
		const manifestDir = path.join(homeDir, ".memory", "exports");
		const manifestPath = path.join(manifestDir, `manifest_${deviceId}_${Date.now()}.json`);
		await fs.mkdir(manifestDir, { recursive: true });
		await fs.writeFile(manifestPath, JSON.stringify(manifest, null, 2), "utf8");
		console.log(`\nManifest: ${manifestPath}`);
	}
}

main().catch((err) => {
	console.error("Fatal:", err?.message ?? err);
	process.exit(1);
});
