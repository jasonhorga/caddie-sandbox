"""Card #3 acceptance: ``build.revision`` in GET /api/v2/health is the 12-character short sha.

Contract: ``.agent/contracts/card-3.md``. ``build`` becomes ``{"revision": R[:12]}``,
where ``R`` is the top-level ``revision``. ``build.short`` is gone, and the top-level
fields keep their current values (``revision`` stays the full value).

Every test launches the real ``server_v2.main.app`` in a fresh interpreter
(``subprocess.run``) with ``AI_CADDIE_BUILD_REVISION`` / ``AI_CADDIE_FIXTURE_MODE``
already in the environment before import, as a deployed or CI-fixture process
starts. The probe drives the app through TestClient without entering its context
manager, so no lifespan/startup hook runs: offline, no database.

A probe step may set (``"setRevision": "<value>"``) or unset
(``"setRevision": None``) the revision variable before its request.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

REPO = Path(__file__).resolve().parents[2]
SENTINEL = "CARD3-HEALTH-PROBE "
HEALTH = "/api/v2/health"
READINESS = "/api/v2/readiness"
FIXTURE_REVISION = "ci-fixture-20260827-v1"
FIXTURE_MARKERS = {"dataMode": "ci_fixture", "source": "non_production", "fixtureRevision": FIXTURE_REVISION}
SHA = "0123456789abcdef0123456789abcdef01234567"
OTHER_SHA = "fedcba9876543210fedcba9876543210fedcba98"
TOP_LEVEL = {"schema": "ai-caddie-health-v2", "status": "ok", "service": "server_v2"}
UNKNOWN_BUILD = {"revision": "unknown"}
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


class HealthShortBuildRevisionTests(unittest.TestCase):
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
                "revision": "0123456789abcdef0123456789abcdef01234567",
                "build": {"revision": "0123456789ab"},
            },
        )

    def test_build_revision_is_the_first_twelve_characters_of_the_stripped_revision(self) -> None:
        # G1
        result = subprocess.run(
            _probe(
                {"path": HEALTH},
                {"path": HEALTH, "setRevision": "abc123"},
                {"path": HEALTH, "setRevision": "0123456789ab"},
                {"path": HEALTH, "setRevision": "0123456789abc"},
                {"path": HEALTH, "setRevision": OTHER_SHA},
            ),
            env=_env(f"  {SHA}\n"),
            **RUN,
        )
        responses = _responses(result)

        self.assertEqual([response["status"] for response in responses], [200] * 5)
        self.assertEqual(
            [(response["body"]["revision"], _build(response)) for response in responses],
            [
                (SHA, {"revision": "0123456789ab"}),
                ("abc123", {"revision": "abc123"}),
                ("0123456789ab", {"revision": "0123456789ab"}),
                ("0123456789abc", {"revision": "0123456789ab"}),
                (OTHER_SHA, {"revision": "fedcba987654"}),
            ],
        )

    def test_short_is_removed_top_level_is_unchanged_and_build_is_read_only(self) -> None:
        # G1
        spoof = {"revision": "spoofed", "short": "spoofed"}
        result = subprocess.run(
            _probe(
                {
                    "path": HEALTH,
                    "params": {**spoof, "build": "spoofed", "build.revision": "spoofed", "build.short": "spoofed"},
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

        self.assertEqual([write["status"] for write in writes], [405, 405, 405, 405])
        for read in (spoofed_read, read_after_writes):
            self.assertEqual(read["status"], 200)
            self.assertEqual(set(read["body"]), {*TOP_LEVEL, "revision", "build"})
            self.assertEqual({key: read["body"][key] for key in TOP_LEVEL}, TOP_LEVEL)
            # The full sha stays at the top level; only build carries the short form.
            self.assertEqual(read["body"]["revision"], SHA)
            self.assertNotIn("short", read["body"]["build"])
            self.assertEqual(_build(read), {"revision": SHA[:12]})

    def test_unset_revision_reports_unknown(self) -> None:
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

        for unset in (unset_at_boot, unset_again):
            self.assertEqual(unset["status"], 200)
            self.assertEqual(unset["body"], {**TOP_LEVEL, "revision": "unknown", "build": UNKNOWN_BUILD})
        self.assertEqual(set_later["body"]["revision"], SHA)
        self.assertEqual(_build(set_later), {"revision": SHA[:12]})

    def test_blank_revision_reports_unknown(self) -> None:
        # G2
        result = subprocess.run(
            _probe(
                {"path": HEALTH},
                {"path": HEALTH, "setRevision": ""},
                {"path": HEALTH, "setRevision": "\t\n"},
                {"path": HEALTH, "setRevision": " \r\n\t "},
                {"path": HEALTH, "setRevision": OTHER_SHA},
                {"path": HEALTH, "setRevision": "   "},
            ),
            env=_env("   "),
            **RUN,
        )
        *blanks, real, blank_again = _responses(result)

        unknown = (200, {**TOP_LEVEL, "revision": "unknown", "build": UNKNOWN_BUILD})
        self.assertEqual([(response["status"], response["body"]) for response in blanks], [unknown] * 4)
        self.assertEqual(_build(real), {"revision": OTHER_SHA[:12]})
        self.assertEqual((blank_again["status"], blank_again["body"]), unknown)

    def test_ci_fixture_health_uses_the_short_build_revision(self) -> None:
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
                "build": {"revision": "ci-fixture-2"},
                **FIXTURE_MARKERS,
            },
        )
        # The card leaves /api/v2/readiness alone.
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

    def test_fixture_and_real_health_share_one_build_contract(self) -> None:
        # G1
        # G3
        real_result = subprocess.run(_probe({"path": HEALTH}), env=_env(SHA), **RUN)
        fixture_result = subprocess.run(_probe({"path": HEALTH}), env=_env(SHA, fixture_mode=True), **RUN)
        [real] = _responses(real_result)
        [fixture] = _responses(fixture_result)

        self.assertEqual(_build(real), {"revision": SHA[:12]})
        self.assertEqual(_build(fixture), {"revision": FIXTURE_REVISION[:12]})
        self.assertEqual(set(fixture["body"]) - set(real["body"]), set(FIXTURE_MARKERS))
        self.assertLessEqual(set(real["body"]), set(fixture["body"]))
        for body in (real["body"], fixture["body"]):
            self.assertEqual(body["build"], {"revision": body["revision"][:12]})

    def test_existing_health_tests_follow_the_new_contract(self) -> None:
        # G3
        # Card #1's tests (the unit test and its acceptance suite) must pass against the new contract.
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "unittest",
                "tests.test_server_v2_health",
                "tests.acceptance.test_card1_health_build",
            ],
            env=_env(None),
            cwd=REPO,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )

        self.assertEqual(result.returncode, 0, f"card #1 health tests failed:\n{result.stderr[-6000:]}")


if __name__ == "__main__":
    unittest.main()
