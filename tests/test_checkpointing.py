import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from graph.checkpointing import create_checkpointer


class CheckpointingTests(unittest.TestCase):
    def test_memory_backend(self):
        self.assertEqual(type(create_checkpointer("memory")).__name__, "InMemorySaver")

    def test_sqlite_backend_creates_persistent_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoints.sqlite"
            fake_settings = SimpleNamespace(
                checkpointer_backend="sqlite",
                checkpoint_db_path=str(path),
            )
            with patch("graph.checkpointing.settings", fake_settings):
                saver = create_checkpointer("sqlite")
                saver.setup()
                saver.conn.close()
            self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main()
