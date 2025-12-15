#!/bin/bash
# Script: install.sh
# Description: Installs the Kombi O.S. telemetry sync service using systemd timer + service

set -euo pipefail

SERVICE_NAME="kombios-telemetry-sync-service"
USER_NAME="kombios"

BASE_DIR="/usr/local/bin/kombios"
SCRIPT_FILE_DST="${BASE_DIR}/${SERVICE_NAME}.py"

SERVICE_FILE_DST="/etc/systemd/system/${SERVICE_NAME}.service"
TIMER_FILE_DST="/etc/systemd/system/${SERVICE_NAME}.timer"

LOG_DIR="/var/log/kombios/telemetry-sync"
STATE_FILE="${LOG_DIR}/.last_hash"

SRC_PY="./${SERVICE_NAME}.py"
SRC_SERVICE="./${SERVICE_NAME}.service"
SRC_TIMER="./${SERVICE_NAME}.timer"

echo "=== Starting installation for ${SERVICE_NAME} ==="

# --- Basic validations (source files) ---
for f in "$SRC_PY" "$SRC_SERVICE" "$SRC_TIMER"; do
  if [ ! -f "$f" ]; then
    echo "ERROR: Missing file: $f" >&2
    exit 2
  fi
done

# --- Ensure directories ---
echo "Creating directories"
sudo mkdir -p "$BASE_DIR" "$LOG_DIR"
sudo chmod 0755 "$BASE_DIR"
sudo chown -R "$USER_NAME:$USER_NAME" "$BASE_DIR" "$LOG_DIR"

# State file (optional)
echo "Creating state file: $STATE_FILE"
sudo touch "$STATE_FILE"
sudo chown "$USER_NAME:$USER_NAME" "$STATE_FILE"
sudo chmod 0644 "$STATE_FILE"

# --- Copy Python script ---
echo "Copying Python script to: $SCRIPT_FILE_DST"
sudo cp "$SRC_PY" "$SCRIPT_FILE_DST"
sudo chown "$USER_NAME:$USER_NAME" "$SCRIPT_FILE_DST"
sudo chmod 0755 "$SCRIPT_FILE_DST"

# --- Install systemd units ---
echo "Installing systemd unit files"
sudo cp "$SRC_SERVICE" "$SERVICE_FILE_DST"
sudo cp "$SRC_TIMER" "$TIMER_FILE_DST"
sudo chmod 0644 "$SERVICE_FILE_DST" "$TIMER_FILE_DST"

# --- Reload systemd ---
echo "Reloading systemd daemon"
sudo systemctl daemon-reload

# --- Sanity check: does the service ExecStart point to the file we installed? ---
echo "Validating unit ExecStart path"
EXECSTART_LINE="$(sudo systemctl cat "${SERVICE_NAME}.service" | sed -n 's/^ExecStart=//p' | head -n 1 || true)"
if [ -z "$EXECSTART_LINE" ]; then
  echo "ERROR: Could not read ExecStart from ${SERVICE_NAME}.service" >&2
  sudo systemctl cat "${SERVICE_NAME}.service" --no-pager || true
  exit 3
fi

# If the service references the expected path, good. Otherwise warn loudly.
if ! echo "$EXECSTART_LINE" | grep -q "${BASE_DIR}/${SERVICE_NAME}.py"; then
  echo "WARN: ExecStart does not reference expected script path."
  echo "      Expected to contain: ${BASE_DIR}/${SERVICE_NAME}.py"
  echo "      ExecStart is: ${EXECSTART_LINE}"
  echo "      Fix your .service or adjust install.sh destination path."
fi

# --- Reset failed state BEFORE starting (so status is clean) ---
sudo systemctl reset-failed "${SERVICE_NAME}.service" "${SERVICE_NAME}.timer" 2>/dev/null || true

# --- Enable & start timer (primary) ---
echo "Enabling and starting timer"
sudo systemctl enable --now "${SERVICE_NAME}.timer"

# --- Force one run now (so you get logs and confirm path) ---
echo "Triggering one manual run of the service (for validation)"
sudo systemctl start "${SERVICE_NAME}.service" || true

# --- Diagnostics ---
echo "Timer state:"
sudo systemctl is-enabled "${SERVICE_NAME}.timer" || true
sudo systemctl is-active "${SERVICE_NAME}.timer" || true
sudo systemctl status "${SERVICE_NAME}.timer" --no-pager || true

echo "Service state:"
sudo systemctl is-enabled "${SERVICE_NAME}.service" || true
sudo systemctl status "${SERVICE_NAME}.service" --no-pager || true

echo "Recent journal (if available):"
sudo journalctl -u "${SERVICE_NAME}.service" -n 50 --no-pager || true

echo "=== Installation complete for ${SERVICE_NAME} ==="
echo "Check:"
echo "  systemctl list-timers | grep ${SERVICE_NAME} || true"
echo "  sudo journalctl -u ${SERVICE_NAME}.service -f"
