/**
 * Test utilities for extension behavioral testing.
 *
 * Usage:
 *   import { createMockExtensionAPI } from "./utils.ts";
 *   const { api, ctx } = createMockExtensionAPI();
 *   myExtension(api);
 *   api.verifyToolRegistered("my-tool");
 */

import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";

// Re-export types for convenience
export type { ExtensionAPI, ExtensionContext };

export interface MockCtxOptions {
	cwd?: string;
	model?: { id: string };
	signal?: AbortSignal;
	isIdle?: () => boolean;
	hasUI?: boolean;
}

export function createMockExtensionAPI(opts: MockCtxOptions = {}) {
	// --- Capture state ---
	const registeredTools: Map<string, object> = new Map();
	const registeredCommands: Map<string, object> = new Map();
	const capturedEvents: Map<string, Array<(...args: unknown[]) => void>> = new Map();
	const sessionEntries: Array<{ type: string; data?: unknown }> = [];

	// --- Fake ctx ---
	const fakeCtx: ExtensionContext = {
		ui: {
			notify: (message: string, _type?: string) => {},
			confirm: async () => false,
			input: async () => undefined,
			select: async () => undefined,
			onTerminalInput: () => () => {},
			setStatus: () => {},
			setWorkingMessage: () => {},
			setWorkingVisible: () => {},
			setWorkingIndicator: () => {},
			setHiddenThinkingLabel: () => {},
			setWidget: () => {},
			setFooter: () => {},
			setHeader: () => {},
			setTitle: () => {},
			pasteToEditor: () => {},
			setEditorText: () => {},
			getEditorText: () => "",
			editor: async () => undefined,
			addAutocompleteProvider: () => {},
			setEditorComponent: () => {},
			getEditorComponent: () => undefined,
			theme: { type: "dark" } as any,
			getAllThemes: () => [],
			getTheme: () => undefined,
			setTheme: () => ({ success: false }),
			getToolsExpanded: () => false,
			setToolsExpanded: () => {},
			custom: async (factory: any) => undefined as any,
		},
		mode: "tui",
		hasUI: opts.hasUI ?? true,
		cwd: opts.cwd ?? "/tmp",
		sessionManager: {
			getBranch: () => sessionEntries,
			getEntries: () => sessionEntries,
		} as any,
		modelRegistry: { list: () => [], get: () => undefined } as any,
		model: opts.model ?? { id: "minimax/MiniMax-M2.7" },
		isIdle: opts.isIdle ?? (() => true),
		isProjectTrusted: () => true,
		signal: opts.signal ?? undefined,
		abort: () => {},
		hasPendingMessages: () => false,
		shutdown: () => {},
		getContextUsage: () => ({ tokens: 0, estimatedCost: 0 }),
		compact: () => {},
		getSystemPrompt: () => "",
	};

	// --- Fake ExtensionAPI ---
	const api: ExtensionAPI = {
		on(event: string, handler: (...args: any[]) => void) {
			if (!capturedEvents.has(event)) capturedEvents.set(event, []);
			capturedEvents.get(event)!.push(handler);
		},
		registerTool(toolDef: any) {
			registeredTools.set(toolDef.name, toolDef);
		},
		registerCommand(name: string, def: any) {
			registeredCommands.set(name, def);
		},
		registerShortcut() {},
		registerFlag() {},
		getFlag: () => undefined,
		registerMessageRenderer() {},
		sendMessage() {},
		sendUserMessage() {},
		appendEntry(type: string, data?: unknown) {
			sessionEntries.push({ type, data });
		},
		setSessionName() {},
		getSessionName: () => undefined,
		setLabel() {},
		exec: async () => ({ stdout: "", stderr: "", exitCode: 0, killed: false, durationMs: 0 }),
		getActiveTools: () => [],
		getAllTools: () => [],
		setActiveTools() {},
		getCommands: () => [],
		setModel: async () => true,
		getThinkingLevel: () => "high",
		setThinkingLevel: () => {},
		registerProvider() {},
		unregisterProvider() {},
		events: {
			on: (event: string, handler: (...args: any[]) => void) => {
				if (!capturedEvents.has(event)) capturedEvents.set(event, []);
				capturedEvents.get(event)!.push(handler);
			},
			emit: (_event: string, ..._args: unknown[]) => {},
		} as any,
	};

	// --- Verification helpers ---
	api.verifyToolRegistered = (name: string) => {
		if (!registeredTools.has(name)) {
			throw new Error(`Tool "${name}" not registered. Registered: ${[...registeredTools.keys()].join(", ")}`);
		}
	};

	api.verifyCommandRegistered = (name: string) => {
		if (!registeredCommands.has(name)) {
			throw new Error(`Command "${name}" not registered. Registered: ${[...registeredCommands.keys()].join(", ")}`);
		}
	};

	api.getToolDef = (name: string) => registeredTools.get(name);

	api.triggerEvent = (event: string, ...args: unknown[]) => {
		const handlers = capturedEvents.get(event) ?? [];
		for (const h of handlers) h(...args);
	};

	return { api, ctx: fakeCtx, registeredTools, registeredCommands, capturedEvents, sessionEntries };
}
