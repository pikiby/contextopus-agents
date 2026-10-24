"""Small SQL helpers. Core owns connections, migration and transactions."""
import hashlib
import json


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(",", ":"))


def revision(value):
    return hashlib.sha256(encoded(value).encode()).hexdigest()


class Store:
    def __init__(self, storage, writer):
        self.sql, self.writer = storage, writer

    def rows(self, sql, args=(), *, tx=None):
        return (tx or self.sql).query(sql, args)["rows"]

    def one(self, table, ident, *, tx=None):
        if table not in {"records"}:
            raise ValueError("Unknown table")
        rows = self.rows(f'SELECT * FROM "{{{{module}}}}::{table}" WHERE id=?', [ident], tx=tx)
        if not rows:
            raise ValueError(f"Unknown {table} ID: {ident}")
        return rows[0]

    def json(self, table, ident):
        return json.loads(self.one(table, ident)["body"])

    def cursor(self, source):
        rows = self.rows('SELECT value FROM "{{module}}::cursors" WHERE source=?', ["source:" + source])
        return json.loads(rows[0]["value"]) if rows else None

    def cursor_put(self, source, value):
        with self.writer:
            self.sql.execute('INSERT INTO "{{module}}::cursors" VALUES (?,?) '
                             'ON CONFLICT(source) DO UPDATE SET value=excluded.value',
                             ["source:" + source, encoded(value)])
