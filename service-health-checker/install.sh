#!/bin/bash

if [ "$EUID" -ne 0 ]; then 
  echo "Please run as root"
  exit 1
fi

echo "Installing Service Health Checker..."

cp checker.py /usr/local/bin/service-health-checker
chmod +x /usr/local/bin/service-health-checker

mkdir -p /etc/service-health-checker
if [ ! -f /etc/service-health-checker/config.json ]; then
    cp config.example.json /etc/service-health-checker/config.json
    echo "Created default config at /etc/service-health-checker/config.json"
else
    echo "Config already exists, skipping."
fi

cp systemd/service-health-checker.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable service-health-checker
echo "Installation complete. Start with: systemctl start service-health-checker"
