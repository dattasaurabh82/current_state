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
    
    if command -v uv &> /dev/null; then
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
    if confirm "Remove generated files (music, logs, news cache)?"; then
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
    
    echo ""
    print_header "EXECUTING REMOVAL"
    
    # Execute in order
    [ "$REMOVE_SERVICES" = true ] && remove_services
    [ "$REMOVE_VENV" = true ] && remove_venv
    [ "$REMOVE_GENERATED" = true ] && remove_generated_files
    [ "$REMOVE_PROJECT" = true ] && remove_project
    [ "$REMOVE_UV" = true ] && remove_uv
    
    # =============================================================================
    # COMPLETE
    # =============================================================================
    
    print_header "REMOVAL COMPLETE"
    
    echo ""
    echo "  Removed:"
    [ "$REMOVE_SERVICES" = true ] && echo "    ${GREEN}✓${NC} Services"
    [ "$REMOVE_VENV" = true ] && echo "    ${GREEN}✓${NC} Virtual environment"
    [ "$REMOVE_GENERATED" = true ] && echo "    ${GREEN}✓${NC} Generated files"
    [ "$REMOVE_PROJECT" = true ] && echo "    ${GREEN}✓${NC} Project directory"
    [ "$REMOVE_UV" = true ] && echo "    ${GREEN}✓${NC} UV package manager"
    echo ""
    
    echo "  Not removed:"
    [ "$REMOVE_SERVICES" = false ] && echo "    ${DIM}• Services${NC}"
    [ "$REMOVE_VENV" = false ] && echo "    ${DIM}• Virtual environment${NC}"
    [ "$REMOVE_GENERATED" = false ] && echo "    ${DIM}• Generated files${NC}"
    [ "$REMOVE_PROJECT" = false ] && echo "    ${DIM}• Project directory${NC}"
    [ "$REMOVE_UV" = false ] && echo "    ${DIM}• UV package manager${NC}"
    echo "    ${DIM}• System dependencies (apt packages)${NC}"
    echo "    ${DIM}• Audio dependencies (PortAudio)${NC}"
    echo "    ${DIM}• GPIO group membership${NC}"
    echo ""
    
    if [ "$PROJECT_REMOVED" = true ]; then
        print_info "To reinstall: curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/current_state/main/setup.sh | bash"
    else
        print_info "To reinstall services: ./services/01_install_and_start_services.sh"
    fi
}

# Run main function
main "$@"
