/**
 * Telegram Extension - Bridges Telegram bot messages to the pi agent
 *
 * Architecture (based on OpenClaw):
 * - Uses long polling via getUpdates API
 * - Maps Telegram chat IDs to agent sessions
 * - Delivers messages via sendUserMessage (steer mode)
 * - Responses are sent back via sendMessage after agent completes
 * - Typing indicator shown while agent is processing
 *
 * Usage:
 *   /telegram set <token>        — configure bot token
 *   /telegram clear               — remove configuration
 *   /telegram status              — show connection status
 */

import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";
import { existsSync, readFileSync, writeFileSync, mkdirSync } from "node:fs";
import path from "node:path";
import os from "node:os";

const TELEGRAM_CONFIG_FILE = path.join(os.homedir(), ".pi", "telegram-config.json");

interface TelegramConfig {
  token: string;
  enabled: boolean;
  lastUpdateId?: number;
  chatId?: number;
  allowedUsers?: number[];
}

interface TelegramUpdate {
  update_id: number;
  message?: {
    message_id: number;
    chat: { id: number; type: string };
    text?: string;
    from?: { id: number; first_name: string; username?: string };
  };
}

let config: TelegramConfig | null = null;
let pollInterval: ReturnType<typeof setInterval> | null = null;
let typingInterval: ReturnType<typeof setInterval> | null = null;

function getConfigPath(): string {
  return TELEGRAM_CONFIG_FILE;
}

function loadConfig(): TelegramConfig | null {
  try {
    if (existsSync(getConfigPath())) {
      return JSON.parse(readFileSync(getConfigPath(), "utf8"));
    }
  } catch {
    // ignore
  }
  return null;
}

function saveConfig(cfg: TelegramConfig): void {
  const dir = path.dirname(getConfigPath());
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true });
  }
  writeFileSync(getConfigPath(), JSON.stringify(cfg, null, 2), "utf8");
}

async function apiRequest(method: string, body?: Record<string, unknown>): Promise<unknown> {
  if (!config?.token) {
    throw new Error("No token configured");
  }

  const postData = body ? JSON.stringify(body) : "";
  const options = {
    hostname: "api.telegram.org",
    path: `/bot${config.token}/${method}`,
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Content-Length": Buffer.byteLength(postData),
    },
  };

  return new Promise((resolve, reject) => {
    const req = require("node:https").request(options, (res: { on: Function }) => {
      let data = "";
      res.on("data", (chunk: string) => (data += chunk));
      res.on("end", () => {
        try {
          resolve(JSON.parse(data));
        } catch {
          resolve({ ok: false });
        }
      });
    });
    req.on("error", reject);
    if (body) req.write(postData);
    req.end();
  });
}

async function getUpdates(offset: number): Promise<{ ok: boolean; result?: TelegramUpdate[] }> {
  return apiRequest("getUpdates", { offset, timeout: 5, allowed_updates: ["message"] }) as Promise<{ ok: boolean; result?: TelegramUpdate[] }>;
}

async function sendChatAction(action: string): Promise<void> {
  if (!config?.chatId) return;
  await apiRequest("sendChatAction", { chat_id: config.chatId, action });
}

async function sendTypingIndicator(): Promise<void> {
  await sendChatAction("typing");
}

async function sendMessage(text: string, replyToMessageId?: number): Promise<void> {
  if (!config?.chatId) {
    throw new Error("No chat ID known");
  }

  const body: Record<string, unknown> = { chat_id: config.chatId, text };
  if (replyToMessageId) {
    body.reply_to_message_id = replyToMessageId;
  }
  await apiRequest("sendMessage", body);
}

async function getMe(): Promise<{ ok: boolean; result?: { id: number; first_name: string; username: string } }> {
  return apiRequest("getMe") as Promise<{ ok: boolean; result?: { id: number; first_name: string; username: string } }>;
}

async function processUpdates(updates: TelegramUpdate[]): Promise<void> {
  for (const update of updates) {
    if (!update.message?.text || !update.message?.chat) continue;

    const msg = update.message;
    const chatId = msg.chat.id;
    const userId = msg.from?.id;
    const text = msg.text?.trim();
    if (!text) continue;

    // Store chat ID for responses
    if (config) {
      config.chatId = chatId;
      saveConfig(config);
    }

    // Security: check allowed users
    if (userId && config?.allowedUsers && config.allowedUsers.length > 0) {
      if (!config.allowedUsers.includes(userId)) {
        console.log(`[Telegram] Rejected unauthorized user: ${userId}`);
        await sendMessage("⛔ Access denied.");
        continue;
      }
    }

    console.log(`[Telegram] Message from ${msg.from?.first_name}: ${text}`);

    // Show typing indicator immediately
    await sendTypingIndicator();

    // Deliver message to pi agent via steer
    const senderName = msg.from?.first_name ?? "Telegram";
    const formattedMessage = `[Telegram:${senderName}] ${text}`;

    // Use sendUserMessage with triggerTurn to get a response
    pi.sendUserMessage(formattedMessage, { deliverAs: "steer", triggerTurn: true });
  }
}

async function poll(): Promise<void> {
  if (!config?.token || !config?.enabled) return;

  try {
    const offset = (config.lastUpdateId ?? 0) + 1;
    const response = await getUpdates(offset);

    if (!response.ok || !response.result || response.result.length === 0) {
      return;
    }

    // Process all pending updates
    await processUpdates(response.result);

    // Update offset to avoid reprocessing
    const maxUpdateId = Math.max(...response.result.map((u) => u.update_id));
    if (config) {
      config.lastUpdateId = maxUpdateId;
      saveConfig(config);
    }
  } catch (error) {
    console.error("[Telegram] Poll error:", error);
  }
}

function startPolling(): void {
  if (pollInterval) return;

  console.log("[Telegram] Starting poll loop...");
  poll(); // Initial poll
  pollInterval = setInterval(poll, 1000);
}

function stopPolling(): void {
  if (pollInterval) {
    clearInterval(pollInterval);
    pollInterval = null;
  }
  stopTypingIndicator();
}

function startTypingIndicator(): void {
  if (typingInterval) return;
  // Send typing every 3 seconds to keep the indicator showing
  typingInterval = setInterval(() => {
    if (config?.chatId) {
      sendTypingIndicator().catch(() => {});
    }
  }, 3000);
}

function stopTypingIndicator(): void {
  if (typingInterval) {
    clearInterval(typingInterval);
    typingInterval = null;
  }
}

export default function telegramExtension(pi: ExtensionAPI) {
  console.log("[Telegram] Extension loading...");
  config = loadConfig();

  // Handle agent responses - send back to Telegram
  pi.on("agent_end", async (_event, ctx) => {
    // Stop typing indicator when agent finishes
    stopTypingIndicator();

    if (!config?.token || !config?.enabled || !config.chatId) return;

    // Get the last assistant response
    const branch = ctx.sessionManager.getBranch();
    let lastResponse = "";

    for (let i = branch.length - 1; i >= 0; i--) {
      const entry = branch[i];
      if (entry.type === "message") {
        const msg = entry.message;
        if ("role" in msg && msg.role === "assistant") {
          const textParts = (msg.content as Array<{ type: string; text: string }>)
            .filter((c) => c.type === "text")
            .map((c) => c.text);
          if (textParts.length > 0) {
            lastResponse = textParts.join("\n");
            break;
          }
        }
      }
    }

    if (!lastResponse) return;

    // Send response back to Telegram
    try {
      await sendMessage(lastResponse);
      console.log(`[Telegram] Response sent (${lastResponse.length} chars)`);
    } catch (error) {
      console.error("[Telegram] Failed to send response:", error);
    }
  });

  // Start typing indicator when agent starts processing
  pi.on("agent_start", async () => {
    startTypingIndicator();
  });

  // Register /telegram command
  pi.registerCommand("telegram", {
    description: "Configure and control Telegram bot integration",
    usage: "/telegram <set|clear|status>",
    handler: async (args, ctx) => {
      const parts = args.trim().split(/\s+/);
      const subcommand = parts[0]?.toLowerCase();

      switch (subcommand) {
        case "set": {
          const token = parts[1]?.trim();
          if (!token) {
            await ctx.ui?.notify("Usage: /telegram set <token>", "error");
            return;
          }

          const me = await getMe();
          if (!me.ok || !me.result) {
            await ctx.ui?.notify(`Invalid token: ${(me as any).description ?? "error"}`, "error");
            return;
          }

          config = {
            token,
            enabled: true,
            lastUpdateId: 0,
            allowedUsers: [7635598213], // Xenmasta's user ID
          };
          saveConfig(config);
          startPolling();

          await ctx.ui?.notify(`Bot @${me.result.username} connected!`, "success", { duration: 3000 });
          break;
        }

        case "clear": {
          stopPolling();
          config = null;
          if (existsSync(getConfigPath())) {
            writeFileSync(getConfigPath(), "", "utf8");
          }
          await ctx.ui?.notify("Telegram disconnected", "info", { duration: 2000 });
          break;
        }

        case "status": {
          if (!config?.token) {
            await ctx.ui?.notify("Not configured", "info");
            return;
          }

          const me = await getMe();
          const polling = pollInterval ? "Polling" : "Stopped";
          await ctx.ui?.notify(
            `Bot: @${me.result?.username ?? "?"} | ${polling}`,
            "success",
            { duration: 3000 }
          );
          break;
        }

        default:
          await ctx.ui?.notify("Usage: /telegram <set|clear|status>", "error");
      }
    }
  });

  // Start polling if we have a saved config
  if (config?.token && config?.enabled) {
    startPolling();
  }
}
