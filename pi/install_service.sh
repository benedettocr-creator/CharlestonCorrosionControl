#!/bin/bash
# Run on each Raspberry Pi to install sensor_reader.py as a systemd service.
# It will start automatically on boot and restart on failure.
#
# Usage:
#   chmod +x install_service.sh
#   sudo ./install_service.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_NAME="corrosion-sensor"
PYTHON="$(which python3)"

echo "Installing corrosion sensor service..."
echo "  Script dir : $SCRIPT_DIR"
echo "  Python     : $PYTHON"

# Install Python dependency
"$PYTHON" -m pip install --quiet -r "$SCRIPT_DIR/requirements.txt"

# Write systemd unit file
cat > /etc/systemd/system/${SERVICE_NAME}.service << EOF
[Unit]
Description=Corrosion Sensor Reader
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=${SCRIPT_DIR}
ExecStart=${PYTHON} ${SCRIPT_DIR}/sensor_reader.py
Restart=on-failure
RestartSec=30
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}.service"
systemctl start  "${SERVICE_NAME}.service"

echo ""
echo "Service installed and started."
echo "  Check status : sudo systemctl status ${SERVICE_NAME}"
echo "  Live logs    : sudo journalctl -u ${SERVICE_NAME} -f"
