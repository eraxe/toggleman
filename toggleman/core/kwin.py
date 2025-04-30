"""
KWin integration for Toggleman.

This module handles integration with KDE's window manager (KWin),
including setting keyboard shortcuts and opening window rules.
"""

import os
import subprocess
import tempfile
import time
import shlex
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
        self._detect_kde_tools()

    def _detect_kde_tools(self):
        """Detect available KDE tools."""
        self.kde_tools = {}
        
        # Check for kcmshell versions
        for tool in ["kcmshell5", "kcmshell6"]:
            if self._is_command_available(tool):
                self.kde_tools["kcmshell"] = tool
                break
                
        # Check for systemsettings versions
        for tool in ["systemsettings5", "systemsettings"]:
            if self._is_command_available(tool):
                self.kde_tools["systemsettings"] = tool
                break
                
        # Check for kmenuedit versions
        for tool in ["kmenuedit", "kmenuedit5"]:
            if self._is_command_available(tool):
                self.kde_tools["kmenuedit"] = tool
                break
                
        # Check for shortcut tools
        for tool in ["kde-open5", "kde-open", "xdg-open"]:
            if self._is_command_available(tool):
                self.kde_tools["opener"] = tool
                break
                
        logger.debug(f"Detected KDE tools: {self.kde_tools}")

    def set_shortcut(self, script_name: str, shortcut: str) -> Tuple[bool, str]:
        """Open KDE's keyboard shortcut editor to set a shortcut for a toggle script.

        Args:
            script_name: The name of the toggle script
            shortcut: The shortcut key sequence (e.g., "Meta+Alt+C") - used as suggestion

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

        # Update the script configuration with the suggested shortcut
        # (The user will need to actually set it in KDE's UI)
        script_config["kwin_shortcut"] = shortcut
        self.config_manager.save_script(script_name, script_config)

        # Open KDE's shortcut editor
        try:
            # Try different methods to open the shortcut editor
            opened = False
            
            # Method 1: Try KDE's Custom Shortcuts module
            if "kcmshell" in self.kde_tools:
                logger.debug(f"Opening custom shortcuts with {self.kde_tools['kcmshell']}")
                try:
                    subprocess.Popen([self.kde_tools["kcmshell"], "kcm_keys"])
                    opened = True
                except Exception as e:
                    logger.warning(f"Error opening custom shortcuts with kcmshell: {e}")
            
            # Method 2: Try systemsettings
            if not opened and "systemsettings" in self.kde_tools:
                logger.debug(f"Opening system settings with {self.kde_tools['systemsettings']}")
                try:
                    if self.kde_tools["systemsettings"] == "systemsettings5":
                        subprocess.Popen([self.kde_tools["systemsettings"], "keys"])
                    else:
                        subprocess.Popen([self.kde_tools["systemsettings"], "--section=shortcuts"])
                    opened = True
                except Exception as e:
                    logger.warning(f"Error opening system settings: {e}")
            
            # Method 3: Use xdg-open or kde-open to open the settings URL
            if not opened and "opener" in self.kde_tools:
                logger.debug(f"Opening shortcuts with {self.kde_tools['opener']}")
                try:
                    subprocess.Popen([self.kde_tools["opener"], "settings://shortcuts"])
                    opened = True
                except Exception as e:
                    logger.warning(f"Error opening shortcuts with opener: {e}")
            
            if not opened:
                # Last resort: Try a direct command
                logger.debug("Trying direct command to open shortcuts")
                try:
                    subprocess.Popen(["systemsettings5", "keys"])
                    opened = True
                except Exception:
                    try:
                        subprocess.Popen(["systemsettings", "--section=shortcuts"])
                        opened = True
                    except Exception as e:
                        logger.warning(f"Error opening shortcuts with direct command: {e}")
            
            if opened:
                return True, (
                    f"Opened KDE shortcut editor.\n\n"
                    f"Please add a new custom shortcut with these details:\n"
                    f"- Command: {script_path}\n"
                    f"- Name: Toggle {script_name}\n"
                    f"- Shortcut: {shortcut} (suggested)\n\n"
                    f"After creating the shortcut, click 'Apply' to save it."
                )
            else:
                return False, (
                    f"Could not open KDE shortcut editor. Please manually add a shortcut:\n"
                    f"1. Open System Settings > Shortcuts > Custom Shortcuts\n"
                    f"2. Add a new shortcut with command: {script_path}\n"
                    f"3. Set the shortcut to: {shortcut} (suggested)"
                )

        except Exception as e:
            logger.error(f"Error opening shortcut editor: {e}")
            return False, f"Error opening shortcut editor: {str(e)}"

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

        # Get current shortcut
        current_shortcut = script_config.get("kwin_shortcut", "")
        
        # Remove the shortcut from script configuration
        if "kwin_shortcut" in script_config:
            del script_config["kwin_shortcut"]
        self.config_manager.save_script(script_name, script_config)

        # Open KDE's shortcut editor for manual removal
        try:
            # Try different methods to open the shortcut editor
            opened = False
            
            # Method 1: Try KDE's Custom Shortcuts module
            if "kcmshell" in self.kde_tools:
                logger.debug(f"Opening custom shortcuts with {self.kde_tools['kcmshell']}")
                try:
                    subprocess.Popen([self.kde_tools["kcmshell"], "kcm_keys"])
                    opened = True
                except Exception as e:
                    logger.warning(f"Error opening custom shortcuts with kcmshell: {e}")
            
            # Method 2: Try systemsettings
            if not opened and "systemsettings" in self.kde_tools:
                logger.debug(f"Opening system settings with {self.kde_tools['systemsettings']}")
                try:
                    if self.kde_tools["systemsettings"] == "systemsettings5":
                        subprocess.Popen([self.kde_tools["systemsettings"], "keys"])
                    else:
                        subprocess.Popen([self.kde_tools["systemsettings"], "--section=shortcuts"])
                    opened = True
                except Exception as e:
                    logger.warning(f"Error opening system settings: {e}")
            
            if opened:
                return True, (
                    f"Removed shortcut from configuration and opened KDE shortcut editor.\n\n"
                    f"Please also remove the shortcut '{current_shortcut}' for 'Toggle {script_name}' "
                    f"from the Custom Shortcuts section if it exists."
                )
            else:
                return True, (
                    f"Removed shortcut from configuration.\n\n"
                    f"Please also manually remove the shortcut '{current_shortcut}' for 'Toggle {script_name}' "
                    f"from System Settings > Shortcuts > Custom Shortcuts."
                )

        except Exception as e:
            logger.error(f"Error opening shortcut editor: {e}")
            return True, f"Removed shortcut from configuration, but error opening KDE shortcut editor: {str(e)}"

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
            # Try different methods to open the window rules editor
            opened = False
            
            # Method 1: Try kcmshell
            if "kcmshell" in self.kde_tools:
                logger.debug(f"Opening window rules with {self.kde_tools['kcmshell']}")
                try:
                    subprocess.Popen([self.kde_tools["kcmshell"], "kwinrules"])
                    opened = True
                except Exception as e:
                    logger.warning(f"Error opening window rules with kcmshell: {e}")
            
            # Method 2: Try systemsettings
            if not opened and "systemsettings" in self.kde_tools:
                logger.debug(f"Opening system settings with {self.kde_tools['systemsettings']}")
                try:
                    if self.kde_tools["systemsettings"] == "systemsettings5":
                        subprocess.Popen([self.kde_tools["systemsettings"], "kcm_kwinrules"])
                    else:
                        subprocess.Popen([self.kde_tools["systemsettings"], "--section=windowmanagement", "--subsection=kwinrules"])
                    opened = True
                except Exception as e:
                    logger.warning(f"Error opening system settings: {e}")
            
            # Method 3: Use xdg-open or kde-open to open the settings URL
            if not opened and "opener" in self.kde_tools:
                logger.debug(f"Opening window rules with {self.kde_tools['opener']}")
                try:
                    subprocess.Popen([self.kde_tools["opener"], "settings://kwinrules"])
                    opened = True
                except Exception as e:
                    logger.warning(f"Error opening window rules with opener: {e}")
            
            if not opened:
                # Last resort: Try a direct command
                logger.debug("Trying direct command to open window rules")
                try:
                    subprocess.Popen(["kcmshell5", "kwinrules"])
                    opened = True
                except Exception:
                    try:
                        subprocess.Popen(["kcmshell6", "kwinrules"])
                        opened = True
                    except Exception as e:
                        logger.warning(f"Error opening window rules with direct command: {e}")
            
            if opened:
                return True, (
                    f"Opened KWin window rules editor.\n\n"
                    f"Please create a rule for windows with class: '{window_class}'\n\n"
                    f"Suggested settings:\n"
                    f"- Window matching: Window class (exact match): {window_class}\n"
                    f"- Position: Remember\n"
                    f"- Size: Remember\n"
                    f"- Minimized: Apply initially (if you want it to start minimized)\n"
                    f"- Skip taskbar: Apply initially (optional)\n"
                    f"- Skip pager: Apply initially (optional)\n\n"
                    f"After creating the rule, click 'Apply' to save it."
                )
            else:
                return False, (
                    f"Could not open KWin window rules editor. Please manually add a window rule:\n"
                    f"1. Open System Settings > Window Management > Window Rules\n"
                    f"2. Add a new rule for windows with class: {window_class}\n"
                    f"3. Configure the desired behavior (position, size, etc.)"
                )

        except Exception as e:
            logger.error(f"Error opening window rules editor: {e}")
            return False, f"Error opening window rules editor: {str(e)}"

    def _is_command_available(self, command: str) -> bool:
        """Check if a command is available in the PATH.

        Args:
            command: The command to check

        Returns:
            True if the command is available, False otherwise
        """
        try:
            # Use subprocess.run instead of which for better compatibility
            result = subprocess.run(
                ["which", command], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            return result.returncode == 0
        except Exception:
            return False