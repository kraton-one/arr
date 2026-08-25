#!/usr/bin/with-contenv bash

# Fix http_host for LazyLibrarian to allow connections through VPN
# LazyLibrarian uses config.ini (not XML) so this requires its own script

CONFIG_FILE="/config/config.ini"

echo "[custom-init] Configuring LazyLibrarian http_host for VPN access"

# Wait for config file to be created if it doesn't exist
if [ ! -f "$CONFIG_FILE" ]; then
    echo "[custom-init] Config file not found yet, LazyLibrarian will create it on first run"
    exit 0
fi

# Check if the [General] section exists and update http_host within it
if grep -q "^\[General\]" "$CONFIG_FILE"; then
    # Use awk to only modify http_host in [General] section
    awk '/^\[General\]/{p=1} /^\[/ && !/^\[General\]/{p=0} p && /^http_host = /{$0="http_host = 0.0.0.0"; modified=1} {print} END{if(p && !modified) print "http_host = 0.0.0.0"}' "$CONFIG_FILE" > "$CONFIG_FILE.tmp" && mv "$CONFIG_FILE.tmp" "$CONFIG_FILE"
    chown abc:abc "$CONFIG_FILE"
    echo "[custom-init] Updated http_host to 0.0.0.0 in [General] section"
else
    echo "[custom-init] No [General] section found, adding http_host setting"
    echo -e "\n[General]\nhttp_host = 0.0.0.0" >> "$CONFIG_FILE"
    chown abc:abc "$CONFIG_FILE"
fi

# Also ensure http_port is 5299 (default)
if grep -q "^\[General\]" "$CONFIG_FILE"; then
    awk '/^\[General\]/{p=1} /^\[/ && !/^\[General\]/{p=0} p && /^http_port = /{$0="http_port = 5299"; modified=1} {print} END{if(p && !modified) print "http_port = 5299"}' "$CONFIG_FILE" > "$CONFIG_FILE.tmp" && mv "$CONFIG_FILE.tmp" "$CONFIG_FILE"
    chown abc:abc "$CONFIG_FILE"
    echo "[custom-init] Updated http_port to 5299 in [General] section"
fi

echo "[custom-init] LazyLibrarian configuration complete"
