CREATE TABLE "{{module}}::records" (
 id TEXT PRIMARY KEY, kind TEXT NOT NULL, title TEXT NOT NULL,
 description TEXT NOT NULL, body TEXT NOT NULL, revision TEXT NOT NULL,
 indexed_revision TEXT, index_error TEXT
);
CREATE TABLE "{{module}}::connections" (id TEXT PRIMARY KEY, body TEXT NOT NULL);
CREATE TABLE "{{module}}::sessions" (
 id TEXT PRIMARY KEY, connection TEXT NOT NULL, native_id TEXT NOT NULL,
 context TEXT NOT NULL, purpose TEXT NOT NULL, profile TEXT,
 state TEXT NOT NULL, observed_at REAL NOT NULL,
 UNIQUE(connection, native_id)
);
CREATE TABLE "{{module}}::deliveries" (
 id TEXT PRIMARY KEY, session TEXT NOT NULL, text TEXT NOT NULL,
 state TEXT NOT NULL, created REAL NOT NULL, result TEXT,
 error TEXT, attempts INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX "{{module}}::delivery_state" ON "{{module}}::deliveries"(state,created);
CREATE TABLE "{{module}}::subscriptions" (id TEXT PRIMARY KEY, body TEXT NOT NULL);
CREATE TABLE "{{module}}::events" (
 source TEXT NOT NULL, id TEXT NOT NULL, body TEXT NOT NULL,
 PRIMARY KEY(source,id)
);
CREATE TABLE "{{module}}::cursors" (source TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE "{{module}}::creations" (
 id TEXT PRIMARY KEY, request TEXT NOT NULL, native_id TEXT, state TEXT NOT NULL
);
CREATE TABLE "{{module}}::policies" (
 session TEXT PRIMARY KEY, activation TEXT NOT NULL, enabled INTEGER NOT NULL,
 revision TEXT NOT NULL
);
