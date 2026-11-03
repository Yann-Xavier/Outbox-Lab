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
    """Run with a single worker. Failed deliveries remain pending."""
    with closing(sqlite3.connect(path)) as db:
        pending = db.execute("SELECT id FROM outbox WHERE delivered = 0").fetchall()
        for (event_id,) in pending:
            send(event_id)
            with db:
                db.execute("UPDATE outbox SET delivered = 1 WHERE id = ?", (event_id,))
