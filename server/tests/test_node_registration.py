import os
import tempfile
import unittest

os.environ["TANDEM_DISABLE_SWEEPER"] = "1"
# The server always has a shared token configured (it generates one if unset), so
# pin a known value here. The whole point of these tests is that a logged-in user
# can register *without* touching it.
os.environ.setdefault("TANDEM_NODE_REGISTRATION_TOKEN", "shared-token")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db.close()
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_tmp_db.name}")

from app import create_app  # noqa: E402
from app.extensions import db, redis_client  # noqa: E402
from app.models import User, UserAPI  # noqa: E402


class NodeRegistrationAuthTests(unittest.TestCase):
    """Registering a node should just work once you're logged in: a valid user
    API key is accepted the same way the shared registration token is. The token
    stays as a fallback for headless nodes, and bogus/absent credentials are
    still refused."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = create_app()
        cls.ctx = cls.app.app_context()
        cls.ctx.push()
        cls.client = cls.app.test_client()
        # Read the token the app actually resolved rather than assuming our own
        # env var won -- when the whole suite runs together, another module's
        # setdefault may have set TANDEM_NODE_REGISTRATION_TOKEN first.
        cls.shared_token = cls.app.config["NODE_REGISTRATION_TOKEN"]

    @classmethod
    def tearDownClass(cls) -> None:
        db.session.remove()
        cls.ctx.pop()

    def setUp(self) -> None:
        redis_client.flushdb()
        db.drop_all()
        db.create_all()

    def _make_user_with_key(self, username: str, api_key: str) -> int:
        user = User(username=username, password="unused")
        db.session.add(user)
        db.session.flush()
        db.session.add(UserAPI(user_id=user.id, api_key=api_key))
        db.session.commit()
        return user.id

    def _register(self, headers: dict) -> "tuple":
        response = self.client.post(
            "/nodes/register",
            json={"supports_wasm": True},
            headers=headers,
        )
        return response

    def test_api_key_registers_without_the_shared_token(self) -> None:
        user_id = self._make_user_with_key("alice", "alice-key")

        response = self._register({"Authorization": "Bearer alice-key"})

        self.assertEqual(response.status_code, 201)
        body = response.get_json()
        self.assertEqual(body["status"], "Registered")
        node_id = body["node_id"]
        # The node is stamped with its owner so the server knows whose it is.
        owner = redis_client.hget(f"node:{node_id}", "owner_user_id")
        owner = owner.decode() if isinstance(owner, bytes) else owner
        self.assertEqual(owner, str(user_id))

    def test_shared_token_still_works_for_headless_nodes(self) -> None:
        response = self._register({"Authorization": f"Bearer {self.shared_token}"})

        self.assertEqual(response.status_code, 201)
        node_id = response.get_json()["node_id"]
        # No user behind a token registration, so there's no owner recorded.
        self.assertIsNone(redis_client.hget(f"node:{node_id}", "owner_user_id"))

    def test_a_bogus_bearer_is_refused(self) -> None:
        self._make_user_with_key("bob", "bob-key")

        response = self._register({"Authorization": "Bearer not-a-real-key"})

        self.assertEqual(response.status_code, 403)

    def test_no_credentials_at_all_is_refused(self) -> None:
        response = self._register({})

        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
