/**
 * Telegram approval bot — runs on the Linux hub (MacBook Air).
 *
 * Polls for new pending proposals and sends them to the user
 * for approval. Handles [Approve] [Modify] [Dismiss] callbacks.
 *
 * Skills are saved to: ~/.memory/skills/{id}/
 * Skills registry at:   ~/.memory/skills/registry.json
 *
 * Usage:
 *   TELEGRAM_BOT_TOKEN=... node bot.mjs
 *   TELEGRAM_BOT_TOKEN=... node bot.mjs --approve-all  ← for testing
 */
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import crypto from "node:crypto";
import dotenv from "dotenv";
import TelegramBot from "node-telegram-bot-api";

dotenv.config({ path: path.join(os.homedir(), ".memory", ".env") });

const TOKEN = process.env.TELEGRAM_BOT_TOKEN;
if (!TOKEN) {
  console.error("TELEGRAM_BOT_TOKEN not set in ~/.memory/.env");
  process.exit(1);
}

const SKILLS_DIR = path.join(os.homedir(), ".memory", "skills");
const REGISTRY_PATH = path.join(SKILLS_DIR, "registry.json");
const Proposals_PATH = path.join(os.homedir(), ".memory", "hub", "proposals.db");

// ── Skills registry ──────────────────────────────────────────────────────────

function loadRegistry() {
  try {
    return JSON.parse(fs.readFileSync(REGISTRY_PATH, "utf8"));
  } catch {
    return { version: 1, skills: [] };
  }
}

function saveRegistry(registry) {
  fs.mkdirSync(SKILLS_DIR, { recursive: true });
  fs.writeFileSync(REGISTRY_PATH, JSON.stringify(registry, null, 2), "utf8");
}

function approveSkill(proposal) {
  const registry = loadRegistry();
  const skillId = proposal.id;
  const skillDir = path.join(SKILLS_DIR, skillId);
  fs.mkdirSync(skillDir, { recursive: true });

  const skill = {
    id: skillId,
    name: proposal.title,
    description: proposal.description,
    trigger: proposal.trigger,
    steps: proposal.steps,
    pattern: proposal.pattern,
    confidence: proposal.confidence,
    frequency: proposal.frequency,
    sources: proposal.sources,
    approved_at: Date.now(),
    status: "active",
  };

  fs.writeFileSync(
    path.join(skillDir, "SKILL.md"),
    `# ${skill.name}\n\n${skill.description}\n\n## Trigger\n${skill.trigger}\n\n## Steps\n${skill.steps.map((s, i) => `${i + 1}. ${s}`).join("\n")}\n\n---\nApproved automatically via Telegram workflow.\n`
  );

  fs.writeFileSync(
    path.join(skillDir, "SKILL.json"),
    JSON.stringify({ ...skill, skill_dir: skillDir }, null, 2)
  );

  // Update registry
  const existing = registry.skills.findIndex((s) => s.id === skillId);
  if (existing >= 0) {
    registry.skills[existing] = skill;
  } else {
    registry.skills.push(skill);
  }
  saveRegistry(registry);

  return skill;
}

// ── DB helpers ───────────────────────────────────────────────────────────────

function getPendingProposals() {
  // Dynamic import for better-sqlite3
  return import("better-sqlite3").then(({ default: betterSqlite3 }) => {
    const db = betterSqlite3(Proposals_PATH, { readonly: true });
    const rows = db
      .prepare(`SELECT * FROM workflow_proposals WHERE status = 'pending' ORDER BY confidence DESC LIMIT 10`)
      .all();
    db.close();
    return rows;
  });
}

function updateProposalStatus(id, status) {
  return import("better-sqlite3").then(({ default: betterSqlite3 }) => {
    const db = betterSqlite3(Proposals_PATH);
    const now = Date.now();
    if (status === "approved") {
      db.prepare(`UPDATE workflow_proposals SET status = 'approved', approved_at = ? WHERE id = ?`).run(now, id);
    } else if (status === "dismissed") {
      db.prepare(`UPDATE workflow_proposals SET status = 'dismissed', dismissed_at = ? WHERE id = ?`).run(now, id);
    }
    db.close();
  });
}

// ── Bot ─────────────────────────────────────────────────────────────────────

const bot = new TelegramBot(TOKEN, { polling: true });

function formatProposal(row) {
  const steps = JSON.parse(row.steps ?? "[]");
  const sources = JSON.parse(row.sources ?? "[]");
  const devices = JSON.parse(row.devices ?? "[]");

  const confidence = Math.round((row.confidence ?? 0.5) * 100);
  const emoji = confidence >= 80 ? "🟢" : confidence >= 60 ? "🟡" : "🔵";

  let text = `${emoji} *${row.title}*\n`;
  text += `\`\`\`\n${(row.pattern ?? "").slice(0, 80)}\n\`\`\`\n`;
  text += `${row.description}\n\n`;
  text += `📊 confidence=${confidence}% | occurrences=${row.frequency}\n`;
  text += `🔧 sources=${sources.join(", ") || "?"} | devices=${devices.length}\n`;
  text += `\n_${row.trigger}_\n`;

  if (steps.length > 0) {
    text += `\n📋 Steps:\n${steps.map((s) => `  ${s}`).join("\n")}`;
  }

  return text;
}

async function sendProposal(row) {
  const text = formatProposal(row);
  const keyboard = {
    inline_keyboard: [
      [
        { text: "✅ Approve", callback_data: `approve:${row.id}` },
        { text: "✏️ Modify", callback_data: `modify:${row.id}` },
        { text: "❌ Dismiss", callback_data: `dismiss:${row.id}` },
      ],
    ],
  };

  try {
    const msg = await bot.sendMessage(process.env.TELEGRAM_CHAT_ID ?? process.env.TELEGRAM_USER_ID ?? TOKEN.split(":")[0], text, {
      parse_mode: "Markdown",
      reply_markup: keyboard,
      disable_web_page_preview: true,
    });
    return msg.message_id;
  } catch (err) {
    console.error(`[bot] Failed to send message: ${err?.message}`);
    return null;
  }
}

// ── Main loop ────────────────────────────────────────────────────────────────

async function main() {
  fs.mkdirSync(SKILLS_DIR, { recursive: true });

  console.log(`[bot] Starting Telegram workflow bot...`);
  console.log(`[bot] Skills dir: ${SKILLS_DIR}`);

  // Process --approve-all flag
  if (process.argv.includes("--approve-all")) {
    console.log("[bot] --approve-all set: auto-approving all pending proposals");
  }

  bot.on("callback_query", async (query) => {
    const [action, id] = (query.data ?? "").split(":");
    const chatId = query.message?.chat.id;
    const msgId = query.message?.message_id;

    console.log(`[bot] Callback: ${action} ${id}`);

    if (action === "approve") {
      await updateProposalStatus(id, "approved");
      const rows = await getPendingProposals().then((db) => db);
      // Re-fetch the specific row
      const { default: betterSqlite3 } = await import("better-sqlite3");
      const db = betterSqlite3(Proposals_PATH, { readonly: true });
      const row = db.prepare("SELECT * FROM workflow_proposals WHERE id = ?").get(id);
      db.close();
      if (row) {
        const skill = approveSkill(row);
        await bot.answerCallbackQuery(query.id, {
          text: `✅ Skill "${skill.name}" saved! All agents will pull it on next restart.`,
          show_alert: true,
        });
        await bot.editMessageReplyMarkup({ chat_id: chatId, message_id: msgId }, { inline_keyboard: [] });
      }
    } else if (action === "dismiss") {
      await updateProposalStatus(id, "dismissed");
      await bot.answerCallbackQuery(query.id, { text: "Proposal dismissed." });
      await bot.editMessageReplyMarkup({ chat_id: chatId, message_id: msgId }, { inline_keyboard: [] });
    } else if (action === "modify") {
      await bot.answerCallbackQuery(query.id, {
        text: "✏️ Reply to this message with your modified version of the workflow steps.",
        show_alert: true,
      });
    }
  });

  // Polling loop: check for new pending proposals every 60s
  async function poll() {
    try {
      const rows = await getPendingProposals();
      for (const row of rows) {
        if (process.argv.includes("--approve-all")) {
          await updateProposalStatus(row.id, "approved");
          approveSkill(row);
          console.log(`[bot] Auto-approved: ${row.title}`);
        } else {
          const msgId = await sendProposal(row);
          if (msgId) {
            console.log(`[bot] Sent proposal: ${row.title} (msg_id=${msgId})`);
          }
        }
      }
      if (rows.length === 0) {
        console.log(`[bot] No pending proposals. Waiting...`);
      }
    } catch (err) {
      console.error(`[bot] Poll error: ${err?.message}`);
    }
  }

  await poll();
  setInterval(poll, 60_000);
}

main().catch((err) => {
  console.error("Fatal:", err?.message ?? err);
  process.exit(1);
});
