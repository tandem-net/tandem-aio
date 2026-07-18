import os
import tempfile
import time
import unittest

# Configure the app for a self-contained test before importing it: don't start
# the real sweeper thread, use an isolated Redis database and a throwaway SQLite
# file, and avoid writing a registration-token file.
os.environ["TANDEM_DISABLE_SWEEPER"] = "1"
os.environ.setdefault("TANDEM_NODE_REGISTRATION_TOKEN", "test-registration-token")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db.close()
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_tmp_db.name}")

from app import create_app  # noqa: E402
from app.extensions import redis_client  # noqa: E402
from app.utils import task_queue  # noqa: E402


class SweeperFailoverTests(unittest.TestCase):
    """The background sweeper reclaims work from nodes that have died: tasks the
    node already claimed, and tasks still waiting in its queue."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = create_app()
        cls.ctx = cls.app.app_context()
        cls.ctx.push()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.ctx.pop()

    def setUp(self) -> None:
        redis_client.flushdb()

    def _queue_contents(self, key: str) -> list[str]:
        return [str(task_queue.decode_value(x)) for x in redis_client.lrange(key, 0, -1)]

    def _register_pair(self) -> float:
        now = time.time()
        redis_client.sadd("nodes", "dead", "alive")
        redis_client.hset(
            "node:dead",
            mapping={"node_token": "t", "last_seen": str(now - 100), "supports_wasm": "1"},
        )
        redis_client.hset(
            "node:alive",
            mapping={"node_token": "t", "last_seen": str(now), "supports_wasm": "1"},
        )
        return now

    def test_drains_a_queued_task_off_a_dead_node(self) -> None:
        self._register_pair()
        redis_client.hset(
            "task:T1",
            mapping={"status": "queued", "runtime": "wasm", "assigned_node": "dead"},
        )
        redis_client.rpush("node:dead:queue", "T1")

        task_queue.sweep_stale_work()

        self.assertEqual(redis_client.llen("node:dead:queue"), 0)
        self.assertIn("T1", self._queue_contents("node:alive:queue"))
        self.assertEqual(task_queue.get_task("T1")["assigned_node"], "alive")

    def test_reclaims_a_claimed_task_off_a_dead_node(self) -> None:
        self._register_pair()
        redis_client.hset("node:dead", mapping={"current_task": "T2"})
        redis_client.hset(
            "task:T2",
            mapping={"status": "running", "runtime": "wasm", "assigned_node": "dead"},
        )

        task_queue.sweep_stale_work()

        self.assertIn("T2", self._queue_contents("node:alive:queue"))
        # the dead node's current-task pointer is cleared out
        self.assertEqual(task_queue.get_node("dead").get("current_task", ""), "")

    def test_leaves_a_healthy_node_alone(self) -> None:
        now = time.time()
        redis_client.sadd("nodes", "alive")
        redis_client.hset(
            "node:alive",
            mapping={"node_token": "t", "last_seen": str(now), "supports_wasm": "1"},
        )
        redis_client.hset(
            "task:T3",
            mapping={"status": "queued", "runtime": "wasm", "assigned_node": "alive"},
        )
        redis_client.rpush("node:alive:queue", "T3")

        task_queue.sweep_stale_work()

        # nothing moved: the node is healthy, so its queued work stays put
        self.assertEqual(self._queue_contents("node:alive:queue"), ["T3"])


if __name__ == "__main__":
    unittest.main()
