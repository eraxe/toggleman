#!/bin/bash
# Enhanced Chrome App Toggler for KDE Wayland
# Usage: ./toggle_app.sh
# Configuration - Edit these variables as needed
readonly APP_COMMAND="/opt/google/chrome/google-chrome.*--app-id=fmpnliohjhemenmnlpbfagaolkdacoja"
readonly APP_PROCESS="chrome.*--app-id=fmpnliohjhemenmnlpbfagaolkdacoja"
readonly WINDOW_CLASS="crx_fmpnliohjhemenmnlpbfagaolkdacoja"
readonly CHROME_EXEC="/opt/google/chrome/google-chrome"
readonly CHROME_PROFILE="Default"
readonly APP_ID="fmpnliohjhemenmnlpbfagaolkdacoja"
# Tray icon configuration - Set the path to the icon file or leave empty for auto-detection
TRAY_ICON_PATH="/home/katana/.local/share/icons/arash/0-other/claude-ai-icon.png"  # Set a custom path here if desired (e.g., "/path/to/icon.png")
readonly TRAY_NAME="Chrome App Toggle"
readonly TRAY_ICON_DIR="$HOME/.cache/toggle_app"
# Error codes
readonly E_GENERAL=1
readonly E_DEPS_MISSING=2
readonly E_APP_LAUNCH=3

# Make sure the cache directory exists
mkdir -p "$TRAY_ICON_DIR"

# Check for required dependencies
check_dependencies() {
    local missing_deps=()
    
    if ! command -v qdbus &>/dev/null; then
        missing_deps+=("qdbus")
    fi
    
    # Don't check for plasma-browser-integration anymore - we're using notifications instead
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        echo "Error: Missing required dependencies: ${missing_deps[*]}"
        echo "Please install them with: sudo pacman -S ${missing_deps[*]}"
        exit $E_DEPS_MISSING
    fi
}

# Function to find all windows matching our target class
find_windows() {
    # Try KDE-specific method first (for Wayland)
    local window_list
    window_list=$(qdbus org.kde.KWin /KWin org.kde.KWin.getWindowList 2>/dev/null)
    
    local matching_windows=""
    
    for win_id in $window_list; do
        local win_class
        win_class=$(qdbus org.kde.KWin /KWin org.kde.KWin.getWindowInfo "$win_id" | grep "resourceClass" | cut -d '"' -f 2)
        
        if [[ "$win_class" == "$WINDOW_CLASS" ]]; then
            matching_windows="$matching_windows $win_id"
        fi
    done
    
    # Fallback to X11 method if no windows found and xdotool is available
    if [ -z "$matching_windows" ] && command -v xdotool &>/dev/null; then
        matching_windows=$(xdotool search --class "$WINDOW_CLASS" 2>/dev/null)
        
        # If still not found, try a more flexible approach
        if [ -z "$matching_windows" ]; then
            matching_windows=$(xdotool search --name ".*" 2>/dev/null | \
                          xargs -I{} sh -c "xprop -id {} WM_CLASS 2>/dev/null | grep -i \"$WINDOW_CLASS\" > /dev/null && echo {}" || echo "")
        fi
    fi
    
    echo "$matching_windows"
}

# Function to check if a window is minimized/iconified
is_minimized() {
    local win_id=$1
    
    # Try KDE-specific method first (works on Wayland)
    local kde_state
    kde_state=$(qdbus org.kde.KWin /KWin org.kde.KWin.isMinimized "$win_id" 2>/dev/null)
    
    if [ "$kde_state" = "true" ]; then
        return 0  # Window is minimized
    fi
    
    # Fallback to X11 method if KDE method failed and xprop is available
    if command -v xprop &>/dev/null; then
        local state_info
        state_info=$(xprop -id "$win_id" 2>/dev/null)
        
        if echo "$state_info" | grep -q "window state: Iconic" || \
           echo "$state_info" | grep -q "_NET_WM_STATE_HIDDEN"; then
            return 0  # Window is minimized
        fi
    fi
    
    return 1  # Window is not minimized
}

# Function to activate a window
activate_window() {
    local win_id=$1
    
    # Try KDE-specific method first (for Wayland)
    qdbus org.kde.KWin /KWin org.kde.KWin.unminimizeWindow "$win_id" 2>/dev/null
    qdbus org.kde.KWin /KWin org.kde.KWin.forceActiveWindow "$win_id" 2>/dev/null
    
    # Fallback to X11 method if xdotool is available
    if command -v xdotool &>/dev/null; then
        xdotool windowmap "$win_id" 2>/dev/null
        xdotool windowactivate "$win_id" 2>/dev/null
    fi
}

# Function to minimize a window
minimize_window() {
    local win_id=$1
    
    # Try KDE-specific method first (for Wayland)
    qdbus org.kde.KWin /KWin org.kde.KWin.minimizeWindow "$win_id" 2>/dev/null
    
    # Fallback to X11 method if xdotool is available
    if command -v xdotool &>/dev/null; then
        xdotool windowminimize "$win_id" 2>/dev/null
    fi
}

# Function to check if app is running
is_app_running() {
    local pids
    pids=$(pgrep -f "$APP_PROCESS")
    
    if [ -n "$pids" ]; then
        return 0  # App is running
    else
        return 1  # App is not running
    fi
}

# Function to check if a process is still starting up
is_starting_up() {
    local pids
    pids=$(pgrep -f "$APP_PROCESS")
    
    if [ -n "$pids" ]; then
        for pid in $pids; do
            local start_time
            start_time=$(ps -o etimes= -p "$pid")
            
            if [ "$start_time" -lt 5 ]; then
                return 0  # True, it's starting up
            fi
        done
    fi
    
    return 1  # False, not starting up
}

# Get icon for the tray if not specified
get_app_icon() {
    local icon_path="$TRAY_ICON_PATH"
    
    # If icon path is not set, try to extract from chrome app
    if [ -z "$icon_path" ]; then
        # Create cache directory if it doesn't exist
        mkdir -p "$TRAY_ICON_DIR"
        
        # Look for the icon in Chrome's app data
        local chrome_app_dir="$HOME/.config/google-chrome/Default/Web Applications"
        
        # Try to find the icon file
        local found_icon
        found_icon=$(find "$chrome_app_dir" -path "*$APP_ID*" -name "*.png" | sort -r | head -n 1)
        
        if [ -n "$found_icon" ]; then
            # Copy the icon to our cache directory
            local icon_name
            icon_name=$(basename "$found_icon")
            cp "$found_icon" "$TRAY_ICON_DIR/$icon_name"
            icon_path="$TRAY_ICON_DIR/$icon_name"
        else
            # Use a default icon if not found
            icon_path="internet-web-browser"  # Use a system icon
        fi
    fi
    
    echo "$icon_path"
}

# Function to create/handle system tray icon
setup_tray_icon() {
    local icon_path
    icon_path=$(get_app_icon)
    
    # Check if we should create a simple Python-based tray script
    if [ ! -f "$TRAY_ICON_DIR/tray_icon.py" ]; then
        # Create a simple PyQt5 tray icon script
        cat > "$TRAY_ICON_DIR/tray_icon.py" << 'EOL'
#!/usr/bin/env python3
import sys
import os
import signal
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QProcess

# Get parameters
if len(sys.argv) < 2:
    print("Usage: tray_icon.py [icon_path] [script_path]")
    sys.exit(1)

icon_path = sys.argv[1]
script_path = sys.argv[2] if len(sys.argv) > 2 else None

# Create application
app = QApplication([])
app.setQuitOnLastWindowClosed(False)

# Create the icon
icon = QIcon(icon_path)

# Create the tray
tray = QSystemTrayIcon()
tray.setIcon(icon)
tray.setVisible(True)

# Create the menu
menu = QMenu()

# Add a toggle action
toggle_action = QAction("Toggle Chrome Claude")
def toggle_app():
    if script_path:
        QProcess.startDetached(script_path, [])
toggle_action.triggered.connect(toggle_app)
menu.addAction(toggle_action)

# Add a quit action
quit_action = QAction("Quit")
def quit_app():
    tray.setVisible(False)
    app.quit()
quit_action.triggered.connect(quit_app)
menu.addAction(quit_action)

# Add the menu to the tray
tray.setContextMenu(menu)

# Handle left click as toggle
def activated(reason):
    if reason == QSystemTrayIcon.Trigger:  # Left click
        toggle_app()
tray.activated.connect(activated)

# Start the app
app.exec_()
EOL
        chmod +x "$TRAY_ICON_DIR/tray_icon.py"
    fi
    
    # Check if PyQt5 is installed
    if python3 -c "import PyQt5" 2>/dev/null; then
        # Check if tray icon is already running
        if pgrep -f "python.*tray_icon.py" >/dev/null; then
            # Already running
            return 0
        fi
        
        # Start the tray icon process
        python3 "$TRAY_ICON_DIR/tray_icon.py" "$icon_path" "$0" &
        local tray_pid=$!
        
        # Store the PID
        echo "$tray_pid" > "$TRAY_ICON_DIR/tray_pid"
        
        return 0
    else
        # PyQt5 not installed - fall back to notifications
        echo "Note: PyQt5 not installed. Install it for system tray icon support."
        echo "      sudo pacman -S python-pyqt5"
        return 1
    fi
}

# Function to show notification
show_notification() {
    local message=$1
    local icon_path
    icon_path=$(get_app_icon)
    
    # Use notify-send if available
    if command -v notify-send &>/dev/null; then
        notify-send -i "$icon_path" "$TRAY_NAME" "$message"
    # Fall back to kdialog passive popup
    elif command -v kdialog &>/dev/null; then
        kdialog --passivepopup "$message" 2 --title "$TRAY_NAME" --icon "$icon_path" &
    else
        echo "$message"
    fi
}

# Apply window properties for KDE
apply_window_properties() {
    local win_id=$1
    
    # Force apply window rules using KWin
    qdbus org.kde.KWin /KWin org.kde.KWin.setMaximize "$win_id" true true 2>/dev/null
    
    # Apply fullscreen if desired (comment out if not needed)
    # qdbus org.kde.KWin /KWin org.kde.KWin.setFullScreen "$win_id" true 2>/dev/null
    
    # Try to apply X11 properties if running on X11
    if [ "$XDG_SESSION_TYPE" = "x11" ] && command -v xprop &>/dev/null; then
        # Apply the "skip taskbar" property
        xprop -id "$win_id" -f _NET_WM_STATE 32a -set _NET_WM_STATE _NET_WM_STATE_SKIP_TASKBAR 2>/dev/null
    fi
    
    # Reconfigure KWin to ensure rules are applied
    qdbus org.kde.KWin /KWin org.kde.KWin.reconfigure 2>/dev/null
}

# Main function
main() {
    # Check for required dependencies
    check_dependencies
    
    # Setup tray icon
    setup_tray_icon
    
    # Find app windows
    local window_ids
    window_ids=($(find_windows))
    
    # If app is running, toggle window state
    if is_app_running; then
        # If we found windows matching our class
        if [ ${#window_ids[@]} -gt 0 ]; then
            # Check if app is just starting
            if is_starting_up; then
                echo "App is starting, waiting..."
                show_notification "App is starting..."
                sleep 3
                
                # Refresh window list
                window_ids=($(find_windows))
                
                # Get the first window only
                local win_id=${window_ids[0]}
                activate_window "$win_id"
                
                # Kill any duplicate windows
                if [ ${#window_ids[@]} -gt 1 ]; then
                    for (( i=1; i<${#window_ids[@]}; i++ )); do
                        if command -v xdotool &>/dev/null; then
                            xdotool windowclose "${window_ids[$i]}" 2>/dev/null
                        fi
                    done
                fi
                
                apply_window_properties "$win_id"
                show_notification "Claude is now active"
                exit 0
            fi
            
            # Get the first window and toggle its state
            local win_id=${window_ids[0]}
            
            # Close any duplicate windows
            if [ ${#window_ids[@]} -gt 1 ]; then
                for (( i=1; i<${#window_ids[@]}; i++ )); do
                    if command -v xdotool &>/dev/null; then
                        xdotool windowclose "${window_ids[$i]}" 2>/dev/null
                    fi
                done
            fi
            
            if is_minimized "$win_id"; then
                echo "Restoring window..."
                activate_window "$win_id"
                show_notification "Restoring Claude"
            else
                echo "Minimizing window..."
                minimize_window "$win_id"
                show_notification "Claude minimized"
            fi
            
            # Apply window properties
            apply_window_properties "$win_id"
        else
            # No windows found but process is running
            echo "Launching app..."
            show_notification "Launching Claude..."
            "$CHROME_EXEC" --profile-directory="$CHROME_PROFILE" --app-id="$APP_ID" &
            
            if [ $? -ne 0 ]; then
                echo "Error: Failed to launch app"
                show_notification "Error: Failed to launch Claude"
                exit $E_APP_LAUNCH
            fi
            
            # Wait for window to appear
            sleep 3
            window_ids=($(find_windows))
            
            if [ ${#window_ids[@]} -gt 0 ]; then
                activate_window "${window_ids[0]}"
                apply_window_properties "${window_ids[0]}"
                show_notification "Claude is now active"
            else
                echo "Warning: No windows found after launch!"
                show_notification "Warning: Claude window not found"
            fi
        fi
    else
        # App is not running at all, so launch it
        echo "Launching app..."
        show_notification "Launching Claude..."
        
        # Launch the app
        "$CHROME_EXEC" --profile-directory="$CHROME_PROFILE" --app-id="$APP_ID" &
        
        if [ $? -ne 0 ]; then
            echo "Error: Failed to launch app"
            show_notification "Error: Failed to launch Claude"
            exit $E_APP_LAUNCH
        fi
        
        # Wait for app to start and capture window
        sleep 3
        window_ids=($(find_windows))
        
        # If window found after starting, make sure it's activated
        if [ ${#window_ids[@]} -gt 0 ]; then
            activate_window "${window_ids[0]}"
            apply_window_properties "${window_ids[0]}"
            show_notification "Claude is now active"
        else
            echo "Warning: No windows found after launching app!"
            show_notification "Warning: Claude window not found"
        fi
    fi
    
    exit 0
}

# Run the main function
main