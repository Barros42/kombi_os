#!/bin/bash
# Script: install.sh
# Description: Installs the Kombi O.S. telemetry service using systemd (service + timer)

set -euo pipefail

SERVICE_NAME="kombios-telemetry-service"
USER_NAME="kombios"
GROUP_NAME="kombios"

BASE_DIR="/usr/local/bin/kombios"
SCRIPT_SRC="./${SERVICE_NAME}.py"
SCRIPT_DST="${BASE_DIR}/${SERVICE_NAME}.py"

SERVICE_SRC="./${SERVICE_NAME}.service"
TIMER_SRC="./${SERVICE_NAME}.timer"

SERVICE_DST="/etc/systemd/system/${SERVICE_NAME}.service"
TIMER_DST="/etc/systemd/system/${SERVICE_NAME}.timer"

LOG_DIR="/var/log/kombios/telemetry"
LOG_FILE="${LOG_DIR}/current.data"

echo "=== Starting installation for ${SERVICE_NAME} ==="

########################################
# Preconditions
########################################
if [ ! -f "${SCRIPT_SRC}" ]; then
  echo "[ERROR] Python script not found: ${SCRIPT_SRC}" >&2
  exit 2
fi

if [ ! -f "${SERVICE_SRC}" ]; then
  echo "[ERROR] Service unit not found: ${SERVICE_SRC}" >&2
  exit 2
fi

if [ ! -f "${TIMER_SRC}" ]; then
  echo "[ERROR] Timer unit not found: ${TIMER_SRC}" >&2
  exit 2
fi

########################################
# Create directories
########################################
echo "Creating directories"
sudo mkdir -p "${BASE_DIR}"
sudo mkdir -p "${LOG_DIR}"

sudo chmod 0755 "${BASE_DIR}"
sudo chmod 0755 "${LOG_DIR}"

sudo chown -R "${USER_NAME}:${GROUP_NAME}" "${BASE_DIR}" "${LOG_DIR}"

########################################
# Create data file (optional)
########################################
echo "Ensuring telemetry data file"
sudo touch "${LOG_FILE}"
sudo chown "${USER_NAME}:${GROUP_NAME}" "${LOG_FILE}"
sudo chmod 0644 "${LOG_FILE}"

########################################
# Install Python script
########################################
echo "Installing Python script"
sudo install -m 0755 -o "${USER_NAME}" -g "${GROUP_NAME}" "${SCRIPT_SRC}" "${SCRIPT_DST}"

########################################
# Install systemd unit files
########################################
echo "Installing systemd unit files"
sudo install -m 0644 "${SERVICE_SRC}" "${SERVICE_DST}"
sudo install -m 0644 "${TIMER_SRC}" "${TIMER_DST}"

########################################
# Reload systemd and clear failed state
########################################
echo "Reloading systemd daemon"
sudo systemctl daemon-reload
sudo systemctl reset-failed "${SERVICE_NAME}.service" "${SERVICE_NAME}.timer" 2>/dev/null || true

########################################
# Enable & start timer
########################################
echo "Enabling + starting timer"
sudo systemctl enable --now "${SERVICE_NAME}.timer"

########################################
# Optional: run service once now (to validate)
# Comment these 2 lines if you ONLY want timer-driven runs.
########################################
echo "Running service once to validate (best effort)"
sudo systemctl start "${SERVICE_NAME}.service" || true

########################################
# Status checks
########################################
echo "Timer status:"
sudo systemctl status "${SERVICE_NAME}.timer" --no-pager || true

echo "Service status:"
sudo systemctl status "${SERVICE_NAME}.service" --no-pager || true

echo "Recent logs:"
sudo journalctl -u "${SERVICE_NAME}.service" -n 50 --no-pager || true

echo "=== Installation complete for ${SERVICE_NAME} ==="
