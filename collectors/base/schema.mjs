/**
 * Unified Event Schema — the one schema that handles every connector.
 *
 * Design rules:
 * 1. Fixed columns = universally true for ALL sources. Never add new fixed columns.
 * 2. metadata = JSON string, grows per-connector. Schema never changes when adding connectors.
 * 3. event_hash is the dedup key. Same source + session + timestamp + content = same event.
 */
import crypto from "node:crypto";

export const CREATE_TABLE_SQL = `
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
CREATE INDEX IF NOT EXISTS idx_events_hash     ON events(event_hash);
`;

/**
 * Compute event_hash for dedup.
 * Same source + session + timestamp + content = same event.
 */
export function computeEventHash(source, session_id, timestamp, content) {
	const input = `${source}:${session_id}:${timestamp}:${content}`;
	return crypto.createHash("sha256").update(input).digest("hex");
}

/**
 * Serialize metadata to JSON, always an object.
 */
export function serializeMetadata(meta = {}) {
	return JSON.stringify(meta);
}

/**
 * Generate a uuid v4.
 */
export function uuid() {
	return crypto.randomUUID();
}
