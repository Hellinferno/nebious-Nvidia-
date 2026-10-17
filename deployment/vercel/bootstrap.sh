#!/usr/bin/env bash
set -euo pipefail

mode="${1:?mode required}"
app_root="${2:?application root required}"
runtime_user="${3:?runtime user required}"
[[ "$app_root" == /vercel/sandbox/benchproof ]] || exit 2
[[ "$runtime_user" =~ ^[a-z_][a-z0-9_-]*$ ]] || exit 2
id "$runtime_user" >/dev/null
exec 9>/tmp/benchproof-bootstrap.lock
flock -x 9
state=/data/benchproof
venv="$app_root/.venv"
config="$app_root/origin-config.json"

if [[ "$mode" == prepare ]]; then
    if ! command -v dockerd >/dev/null; then
        apt-get update -qq
        DEBIAN_FRONTEND=noninteractive apt-get install -y -qq docker.io
    fi
    command -v uv >/dev/null
    export UV_PYTHON_INSTALL_DIR="$app_root/.python"
    install -d -m 755 "$UV_PYTHON_INSTALL_DIR"
    uv venv --clear --python 3.12 "$venv"
    uv pip install --python "$venv/bin/python" -r "$app_root/backend/requirements.lock.txt"
    install -d -m 700 -o "$runtime_user" -g "$(id -gn "$runtime_user")" "$state" "$state/runtime" "$state/logs"
elif [[ "$mode" != start ]]; then
    exit 2
fi

control_root=/sys/fs/cgroup
if ! grep -qw memory "$control_root/cgroup.subtree_control"; then
    for directory in "$control_root"/*/; do
        [[ ! -d "$directory" || "$directory" == "$control_root/docker/" || "$directory" == "$control_root/benchproof-services/" ]] || exit 2
    done
    if [[ -d "$control_root/docker" ]]; then
        grep -qx 'populated 0' "$control_root/docker/cgroup.events"
        rmdir "$control_root/docker"
    fi
    echo '-cpuset -cpu -pids' > "$control_root/cgroup.subtree_control"
    mkdir -p "$control_root/benchproof-services"
    for attempt in $(seq 1 10); do
        process_ids=$(cat "$control_root/cgroup.procs")
        [[ -n "$process_ids" ]] || break
        for process_id in $process_ids; do
            echo "$process_id" > "$control_root/benchproof-services/cgroup.procs" || [[ ! -d "/proc/$process_id" ]]
        done
    done
    echo '+cpuset +cpu +memory +pids' > "$control_root/cgroup.subtree_control"
fi
grep -qw memory "$control_root/cgroup.subtree_control"

if ! docker info >/dev/null 2>&1; then
    nohup dockerd --host=unix:///var/run/docker.sock >"$state/logs/docker.log" 2>&1 < /dev/null 9>&- &
    for attempt in $(seq 1 40); do
        docker info >/dev/null 2>&1 && break
        sleep 1
    done
fi
docker info >/dev/null
chown "$runtime_user" /var/run/docker.sock
chmod 660 /var/run/docker.sock
if ! docker image inspect benchproof-candidate:dev >/dev/null 2>&1; then
    docker build -t benchproof-candidate:dev "$app_root/backend/runner/image"
fi

probe() {
    "$venv/bin/python" - "$config" <<'PY'
import json
import sys
import urllib.request
config = json.load(open(sys.argv[1], encoding="utf-8"))
request = urllib.request.Request("http://127.0.0.1:8765/api/v1/ready", headers={"X-BenchProof-Origin": config["origin_token"]})
with urllib.request.urlopen(request, timeout=3) as response:
    ready = json.load(response)
assert ready["runner"]["isolated_execution_available"]
assert ready["provider"]["configured"]
assert ready["worker"]["alive"]
PY
}

if probe >/dev/null 2>&1; then
    exit 0
fi
runuser -u "$runtime_user" -- sh -c 'nohup "$1/bin/python" "$2/deployment/vercel/origin.py" --config "$2/origin-config.json" >"$3/logs/api.log" 2>&1 < /dev/null &' sh "$venv" "$app_root" "$state" 9>&-
for attempt in $(seq 1 45); do
    if probe >/dev/null 2>&1; then
        echo 'Trusted origin, Docker and heartbeat ready'
        exit 0
    fi
    sleep 1
done
echo 'Origin readiness failed; inspect private API log' >&2
exit 1
