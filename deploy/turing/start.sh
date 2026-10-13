#!/usr/bin/env bash
set -euo pipefail
APP_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
test -f "$APP_ROOT/run/configured"
if tmux has-session -t yangbin-code 2>/dev/null; then
  echo "yangbin-code is already running"
  exit 0
fi
tmux new-session -d -s yangbin-code "cd '$APP_ROOT' && umask 077 && exec python3 '$APP_ROOT/deploy/turing/supervise.py'"
echo "Started yangbin-code"
