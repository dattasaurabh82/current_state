#!/bin/bash
# =============================================================================
# 00_status.sh
#
# Quick status check for all services. Run this before other scripts to
# diagnose issues.
#
# Usage: ./00_status.sh
# =============================================================================

# =============================================================================
# DERIVED VARIABLES
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

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
DIM='\033[2m'
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

print_subheader() {
    echo ""
    echo -e "${YELLOW}── $1 ──${NC}"
}

print_info() {
    echo -e "${CYAN}ℹ${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_dim() {
    echo -e "${DIM}  $1${NC}"
}

get_service_status() {
    if systemctl --user is-active --quiet "$1" 2>/dev/null; then
        echo -e "${GREEN}● ACTIVE${NC}"
    else
        echo -e "${RED}● INACTIVE${NC}"
    fi
}

get_nginx_status() {
    if systemctl is-active --quiet nginx 2>/dev/null; then
        echo -e "${GREEN}● ACTIVE${NC}"
    else
        echo -e "${RED}● INACTIVE${NC}"
    fi
}

is_service_active() {
    systemctl --user is-active --quiet "$1" 2>/dev/null
}

is_nginx_active() {
    systemctl is-active --quiet nginx 2>/dev/null
}

# =============================================================================
# MAIN STATUS CHECK
# =============================================================================

print_header "SERVICES STATUS"

print_info "Project: $PROJECT_DIR"
print_info "User: $CURRENT_USER"
print_info "Hostname: $HOSTNAME"

# Get status for each service
STATUS_MUSIC=$(get_service_status music-player.service)
STATUS_BTN=$(get_service_status full-cycle-btn.service)
STATUS_WEB=$(get_service_status process-monitor-web.service)
STATUS_NGINX=$(get_nginx_status)

echo ""
echo -e "╔═══════════════════════════════╦═══════════════════════════════╗"
echo -e "║  music-player      $STATUS_MUSIC   ║  full-cycle-btn    $STATUS_BTN    ║"
echo -e "╠═══════════════════════════════╬═══════════════════════════════╣"
echo -e "║  web-dashboard     $STATUS_WEB   ║  nginx             $STATUS_NGINX    ║"
echo -e "╚═══════════════════════════════╩═══════════════════════════════╝"

# =============================================================================
# DIAGNOSTICS FOR FAILED SERVICES
# =============================================================================

ISSUES_FOUND=false

# Check music-player
if ! is_service_active "music-player.service"; then
    ISSUES_FOUND=true
    print_subheader "music-player.service"
    
    if [ ! -f "$SYSTEMD_USER_DIR/music-player.service" ]; then
        print_error "Service file not installed"
        print_dim "Run: ./01_install_and_start_services.sh"
    else
        print_error "Service installed but not running"
        print_dim "Recent logs:"
        journalctl --user -u music-player.service -n 5 --no-pager 2>/dev/null | while read -r line; do
            print_dim "$line"
        done
        if [ $? -ne 0 ] || [ -z "$(journalctl --user -u music-player.service -n 1 --no-pager 2>/dev/null)" ]; then
            print_dim "(no journal logs - try: systemctl --user status music-player.service)"
        fi
    fi
fi

# Check full-cycle-btn
if ! is_service_active "full-cycle-btn.service"; then
    ISSUES_FOUND=true
    print_subheader "full-cycle-btn.service"
    
    if [ ! -f "$SYSTEMD_USER_DIR/full-cycle-btn.service" ]; then
        print_error "Service file not installed"
        print_dim "Run: ./01_install_and_start_services.sh"
    else
        print_error "Service installed but not running"
        print_dim "Recent logs:"
        journalctl --user -u full-cycle-btn.service -n 5 --no-pager 2>/dev/null | while read -r line; do
            print_dim "$line"
        done
        if [ $? -ne 0 ] || [ -z "$(journalctl --user -u full-cycle-btn.service -n 1 --no-pager 2>/dev/null)" ]; then
            print_dim "(no journal logs - try: systemctl --user status full-cycle-btn.service)"
        fi
    fi
fi

# Check process-monitor-web
if ! is_service_active "process-monitor-web.service"; then
    ISSUES_FOUND=true
    print_subheader "process-monitor-web.service"
    
    if [ ! -f "$SYSTEMD_USER_DIR/process-monitor-web.service" ]; then
        print_error "Service file not installed"
        print_dim "Run: ./01_install_and_start_services.sh"
    else
        print_error "Service installed but not running"
        print_dim "Recent logs:"
        journalctl --user -u process-monitor-web.service -n 5 --no-pager 2>/dev/null | while read -r line; do
            print_dim "$line"
        done
        if [ $? -ne 0 ] || [ -z "$(journalctl --user -u process-monitor-web.service -n 1 --no-pager 2>/dev/null)" ]; then
            print_dim "(no journal logs - try: systemctl --user status process-monitor-web.service)"
        fi
        print_dim ""
        print_dim "Manual test: cd $PROJECT_DIR && uv run uvicorn web.app:app --port 7070"
    fi
fi

# Check nginx
if ! is_nginx_active; then
    ISSUES_FOUND=true
    print_subheader "nginx"
    
    if ! command -v nginx &> /dev/null; then
        print_error "nginx not installed"
        print_dim "Run: sudo apt install nginx"
    elif [ ! -f "$NGINX_SITES_AVAILABLE/$NGINX_CONFIG_NAME" ]; then
        print_error "nginx config not installed"
        print_dim "Run: ./01_install_and_start_services.sh"
    else
        print_error "nginx installed but not running"
        print_dim "Check config: sudo nginx -t"
        print_dim "Start: sudo systemctl start nginx"
    fi
fi

# =============================================================================
# CRON STATUS
# =============================================================================

print_subheader "Cron Jobs"

CRON_GENERATE=$(crontab -l 2>/dev/null | grep "main.py.*--fetch.*--play" || true)
CRON_BACKUP=$(crontab -l 2>/dev/null | grep "bkp_gen_music.py" || true)

if [ -n "$CRON_GENERATE" ]; then
    print_success "Generate: installed"
    print_dim "$CRON_GENERATE"
else
    ISSUES_FOUND=true
    print_error "Generate: not installed"
fi

if [ -n "$CRON_BACKUP" ]; then
    print_success "Backup: installed"
    print_dim "$CRON_BACKUP"
else
    ISSUES_FOUND=true
    print_error "Backup: not installed"
fi

# =============================================================================
# SUMMARY
# =============================================================================

print_header "SUMMARY"

if [ "$ISSUES_FOUND" = true ]; then
    echo ""
    print_error "Issues found - see diagnostics above"
    echo ""
    echo "  Quick fixes:"
    echo "    Install all:  ./01_install_and_start_services.sh"
    echo "    Start only:   ./02_start_services.sh"
    echo "    Reinstall:    ./04_stop_and_uninstall_services.sh && ./01_install_and_start_services.sh"
    echo ""
    exit 1
else
    echo ""
    print_success "All services running"
    echo ""
    print_info "Web Dashboard: http://${HOSTNAME}.local"
    print_info "Direct:        http://${HOSTNAME}.local:7070"
    echo ""
    exit 0
fi
