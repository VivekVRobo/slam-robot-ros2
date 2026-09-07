# WSL2 path for real Gazebo evidence

This project can produce legitimate **simulation runtime evidence** before physical robot hardware exists. The recommended Windows path is WSL2 with Ubuntu matching the ROS 2 Lyrical support matrix.

## Supported baseline

ROS 2 Lyrical is the current stable ROS 2 release documented for Ubuntu Resolute (26.04). The ROS documentation also provides a Gazebo tutorial for Lyrical using the current Gazebo stack (`gz sim`).

Official references:

- ROS 2 Lyrical Ubuntu installation: https://docs.ros.org/en/lyrical/Installation/Alternatives/Ubuntu-Install-Binary.html
- ROS 2 Lyrical Gazebo setup: https://docs.ros.org/en/ros2_documentation/lyrical/Tutorials/Advanced/Simulators/Gazebo/Gazebo.html
- Microsoft WSL GUI support: https://learn.microsoft.com/windows/wsl/tutorials/gui-apps

For benchmark evidence, prefer the repository's **headless** simulation path even if WSLg is available. Headless execution reduces presentation/display variability and keeps the evidence focused on ROS/Gazebo runtime behavior rather than GUI performance.

## Preflight

From PowerShell, verify WSL2 is current:

```powershell
wsl --update
wsl --status
wsl -l -v
```

Inside the Linux distribution, verify:

```bash
uname -a
cat /etc/os-release
ros2 --help >/dev/null
gz sim --version
printf 'ROS_DISTRO=%s\n' "${ROS_DISTRO:-unset}"
```

The evidence campaign intentionally fails if the expected ROS environment is not sourced or the working tree is dirty.

## Build and run

After installing the ROS/Gazebo dependencies required by the repository:

```bash
source /opt/ros/lyrical/setup.bash
bash scripts/run_simulation_evidence_campaign.sh
```

The campaign performs a clean package build, launches the existing headless Gazebo benchmark, records the runtime artifacts, computes the benchmark metrics, captures host provenance, hashes the evidence files, and validates the generated simulation manifest.

Output is staged under:

```text
artifacts/evidence/<run-id>/
```

A run is not automatically promoted into committed recruiter evidence. Review the generated logs and metrics first.

## Evidence boundary

A WSL2 run may support claims such as:

> The documented commit successfully executed the named ROS 2/Gazebo benchmark in the recorded WSL2 environment and produced the archived trajectory, map, and metrics.

It does **not** support claims about:

- physical LiDAR accuracy;
- wheel encoder accuracy;
- real robot localization quality;
- real-time guarantees on embedded hardware;
- native-Linux performance equivalence;
- physical navigation robustness.

When native Linux or physical hardware becomes available, record it as a separate evidence tier rather than overwriting the WSL2 result.
