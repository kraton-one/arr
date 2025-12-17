#!/usr/bin/with-contenv bash

# Configure SABnzbd to use port 8085 instead of default 8080
# This script runs on container startup

CONFIG_FILE="/config/sabnzbd.ini"
DOMAIN="${DOMAIN:-yourdomain.com}"

echo "[custom-init] Configuring SABnzbd port and host whitelist for ${DOMAIN}"

# Wait for config file to be created if it doesn't exist
if [ ! -f "$CONFIG_FILE" ]; then
    echo "[custom-init] Config file not found yet, will be created by SABnzbd"
    # Create a basic config with the correct port and host whitelist
    mkdir -p /config
    cat > "$CONFIG_FILE" << EOF
[misc]
host = 0.0.0.0
port = 8085
host_whitelist = sabnzbd.${DOMAIN}, qbittorrent.${DOMAIN}, gluetun
EOF
    chown abc:abc "$CONFIG_FILE"
    echo "[custom-init] Created initial config with port 8085 and host whitelist"
else
    echo "[custom-init] Config file exists, updating configuration"
    # Update port in [misc] section only
    if grep -q "^\[misc\]" "$CONFIG_FILE"; then
        # Use awk to only modify port in [misc] section
        awk '/^\[misc\]/{p=1} /^\[/ && !/^\[misc\]/{p=0} p && /^port = /{$0="port = 8085"; modified=1} {print} END{if(p && !modified) print "port = 8085"}' "$CONFIG_FILE" > "$CONFIG_FILE.tmp" && mv "$CONFIG_FILE.tmp" "$CONFIG_FILE"
        chown abc:abc "$CONFIG_FILE"
        echo "[custom-init] Updated port to 8085 in [misc] section"
    fi

    # Ensure host is set to 0.0.0.0 to accept connections (only in [misc] section)
    if grep -q "^\[misc\]" "$CONFIG_FILE"; then
        # Use awk to only modify host in [misc] section
        awk '/^\[misc\]/{p=1} /^\[/ && !/^\[misc\]/{p=0} p && /^host = /{$0="host = 0.0.0.0"; modified=1} {print} END{if(p && !modified) print "host = 0.0.0.0"}' "$CONFIG_FILE" > "$CONFIG_FILE.tmp" && mv "$CONFIG_FILE.tmp" "$CONFIG_FILE"
        chown abc:abc "$CONFIG_FILE"
        echo "[custom-init] Updated host to 0.0.0.0 in [misc] section"
    fi

    # Add host_whitelist to allow access via domain name
    if grep -q "^host_whitelist = " "$CONFIG_FILE"; then
        sed -i "s/^host_whitelist = .*/host_whitelist = sabnzbd.${DOMAIN}, qbittorrent.${DOMAIN}, gluetun/" "$CONFIG_FILE"
        echo "[custom-init] Updated host_whitelist"
    else
        sed -i "/^\[misc\]/a host_whitelist = sabnzbd.${DOMAIN}, qbittorrent.${DOMAIN}, gluetun" "$CONFIG_FILE"
        echo "[custom-init] Added host_whitelist to config"
    fi
fi
