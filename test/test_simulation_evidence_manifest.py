from pathlib import Path

from tools.simulation_evidence_manifest import lint


def valid_manifest() -> dict:
    return {
        "simulation_run": {
            "run_id": "2026-09-07_gazebo_loop_square_deadbee",
            "date": "2026-09-07",
            "commit_sha": "deadbee",
            "simulation": True,
            "physical_hardware": False,
            "scenario": "gazebo_loop_square",
            "environment": {
                "os": "Ubuntu",
                "kernel": "test",
                "cpu": "test-cpu",
                "ram": "16 GiB",
                "ros_distro": "lyrical",
                "gazebo_version": "test",
                "mode": "headless",
            },
            "commands": {"launch": "ros2 launch ..."},
            "topics": ["/scan", "/odom", "/ground_truth/odom", "/tf", "/tf_static", "/map", "/clock"],
            "artifacts": {
                "trajectory": "trajectory.csv",
                "trajectory_metrics": "trajectory-metrics.json",
                "loop_metrics": "loop-metrics.json",
                "resource_profile": "resource-profile.json",
                "map_image": "map.pgm",
                "map_metadata": "map.yaml",
                "replay_notes": "replay.md",
            },
        }
    }


def test_valid_manifest_passes_without_file_check():
    assert lint(valid_manifest(), Path("."), check_files=False) == []


def test_manifest_rejects_hardware_claim_and_missing_topic():
    data = valid_manifest()
    data["simulation_run"]["physical_hardware"] = True
    data["simulation_run"]["topics"].remove("/ground_truth/odom")
    errors = lint(data, Path("."), check_files=False)
    assert "simulation_run.physical_hardware must be false" in errors
    assert "missing required runtime topic: /ground_truth/odom" in errors


def test_manifest_rejects_invalid_sha():
    data = valid_manifest()
    data["simulation_run"]["commit_sha"] = "not-a-sha"
    assert any("commit_sha" in error for error in lint(data, Path("."), check_files=False))
