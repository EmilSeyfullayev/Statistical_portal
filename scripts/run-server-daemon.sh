#!/usr/bin/env bash
# Start Django detached from any terminal session (survives closing Cursor / IDE).
# Usage: ./scripts/run-server-daemon.sh
# Optional: PORT=8080 ./scripts/run-server-daemon.sh

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PORT="${PORT:-8000}"
LOG="${ROOT}/runserver.log"
PIDFILE="${ROOT}/runserver.pid"
VENV_PY="${ROOT}/.venv/bin/python"

if [[ ! -x "$VENV_PY" ]]; then
  echo "Missing venv Python: ${VENV_PY}" >&2
  exit 1
fi

if ss -tln 2>/dev/null | grep -qE ":${PORT}[[:space:]]"; then
  echo "Port ${PORT} is already in use. Nothing started."
  echo "Listening sockets:"
  ss -tlnp 2>/dev/null | grep -E ":${PORT}[[:space:]]" || true
  exit 0
fi

setsid nohup "${VENV_PY}" -u manage.py runserver "0.0.0.0:${PORT}" --noreload \
  >>"${LOG}" 2>&1 </dev/null &
sleep 1

if ! pgrep -f "manage.py runserver" >/dev/null; then
  echo "Server failed to start. Last lines of ${LOG}:" >&2
  tail -20 "${LOG}" 2>/dev/null || true
  exit 1
fi

pgrep -n -f "manage.py runserver" >"${PIDFILE}"
echo "Django listening on 0.0.0.0:${PORT} (pid $(tr -d '\n' <"${PIDFILE}")). Log: ${LOG}"
