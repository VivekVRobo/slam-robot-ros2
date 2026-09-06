from pathlib import Path
import yaml
from slam_robot_ros2.contracts import validate_robot_contract

ROOT = Path(__file__).resolve().parents[1]

def test_robot_contract_is_valid():
    data = yaml.safe_load((ROOT / "config/robot.yaml").read_text())
    assert validate_robot_contract(data) == []

def test_bad_topic_is_rejected():
    data = yaml.safe_load((ROOT / "config/robot.yaml").read_text())
    data["topics"]["scan"] = "scan"
    assert any("scan" in error for error in validate_robot_contract(data))
