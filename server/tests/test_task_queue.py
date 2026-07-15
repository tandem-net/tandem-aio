import unittest
from unittest.mock import patch

from app.utils import task_queue


class _FakeRedis:
    """Just enough Redis for the selection logic: fixed queue lengths."""

    def __init__(self, lengths: dict[str, int]) -> None:
        self._lengths = lengths

    def llen(self, key: str) -> int:
        return self._lengths.get(key, 0)


class SelectLeastLoadedNodeTests(unittest.TestCase):
    """The planner assigns each task to whichever node has the fewest queued
    tasks, counting both what's in Redis and what this same pass already handed
    out, so a burst spreads across nodes instead of piling on one."""

    def test_prefers_the_shortest_queue_and_spreads_within_a_pass(self) -> None:
        fake = _FakeRedis(
            {
                "node:busy:queue": 5,
                "node:empty:queue": 0,
                "node:middle:queue": 2,
            }
        )

        with patch.object(task_queue, "redis_client", fake):
            pending: dict[str, int] = {}
            picks = [
                task_queue.select_least_loaded_node(
                    ["busy", "empty", "middle"], pending
                )
                for _ in range(4)
            ]

        # "empty" starts with nothing queued, so it's picked first and keeps
        # getting picked until its running total catches up with the others.
        self.assertEqual(picks[0], "empty")
        # "busy" already has 5 queued, so across four assignments it never wins.
        self.assertNotIn("busy", picks)

    def test_single_node_always_wins(self) -> None:
        with patch.object(task_queue, "redis_client", _FakeRedis({})):
            pending: dict[str, int] = {}
            self.assertEqual(
                task_queue.select_least_loaded_node(["only"], pending), "only"
            )
            self.assertEqual(pending["only"], 1)


if __name__ == "__main__":
    unittest.main()
