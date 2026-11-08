#!/usr/bin/env python3
"""Capture reproducibility metadata for a Gazebo/ROS 2 simulation run."""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def run_command(*args: str) -> dict[str, object]:
    if shutil.which(args[0]) is None:
        return {"available": False, "command": list(args), "stdout": "", "stderr": "executable not found"}
    try:
        result = subprocess.run(args, check=False, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"available": True, "command": list(args), "stdout": "", "stderr": str(exc)}
    return {
        "available": True,
        "command": list(args),
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def git_metadata() -> dict[str, object]:
    sha = run_command("git", "rev-parse", "HEAD")
    status = run_command("git", "status", "--porcelain")
    return {
        "commit_sha": sha["stdout"] if sha.get("returncode") == 0 else None,
        "working_tree": "clean" if status.get("returncode") == 0 and not status.get("stdout") else "dirty",
        "status_error": status.get("stderr") if status.get("returncode") != 0 else None,
    }


def parse_os_release() -> dict[str, str]:
    path = Path("/etc/os-release")
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        values[key] = value.strip().strip('"')
    return values


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--scenario", default="unspecified")
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    ros2 = run_command("ros2", "--version")
    gazebo = run_command("gz", "sim", "--version")
    if not gazebo.get("available"):
        gazebo = run_command("gz", "--version")

    cpu = run_command("nproc")
    ram = run_command("free", "-b")
    os_release = parse_os_release()

    data = {
        "schema_version": 1,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "host": {
            "hostname": socket.gethostname(),
            "os": os_release.get("PRETTY_NAME") or platform.platform(),
            "kernel": platform.release(),
            "architecture": platform.machine(),
            "cpu_model": platform.processor() or None,
            "logical_cpus": int(cpu["stdout"]) if cpu.get("returncode") == 0 and str(cpu.get("stdout", "")).isdigit() else None,
            "memory_bytes": None,
        },
        "software": {
            "python": platform.python_version(),
            "ros_2_distribution": os.environ.get("ROS_DISTRO"),
            "ros2_version": ros2,
            "gazebo_version": gazebo,
        },
        "repository": git_metadata(),
        "benchmark": {"scenario": args.scenario, "headless": args.headless},
    }

    if ram.get("returncode") == 0:
        for line in str(ram.get("stdout", "")).splitlines():
            parts = line.split()
            if parts and parts[0] == "Mem:" and len(parts) >= 2:
                try:
                    data["host"]["memory_bytes"] = int(parts[1])
                except ValueError:
                    pass

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(data, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
