import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from lab import dispatch, initialize, record


class OutboxTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "lab.sqlite"
        initialize(self.path)

    def test_recovers_pending_event_after_restart(self):
        record(self.path, "event-1")
        sent = []
        dispatch(self.path, sent.append)
        dispatch(self.path, sent.append)
        self.assertEqual(sent, ["event-1"])

    def test_delivery_can_repeat_if_confirmation_is_lost(self):
        record(self.path, "event-1")
        effects = set()
        attempts = []

        def receive(event_id):
            attempts.append(event_id)
            effects.add(event_id)
            if len(attempts) == 1:
                raise TimeoutError("resposta perdida após o recebimento")

        with self.assertRaises(TimeoutError):
            dispatch(self.path, receive)
        dispatch(self.path, receive)
        self.assertEqual(attempts, ["event-1", "event-1"])
        self.assertEqual(effects, {"event-1"})

    def test_event_rolls_back_if_outbox_write_fails(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("CREATE TRIGGER reject_outbox BEFORE INSERT ON outbox "
                       "BEGIN SELECT RAISE(ABORT, 'falha injetada'); END;")
        with self.assertRaises(sqlite3.IntegrityError):
            record(self.path, "event-1")
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute("SELECT id FROM events").fetchall(), [])


if __name__ == "__main__":
    unittest.main()
