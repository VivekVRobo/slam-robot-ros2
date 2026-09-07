#!/usr/bin/env bash
set -euo pipefail

OUT=${1:-artifacts/environment.md}
mkdir -p "$(dirname "$OUT")"

sha=$(git rev-parse HEAD 2>/dev/null || echo unknown)
branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)
os=$(grep '^PRETTY_NAME=' /etc/os-release 2>/dev/null | cut -d= -f2- | tr -d '"' || uname -s)
kernel=$(uname -a)
cpu=$(awk -F: '/model name/{gsub(/^ +/,"",$2); print $2; exit}' /proc/cpuinfo 2>/dev/null || echo unknown)
ram=$(awk '/MemTotal/{printf "%.1f GiB", $2/1024/1024}' /proc/meminfo 2>/dev/null || echo unknown)
ros=${ROS_DISTRO:-unknown}
python_version=$(python3 --version 2>&1 || true)
gazebo_version=$(gz sim --versions 2>/dev/null | head -n 1 || gz sim --version 2>/dev/null | head -n 1 || echo unavailable)
wsl=no
if grep -qi microsoft /proc/version 2>/dev/null; then wsl=yes; fi

cat > "$OUT" <<EOF
# Simulation environment

- Git commit: \`$sha\`
- Git branch: \`$branch\`
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

printf 'wrote %s\n' "$OUT"
