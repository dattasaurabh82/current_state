#!/bin/bash
# =============================================================================
# setup.sh
#
# Main setup script for World Theme Music Player
# Installs all dependencies and configures the environment
#
# Usage (first time - via curl/wget):
#   curl -fsSL https://raw.githubusercontent.com/dattasaurabh82/current_state/main/setup.sh | bash
#   OR
#   wget -qO- https://raw.githubusercontent.com/dattasaurabh82/current_state/main/setup.sh | bash
#
# Usage (after clone - local):
#   ./setup.sh
#
# =============================================================================

set -e  # Exit on error

# =============================================================================
# CONFIGURATION
# =============================================================================

REPO_URL="https://github.com/dattasaurabh82/current_state.git"
PROJECT_NAME="current_state"
INSTALL_DIR="$HOME/$PROJECT_NAME"
HOSTNAME="aimusicplayer"

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

prompt_input() {
    local prompt="$1"
    local var_name="$2"
    local is_secret="${3:-false}"
    
    echo -ne "${CYAN}?${NC} $prompt: "
    if [ "$is_secret" = "true" ]; then
        read -s value
        echo ""  # New line after hidden input
    else
        read value
    fi
    eval "$var_name='$value'"
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
# DETECT EXECUTION CONTEXT
# =============================================================================

detect_context() {
    # Check if we're running from within the project directory
    if [ -f "pyproject.toml" ] && grep -q "world-theme-music-player\|current_state" "pyproject.toml" 2>/dev/null; then
        CONTEXT="local"
        PROJECT_DIR="$(pwd)"
    elif [ -f "../pyproject.toml" ] && grep -q "world-theme-music-player\|current_state" "../pyproject.toml" 2>/dev/null; then
        CONTEXT="local"
        PROJECT_DIR="$(cd .. && pwd)"
    else
        CONTEXT="remote"
        PROJECT_DIR="$INSTALL_DIR"
    fi
}

# Restore stdin for interactive prompts (needed when piped via curl | bash)
if [ -t 0 ] || [ -e /dev/tty ]; then
    exec < /dev/tty
fi

# =============================================================================
# SYSTEM CHECKS
# =============================================================================

check_raspberry_pi() {
    print_step "Checking system..."
    
    # Use /proc/cpuinfo instead of /proc/device-tree/model to avoid null byte issues
    if [ -f /proc/cpuinfo ]; then
        if grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
            MODEL=$(grep "Model" /proc/cpuinfo | cut -d: -f2 | xargs)
            print_success "Running on: $MODEL"
            return 0
        fi
    fi
    
    print_warning "Not running on Raspberry Pi"
    print_info "Some features (GPIO, hardware buttons) won't work"
    
    if ! confirm "Continue anyway?"; then
        echo "Exiting."
        exit 0
    fi
}

check_internet() {
    print_step "Checking internet connection..."
    
    if ping -c 1 google.com &> /dev/null; then
        print_success "Internet connection OK"
    else
        print_error "No internet connection"
        print_info "Please connect to the internet and try again"
        exit 1
    fi
}

sync_datetime() {
    print_header "SYNCING DATE/TIME"
    
    print_step "Enabling NTP time synchronization..."
    sudo timedatectl set-ntp true
    print_success "NTP enabled"
    
    print_step "Restarting time sync service..."
    sudo systemctl restart systemd-timesyncd
    
    # Wait a moment for sync
    sleep 2
    
    # Show current time
    CURRENT_TIME=$(date)
    print_success "System time: $CURRENT_TIME"
    
    # Verify sync status
    if timedatectl show --property=NTPSynchronized --value | grep -q "yes"; then
        print_success "Time synchronized with NTP server"
    else
        print_warning "NTP sync pending (may take a moment)"
        print_info "Time will sync automatically in the background"
    fi
}

# =============================================================================
# SYSTEM CONFIGURATION FUNCTIONS
# =============================================================================

configure_hostname() {
    print_header "CONFIGURING HOSTNAME"
    
    CURRENT_HOSTNAME=$(hostname)
    
    if [ "$CURRENT_HOSTNAME" = "$HOSTNAME" ]; then
        print_info "Hostname already set to '$HOSTNAME'"
    else
        print_step "Setting hostname to '$HOSTNAME'..."
        sudo raspi-config nonint do_hostname "$HOSTNAME"
        print_success "Hostname set to '$HOSTNAME'"
        print_info "After reboot, access via: ${HOSTNAME}.local"
        REBOOT_REQUIRED=true
    fi
}

configure_autologin() {
    print_header "CONFIGURING AUTO-LOGIN"
    
    print_step "Enabling console auto-login..."
    sudo raspi-config nonint do_boot_behaviour B2
    print_success "Auto-login enabled for user: $USER"
    REBOOT_REQUIRED=true
}

configure_interfaces() {
    print_header "CONFIGURING HARDWARE INTERFACES"
    
    # Disable I2C (frees GPIO3 for power button)
    print_step "Disabling I2C (to free GPIO3 for power button)..."
    sudo raspi-config nonint do_i2c 1
    print_success "I2C disabled"
    
    # Enable Serial Hardware (for RD-03D radar)
    print_step "Enabling serial hardware (for RD-03D radar)..."
    sudo raspi-config nonint do_serial_hw 0
    print_success "Serial hardware enabled"
    
    # Disable Serial Console (so it doesn't interfere with radar)
    print_step "Disabling serial console (prevents interference with radar)..."
    sudo raspi-config nonint do_serial_cons 1
    print_success "Serial console disabled"
    
    REBOOT_REQUIRED=true
}

configure_gpio_shutdown() {
    print_header "CONFIGURING GPIO SHUTDOWN BUTTON"
    
    CONFIG_FILE="/boot/firmware/config.txt"
    OVERLAY_LINE="dtoverlay=gpio-shutdown"
    
    # Check if already configured
    if grep -q "^${OVERLAY_LINE}" "$CONFIG_FILE" 2>/dev/null; then
        print_info "GPIO shutdown overlay already configured"
        return 0
    fi
    
    print_step "Adding GPIO shutdown overlay to config.txt..."
    
    # CRITICAL: Must be placed BEFORE any [section] blocks like [cm4], [cm5], [all]
    # Best location: right after "# /boot/firmware/overlays/README" comment
    
    # Create temp file
    TEMP_FILE=$(mktemp)
    
    # Insert the overlay line after the README comment line
    # This ensures it's in the main body, before any [section] blocks
    awk -v overlay="$OVERLAY_LINE" '
        /^# \/boot\/firmware\/overlays\/README/ {
            print
            print overlay
            next
        }
        { print }
    ' "$CONFIG_FILE" > "$TEMP_FILE"
    
    # Verify the insertion worked
    if grep -q "^${OVERLAY_LINE}" "$TEMP_FILE"; then
        sudo cp "$TEMP_FILE" "$CONFIG_FILE"
        print_success "GPIO shutdown overlay added"
        print_info "GPIO3 button will now shutdown/wake the Pi"
        REBOOT_REQUIRED=true
    else
        # Fallback: insert after the "Additional overlays" comment
        awk -v overlay="$OVERLAY_LINE" '
            /^# Additional overlays and parameters/ {
                print
                getline
                print
                print overlay
                next
            }
            { print }
        ' "$CONFIG_FILE" > "$TEMP_FILE"
        
        if grep -q "^${OVERLAY_LINE}" "$TEMP_FILE"; then
            sudo cp "$TEMP_FILE" "$CONFIG_FILE"
            print_success "GPIO shutdown overlay added (fallback location)"
            REBOOT_REQUIRED=true
        else
            print_error "Failed to add GPIO shutdown overlay automatically"
            print_info "Please add manually to $CONFIG_FILE:"
            print_info "  $OVERLAY_LINE"
            print_info "  (Place it BEFORE any [cm4], [cm5], [all] sections)"
        fi
    fi
    
    rm -f "$TEMP_FILE"
}

configure_settings() {
    print_header "CONFIGURING SETTINGS"
    
    SETTINGS_FILE="$PROJECT_DIR/settings.json"
    SETTINGS_TEMPLATE="$PROJECT_DIR/settings.json.template"
    
    if [ -f "$SETTINGS_FILE" ]; then
        print_info "settings.json already exists"
        
        if confirm "Reconfigure settings?"; then
            cp "$SETTINGS_FILE" "$SETTINGS_FILE.bak"
            print_info "Backed up existing settings to settings.json.bak"
        else
            print_info "Keeping existing settings.json"
            return 0
        fi
    fi
    
    if [ ! -f "$SETTINGS_TEMPLATE" ]; then
        print_error "settings.json.template not found"
        return 1
    fi
    
    # Copy template first
    cp "$SETTINGS_TEMPLATE" "$SETTINGS_FILE"
    
    echo ""
    print_info "Let's configure your hardware settings."
    echo ""
    
    # 1. Radar Model
    echo -e "${CYAN}?${NC} Select radar model:"
    echo "    1) RCWL-0516 (GPIO-based, simple presence detection)"
    echo "    2) RD-03D (Serial UART, distance-based detection)"
    echo -ne "${CYAN}?${NC} Enter choice [1]: "
    read radar_choice
    radar_choice=${radar_choice:-1}
    
    if [ "$radar_choice" = "2" ]; then
        RADAR_MODEL="RD-03D"
        
        # 2. Radar Range (only for RD-03D)
        echo -ne "${CYAN}?${NC} Enter detection range in meters [2.5]: "
        read radar_range
        radar_range=${radar_range:-2.5}
    else
        RADAR_MODEL="RCWL-0516"
        radar_range="2.5"  # Keep default, not used for RCWL
    fi
    print_success "Radar: $RADAR_MODEL"
    
    # 3. Motion Triggered Playback Duration
    echo -ne "${CYAN}?${NC} Playback duration after motion detected (seconds) [300]: "
    read playback_duration
    playback_duration=${playback_duration:-300}
    print_success "Playback duration: ${playback_duration}s"
    
    # 4. LED Brightness
    echo -ne "${CYAN}?${NC} LED brightness (0-100) [25]: "
    read led_brightness
    led_brightness=${led_brightness:-25}
    print_success "LED brightness: $led_brightness"
    
    echo ""
    
    # Update settings.json using jq
    print_step "Saving settings..."
    
    jq --arg radar "$RADAR_MODEL" \
       --argjson range "$radar_range" \
       --argjson duration "$playback_duration" \
       --argjson brightness "$led_brightness" \
       '.inputPins.radarModel = $radar | 
        .hwFeatures.radarMaxRangeMeters = $range | 
        .hwFeatures.motionTriggeredPlaybackDurationSec = $duration | 
        .hwFeatures.maxLEDBrightness = $brightness' \
       "$SETTINGS_FILE" > "${SETTINGS_FILE}.tmp" && mv "${SETTINGS_FILE}.tmp" "$SETTINGS_FILE"
    
    print_success "Settings saved to settings.json"
}

# =============================================================================
# INSTALLATION FUNCTIONS
# =============================================================================

install_system_deps() {
    print_header "INSTALLING SYSTEM DEPENDENCIES"
    
    print_step "Updating package lists..."
    sudo apt update -y
    print_success "Package lists updated"
    
    print_step "Upgrading existing packages..."
    sudo apt upgrade -y
    print_success "Packages upgraded"
    
    print_step "Installing build tools and libraries..."
    sudo apt install -y \
        git \
        build-essential \
        libssl-dev \
        zlib1g-dev \
        libbz2-dev \
        libreadline-dev \
        libsqlite3-dev \
        curl \
        libncursesw5-dev \
        xz-utils \
        tk-dev \
        libxml2-dev \
        libxmlsec1-dev \
        libffi-dev \
        liblzma-dev \
        jq \
        tree \
        python3-dev
    print_success "Build tools installed"
}

install_audio_deps() {
    print_header "INSTALLING AUDIO DEPENDENCIES"
    
    print_step "Installing PortAudio..."
    sudo apt install -y libportaudio2
    print_success "PortAudio installed"
}

install_uv() {
    print_header "INSTALLING UV PACKAGE MANAGER"
    
    if command -v uv &> /dev/null; then
        print_info "UV is already installed: $(uv --version)"
        
        if confirm "Update to latest version?"; then
            print_step "Updating UV..."
            curl -LsSf https://astral.sh/uv/install.sh | sh
            print_success "UV updated"
        fi
    else
        print_step "Installing UV..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        print_success "UV installed"
    fi
    
    # Ensure UV is in PATH for this session
    export PATH="$HOME/.local/bin:$PATH"
    
    # Add to shell config if not present
    SHELL_RC="$HOME/.bashrc"
    if [ -f "$HOME/.zshrc" ]; then
        SHELL_RC="$HOME/.zshrc"
    fi
    
    if ! grep -q '.local/bin' "$SHELL_RC" 2>/dev/null; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
        print_success "Added UV to $SHELL_RC"
    fi
    
    # Verify installation
    if command -v uv &> /dev/null || [ -x "$HOME/.local/bin/uv" ]; then
        print_success "UV ready: $($HOME/.local/bin/uv --version 2>/dev/null || uv --version)"
    else
        print_error "UV installation failed"
        exit 1
    fi
}

configure_gpio() {
    print_header "CONFIGURING GPIO PERMISSIONS"
    
    CURRENT_USER="$USER"
    
    if groups "$CURRENT_USER" | grep -q '\bgpio\b'; then
        print_info "User '$CURRENT_USER' already in gpio group"
    else
        print_step "Adding user '$CURRENT_USER' to gpio group..."
        sudo usermod -a -G gpio "$CURRENT_USER"
        print_success "User added to gpio group"
        print_warning "You'll need to log out and back in for this to take effect"
        GPIO_CHANGED=true
    fi
}

clone_or_update_repo() {
    print_header "SETTING UP PROJECT"
    
    if [ "$CONTEXT" = "local" ]; then
        print_info "Already in project directory: $PROJECT_DIR"
        cd "$PROJECT_DIR"
        
        if confirm "Pull latest changes from git?" "y"; then
            print_step "Pulling latest changes..."
            git pull
            print_success "Repository updated"
        fi
    else
        # Remote context - need to clone
        if [ -d "$INSTALL_DIR" ]; then
            print_info "Project found at $INSTALL_DIR"
            cd "$INSTALL_DIR"
            PROJECT_DIR="$INSTALL_DIR"
            
            if confirm "Pull latest changes from git?" "y"; then
                print_step "Pulling latest changes..."
                git pull
                print_success "Repository updated"
            fi
        else
            print_step "Cloning repository to $INSTALL_DIR..."
            git clone "$REPO_URL" "$INSTALL_DIR"
            cd "$INSTALL_DIR"
            PROJECT_DIR="$INSTALL_DIR"
            print_success "Repository cloned"
        fi
    fi
}

install_python_deps() {
    print_header "INSTALLING PYTHON DEPENDENCIES"
    
    # Use full path to uv in case PATH isn't updated yet
    UV_CMD="${HOME}/.local/bin/uv"
    if ! [ -x "$UV_CMD" ]; then
        UV_CMD="uv"
    fi
    
    print_step "Running uv sync..."
    $UV_CMD sync
    print_success "Python dependencies installed"
    
    # Check if RPi.GPIO is needed and install if missing
    if grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
        print_step "Checking RPi.GPIO..."
        if ! $UV_CMD run python -c "import RPi.GPIO" 2>/dev/null; then
            print_warning "RPi.GPIO not installed, attempting installation..."
            $UV_CMD pip install RPi.GPIO --break-system-packages || true
        else
            print_success "RPi.GPIO is available"
        fi
    fi
}

configure_env() {
    print_header "CONFIGURING API CREDENTIALS"
    
    ENV_FILE="$PROJECT_DIR/.env"
    ENV_TEMPLATE="$PROJECT_DIR/.env.template"
    
    if [ -f "$ENV_FILE" ]; then
        print_info ".env file already exists"
        
        if confirm "Reconfigure API credentials?"; then
            # Backup existing
            cp "$ENV_FILE" "$ENV_FILE.bak"
            print_info "Backed up existing .env to .env.bak"
        else
            print_info "Keeping existing .env"
            return 0
        fi
    fi
    
    echo ""
    print_info "You'll need your API keys ready."
    print_info "Get them from:"
    echo -e "  ${DIM}NewsAPI:${NC}    https://newsapi.org/account"
    echo -e "  ${DIM}Replicate:${NC}  https://replicate.com/account/api-tokens"
    echo ""
    
    if ! confirm "Ready to enter credentials?" "y"; then
        print_warning "Skipping credential configuration"
        print_info "You can manually edit .env later:"
        print_info "  cp .env.template .env"
        print_info "  nano .env"
        return 0
    fi
    
    echo ""
    prompt_input "Enter NewsAPI key" NEWS_API_KEY true
    prompt_input "Enter Replicate API token" REPLICATE_API_TOKEN true
    
    # Write .env file (keep Dropbox placeholders)
    cat > "$ENV_FILE" << EOF
NEWS_API_KEY="$NEWS_API_KEY"
REPLICATE_API_TOKEN="$REPLICATE_API_TOKEN"
DROPBOX_CLIENT_ID="YOUR_DROPBOX_CLIENT_ID_HERE"
DROPBOX_CLIENT_SECRET="YOUR_DROPBOX_CLIENT_SECRET_HERE"
DROPBOX_REFRESH_TOKEN="YOUR_DROPBOX_REFRESH_TOKEN_HERE"
EOF
    
    chmod 600 "$ENV_FILE"
    print_success "API credentials saved to .env"
}

# =============================================================================
# MAIN
# =============================================================================

main() {
    print_header "WORLD THEME MUSIC PLAYER - SETUP"
    
    # Detect if running locally or via curl/wget
    detect_context
    
    echo ""
    if [ "$CONTEXT" = "local" ]; then
        print_info "Running in LOCAL mode (project already cloned)"
    else
        print_info "Running in REMOTE mode (will clone project)"
    fi
    echo ""
    
    echo "  This script will install:"
    echo "    • System dependencies (build tools, libraries)"
    echo "    • Audio dependencies (PortAudio)"
    echo "    • UV package manager"
    echo "    • Python dependencies"
    echo ""
    echo "  And configure:"
    echo "    • Hostname (${HOSTNAME}.local)"
    echo "    • Console auto-login"
    echo "    • Hardware interfaces (I2C, Serial)"
    echo "    • GPIO shutdown button (GPIO3)"
    echo "    • GPIO permissions"
    echo "    • Hardware settings (settings.json)"
    echo "    • API credentials (.env)"
    echo ""
    
    if ! confirm "Continue with installation?" "y"; then
        echo "Exiting."
        exit 0
    fi
    
    # Run checks
    check_raspberry_pi
    check_internet
    
    # Sync time first (requires internet)
    sync_datetime
    
    # Run installation steps
    install_system_deps
    install_audio_deps
    install_uv
    configure_gpio
    clone_or_update_repo
    install_python_deps
    
    # Configure system (hostname, autologin, interfaces, GPIO shutdown)
    configure_hostname
    configure_autologin
    configure_interfaces
    configure_gpio_shutdown
    
    # Configure project files
    configure_settings
    configure_env
    
    # =============================================================================
    # COMPLETE
    # =============================================================================
    
    echo ""
    echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}SETUP COMPLETE - REBOOT REQUIRED${NC}"
    echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${GREEN}✓${NC} Date/time synchronized"
    echo -e "  ${GREEN}✓${NC} System dependencies installed"
    echo -e "  ${GREEN}✓${NC} Audio dependencies installed"
    echo -e "  ${GREEN}✓${NC} UV package manager installed"
    echo -e "  ${GREEN}✓${NC} GPIO permissions configured"
    echo -e "  ${GREEN}✓${NC} Python dependencies installed"
    echo -e "  ${GREEN}✓${NC} Hostname set to: ${HOSTNAME}"
    echo -e "  ${GREEN}✓${NC} Console auto-login enabled"
    echo -e "  ${GREEN}✓${NC} I2C disabled (GPIO3 available for power button)"
    echo -e "  ${GREEN}✓${NC} Serial enabled (for RD-03D radar)"
    echo -e "  ${GREEN}✓${NC} GPIO shutdown overlay configured"
    echo -e "  ${GREEN}✓${NC} Hardware settings configured (settings.json)"
    echo -e "  ${GREEN}✓${NC} API credentials configured (.env)"
    echo ""
    echo "  Project location: $PROJECT_DIR"
    echo ""
    echo -e "${YELLOW}════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${YELLOW}  NEXT STEPS${NC}"
    echo -e "${YELLOW}════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${RED}1. REBOOT NOW (required for changes to take effect):${NC}"
    echo -e "     ${DIM}sudo reboot${NC}"
    echo ""
    echo -e "  2. After reboot, test hardware:"
    echo -e "     ${DIM}cd ~/current_state${NC}"
    echo -e "     ${DIM}uv run python tests/01_test_IOs.py${NC}"
    echo ""
    echo -e "  3. Install WiFi manager (optional, for headless setup):"
    echo -e "     ${DIM}See README.md Step 5${NC}"
    echo ""
    echo -e "  4. Install services:"
    echo -e "     ${DIM}./services/01_install_and_start_services.sh${NC}"
    echo ""
    echo -e "${CYAN}────────────────────────────────────────────────────────────${NC}"
    print_info "After reboot, access web dashboard at: http://${HOSTNAME}.local"
    print_info "See README.md for detailed instructions"
    echo ""
    print_info "To re-run this setup later:"
    echo -e "     ${DIM}cd $PROJECT_DIR && ./setup.sh${NC}"
    echo ""
}

# Run main function
main "$@"
