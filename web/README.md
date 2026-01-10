# Web Dashboard

TUI-style web interface for monitoring the World Theme Music Player pipeline.

![Dashboard Preview](../assets/web_dashboard_preview.png)

## Features

- **News Tab**: Current headlines grouped by region with timestamps
- **Pipeline Tab**: Interactive visualization of the news → music generation flow
- **Logs Tab**: Live streaming logs via WebSocket (xterm.js terminal)

## Quick Start (Development)

```bash
# From project root
uv run uvicorn web.app:app --reload --host 0.0.0.0 --port 7070
```

Visit: `http://localhost:7070`

## Architecture

```
web/
├── app.py              # FastAPI application + WebSocket
├── README.md           # This file
├── templates/
│   └── base.html       # Single-page Jinja2 template
└── static/
    ├── css/
    │   └── tui.css     # TUI styling (Dracula theme)
    ├── js/
    │   ├── main.js     # Tab switching, news loading
    │   ├── logs.js     # WebSocket terminal connection
    │   └── derivation.js  # vis-network pipeline graph
    └── vendor/
        ├── xterm/      # Terminal emulator
        └── vis-network/ # Graph visualization
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Redirect to news tab |
| `/news` | GET | News bulletin tab |
| `/pipeline` | GET | Pipeline visualization tab |
| `/logs` | GET | Live logs tab |
| `/api/news` | GET | JSON: Current news data |
| `/api/derivation` | GET | JSON: Pipeline derivation data |
| `/ws/logs` | WebSocket | Live log streaming |
| `/health` | GET | Health check |

## Production Deployment (Raspberry Pi)

### Prerequisites

- Raspberry Pi with hostname `aimusicplayer`
- avahi-daemon running (default on Raspberry Pi OS)
- Project cloned to `/home/pi/daily_mood_theme_song_player`

### Step 1: Change Hostname (if needed)

```bash
# Check current hostname
hostname

# Change to aimusicplayer
sudo hostnamectl set-hostname aimusicplayer
sudo reboot
```

After reboot, Pi will be accessible at `aimusicplayer.local`

### Step 2: Create systemd User Service

The service file is already in the repo at `services/process-monitor-web.service`.

```bash
# Copy to user systemd directory
mkdir -p ~/.config/systemd/user
cp services/process-monitor-web.service ~/.config/systemd/user/

# Reload and enable
systemctl --user daemon-reload
systemctl --user enable process-monitor-web.service
systemctl --user start process-monitor-web.service

# Check status
systemctl --user status process-monitor-web.service
```

**Service file contents** (`services/process-monitor-web.service`):

```ini
[Unit]
Description=Web Dashboard for full process monitor of the project AI music generation project
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/pi/daily_mood_theme_song_player
ExecStart=/home/pi/.local/bin/uv run uvicorn web.app:app --host 0.0.0.0 --port 7070
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
```

> **Note:** Use `--host 0.0.0.0` for direct LAN access, or `--host 127.0.0.1` when using nginx as reverse proxy.

### Step 3: Enable Linger (for boot startup)

User services only run when the user is logged in. To start on boot:

```bash
sudo loginctl enable-linger pi
```

### Step 4: Verify (without nginx)

From any device on the same network:

```bash
# Should resolve via mDNS
ping aimusicplayer.local

# Open in browser (note: port 7070 required without nginx)
http://aimusicplayer.local:7070
```

### Step 5 (Optional): nginx for Port 80

If you want `http://aimusicplayer.local` (no port number):

```bash
sudo apt update
sudo apt install nginx -y
```

**Fix permissions** (nginx needs to traverse `/home/pi`):

```bash
chmod o+x /home/pi
```

Create `/etc/nginx/sites-available/world-theme`:

```nginx
server {
    listen 80;
    server_name aimusicplayer.local aimusicplayer;

    # Serve static files directly (more efficient)
    location /static/ {
        alias /home/pi/daily_mood_theme_song_player/web/static/;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }

    # Proxy all other requests to uvicorn
    location / {
        proxy_pass http://127.0.0.1:7070;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_read_timeout 86400;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/world-theme /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default  # Remove default site
sudo nginx -t  # Test configuration
sudo systemctl restart nginx
sudo systemctl enable nginx
```

### Step 4: Verify

From any device on the same network:

```bash
# Should resolve via mDNS
ping aimusicplayer.local

# Open in browser
http://aimusicplayer.local
```

## Alternative: iptables Redirect (No nginx)

If you prefer not to use nginx:

```bash
# Redirect port 80 → 7070
sudo iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 7070

# Make persistent (install iptables-persistent)
sudo apt install iptables-persistent
sudo netfilter-persistent save
```

Then update the systemd service to bind to `0.0.0.0:7070` instead of `127.0.0.1:7070`.

**Note:** nginx is recommended because it:
- Serves static files more efficiently
- Handles WebSocket upgrades properly
- Provides better logging and error handling
- Is more production-ready

## Troubleshooting

### Static files 403 / Permission denied

```bash
# Check nginx error log
sudo tail -20 /var/log/nginx/error.log

# If you see "Permission denied" - nginx can't traverse /home/pi
chmod o+x /home/pi
sudo systemctl reload nginx
```

### Service won't start

```bash
# Check logs
journalctl --user -u process-monitor-web.service -f

# Common issues:
# - Wrong path in WorkingDirectory (status=200/CHDIR)
# - uv not found at /home/pi/.local/bin/uv
# - Port already in use
```

### Can't access aimusicplayer.local

```bash
# Check avahi is running
sudo systemctl status avahi-daemon

# Check hostname
hostname

# Try IP address directly
ip addr show  # Find Pi's IP
```

### WebSocket not connecting

```bash
# Check nginx config has WebSocket headers
# Check browser console for errors
# Verify uvicorn is running on 7070
```

## Development vs Production

| Aspect | Development | Production (no nginx) | Production (with nginx) |
|--------|-------------|----------------------|-------------------------|
| Command | `uv run uvicorn ... --reload` | systemd user service | systemd user service |
| Port | 7070 | 7070 | 80 (nginx) → 7070 |
| Host bind | `0.0.0.0` | `0.0.0.0` | `127.0.0.1` |
| URL | `localhost:7070` | `aimusicplayer.local:7070` | `aimusicplayer.local` |
| Auto-restart | Manual | `Restart=on-failure` | `Restart=on-failure` |

## Tech Stack

- **Backend**: FastAPI + Uvicorn
- **Frontend**: Vanilla JS, no build step
- **Styling**: Custom TUI CSS (Dracula theme)
- **Terminal**: xterm.js
- **Graphs**: vis-network.js
- **Fonts**: IBM Plex Mono (local)
