#!/usr/bin/env python3
"""Capture reproducible host, ROS 2, Gazebo, and Git metadata as JSON."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
from typing import Sequence


def command_output(
    command: Sequence[str], *, cwd: Path | None = None, timeout: float = 5.0
) -> str | None:
    """Run a read-only probe and return combined output, or None if unavailable."""
    try:
        result = subprocess.run(
            list(command),
            cwd=str(cwd) if cwd is not None else None,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def package_version(distribution: str) -> str | None:
    """Return an installed Python distribution version without importing it."""
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return None


def detect_gazebo_version() -> dict[str, str | None]:
    """Probe current Gazebo Sim first, then the legacy Gazebo Classic CLI."""
    probes = (
        (["gz", "sim", "--versions"], "gz sim --versions"),
        (["gz", "sim", "--version"], "gz sim --version"),
        (["gazebo", "--version"], "gazebo --version"),
    )
    for command, label in probes:
        output = command_output(command)
        if output:
            return {"command": label, "version": output}
    return {"command": None, "version": None}


def os_metadata() -> dict[str, str | None]:
    try:
        release = platform.freedesktop_os_release()
    except (AttributeError, OSError):
        release = {}
    return {
        "name": release.get("PRETTY_NAME") or platform.system() or None,
        "id": release.get("ID"),
        "version": release.get("VERSION_ID"),
        "kernel": platform.release() or None,
        "platform": platform.platform() or None,
    }


def capture_environment(repo: Path = Path(".")) -> dict:
    """Collect metadata without changing the host or repository."""
    repo = repo.resolve()
    commit_sha = command_output(["git", "rev-parse", "HEAD"], cwd=repo)
    branch = command_output(["git", "branch", "--show-current"], cwd=repo)
    git_status = command_output(
        ["git", "status", "--porcelain=v1", "--untracked-files=normal"],
        cwd=repo,
    )
    if git_status is None:
        worktree_state = "unknown"
    elif git_status == "":
        worktree_state = "clean"
    else:
        worktree_state = "dirty"

    return {
        "schema_version": 1,
        "captured_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "host": os_metadata(),
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
        },
        "ros2": {
            "distribution": os.environ.get("ROS_DISTRO") or None,
            "cli_package_version": package_version("ros2cli"),
        },
        "gazebo": detect_gazebo_version(),
        "git": {
            "commit_sha": commit_sha or None,
            "branch": branch or None,
            "working_tree": worktree_state,
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/environment.json"),
        help="JSON output path (default: artifacts/environment.json)",
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path("."),
        help="Git repository to inspect (default: current directory)",
    )
    args = parser.parse_args(argv)

    result = capture_environment(args.repo)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
