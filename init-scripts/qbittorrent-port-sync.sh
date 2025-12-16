#!/usr/bin/with-contenv bash

# Continuous port forwarding sync for qBittorrent
# Monitors gluetun's forwarded port and updates qBittorrent automatically

PORT_FILE="/tmp/gluetun/forwarded_port"
CHECK_INTERVAL=60  # Check every 60 seconds
LAST_PORT=""

QB_HOST="http://localhost:8080"
QB_USER="${QBITTORRENT_USER:-admin}"
QB_PASS="${QBITTORRENT_PASS:-adminadmin}"

echo "[qbit-port-sync] Starting qBittorrent port forwarding monitor..."

# Function to update qBittorrent port
update_qbittorrent_port() {
    local port=$1

    # Try authentication first
    local auth_response=$(curl -s -i --header "Referer: ${QB_HOST}" \
        --data "username=${QB_USER}&password=${QB_PASS}" \
        "${QB_HOST}/api/v2/auth/login")

    local cookie=$(echo "$auth_response" | grep -i 'set-cookie' | cut -d' ' -f2 | tr -d '\r')

    # Try with authentication
    if [ -n "$cookie" ]; then
        echo "[qbit-port-sync] Using authenticated session"
        local result=$(curl -s -w "\n%{http_code}" -X POST "${QB_HOST}/api/v2/app/setPreferences" \
            --cookie "$cookie" \
            --data "json={\"listen_port\":${port},\"random_port\":false,\"upnp\":false}")
        local http_code=$(echo "$result" | tail -n1)

        if [ "$http_code" == "200" ]; then
            echo "[qbit-port-sync] Successfully updated qBittorrent port to ${port}"
            return 0
        fi
    fi

    # Try without authentication (some setups have it disabled)
    echo "[qbit-port-sync] Trying without authentication..."
    local result=$(curl -s -w "\n%{http_code}" -X POST "${QB_HOST}/api/v2/app/setPreferences" \
        --data "json={\"listen_port\":${port},\"random_port\":false,\"upnp\":false}")
    local http_code=$(echo "$result" | tail -n1)

    if [ "$http_code" == "200" ]; then
        echo "[qbit-port-sync] Successfully updated qBittorrent port to ${port} (no auth)"
        return 0
    else
        echo "[qbit-port-sync] Failed to update port (HTTP ${http_code}). Check qBittorrent Web UI credentials."
        return 1
    fi
}

# Wait for qBittorrent to be ready
echo "[qbit-port-sync] Waiting for qBittorrent to start..."
for i in {1..30}; do
    if curl -s "${QB_HOST}/api/v2/app/version" > /dev/null 2>&1; then
        echo "[qbit-port-sync] qBittorrent is ready"
        break
    fi
    sleep 2
done

# Main monitoring loop
while true; do
    if [ -f "$PORT_FILE" ]; then
        CURRENT_PORT=$(cat "$PORT_FILE" 2>/dev/null)

        if [ -n "$CURRENT_PORT" ] && [ "$CURRENT_PORT" != "$LAST_PORT" ]; then
            echo "[qbit-port-sync] Port change detected: ${LAST_PORT:-none} -> ${CURRENT_PORT}"

            if update_qbittorrent_port "$CURRENT_PORT"; then
                LAST_PORT="$CURRENT_PORT"
            fi
        fi
    else
        echo "[qbit-port-sync] Waiting for forwarded port file at ${PORT_FILE}..."
    fi

    sleep $CHECK_INTERVAL
done
