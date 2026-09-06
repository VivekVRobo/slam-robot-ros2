#!/usr/bin/env python3
from pathlib import Path
import argparse, sys, yaml

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]

def generate(root: Path = ROOT) -> str:
    robot = yaml.safe_load((root / "config/robot.yaml").read_text(encoding="utf-8"))
    frames = robot["frames"]; topics = robot["topics"]; val = robot["validation"]
    lines = [
        "# SLAM Robot Engineering Report", "",
        f"- Reference ROS distribution: **{robot['project']['reference_ros_distro']}**",
        f"- Project status: **{robot['project']['status']}**",
        f"- TF contract: `{frames['map']} -> {frames['odom']} -> {frames['base_footprint']} -> {frames['base_link']} -> {frames['laser']}`",
        f"- Scan topic: `{topics['scan']}`",
        f"- Odometry topic: `{topics['odom']}`", "",
        "## Validation state", "",
    ]
    lines += [f"- {'✅' if value else '❌'} `{key}`" for key, value in val.items()]
    return "\n".join(lines) + "\n"

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, default=Path("artifacts/engineering-report.md"))
    a = p.parse_args()
    text = generate()
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(text, encoding="utf-8")
    print(text)

if __name__ == "__main__":
    main()
