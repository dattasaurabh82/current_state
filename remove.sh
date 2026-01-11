#!/bin/bash
# =============================================================================
# remove.sh
#
# Complete removal script for World Theme Music Player
# Removes services, configurations, and optionally the project files
#
# This script:
# - Stops and removes all services (calls existing uninstall script)
# - Optionally removes project files
# - Optionally removes UV and Python virtual environment
# - Optionally reverts system configuration (hostname, I2C, serial, etc.)
#
# Usage: ./remove.sh
#
# =============================================================================

set -e  # Exit on error

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

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

confirm() {
    local prompt="$1"
    local default="${2:-n}"
    
    if [ "$default" = "y" ]; then
        echo -ne "${CYAN}?${NC} $prompt [Y/n]: "
    else
        echo -ne "${CYAN}?${NC} $prompt [y/N]: "
    fi
    
    read response
    response=${response:-$default}
    
    [[ "$response" =~ ^[Yy]$ ]]
}

# =============================================================================
# DERIVED VARIABLES
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
PROJECT_NAME="$(basename "$PROJECT_DIR")"

CURRENT_USER="$USER"
USER_HOME="$HOME"

SERVICES_UNINSTALL="$PROJECT_DIR/services/04_stop_and_uninstall_services.sh"

REBOOT_REQUIRED=false

# =============================================================================
# REMOVAL FUNCTIONS
# =============================================================================

remove_services() {
    print_header "REMOVING SERVICES"
    
    if [ -x "$SERVICES_UNINSTALL" ]; then
        print_step "Running service uninstaller..."
        "$SERVICES_UNINSTALL"
        print_success "Services removed"
    else
        print_info "Service uninstall script not found, checking manually..."
        
        # Manual service removal
        SERVICES=(
            "music-player.service"
            "full-cycle-btn.service"
            "process-monitor-web.service"
        )
        
        for service in "${SERVICES[@]}"; do
            if systemctl --user is-active --quiet "$service" 2>/dev/null; then
                systemctl --user stop "$service" || true
                print_success "Stopped $service"
            fi
            
            if systemctl --user is-enabled --quiet "$service" 2>/dev/null; then
                systemctl --user disable "$service" || true
                print_success "Disabled $service"
            fi
            
            SERVICE_FILE="$USER_HOME/.config/systemd/user/$service"
            if [ -f "$SERVICE_FILE" ]; then
                rm -f "$SERVICE_FILE"
                print_success "Removed $SERVICE_FILE"
            fi
        done
        
        systemctl --user daemon-reload || true
        
        # Remove nginx config
        if [ -L "/etc/nginx/sites-enabled/process-monitor-web" ]; then
            sudo rm -f "/etc/nginx/sites-enabled/process-monitor-web"
            print_success "Removed nginx site symlink"
        fi
        
        if [ -f "/etc/nginx/sites-available/process-monitor-web" ]; then
            sudo rm -f "/etc/nginx/sites-available/process-monitor-web"
            print_success "Removed nginx config"
        fi
        
        if systemctl is-active --quiet nginx 2>/dev/null; then
            sudo nginx -t && sudo systemctl reload nginx || true
        fi
    fi
}

remove_venv() {
    print_header "REMOVING VIRTUAL ENVIRONMENT"
    
    VENV_DIR="$PROJECT_DIR/.venv"
    
    if [ -d "$VENV_DIR" ]; then
        print_step "Removing .venv directory..."
        rm -rf "$VENV_DIR"
        print_success "Virtual environment removed"
    else
        print_info "No virtual environment found"
    fi
}

remove_generated_files() {
    print_header "REMOVING GENERATED FILES"
    
    # List of directories/files to remove
    GENERATED=(
        "$PROJECT_DIR/music_generated"
        "$PROJECT_DIR/generation_results"
        "$PROJECT_DIR/logs"
        "$PROJECT_DIR/__pycache__"
        "$PROJECT_DIR/lib/__pycache__"
        "$PROJECT_DIR/web/__pycache__"
        "$PROJECT_DIR/tests/__pycache__"
        "$PROJECT_DIR/tools/__pycache__"
        "$PROJECT_DIR/news_data_*.json"
        "$PROJECT_DIR/.env"
        "$PROJECT_DIR/settings.json"
    )
    
    for item in "${GENERATED[@]}"; do
        # Handle glob patterns
        for expanded in $item; do
            if [ -e "$expanded" ]; then
                if [ -d "$expanded" ]; then
                    rm -rf "$expanded"
                    print_success "Removed directory: $(basename "$expanded")"
                else
                    rm -f "$expanded"
                    print_success "Removed file: $(basename "$expanded")"
                fi
            fi
        done
    done
}

remove_project() {
    print_header "REMOVING PROJECT FILES"
    
    print_warning "This will delete the entire project directory:"
    echo "  $PROJECT_DIR"
    echo ""
    
    if confirm "Are you sure you want to delete all project files?"; then
        print_step "Removing project directory..."
        cd "$USER_HOME"
        rm -rf "$PROJECT_DIR"
        print_success "Project directory removed"
        PROJECT_REMOVED=true
    else
        print_info "Project files kept"
    fi
}

remove_uv() {
    print_header "REMOVING UV PACKAGE MANAGER"
    
    if command -v uv &> /dev/null || [ -x "$USER_HOME/.local/bin/uv" ]; then
        print_warning "UV is a standalone tool that may be used by other projects"
        
        if confirm "Remove UV package manager?"; then
            print_step "Removing UV..."
            
            # Remove UV binary
            UV_PATH="$USER_HOME/.local/bin/uv"
            UVX_PATH="$USER_HOME/.local/bin/uvx"
            
            [ -f "$UV_PATH" ] && rm -f "$UV_PATH"
            [ -f "$UVX_PATH" ] && rm -f "$UVX_PATH"
            
            # Remove UV cache
            UV_CACHE="$USER_HOME/.cache/uv"
            [ -d "$UV_CACHE" ] && rm -rf "$UV_CACHE"
            
            print_success "UV removed"
        else
            print_info "UV kept"
        fi
    else
        print_info "UV not installed"
    fi
}

revert_system_config() {
    print_header "REVERTING SYSTEM CONFIGURATION"
    
    print_warning "This will revert system settings changed by setup.sh"
    echo ""
    echo "  Will revert:"
    echo "    • Hostname → raspberrypi"
    echo "    • Cloud-init hostname fix → removed"
    echo "    • I2C → enabled"
    echo "    • Serial hardware → disabled"
    echo "    • Serial console → enabled"
    echo "    • Auto-login → disabled"
    echo "    • GPIO shutdown overlay → removed"
    echo ""
    
    if ! confirm "Revert all system configurations?"; then
        print_info "System configurations kept"
        return 0
    fi
    
    # Revert hostname
    print_step "Reverting hostname to 'raspberrypi'..."
    sudo raspi-config nonint do_hostname raspberrypi
    print_success "Hostname reverted"
    
    # Remove cloud-init fix
    if [ -f /etc/cloud/cloud.cfg.d/99_preserve_hostname.cfg ]; then
        print_step "Removing cloud-init hostname fix..."
        sudo rm -f /etc/cloud/cloud.cfg.d/99_preserve_hostname.cfg
        print_success "Cloud-init fix removed"
    fi
    
    # Re-enable I2C
    print_step "Re-enabling I2C..."
    sudo raspi-config nonint do_i2c 0
    print_success "I2C enabled"
    
    # Disable serial hardware
    print_step "Disabling serial hardware..."
    sudo raspi-config nonint do_serial_hw 1
    print_success "Serial hardware disabled"
    
    # Enable serial console
    print_step "Enabling serial console..."
    sudo raspi-config nonint do_serial_cons 0
    print_success "Serial console enabled"
    
    # Disable auto-login
    print_step "Disabling auto-login..."
    sudo raspi-config nonint do_boot_behaviour B1
    print_success "Auto-login disabled"
    
    # Remove GPIO shutdown overlay
    if grep -q "^dtoverlay=gpio-shutdown" /boot/firmware/config.txt 2>/dev/null; then
        print_step "Removing GPIO shutdown overlay..."
        sudo sed -i '/^dtoverlay=gpio-shutdown$/d' /boot/firmware/config.txt
        print_success "GPIO shutdown overlay removed"
    fi
    
    REBOOT_REQUIRED=true
    print_success "System configuration reverted"
}

# =============================================================================
# MAIN
# =============================================================================

main() {
    print_header "WORLD THEME MUSIC PLAYER - REMOVAL"
    
    echo ""
    echo "  This script can remove:"
    echo "    • Services (systemd, nginx)"
    echo "    • Virtual environment (.venv)"
    echo "    • Generated files (music, logs, cache)"
    echo "    • Project files (entire directory)"
    echo "    • UV package manager"
    echo "    • System configuration (hostname, I2C, serial, auto-login)"
    echo ""
    print_warning "This action cannot be undone!"
    echo ""
    
    if ! confirm "Continue with removal?"; then
        echo "Exiting."
        exit 0
    fi
    
    echo ""
    echo "Select what to remove:"
    echo ""
    
    # Services (always offered)
    REMOVE_SERVICES=false
    if confirm "Remove services (systemd, nginx config)?"; then
        REMOVE_SERVICES=true
    fi
    
    # Virtual environment
    REMOVE_VENV=false
    if confirm "Remove Python virtual environment (.venv)?"; then
        REMOVE_VENV=true
    fi
    
    # Generated files
    REMOVE_GENERATED=false
    if confirm "Remove generated files (music, logs, settings.json, .env)?"; then
        REMOVE_GENERATED=true
    fi
    
    # Project files
    REMOVE_PROJECT=false
    if confirm "Remove entire project directory?"; then
        REMOVE_PROJECT=true
    fi
    
    # UV (only if removing project)
    REMOVE_UV=false
    if [ "$REMOVE_PROJECT" = true ]; then
        if confirm "Remove UV package manager?"; then
            REMOVE_UV=true
        fi
    fi
    
    # System configuration (only if removing project)
    REVERT_SYSTEM=false
    if [ "$REMOVE_PROJECT" = true ]; then
        echo ""
        print_warning "System configuration changes (hostname, I2C, serial, etc.)"
        if confirm "Revert system configurations to defaults?"; then
            REVERT_SYSTEM=true
        fi
    fi
    
    echo ""
    print_header "EXECUTING REMOVAL"
    
    # Execute in order
    [ "$REMOVE_SERVICES" = true ] && remove_services
    [ "$REMOVE_VENV" = true ] && remove_venv
    [ "$REMOVE_GENERATED" = true ] && remove_generated_files
    [ "$REMOVE_PROJECT" = true ] && remove_project
    [ "$REMOVE_UV" = true ] && remove_uv
    [ "$REVERT_SYSTEM" = true ] && revert_system_config
    
    # =============================================================================
    # COMPLETE
    # =============================================================================
    
    print_header "REMOVAL COMPLETE"
    
    echo ""
    echo "  Removed:"
    [ "$REMOVE_SERVICES" = true ] && echo -e "    ${GREEN}✓${NC} Services"
    [ "$REMOVE_VENV" = true ] && echo -e "    ${GREEN}✓${NC} Virtual environment"
    [ "$REMOVE_GENERATED" = true ] && echo -e "    ${GREEN}✓${NC} Generated files"
    [ "$REMOVE_PROJECT" = true ] && echo -e "    ${GREEN}✓${NC} Project directory"
    [ "$REMOVE_UV" = true ] && echo -e "    ${GREEN}✓${NC} UV package manager"
    [ "$REVERT_SYSTEM" = true ] && echo -e "    ${GREEN}✓${NC} System configuration"
    echo ""
    
    echo "  Not removed:"
    [ "$REMOVE_SERVICES" = false ] && echo -e "    ${DIM}• Services${NC}"
    [ "$REMOVE_VENV" = false ] && echo -e "    ${DIM}• Virtual environment${NC}"
    [ "$REMOVE_GENERATED" = false ] && echo -e "    ${DIM}• Generated files${NC}"
    [ "$REMOVE_PROJECT" = false ] && echo -e "    ${DIM}• Project directory${NC}"
    [ "$REMOVE_UV" = false ] && echo -e "    ${DIM}• UV package manager${NC}"
    [ "$REVERT_SYSTEM" = false ] && echo -e "    ${DIM}• System configuration (hostname, I2C, serial, auto-login)${NC}"
    echo -e "    ${DIM}• System dependencies (apt packages)${NC}"
    echo -e "    ${DIM}• Audio dependencies (PortAudio)${NC}"
    echo -e "    ${DIM}• GPIO group membership${NC}"
    echo ""
    
    if [ "$PROJECT_REMOVED" = true ]; then
        print_info "To reinstall: curl -fsSL https://raw.githubusercontent.com/dattasaurabh82/current_state/main/setup.sh | bash"
    else
        print_info "To reinstall services: ./services/01_install_and_start_services.sh"
    fi
    
    if [ "$REBOOT_REQUIRED" = true ]; then
        echo ""
        print_warning "Reboot required for system changes to take effect"
        if confirm "Reboot now?"; then
            sudo reboot
        else
            print_info "Remember to reboot later: sudo reboot"
        fi
    fi
}

# Run main function
main "$@"
