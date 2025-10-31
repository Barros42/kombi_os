#!/bin/bash
# Script: install.sh
# Description: Installs the Kombi O.S. GPS Service with virtual environment

LOG_DIR=/var/log/kombios/gps

CURRENT_POSITION_FILE=$LOG_DIR/current.position
LAST_POSITION_FILE=$LOG_DIR/last.position
HISTORIC_POSITION_FILE=$LOG_DIR/historic.position

SERVICE_FILE=/etc/systemd/system/kombios-gps-service.service
SCRIPT_FILE=/usr/local/bin/kombios-gps-service.py
USER_NAME=kombios
VENV_DIR=/opt/kombios/venv

echo "=== Starting Kombi O.S. GPS Service installation ==="

# Create dedicated user (if it doesn't exist)
if ! id -u $USER_NAME >/dev/null 2>&1; then
    echo "Creating dedicated user: $USER_NAME"
    sudo useradd -r -s /bin/false $USER_NAME
else
    echo "User $USER_NAME already exists"
fi

# Create log directory
echo "Creating log directory: $LOG_DIR"
sudo mkdir -p $LOG_DIR
sudo chown $USER_NAME:$USER_NAME $LOG_DIR

# Create empty log file
echo "Creating current position log file: $CURRENT_POSITION_FILE"
sudo touch $CURRENT_POSITION_FILE
sudo chown $USER_NAME:$USER_NAME $CURRENT_POSITION_FILE

# Create empty log file
echo "Creating last position log file: $LAST_POSITION_FILE"
sudo touch $LAST_POSITION_FILE
sudo chown $USER_NAME:$USER_NAME $LAST_POSITION_FILE

# Create empty log file
echo "Creating historic log file: $HISTORIC_POSITION_FILE"
sudo touch $HISTORIC_POSITION_FILE
sudo chown $USER_NAME:$USER_NAME $HISTORIC_POSITION_FILE

# Create virtual environment directory
echo "Creating virtual environment at $VENV_DIR"
sudo mkdir -p $VENV_DIR
sudo chown $USER_NAME:$USER_NAME $VENV_DIR
sudo -u $USER_NAME python3 -m venv $VENV_DIR

# Install required Python packages inside venv
echo "Installing required Python packages in venv"
sudo -u $USER_NAME $VENV_DIR/bin/pip install --upgrade pip
sudo -u $USER_NAME $VENV_DIR/bin/pip install -r requirements.txt

# Copy Python script
echo "Copying Python script to $SCRIPT_FILE"
sudo cp ./kombios-gps-service.py $SCRIPT_FILE
sudo chmod +x $SCRIPT_FILE
sudo chown $USER_NAME:$USER_NAME $SCRIPT_FILE

# Copy systemd service file
echo "Copying systemd service file to $SERVICE_FILE"
sudo cp ./kombios-gps-service.service $SERVICE_FILE

# Reload systemd
echo "Reloading systemd daemon"
sudo systemctl daemon-reload

# Enable service at boot
echo "Enabling service at boot"
sudo systemctl enable kombios-gps-service.service

# Start service immediately
echo "Starting service now"
sudo systemctl start kombios-gps-service.service

# Show service status
echo "Checking service status"
sudo systemctl status kombios-gps-service.service

echo "=== Installation complete ==="
