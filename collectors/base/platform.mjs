/**
 * Platform detection and path utilities.
 * Runs on: Node.js (Windows, Linux, macOS).
 */
import os from "node:os";
import path from "node:path";
import fsSync from "node:fs";

export function getPlatform() {
	const p = process.platform;
	if (p === "win32") return "windows";
	if (p === "linux") return "linux";
	if (p === "darwin") return "darwin";
	throw new Error(`Unsupported platform: ${p}`);
}

export function getHomeDir() {
	return os.homedir();
}

/**
 * Resolve ~ and %USERPROFILE% in paths.
 */
export function resolvePath(template) {
	if (!template) return template;
	if (template.startsWith("~")) {
		return path.join(os.homedir(), template.slice(1));
	}
	if (getPlatform() === "windows" && template.includes("%USERPROFILE%")) {
		return template.replace(/%USERPROFILE%/gi, os.homedir());
	}
	return template;
}

/**
 * Recursively find all files with a given extension in a directory.
 */
export async function findFiles(dir, { ext = ".jsonl", recursive = true } = {}) {
	const results = [];

	async function walk(current) {
		let entries;
		try {
			entries = await fsSync.promises.readdir(current, { withFileTypes: true });
		} catch {
			return;
		}
		for (const entry of entries) {
			const full = path.join(current, entry.name);
			if (entry.isDirectory() && recursive) {
				await walk(full);
			} else if (entry.isFile() && entry.name.endsWith(ext)) {
				results.push(full);
			}
		}
	}

	await walk(dir);
	results.sort();
	return results;
}

/**
 * Stable device ID: hostname + platform.
 */
export function getDeviceId() {
	const hostname = os.hostname();
	const platform = getPlatform();
	const safe = hostname.replace(/[^a-zA-Z0-9_-]/g, "-").toLowerCase();
	return `${platform}-${safe}`;
}
