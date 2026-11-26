from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "capture_simulation_environment.py"

def _git_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    (path / "marker.txt").write_text("clean\n", encoding="utf-8")
    subprocess.run(["git", "add", "marker.txt"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-qm", "test"], cwd=path, check=True)

def test_environment_capture_json_is_machine_readable(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    for name, output in (("ros2", "ros2 0.1.0-test"), ("gz", "Gazebo Sim, version 9.0.0-test")):
        path = fake_bin / name
        path.write_text(f"#!/bin/sh\necho '{output}'\n", encoding="utf-8")
        path.chmod(0o755)
    repo = tmp_path / "repo"
    repo.mkdir()
    _git_repo(repo)
    output = tmp_path / "environment.json"
    env = os.environ.copy()
    env["PATH"] = str(fake_bin) + os.pathsep + env["PATH"]
    env["ROS_DISTRO"] = "lyrical"
    subprocess.run(["python3", str(SCRIPT), str(output), "--scenario", "test_scenario", "--non-default-parameters", "headless=true"], cwd=repo, env=env, check=True)
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["git"]["working_tree"] == "clean"
    assert len(data["git"]["commit_sha"]) == 40
    assert data["scenario"] == "test_scenario"
    assert data["environment"]["ros_distro"] == "lyrical"
    assert data["environment"]["ros2_version"] == "ros2 0.1.0-test"
    assert data["environment"]["gazebo_version"] == "Gazebo Sim, version 9.0.0-test"
    assert data["non_default_parameters"] == "headless=true"

def test_environment_capture_reports_dirty_tree(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git_repo(repo)
    (repo / "marker.txt").write_text("dirty\n", encoding="utf-8")
    output = tmp_path / "environment.json"
    subprocess.run(["python3", str(SCRIPT), str(output)], cwd=repo, env=os.environ.copy(), check=True)
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["git"]["working_tree"] == "dirty"