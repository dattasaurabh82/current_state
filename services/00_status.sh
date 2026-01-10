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
    "full-cycle-btn.service"
    "music-player.service"
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
echo ""

ISSUES_FOUND=false

# -----------------------------------------------------------------------------
# User Services
# -----------------------------------------------------------------------------

echo -e "${BOLD}User Services${NC}"
echo ""

for service in "${SERVICES[@]}"; do
    if is_service_active "$service"; then
        echo -e "  ${GREEN}●${NC} $service"
    else
        echo -e "  ${RED}●${NC} $service"
        ISSUES_FOUND=true
    fi
done

echo ""

# -----------------------------------------------------------------------------
# nginx
# -----------------------------------------------------------------------------

echo -e "${BOLD}nginx${NC}"
echo ""

if is_nginx_active; then
    echo -e "  ${GREEN}●${NC} nginx"
else
    echo -e "  ${RED}●${NC} nginx"
    ISSUES_FOUND=true
fi

if [ -f "$NGINX_SITES_AVAILABLE/$NGINX_CONFIG_NAME" ]; then
    echo -e "  ${GREEN}●${NC} config installed"
else
    echo -e "  ${RED}●${NC} config missing"
    ISSUES_FOUND=true
fi

echo ""

# -----------------------------------------------------------------------------
# Cron Jobs
# -----------------------------------------------------------------------------

echo -e "${BOLD}Cron Jobs${NC}"
echo ""

CRON_GENERATE=$(crontab -l 2>/dev/null | grep "main.py.*--fetch.*--play" || true)
CRON_BACKUP=$(crontab -l 2>/dev/null | grep "bkp_gen_music.py" || true)

if [ -n "$CRON_GENERATE" ]; then
    echo -e "  ${GREEN}●${NC} generate (3:00 AM)"
else
    echo -e "  ${RED}●${NC} generate - not installed"
    ISSUES_FOUND=true
fi

if [ -n "$CRON_BACKUP" ]; then
    echo -e "  ${GREEN}●${NC} backup (2:40 AM)"
else
    echo -e "  ${RED}●${NC} backup - not installed"
    ISSUES_FOUND=true
fi

echo ""

# =============================================================================
# DIAGNOSTICS (only if issues found)
# =============================================================================

if [ "$ISSUES_FOUND" = true ]; then
    print_header "DIAGNOSTICS"
    
    # Check each service
    for service in "${SERVICES[@]}"; do
        if ! is_service_active "$service"; then
            echo ""
            echo -e "${YELLOW}$service${NC}"
            
            if [ ! -f "$SYSTEMD_USER_DIR/$service" ]; then
                print_error "Service file not installed"
                print_dim "Run: ./01_install_and_start_services.sh"
            else
                print_error "Service installed but not running"
                print_dim "Try: systemctl --user start $service"
                print_dim "Logs: journalctl --user -u $service -n 10"
            fi
        fi
    done
    
    # Check nginx
    if ! is_nginx_active; then
        echo ""
        echo -e "${YELLOW}nginx${NC}"
        
        if ! command -v nginx &> /dev/null; then
            print_error "nginx not installed"
            print_dim "Run: sudo apt install nginx"
        else
            print_error "nginx not running"
            print_dim "Try: sudo systemctl start nginx"
        fi
    fi
    
    echo ""
    print_header "QUICK FIX"
    echo ""
    echo "  Reinstall everything:"
    echo "    ./04_stop_and_uninstall_services.sh"
    echo "    ./01_install_and_start_services.sh"
    echo ""
    
    exit 1
fi

# =============================================================================
# ALL GOOD
# =============================================================================

print_header "ALL SERVICES RUNNING"

echo ""
print_info "Web Dashboard: http://${HOSTNAME}.local"
print_info "Direct:        http://${HOSTNAME}.local:7070"
echo ""

exit 0
