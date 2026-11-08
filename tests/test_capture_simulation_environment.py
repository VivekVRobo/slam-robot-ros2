from __future__ import annotations

import json

from tools.capture_simulation_environment import git_metadata, parse_os_release


def test_git_metadata_reports_current_repository_state():
    metadata = git_metadata()
    assert len(metadata["commit_sha"]) == 40
    assert metadata["working_tree"] in {"clean", "dirty"}


def test_os_release_parser_returns_string_mapping():
    values = parse_os_release()
    assert isinstance(values, dict)
    assert all(isinstance(key, str) and isinstance(value, str) for key, value in values.items())


def test_output_schema_can_be_serialized(tmp_path):
    output = tmp_path / "environment.json"
    data = {
        "schema_version": 1,
        "host": {"kernel": "test"},
        "software": {"python": "3.12"},
        "repository": {"commit_sha": "a" * 40, "working_tree": "clean"},
        "benchmark": {"scenario": "gazebo_loop_square", "headless": True},
    }
    output.write_text(json.dumps(data), encoding="utf-8")
    loaded = json.loads(output.read_text(encoding="utf-8"))
    assert loaded["schema_version"] == 1
    assert loaded["repository"]["working_tree"] == "clean"
