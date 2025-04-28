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
            # Method 1: Direct DBus method
            try:
                bus = dbus.SessionBus()
                kglobalaccel = bus.get_object("org.kde.kglobalaccel", "/kglobalaccel")
                kglobalaccel_iface = dbus.Interface(kglobalaccel, "org.kde.KGlobalAccel")

                # First, check if the shortcut already exists and remove it
                component = "toggleman"
                context = ""
                action_id = f"toggle_{script_name}"
                key_sequence = [shortcut]

                # This is the preferred Plasma 5 approach, check if it works
                try:
                    kglobalaccel_iface.setShortcut(component, action_id, key_sequence, context, {})
                    logger.info(f"Set shortcut via DBus: {shortcut} for {script_name}")

                    # Update the script configuration
                    script_config["kwin_shortcut"] = shortcut
                    self.config_manager.save_script(script_name, script_config)

                    return True, f"Set shortcut '{shortcut}' for toggle script '{script_name}'"
                except Exception as e:
                    logger.warning(f"DBus shortcut method failed: {e}, trying khotkeys method")
            except Exception as e:
                logger.warning(f"Could not connect to KGlobalAccel: {e}, trying khotkeys method")

            # Method 2: kwriteconfig method
            self._create_shortcut_with_kwriteconfig(shortcut_name, command_string, shortcut)

            # Update the script configuration
            script_config["kwin_shortcut"] = shortcut
            self.config_manager.save_script(script_name, script_config)

            # As a backup measure, also try to use qdbus
            try:
                subprocess.run([
                    "qdbus", "org.kde.kglobalaccel", "/kglobalaccel",
                    "org.kde.KGlobalAccel.setShortcut",
                    f"toggleman: {script_name}",
                    shortcut,
                    "default",
                    "default",
                    "toggle"
                ], check=False)
            except Exception:
                pass  # Ignore errors, this is just a backup method

            # Method 3: Try using khotkeys directly (more compatible with older KDE versions)
            try:
                script_cmd = f"sh -c '{script_path}'"
                subprocess.run([
                    "khotkeys", "--command", script_cmd,
                    "--shortcut", shortcut,
                    "--title", shortcut_name
                ], check=False)
            except Exception:
                pass  # Ignore errors, this is just a backup method

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
        config_name = shortcut_name.replace(" ", "_").lower()

        try:
            # Use kwriteconfig5 to disable the shortcut
            kwrite_cmd = "kwriteconfig5"
            if not self._is_command_available(kwrite_cmd):
                kwrite_cmd = "kwriteconfig"

            subprocess.run(
                [kwrite_cmd, "--file", "khotkeysrc", "--group", f"Data_1_{config_name}", "--key", "Enabled", "false"])

            # Try to use qdbus to remove shortcut as well
            try:
                bus = dbus.SessionBus()
                kglobalaccel = bus.get_object("org.kde.kglobalaccel", "/kglobalaccel")
                kglobalaccel_iface = dbus.Interface(kglobalaccel, "org.kde.KGlobalAccel")

                component = "toggleman"
                action_id = f"toggle_{script_name}"
                key_sequence = []  # Empty sequence to clear
                context = ""

                kglobalaccel_iface.setShortcut(component, action_id, key_sequence, context, {})
            except Exception:
                pass  # Ignore errors, this is just a backup method

            # Force reload of shortcuts
            subprocess.run(["kquitapp5", "kglobalaccel"], check=False)
            time.sleep(1)  # Wait for process to terminate
            subprocess.run(["kglobalaccel5"], check=False)

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
            # First check if kcmshell5 is available
            if self._is_command_available("kcmshell5"):
                # Launch KWin window rules with capture first
                window_capture_cmd = ["kcmshell5", "kwinrules"]
                capture_process = subprocess.Popen(window_capture_cmd)
            else:
                # Try the newer kcmshell6 on newer KDE versions
                window_capture_cmd = ["kcmshell6", "kwinrules"]
                capture_process = subprocess.Popen(window_capture_cmd)

            # Wait a bit for the dialog to open
            time.sleep(2)

            # Alternative method: use systemsettings
            if capture_process.poll() is not None:  # Process exited already
                # Try using systemsettings
                try:
                    subprocess.Popen(["systemsettings5", "kcm_kwinrules"])
                except Exception:
                    # Try newer systemsettings
                    try:
                        subprocess.Popen(["systemsettings", "kcm_kwinrules"])
                    except Exception as e:
                        logger.error(f"Error launching system settings: {e}")

            # Display a message to the user
            return True, f"Opened window rules editor. Please create a rule for window class: {window_class}"

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

        # Try to determine which kwriteconfig version to use
        kwrite_cmd = "kwriteconfig5"
        if not self._is_command_available(kwrite_cmd):
            kwrite_cmd = "kwriteconfig"

        # Find a unique index for this shortcut
        try:
            # Look for existing Data_X groups
            result = subprocess.run(
                ["grep", "-r", "Data_[0-9]", f"{os.path.expanduser('~')}/.config/khotkeysrc"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Parse output to find the highest index
            highest_index = 1
            if result.returncode == 0:
                import re
                indices = re.findall(r'Data_(\d+)', result.stdout)
                if indices:
                    highest_index = max(map(int, indices)) + 1
        except Exception:
            highest_index = 1

        data_group = f"Data_{highest_index}"
        action_group = f"{data_group}_{config_name}"

        # Use kwriteconfig to set shortcut
        subprocess.run([kwrite_cmd, "--file", "khotkeysrc", "--group", data_group, "--key", "Comment", "Toggleman Shortcuts"])
        subprocess.run([kwrite_cmd, "--file", "khotkeysrc", "--group", data_group, "--key", "Enabled", "true"])
        subprocess.run([kwrite_cmd, "--file", "khotkeysrc", "--group", data_group, "--key", "Name", "Toggleman Shortcuts"])
        subprocess.run([kwrite_cmd, "--file", "khotkeysrc", "--group", data_group, "--key", "Type", "GENERIC"])

        # Create new group for the shortcut
        subprocess.run([kwrite_cmd, "--file", "khotkeysrc", "--group", action_group, "--key", "Comment", shortcut_name])
        subprocess.run([kwrite_cmd, "--file", "khotkeysrc", "--group", action_group, "--key", "Enabled", "true"])
        subprocess.run([kwrite_cmd, "--file", "khotkeysrc", "--group", action_group, "--key", "Name", shortcut_name])
        subprocess.run([kwrite_cmd, "--file", "khotkeysrc", "--group", action_group, "--key", "Type", "SIMPLE_ACTION_DATA"])

        # Set the actual shortcut
        subprocess.run([kwrite_cmd, "--file", "khotkeysrc", "--group", f"{action_group}Actions", "--key", "ActionsCount", "1"])
        subprocess.run([kwrite_cmd, "--file", "khotkeysrc", "--group", f"{action_group}Actions0", "--key", "CommandURL", command])
        subprocess.run([kwrite_cmd, "--file", "khotkeysrc", "--group", f"{action_group}Actions0", "--key", "Type", "COMMAND_URL"])

        # Set the trigger
        subprocess.run([kwrite_cmd, "--file", "khotkeysrc", "--group", f"{action_group}Triggers", "--key", "Comment", "Simple_action"])
        subprocess.run([kwrite_cmd, "--file", "khotkeysrc", "--group", f"{action_group}Triggers", "--key", "TriggersCount", "1"])
        subprocess.run([kwrite_cmd, "--file", "khotkeysrc", "--group", f"{action_group}Triggers0", "--key", "Key", keys])
        subprocess.run([kwrite_cmd, "--file", "khotkeysrc", "--group", f"{action_group}Triggers0", "--key", "Type", "SHORTCUT"])

        # Force reload of shortcuts
        try:
            subprocess.run(["kquitapp5", "kglobalaccel"], check=False)
            time.sleep(1)  # Wait for process to terminate
            subprocess.run(["kglobalaccel5"], check=False)
        except Exception:
            # Try alternate methods
            try:
                subprocess.run(["killall", "kglobalaccel5"], check=False)
                time.sleep(1)
                subprocess.run(["kglobalaccel5"], check=False)
            except Exception:
                pass

    def _is_command_available(self, command: str) -> bool:
        """Check if a command is available in the PATH.

        Args:
            command: The command to check

        Returns:
            True if the command is available, False otherwise
        """
        try:
            subprocess.run(["which", command], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except Exception:
            return False