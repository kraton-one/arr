# Media Stack with VPN

A complete media management stack running on Docker with VPN protection for downloading services.

> **Important:** Before deploying, you must customize [.env](.env) (copy from [.env.example](.env.example)):
> - `CONFIG_ROOT` - Path to store all service configurations (e.g., `/mnt/storage/configs`)
> - `MEDIA_ROOT` - Path to your media library (e.g., `/mnt/storage/media`)
> - `DOMAIN` - Your domain name (e.g., `example.com`) - automatically configures all subdomains
> - Network subnets in `FIREWALL_INBOUND_SUBNETS` in docker-compose.yaml to match your LAN
> - Port bindings in docker-compose.yaml if needed (currently configured for specific host IP)
>
> **No manual file editing needed!** All paths and domains configured via environment variables.

## Architecture

This setup uses a **single-host architecture** running on TrueNAS or any Docker-capable host:

- **VPN-Protected Services**: Download clients and media management apps route through Gluetun VPN
  - qBittorrent (torrents), SABnzbd (usenet)
  - Sonarr, Radarr, Lidarr, Bazarr, LazyLibrarian
  - Prowlarr (indexer manager)
  - Unpackerr (automatic archive extraction)
  - Notifiarr (unified notifications)

- **Direct Connection Services**: Media serving runs without VPN for optimal performance
  - Jellyfin (media server)
  - Jellyseerr (media requests)
  - Homepage (dashboard)

- **Shared Infrastructure**
  - Caddy reverse proxy with automatic Let's Encrypt SSL (Cloudflare DNS challenge)
  - All services accessible via friendly subdomains on your domain

## Services

### Media Management (Through VPN)
- **Sonarr** - TV series management
  - https://tv.yourdomain.com | https://sonarr.yourdomain.com
- **Radarr** - Movie management
  - https://movies.yourdomain.com | https://radarr.yourdomain.com
- **Lidarr** - Music management
  - https://music.yourdomain.com | https://lidarr.yourdomain.com
- **Bazarr** - Subtitle management
  - https://captions.yourdomain.com | https://bazarr.yourdomain.com
- **LazyLibrarian** - Book management
  - https://books.yourdomain.com | https://lazylibrarian.yourdomain.com

### Download Clients (Through VPN)
- **qBittorrent** - Torrent client
  - https://qbittorrent.yourdomain.com
- **SABnzbd** - Usenet client
  - https://sabnzbd.yourdomain.com
- **Prowlarr** - Indexer manager
  - https://prowlarr.yourdomain.com

### Utilities (Through VPN)
- **Unpackerr** - Automatic archive extraction
  - https://unpackerr.yourdomain.com
- **Notifiarr** - Unified notification client
  - https://notify.yourdomain.com | https://notifiarr.yourdomain.com
- **FlareSolverr** - Cloudflare bypass helper
  - https://flaresolverr.yourdomain.com
- **Gluetun** - VPN gateway using ProtonVPN WireGuard

### Media Serving (Direct - No VPN)
- **Jellyfin** - Media server
  - https://watch.yourdomain.com | https://jellyfin.yourdomain.com
  - Local: http://YOUR_HOST_IP:8096
- **Jellyseerr** - Media request management
  - https://guide.yourdomain.com | https://jellyseerr.yourdomain.com
  - Local: http://YOUR_HOST_IP:5055

### Infrastructure
- **Homepage** - Unified dashboard with service widgets
  - https://hub.yourdomain.com
  - Local: http://YOUR_HOST_IP:3000
- **Caddy** - Reverse proxy with automatic Let's Encrypt SSL (Cloudflare DNS)

## Quick Start

### 1. Setup Environment

```bash
# Copy environment template
cp .env.example .env

# Edit and add your credentials
nano .env
```

Required variables:
- `CONFIG_ROOT` - Path for service configurations (e.g., `/mnt/storage/configs`)
- `MEDIA_ROOT` - Path for media library (e.g., `/mnt/storage/media`)
- `DOMAIN` - Your domain name (e.g., `example.com`) - used for all service subdomains
- `WIREGUARD_PRIVATE_KEY` - From ProtonVPN
- `WIREGUARD_ADDRESSES` - From ProtonVPN (format: 10.x.x.x/32)
- `CLOUDFLARE_API_TOKEN` - For DNS challenges and SSL certificates
- `LETSENCRYPT_EMAIL` - Email for Let's Encrypt certificate notifications
- `QBITTORRENT_PASS` - Password for qBittorrent WebUI
- All the `*_API_KEY` variables for Homepage widgets (obtain after initial setup)

### 2. Create Directory Structure

Create the directories specified in your `.env` file:

```bash
# Create directories matching your CONFIG_ROOT and MEDIA_ROOT from .env
# Example if CONFIG_ROOT=/mnt/storage/configs and MEDIA_ROOT=/mnt/storage/media

mkdir -p /mnt/storage/configs
mkdir -p /mnt/storage/media/library/{tv,movies,music,books}
mkdir -p /mnt/storage/media/downloads/{complete,incomplete}
```

The docker-compose.yaml automatically uses `${CONFIG_ROOT}` and `${MEDIA_ROOT}` - no manual path editing needed!

### 3. Start the Stack

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f

# View specific service logs
docker compose logs -f jellyfin
docker compose logs -f gluetun

# Verify VPN is working
docker exec gluetun curl ifconfig.me

# Stop all services
docker compose down
```

### 4. Access Services

All services are available via your configured domains (see Services section above) or locally:
- Homepage: http://YOUR_HOST_IP:3000
- Jellyfin: http://YOUR_HOST_IP:8096
- Jellyseerr: http://YOUR_HOST_IP:5055
- qBittorrent: http://YOUR_HOST_IP:8080
- SABnzbd: http://YOUR_HOST_IP:8085 (via gluetun)
- Sonarr: http://YOUR_HOST_IP:8989 (via gluetun)
- Radarr: http://YOUR_HOST_IP:7878 (via gluetun)
- Prowlarr: http://YOUR_HOST_IP:9696 (via gluetun)

## Deployment

This is a single-host deployment designed for Docker-capable hosts (TrueNAS, Ubuntu, Debian, etc.).

### Host Setup

```bash
# Clone or copy repository to your host
cd /path/to/arr

# Setup environment
cp .env.example .env
nano .env  # Set CONFIG_ROOT, MEDIA_ROOT, DOMAIN, VPN credentials, and API keys

# Create directory structure matching your .env paths
mkdir -p ${CONFIG_ROOT}
mkdir -p ${MEDIA_ROOT}/library/{tv,movies,music,books}
mkdir -p ${MEDIA_ROOT}/downloads/{complete,incomplete}

# Deploy the full stack (paths automatically configured from .env)
docker compose up -d

# Verify VPN is working (should show VPN IP, not your real IP)
docker exec gluetun curl ifconfig.me

# Check all services are running
docker compose ps
```

### Network Configuration

**Port Bindings:**
By default, services bind to specific IPs for security. Update in [docker-compose.yaml](docker-compose.yaml):
- Jellyfin ports: `8096` (HTTP), `8920` (HTTPS), `7359/udp`, `1900/udp`
- Jellyseerr: `5055`
- Caddy HTTP/HTTPS: `80`, `443`
- Homepage: `3000`
- All VPN-routed services accessible through gluetun on their respective ports

**Firewall Configuration:**
Update `FIREWALL_INBOUND_SUBNETS` in [docker-compose.yaml](docker-compose.yaml) to match your network:
- Your LAN subnet (e.g., `192.168.1.0/24`)
- Any additional trusted networks
- Docker network: `172.28.0.0/16`

## Configuration

### VPN Setup (Gluetun)

1. Get ProtonVPN WireGuard credentials:
   - Login to ProtonVPN
   - Go to Account → OpenVPN/WireGuard credentials
   - Copy your Private Key and IP address

2. Add to [.env.example](.env.example):
   ```bash
   WIREGUARD_PRIVATE_KEY=your_private_key_here
   WIREGUARD_ADDRESSES=10.x.x.x/32
   ```

3. The stack routes these services through VPN:
   - **Media Management**: Sonarr, Radarr, Lidarr, Bazarr, LazyLibrarian
   - **Download Clients**: qBittorrent, SABnzbd
   - **Indexer**: Prowlarr
   - **Utilities**: Unpackerr, Notifiarr, FlareSolverr

4. VPN features enabled:
   - Port forwarding (for qBittorrent)
   - Amsterdam, Netherlands server location
   - Kill switch (blocks traffic if VPN drops)
   - Firewall configured for local subnet access

### Download Client Configuration

#### qBittorrent
- Initial WebUI access: `http://YOUR_HOST_IP:8080`
- Username: `admin` (or value from `QBITTORRENT_USER`)
- Password: Set via `QBITTORRENT_PASS` in [.env](.env)
- The init script automatically configures port forwarding from Gluetun

#### SABnzbd
- Initial WebUI access: `http://YOUR_HOST_IP:8085`
- API key: Set via `SABNZBD_API_KEY` in [.env](.env) after first run
- Configure your Usenet provider in SABnzbd settings
- The init script fixes bind address issues for VPN compatibility

### Automation Tools

#### Unpackerr
Automatically extracts archives downloaded by:
- Sonarr
- Radarr
- Lidarr

Configuration is automatic - just ensure API keys are set in [.env](.env).

#### Notifiarr
Unified notification client that integrates with:
- Sonarr, Radarr, Lidarr, Prowlarr
- qBittorrent
- Discord (configure at notifiarr.com)

Requires `NOTIFIARR_API_KEY` from [notifiarr.com](https://notifiarr.com).

### Homepage Widget Configuration

Homepage shows real-time stats for all services. To enable widgets:

1. **Get API Keys** from each service after initial setup:
   - **Arr apps** (Sonarr/Radarr/Lidarr/Bazarr/Prowlarr): Settings → General → Security → API Key
   - **Jellyfin**: Dashboard → API Keys → Create new key
   - **Jellyseerr**: Settings → General → API Key
   - **SABnzbd**: Config → General → API Key

2. Add all API keys to [.env](.env) file

3. **Configure URLs** in [config/homepage/services.yaml](config/homepage/services.yaml):
   - Direct services use container names (e.g., `http://jellyfin:8096`)
   - VPN services use `gluetun` as hostname (e.g., `http://gluetun:8989`)

### Caddy SSL Certificates

Caddy automatically obtains Let's Encrypt SSL certificates using Cloudflare DNS challenge.

**Setup:**
1. Set your domain in [.env](.env):
   ```bash
   DOMAIN=example.com
   ```

2. All subdomains are automatically configured via the [Caddyfile](Caddyfile):
   - `qbittorrent.example.com`
   - `tv.example.com`, `sonarr.example.com`
   - `movies.example.com`, `radarr.example.com`
   - `watch.example.com`, `jellyfin.example.com`
   - And more... (see Services section)

**Requirements:**
- Domain pointed to your server (or Cloudflare proxy enabled)
- Cloudflare API token with DNS edit permissions
- Token added to [.env](.env) as `CLOUDFLARE_API_TOKEN`
- Email address in `LETSENCRYPT_EMAIL` for certificate notifications

## Network Architecture

```
                    ┌─────────────────────────────┐
                    │         Internet            │
                    └──────────────┬──────────────┘
                                   │
                        ┌──────────┴──────────┐
                        │   Caddy (80/443)    │
                        │  Reverse Proxy +    │
                        │   Let's Encrypt     │
                        │   Cloudflare DNS    │
                        └──────────┬──────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    │      Docker Host            │
                    │      arr_network            │
                    │     (172.28.0.0/16)         │
                    └──────────────┬──────────────┘
                                   │
            ┌──────────────────────┼──────────────────────┐
            │                      │                      │
   ┌────────┴─────────┐   ┌────────┴─────────┐   ┌───────┴────────┐
   │    Gluetun       │   │  Jellyfin        │   │   Homepage     │
   │  (VPN Gateway)   │   │ (Media Server)   │   │  (Dashboard)   │
   │   ProtonVPN WG   │   │   Port: 8096     │   │   Port: 3000   │
   └────────┬─────────┘   └──────────────────┘   └────────────────┘
            │
   ┌────────┴─────────────────────────────┐
   │  VPN-Protected Services              │
   ├──────────────────────────────────────┤
   │  Download Clients:                   │
   │  • qBittorrent (8080)                │
   │  • SABnzbd (8085)                    │
   │                                      │
   │  Media Management:                   │
   │  • Sonarr (8989)                     │
   │  • Radarr (7878)                     │
   │  • Lidarr (8686)                     │
   │  • Bazarr (6767)                     │
   │  • LazyLibrarian (5299)              │
   │                                      │
   │  Utilities:                          │
   │  • Prowlarr (9696)                   │
   │  • Unpackerr (5656)                  │
   │  • Notifiarr (5454)                  │
   │  • FlareSolverr (8191)               │
   └──────────────────────────────────────┘
            │
   ┌────────┴─────────┐
   │  Local Storage   │
   │  /path/to/data   │
   │   ├─ configs/    │
   │   └─ media/      │
   │      ├─ library/ │
   │      └─downloads/│
   └──────────────────┘
```

### Single-Host Architecture Benefits:

**All services on one host:**
- Download services protected by VPN (Gluetun WireGuard)
- Direct local storage access for optimal performance (no network mounts)
- Hardlinks work properly between downloads and library
- Media serving (Jellyfin/Jellyseerr) runs without VPN for optimal streaming
- Centralized management of all services

**VPN Protection:**
- All download and indexer traffic routes through ProtonVPN (or other supported VPN)
- Kill switch prevents leaks if VPN disconnects
- Port forwarding enabled for torrent connectivity
- Firewall configured to allow local subnet access

**SSL/TLS:**
- Caddy handles all external HTTPS traffic
- Automatic Let's Encrypt certificates via Cloudflare DNS
- Friendly subdomains for all services

## Troubleshooting

### VPN Connection Issues

```bash
# Check Gluetun logs
docker compose logs gluetun

# Verify VPN connection (should show ProtonVPN IP, not your real IP)
docker exec gluetun curl ifconfig.me

# Test port forwarding
docker compose logs gluetun | grep -i "port forward"

# Check VPN health
docker compose ps gluetun
```

### Services Can't Connect

If Arr apps can't reach qBittorrent or each other:
1. Verify all VPN-routed services use `network_mode: "service:gluetun"`
2. Check Gluetun container is healthy: `docker compose ps gluetun`
3. Ensure services are using `gluetun` as hostname (not localhost or container name)
4. Check firewall rules in Gluetun logs allow your subnet

### Download Client Issues

#### qBittorrent
```bash
# Check if port forwarding is active
docker compose logs gluetun | grep -i "forwarded port"

# Verify qBittorrent is using the forwarded port
docker compose exec qbittorrent cat /tmp/gluetun/forwarded_port
```

#### SABnzbd
```bash
# Check SABnzbd logs
docker compose logs sabnzbd

# Verify bind address fix was applied
docker compose logs sabnzbd | grep -i "bind"
```

### Homepage Widgets Not Loading

1. Verify API keys are correct in [.env](.env)
2. Check service URLs in [config/homepage/services.yaml](config/homepage/services.yaml)
3. For VPN services, ensure URL uses `gluetun` as hostname (e.g., `http://gluetun:8989`)
4. For direct services, use container name (e.g., `http://jellyfin:8096`)
5. Check logs: `docker compose logs homepage`

### Caddy SSL Issues

```bash
# Check Caddy logs
docker compose logs caddy

# Verify Cloudflare API token is set
docker compose exec caddy env | grep CLOUDFLARE

# Test certificate (replace with your domain)
curl -vI https://jellyfin.yourdomain.com

# Force certificate renewal
docker compose restart caddy
```

### Permission Issues

If you encounter permission errors:
```bash
# Check PUID/PGID in .env match your user
id

# Fix ownership of config directories (replace paths with your actual paths)
sudo chown -R 1000:1000 /path/to/configs
sudo chown -R 1000:1000 /path/to/media
```

## Updating

```bash
# Pull latest images
docker compose pull

# Recreate containers
docker compose up -d

# Remove old images
docker image prune
```

## Storage Management

Recommended directory structure:
```
/path/to/data/
├── configs/          # Service configurations (persistent)
│   ├── gluetun/
│   ├── qbittorrent/
│   ├── sabnzbd/
│   ├── sonarr/
│   ├── radarr/
│   ├── lidarr/
│   ├── bazarr/
│   ├── lazylibrarian/
│   ├── prowlarr/
│   ├── unpackerr/
│   ├── notifiarr/
│   ├── jellyfin/
│   ├── jellyseerr/
│   ├── homepage/
│   └── caddy/
│       ├── data/     # SSL certificates
│       └── config/
└── media/
    ├── library/      # Media files (organized by type)
    │   ├── tv/
    │   ├── movies/
    │   ├── music/
    │   └── books/
    └── downloads/    # Download directory
        ├── complete/
        └── incomplete/
```

### Storage Notes:
- Set `CONFIG_ROOT` and `MEDIA_ROOT` in [.env](.env) - all volume paths automatically configured
- All configs persist in `${CONFIG_ROOT}` directory
- Media library uses hardlinks when possible (downloads to library)
- **Important:** Downloads and library must be on the same filesystem for hardlinks to work
- Jellyfin transcoding cache stored in `${CONFIG_ROOT}/jellyfin/`

## Security Notes

1. **Never commit `.env`** - Contains sensitive credentials (WireGuard keys, API keys, passwords)
2. **VPN killswitch** - Gluetun blocks all traffic if VPN connection drops
3. **Firewall** - Configure `FIREWALL_INBOUND_SUBNETS` in docker-compose.yaml to allow only:
   - Your LAN subnet (e.g., `192.168.1.0/24`)
   - Any additional trusted networks
   - Docker network: `172.28.0.0/16`
4. **API keys** - Stored in environment variables, never hardcoded
5. **SSL/TLS** - All external traffic encrypted via Caddy with Let's Encrypt
6. **Port binding** - Consider binding services to specific host IP (not 0.0.0.0) for security
7. **Network isolation** - VPN services isolated from direct internet access

## Key Features

- **Fully Environment-Driven**: All configuration via `.env` file - no manual file editing needed
  - `CONFIG_ROOT` and `MEDIA_ROOT` control all volume paths
  - Domain name automatically configures all Caddy subdomains
  - Network settings, credentials, and API keys all in one place
- **Dual Download Support**: Both torrent (qBittorrent) and Usenet (SABnzbd)
- **Automatic Management**: Unpackerr extracts archives, Notifiarr provides notifications
- **Hardlink Support**: Instant "moves" from downloads to library (same filesystem)
- **VPN Protection**: All acquisition traffic routed through ProtonVPN
- **SSL Everywhere**: Automatic HTTPS with friendly domain names via Cloudflare DNS
- **Unified Dashboard**: Homepage provides overview of all services
- **FlareSolverr**: Bypass Cloudflare challenges for indexers

## Resources

### Documentation
- **Servarr Wiki**: [https://wiki.servarr.com/](https://wiki.servarr.com/)
- **TRaSH Guides**: [https://trash-guides.info/](https://trash-guides.info/) (quality profiles, custom formats)
- **Gluetun**: [https://github.com/qdm12/gluetun](https://github.com/qdm12/gluetun)
- **Homepage**: [https://gethomepage.dev/](https://gethomepage.dev/)

### Service Links
- **Jellyfin**: [https://jellyfin.org/](https://jellyfin.org/)
- **Jellyseerr**: [https://github.com/Fallenbagel/jellyseerr](https://github.com/Fallenbagel/jellyseerr)
- **Notifiarr**: [https://notifiarr.com/](https://notifiarr.com/)
- **Caddy**: [https://caddyserver.com/](https://caddyserver.com/)
