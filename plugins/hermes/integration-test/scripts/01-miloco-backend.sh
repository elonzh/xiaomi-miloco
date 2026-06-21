#!/usr/bin/env bash
set -e

export MILOCO_HOME="${MILOCO_HOME:-/opt/data/miloco}"
mkdir -p "$MILOCO_HOME"

nohup miloco-backend &

for i in $(seq 1 30); do
    if curl -sf http://127.0.0.1:1810/health >/dev/null 2>&1; then
        echo "[miloco-entrypoint] backend ready"
        exit 0
    fi
    sleep 1
done

echo "[miloco-entrypoint] backend failed to start" >&2
exit 1
