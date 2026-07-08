import { existsSync } from "node:fs";
import { join } from "node:path";

export interface PiEntry {
	command: string;
	prefixArgs: string[];
}

export function resolvePiEntry(additionalCandidates?: string[]): PiEntry | null {
	const baseCandidates = [
		join(process.env.APPDATA || "", "npm", "node_modules", "@earendil-works", "pi-coding-agent", "dist", "cli.js"),
		join(process.env.HOME || "", ".bun", "install", "global", "node_modules", "@earendil-works", "pi-coding-agent", "dist", "cli.js"),
		join(process.cwd(), "node_modules", "@earendil-works", "pi-coding-agent", "dist", "cli.js"),
	];
	const candidates = additionalCandidates?.length ? [...baseCandidates, ...additionalCandidates] : baseCandidates;
	for (const c of candidates) {
		if (c && existsSync(c)) return { command: process.execPath, prefixArgs: [c] };
	}
	return null;
}
