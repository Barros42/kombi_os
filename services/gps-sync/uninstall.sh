#!/bin/bash
# Script: uninstall.sh
# Description: Uninstalls the Kombi O.S. GPS Sync service and associated resources

set -euo pipefail

SERVICE_NAME="kombios-gps-sync-service"
USER_NAME="kombios"

SCRIPT_FILE="/usr/local/bin/${SERVICE_NAME}.py"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo "=== Starting uninstallation for ${SERVICE_NAME} ==="

# Stop the service if it's running
if systemctl is-active --quiet "${SERVICE_NAME}"; then
  echo "Stopping service: ${SERVICE_NAME}"
  sudo systemctl stop "${SERVICE_NAME}"
fi

# Disable service at boot
if systemctl is-enabled --quiet "${SERVICE_NAME}"; then
  echo "Disabling service at boot"
  sudo systemctl disable "${SERVICE_NAME}"
fi

# Remove systemd service file
if [ -f "${SERVICE_FILE}" ]; then
  echo "Removing systemd service file: ${SERVICE_FILE}"
  sudo rm -f "${SERVICE_FILE}"
fi

# Reload systemd daemon
echo "Reloading systemd daemon"
sudo systemctl daemon-reload

# Remove Python script
if [ -f "${SCRIPT_FILE}" ]; then
  echo "Removing script file: ${SCRIPT_FILE}"
  sudo rm -f "${SCRIPT_FILE}"
fi


echo "=== Uninstallation complete for ${SERVICE_NAME} ==="
