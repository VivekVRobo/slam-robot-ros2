#!/usr/bin/env bash
set -euo pipefail

OUT=${1:-artifacts/environment.md}
JSON_OUT=${2:-artifacts/environment.json}
mkdir -p "$(dirname "$OUT")" "$(dirname "$JSON_OUT")"

sha=$(git rev-parse HEAD 2>/dev/null || echo unknown)
branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)
git_status=clean
if [[ -n "$(git status --porcelain 2>/dev/null)" ]]; then
  git_status=dirty
fi
os=$(grep '^PRETTY_NAME=' /etc/os-release 2>/dev/null | cut -d= -f2- | tr -d '"' || uname -s)
kernel=$(uname -a)
cpu=$(awk -F: '/model name/{gsub(/^ +/,"",$2); print $2; exit}' /proc/cpuinfo 2>/dev/null || echo unknown)
ram=$(awk '/MemTotal/{printf "%.1f GiB", $2/1024/1024}' /proc/meminfo 2>/dev/null || echo unknown)
ros=\${ROS_DISTRO:-unknown}
python_version=$(python3 --version 2>&1 || true)
gazebo_version=$(gz sim --versions 2>/dev/null | head -n 1 || gz sim --version 2>/dev/null | head -n 1 || echo unavailable)
wsl=no
if grep -qi microsoft /proc/version 2>/dev/null; then wsl=yes; fi

python3 - "$JSON_OUT" <<PY
import json
import sys

data = {
    "git_commit": "$sha",
    "git_branch": "$branch",
    "git_worktree": "$git_status",
    "os": "$os",
    "kernel": "$kernel",
    "cpu": "$cpu",
    "ram": "$ram",
    "ros_distribution": "$ros",
    "python_version": "$python_version",
    "gazebo_version": "$gazebo_version",
    "wsl_detected": "$wsl",
}
with open(sys.argv[1], "w", encoding="utf-8") as fh:
    json.dump(data, fh, indent=2, sort_keys=True)
    fh.write("\n")
PY

cat > "$OUT" <<EOF
# Simulation environment

- Git commit: \`$sha\`
- Git branch: \`$branch\`
- Git worktree: **$git_status**
- OS: $os
- Kernel: \`$kernel\`
- CPU: $cpu
- RAM: $ram
- ROS distribution: \`$ros\`
- Gazebo: \`$gazebo_version\`
- Python: \`$python_version\`
- WSL detected: \`$wsl\`

> This file records execution provenance only. It does not prove that the simulation launched successfully; pair it with runtime topics, artifacts, logs, and the simulation evidence manifest.
EOF

printf 'wrote %s and %s\n' "$OUT" "$JSON_OUT"
