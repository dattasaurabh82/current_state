#!/bin/bash
# =============================================================================
# 04_stop_and_uninstall_services.sh
#
# Stops and removes all services for the World Theme Music Player:
# - User systemd services (music-player, full-cycle-btn, process-monitor-web)
# - nginx reverse proxy configuration (not nginx itself)
# - Cron jobs for daily generation and backup
#
# Usage: ./04_stop_and_uninstall_services.sh
# =============================================================================

set -e  # Exit on error

# =============================================================================
# DERIVED VARIABLES
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_NAME="$(basename "$PROJECT_DIR")"

CURRENT_USER="$USER"
USER_HOME="$HOME"
HOSTNAME="$(hostname)"

SYSTEMD_USER_DIR="$USER_HOME/.config/systemd/user"
NGINX_SITES_AVAILABLE="/etc/nginx/sites-available"
NGINX_SITES_ENABLED="/etc/nginx/sites-enabled"
NGINX_CONFIG_NAME="process-monitor-web"

# Service names
SERVICES=(
    "music-player.service"
    "full-cycle-btn.service"
    "process-monitor-web.service"
)

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

# =============================================================================
# MAIN UNINSTALLATION
# =============================================================================

print_header "SERVICES UNINSTALLER"

print_info "Project: $PROJECT_DIR"
print_info "User: $CURRENT_USER"
print_info "Hostname: $HOSTNAME"
echo ""

# -----------------------------------------------------------------------------
# Step 1: Stop and disable user services
# -----------------------------------------------------------------------------

print_step "Stopping and disabling user services..."

for service in "${SERVICES[@]}"; do
    if systemctl --user is-active --quiet "$service" 2>/dev/null; then
        systemctl --user stop "$service"
        print_success "Stopped $service"
    else
        print_info "$service was not running"
    fi
    
    if systemctl --user is-enabled --quiet "$service" 2>/dev/null; then
        systemctl --user disable "$service"
        print_success "Disabled $service"
    else
        print_info "$service was not enabled"
    fi
done

# -----------------------------------------------------------------------------
# Step 2: Remove service files
# -----------------------------------------------------------------------------

print_step "Removing service files..."

for service in "${SERVICES[@]}"; do
    SERVICE_FILE="$SYSTEMD_USER_DIR/$service"
    if [ -f "$SERVICE_FILE" ]; then
        rm -f "$SERVICE_FILE"
        print_success "Removed $SERVICE_FILE"
    else
        print_info "$service file not found (already removed?)"
    fi
done

# -----------------------------------------------------------------------------
# Step 3: Reload systemd daemon
# -----------------------------------------------------------------------------

print_step "Reloading systemd daemon..."
systemctl --user daemon-reload
print_success "Systemd daemon reloaded"

# -----------------------------------------------------------------------------
# Step 4: Remove nginx configuration
# -----------------------------------------------------------------------------

print_step "Removing nginx configuration..."

# Remove symlink from sites-enabled
if [ -L "$NGINX_SITES_ENABLED/$NGINX_CONFIG_NAME" ]; then
    sudo rm "$NGINX_SITES_ENABLED/$NGINX_CONFIG_NAME"
    print_success "Removed nginx site symlink"
else
    print_info "nginx site symlink not found"
fi

# Remove config from sites-available
if [ -f "$NGINX_SITES_AVAILABLE/$NGINX_CONFIG_NAME" ]; then
    sudo rm "$NGINX_SITES_AVAILABLE/$NGINX_CONFIG_NAME"
    print_success "Removed nginx config file"
else
    print_info "nginx config file not found"
fi

# Reload nginx (don't stop it - might be used by other sites)
if systemctl is-active --quiet nginx 2>/dev/null; then
    sudo nginx -t && sudo systemctl reload nginx
    print_success "nginx reloaded"
fi

# -----------------------------------------------------------------------------
# Step 5: Remove cron jobs
# -----------------------------------------------------------------------------

print_step "Removing cron jobs..."

# Remove lines matching our specific scripts
CRON_BEFORE=$(crontab -l 2>/dev/null | wc -l)

crontab -l 2>/dev/null | \
    grep -v "main.py.*--fetch.*--play" | \
    grep -v "bkp_gen_music.py" | \
    crontab - 2>/dev/null || true

CRON_AFTER=$(crontab -l 2>/dev/null | wc -l)
CRON_REMOVED=$((CRON_BEFORE - CRON_AFTER))

if [ "$CRON_REMOVED" -gt 0 ]; then
    print_success "Removed $CRON_REMOVED cron job(s)"
else
    print_info "No matching cron jobs found"
fi

# =============================================================================
# COMPLETE
# =============================================================================

print_header "UNINSTALLATION COMPLETE"

echo ""
echo "  Removed:"
echo "    • User systemd services (stopped, disabled, files deleted)"
echo "    • nginx site configuration (config removed, nginx still running)"
echo "    • Cron jobs (daily generation and backup)"
echo ""
echo "  NOT removed:"
echo "    • nginx itself (may be used by other sites)"
echo "    • linger setting (may be used by other user services)"
echo "    • Project files (your code is safe)"
echo ""
print_info "To reinstall: ./01_install_and_start_services.sh"
echo ""
