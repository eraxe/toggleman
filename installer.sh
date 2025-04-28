#!/bin/bash
# Toggleman Installer Script
# This script installs the Toggleman application on Arch Linux with KDE

set -e  # Exit on error

# Define colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Define installation paths
APP_NAME="toggleman"
INSTALL_DIR="/opt/${APP_NAME}"
CONFIG_DIR="${HOME}/.config/${APP_NAME}"
SHARE_DIR="/usr/share/${APP_NAME}"
BIN_PATH="/usr/local/bin/${APP_NAME}"
DESKTOP_PATH="/usr/share/applications/${APP_NAME}.desktop"
AUTOSTART_PATH="${HOME}/.config/autostart/${APP_NAME}.desktop"
ICON_PATH="/usr/share/icons/hicolor/128x128/apps/${APP_NAME}.png"

# Function to check if running as root with sudo
check_sudo() {
    if [ "$EUID" -ne 0 ]; then
        echo -e "${RED}Please run this script with sudo privileges.${NC}"
        exit 1
    fi
}

# Function to check dependencies
check_dependencies() {
    local missing_deps=()

    # Check for Python and required modules
    if ! command -v python3 &>/dev/null; then
        missing_deps+=("python")
    fi

    if ! python3 -c "import PyQt5" 2>/dev/null; then
        missing_deps+=("python-pyqt5")
    fi

    if ! python3 -c "import yaml" 2>/dev/null; then
        missing_deps+=("python-pyyaml")
    fi

    # Check for other required commands
    for cmd in qdbus xdotool notify-send; do
        if ! command -v "$cmd" &>/dev/null; then
            case "$cmd" in
                qdbus)
                    missing_deps+=("qt5-tools")
                    ;;
                xdotool)
                    missing_deps+=("xdotool")
                    ;;
                notify-send)
                    missing_deps+=("libnotify")
                    ;;
            esac
        fi
    done

    if [ ${#missing_deps[@]} -gt 0 ]; then
        echo -e "${RED}Missing required dependencies: ${missing_deps[*]}${NC}"
        echo -e "Installing them with pacman..."

        if ! pacman -S --noconfirm "${missing_deps[@]}"; then
            echo -e "${RED}Failed to install dependencies.${NC}"
            echo -e "Please install them manually: ${missing_deps[*]}"
            exit 1
        fi

        echo -e "${GREEN}Dependencies installed successfully.${NC}"
    fi
}

# Function to create necessary directories
create_directories() {
    echo "Creating necessary directories..."

    # Create installation directories
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$CONFIG_DIR/scripts"
    mkdir -p "$CONFIG_DIR/logs"
    mkdir -p "$SHARE_DIR"
    mkdir -p "$SHARE_DIR/templates"
    mkdir -p "$SHARE_DIR/icons"
    mkdir -p "$(dirname "$ICON_PATH")"

    # Set permissions
    chown -R "$SUDO_USER:$SUDO_USER" "$CONFIG_DIR"
    chmod -R 755 "$INSTALL_DIR"
}

# Function to copy application files
copy_files() {
    echo "Copying application files..."

    # Get the directory of the installation script
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

    # Copy Python package
    cp -r "$script_dir/toggleman" "$INSTALL_DIR/"

    # Copy templates
    cp -r "$script_dir/data/templates/"* "$SHARE_DIR/templates/"

    # Copy icons
    cp "$script_dir/data/icons/toggleman.svg" "$ICON_PATH"
    cp -r "$script_dir/data/icons/"* "$SHARE_DIR/icons/"

    # Set permissions
    chown -R root:root "$INSTALL_DIR"
    chown -R root:root "$SHARE_DIR"
    chmod -R 755 "$INSTALL_DIR"
    chmod -R 755 "$SHARE_DIR"
}

# Function to create executable
create_executable() {
    echo "Creating executable..."

    # Create executable script
    cat > "$BIN_PATH" << EOL
#!/bin/bash
python3 "$INSTALL_DIR/toggleman" "\$@"
EOL

    # Make it executable
    chmod +x "$BIN_PATH"
}

# Function to create desktop entry
create_desktop_entry() {
    echo "Creating desktop entry..."

    # Create desktop entry file
    cat > "$DESKTOP_PATH" << EOL
[Desktop Entry]
Version=1.0
Type=Application
Name=Toggleman
Comment=Manager for application toggle scripts
Exec=$BIN_PATH
Icon=$APP_NAME
Terminal=false
Categories=Utility;System;
Keywords=toggle;application;manager;
StartupNotify=true
EOL

    # Copy to autostart if requested
    if [ "$1" == "autostart" ]; then
        cp "$DESKTOP_PATH" "$AUTOSTART_PATH"
        chown "$SUDO_USER:$SUDO_USER" "$AUTOSTART_PATH"
    fi
}

# Function to create uninstaller
create_uninstaller() {
    echo "Creating uninstaller..."

    # Create uninstaller script
    cat > "$INSTALL_DIR/uninstall.sh" << EOL
#!/bin/bash
# Toggleman Uninstaller Script

set -e  # Exit on error

# Check if running as root
if [ "\$EUID" -ne 0 ]; then
    echo "Please run this script with sudo privileges."
    exit 1
fi

# Remove files and directories
echo "Removing Toggleman..."
rm -rf "$INSTALL_DIR"
rm -rf "$SHARE_DIR"
rm -f "$BIN_PATH"
rm -f "$DESKTOP_PATH"

# Ask if user wants to remove configuration
read -p "Do you want to remove user configuration too? (y/n): " remove_config
if [[ "\$remove_config" =~ ^[Yy] ]]; then
    echo "Removing configuration directory..."
    rm -rf "$CONFIG_DIR"
fi

echo "Toggleman has been uninstalled."
EOL

    # Make uninstaller executable
    chmod +x "$INSTALL_DIR/uninstall.sh"
}

# Main installation process
main() {
    echo -e "${BLUE}Installing Toggleman...${NC}"

    # Check if running with sudo
    check_sudo

    # Check for dependencies
    check_dependencies

    # Create directories
    create_directories

    # Copy files
    copy_files

    # Create executable
    create_executable

    # Create desktop entry (with autostart if requested)
    if [ "$1" == "autostart" ]; then
        create_desktop_entry "autostart"
        echo -e "${GREEN}Toggleman will start automatically at login.${NC}"
    else
        create_desktop_entry
    fi

    # Create uninstaller
    create_uninstaller

    # Create initial configuration
    if [ -n "$SUDO_USER" ]; then
        sudo -u "$SUDO_USER" python3 "$INSTALL_DIR/toggleman" --init
    else
        python3 "$INSTALL_DIR/toggleman" --init
    fi

    echo -e "${GREEN}Installation complete!${NC}"
    echo -e "You can run toggleman from the application menu or by typing 'toggleman' in terminal."
    echo -e "To uninstall, run: ${BLUE}sudo $INSTALL_DIR/uninstall.sh${NC}"
}

# Parse command line arguments
if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    echo "Usage: $0 [OPTIONS]"
    echo "Install Toggleman application."
    echo
    echo "Options:"
    echo "  --autostart    Configure Toggleman to start automatically at login"
    echo "  --help, -h     Display this help and exit"
    exit 0
elif [ "$1" == "--autostart" ]; then
    main "autostart"
else
    main
fi