"""
Toggle script generator for Toggleman.

This module handles generating toggle scripts based on templates and user configuration.
"""

import os
import stat
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from string import Template

from toggleman.core.debug import get_logger

logger = get_logger(__name__)


class ScriptGenerator:
    """Generates toggle scripts from templates and configuration."""

    def __init__(self, config_manager):
        """Initialize the script generator.

        Args:
            config_manager: The configuration manager instance
        """
        self.config_manager = config_manager
        self.template_dir = Path("/usr/share/toggleman/templates")

        # Use fallback template path if system template dir doesn't exist
        if not self.template_dir.exists():
            self.template_dir = Path(__file__).parent.parent.parent / "data" / "templates"

        self.template_file = self.template_dir / "toggle_template.sh"

    def generate_script(self, script_name: str) -> Tuple[bool, str]:
        """Generate a toggle script from the configuration.

        Args:
            script_name: The name of the script configuration to use

        Returns:
            Tuple of (success, message)
        """
        # Get script configuration
        script_config = self.config_manager.get_script(script_name)
        if not script_config:
            return False, f"Script configuration '{script_name}' not found"

        # Load template
        try:
            if not self.template_file.exists():
                return False, f"Template file not found at {self.template_file}"

            with open(self.template_file, 'r') as f:
                template_content = f.read()

            # Get home directory
            home_dir = os.path.expanduser("~")

            # Prepare substitution variables with safe defaults
            script_vars = {
                # Required variables with defaults to avoid template errors
                "APP_COMMAND": script_config.get("app_command", ""),
                "APP_PROCESS": script_config.get("app_process", ""),
                "WINDOW_CLASS": script_config.get("window_class", ""),
                "CHROME_EXEC": script_config.get("chrome_exec", ""),
                "CHROME_PROFILE": script_config.get("chrome_profile", "Default"),
                "APP_ID": script_config.get("app_id", ""),
                "TRAY_ICON_PATH": script_config.get("icon_path", ""),
                "TRAY_NAME": script_config.get("tray_name", f"{script_name} Toggle"),
                "DEBUG": "true" if script_config.get("debug", False) else "false",
                "NOTIFICATIONS": "true" if script_config.get("notifications", True) else "false",
                "HOME": home_dir,
                "TRAY_ICON_DIR": f"{home_dir}/.cache/toggle_app"
            }

            # Create template with safe_substitute to avoid errors with missing placeholders
            template = Template(template_content)
            script_content = template.safe_substitute(script_vars)

            # Determine script path
            script_path = script_config.get("script_path", "")
            if not script_path:
                default_dir = self.config_manager.get_setting("general", "default_script_dir",
                                                              str(Path.home() / ".local/bin"))
                script_path = os.path.join(default_dir, f"toggle-{script_name.lower()}.sh")

            # Ensure directory exists
            script_dir = os.path.dirname(script_path)
            os.makedirs(script_dir, exist_ok=True)

            # Write script file
            with open(script_path, 'w') as f:
                f.write(script_content)

            # Make script executable
            os.chmod(script_path, os.stat(script_path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

            # Update script path in configuration
            script_config["script_path"] = script_path
            self.config_manager.save_script(script_name, script_config)

            return True, f"Successfully generated script at {script_path}"

        except Exception as e:
            logger.error(f"Error generating script for {script_name}: {e}")
            return False, f"Error generating script: {str(e)}"

    def delete_script(self, script_name: str) -> Tuple[bool, str]:
        """Delete a toggle script.

        Args:
            script_name: The name of the script to delete

        Returns:
            Tuple of (success, message)
        """
        # Get script configuration
        script_config = self.config_manager.get_script(script_name)
        if not script_config:
            return False, f"Script configuration '{script_name}' not found"

        # Get script path
        script_path = script_config.get("script_path", "")
        if not script_path or not os.path.exists(script_path):
            # Just delete the configuration if script doesn't exist
            self.config_manager.delete_script(script_name)
            return True, f"Deleted script configuration for {script_name}"

        # Delete the script file
        try:
            os.remove(script_path)
            self.config_manager.delete_script(script_name)
            return True, f"Deleted script {script_path} and its configuration"
        except Exception as e:
            logger.error(f"Error deleting script {script_path}: {e}")
            return False, f"Error deleting script: {str(e)}"

    def install_template(self, template_path: Optional[str] = None) -> Tuple[bool, str]:
        """Install a toggle script template.

        Args:
            template_path: Optional path to a custom template file

        Returns:
            Tuple of (success, message)
        """
        try:
            # Create template directory if it doesn't exist
            os.makedirs(os.path.dirname(self.template_file), exist_ok=True)

            if template_path and os.path.exists(template_path):
                # Copy custom template
                shutil.copy2(template_path, self.template_file)
                return True, f"Installed custom template from {template_path}"
            else:
                # Install default template
                default_template = self._get_default_template()

                with open(self.template_file, 'w') as f:
                    f.write(default_template)

                return True, "Installed default template"

        except Exception as e:
            logger.error(f"Error installing template: {e}")
            return False, f"Error installing template: {str(e)}"

    def _get_default_template(self) -> str:
        """Get the default toggle script template."""
        return '''#!/bin/bash
# Generated Toggle Script by Toggleman
# Do not edit directly - use Toggleman to modify this script

# Error handling
set -o pipefail
trap 'echo "Error on line $LINENO"; exit 1' ERR

# Configuration
readonly APP_COMMAND="${APP_COMMAND}"
readonly APP_PROCESS="${APP_PROCESS}"
readonly WINDOW_CLASS="${WINDOW_CLASS}"
readonly CHROME_EXEC="${CHROME_EXEC}"
readonly CHROME_PROFILE="${CHROME_PROFILE:-Default}"
readonly APP_ID="${APP_ID}"
readonly TRAY_ICON_PATH="${TRAY_ICON_PATH}"
readonly TRAY_NAME="${TRAY_NAME}"
readonly TRAY_ICON_DIR="${TRAY_ICON_DIR:-$HOME/.cache/toggle_app}"

# Debug settings
DEBUG="${DEBUG:-false}"
NOTIFICATIONS="${NOTIFICATIONS:-true}"

# Error codes
readonly E_GENERAL=1
readonly E_DEPS_MISSING=2
readonly E_APP_LAUNCH=3

# Make sure the cache directory exists
mkdir -p "$TRAY_ICON_DIR" 2>/dev/null || {
    echo "Warning: Could not create cache directory $TRAY_ICON_DIR"
}

# Function for debug logging
log_debug() {
    if [ "$DEBUG" == "true" ]; then
        echo "[DEBUG] $1"
    fi
}

# Check for required dependencies
check_dependencies() {
    local missing_deps=()

    if ! command -v qdbus &>/dev/null; then
        missing_deps+=("qdbus")
    fi

    # For X11 sessions, check for xdotool
    if [ "$XDG_SESSION_TYPE" = "x11" ] && ! command -v xdotool &>/dev/null; then
        log_debug "xdotool not found but might be useful on X11 sessions"
    fi

    if [ ${#missing_deps[@]} -gt 0 ]; then
        echo "Error: Missing required dependencies: ${missing_deps[*]}"
        echo "Please install them with: sudo pacman -S ${missing_deps[*]}"
        exit $E_DEPS_MISSING
    fi
    
    log_debug "All dependencies satisfied"
}

# Function to find all windows matching our target class
find_windows() {
    log_debug "Searching for windows with class: $WINDOW_CLASS"

    local matching_windows=""
    
    # Determine window management system
    if [ "$XDG_SESSION_TYPE" = "wayland" ] || command -v qdbus &>/dev/null; then
        log_debug "Using KWin/Wayland method for window detection"
        
        # Try KDE-specific method first (for Wayland)
        if qdbus org.kde.KWin /KWin &>/dev/null; then
            local window_list
            window_list=$(qdbus org.kde.KWin /KWin org.kde.KWin.getWindowList 2>/dev/null)

            for win_id in $window_list; do
                local win_class
                win_class=$(qdbus org.kde.KWin /KWin org.kde.KWin.getWindowInfo "$win_id" | grep "resourceClass" | cut -d '"' -f 2)

                if [[ "$win_class" == "$WINDOW_CLASS" ]]; then
                    matching_windows="$matching_windows $win_id"
                    log_debug "Found matching window ID: $win_id with class $win_class"
                fi
            done
        else
            log_debug "KWin DBus interface not available"
        fi
    fi

    # Fallback to X11 method if no windows found and xdotool is available
    if [ -z "$matching_windows" ] && command -v xdotool &>/dev/null; then
        log_debug "No windows found with KDE method, trying xdotool..."
        matching_windows=$(xdotool search --class "$WINDOW_CLASS" 2>/dev/null)

        # If still not found, try a more flexible approach
        if [ -z "$matching_windows" ]; then
            log_debug "Trying more flexible xdotool approach..."
            matching_windows=$(xdotool search --name ".*" 2>/dev/null | \
                          xargs -I{} sh -c "xprop -id {} WM_CLASS 2>/dev/null | grep -i \"$WINDOW_CLASS\" > /dev/null && echo {}" || echo "")
        fi
    fi

    # For Chrome apps on Wayland, try a more aggressive approach
    if [ -z "$matching_windows" ] && [ -n "$APP_ID" ] && [ "$XDG_SESSION_TYPE" = "wayland" ]; then
        log_debug "Trying special Chrome app detection method for Wayland..."
        for win_id in $(qdbus org.kde.KWin /KWin org.kde.KWin.getWindowList 2>/dev/null); do
            local win_class win_title
            win_class=$(qdbus org.kde.KWin /KWin org.kde.KWin.getWindowInfo "$win_id" | grep "resourceClass" | cut -d '"' -f 2)
            win_title=$(qdbus org.kde.KWin /KWin org.kde.KWin.getWindowInfo "$win_id" | grep "caption" | cut -d '"' -f 2)
            
            # Check for Chrome or Chrome app
            if [[ "$win_class" == *"chrome"* ]] || [[ "$win_class" == *"crx"* ]]; then
                matching_windows="$matching_windows $win_id"
                log_debug "Found potential Chrome app window: $win_id, class=$win_class, title=$win_title"
            fi
        done
    fi

    echo "$matching_windows"
}

# Function to check if a window is minimized/iconified
is_minimized() {
    local win_id=$1

    # Try KDE-specific method first (works on Wayland)
    if qdbus org.kde.KWin /KWin &>/dev/null; then
        local kde_state
        kde_state=$(qdbus org.kde.KWin /KWin org.kde.KWin.isMinimized "$win_id" 2>/dev/null)

        if [ "$kde_state" = "true" ]; then
            log_debug "Window $win_id is minimized (KDE method)"
            return 0  # Window is minimized
        fi
    fi

    # Fallback to X11 method if KDE method failed and xprop is available
    if command -v xprop &>/dev/null; then
        local state_info
        state_info=$(xprop -id "$win_id" 2>/dev/null)

        if echo "$state_info" | grep -q "window state: Iconic" || \
           echo "$state_info" | grep -q "_NET_WM_STATE_HIDDEN"; then
            log_debug "Window $win_id is minimized (X11 method)"
            return 0  # Window is minimized
        fi
    fi

    log_debug "Window $win_id is not minimized"
    return 1  # Window is not minimized
}

# Function to activate a window
activate_window() {
    local win_id=$1

    log_debug "Activating window $win_id"

    # Try KDE-specific method first (for Wayland)
    if qdbus org.kde.KWin /KWin &>/dev/null; then
        qdbus org.kde.KWin /KWin org.kde.KWin.unminimizeWindow "$win_id" 2>/dev/null
        qdbus org.kde.KWin /KWin org.kde.KWin.forceActiveWindow "$win_id" 2>/dev/null
    fi

    # Fallback to X11 method if xdotool is available
    if command -v xdotool &>/dev/null; then
        log_debug "Using xdotool fallback for window activation"
        xdotool windowmap "$win_id" 2>/dev/null
        xdotool windowactivate "$win_id" 2>/dev/null
    fi
}

# Function to minimize a window
minimize_window() {
    local win_id=$1

    log_debug "Minimizing window $win_id"

    # Try KDE-specific method first (for Wayland)
    if qdbus org.kde.KWin /KWin &>/dev/null; then
        qdbus org.kde.KWin /KWin org.kde.KWin.minimizeWindow "$win_id" 2>/dev/null
    fi

    # Fallback to X11 method if xdotool is available
    if command -v xdotool &>/dev/null; then
        log_debug "Using xdotool fallback for window minimization"
        xdotool windowminimize "$win_id" 2>/dev/null
    fi
}

# Function to check if app is running
is_app_running() {
    local pids
    pids=$(pgrep -f "$APP_PROCESS" 2>/dev/null || echo "")

    if [ -n "$pids" ]; then
        log_debug "App is running with PIDs: $pids"
        return 0  # App is running
    else
        log_debug "App is not running"
        return 1  # App is not running
    fi
}

# Function to check if a process is still starting up
is_starting_up() {
    local pids
    pids=$(pgrep -f "$APP_PROCESS" 2>/dev/null || echo "")

    if [ -n "$pids" ]; then
        for pid in $pids; do
            if [ -n "$pid" ] && [ "$pid" -gt 0 ]; then
                local start_time
                start_time=$(ps -o etimes= -p "$pid" 2>/dev/null || echo "999")

                if [ "$start_time" -lt 5 ]; then
                    log_debug "App is starting up (PID $pid, started $start_time seconds ago)"
                    return 0  # True, it's starting up
                fi
            fi
        done
    fi

    log_debug "App is not in startup phase"
    return 1  # False, not starting up
}

# Get icon for the tray if not specified
get_app_icon() {
    local icon_path="$TRAY_ICON_PATH"

    # If icon path is not set, try to extract from chrome app
    if [ -z "$icon_path" ]; then
        log_debug "No icon path specified, looking for suitable icon"

        # Create cache directory if it doesn't exist
        mkdir -p "$TRAY_ICON_DIR" 2>/dev/null || {
            log_debug "Could not create cache directory $TRAY_ICON_DIR"
        }

        # Look for the icon in Chrome's app data if this is a Chrome app
        if [ -n "$APP_ID" ] && [ -n "$CHROME_PROFILE" ]; then
            local chrome_app_dir="$HOME/.config/google-chrome/$CHROME_PROFILE/Web Applications"

            if [ -d "$chrome_app_dir" ]; then
                # Try to find the icon file
                local found_icon
                found_icon=$(find "$chrome_app_dir" -path "*$APP_ID*" -name "*.png" 2>/dev/null | sort -r | head -n 1)

                if [ -n "$found_icon" ]; then
                    # Copy the icon to our cache directory
                    local icon_name
                    icon_name=$(basename "$found_icon")
                    if cp "$found_icon" "$TRAY_ICON_DIR/$icon_name" 2>/dev/null; then
                        icon_path="$TRAY_ICON_DIR/$icon_name"
                        log_debug "Found and using Chrome app icon: $icon_path"
                    fi
                fi
            else
                log_debug "Chrome app directory not found at $chrome_app_dir"
            fi
        fi

        # If still no icon, use a default one
        if [ -z "$icon_path" ]; then
            icon_path="internet-web-browser"  # Use a system icon
            log_debug "Using default system icon: $icon_path"
        fi
    else
        log_debug "Using specified icon: $icon_path"
    fi

    echo "$icon_path"
}

# Function to show notification
show_notification() {
    if [ "$NOTIFICATIONS" != "true" ]; then
        return
    fi

    local message=$1
    local icon_path
    icon_path=$(get_app_icon)

    log_debug "Showing notification: $message"

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

    log_debug "Applying window properties to window $win_id"

    # Force apply window rules using KWin
    if qdbus org.kde.KWin /KWin &>/dev/null; then
        qdbus org.kde.KWin /KWin org.kde.KWin.setMaximize "$win_id" true true 2>/dev/null
    
        # Try to apply X11 properties if running on X11
        if [ "$XDG_SESSION_TYPE" = "x11" ] && command -v xprop &>/dev/null; then
            log_debug "Applying X11 window properties"
            # Apply the "skip taskbar" property
            xprop -id "$win_id" -f _NET_WM_STATE 32a -set _NET_WM_STATE _NET_WM_STATE_SKIP_TASKBAR 2>/dev/null
        fi
    
        # Reconfigure KWin to ensure rules are applied
        qdbus org.kde.KWin /KWin org.kde.KWin.reconfigure 2>/dev/null
    else
        log_debug "KWin DBus interface not available, skipping window property application"
    fi
}

# Main function
main() {
    log_debug "Starting toggle script"

    # Check for required dependencies
    check_dependencies

    # Find app windows
    local window_ids
    window_ids=($(find_windows))
    log_debug "Found ${#window_ids[@]} window(s)"

    # If app is running, toggle window state
    if is_app_running; then
        # If we found windows matching our class
        if [ ${#window_ids[@]} -gt 0 ]; then
            # Check if app is just starting
            if is_starting_up; then
                log_debug "App is starting, waiting..."
                show_notification "App is starting..."
                sleep 3

                # Refresh window list
                window_ids=($(find_windows))
                log_debug "Refreshed window list, found ${#window_ids[@]} window(s)"

                # Get the first window only
                local win_id=${window_ids[0]}
                activate_window "$win_id"

                # Kill any duplicate windows
                if [ ${#window_ids[@]} -gt 1 ]; then
                    log_debug "Found duplicate windows, closing extras"
                    for (( i=1; i<${#window_ids[@]}; i++ )); do
                        if command -v xdotool &>/dev/null; then
                            xdotool windowclose "${window_ids[$i]}" 2>/dev/null
                            log_debug "Closed duplicate window: ${window_ids[$i]}"
                        fi
                    done
                fi

                apply_window_properties "$win_id"
                show_notification "Application is now active"
                exit 0
            fi

            # Get the first window and toggle its state
            local win_id=${window_ids[0]}

            # Close any duplicate windows
            if [ ${#window_ids[@]} -gt 1 ]; then
                log_debug "Found duplicate windows, closing extras"
                for (( i=1; i<${#window_ids[@]}; i++ )); do
                    if command -v xdotool &>/dev/null; then
                        xdotool windowclose "${window_ids[$i]}" 2>/dev/null
                        log_debug "Closed duplicate window: ${window_ids[$i]}"
                    fi
                done
            fi

            if is_minimized "$win_id"; then
                log_debug "Restoring window..."
                activate_window "$win_id"
                show_notification "Restoring application"
            else
                log_debug "Minimizing window..."
                minimize_window "$win_id"
                show_notification "Application minimized"
            fi

            # Apply window properties
            apply_window_properties "$win_id"
        else
            # No windows found but process is running
            log_debug "No windows found but process is running, launching app..."
            show_notification "Launching application..."

            # Choose launch method based on configuration
            if [ -n "$CHROME_EXEC" ] && [ -n "$APP_ID" ]; then
                log_debug "Launching as Chrome app"
                "$CHROME_EXEC" --profile-directory="$CHROME_PROFILE" --app-id="$APP_ID" &
            else
                log_debug "Launching with APP_COMMAND"
                eval "$APP_COMMAND" &
            fi

            if [ $? -ne 0 ]; then
                log_debug "Failed to launch app"
                show_notification "Error: Failed to launch application"
                exit $E_APP_LAUNCH
            fi

            # Wait for window to appear
            log_debug "Waiting for window to appear..."
            sleep 3
            window_ids=($(find_windows))

            if [ ${#window_ids[@]} -gt 0 ]; then
                activate_window "${window_ids[0]}"
                apply_window_properties "${window_ids[0]}"
                show_notification "Application is now active"
            else
                log_debug "No windows found after launch!"
                show_notification "Warning: Application window not found"
            fi
        fi
    else
        # App is not running at all, so launch it
        log_debug "App is not running, launching..."
        show_notification "Launching application..."

        # Choose launch method based on configuration
        if [ -n "$CHROME_EXEC" ] && [ -n "$APP_ID" ]; then
            log_debug "Launching as Chrome app"
            "$CHROME_EXEC" --profile-directory="$CHROME_PROFILE" --app-id="$APP_ID" &
        else
            log_debug "Launching with APP_COMMAND"
            eval "$APP_COMMAND" &
        fi

        if [ $? -ne 0 ]; then
            log_debug "Failed to launch app"
            show_notification "Error: Failed to launch application"
            exit $E_APP_LAUNCH
        fi

        # Wait for app to start and capture window
        log_debug "Waiting for window to appear..."
        sleep 3
        window_ids=($(find_windows))

        # If window found after starting, make sure it's activated
        if [ ${#window_ids[@]} -gt 0 ]; then
            activate_window "${window_ids[0]}"
            apply_window_properties "${window_ids[0]}"
            show_notification "Application is now active"
        else
            log_debug "No windows found after launching app!"
            show_notification "Warning: Application window not found"
        fi
    fi

    exit 0
}

# Run the main function
main
'''