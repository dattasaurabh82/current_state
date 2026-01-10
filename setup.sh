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

# =============================================================================
# SYSTEM CHECKS
# =============================================================================

check_raspberry_pi() {
    print_step "Checking system..."
    
    if [ -f /proc/device-tree/model ]; then
        MODEL=$(cat /proc/device-tree/model)
        if [[ "$MODEL" == *"Raspberry Pi"* ]]; then
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
    if [ -f /proc/device-tree/model ]; then
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
    echo "    • GPIO permissions"
    echo "    • API credentials (.env file)"
    echo ""
    
    if ! confirm "Continue with installation?" "y"; then
        echo "Exiting."
        exit 0
    fi
    
    # Run checks
    check_raspberry_pi
    check_internet
    
    # Run installation steps
    install_system_deps
    install_audio_deps
    install_uv
    configure_gpio
    clone_or_update_repo
    install_python_deps
    configure_env
    
    # =============================================================================
    # COMPLETE
    # =============================================================================
    
    print_header "SETUP COMPLETE"
    
    echo ""
    echo -e "  ${GREEN}✓${NC} System dependencies installed"
    echo -e "  ${GREEN}✓${NC} Audio dependencies installed"
    echo -e "  ${GREEN}✓${NC} UV package manager installed"
    echo -e "  ${GREEN}✓${NC} GPIO permissions configured"
    echo -e "  ${GREEN}✓${NC} Python dependencies installed"
    echo -e "  ${GREEN}✓${NC} API credentials configured"
    echo ""
    
    if [ "$GPIO_CHANGED" = true ]; then
        print_warning "IMPORTANT: Log out and back in for GPIO permissions to take effect"
        echo ""
    fi
    
    echo "  Project location: $PROJECT_DIR"
    echo ""
    echo "  Next steps:"
    echo ""
    echo "    1. ${DIM}cd $PROJECT_DIR${NC}"
    echo ""
    echo "    2. Test hardware:"
    echo "       ${DIM}uv run python tests/01_test_IOs.py${NC}"
    echo ""
    echo "    3. Test full pipeline:"
    echo "       ${DIM}uv run python main.py --fetch true --play false${NC}"
    echo ""
    echo "    4. Install services:"
    echo "       ${DIM}./services/01_install_and_start_services.sh${NC}"
    echo ""
    
    print_info "See README.md for detailed instructions"
    echo ""
    print_info "To re-run this setup later:"
    echo "       ${DIM}cd $PROJECT_DIR && ./setup.sh${NC}"
}

# Run main function
main "$@"
