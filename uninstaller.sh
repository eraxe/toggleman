#!/bin/bash
# Toggleman Uninstaller Script
# This script uninstalls the Toggleman application from the system

set -e  # Exit on error

# Define colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Define paths
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

# Function to stop running instances
stop_instances() {
    echo "Stopping any running instances..."
    pkill -f "${APP_NAME}" || true
}

# Function to remove application files
remove_files() {
    echo "Removing application files..."

    # Remove installation directory
    if [ -d "$INSTALL_DIR" ]; then
        rm -rf "$INSTALL_DIR"
    fi

    # Remove shared directory
    if [ -d "$SHARE_DIR" ]; then
        rm -rf "$SHARE_DIR"
    fi

    # Remove executable
    if [ -f "$BIN_PATH" ]; then
        rm -f "$BIN_PATH"
    fi

    # Remove desktop entry
    if [ -f "$DESKTOP_PATH" ]; then
        rm -f "$DESKTOP_PATH"
    fi

    # Remove autostart entry
    if [ -f "$AUTOSTART_PATH" ]; then
        rm -f "$AUTOSTART_PATH"
    fi

    # Remove icon
    if [ -f "$ICON_PATH" ]; then
        rm -f "$ICON_PATH"
    fi
}

# Function to handle user configuration
handle_config() {
    if [ -d "$CONFIG_DIR" ]; then
        read -p "Do you want to remove user configuration too? (y/n): " remove_config
        if [[ "$remove_config" =~ ^[Yy] ]]; then
            echo "Removing configuration directory..."
            rm -rf "$CONFIG_DIR"
        else
            echo "Keeping configuration directory at $CONFIG_DIR"
        fi
    fi
}

# Function to clean up any leftover toggle scripts
clean_toggle_scripts() {
    local toggle_scripts=($(find "$HOME/.local/bin" -name "toggle-*.sh" 2>/dev/null))

    if [ ${#toggle_scripts[@]} -gt 0 ]; then
        echo "Found ${#toggle_scripts[@]} toggle scripts in $HOME/.local/bin"
        read -p "Do you want to remove these toggle scripts as well? (y/n): " remove_scripts

        if [[ "$remove_scripts" =~ ^[Yy] ]]; then
            echo "Removing toggle scripts..."
            for script in "${toggle_scripts[@]}"; do
                rm -f "$script"
                echo "Removed: $script"
            done
        else
            echo "Keeping toggle scripts"
        fi
    fi
}

# Function to clean up system tray components
clean_tray_components() {
    local tray_dir="$HOME/.cache/toggle_app"

    if [ -d "$tray_dir" ]; then
        echo "Found system tray components in $tray_dir"
        read -p "Do you want to remove these components as well? (y/n): " remove_tray

        if [[ "$remove_tray" =~ ^[Yy] ]]; then
            echo "Removing system tray components..."
            rm -rf "$tray_dir"
        else
            echo "Keeping system tray components"
        fi
    fi
}

# Main uninstallation process
main() {
    echo "Uninstalling Toggleman..."

    # Check if running with sudo
    check_sudo

    # Stop running instances
    stop_instances

    # Remove application files
    remove_files

    # Handle user configuration
    handle_config

    # Clean up toggle scripts
    clean_toggle_scripts

    # Clean up system tray components
    clean_tray_components

    echo -e "${GREEN}Toggleman has been uninstalled.${NC}"
}

# Run main function
main