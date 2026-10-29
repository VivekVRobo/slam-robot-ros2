import json

from tools import capture_environment


def _fake_probe(status=""):
    values = {
        ("git", "rev-parse", "HEAD"): "abc123def456",
        ("git", "branch", "--show-current"): "feature/test",
        ("git", "status", "--porcelain=v1", "--untracked-files=normal"): status,
    }

    def fake(command, *, cwd=None, timeout=5.0):
        return values.get(tuple(command))

    return fake


def test_capture_environment_records_ros_git_and_host(monkeypatch, tmp_path):
    monkeypatch.setenv("ROS_DISTRO", "lyrical")
    monkeypatch.setattr(capture_environment, "command_output", _fake_probe())
    monkeypatch.setattr(capture_environment, "package_version", lambda name: "0.35.0")
    monkeypatch.setattr(
        capture_environment,
        "detect_gazebo_version",
        lambda: {"command": "gz sim --versions", "version": "Gazebo Sim, version 8.0.0"},
    )

    data = capture_environment.capture_environment(tmp_path)

    assert data["schema_version"] == 1
    assert data["ros2"] == {"distribution": "lyrical", "cli_package_version": "0.35.0"}
    assert data["git"] == {
        "commit_sha": "abc123def456",
        "branch": "feature/test",
        "working_tree": "clean",
    }
    assert data["gazebo"]["version"] == "Gazebo Sim, version 8.0.0"
    assert data["host"]["kernel"]
    assert data["python"]["version"]


def test_dirty_and_unavailable_git_states_are_explicit(monkeypatch, tmp_path):
    monkeypatch.setattr(capture_environment, "command_output", _fake_probe(" M README.md"))
    monkeypatch.setattr(capture_environment, "package_version", lambda name: None)
    monkeypatch.setattr(
        capture_environment,
        "detect_gazebo_version",
        lambda: {"command": None, "version": None},
    )
    dirty = capture_environment.capture_environment(tmp_path)
    assert dirty["git"]["working_tree"] == "dirty"

    monkeypatch.setattr(capture_environment, "command_output", lambda *a, **k: None)
    unavailable = capture_environment.capture_environment(tmp_path)
    assert unavailable["git"]["commit_sha"] is None
    assert unavailable["git"]["working_tree"] == "unknown"
    assert unavailable["gazebo"]["version"] is None


def test_gazebo_probe_falls_back_to_legacy_cli(monkeypatch):
    seen = []

    def fake(command, *, cwd=None, timeout=5.0):
        seen.append(tuple(command))
        if tuple(command) == ("gazebo", "--version"):
            return "Gazebo multi-robot simulator, version 11.13.0"
        return None

    monkeypatch.setattr(capture_environment, "command_output", fake)
    result = capture_environment.detect_gazebo_version()
    assert result == {
        "command": "gazebo --version",
        "version": "Gazebo multi-robot simulator, version 11.13.0",
    }
    assert seen == [
        ("gz", "sim", "--versions"),
        ("gz", "sim", "--version"),
        ("gazebo", "--version"),
    ]


def test_cli_writes_json_to_selected_artifact_path(monkeypatch, tmp_path):
    expected = {
        "schema_version": 1,
        "git": {"commit_sha": "abc123", "working_tree": "clean"},
    }
    monkeypatch.setattr(capture_environment, "capture_environment", lambda repo: expected)
    output = tmp_path / "artifacts" / "environment.json"

    assert capture_environment.main(["--repo", str(tmp_path), "--output", str(output)]) == 0
    assert json.loads(output.read_text(encoding="utf-8")) == expected
