#!/usr/bin/with-contenv bash

# Fix BindAddress for arr services to allow external connections
# This script runs on container startup

CONFIG_FILE="${CONFIG_FILE:-/config/config.xml}"

if [ -f "$CONFIG_FILE" ]; then
    echo "[custom-init] Checking BindAddress in $CONFIG_FILE"

    # Check if BindAddress exists
    if grep -q "<BindAddress>" "$CONFIG_FILE"; then
        # Update existing BindAddress to *
        sed -i 's|<BindAddress>.*</BindAddress>|<BindAddress>*</BindAddress>|' "$CONFIG_FILE"
        echo "[custom-init] Updated BindAddress to '*'"
    else
        echo "[custom-init] No BindAddress found, service may use default"
    fi
else
    echo "[custom-init] Config file not found at $CONFIG_FILE, skipping"
fi
