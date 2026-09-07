#!/usr/bin/env python3
"""Validate provenance for a reproducible Gazebo/SLAM simulation evidence bundle."""
from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path

import yaml

REQUIRED_TOPICS = {
    "/scan",
    "/odom",
    "/ground_truth/odom",
    "/tf",
    "/tf_static",
    "/map",
    "/clock",
}
REQUIRED_ARTIFACTS = {
    "trajectory",
    "trajectory_metrics",
    "loop_metrics",
    "resource_profile",
    "map_image",
    "map_metadata",
    "replay_notes",
}
HEX_SHA = re.compile(r"^[0-9a-fA-F]{7,40}$")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def lint(data: dict, base: Path, *, check_files: bool = False) -> list[str]:
    errors: list[str] = []
    run = data.get("simulation_run")
    if not isinstance(run, dict):
        return ["missing simulation_run mapping"]

    for key in ("run_id", "date", "commit_sha", "scenario", "environment", "commands", "artifacts", "topics"):
        if run.get(key) in (None, "", {}, []):
            errors.append(f"missing required run field: {key}")

    if run.get("simulation") is not True:
        errors.append("simulation_run.simulation must be true")
    if run.get("physical_hardware") is not False:
        errors.append("simulation_run.physical_hardware must be false")

    commit_sha = str(run.get("commit_sha", ""))
    if commit_sha and not HEX_SHA.fullmatch(commit_sha):
        errors.append("commit_sha must be a 7-40 character hexadecimal Git SHA")

    environment = run.get("environment")
    if isinstance(environment, dict):
        for key in ("os", "kernel", "cpu", "ram", "ros_distro", "gazebo_version", "mode"):
            if environment.get(key) in (None, ""):
                errors.append(f"missing environment field: {key}")

    topics = set(run.get("topics") or [])
    for topic in sorted(REQUIRED_TOPICS - topics):
        errors.append(f"missing required runtime topic: {topic}")

    artifacts = run.get("artifacts")
    if isinstance(artifacts, dict):
        for key in sorted(REQUIRED_ARTIFACTS):
            if artifacts.get(key) in (None, ""):
                errors.append(f"missing required artifact field: {key}")

        if check_files:
            for key, rel in artifacts.items():
                if not rel or key in {"rosbag_external_uri", "rosbag_sha256"}:
                    continue
                path = (base / str(rel)).resolve()
                if not path.exists():
                    errors.append(f"missing evidence path for {key}: {rel}")

    files = run.get("files", [])
    if files and not isinstance(files, list):
        errors.append("files must be a list")
    elif check_files:
        for item in files:
            if not isinstance(item, dict) or not item.get("path"):
                errors.append("file entry missing path")
                continue
            rel = str(item["path"])
            path = (base / rel).resolve()
            if not path.exists():
                errors.append(f"missing evidence file: {rel}")
                continue
            expected = item.get("sha256")
            if expected and path.is_file() and sha256(path) != expected:
                errors.append(f"sha256 mismatch: {rel}")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--check-files", action="store_true")
    args = parser.parse_args()

    data = yaml.safe_load(args.manifest.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("ERROR: manifest root must be a mapping")
    errors = lint(data, args.manifest.parent, check_files=args.check_files)
    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors))
        raise SystemExit(1)
    print("simulation evidence manifest: PASS")


if __name__ == "__main__":
    main()
