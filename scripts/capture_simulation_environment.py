#!/usr/bin/env python3
"""Capture reproducibility metadata for a Gazebo/SLAM benchmark run."""
from __future__ import annotations
import argparse, json, os, platform, shutil, subprocess
from datetime import datetime, timezone
from pathlib import Path

def run_command(command: list[str]) -> str:
    if shutil.which(command[0]) is None: return "unavailable"
    try: result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired): return "unavailable"
    output = (result.stdout or result.stderr).strip()
    return output.splitlines()[0] if output else "unavailable"

def git_value(args: list[str]) -> str:
    try: result = subprocess.run(["git", *args], check=True, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired): return "unavailable"
    return result.stdout.strip()

def capture(scenario: str, non_default_parameters: str) -> dict:
    commit_sha = git_value(["rev-parse", "HEAD"])
    dirty = bool(git_value(["status", "--porcelain"]))
    version = Path("/proc/version").read_text(encoding="utf-8", errors="ignore").lower() if Path("/proc/version").exists() else ""
    ram = run_command(["bash","-lc","awk '/MemTotal/{printf \"%.1f GiB\\n\", $2/1024/1024}' /proc/meminfo"])
    return {"captured_at_utc": datetime.now(timezone.utc).isoformat(), "git": {"commit_sha": commit_sha, "working_tree": "dirty" if dirty else "clean"}, "scenario": scenario, "environment": {"os": platform.platform(), "kernel": platform.release(), "cpu": platform.processor() or "unavailable", "ram": ram, "python": platform.python_version(), "ros_distro": os.environ.get("ROS_DISTRO", "unset"), "ros2_version": run_command(["ros2","--version"]), "gazebo_version": run_command(["gz","sim","--version"]), "runtime_mode": "wsl2" if "microsoft" in version else "native-linux", "headless": os.environ.get("QT_QPA_PLATFORM") == "offscreen"}, "non_default_parameters": non_default_parameters or "none documented"}

def render_markdown(data: dict) -> str:
    env, git = data["environment"], data["git"]
    return """# Simulation environment capture

- Captured (UTC): {captured_at_utc}
- Commit SHA: `{commit_sha}`
- Working tree: **{working_tree}**
- Scenario: `{scenario}`
- OS: `{os}`
- Kernel: `{kernel}`
- CPU: `{cpu}`
- RAM: `{ram}`
- Python: `{python}`
- ROS 2 distribution: `{ros_distro}`
- ROS 2 version: `{ros2_version}`
- Gazebo version: `{gazebo_version}`
- Runtime mode: `{runtime_mode}`
- Headless: `{headless}`
- Non-default parameters: `{non_default_parameters}`

This file records environment provenance only. It does not establish benchmark quality or physical-hardware validation.
""".format(captured_at_utc=data["captured_at_utc"], commit_sha=git["commit_sha"], working_tree=git["working_tree"], scenario=data["scenario"], **env, non_default_parameters=data["non_default_parameters"])

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--scenario", default=os.environ.get("SCENARIO", "gazebo_loop_square"))
    parser.add_argument("--non-default-parameters", default=os.environ.get("NON_DEFAULT_PARAMETERS", ""))
    args = parser.parse_args()
    data = capture(args.scenario, args.non_default_parameters)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.suffix.lower() == ".json": args.output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    else: args.output.write_text(render_markdown(data), encoding="utf-8")

if __name__ == "__main__": main()