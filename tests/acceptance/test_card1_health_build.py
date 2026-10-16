"""Card #1 acceptance: GET /api/v2/health carries a read-only ``build`` object.

Every test launches the real ``server_v2.main.app`` in a fresh interpreter
(``subprocess.run``) with ``AI_CADDIE_BUILD_REVISION`` / ``AI_CADDIE_FIXTURE_MODE``
already in the environment before import, exactly as a deployed or CI-fixture
process starts. The probe drives the app through TestClient without entering its
context manager, so no lifespan/startup hook runs: offline, no database.

A probe step may set (``"setRevision": "<value>"``) or unset
(``"setRevision": None``) the revision variable before its request, which checks
that ``build`` always reports the same value as the top-level ``revision``.
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
HEALTH = "/api/v2/health"
READINESS = "/api/v2/readiness"
FIXTURE_REVISION = "ci-fixture-20260827-v1"
FIXTURE_MARKERS = {"dataMode": "ci_fixture", "source": "non_production", "fixtureRevision": FIXTURE_REVISION}
SHA = "0123456789abcdef0123456789abcdef01234567"
UNKNOWN_BUILD = {"revision": "unknown", "short": "unknown"}
RUN = {"cwd": REPO, "capture_output": True, "text": True, "timeout": 120, "check": False}

_PROBE = f"""
import json
import os
import sys

from fastapi.testclient import TestClient

from server_v2.main import app

client = TestClient(app)
results = []
for step in json.loads(sys.argv[1]):
    if "setRevision" in step:
        if step["setRevision"] is None:
            os.environ.pop("AI_CADDIE_BUILD_REVISION", None)
        else:
            os.environ["AI_CADDIE_BUILD_REVISION"] = step["setRevision"]
    response = client.request(
        step.get("method", "GET"),
        step["path"],
        params=step.get("params"),
        headers=step.get("headers"),
        json=step.get("json"),
    )
    try:
        body = response.json()
    except ValueError:
        body = None
    results.append({{"status": response.status_code, "body": body}})
print({SENTINEL!r} + json.dumps(results))
"""


def _env(revision: str | None, *, fixture_mode: bool = False) -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"AI_CADDIE_BUILD_REVISION", "AI_CADDIE_FIXTURE_MODE"}
    }
    if revision is not None:
        env["AI_CADDIE_BUILD_REVISION"] = revision
    if fixture_mode:
        env["AI_CADDIE_FIXTURE_MODE"] = "1"
    return env


def _probe(*steps: dict) -> list[str]:
    return [sys.executable, "-c", _PROBE, json.dumps(list(steps))]


def _responses(result: subprocess.CompletedProcess[str]) -> list[dict]:
    if result.returncode != 0:
        raise AssertionError(f"health probe exited {result.returncode}:\n{result.stderr[-4000:]}")
    lines = [line for line in result.stdout.splitlines() if line.startswith(SENTINEL)]
    if not lines:
        raise AssertionError(f"health probe printed no result:\n{result.stdout[-2000:]}\n{result.stderr[-2000:]}")
    return json.loads(lines[-1][len(SENTINEL):])


def _build(response: dict) -> object:
    body = response["body"]
    return body.get("build") if isinstance(body, dict) else None


class HealthBuildObjectTests(unittest.TestCase):
    def test_health_matches_card_example_exactly(self) -> None:
        # G1
        result = subprocess.run(_probe({"path": HEALTH}), env=_env(SHA), **RUN)
        [health] = _responses(result)

        self.assertEqual(health["status"], 200)
        self.assertEqual(
            health["body"],
            {
                "schema": "ai-caddie-health-v2",
                "status": "ok",
                "service": "server_v2",
                "revision": SHA,
                "build": {"revision": SHA, "short": "0123456789ab"},
            },
        )

    def test_build_revision_is_the_stripped_top_level_revision(self) -> None:
        # G1
        result = subprocess.run(_probe({"path": HEALTH}), env=_env("  feedfacecafebeef1234\n"), **RUN)
        [health] = _responses(result)

        self.assertEqual(health["status"], 200)
        self.assertEqual(health["body"]["revision"], "feedfacecafebeef1234")
        self.assertEqual(_build(health), {"revision": "feedfacecafebeef1234", "short": "feedfacecafe"})

    def test_short_is_the_first_twelve_characters(self) -> None:
        # G1
        result = subprocess.run(
            _probe(
                {"path": HEALTH},
                {"path": HEALTH, "setRevision": "0123456789ab"},
                {"path": HEALTH, "setRevision": "0123456789abc"},
            ),
            env=_env("abc123"),
            **RUN,
        )
        responses = _responses(result)

        self.assertEqual([response["status"] for response in responses], [200, 200, 200])
        self.assertEqual(
            [_build(response) for response in responses],
            [
                {"revision": "abc123", "short": "abc123"},
                {"revision": "0123456789ab", "short": "0123456789ab"},
                {"revision": "0123456789abc", "short": "0123456789ab"},
            ],
        )

    def test_build_tracks_the_top_level_revision_on_every_request(self) -> None:
        # G1
        result = subprocess.run(
            _probe({"path": HEALTH}, {"path": HEALTH, "setRevision": SHA}),
            env=_env("boot-revision-aaaaaaaa"),
            **RUN,
        )
        at_boot, after_change = _responses(result)

        self.assertEqual(at_boot["body"]["revision"], "boot-revision-aaaaaaaa")
        self.assertEqual(_build(at_boot), {"revision": "boot-revision-aaaaaaaa", "short": "boot-revisio"})
        self.assertEqual(after_change["body"]["revision"], SHA)
        self.assertEqual(_build(after_change), {"revision": SHA, "short": SHA[:12]})

    def test_build_cannot_be_overridden_or_written(self) -> None:
        # G1
        spoof = {"revision": "spoofed", "short": "spoofed"}
        result = subprocess.run(
            _probe(
                {
                    "path": HEALTH,
                    "params": {**spoof, "build": "spoofed", "build.revision": "spoofed"},
                    "headers": {"X-AI-Caddie-Build-Revision": "spoofed", "X-Build-Revision": "spoofed"},
                },
                {"method": "POST", "path": HEALTH, "json": {"build": spoof}},
                {"method": "PUT", "path": HEALTH, "json": {"build": spoof}},
                {"method": "PATCH", "path": HEALTH, "json": {"build": spoof}},
                {"method": "DELETE", "path": HEALTH},
                {"path": HEALTH},
            ),
            env=_env(SHA),
            **RUN,
        )
        spoofed_read, *writes, read_after_writes = _responses(result)

        self.assertEqual(spoofed_read["status"], 200)
        self.assertEqual(spoofed_read["body"]["revision"], SHA)
        self.assertEqual(_build(spoofed_read), {"revision": SHA, "short": SHA[:12]})
        self.assertEqual([write["status"] for write in writes], [405, 405, 405, 405])
        self.assertEqual(_build(read_after_writes), {"revision": SHA, "short": SHA[:12]})

    def test_unset_revision_falls_back_to_unknown_everywhere(self) -> None:
        # G2
        result = subprocess.run(
            _probe(
                {"path": HEALTH},
                {"path": HEALTH, "setRevision": SHA},
                {"path": HEALTH, "setRevision": None},
            ),
            env=_env(None),
            **RUN,
        )
        unset_at_boot, set_later, unset_again = _responses(result)

        self.assertEqual(unset_at_boot["status"], 200)
        self.assertEqual(unset_at_boot["body"]["revision"], "unknown")
        self.assertEqual(_build(unset_at_boot), UNKNOWN_BUILD)
        self.assertEqual(_build(set_later), {"revision": SHA, "short": SHA[:12]})
        self.assertEqual(unset_again["body"]["revision"], "unknown")
        self.assertEqual(_build(unset_again), UNKNOWN_BUILD)

    def test_blank_revision_falls_back_to_unknown_everywhere(self) -> None:
        # G2
        result = subprocess.run(
            _probe(
                {"path": HEALTH},
                {"path": HEALTH, "setRevision": ""},
                {"path": HEALTH, "setRevision": "\t\n"},
                {"path": HEALTH, "setRevision": " \r\n\t "},
            ),
            env=_env("   "),
            **RUN,
        )
        responses = _responses(result)

        self.assertEqual(
            [(response["status"], response["body"]["revision"], _build(response)) for response in responses],
            [(200, "unknown", UNKNOWN_BUILD)] * 4,
        )

    def test_ci_fixture_health_carries_the_same_build_shape(self) -> None:
        # G3
        result = subprocess.run(
            _probe({"path": HEALTH}, {"path": READINESS}),
            env=_env(SHA, fixture_mode=True),
            **RUN,
        )
        health, readiness = _responses(result)

        self.assertEqual(health["status"], 200)
        self.assertEqual(
            health["body"],
            {
                "schema": "ai-caddie-health-v2",
                "status": "ok",
                "service": "server_v2",
                "revision": FIXTURE_REVISION,
                "build": {"revision": FIXTURE_REVISION, "short": "ci-fixture-2"},
                **FIXTURE_MARKERS,
            },
        )
        # The card leaves /api/v2/readiness alone: build belongs to health only.
        self.assertEqual(readiness["status"], 200)
        self.assertEqual(
            readiness["body"],
            {
                "schema": "ai-caddie-readiness-v1",
                "status": "ready",
                "authenticated": True,
                "checks": [{"label": "fixture", "state": "ready"}],
                **FIXTURE_MARKERS,
            },
        )

    def test_fixture_and_real_health_share_one_contract(self) -> None:
        # G1
        # G3
        real_result = subprocess.run(_probe({"path": HEALTH}), env=_env(SHA), **RUN)
        fixture_result = subprocess.run(_probe({"path": HEALTH}), env=_env(SHA, fixture_mode=True), **RUN)
        [real] = _responses(real_result)
        [fixture] = _responses(fixture_result)

        self.assertIsInstance(_build(real), dict)
        self.assertIsInstance(_build(fixture), dict)
        self.assertEqual(set(_build(real)), {"revision", "short"})
        self.assertEqual(set(_build(fixture)), set(_build(real)))
        self.assertEqual(set(fixture["body"]) - set(real["body"]), set(FIXTURE_MARKERS))
        self.assertLessEqual(set(real["body"]), set(fixture["body"]))
        for body in (real["body"], fixture["body"]):
            self.assertEqual(body["build"]["revision"], body["revision"])
            self.assertEqual(body["build"]["short"], body["revision"][:12])
            self.assertTrue(all(isinstance(value, str) for value in body["build"].values()))


if __name__ == "__main__":
    unittest.main()
