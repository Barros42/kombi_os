#!/bin/bash
# Script: uninstall.sh
# Description: Removes the Kombi O.S. GPS Service

SERVICE_NAME=kombios-gps-service.service
SCRIPT_PATH=/usr/local/bin/kombios-gps-service.py
LOG_DIR=/var/log/kombios/gps
USER_NAME=kombios

echo "=== Starting Kombi O.S. GPS Service uninstallation ==="

# Stop the service
echo "Stopping the service..."
sudo systemctl stop $SERVICE_NAME

# Disable the service
echo "Disabling the service..."
sudo systemctl disable $SERVICE_NAME

# Remove the systemd service file
echo "Removing the service from systemd... > " $SERVICE_NAME
sudo rm -f /etc/systemd/system/$SERVICE_NAME
sudo systemctl daemon-reload
sudo systemctl reset-failed

# Remove the Python script
echo "Removing the Python script... > " $SCRIPT_PATH
sudo rm -f $SCRIPT_PATH

# Remove dedicated user
echo "Removing dedicated user..."
sudo userdel -r $USER_NAME 2>/dev/null || echo "User $USER_NAME does not exist"

# Remove log directory
echo "Removing log directory... >" $LOG_DIR
sudo rm -rf $LOG_DIR

echo "=== Kombi O.S. GPS Service successfully uninstalled ==="
