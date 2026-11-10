import sqlite3
from contextlib import closing


def initialize(path):
    with closing(sqlite3.connect(path)) as db, db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS outbox (
                id TEXT PRIMARY KEY, delivered INTEGER NOT NULL DEFAULT 0
            );
        """)


def record(path, event_id):
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("INSERT INTO events VALUES (?)", (event_id,))
        db.execute("INSERT INTO outbox (id) VALUES (?)", (event_id,))


def dispatch(path, send):
    """Send pending events in insertion order with a single worker.

    A failed delivery stays pending and does not stop the others.
    Returns the IDs that failed in this run.
    """
    failed = []
    with closing(sqlite3.connect(path)) as db:
        pending = db.execute(
            "SELECT id FROM outbox WHERE delivered = 0 ORDER BY rowid"
        ).fetchall()
        for (event_id,) in pending:
            try:
                send(event_id)
            except Exception:
                failed.append(event_id)
                continue
            with db:
                db.execute("UPDATE outbox SET delivered = 1 WHERE id = ?", (event_id,))
    return failed
