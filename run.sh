#!/usr/bin/env bash
# 每 30 分钟由 cron 调用；flock 防止上一次还没跑完时重叠执行。
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec 9>"$ROOT/logs/run.lock"
flock -n 9 || { echo "$(date -Is) another run in progress, skip"; exit 0; }
echo "$(date -Is) run start"
python3 "$ROOT/runner/run_tests.py"
echo "$(date -Is) run end"
