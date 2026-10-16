"""Card #1 acceptance: GET /api/v2/health carries a read-only ``build`` object.

Every test boots the real ``server_v2.main.app`` in a fresh interpreter so the
environment (``AI_CADDIE_BUILD_REVISION`` / ``AI_CADDIE_FIXTURE_MODE``) is in
place before import, exactly as in a deployed or CI-fixture process. The probe
uses TestClient without entering its context manager, so no lifespan/startup
hook runs: offline, no database.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

REPO = Path(__file__).resolve().parents[2]
SENTINEL = "CARD1-HEALTH-PROBE "
FIXTURE_REVISION = "ci-fixture-20260827-v1"
SHA = "0123456789abcdef0123456789abcdef01234567"

_PROBE = f"""
import json
from fastapi.testclient import TestClient
from server_v2.main import app

response = TestClient(app).get("/api/v2/health")
print({SENTINEL!r} + json.dumps({{"status": response.status_code, "body": response.json()}}))
"""


def _health(revision: str | None, *, fixture_mode: bool = False) -> tuple[int, dict]:
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"AI_CADDIE_BUILD_REVISION", "AI_CADDIE_FIXTURE_MODE"}
    }
    if revision is not None:
        env["AI_CADDIE_BUILD_REVISION"] = revision
    if fixture_mode:
        env["AI_CADDIE_FIXTURE_MODE"] = "1"
    result = subprocess.run(
        [sys.executable, "-c", _PROBE],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(f"health probe exited {result.returncode}:\n{result.stderr[-4000:]}")
    lines = [line for line in result.stdout.splitlines() if line.startswith(SENTINEL)]
    if not lines:
        raise AssertionError(f"health probe printed no result:\n{result.stdout[-2000:]}\n{result.stderr[-2000:]}")
    payload = json.loads(lines[-1][len(SENTINEL):])
    return payload["status"], payload["body"]


class HealthBuildObjectTests(unittest.TestCase):
    def test_health_matches_card_example_exactly(self) -> None:
        # G1
        status, body = _health(SHA)

        self.assertEqual(status, 200)
        self.assertEqual(
            body,
            {
                "schema": "ai-caddie-health-v2",
                "status": "ok",
                "service": "server_v2",
                "revision": SHA,
                "build": {"revision": SHA, "short": "0123456789ab"},
            },
        )

    def test_build_revision_equals_stripped_top_level_revision(self) -> None:
        # G1
        status, body = _health("  feedfacecafebeef1234\n")

        self.assertEqual(status, 200)
        self.assertEqual(body["revision"], "feedfacecafebeef1234")
        self.assertIn("build", body)
        self.assertEqual(body["build"], {"revision": "feedfacecafebeef1234", "short": "feedfacecafe"})

    def test_short_revision_under_twelve_chars_is_kept_whole(self) -> None:
        # G1
        status, body = _health("abc123")

        self.assertEqual(status, 200)
        self.assertEqual(body["revision"], "abc123")
        self.assertIn("build", body)
        self.assertEqual(body["build"], {"revision": "abc123", "short": "abc123"})

    def test_unset_revision_falls_back_to_unknown_everywhere(self) -> None:
        # G2
        status, body = _health(None)

        self.assertEqual(status, 200)
        self.assertEqual(body["revision"], "unknown")
        self.assertIn("build", body)
        self.assertEqual(body["build"], {"revision": "unknown", "short": "unknown"})

    def test_blank_revision_falls_back_to_unknown_everywhere(self) -> None:
        # G2
        for blank in ("", "   ", "\t\n"):
            with self.subTest(revision=repr(blank)):
                status, body = _health(blank)

                self.assertEqual(status, 200)
                self.assertEqual(body["revision"], "unknown")
                self.assertIn("build", body)
                self.assertEqual(body["build"], {"revision": "unknown", "short": "unknown"})

    def test_ci_fixture_health_carries_same_build_shape(self) -> None:
        # G3
        status, body = _health(SHA, fixture_mode=True)

        self.assertEqual(status, 200)
        self.assertEqual(body["schema"], "ai-caddie-health-v2")
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["service"], "server_v2")
        self.assertEqual(body["revision"], FIXTURE_REVISION)
        self.assertEqual(body["dataMode"], "ci_fixture")
        self.assertEqual(body["source"], "non_production")
        self.assertEqual(body["fixtureRevision"], FIXTURE_REVISION)
        self.assertIn("build", body)
        self.assertEqual(body["build"], {"revision": FIXTURE_REVISION, "short": FIXTURE_REVISION[:12]})

    def test_fixture_and_real_build_objects_share_one_contract(self) -> None:
        # G1 G3
        _, real = _health(SHA)
        _, fixture = _health(SHA, fixture_mode=True)

        self.assertIn("build", real)
        self.assertIn("build", fixture)
        self.assertEqual(set(real["build"]), {"revision", "short"})
        self.assertEqual(set(fixture["build"]), set(real["build"]))
        for body in (real, fixture):
            self.assertEqual(body["build"]["revision"], body["revision"])
            self.assertEqual(body["build"]["short"], body["revision"][:12])
            self.assertTrue(all(isinstance(value, str) for value in body["build"].values()))


if __name__ == "__main__":
    unittest.main()
