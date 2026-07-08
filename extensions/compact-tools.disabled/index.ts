/**
 * Compact Tool Renderer - One-liner summaries for tool calls
 *
 * Replaces default tool rendering with minimal one-liners:
 * - read: "read path/to/file (N lines)"
 * - bash: "$ command → done/exit N (N lines)"
 * - edit: "edit path (+N/-N)"
 * - write: "write path (N lines)"
 *
 * Usage:
 *   pi -e ./index.ts
 */

import type { BashToolDetails, EditToolDetails, ExtensionAPI, ReadToolDetails } from "@mariozechner/pi-coding-agent";
import { createBashTool, createEditTool, createReadTool, createWriteTool } from "@mariozechner/pi-coding-agent";
import { Text } from "@mariozechner/pi-tui";

export default function (pi: ExtensionAPI) {
	const cwd = process.cwd();

	// --- Read tool ---
	const originalRead = createReadTool(cwd);
	pi.registerTool({
		name: "read",
		label: "read",
		description: originalRead.description,
		parameters: originalRead.parameters,
		renderShell: "self",
		async execute(toolCallId, params, signal, onUpdate) {
			return originalRead.execute(toolCallId, params, signal, onUpdate);
		},
		renderCall(args, theme) {
			return new Text(theme.fg("toolTitle", `read ${args.path}`), 0, 0);
		},
		renderResult(result, { isPartial }, theme) {
			if (isPartial) return new Text(theme.fg("warning", "Reading..."), 0, 0);
			const content = result.content[0];
			if (content?.type === "image") {
				return new Text(theme.fg("success", "Image loaded"), 0, 0);
			}
			if (content?.type !== "text") {
				return new Text(theme.fg("error", "No content"), 0, 0);
			}
			const lineCount = content.text.split("\n").length;
			const details = result.details as ReadToolDetails | undefined;
			const truncated = details?.truncation?.truncated ? `/${details.truncation.totalLines}` : "";
			return new Text(theme.fg("success", `${lineCount}${truncated} lines`), 0, 0);
		},
	});

	// --- Bash tool ---
	const originalBash = createBashTool(cwd);
	pi.registerTool({
		name: "bash",
		label: "bash",
		description: originalBash.description,
		parameters: originalBash.parameters,
		renderShell: "self",
		async execute(toolCallId, params, signal, onUpdate) {
			return originalBash.execute(toolCallId, params, signal, onUpdate);
		},
		renderCall(args, theme) {
			const cmd = args.command.length > 60 ? `${args.command.slice(0, 57)}...` : args.command;
			return new Text(theme.fg("toolTitle", `$ ${cmd}`), 0, 0);
		},
		renderResult(result, { isPartial }, theme) {
			if (isPartial) return new Text(theme.fg("warning", "Running..."), 0, 0);
			const output = (result.content[0] as any)?.text ?? "";
			const exitMatch = output.match(/exit code: (\d+)/);
			const exitCode = exitMatch ? parseInt(exitMatch[1], 10) : null;
			const lineCount = output.split("\n").filter(l => l.trim()).length;
			const status = exitCode === 0 || exitCode === null ? theme.fg("success", "→ done") : theme.fg("error", `→ exit ${exitCode}`);
			return new Text(`${status}${theme.fg("dim", ` (${lineCount} lines)`)}`, 0, 0);
		},
	});

	// --- Edit tool ---
	const originalEdit = createEditTool(cwd);
	pi.registerTool({
		name: "edit",
		label: "edit",
		description: originalEdit.description,
		parameters: originalEdit.parameters,
		renderShell: "self",
		async execute(toolCallId, params, signal, onUpdate) {
			return originalEdit.execute(toolCallId, params, signal, onUpdate);
		},
		renderCall(args, theme) {
			return new Text(theme.fg("toolTitle", `edit ${args.path}`), 0, 0);
		},
		renderResult(result, { isPartial }, theme) {
			if (isPartial) return new Text(theme.fg("warning", "Editing..."), 0, 0);
			const content = result.content[0];
			if (content?.type === "text" && content.text.startsWith("Error")) {
				return new Text(theme.fg("error", content.text.split("\n")[0]), 0, 0);
			}
			const details = result.details as EditToolDetails | undefined;
			if (!details?.diff) {
				return new Text(theme.fg("success", "Applied"), 0, 0);
			}
			const diffLines = details.diff.split("\n");
			let additions = 0, removals = 0;
			for (const line of diffLines) {
				if (line.startsWith("+") && !line.startsWith("+++")) additions++;
				if (line.startsWith("-") && !line.startsWith("---")) removals++;
			}
			return new Text(`${theme.fg("success", `+${additions}`)}${theme.fg("dim", "/")}${theme.fg("error", `-${removals}`)}`, 0, 0);
		},
	});

	// --- Write tool ---
	const originalWrite = createWriteTool(cwd);
	pi.registerTool({
		name: "write",
		label: "write",
		description: originalWrite.description,
		parameters: originalWrite.parameters,
		renderShell: "self",
		async execute(toolCallId, params, signal, onUpdate) {
			return originalWrite.execute(toolCallId, params, signal, onUpdate);
		},
		renderCall(args, theme) {
			const lines = args.content.split("\n").length;
			return new Text(`${theme.fg("toolTitle", `write ${args.path}`)}${theme.fg("dim", ` (${lines} lines)`)}`, 0, 0);
		},
		renderResult(result, { isPartial }, theme) {
			if (isPartial) return new Text(theme.fg("warning", "Writing..."), 0, 0);
			const content = result.content[0];
			if (content?.type === "text" && content.text.startsWith("Error")) {
				return new Text(theme.fg("error", content.text.split("\n")[0]), 0, 0);
			}
			return new Text(theme.fg("success", "Written"), 0, 0);
		},
	});
}