import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from lab import dispatch, initialize, record

HERE = Path(__file__).resolve().parent


def run_and_crash(code, *args):
    """Run code in a new process that ends with os._exit, without cleanup."""
    script = f"import os, sys\nsys.path.insert(0, {str(HERE)!r})\n{code}\nos._exit(1)\n"
    subprocess.run([sys.executable, "-c", script, *map(str, args)], check=False)


class OutboxTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "lab.sqlite"
        initialize(self.path)

    def delivered(self, event_id):
        with closing(sqlite3.connect(self.path)) as db:
            return db.execute(
                "SELECT delivered FROM outbox WHERE id = ?", (event_id,)
            ).fetchone()[0]

    def test_recovers_pending_event_after_restart(self):
        # O processo grava o evento e morre antes de qualquer envio.
        run_and_crash(
            "from lab import record\nrecord(sys.argv[1], 'event-1')", self.path
        )
        sent = []
        self.assertEqual(dispatch(self.path, sent.append), [])
        dispatch(self.path, sent.append)
        self.assertEqual(sent, ["event-1"])

    def test_resends_if_process_dies_after_send(self):
        # O processo envia e morre antes de marcar a entrega como concluída.
        record(self.path, "event-1")
        received = self.path.with_name("received.txt")
        run_and_crash(
            "from lab import dispatch\n"
            "def send(event_id):\n"
            "    with open(sys.argv[2], 'a') as received:\n"
            "        received.write(event_id + '\\n')\n"
            "    os._exit(1)\n"
            "dispatch(sys.argv[1], send)",
            self.path, received,
        )
        self.assertEqual(received.read_text().split(), ["event-1"])
        self.assertEqual(self.delivered("event-1"), 0)

        sent = []
        dispatch(self.path, sent.append)
        self.assertEqual(sent, ["event-1"])
        self.assertEqual(self.delivered("event-1"), 1)

    def test_lost_confirmation_causes_second_delivery(self):
        record(self.path, "event-1")
        attempts = []

        def receive(event_id):
            attempts.append(event_id)
            if len(attempts) == 1:
                raise TimeoutError("resposta perdida após o recebimento")

        self.assertEqual(dispatch(self.path, receive), ["event-1"])
        self.assertEqual(self.delivered("event-1"), 0)
        self.assertEqual(dispatch(self.path, receive), [])
        # O outbox não deduplica: o receptor recebe o mesmo ID duas vezes.
        self.assertEqual(attempts, ["event-1", "event-1"])
        self.assertEqual(self.delivered("event-1"), 1)

    def test_failure_does_not_block_other_events(self):
        for event_id in ("event-1", "event-2", "event-3"):
            record(self.path, event_id)
        sent = []

        def send(event_id):
            if event_id == "event-1":
                raise TimeoutError("receptor indisponível")
            sent.append(event_id)

        self.assertEqual(dispatch(self.path, send), ["event-1"])
        self.assertEqual(sent, ["event-2", "event-3"])
        self.assertEqual(self.delivered("event-1"), 0)

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
