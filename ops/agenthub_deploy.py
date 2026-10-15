#!/usr/bin/env python3
"""Single-command homeserver API deploy/rollback for the agenthub executor.

Usage:
    ops/agenthub_deploy.py deploy <40-hex-sha>
    ops/agenthub_deploy.py rollback <40-hex-sha>

The executor runs this file from a `git archive <sha>` tree (no `.git`) and
then polls `/api/v2/health` for `revision == sha`. Exit codes:

    0  success (also for an idempotent re-run of an already-live revision)
    1  failed; the previous container is serving again (or was never stopped)
    2  invalid invocation or configuration; nothing was touched
    3  failed and the previous container could NOT be confirmed healthy

Every host-specific value comes from the environment (see
docs/operations/runbook.md, "agenthub executor deploy"); the defaults are the
production values already used by ops/homeserver_sync.sh and the deploy gate.
The production container's environment carries credentials, so it is copied
only into a 0600 file on tmpfs that is removed immediately after `docker run`.
Nothing in this file prints environment values, env-file contents, or the
configured paths/URLs.
"""
from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import traceback

REPO_ROOT = Path(__file__).resolve().parents[1]
GATE_SCRIPT = REPO_ROOT / "ops" / "complete_homeserver_api_deploy.sh"
SYNC_BUILD_SCRIPT = REPO_ROOT / "ops" / "build_sync_image.sh"

SHA_PATTERN = re.compile(r"[0-9a-f]{40}")
PREFIX_PATTERN = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*")
REVISION_LABEL = "ai.caddie.source-revision"
API_REPOSITORY = "garmin-ai-caddie-api"
SYNC_REPOSITORY = "aicaddie-sync"
PRIVATE_ROOT = "/var/lib/ai-caddie"
CONTAINER_PORT = "9000"
STOP_TIMEOUT_SECONDS = "30"
SYNC_CHECK_MARKER = "sync contract ok (check-only)"

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2
EXIT_UNRECOVERED = 3

# Explicit projections keep other projects' container environments out of
# this process; only the production container's Env is read, separately.
CONTAINER_FORMAT = (
    '{"id":{{json .Id}},"name":{{json .Name}},"image":{{json .Image}},'
    '"labels":{{json .Config.Labels}},"running":{{json .State.Running}},'
    '"finishedAt":{{json .State.FinishedAt}},'
    '"ports":{{json .HostConfig.PortBindings}},'
    '"network":{{json .HostConfig.NetworkMode}},"mounts":{{json .Mounts}},'
    '"memory":{{json .HostConfig.Memory}},"nanoCpus":{{json .HostConfig.NanoCpus}}}'
)
ENV_FORMAT = "{{json .Config.Env}}"
IMAGE_FORMAT = '{"id":{{json .Id}},"tags":{{json .RepoTags}},"labels":{{json .Config.Labels}}}'

# Overrides applied on top of the copied production environment, matching the
# exact-revision deploy controller used before agenthub.
FIXED_ENV = {
    "AI_CADDIE_PRIVATE_ROOT": PRIVATE_ROOT,
    "AI_CADDIE_TOPO_RENDER_PROCESSES": "2",
    "PORT": CONTAINER_PORT,
}

# Caller variables that would bypass the revision binding of the helpers.
UNSAFE_CHILD_ENV = ("API_IMAGE", "SYNC_IMAGE_TAG", "PUBLISH_LATEST", "AICADDIE_SYNC_IMAGE")


class DeployError(Exception):
    """A failure whose message is safe to print (no environment values)."""


class ConfigError(DeployError):
    pass


class Interrupted(DeployError):
    pass


class CutoverFailed(DeployError):
    def __init__(self, message: str, restored: bool | None):
        super().__init__(message)
        self.restored = restored  # None: there was no previous container


def log(message: str) -> None:
    print(f"agenthub-deploy: {message}", flush=True)


# ---------------------------------------------------------------------------
# Configuration


class Config:
    def __init__(self, env: dict[str, str]):
        self.port = _int(env, "AICADDIE_API_PORT", 39055, minimum=1, maximum=65535)
        self.prefix = env.get("AICADDIE_CONTAINER_PREFIX") or "aicaddie-release-"
        if not PREFIX_PATTERN.fullmatch(self.prefix):
            raise ConfigError("AICADDIE_CONTAINER_PREFIX must be a valid container name prefix")
        self.network = env.get("AICADDIE_DEPLOY_NETWORK") or "garmin-ai-caddie_default"
        self.volume = env.get("AICADDIE_PRIVATE_VOLUME") or "garmin-ai-caddie_ai-caddie-private"
        self.lock_path = env.get("AICADDIE_SYNC_LOCK") or "/tmp/aicaddie-sync.lock"
        self.sync_script = env.get("AICADDIE_SYNC_SCRIPT") or ""
        self.public_health_url = env.get("AICADDIE_DEPLOY_PUBLIC_HEALTH_URL") or ""
        self.bootstrap_env_file = env.get("AICADDIE_DEPLOY_BOOTSTRAP_ENV_FILE") or ""
        self.keep_stopped = _int(env, "AICADDIE_DEPLOY_KEEP_STOPPED", 2, minimum=1)
        self.default_cpus = _float(env, "AICADDIE_DEPLOY_DEFAULT_CPUS", 2.0, positive=True)
        self.default_memory = _int(env, "AICADDIE_DEPLOY_DEFAULT_MEMORY_BYTES", 3 * 1024**3, minimum=1)
        self.health_timeout = _float(env, "AICADDIE_DEPLOY_HEALTH_TIMEOUT_SECONDS", 180.0)
        self.public_timeout = _float(env, "AICADDIE_DEPLOY_PUBLIC_HEALTH_TIMEOUT_SECONDS", 60.0)
        self.lock_timeout = _float(env, "AICADDIE_DEPLOY_LOCK_TIMEOUT_SECONDS", 900.0)
        self.poll = _float(env, "AICADDIE_DEPLOY_POLL_SECONDS", 2.0)

    @property
    def local_health_url(self) -> str:
        return f"http://127.0.0.1:{self.port}/api/v2/health"


def _int(env, name, default, *, minimum, maximum=None):
    raw = env.get(name)
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ConfigError(f"{name} must be an integer") from None
    if value < minimum or (maximum is not None and value > maximum):
        raise ConfigError(f"{name} is out of range")
    return value


def _float(env, name, default, *, positive=False):
    raw = env.get(name)
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        raise ConfigError(f"{name} must be a number") from None
    if value != value or value < 0 or (positive and value == 0):
        raise ConfigError(f"{name} is out of range")
    return value


# ---------------------------------------------------------------------------
# Process and Docker helpers


def child_env(**extra: str) -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if key not in UNSAFE_CHILD_ENV}
    env.update(extra)
    return env


def run(args, *, label, capture=False, quiet=False, env=None, check=True):
    """Run a command; a failure reports only `label`, never the arguments."""
    result = subprocess.run(
        args, cwd=REPO_ROOT, env=env, text=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.DEVNULL if quiet else None,
    )
    if check and result.returncode != 0:
        raise DeployError(f"{label} failed (exit {result.returncode})")
    return result


def docker(*args, label=None, capture=False, quiet=False, check=True):
    return run(["docker", *args], label=label or f"docker {args[0]}",
               capture=capture, quiet=quiet, check=check)


def _finished_key(value: str) -> tuple[str, float]:
    # Docker trims trailing zeros from the fraction, so compare it numerically.
    match = re.fullmatch(r"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(\.\d+)?Z", value)
    return (match[1], float(match[2] or 0)) if match else ("", 0.0)


class Container:
    def __init__(self, data: dict):
        self.id = data["id"]
        self.name = data["name"].lstrip("/")
        self.image_id = data.get("image") or ""
        self.labels = data.get("labels") or {}
        self.running = bool(data.get("running"))
        self.finished_key = _finished_key(data.get("finishedAt") or "")
        self.ports = data.get("ports") or {}
        self.network = data.get("network") or ""
        self.mounts = data.get("mounts") or []
        self.memory = int(data.get("memory") or 0)
        self.nano_cpus = int(data.get("nanoCpus") or 0)

    @property
    def revision(self) -> str:
        return self.labels.get(REVISION_LABEL, "")

    def publishes(self, port: int) -> bool:
        return any(
            str(binding.get("HostPort")) == str(port)
            for bindings in self.ports.values()
            for binding in (bindings or [])
        )


def list_containers() -> list[Container]:
    ids = docker("ps", "-a", "--no-trunc", "--format", "{{.ID}}", capture=True).stdout.split()
    if not ids:
        return []
    output = docker("inspect", "--format", CONTAINER_FORMAT, *ids, capture=True).stdout
    return [Container(json.loads(line)) for line in output.splitlines() if line.strip()]


def container_env(name: str) -> list[str]:
    output = docker("inspect", "--format", ENV_FORMAT, name, capture=True).stdout
    return json.loads(output) or []


def image_info(reference: str) -> dict | None:
    result = docker("image", "inspect", "--format", IMAGE_FORMAT, reference,
                    capture=True, quiet=True, check=False)
    if result.returncode != 0:
        return None
    info = json.loads(result.stdout)
    info["labels"] = info.get("labels") or {}
    info["tags"] = info.get("tags") or []
    return info


def image_revision(reference: str) -> str:
    info = image_info(reference)
    return info["labels"].get(REVISION_LABEL, "") if info else ""


def fetch_health(url: str) -> dict | None:
    # curl's own error text may echo the URL, so it is discarded.
    result = subprocess.run(
        ["curl", "--fail", "--silent", "--max-time", "5", url],
        stdin=subprocess.DEVNULL, capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    try:
        data = json.loads(result.stdout)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def wait_health(url: str, revision: str, timeout: float, poll: float) -> bool:
    deadline = time.monotonic() + timeout
    while True:
        data = fetch_health(url)
        if data and data.get("status") == "ok" and data.get("revision") == revision:
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(poll)


class SyncLock:
    """The same flock the sync cron takes, so no sync runs during a switch."""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.handle = None

    def __enter__(self):
        self.handle = open(self.cfg.lock_path, "a")
        deadline = time.monotonic() + self.cfg.lock_timeout
        while True:
            try:
                fcntl.flock(self.handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                log("sync lock acquired")
                return self
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    self.handle.close()
                    raise DeployError("sync lock was not acquired in time; a sync is still running") from None
                time.sleep(min(max(self.cfg.poll, 0.05), 1.0))

    def __exit__(self, *exc):
        fcntl.flock(self.handle, fcntl.LOCK_UN)
        self.handle.close()
        log("sync lock released")
        return False


class PrivateDir:
    """A 0700 tmpfs directory for the env file and helper logs."""

    def __enter__(self):
        base = os.environ.get("XDG_RUNTIME_DIR") or ""
        if not base or not os.path.isdir(base):
            base = "/dev/shm"
        if not os.path.isdir(base):
            raise DeployError("no tmpfs directory (XDG_RUNTIME_DIR or /dev/shm) for the private env file")
        self.path = Path(tempfile.mkdtemp(prefix="aicaddie-agenthub-deploy-", dir=base))
        return self.path

    def __exit__(self, *exc):
        shutil.rmtree(self.path, ignore_errors=True)
        return False


def install_signal_handlers() -> None:
    def handler(signum, _frame):
        # Ignore repeats so a restore in progress is not cut short.
        for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
            signal.signal(sig, signal.SIG_IGN)
        raise Interrupted(f"interrupted by signal {signum}")

    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, handler)


# ---------------------------------------------------------------------------
# Shared deploy/rollback steps


def find_current(cfg: Config, containers: list[Container]) -> Container | None:
    on_port = [c for c in containers if c.running and c.publishes(cfg.port)]
    foreign = sorted(c.name for c in on_port if not c.name.startswith(cfg.prefix))
    if foreign:
        raise DeployError(f"the configured port is published by a non-release container: {', '.join(foreign)}")
    if len(on_port) > 1:
        names = ", ".join(sorted(c.name for c in on_port))
        raise DeployError(f"multiple running release containers publish the configured port: {names}")
    return on_port[0] if on_port else None


def assert_layout(cfg: Config, container: Container) -> None:
    mounts = container.mounts
    if not (len(mounts) == 1 and mounts[0].get("Name") == cfg.volume
            and mounts[0].get("Destination") == PRIVATE_ROOT and mounts[0].get("RW")):
        raise DeployError(f"{container.name} does not mount exactly the configured private volume read-write at {PRIVATE_ROOT}")
    if container.network != cfg.network:
        raise DeployError(f"{container.name} is not on the configured network")


def restore_previous(cfg: Config, previous: Container | None) -> bool | None:
    if previous is None:
        log("no previous container to restore")
        return None
    try:
        docker("start", previous.name)
    except DeployError as exc:
        log(f"error: {exc}")
    if wait_health(cfg.local_health_url, previous.revision, cfg.health_timeout, cfg.poll):
        log(f"restored: {previous.name} serves revision {previous.revision}")
        return True
    log(f"error: ROLLBACK NOT CONFIRMED: {previous.name} did not report revision {previous.revision}")
    return False


# ---------------------------------------------------------------------------
# deploy


def ensure_images(sha: str) -> None:
    api_image = f"{API_REPOSITORY}:{sha}"
    if image_revision(api_image) == sha:
        log(f"api image {api_image} present; build skipped")
    else:
        log(f"building api image {api_image}")
        run(["docker", "build", "--label", f"{REVISION_LABEL}={sha}", "-t", api_image,
             "-f", "Dockerfile", "."], label="api image build")
        if image_revision(api_image) != sha:
            raise DeployError(f"{api_image} is not labelled with revision {sha} after the build")

    sync_image = f"{SYNC_REPOSITORY}:{sha}"
    if image_revision(sync_image) == sha:
        log(f"sync image {sync_image} present; build skipped")
    else:
        log(f"building sync image {sync_image}")
        run(["bash", str(SYNC_BUILD_SCRIPT)], label="sync image build",
            env=child_env(API_IMAGE=api_image))
        if image_revision(sync_image) != sha:
            raise DeployError(f"{sync_image} is not labelled with revision {sha} after the build")


def read_env_file(path: str) -> list[str]:
    """Parse a docker --env-file style file (KEY=VALUE, `#` comments)."""
    entries = []
    try:
        lines = Path(path).read_text().splitlines()
    except OSError:
        raise DeployError("the bootstrap env file cannot be read") from None
    for number, line in enumerate(lines, 1):
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            raise DeployError(f"bootstrap env file line {number} is not KEY=VALUE")
        entries.append(stripped)
    return entries


def write_env_file(directory: Path, entries: list[str], sha: str) -> Path:
    values: dict[str, str] = {}
    for entry in entries:
        if "=" not in entry:
            continue
        key, value = entry.split("=", 1)
        values[key] = value
    values.update(FIXED_ENV, AI_CADDIE_BUILD_REVISION=sha)
    path = directory / "api.env"
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as handle:
        for key, value in values.items():
            if not key or any(ch in key for ch in "= \t\r\n") or "\n" in value or "\r" in value:
                raise DeployError("an environment entry cannot be represented in an env file")
            handle.write(f"{key}={value}\n")
    return path


def run_api_container(cfg: Config, name: str, sha: str, env_file: Path,
                      cpus: float, memory: int) -> None:
    try:
        docker("run", "-d", "--init", "--name", name,
               "--restart", "on-failure:3",
               "--cpus", str(cpus), "--memory", str(memory),
               "--network", cfg.network,
               "--log-driver", "json-file", "--log-opt", "max-size=10m", "--log-opt", "max-file=3",
               "--label", f"{REVISION_LABEL}={sha}",
               "--env-file", str(env_file),
               "-p", f"127.0.0.1:{cfg.port}:{CONTAINER_PORT}",
               "-v", f"{cfg.volume}:{PRIVATE_ROOT}",
               f"{API_REPOSITORY}:{sha}", capture=True)
    finally:
        env_file.unlink(missing_ok=True)


def post_checks(cfg: Config, container: str, sha: str, private: Path) -> None:
    run(["bash", str(GATE_SCRIPT)], label="deployment gate (check-only)",
        env=child_env(AICADDIE_DEPLOY_GATE_CHECK_ONLY="1",
                      AICADDIE_API_CONTAINER=container,
                      AICADDIE_API_PORT=str(cfg.port)))
    log("deployment gate (check-only): ok")

    if cfg.sync_script:
        # A private lock/log: this process already holds the real sync lock,
        # and a busy lock would make the sync script skip with exit 0.
        sync_log = private / "sync-check.log"
        run(["bash", cfg.sync_script], label="sync contract (check-only)",
            env=child_env(AICADDIE_SYNC_CHECK_ONLY="1",
                          AICADDIE_API_CONTAINER=container,
                          AICADDIE_API_PORT=str(cfg.port),
                          AICADDIE_SYNC_LOCK=str(private / "sync-check.lock"),
                          AICADDIE_SYNC_LOG=str(sync_log)))
        lines = sync_log.read_text().splitlines() if sync_log.exists() else []
        if not any(line.endswith(SYNC_CHECK_MARKER) for line in lines):
            raise DeployError("sync contract (check-only) did not report success")
        log("sync contract (check-only): ok")
    else:
        log("sync contract (check-only): skipped (AICADDIE_SYNC_SCRIPT not configured)")

    if cfg.public_health_url:
        if not wait_health(cfg.public_health_url, sha, cfg.public_timeout, cfg.poll):
            raise DeployError(f"public health did not report revision {sha}")
        log("public health: ok")
    else:
        log("public health: skipped (AICADDIE_DEPLOY_PUBLIC_HEALTH_URL not configured)")


def check_deploy_source(cfg: Config, current: Container | None) -> None:
    if current is None:
        if not cfg.bootstrap_env_file:
            raise DeployError("no running release container publishes the configured port "
                              "(set AICADDIE_DEPLOY_BOOTSTRAP_ENV_FILE for a first deploy)")
    else:
        assert_layout(cfg, current)


def deploy(cfg: Config, sha: str) -> str:
    new_name = f"{cfg.prefix}{sha[:8]}"
    # Fail fast before the long image builds; everything is re-read under the lock.
    check_deploy_source(cfg, find_current(cfg, list_containers()))
    ensure_images(sha)

    with PrivateDir() as private, SyncLock(cfg):
        containers = list_containers()
        current = find_current(cfg, containers)

        if current is not None and current.revision == sha:
            log(f"{current.name} already runs revision {sha}; verifying only")
            if not wait_health(cfg.local_health_url, sha, cfg.health_timeout, cfg.poll):
                raise DeployError(f"{current.name} runs revision {sha} but its health check fails")
            post_checks(cfg, current.name, sha, private)
            deployed = current.name
        else:
            check_deploy_source(cfg, current)
            if current is None:
                log("no current container; bootstrap deploy from the configured env file")
                entries = read_env_file(cfg.bootstrap_env_file)
                cpus, memory = cfg.default_cpus, cfg.default_memory
            else:
                entries = container_env(current.name)
                cpus = current.nano_cpus / 1e9 if current.nano_cpus else cfg.default_cpus
                memory = current.memory or cfg.default_memory

            residual = next((c for c in containers if c.name == new_name), None)
            if residual is not None:
                if residual.running or residual.revision != sha:
                    raise DeployError(f"{new_name} already exists and is not a stopped revision-{sha[:8]} container")
                log(f"removing stopped residual {new_name}")
                docker("rm", "-v", new_name, capture=True)

            env_file = write_env_file(private, entries, sha)
            try:
                if current is not None:
                    log(f"stopping {current.name}")
                    docker("stop", "--time", STOP_TIMEOUT_SECONDS, current.name, capture=True)
                log(f"starting {new_name}")
                run_api_container(cfg, new_name, sha, env_file, cpus, memory)
                if not wait_health(cfg.local_health_url, sha, cfg.health_timeout, cfg.poll):
                    raise DeployError(f"{new_name} did not report status=ok revision={sha}")
                log(f"{new_name} healthy")
                post_checks(cfg, new_name, sha, private)
            except BaseException as exc:
                reason = str(exc) if isinstance(exc, DeployError) else f"unexpected {type(exc).__name__}"
                log(f"error: {reason}; restoring the previous container")
                env_file.unlink(missing_ok=True)
                removed = docker("rm", "-f", "-v", new_name, capture=True, quiet=True, check=False)
                if removed.returncode == 0:
                    log(f"removed {new_name}")
                restored = restore_previous(cfg, current)
                raise CutoverFailed(reason, restored) from None
            deployed = new_name

    try:
        cleanup(cfg)
    except Exception as exc:  # the new release is live; cleanup is best effort
        reason = str(exc) if isinstance(exc, DeployError) else type(exc).__name__
        log(f"warning: cleanup incomplete: {reason}")
    return deployed


def cleanup(cfg: Config) -> None:
    containers = list_containers()
    stopped = sorted((c for c in containers if c.name.startswith(cfg.prefix) and not c.running),
                     key=lambda c: c.finished_key, reverse=True)
    doomed = stopped[cfg.keep_stopped:]
    if not doomed:
        log(f"cleanup: nothing to remove ({len(stopped)} stopped release container(s) kept)")
        return
    for container in doomed:
        docker("rm", "-v", container.name, capture=True)
        log(f"cleanup: removed container {container.name}")

    doomed_ids = {c.id for c in doomed}
    remaining = [c for c in containers if c.id not in doomed_ids]
    used_images = {c.image_id for c in remaining}
    used_revisions = {c.revision for c in remaining if c.revision}
    handled: set[str] = set()
    for container in doomed:
        candidates = [image_info(container.image_id)] if container.image_id else []
        if SHA_PATTERN.fullmatch(container.revision) and container.revision not in used_revisions:
            candidates.append(image_info(f"{SYNC_REPOSITORY}:{container.revision}"))
        for info in candidates:
            if not info or info["id"] in handled or info["id"] in used_images:
                continue
            handled.add(info["id"])
            repositories = {tag.rsplit(":", 1)[0] for tag in info["tags"]}
            if not info["tags"] or not repositories <= {API_REPOSITORY, SYNC_REPOSITORY}:
                log(f"cleanup: kept image {info['id'][:19]} (untagged or not an api/sync image)")
                continue
            for tag in info["tags"]:
                removed = docker("rmi", tag, capture=True, check=False)
                log(f"cleanup: {'removed' if removed.returncode == 0 else 'could not remove'} image {tag}")


# ---------------------------------------------------------------------------
# rollback


def select_rollback(cfg: Config, sha: str) -> tuple[Container | None, Container | None]:
    """Return (current, target); target is None when sha already serves."""
    containers = list_containers()
    current = find_current(cfg, containers)
    if current is not None and current.revision == sha:
        return current, None
    targets = sorted((c for c in containers if c.name.startswith(cfg.prefix)
                      and not c.running and c.revision == sha),
                     key=lambda c: c.finished_key, reverse=True)
    if not targets:
        raise DeployError(f"no stopped release container is labelled with revision {sha}")
    target = targets[0]
    assert_layout(cfg, target)
    if not target.publishes(cfg.port):
        raise DeployError(f"{target.name} does not publish the configured port")
    sync_image = f"{SYNC_REPOSITORY}:{sha}"
    if image_revision(sync_image) != sha:
        raise DeployError(f"{sync_image} is missing or mislabelled; the sync cron would refuse this revision")
    return current, target


def rollback(cfg: Config, sha: str) -> str:
    select_rollback(cfg, sha)
    with SyncLock(cfg):
        current, target = select_rollback(cfg, sha)
        if target is None:
            if not wait_health(cfg.local_health_url, sha, cfg.health_timeout, cfg.poll):
                raise DeployError(f"{current.name} runs revision {sha} but its health check fails")
            log(f"{current.name} already runs revision {sha}")
            return current.name

        try:
            if current is not None:
                log(f"stopping {current.name}")
                docker("stop", "--time", STOP_TIMEOUT_SECONDS, current.name, capture=True)
            log(f"starting {target.name}")
            docker("start", target.name, capture=True)
            if not wait_health(cfg.local_health_url, sha, cfg.health_timeout, cfg.poll):
                raise DeployError(f"{target.name} did not report status=ok revision={sha}")
        except BaseException as exc:
            reason = str(exc) if isinstance(exc, DeployError) else f"unexpected {type(exc).__name__}"
            log(f"error: {reason}; restoring the previous container")
            docker("stop", "--time", STOP_TIMEOUT_SECONDS, target.name, capture=True, quiet=True, check=False)
            restored = restore_previous(cfg, current)
            raise CutoverFailed(reason, restored) from None
        return target.name


# ---------------------------------------------------------------------------


USAGE = "usage: agenthub_deploy.py {deploy|rollback} <40-lowercase-hex-sha>"


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[0] not in ("deploy", "rollback") or not SHA_PATTERN.fullmatch(argv[1]):
        print(USAGE, file=sys.stderr, flush=True)
        return EXIT_USAGE
    action, sha = argv
    expected = os.environ.get("AGENTHUB_DEPLOY_SHA")
    if expected and expected != sha:
        print("error: argument sha does not match AGENTHUB_DEPLOY_SHA", file=sys.stderr, flush=True)
        return EXIT_USAGE
    try:
        cfg = Config(dict(os.environ))
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr, flush=True)
        return EXIT_USAGE

    install_signal_handlers()
    started = time.monotonic()
    log(f"action={action} revision={sha}")
    try:
        container = deploy(cfg, sha) if action == "deploy" else rollback(cfg, sha)
    except CutoverFailed as exc:
        code = EXIT_UNRECOVERED if exc.restored is False else EXIT_FAILED
        restored = "none" if exc.restored is None else str(exc.restored).lower()
        log(f"result=failed action={action} revision={sha} previous_restored={restored} "
            f"elapsed_s={time.monotonic() - started:.1f} reason={exc}")
        return code
    except DeployError as exc:
        log(f"result=failed action={action} revision={sha} previous_untouched=true "
            f"elapsed_s={time.monotonic() - started:.1f} reason={exc}")
        return EXIT_FAILED
    except Exception as exc:  # report the location, not a message that may carry values
        frame = traceback.extract_tb(exc.__traceback__)[-1]
        log(f"result=failed action={action} revision={sha} previous_untouched=true "
            f"reason=unexpected {type(exc).__name__} in {frame.name} line {frame.lineno}")
        return EXIT_FAILED
    log(f"result=ok action={action} revision={sha} container={container} "
        f"elapsed_s={time.monotonic() - started:.1f}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
