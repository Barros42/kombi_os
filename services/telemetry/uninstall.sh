#!/bin/bash
# Script: uninstall.sh
# Description: Uninstalls the Kombi O.S. telemetry service and timer

set -euo pipefail

SERVICE_NAME="kombios-telemetry-service"
USER_NAME="kombios"

BASE_DIR="/usr/local/bin/kombios"
SCRIPT_FILE="${BASE_DIR}/${SERVICE_NAME}.py"

SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
TIMER_FILE="/etc/systemd/system/${SERVICE_NAME}.timer"

LOG_DIR="/var/log/kombios/telemetry"
LOG_FILE="${LOG_DIR}/current.data"

echo "=== Starting uninstallation for ${SERVICE_NAME} ==="

# Stop/disable timer and service (best effort)
echo "Stopping/disabling systemd units (best effort)"
sudo systemctl disable --now "${SERVICE_NAME}.timer" 2>/dev/null || true
sudo systemctl stop "${SERVICE_NAME}.timer" 2>/dev/null || true

# Service is oneshot; disable/stop best effort anyway
sudo systemctl disable --now "${SERVICE_NAME}.service" 2>/dev/null || true
sudo systemctl stop "${SERVICE_NAME}.service" 2>/dev/null || true

# Remove systemd unit files
if [ -f "$SERVICE_FILE" ]; then
  echo "Removing service file: $SERVICE_FILE"
  sudo rm -f "$SERVICE_FILE"
else
  echo "Service file not found: $SERVICE_FILE"
fi

if [ -f "$TIMER_FILE" ]; then
  echo "Removing timer file: $TIMER_FILE"
  sudo rm -f "$TIMER_FILE"
else
  echo "Timer file not found: $TIMER_FILE"
fi

# Reload systemd and clear cached/failed state
echo "Reloading systemd daemon"
sudo systemctl daemon-reload

echo "Resetting failed state (best effort)"
sudo systemctl reset-failed "${SERVICE_NAME}.timer" "${SERVICE_NAME}.service" 2>/dev/null || true

# Remove Python script
if [ -f "$SCRIPT_FILE" ]; then
  echo "Removing script file: $SCRIPT_FILE"
  sudo rm -f "$SCRIPT_FILE"
else
  echo "Script file not found: $SCRIPT_FILE"
fi

# (Optional) remove telemetry data
if [ -f "$LOG_FILE" ]; then
  echo "Removing telemetry data file: $LOG_FILE"
  sudo rm -f "$LOG_FILE"
else
  echo "Telemetry data file not found: $LOG_FILE"
fi

# (Optional) remove empty log dir
if [ -d "$LOG_DIR" ] && [ -z "$(ls -A "$LOG_DIR" 2>/dev/null || true)" ]; then
  echo "Removing empty log dir: $LOG_DIR"
  sudo rmdir "$LOG_DIR" 2>/dev/null || true
fi

echo "=== Uninstallation complete for ${SERVICE_NAME} ==="
echo "Checks:"
echo "  systemctl list-timers | grep ${SERVICE_NAME} || echo ok"
echo "  systemctl list-units --type=service | grep ${SERVICE_NAME} || echo ok"
echo "  systemctl list-unit-files | grep ${SERVICE_NAME} || echo ok"
