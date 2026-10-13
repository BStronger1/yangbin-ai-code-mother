#!/usr/bin/env bash
set -euo pipefail
APP_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
if ! tmux has-session -t yangbin-code 2>/dev/null; then exit 0; fi
tmux send-keys -t yangbin-code C-c
for i in $(seq 1 150); do
  if ! tmux has-session -t yangbin-code 2>/dev/null; then echo "Stopped yangbin-code"; exit 0; fi
  sleep 1
done
echo "Graceful shutdown is still in progress; inspect application logs." >&2
exit 1
