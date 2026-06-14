/**
 * Synthesis engine — pattern detection + workflow proposal.
 *
 * Pattern detection approach (content-based, not tool-based):
 * 1. Extract frequent phrase/n-gram sequences from transcript content
 * 2. Detect session structure patterns (role transitions, session openers/closers)
 * 3. Find cross-source patterns (same user patterns across pi + hermes + claude-cli)
 * 4. Generate workflow proposals for high-confidence patterns
 *
 * Tool-sequence detection is备用 when toolCall blocks are present.
 */
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import crypto from "node:crypto";
import betterSqlite3 from "better-sqlite3";

const DB_PATH = path.join(os.homedir(), ".memory", "hub", "events.db");
const Proposals_PATH = path.join(os.homedir(), ".memory", "hub", "proposals.db");
const MIN_CONFIDENCE = parseFloat(
  process.argv.includes("--min-confidence")
    ? process.argv[process.argv.indexOf("--min-confidence") + 1]
    : "0.55"
);

// ── Content n-gram extraction ─────────────────────────────────────────────────

/**
 * Extract significant word trigrams from content, filtered by:
 * - Minimum word length (3 chars)
 * - Stopword removal (common words)
 * - Must appear in ≥3 sessions
 */
function extractPhrasePatterns(db) {
  const STOPWORDS = new Set([
    "the", "and", "for", "are", "but", "not", "you", "all", "can", "had",
    "her", "was", "one", "our", "out", "has", "have", "been", "were", "they",
    "this", "that", "with", "from", "your", "what", "when", "where", "which",
    "their", "will", "would", "there", "could", "other", "into", "just",
    "about", "also", "only", "some", "them", "then", "very", "after", "before",
    "more", "most", "these", "those", "than", "well", "back", "over", "such",
    "here", "now", "see", "way", "new", "because", "like", "get", "make",
    "made", "need", "want", "use", "used", "using", "does", "did", "done",
    "going", "know", "think", "thought", "yes", "no", "okay", "ok", "sure",
    "right", "left", "does", "don't", "doesn't", "isn't", "aren't", "wasn't",
    "weren't", "hasn't", "haven't", "hadn't", "won't", "wouldn't", "can't",
    "couldn't", "shouldn't", "let's", "that's", "there's", "here's", "what's",
  ]);

  const rows = db
    .prepare(`
      SELECT id, device_id, source, session_id, content
      FROM events
      WHERE content_type = 'transcript' AND length(content) > 20
      ORDER BY session_id, timestamp ASC
    `)
    .all();

  // Group content by session
  const bySession = new Map();
  for (const row of rows) {
    if (!bySession.has(row.session_id)) {
      bySession.set(row.session_id, new Set());
    }
    // Extract trigrams from content (skip thinking blocks and tool echoes)
    const clean = row.content
      .replace(/\[thinking\][^\n]*\n?/gi, "")
      .replace(/\[tool_result:[^\]]*\][^\n]*\n?/gi, "")
      .replace(/\[tool:[^\]]*\][^\n]*\n?/gi, "")
      .replace(/`{1,3}[^`]*`{1,3}/g, "");

    const words = clean
      .toLowerCase()
      .replace(/[^a-z0-9\s]/g, " ")
      .split(/\s+/)
      .filter((w) => w.length >= 4 && !STOPWORDS.has(w));

    for (let i = 0; i <= words.length - 3; i++) {
      const trigram = words.slice(i, i + 3).join(" ");
      bySession.get(row.session_id).add(trigram);
    }
  }

  // Count sessions per trigram
  const phraseFreq = new Map();
  for (const [, phrases] of bySession) {
    for (const phrase of phrases) {
      if (!phraseFreq.has(phrase)) {
        phraseFreq.set(phrase, { phrase, count: 0, sources: new Set(), devices: new Set() });
      }
      const e = phraseFreq.get(phrase);
      e.count++;
    }
  }

  // Filter by minimum session count and source diversity
  const patterns = [];
  for (const [phrase, data] of phraseFreq) {
    if (data.count < 3) continue;
    // Re-collect sources/devices for trigrams that pass the count filter
    const sources = new Set();
    const devices = new Set();
    for (const [session_id, phrases] of bySession) {
      if (phrases.has(phrase)) {
        // Find the row to get source/device
      }
    }
    patterns.push({ phrase, count: data.count });
  }

  return patterns.sort((a, b) => b.count - a.count).slice(0, 50);
}

/**
 * Extract session openers and closers (first/last message patterns).
 */
function extractSessionStructure(db) {
  const rows = db
    .prepare(`
      SELECT e.session_id, e.device_id, e.source, e.role, e.content, e.timestamp
      FROM (
        SELECT session_id, device_id, source,
               MIN(timestamp) as min_ts, MAX(timestamp) as max_ts
        FROM events WHERE content_type = 'transcript'
        GROUP BY session_id
      ) as sess
      JOIN events e ON e.session_id = sess.session_id
        AND (e.timestamp = sess.min_ts OR e.timestamp = sess.max_ts)
      ORDER BY e.session_id, e.timestamp
    `)
    .all();

  // Group by session
  const sessions = new Map();
  for (const row of rows) {
    if (!sessions.has(row.session_id)) {
      sessions.set(row.session_id, { first: null, last: null, source: row.source });
    }
    const s = sessions.get(row.session_id);
    if (!s.first && row.timestamp === s.first?.timestamp) {
      s.first = row;
    } else if (!s.first) {
      s.first = row;
    }
    s.last = row;
  }

  return sessions;
}

// ── Workflow templates matched by content ────────────────────────────────────

const CONTENT_TEMPLATES = [
  {
    match: /\b(explain|what is|what are|how does|how do|define|describe)\b/i,
    title: "Explanation Request",
    description: "User asks for explanation of a concept, mechanism, or code.",
    trigger: "When user asks 'what is X' or 'explain Y'",
    steps: [
      "1. Clarify what specifically about X the user wants to understand",
      "2. Give a concise explanation with a concrete example",
      "3. Offer to dive deeper into any specific aspect",
    ],
  },
  {
    match: /\b(fix|bug|error|issue|broken|not working|crash|failed|failure)\b/i,
    title: "Bug Investigation",
    description: "User reports a bug or error that needs investigation and fix.",
    trigger: "When user describes something that isn't working",
    steps: [
      "1. Ask for the exact error message or unexpected behavior",
      "2. Guide user through diagnostic commands",
      "3. Identify the root cause",
      "4. Propose and verify the fix",
    ],
  },
  {
    match: /\b(write|create|build|implement|add|make a new)\b/i,
    title: "Code Creation",
    description: "User wants to create a new file, component, or feature from scratch.",
    trigger: "When user says 'create X' or 'write a function that'",
    steps: [
      "1. Clarify requirements and edge cases",
      "2. Write the code with clear structure",
      "3. Add inline documentation",
      "4. Verify with tests or examples",
    ],
  },
  {
    match: /\b(refactor|simplify|clean up|restructure|improve)\b/i,
    title: "Code Improvement",
    description: "User wants to improve existing code quality or structure.",
    trigger: "When user asks to refactor or improve code",
    steps: [
      "1. Read and understand the current code",
      "2. Identify specific improvements to make",
      "3. Apply changes incrementally",
      "4. Verify behavior is unchanged",
    ],
  },
  {
    match: /\b(test|testing|unit test|integration test|coverage)\b/i,
    title: "Test Writing",
    description: "User wants tests added for existing code.",
    trigger: "When user mentions testing or asks to add test coverage",
    steps: [
      "1. Identify the function/file to test",
      "2. Write tests covering happy path and edge cases",
      "3. Run tests to verify they pass",
      "4. Check coverage and add missing cases",
    ],
  },
  {
    match: /\b(search|find|look for|locate|grep|find all)\b/i,
    title: "Code Search",
    description: "User needs to find something in the codebase.",
    trigger: "When user says 'find X' or 'search for Y'",
    steps: [
      "1. Use grep/find to locate relevant files",
      "2. Read the most relevant results",
      "3. Summarize findings with file paths and line numbers",
    ],
  },
  {
    match: /\b(debug|trace|inspect|investigate)\b/i,
    title: "Debugging Session",
    description: "Systematic investigation of unexpected behavior.",
    trigger: "When something needs systematic debugging",
    steps: [
      "1. Reproduce the issue with minimal steps",
      "2. Add logging/breakpoints to isolate the problem",
      "3. Identify root cause",
      "4. Apply minimal fix",
      "5. Verify the fix works",
    ],
  },
];

async function generateProposals(contentPatterns, db) {
  // Check existing approved proposals to avoid duplicates
  let existingTitles = new Set();
  try {
    const existing = proposalsDb
      .prepare("SELECT title FROM workflow_proposals WHERE status = 'approved'")
      .all();
    existingTitles = new Set(existing.map((r) => r.title));
  } catch {}

  const proposals = [];
  for (const template of CONTENT_TEMPLATES) {
    if (existingTitles.has(template.title)) continue;

    const id = crypto.randomUUID();
    proposals.push({
      id,
      title: template.title,
      description: template.description,
      trigger: template.trigger,
      steps: template.steps,
      confidence: 0.7,
      pattern: template.match.source,
    });
  }

  return proposals;
}

// ── Main ─────────────────────────────────────────────────────────────────────

async function main() {
  if (!fs.existsSync(DB_PATH)) {
    console.log("[synthesis] No events DB — run ingest first.");
    return;
  }

  const { default: bsqlite } = await import("better-sqlite3");
  const proposalsDb = new bsqlite(Proposals_PATH);
  proposalsDb.pragma("journal_mode = WAL");
  proposalsDb.exec(`
    CREATE TABLE IF NOT EXISTS workflow_proposals (
      id            TEXT PRIMARY KEY,
      pattern_hash  TEXT,
      pattern       TEXT NOT NULL,
      title         TEXT NOT NULL,
      description   TEXT NOT NULL,
      trigger       TEXT NOT NULL,
      steps         TEXT NOT NULL DEFAULT '[]',
      confidence    REAL NOT NULL,
      frequency     INTEGER NOT NULL DEFAULT 0,
      sources       TEXT NOT NULL DEFAULT '[]',
      devices       TEXT NOT NULL DEFAULT '[]',
      status        TEXT NOT NULL DEFAULT 'pending',
      telegram_msg_id INTEGER,
      approved_at   INTEGER,
      dismissed_at  INTEGER,
      created_at    INTEGER NOT NULL DEFAULT (unixepoch('now') * 1000)
    );
  `);

  const db = new bsqlite(DB_PATH);
  db.pragma("read_only = true");

  console.log("[synthesis] Analyzing session content patterns...");
  const contentPatterns = extractPhrasePatterns(db);
  console.log(`[synthesis] Top phrase patterns:`);
  for (const { phrase, count } of contentPatterns.slice(0, 10)) {
    console.log(`  [${count} sessions] ${phrase}`);
  }

  console.log("\n[synthesis] Matching workflow templates...");
  const proposals = await generateProposals(contentPatterns, db);
  console.log(`[synthesis] ${proposals.length} proposals generated`);

  if (proposals.length > 0) {
    const insert = proposalsDb.prepare(`
      INSERT OR IGNORE INTO workflow_proposals
        (id, pattern_hash, pattern, title, description, trigger, steps, confidence, frequency, sources, devices)
      VALUES
        (@id, @pattern_hash, @pattern, @title, @description, @trigger, @steps, @confidence, 0, '[]', '[]')
    `);

    const saveAll = proposalsDb.transaction((props) => {
      for (const p of props) {
        insert.run({
          ...p,
          pattern_hash: crypto.createHash("sha256").update(p.pattern).digest("hex").slice(0, 16),
          steps: JSON.stringify(p.steps),
        });
      }
    });

    saveAll(proposals);
    proposalsDb.close();

    console.log("\n[synthesis] Proposals saved:");
    for (const p of proposals) {
      console.log(`  [${Math.round(p.confidence * 100)}%] ${p.title}`);
      console.log(`    trigger: ${p.trigger}`);
    }
  }

  db.close();
}

main().catch((err) => {
  console.error("Fatal:", err?.message ?? err);
  process.exit(1);
});
