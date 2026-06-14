/**
 * SQLite ingestion — runs on the Linux hub (MacBook Air).
 *
 * Reads JSONL exports from ~/.memory/exports/ (synced from each machine),
 * merges them into a local SQLite DB, skips already-seen event_hash values.
 *
 * Usage: node merge-events.mjs [--export-dir ~/.memory/exports]
 */
import fs from "node:fs";
import fsPromises from "node:fs/promises";
import path from "node:path";
import os from "node:os";
import betterSqlite3 from "better-sqlite3";

const EXPORT_DIR = process.argv.includes("--export-dir")
  ? process.argv[process.argv.indexOf("--export-dir") + 1]
  : path.join(os.homedir(), ".memory", "exports");

const DB_PATH = path.join(os.homedir(), ".memory", "hub", "events.db");

// ── Schema ───────────────────────────────────────────────────────────────────

const CREATE_TABLE = `
CREATE TABLE IF NOT EXISTS events (
  id            TEXT PRIMARY KEY,
  timestamp     INTEGER NOT NULL,
  content_type  TEXT NOT NULL,
  content       TEXT NOT NULL,
  source        TEXT NOT NULL,
  source_type   TEXT NOT NULL,
  device_id     TEXT NOT NULL,
  session_id    TEXT NOT NULL,
  event_hash    TEXT NOT NULL UNIQUE,
  metadata      TEXT NOT NULL DEFAULT '{}',
  imported_at   INTEGER NOT NULL DEFAULT (unixepoch('now') * 1000)
);

CREATE INDEX IF NOT EXISTS idx_events_timestamp  ON events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_source     ON events(source);
CREATE INDEX IF NOT EXISTS idx_events_ctype     ON events(content_type);
CREATE INDEX IF NOT EXISTS idx_events_device    ON events(device_id);
CREATE INDEX IF NOT EXISTS idx_events_session   ON events(session_id);
CREATE INDEX IF NOT EXISTS idx_events_hash      ON events(event_hash);

CREATE TABLE IF NOT EXISTS patterns (
  id            TEXT PRIMARY KEY,
  device_id     TEXT NOT NULL,
  source        TEXT NOT NULL,
  pattern_type  TEXT NOT NULL,
  pattern_hash  TEXT NOT NULL UNIQUE,
  frequency     INTEGER NOT NULL DEFAULT 1,
  avg_duration_ms INTEGER,
  outcomes      TEXT NOT NULL DEFAULT '{}',
  tool_sequence TEXT NOT NULL DEFAULT '[]',
  first_seen    INTEGER NOT NULL,
  last_seen     INTEGER NOT NULL,
  confidence    REAL NOT NULL DEFAULT 0.5,
  metadata      TEXT NOT NULL DEFAULT '{}',
  discovered_at INTEGER NOT NULL DEFAULT (unixepoch('now') * 1000)
);

CREATE TABLE IF NOT EXISTS workflow_proposals (
  id            TEXT PRIMARY KEY,
  pattern_id    TEXT,
  title         TEXT NOT NULL,
  description   TEXT NOT NULL,
  trigger       TEXT NOT NULL,
  steps         TEXT NOT NULL DEFAULT '[]',
  status        TEXT NOT NULL DEFAULT 'pending',
  telegram_msg_id INTEGER,
  approved_at   INTEGER,
  dismissed_at  INTEGER,
  approved_by   TEXT,
  created_at    INTEGER NOT NULL DEFAULT (unixepoch('now') * 1000)
);

CREATE TABLE IF NOT EXISTS sync_state (
  device_id     TEXT PRIMARY KEY,
  source         TEXT NOT NULL,
  last_event_ts  INTEGER NOT NULL DEFAULT 0,
  last_sync_at   INTEGER NOT NULL DEFAULT (unixepoch('now') * 1000)
);
`;

// ── Main ─────────────────────────────────────────────────────────────────────

async function main() {
  await fsPromises.mkdir(path.dirname(DB_PATH), { recursive: true });

  const db = new betterSqlite3(DB_PATH);
  db.pragma("journal_mode = WAL");
  db.exec(CREATE_TABLE);

  const insertEvent = db.prepare(`
    INSERT OR IGNORE INTO events
      (id, timestamp, content_type, content, source, source_type, device_id, session_id, event_hash, metadata)
    VALUES
      (@id, @timestamp, @content_type, @content, @source, @source_type, @device_id, @session_id, @event_hash, @metadata)
  `);

  const updateSync = db.prepare(`
    INSERT INTO sync_state (device_id, source, last_event_ts, last_sync_at)
    VALUES (@device_id, @source, @last_event_ts, unixepoch('now') * 1000)
    ON CONFLICT(device_id) DO UPDATE SET
      last_event_ts = MAX(last_event_ts, @last_event_ts),
      last_sync_at = unixepoch('now') * 1000
  `);

  const getManifests = () =>
    fsPromises.readdir(EXPORT_DIR).then((ents) =>
      ents
        .filter((e) => e.startsWith("manifest_") && e.endsWith(".json"))
        .map((f) => path.join(EXPORT_DIR, f))
        .sort()
    );

  const manifests = await getManifests();
  if (manifests.length === 0) {
    console.log("[ingest] No manifests found — run collectors first.");
    return;
  }

  let totalIngested = 0;
  let totalSkipped = 0;

  for (const manifestPath of manifests) {
    const manifest = JSON.parse(await fsPromises.readFile(manifestPath, "utf8"));
    const { device_id, platform } = manifest;

    console.log(`[ingest] Device: ${device_id} (${platform})`);

    for (const exportEntry of manifest.exports ?? []) {
      const { source, file } = exportEntry;
      if (!file || !fs.existsSync(file)) {
        console.log(`  [${source}] file not found, skipping`);
        continue;
      }

      const raw = await fsPromises.readFile(file, "utf8");
      const lines = raw.split("\n").filter((l) => l.trim());
      let ingested = 0;
      let skipped = 0;
      let maxTs = 0;

      const insertMany = db.transaction((events) => {
        for (const ev of events) {
          const res = insertEvent.run(ev);
          if (res.changes > 0) {
            ingested++;
            if (ev.timestamp > maxTs) maxTs = ev.timestamp;
          } else {
            skipped++;
          }
        }
      });

      const events = [];
      for (const line of lines) {
        try {
          events.push(JSON.parse(line));
        } catch {
          skipped++;
        }
      }

      insertMany(events);
      totalIngested += ingested;
      totalSkipped += skipped;

      if (maxTs > 0) {
        updateSync.run({ device_id, source, last_event_ts: maxTs });
      }

      console.log(`  [${source}] ingested=${ingested} skipped=${skipped}`);
    }
  }

  console.log(`\n[ingest] Total: +${totalIngested} events, ${totalSkipped} skipped (already seen)`);

  // Stats
  const counts = db
    .prepare("SELECT source, COUNT(*) as n FROM events GROUP BY source")
    .all();
  console.log("\n[ingest] DB summary:");
  for (const { source, n } of counts) {
    console.log(`  ${source}: ${n} events`);
  }

  db.close();
}

main().catch((err) => {
  console.error("Fatal:", err?.message ?? err);
  process.exit(1);
});
