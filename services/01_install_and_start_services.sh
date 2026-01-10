#!/bin/bash
# =============================================================================
# 01_install_and_start_services.sh
#
# Installs and starts all services for the World Theme Music Player:
# - User systemd services (music-player, full-cycle-btn, process-monitor-web)
# - nginx reverse proxy configuration
# - Cron jobs for daily generation and backup
#
# Usage: ./01_install_and_start_services.sh
# =============================================================================

set -e  # Exit on error

# =============================================================================
# CONFIGURATION
# =============================================================================

# Cron schedule (24h format)
CRON_BACKUP_TIME="40 2"      # 2:40 AM - Backup to Dropbox
CRON_GENERATE_TIME="0 3"     # 3:00 AM - Generate new music

# Web dashboard port
WEB_PORT=7070

# =============================================================================
# DERIVED VARIABLES (do not edit)
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_NAME="$(basename "$PROJECT_DIR")"

CURRENT_USER="$USER"
USER_HOME="$HOME"
UV_PATH="$(which uv)"
HOSTNAME="$(hostname)"

SYSTEMD_USER_DIR="$USER_HOME/.config/systemd/user"
NGINX_SITES_AVAILABLE="/etc/nginx/sites-available"
NGINX_SITES_ENABLED="/etc/nginx/sites-enabled"
NGINX_CONFIG_NAME="process-monitor-web"

# Service files (relative to SCRIPT_DIR)
SERVICE_FILES=(
    "full-cycle-btn.service"
    "music-player.service"
    "process-monitor-web.service"
)
NGINX_TEMPLATE="process-monitor-web"

# =============================================================================
# COLORS
# =============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

print_header() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}$1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_step() {
    echo -e "${YELLOW}▶${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${CYAN}ℹ${NC} $1"
}

# Replace placeholders in a file and output to stdout
substitute_placeholders() {
    local file="$1"
    sed -e "s|__PROJECT_DIR__|${PROJECT_DIR}|g" \
        -e "s|__UV_PATH__|${UV_PATH}|g" \
        -e "s|__WEB_PORT__|${WEB_PORT}|g" \
        -e "s|__HOSTNAME__|${HOSTNAME}|g" \
        "$file"
}

# =============================================================================
# MAIN INSTALLATION
# =============================================================================

print_header "SERVICES INSTALLER"

print_info "Project: $PROJECT_DIR"
print_info "User: $CURRENT_USER"
print_info "Hostname: $HOSTNAME"
print_info "UV Path: $UV_PATH"
echo ""

# -----------------------------------------------------------------------------
# Step 1: Create systemd user directory
# -----------------------------------------------------------------------------
mkdir -p "$SYSTEMD_USER_DIR"

# -----------------------------------------------------------------------------
# Step 2: Install service files (sed placeholders + copy)
# -----------------------------------------------------------------------------
print_step "Installing systemd service files..."

for service in "${SERVICE_FILES[@]}"; do
    SOURCE_FILE="$SCRIPT_DIR/$service"
    DEST_FILE="$SYSTEMD_USER_DIR/$service"
    
    if [ ! -f "$SOURCE_FILE" ]; then
        print_error "Source file not found: $SOURCE_FILE"
        exit 1
    fi
    
    substitute_placeholders "$SOURCE_FILE" > "$DEST_FILE"
    print_success "Installed $service"
done

# -----------------------------------------------------------------------------
# Step 3: Reload systemd and enable services
# -----------------------------------------------------------------------------
print_step "Reloading systemd daemon..."
systemctl --user daemon-reload
print_success "Systemd daemon reloaded"

print_step "Enabling and starting user services..."
for service in "${SERVICE_FILES[@]}"; do
    systemctl --user enable --now "$service"
    print_success "Enabled $service"
done

# -----------------------------------------------------------------------------
# Step 4: Enable linger (services start on boot without login)
# -----------------------------------------------------------------------------
print_step "Enabling linger for $CURRENT_USER..."
sudo loginctl enable-linger "$CURRENT_USER"
print_success "Linger enabled"

# -----------------------------------------------------------------------------
# Step 5: Install nginx configuration
# -----------------------------------------------------------------------------
print_step "Installing nginx configuration..."

# Ensure home directory is traversable by nginx
chmod o+x "$USER_HOME"

# Generate nginx config from template
NGINX_SOURCE="$SCRIPT_DIR/$NGINX_TEMPLATE"
NGINX_DEST="$NGINX_SITES_AVAILABLE/$NGINX_CONFIG_NAME"

if [ ! -f "$NGINX_SOURCE" ]; then
    print_error "nginx template not found: $NGINX_SOURCE"
    exit 1
fi

# Write nginx config (requires sudo)
substitute_placeholders "$NGINX_SOURCE" | sudo tee "$NGINX_DEST" > /dev/null
print_success "Installed nginx config"

# Enable site (create symlink)
if [ ! -L "$NGINX_SITES_ENABLED/$NGINX_CONFIG_NAME" ]; then
    sudo ln -s "$NGINX_DEST" "$NGINX_SITES_ENABLED/$NGINX_CONFIG_NAME"
    print_success "Enabled nginx site"
else
    print_info "nginx site already enabled"
fi

# Remove default site if exists
if [ -L "$NGINX_SITES_ENABLED/default" ]; then
    sudo rm "$NGINX_SITES_ENABLED/default"
    print_success "Removed default nginx site"
fi

# Test, enable, start, and reload nginx
sudo nginx -t
sudo systemctl enable nginx
sudo systemctl start nginx
sudo systemctl reload nginx
print_success "nginx configured and started"

# -----------------------------------------------------------------------------
# Step 6: Install cron jobs
# -----------------------------------------------------------------------------

print_step "Installing cron jobs..."

# Build cron entries with dynamic paths
CRON_GENERATE="$CRON_GENERATE_TIME * * * cd $PROJECT_DIR && $UV_PATH run python main.py --fetch true --play false >> $PROJECT_DIR/logs/cron.log 2>&1"
CRON_BACKUP="$CRON_BACKUP_TIME * * * cd $PROJECT_DIR && $UV_PATH run python tools/bkp_gen_music.py >> $PROJECT_DIR/logs/backup.log 2>&1"

# Remove existing entries (if any) and add fresh ones
(
    crontab -l 2>/dev/null | grep -v "main.py.*--fetch.*--play" | grep -v "bkp_gen_music.py"
    echo "$CRON_BACKUP"
    echo "$CRON_GENERATE"
) | crontab -

print_success "Cron jobs installed"
print_info "  Backup:   $CRON_BACKUP_TIME (2:40 AM)"
print_info "  Generate: $CRON_GENERATE_TIME (3:00 AM)"

# =============================================================================
# COMPLETE
# =============================================================================

print_header "INSTALLATION COMPLETE"

echo ""
print_info "Web Dashboard (via nginx):  http://${HOSTNAME}.local"
print_info "Web Dashboard (direct):     http://${HOSTNAME}.local:${WEB_PORT}"
echo ""
print_info "Run ./00_status.sh to check service status"
echo ""
