"""
Configuration management for Toggleman.

This module handles loading, saving, and validating configuration for the application
and individual toggle scripts.
"""

import os
import json
import yaml
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

from toggleman.core.debug import get_logger

logger = get_logger(__name__)


class ConfigManager:
    """Manages configuration for Toggleman and toggle scripts."""

    def __init__(self):
        """Initialize the configuration manager."""
        # Define configuration paths
        self.user_config_dir = Path(os.path.expanduser("~/.config/toggleman"))
        self.system_config_dir = Path("/usr/share/toggleman")
        self.scripts_dir = self.user_config_dir / "scripts"
        self.config_file = self.user_config_dir / "config.yaml"

        # Create necessary directories if they don't exist
        self.user_config_dir.mkdir(parents=True, exist_ok=True)
        self.scripts_dir.mkdir(parents=True, exist_ok=True)

        # Load configuration
        self.config = self._load_config()
        self.scripts = self._load_scripts()

    def _load_config(self) -> Dict[str, Any]:
        """Load the main configuration file."""
        if not self.config_file.exists():
            # Create default configuration
            default_config = {
                "general": {
                    "debug": False,
                    "start_minimized": False,
                    "autostart": False,
                    "default_script_dir": str(Path.home() / ".local/bin"),
                },
                "appearance": {
                    "theme": "system",
                    "icon_size": 32,
                },
                "behavior": {
                    "confirm_delete": True,
                    "auto_refresh": True,
                    "notifications": True,
                },
                "kwin": {
                    "enable_shortcuts": True,
                    "enable_rules": True,
                }
            }

            # Save default configuration
            with open(self.config_file, 'w') as f:
                yaml.dump(default_config, f, default_flow_style=False)

            return default_config

        try:
            with open(self.config_file, 'r') as f:
                config = yaml.safe_load(f)

            # Validate and update if necessary
            if not config:
                config = {}

            # Ensure all required sections exist
            if "general" not in config:
                config["general"] = {}
            if "appearance" not in config:
                config["appearance"] = {}
            if "behavior" not in config:
                config["behavior"] = {}
            if "kwin" not in config:
                config["kwin"] = {}

            return config

        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return {
                "general": {},
                "appearance": {},
                "behavior": {},
                "kwin": {}
            }

    def _load_scripts(self) -> Dict[str, Dict[str, Any]]:
        """Load all toggle script configurations."""
        scripts = {}

        try:
            # Iterate through script configuration files
            for script_file in self.scripts_dir.glob("*.json"):
                with open(script_file, 'r') as f:
                    script_config = json.load(f)

                # Use filename (without .json) as the script name
                script_name = script_file.stem
                scripts[script_name] = script_config

        except Exception as e:
            logger.error(f"Error loading script configurations: {e}")

        return scripts

    def save_config(self) -> bool:
        """Save the main configuration to disk."""
        try:
            with open(self.config_file, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
            return True
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            return False

    def save_script(self, name: str, config: Dict[str, Any]) -> bool:
        """Save a toggle script configuration to disk."""
        try:
            script_file = self.scripts_dir / f"{name}.json"
            with open(script_file, 'w') as f:
                json.dump(config, f, indent=2)

            # Update scripts dictionary
            self.scripts[name] = config

            return True
        except Exception as e:
            logger.error(f"Error saving script configuration for {name}: {e}")
            return False

    def delete_script(self, name: str) -> bool:
        """Delete a toggle script configuration."""
        try:
            script_file = self.scripts_dir / f"{name}.json"

            if script_file.exists():
                script_file.unlink()

            # Remove from scripts dictionary
            if name in self.scripts:
                del self.scripts[name]

            return True
        except Exception as e:
            logger.error(f"Error deleting script configuration for {name}: {e}")
            return False

    def get_script(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a toggle script configuration by name."""
        return self.scripts.get(name)

    def get_all_scripts(self) -> Dict[str, Dict[str, Any]]:
        """Get all toggle script configurations."""
        return self.scripts

    def get_setting(self, section: str, key: str, default: Any = None) -> Any:
        """Get a setting from the configuration."""
        if section in self.config and key in self.config[section]:
            return self.config[section][key]
        return default

    def set_setting(self, section: str, key: str, value: Any) -> None:
        """Set a setting in the configuration."""
        if section not in self.config:
            self.config[section] = {}

        self.config[section][key] = value

    def initialize_default(self) -> bool:
        """Initialize default configuration and example script."""
        try:
            # Create default configuration
            self._load_config()

            # Create example toggle script based on the provided script
            example_script = {
                "name": "Chrome Claude",
                "description": "Toggle Chrome Claude AI webapp",
                "app_command": "/opt/google/chrome/google-chrome --profile-directory=Default --app-id=fmpnliohjhemenmnlpbfagaolkdacoja",
                "app_process": "chrome.*--app-id=fmpnliohjhemenmnlpbfagaolkdacoja",
                "window_class": "crx_fmpnliohjhemenmnlpbfagaolkdacoja",
                "chrome_exec": "/opt/google/chrome/google-chrome",
                "chrome_profile": "Default",
                "app_id": "fmpnliohjhemenmnlpbfagaolkdacoja",
                "icon_path": "",
                "tray_name": "Chrome Claude Toggle",
                "script_path": str(Path.home() / ".local/bin/toggle-chrome-claude.sh"),
                "kwin_shortcut": "",
                "autostart": False,
                "notifications": True,
                "debug": False
            }

            # Save example script
            self.save_script("chrome-claude", example_script)

            return True

        except Exception as e:
            logger.error(f"Error initializing default configuration: {e}")
            return False