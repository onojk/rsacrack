# Save as: manage_rsacrack.sh
# Usage:
#   ./manage_rsacrack.sh            # stop -> free 8001 -> start -> verify
#   ./manage_rsacrack.sh --status   # just show status and port usage
#   ./manage_rsacrack.sh --dev 5000 # (optional) run app_demo.py on port 5000 (stops service first)

#!/usr/bin/env bash
set -euo pipefail

SERVICE="rsacrack"
PORT="8001"
HTTPS_HOST="https://rsacrack.com"
LOCAL_URL="http://127.0.0.1:${PORT}/healthz"
HTTPS_URL="${HTTPS_HOST}/healthz"

log(){ printf "\033[1;34m[rsacrack]\033[0m %s\n" "$*"; }
warn(){ printf "\033[1;33m[warn]\033[0m %s\n" "$*"; }
err(){ printf "\033[1;31m[err]\033[0m %s\n" "$*" >&2; }

need() { command -v "$1" >/dev/null 2>&1 || { err "Missing '$1'"; exit 1; }; }

show_status(){
  log "systemd service:"
  if systemctl is-active --quiet "$SERVICE"; then
    echo "  -> active"
  else
    echo "  -> inactive"
  fi
  log "processes:"
  (pgrep -fl gunicorn || true)
  log "port ${PORT}:"
  (sudo ss -ltnp | grep ":${PORT}" || echo "  -> free")
}

wait_for_port_free(){
  local tries=20
  while (( tries-- > 0 )); do
    if ! sudo ss -ltnp | grep -q ":${PORT}\b"; then
      return 0
    fi
    sleep 0.2
  done
  return 1
}

free_port(){
  if sudo ss -ltnp | grep -q ":${PORT}\b"; then
    warn "Port ${PORT} still in use; trying to free it"
    if command -v fuser >/dev/null 2>&1; then
      sudo fuser -v "${PORT}/tcp" || true
      sudo fuser -k "${PORT}/tcp" || true
    else
      warn "fuser not found; killing gunicorn as a fallback"
      pkill -f gunicorn || true
    fi
  fi
}

verify_url(){
  local url="$1" tries=20
  while (( tries-- > 0 )); do
    if curl -fsS "$url" | grep -qi 'ok'; then
      log "OK: $url"
      return 0
    fi
    sleep 0.3
  done
  err "FAILED: $url"
  return 1
}

start_service(){
  log "Starting ${SERVICE}…"
  sudo systemctl start "$SERVICE"
  # Wait until port is listening
  local tries=20
  while (( tries-- > 0 )); do
    if sudo ss -ltnp | grep -q ":${PORT}\b"; then
      break
    fi
    sleep 0.3
  done
}

stop_service(){
  if systemctl is-active --quiet "$SERVICE"; then
    log "Stopping ${SERVICE}…"
    sudo systemctl stop "$SERVICE"
  else
    log "${SERVICE} already stopped"
  fi
}

dev_mode(){
  local dev_port="${1:-5000}"
  log "DEV mode: stopping service and running app_demo.py on :${dev_port}"
  stop_service
  free_port
  log "Launching dev server (Ctrl+C to stop)…"
  exec python3 app_demo.py --port "$dev_port"
}

main(){
  need systemctl
  need curl
  need ss

  case "${1:-}" in
    --status)
      show_status
      exit 0
      ;;
    --dev)
      dev_mode "${2:-5000}"
      ;;
  esac

  log "Restarting ${SERVICE} cleanly…"
  stop_service
  free_port
  if ! wait_for_port_free; then
    warn "Port ${PORT} still busy; forcing cleanup again"
    free_port
  fi

  start_service

  log "Verifying health endpoints…"
  verify_url "$LOCAL_URL" || true
  verify_url "$HTTPS_URL" || true

  log "Final status:"
  show_status

  if systemctl is-active --quiet "$SERVICE"; then
    log "Restart complete."
  else
    err "Service is not active. Check: sudo journalctl -u ${SERVICE} -n 200 --no-pager"
    exit 1
  fi
}

main "$@"
