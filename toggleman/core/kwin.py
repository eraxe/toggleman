"""
KWin integration for Toggleman.

This module handles integration with KDE's window manager (KWin),
including setting keyboard shortcuts and opening window rules.
"""

import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import dbus

from toggleman.core.debug import get_logger

logger = get_logger(__name__)


class KWinManager:
    """Manages integration with KWin."""

    def __init__(self, config_manager):
        """Initialize the KWin manager.

        Args:
            config_manager: The configuration manager instance
        """
        self.config_manager = config_manager

    def set_shortcut(self, script_name: str, shortcut: str) -> Tuple[bool, str]:
        """Set a KWin keyboard shortcut for a toggle script.

        Args:
            script_name: The name of the toggle script
            shortcut: The shortcut key sequence (e.g., "Meta+Alt+C")

        Returns:
            Tuple of (success, message)
        """
        # Check if script exists
        script_config = self.config_manager.get_script(script_name)
        if not script_config:
            return False, f"Toggle script '{script_name}' not found"

        # Get script path
        script_path = script_config.get("script_path", "")
        if not script_path or not os.path.exists(script_path):
            return False, f"Script file not found at {script_path}"

        # Create shortcut name
        shortcut_name = f"Toggle {script_name}"
        command_string = script_path

        try:
            # Check if we have DBus connection
            bus = dbus.SessionBus()
            kwin = bus.get_object("org.kde.kglobalaccel", "/kglobalaccel")
            kglobalaccel = dbus.Interface(kwin, "org.kde.KGlobalAccel")

            # First, check if the shortcut already exists and remove it
            self._remove_shortcut(shortcut_name)

            # Create the shortcut using kwriteconfig5
            self._create_shortcut_with_kwriteconfig(shortcut_name, command_string, shortcut)

            # Update the script configuration
            script_config["kwin_shortcut"] = shortcut
            self.config_manager.save_script(script_name, script_config)

            return True, f"Set shortcut '{shortcut}' for toggle script '{script_name}'"

        except Exception as e:
            logger.error(f"Error setting shortcut for {script_name}: {e}")
            return False, f"Error setting shortcut: {str(e)}"

    def remove_shortcut(self, script_name: str) -> Tuple[bool, str]:
        """Remove a KWin keyboard shortcut for a toggle script.

        Args:
            script_name: The name of the toggle script

        Returns:
            Tuple of (success, message)
        """
        # Check if script exists
        script_config = self.config_manager.get_script(script_name)
        if not script_config:
            return False, f"Toggle script '{script_name}' not found"

        # Create shortcut name
        shortcut_name = f"Toggle {script_name}"

        try:
            # Remove the shortcut
            self._remove_shortcut(shortcut_name)

            # Update the script configuration
            if "kwin_shortcut" in script_config:
                del script_config["kwin_shortcut"]

            self.config_manager.save_script(script_name, script_config)

            return True, f"Removed shortcut for toggle script '{script_name}'"

        except Exception as e:
            logger.error(f"Error removing shortcut for {script_name}: {e}")
            return False, f"Error removing shortcut: {str(e)}"

    def get_shortcuts(self) -> Dict[str, str]:
        """Get all KWin keyboard shortcuts set for toggle scripts.

        Returns:
            Dictionary mapping script names to shortcuts
        """
        shortcuts = {}

        # Get all script configurations
        scripts = self.config_manager.get_all_scripts()

        for name, config in scripts.items():
            shortcut = config.get("kwin_shortcut", "")
            if shortcut:
                shortcuts[name] = shortcut

        return shortcuts

    def open_window_rules(self, script_name: str) -> Tuple[bool, str]:
        """Open KWin window rules editor for a toggle script.

        Args:
            script_name: The name of the toggle script

        Returns:
            Tuple of (success, message)
        """
        # Check if script exists
        script_config = self.config_manager.get_script(script_name)
        if not script_config:
            return False, f"Toggle script '{script_name}' not found"

        # Get window class
        window_class = script_config.get("window_class", "")
        if not window_class:
            return False, "Window class not defined in script configuration"

        try:
            # Launch KWin window rules with capture first
            window_capture_cmd = ["kcmshell5", "kwinrules"]
            capture_process = subprocess.Popen(window_capture_cmd)

            # Wait a bit for the dialog to open
            time.sleep(2)

            # TODO: Find a more reliable way to pre-fill the window class
            # Currently, this opens the window rules dialog, but doesn't pre-fill the window class

            return True, f"Opened window rules editor for '{script_name}'"

        except Exception as e:
            logger.error(f"Error opening window rules for {script_name}: {e}")
            return False, f"Error opening window rules: {str(e)}"

    def _create_shortcut_with_kwriteconfig(self, shortcut_name: str, command: str, keys: str) -> None:
        """Create a custom shortcut using kwriteconfig5.

        Args:
            shortcut_name: The name of the shortcut
            command: The command to execute
            keys: The shortcut key sequence
        """
        # Sanitize shortcut name for config
        config_name = shortcut_name.replace(" ", "_").lower()

        # Use kwriteconfig5 to set shortcut
        subprocess.run(
            ["kwriteconfig5", "--file", "khotkeysrc", "--group", "Data_1", "--key", "Comment", "Toggleman Shortcuts"])
        subprocess.run(["kwriteconfig5", "--file", "khotkeysrc", "--group", "Data_1", "--key", "Enabled", "true"])
        subprocess.run(
            ["kwriteconfig5", "--file", "khotkeysrc", "--group", "Data_1", "--key", "Name", "Toggleman Shortcuts"])
        subprocess.run(["kwriteconfig5", "--file", "khotkeysrc", "--group", "Data_1", "--key", "Type", "GENERIC"])

        # Create new group for the shortcut
        subprocess.run(["kwriteconfig5", "--file", "khotkeysrc", "--group", f"Data_1_{config_name}", "--key", "Comment",
                        shortcut_name])
        subprocess.run(
            ["kwriteconfig5", "--file", "khotkeysrc", "--group", f"Data_1_{config_name}", "--key", "Enabled", "true"])
        subprocess.run(["kwriteconfig5", "--file", "khotkeysrc", "--group", f"Data_1_{config_name}", "--key", "Name",
                        shortcut_name])
        subprocess.run(["kwriteconfig5", "--file", "khotkeysrc", "--group", f"Data_1_{config_name}", "--key", "Type",
                        "SIMPLE_ACTION_DATA"])

        # Set the actual shortcut
        subprocess.run(["kwriteconfig5", "--file", "khotkeysrc", "--group", f"Data_1_{config_name}Actions", "--key",
                        "ActionsCount", "1"])
        subprocess.run(
            ["kwriteconfig5", "--file", "khotkeysrc", "--group", f"Data_1_{config_name}Actions0", "--key", "CommandURL",
             command])
        subprocess.run(
            ["kwriteconfig5", "--file", "khotkeysrc", "--group", f"Data_1_{config_name}Actions0", "--key", "Type",
             "COMMAND_URL"])

        # Set the trigger
        subprocess.run(
            ["kwriteconfig5", "--file", "khotkeysrc", "--group", f"Data_1_{config_name}Triggers", "--key", "Comment",
             "Simple_action"])
        subprocess.run(["kwriteconfig5", "--file", "khotkeysrc", "--group", f"Data_1_{config_name}Triggers", "--key",
                        "TriggersCount", "1"])
        subprocess.run(
            ["kwriteconfig5", "--file", "khotkeysrc", "--group", f"Data_1_{config_name}Triggers0", "--key", "Key",
             keys])
        subprocess.run(
            ["kwriteconfig5", "--file", "khotkeysrc", "--group", f"Data_1_{config_name}Triggers0", "--key", "Type",
             "SHORTCUT"])

        # Force reload of shortcuts
        subprocess.run(["kquitapp5", "kglobalaccel"])
        time.sleep(1)  # Wait for process to terminate
        subprocess.run(["kglobalaccel5"])

    def _remove_shortcut(self, shortcut_name: str) -> None:
        """Remove a custom shortcut.

        Args:
            shortcut_name: The name of the shortcut
        """
        # Sanitize shortcut name for config
        config_name = shortcut_name.replace(" ", "_").lower()

        # Use kwriteconfig5 to remove the shortcut
        subprocess.run(
            ["kwriteconfig5", "--file", "khotkeysrc", "--group", f"Data_1_{config_name}", "--key", "Enabled", "false"])

        # Force reload of shortcuts
        subprocess.run(["kquitapp5", "kglobalaccel"])
        time.sleep(1)  # Wait for process to terminate
        subprocess.run(["kglobalaccel5"])