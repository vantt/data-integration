CREATE TABLE IF NOT EXISTS webhooks (
    msg_id TEXT PRIMARY KEY,       -- UUID 
    payload TEXT,                  -- JSON Body
    source_system TEXT,            -- "stripe", "github", etc.
    headers TEXT,                  -- JSON Headers
    status TEXT DEFAULT 'NEW',     -- NEW, PROCESSING, DONE
    enqueued_at INTEGER,           -- Unix Timestamp
    locked_until INTEGER DEFAULT 0 -- Timestamp for Visibility Timeout
);

CREATE INDEX IF NOT EXISTS idx_status_locked ON webhooks(status, locked_until);
CREATE INDEX IF NOT EXISTS idx_source_status_locked ON webhooks(source_system, status, locked_until);

CREATE TABLE IF NOT EXISTS webhook_errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    webhook_id TEXT,               -- Optional, link to webhooks.msg_id if available
    error_type TEXT,               -- e.g., 'JSON_PARSE_ERROR', 'DB_INSERT_ERROR'
    error_message TEXT,
    stack_trace TEXT,
    payload TEXT,                  -- The original payload that caused the error (if available)
    created_at INTEGER DEFAULT (strftime('%s', 'now'))
);

