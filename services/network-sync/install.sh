#!/bin/bash
# Script: install.sh
# Description: Installs the Kombi O.S. service with virtual environment support

set -euo pipefail

SERVICE_NAME="kombios-network-sync-service"
USER_NAME="kombios"

LOG_DIR="/var/log/kombios/network"
SCRIPT_FILE="/usr/local/bin/kombios/${SERVICE_NAME}.py"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

LOG_FILES=(
  "$LOG_DIR/current.data"
)

echo "=== Starting installation for ${SERVICE_NAME} ==="

# Create log directory
echo "Creating log directory: $LOG_DIR"
sudo mkdir -p "$LOG_DIR"
sudo chown "$USER_NAME:$USER_NAME" "$LOG_DIR"

# Create empty log files
for FILE in "${LOG_FILES[@]}"; do
  echo "Creating log file: $FILE"
  sudo touch "$FILE"
  sudo chown "$USER_NAME:$USER_NAME" "$FILE"
done

# Copy Python script
echo "Copying Python script to $SCRIPT_FILE"
sudo cp "./${SERVICE_NAME}.py" "$SCRIPT_FILE"
sudo chmod +x "$SCRIPT_FILE"
sudo chown "$USER_NAME:$USER_NAME" "$SCRIPT_FILE"

# Copy systemd service file
echo "Copying systemd service file to $SERVICE_FILE"
sudo cp "./${SERVICE_NAME}.service" "$SERVICE_FILE"

# Reload systemd
echo "Reloading systemd daemon"
sudo systemctl daemon-reload

# Enable service at boot
echo "Enabling service at boot"
sudo systemctl enable "$SERVICE_NAME"

# Start service immediately
echo "Starting service"
sudo systemctl start "$SERVICE_NAME"

# Show service status
echo "Checking service status"
sudo systemctl status "$SERVICE_NAME"

echo "=== Installation complete for ${SERVICE_NAME} ==="
