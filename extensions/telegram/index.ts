import type { AgentEndEvent, ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { getAgentDir } from "@earendil-works/pi-coding-agent";
import {
	closeSync,
	existsSync,
	openSync,
	readFileSync,
	renameSync,
	unlinkSync,
	writeFileSync,
} from "node:fs";
import { dirname, join } from "node:path";

interface TelegramConfig {
	token: string;
	enabled: boolean;
	lastUpdateId: number;
	allowedUsers: number[];
}

interface TelegramMessage {
	chat: { id: number };
	from?: { id: number };
	text?: string;
}

const stateDir = dirname(getAgentDir());
const configPath = join(stateDir, "telegram-config.json");
const lockPath = join(stateDir, "telegram-poller.lock");
let lockFd: number | undefined;
let abortController: AbortController | undefined;
let activeChatId: number | undefined;
let lastError: string | undefined;

function readConfig(): TelegramConfig | undefined {
	if (!existsSync(configPath)) return undefined;
	return JSON.parse(readFileSync(configPath, "utf8")) as TelegramConfig;
}

function saveConfig(config: TelegramConfig): void {
	const contents = `${JSON.stringify(config, null, 2)}\n`;
	if (process.platform === "win32") {
		// Replacing the file via rename resets its explicit Windows ACL.
		writeFileSync(configPath, contents, { encoding: "utf8", mode: 0o600 });
		return;
	}
	const tempPath = `${configPath}.tmp`;
	writeFileSync(tempPath, contents, { encoding: "utf8", mode: 0o600 });
	renameSync(tempPath, configPath);
}

function acquireLock(): boolean {
	try {
		lockFd = openSync(lockPath, "wx");
		writeFileSync(lockFd, String(process.pid));
		return true;
	} catch {
		try {
			const raw = readFileSync(lockPath, "utf8");
			const pid = Number(raw);
			if (!Number.isInteger(pid) || pid <= 0) throw new Error("invalid lock pid");
			process.kill(pid, 0);
			return false;
		} catch {
			try {
				unlinkSync(lockPath);
			} catch {
				return false;
			}
			return acquireLock();
		}
	}
}

function releaseLock(): void {
	abortController?.abort();
	abortController = undefined;
	if (lockFd !== undefined) {
		closeSync(lockFd);
		lockFd = undefined;
	}
	try {
		unlinkSync(lockPath);
	} catch {
		// Lock already removed.
	}
}

async function telegramApi(config: TelegramConfig, method: string, body?: object): Promise<any> {
	const response = await fetch(`https://api.telegram.org/bot${config.token}/${method}`, {
		method: body ? "POST" : "GET",
		headers: body ? { "content-type": "application/json" } : undefined,
		body: body ? JSON.stringify(body) : undefined,
		signal: abortController?.signal,
	});
	const result = await response.json() as { ok: boolean; description?: string; result?: any };
	if (!result.ok) throw new Error(result.description || `${method} failed`);
	return result.result;
}

async function sendText(config: TelegramConfig, chatId: number, text: string): Promise<void> {
	for (let offset = 0; offset < text.length; offset += 4000) {
		await telegramApi(config, "sendMessage", { chat_id: chatId, text: text.slice(offset, offset + 4000) });
	}
}

function assistantText(event: AgentEndEvent): string {
	const message = [...event.messages].reverse().find((entry: any) => entry.role === "assistant") as any;
	if (!message) return "";
	if (typeof message.content === "string") return message.content;
	if (Array.isArray(message.content)) {
		return message.content
			.filter((part: any) => part?.type === "text" && typeof part.text === "string")
			.map((part: any) => part.text)
			.join("\n");
	}
	return "";
}

async function poll(pi: ExtensionAPI): Promise<void> {
	if (process.env.PI_TELEGRAM_POLLER === "0") return;
	const config = readConfig();
	if (!config?.enabled || !config.token || !acquireLock()) return;
	const controller = new AbortController();
	let consecutiveFailures = 0;
	abortController = controller;

	while (!controller.signal.aborted) {
		try {
			const updates = await telegramApi(
				config,
				`getUpdates?timeout=25&offset=${config.lastUpdateId + 1}&allowed_updates=${encodeURIComponent('["message"]')}`,
			) as Array<{ update_id: number; message?: TelegramMessage }>;
			for (const update of updates) {
				config.lastUpdateId = Math.max(config.lastUpdateId, update.update_id);
				const message = update.message;
				const userId = message?.from?.id;
				if (!message?.text || !userId || !config.allowedUsers.includes(userId)) continue;
				activeChatId = message.chat.id;
				pi.sendUserMessage(`[Telegram user ${userId}] ${message.text}`, { deliverAs: "followUp" });
			}
			if (updates.length) { saveConfig(config); consecutiveFailures = 0; }
		} catch (error) {
			if (controller.signal.aborted) break;
			lastError = error instanceof Error ? error.message : String(error);
			// Exponential backoff capped at 60s
			const delayMs = Math.min(60_000, 2000 * 2 ** consecutiveFailures);
			consecutiveFailures = Math.min(consecutiveFailures + 1, 5);
			await new Promise((resolve) => setTimeout(resolve, delayMs));
		}
	}
}

export default function telegramExtension(pi: ExtensionAPI) {
	pi.on("session_start", () => {
		void poll(pi);
	});

	pi.on("agent_end", async (event) => {
		const config = readConfig();
		const text = assistantText(event);
		if (!config?.enabled || !activeChatId || !text) return;
		try {
			await sendText(config, activeChatId, text);
		} catch (error) {
			lastError = error instanceof Error ? error.message : String(error);
		}
	});

	pi.on("session_shutdown", () => {
		releaseLock();
	});

	pi.registerCommand("telegram", {
		description: "Start the Telegram bridge and show its status",
		handler: async (_args, ctx) => {
			if (lockFd === undefined) void poll(pi);
			await new Promise((resolve) => setTimeout(resolve, 100));
			const config = readConfig();
			const status = config?.enabled
				? `Telegram enabled; poller=${lockFd === undefined ? "standby" : "active"}${lastError ? `; last error=${lastError}` : ""}`
				: "Telegram disabled or not configured";
			ctx.ui.notify(status, "info");
		},
	});
}
