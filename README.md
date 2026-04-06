# Media Stack with VPN

A fully containerized media management stack running on Docker. All download and indexer traffic routes through a VPN, while media serving and library management run on direct connections for optimal performance.

## What's Included

| Category | Service | Subdomain | Description |
|----------|---------|-----------|-------------|
| **Streaming** | [Jellyfin](https://jellyfin.org/) | `watch.*` | Media server with hardware transcoding |
| | [Audiobookshelf](https://www.audiobookshelf.org/) | `listen.*` | Audiobook and podcast server |
| | [Calibre-Web](https://github.com/janeczku/calibre-web) | `read.*` | Ebook library web interface |
| | [Calibre](https://calibre-ebook.com/) | `library.*` | Ebook library manager |
| | [Seerr](https://github.com/seerr-team/seerr) | `guide.*` | Media request management |
| **Content Management** | [Sonarr](https://sonarr.tv/) | `tv.*` | TV series automation |
| | [Radarr](https://radarr.video/) | `movies.*` | Movie automation |
| | [Lidarr](https://lidarr.audio/) | `music.*` | Music automation |
| | [Bazarr](https://www.bazarr.media/) | `captions.*` | Subtitle management |
| | [LazyLibrarian](https://lazylibrarian.gitlab.io/) | `books.*` | Book and audiobook search |
| **Downloads** | [qBittorrent](https://www.qbittorrent.org/) | `qbittorrent.*` | Torrent client |
| | [SABnzbd](https://sabnzbd.org/) | `sabnzbd.*` | Usenet client |
| | [Prowlarr](https://prowlarr.com/) | `prowlarr.*` | Indexer manager |
| **Utilities** | [Unpackerr](https://unpackerr.zip/) | `unpackerr.*` | Automatic archive extraction |
| | [Notifiarr](https://notifiarr.com/) | `notify.*` | Unified notifications |
| | [FlareSolverr](https://github.com/FlareSolverr/FlareSolverr) | `flaresolverr.*` | Cloudflare bypass for indexers |
| **Transcoding** | [Tdarr](https://home.tdarr.io/) | `tdarr.*` | Automated media transcoding |
| **Infrastructure** | [Gluetun](https://github.com/qdm12/gluetun) | &mdash; | VPN gateway (ProtonVPN WireGuard) |
| | [Caddy](https://caddyserver.com/) (x2) | &mdash; | Reverse proxy with auto SSL |
| | [Homepage](https://gethomepage.dev/) | `hub.*` | Dashboard with service widgets |

## Architecture

```
                         Internet
                            │
              ┌─────────────┴─────────────┐
              │     Dual Caddy Proxies     │
              │   (Let's Encrypt via CF)   │
              ├───────────┬───────────────┤
              │ SERVICES_IP:443           │
              │  arr / download UIs       │
              │  hub, books, notify, etc. │
              ├───────────┼───────────────┤
              │ HOST_IP:443               │
              │  watch, listen, read,     │
              │  library, guide, tdarr    │
              └───────────┬───────────────┘
                          │
              ┌───────────┴───────────────┐
              │     Docker (arr_network)   │
              └───┬──────────┬─────────┬──┘
                  │          │         │
         ┌────────┴───┐  ┌──┴───┐  ┌──┴──────────────┐
         │  Gluetun   │  │Direct│  │   Homepage       │
         │ (ProtonVPN)│  │      │  │   Port 3000      │
         └────┬───────┘  │      │  └──────────────────┘
              │          │      │
   VPN-routed services   │  Direct services
   ───────────────────   │  ────────────────
   qBittorrent           │  Jellyfin (+ HW transcode)
   SABnzbd               │  Audiobookshelf
   Sonarr / Radarr       │  Calibre / Calibre-Web
   Lidarr / Bazarr       │  Seerr
   Prowlarr              │  Tdarr
   LazyLibrarian         │
   Unpackerr / Notifiarr │
   FlareSolverr          │
              │          │
         ┌────┴──────────┴────┐
         │   Local Storage    │
         │  CONFIG_ROOT/      │
         │  MEDIA_ROOT/       │
         │   ├─ library/      │
         │   │  ├─ tv/        │
         │   │  ├─ movies/    │
         │   │  ├─ music/     │
         │   │  ├─ books/     │
         │   │  ├─ audiobooks/│
         │   │  └─ podcasts/  │
         │   └─ downloads/    │
         │      ├─ complete/  │
         │      └─ incomplete/│
         └────────────────────┘
```

**Key design decisions:**

- **VPN kill switch** &mdash; Gluetun blocks all traffic if the VPN drops; download clients never leak your real IP.
- **Dual reverse proxy** &mdash; Arr services and media services bind to separate IPs via two Caddy instances, allowing network segmentation (e.g., different VLANs).
- **No direct port access** &mdash; All web UIs are served over HTTPS through Caddy. The only exception is Homepage on port 3000.
- **Hardlink support** &mdash; Downloads and library directories live under the same `MEDIA_ROOT`, so moves are instant hardlinks (no copy).
- **Hardware transcoding** &mdash; Jellyfin and Tdarr pass through `/dev/dri` for GPU-accelerated transcoding.

## Prerequisites

- Docker and Docker Compose
- A domain name with DNS managed by (or proxied through) Cloudflare
- A ProtonVPN account with WireGuard credentials (or another [Gluetun-supported VPN](https://github.com/qdm12/gluetun-wiki))
- A Cloudflare API token with **DNS:Edit** permission for your zone

## Quick Start

### 1. Clone and Configure

```bash
git clone https://github.com/your-user/arr.git
cd arr
cp .env.example .env
```

Edit `.env` with your values. The required variables are grouped below.

### 2. Environment Variables

The entire stack is configured through a single `.env` file. See [`.env.example`](.env.example) for the full template.

#### Storage Paths

| Variable | Description | Example |
|----------|-------------|---------|
| `CONFIG_ROOT` | Base path for all service configs | `/mnt/storage/configs` |
| `MEDIA_ROOT` | Base path for media and downloads | `/mnt/storage/media` |
| `TDARR_CACHE_ROOT` | Transcode temp directory (ideally fast storage) | `/mnt/ssd/transcode_cache` |

#### Identity & Timezone

| Variable | Default | Description |
|----------|---------|-------------|
| `PUID` | `1000` | User ID for file ownership |
| `PGID` | `1000` | Group ID for file ownership |
| `TZ` | `America/Chicago` | Timezone |

Run `id` on the host to confirm your UID/GID.

#### Network

| Variable | Description |
|----------|-------------|
| `HOST_IP` | IP for media Caddy + Jellyfin ports (e.g., your host's main IP) |
| `SERVICES_IP` | IP for arr Caddy (can be the same as `HOST_IP` or a second interface) |
| `FIREWALL_INBOUND_SUBNETS` | Comma-separated CIDRs allowed to reach VPN-routed services (your LAN + Docker network) |
| `TDARR_SERVER_IP` | IP the Tdarr server listens on for remote nodes (use `0.0.0.0` or host IP) |

#### Domain & SSL

| Variable | Description |
|----------|-------------|
| `DOMAIN` | Your domain (e.g., `example.com`) &mdash; all subdomains derive from this |
| `LETSENCRYPT_EMAIL` | Email for Let's Encrypt certificate notifications |
| `CLOUDFLARE_API_TOKEN` | Cloudflare API token with DNS:Edit permission |

#### VPN (ProtonVPN WireGuard)

| Variable | Description |
|----------|-------------|
| `WIREGUARD_PRIVATE_KEY` | WireGuard private key from ProtonVPN |
| `WIREGUARD_ADDRESSES` | WireGuard IP (format: `10.x.x.x/32`) |

To get these: log into ProtonVPN &rarr; Account &rarr; WireGuard configuration.

To use a different VPN provider, update the `gluetun` environment variables in [`docker-compose.yaml`](docker-compose.yaml) per the [Gluetun wiki](https://github.com/qdm12/gluetun-wiki).

#### Credentials

| Variable | Description |
|----------|-------------|
| `QBITTORRENT_USER` | qBittorrent WebUI username (default: `admin`) |
| `QBITTORRENT_PASS` | qBittorrent WebUI password |

#### API Keys

These are obtained from each service **after first startup**. Leave the defaults in `.env` initially, start the stack, then retrieve the keys and update `.env`.

| Variable | Where to Find It |
|----------|------------------|
| `SABNZBD_API_KEY` | SABnzbd &rarr; Config &rarr; General &rarr; API Key |
| `JELLYFIN_API_KEY` | Jellyfin &rarr; Dashboard &rarr; API Keys &rarr; Create |
| `AUDIOBOOKSHELF_API_KEY` | Audiobookshelf &rarr; Settings &rarr; API Keys |
| `SEERR_API_KEY` | Seerr &rarr; Settings &rarr; General |
| `SONARR_API_KEY` | Sonarr &rarr; Settings &rarr; General &rarr; Security |
| `RADARR_API_KEY` | Radarr &rarr; Settings &rarr; General &rarr; Security |
| `LIDARR_API_KEY` | Lidarr &rarr; Settings &rarr; General &rarr; Security |
| `BAZARR_API_KEY` | Bazarr &rarr; Settings &rarr; General &rarr; Security |
| `PROWLARR_API_KEY` | Prowlarr &rarr; Settings &rarr; General &rarr; Security |
| `NOTIFIARR_API_KEY` | [notifiarr.com](https://notifiarr.com) account |

### 3. Create Directory Structure

```bash
# Adjust paths to match your .env
mkdir -p /mnt/storage/configs
mkdir -p /mnt/storage/media/library/{tv,movies,music,books,audiobooks,podcasts}
mkdir -p /mnt/storage/media/downloads/{complete,incomplete}
mkdir -p /mnt/storage/transcode_cache
```

### 4. Start the Stack

```bash
docker compose up -d
```

On first run, the `homepage-init` container copies the bundled Homepage config into your `CONFIG_ROOT`. Caddy images are built from [`Dockerfile.caddy`](Dockerfile.caddy) to include the Cloudflare DNS plugin. LazyLibrarian is built from [`Dockerfile.lazylibrarian`](Dockerfile.lazylibrarian) with Calibre bundled for ebook processing.

### 5. Verify

```bash
# Check all containers
docker compose ps

# Confirm VPN is active (should show a VPN IP, not yours)
docker exec gluetun curl -s ifconfig.me

# Check port forwarding for torrents
docker compose logs gluetun | grep -i "forwarded port"

# Watch specific service logs
docker compose logs -f sonarr
```

### 6. Initial Service Setup

1. Access each arr service through its subdomain (e.g., `https://tv.yourdomain.com`).
2. Complete initial setup wizards.
3. Copy the API key from each service's settings.
4. Update `.env` with all API keys and restart:
   ```bash
   docker compose down && docker compose up -d
   ```
5. In Prowlarr, add your indexers, then use "Apps" to sync them to Sonarr/Radarr/Lidarr.
6. In Sonarr/Radarr/Lidarr, add qBittorrent and/or SABnzbd as download clients:
   - Host: `localhost` (they share Gluetun's network namespace)
   - Port: `8080` (qBittorrent) or `8085` (SABnzbd)
7. Set root folders in each arr app to the appropriate library path (e.g., `/tv`, `/movies`, `/music`).
8. In Bazarr, connect to Sonarr and Radarr using `localhost` and the respective ports.

## Configuration Details

### How VPN Routing Works

Services that need VPN protection use `network_mode: "service:gluetun"` in the compose file. This means they share Gluetun's network stack &mdash; all their traffic exits through the VPN tunnel. Because they share a network namespace, these services reach each other via `localhost` and their respective ports.

Services that don't need VPN (Jellyfin, Audiobookshelf, Calibre, Seerr, Tdarr) connect directly to the `arr_network` bridge and bind their own ports.

Caddy reaches VPN-routed services by proxying to `gluetun:<port>`. It reaches direct services by container name (e.g., `jellyfin:8096`).

### Dual Caddy Reverse Proxy

Two Caddy instances provide HTTPS for all services:

- **`caddy`** (binds to `SERVICES_IP:443`) &mdash; Handles arr services, download clients, Homepage, and utilities. Config: [`Caddyfile`](Caddyfile).
- **`caddy-media`** (binds to `HOST_IP:443`) &mdash; Handles Jellyfin, Audiobookshelf, Calibre, Calibre-Web, Seerr, and Tdarr. Config: [`Caddyfile.media`](Caddyfile.media).

Both instances are built from [`Dockerfile.caddy`](Dockerfile.caddy), which adds the [caddy-dns/cloudflare](https://github.com/caddy-dns/cloudflare) plugin for DNS-01 ACME challenges. Certificates are issued automatically by Let's Encrypt.

**Why two instances?** Binding to separate IPs allows you to place arr services and media services on different network interfaces or VLANs. If you only have one IP, set `SERVICES_IP` and `HOST_IP` to the same value, though you'll need to adjust ports to avoid the 443 conflict.

### DNS Setup

Create DNS A records pointing each subdomain to the appropriate IP:

| Records | Points To |
|---------|-----------|
| `watch`, `listen`, `read`, `library`, `guide`, `tdarr` | `HOST_IP` |
| `tv`, `movies`, `music`, `books`, `captions`, `qbittorrent`, `sabnzbd`, `prowlarr`, `hub`, `notify`, `unpackerr`, `flaresolverr` | `SERVICES_IP` |

If using Cloudflare proxy (orange cloud), the DNS-01 challenge still works since it validates via TXT records, not HTTP.

### Init Scripts

The [`init-scripts/`](init-scripts/) directory contains startup scripts mounted into containers:

| Script | Used By | Purpose |
|--------|---------|---------|
| [`qbittorrent-port-sync.sh`](init-scripts/qbittorrent-port-sync.sh) | qBittorrent | Monitors Gluetun's forwarded port and automatically updates qBittorrent's listening port. Polls every 60 seconds. |
| [`sabnzbd-port-fix.sh`](init-scripts/sabnzbd-port-fix.sh) | SABnzbd | Sets SABnzbd to port 8085 (avoiding conflict with qBittorrent on 8080), binds to `0.0.0.0`, and configures the host whitelist for reverse proxy access. |
| [`fix-bindaddress.sh`](init-scripts/fix-bindaddress.sh) | Sonarr, Radarr, Lidarr, Bazarr, Prowlarr, Unpackerr | Sets `<BindAddress>` to `*` in each service's `config.xml` so they accept connections from Caddy through the Gluetun network namespace. |

### Custom Dockerfiles

| File | Purpose |
|------|---------|
| [`Dockerfile.caddy`](Dockerfile.caddy) | Builds Caddy with the Cloudflare DNS plugin for ACME DNS-01 challenges |
| [`Dockerfile.lazylibrarian`](Dockerfile.lazylibrarian) | Extends LazyLibrarian with Calibre installed for `calibredb` integration |

### Homepage Dashboard

[Homepage](https://gethomepage.dev/) provides a unified dashboard with live widgets for all services. Config files in [`config/homepage/`](config/homepage/) are copied to `CONFIG_ROOT/homepage/` on first run by the `homepage-init` container.

Widget configuration uses Homepage's template variable syntax (`{{HOMEPAGE_VAR_*}}`), with values injected from environment variables. Once API keys are set in `.env`, widgets automatically display live stats.

### Tdarr Remote Node

A separate compose file ([`docker-compose.tdarr-node.yml`](docker-compose.tdarr-node.yml)) is provided for running a Tdarr transcoding node on a different machine (e.g., a GPU-equipped workstation). The remote node connects back to the main Tdarr server.

```bash
# On the remote machine
cp .env.example .env
# Set TDARR_SERVER_IP to the main server's IP
# Set MEDIA_ROOT and TDARR_CACHE_ROOT for local paths
docker compose -f docker-compose.tdarr-node.yml up -d
```

The node needs access to the same media files (via NFS/SMB mount or similar) and a fast local cache directory for transcoding temp files.

### Upgrade Script

```bash
# Pull latest images and recreate all containers
./scripts/upgrade.sh
```

This runs `docker compose pull` followed by `docker compose up -d --force-recreate --build`.

## Troubleshooting

### VPN

```bash
# Check Gluetun logs for connection status
docker compose logs gluetun

# Verify VPN IP (should NOT be your real IP)
docker exec gluetun curl -s ifconfig.me

# Check port forwarding
docker compose logs gluetun | grep -i "forwarded port"
```

### Services Can't Connect to Each Other

- VPN-routed services reach each other via `localhost` (shared network namespace).
- Caddy reaches VPN services via `gluetun:<port>`.
- Caddy reaches direct services via container name (e.g., `jellyfin:8096`).
- Verify Gluetun is healthy: `docker compose ps gluetun`
- Check `FIREWALL_INBOUND_SUBNETS` includes your LAN and the Docker network.

### qBittorrent Port Forwarding

```bash
# Check the forwarded port
docker exec gluetun cat /tmp/gluetun/forwarded_port

# Check if the sync script is running
docker compose logs qbittorrent | grep "qbit-port-sync"
```

### SABnzbd Host Whitelist Errors

The init script handles this automatically, but if you see whitelist errors:
```bash
docker compose logs sabnzbd | grep "custom-init"
```
The script sets `host_whitelist` to include your subdomain and `gluetun`.

### Caddy / SSL

```bash
# Check certificate status
docker compose logs caddy | grep -i "certificate"
docker compose logs caddy-media | grep -i "certificate"

# Verify Cloudflare token is set
docker compose exec caddy printenv CLOUDFLARE_API_TOKEN | head -c 5
```

If certificates fail, check that your Cloudflare API token has DNS:Edit permission for the zone and that DNS records exist for the subdomains.

### Permissions

```bash
# Find your UID/GID
id

# Fix ownership (adjust paths to match your .env)
sudo chown -R 1000:1000 /path/to/configs
sudo chown -R 1000:1000 /path/to/media
```

## Updating

```bash
# Pull latest images and recreate containers
./scripts/upgrade.sh

# Or manually
docker compose pull
docker compose up -d

# Clean up old images
docker image prune
```

## Security Notes

- **Never commit `.env`** &mdash; it contains VPN keys, API keys, and passwords. It's in `.gitignore`.
- **VPN kill switch** &mdash; Gluetun blocks all traffic if the tunnel drops.
- **No direct port access** &mdash; All web UIs served through Caddy with TLS (except Homepage on port 3000).
- **Firewall** &mdash; `FIREWALL_INBOUND_SUBNETS` restricts which networks can reach VPN-routed services.
- **Network segmentation** &mdash; Dual Caddy instances allow placing arr and media services on separate network interfaces.

## Resources

- [Servarr Wiki](https://wiki.servarr.com/) &mdash; Documentation for Sonarr, Radarr, Lidarr, Prowlarr
- [TRaSH Guides](https://trash-guides.info/) &mdash; Quality profiles, custom formats, best practices
- [Gluetun Wiki](https://github.com/qdm12/gluetun-wiki) &mdash; VPN provider setup and configuration
- [Homepage Docs](https://gethomepage.dev/) &mdash; Dashboard customization and widgets
- [Caddy Docs](https://caddyserver.com/docs/) &mdash; Reverse proxy configuration
