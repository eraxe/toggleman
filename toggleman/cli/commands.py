"""
Command-line interface commands for Toggleman.

This module handles processing of command-line arguments and executing
the corresponding actions.
"""

import os
import sys
import argparse
from typing import Dict, List, Optional, Any, Tuple

from toggleman.core.config import ConfigManager
from toggleman.core.toggle_manager import ToggleManager
from toggleman.core.kwin import KWinManager
from toggleman.core.debug import get_logger

logger = get_logger(__name__)


def process_command(args: argparse.Namespace, config: ConfigManager) -> int:
    """Process a command-line command.

    Args:
        args: The parsed command-line arguments
        config: The configuration manager instance

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    # Create managers
    toggle_manager = ToggleManager(config)
    kwin_manager = KWinManager(config)

    # Process commands
    if args.command == "list":
        return cmd_list(config, toggle_manager)
    elif args.command == "create":
        return cmd_create(args, config, toggle_manager)
    elif args.command == "edit":
        return cmd_edit(args, config, toggle_manager)
    elif args.command == "remove":
        return cmd_remove(args, config, toggle_manager)
    elif args.command == "toggle":
        return cmd_toggle(args, toggle_manager)
    elif args.command == "run":
        return cmd_run(args, toggle_manager)
    elif args.command == "kwin":
        if args.kwin_command == "shortcut":
            return cmd_kwin_shortcut(args, config, kwin_manager)
        elif args.kwin_command == "rule":
            return cmd_kwin_rule(args, config, kwin_manager)
        else:
            print(f"Unknown KWin command: {args.kwin_command}")
            return 1
    else:
        print(f"Unknown command: {args.command}")
        return 1


def cmd_list(config: ConfigManager, toggle_manager: ToggleManager) -> int:
    """List all toggle scripts.

    Args:
        config: The configuration manager instance
        toggle_manager: The toggle manager instance

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    scripts = config.get_all_scripts()
    running_toggles = toggle_manager.get_running_toggles()

    if not scripts:
        print("No toggle scripts found.")
        return 0

    print(f"Found {len(scripts)} toggle scripts:")
    print("")

    for name, script_config in scripts.items():
        # Get status (running or not)
        status = "RUNNING" if name in running_toggles else "STOPPED"

        # Get path
        path = script_config.get("script_path", "Not generated")

        # Get shortcut
        shortcut = script_config.get("kwin_shortcut", "None")

        # Print info
        print(f"- {name}:")
        print(f"  Description: {script_config.get('description', 'No description')}")
        print(f"  Status: {status}")
        print(f"  Path: {path}")
        print(f"  Shortcut: {shortcut}")
        print("")

    return 0


def cmd_create(args: argparse.Namespace, config: ConfigManager, toggle_manager: ToggleManager) -> int:
    """Create a new toggle script.

    Args:
        args: The parsed command-line arguments
        config: The configuration manager instance
        toggle_manager: The toggle manager instance

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    # Check if script already exists
    if config.get_script(args.name):
        print(f"Toggle script '{args.name}' already exists.")
        return 1

    # Create basic configuration
    script_config = {
        "name": args.name,
        "description": f"Toggle script for {args.name}",
        "app_command": args.app_command or "",
        "app_process": args.app_command or "",  # Use app_command as default
        "window_class": args.window_class or "",
        "icon_path": args.icon or "",
        "tray_name": f"{args.name} Toggle",
        "script_path": "",
        "notifications": True,
        "debug": False
    }

    # Validate configuration
    missing_fields = []
    if not script_config["app_command"]:
        missing_fields.append("app_command")
    if not script_config["window_class"]:
        missing_fields.append("window_class")

    if missing_fields:
        print(f"Missing required fields: {', '.join(missing_fields)}")
        print("Please provide these fields using --app-command and --window-class options.")
        return 1

    # Create toggle script
    success, message = toggle_manager.create_toggle(args.name, script_config)

    if success:
        print(f"Successfully created toggle script '{args.name}'.")
        print(message)
        return 0
    else:
        print(f"Failed to create toggle script: {message}")
        return 1


def cmd_edit(args: argparse.Namespace, config: ConfigManager, toggle_manager: ToggleManager) -> int:
    """Edit an existing toggle script.

    Args:
        args: The parsed command-line arguments
        config: The configuration manager instance
        toggle_manager: The toggle manager instance

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    # Check if script exists
    script_config = config.get_script(args.name)
    if not script_config:
        print(f"Toggle script '{args.name}' not found.")
        return 1

    # Update configuration
    updated = False

    if args.app_command:
        script_config["app_command"] = args.app_command
        updated = True

    if args.window_class:
        script_config["window_class"] = args.window_class
        updated = True

    if args.icon:
        script_config["icon_path"] = args.icon
        updated = True

    if not updated:
        print("No changes specified. Use --app-command, --window-class, or --icon to make changes.")
        return 1

    # Update toggle script
    success, message = toggle_manager.update_toggle(args.name, script_config)

    if success:
        print(f"Successfully updated toggle script '{args.name}'.")
        print(message)
        return 0
    else:
        print(f"Failed to update toggle script: {message}")
        return 1


def cmd_remove(args: argparse.Namespace, config: ConfigManager, toggle_manager: ToggleManager) -> int:
    """Remove a toggle script.

    Args:
        args: The parsed command-line arguments
        config: The configuration manager instance
        toggle_manager: The toggle manager instance

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    # Check if script exists
    if not config.get_script(args.name):
        print(f"Toggle script '{args.name}' not found.")
        return 1

    # Confirm removal
    confirmation = input(f"Are you sure you want to remove toggle script '{args.name}'? (y/n): ")
    if confirmation.lower() != 'y':
        print("Removal canceled.")
        return 0

    # Remove toggle script
    success, message = toggle_manager.delete_toggle(args.name)

    if success:
        print(f"Successfully removed toggle script '{args.name}'.")
        print(message)
        return 0
    else:
        print(f"Failed to remove toggle script: {message}")
        return 1


def cmd_toggle(args: argparse.Namespace, toggle_manager: ToggleManager) -> int:
    """Toggle an application window.

    Args:
        args: The parsed command-line arguments
        toggle_manager: The toggle manager instance

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    # Run toggle script
    success, message = toggle_manager.run_toggle(args.name)

    if success:
        return 0
    else:
        print(f"Failed to toggle application: {message}")
        return 1


def cmd_run(args: argparse.Namespace, toggle_manager: ToggleManager) -> int:
    """Run an application from a toggle script.

    Args:
        args: The parsed command-line arguments
        toggle_manager: The toggle manager instance

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    # Run toggle script
    success, message = toggle_manager.run_toggle(args.name)

    if success:
        return 0
    else:
        print(f"Failed to run application: {message}")
        return 1


def cmd_kwin_shortcut(args: argparse.Namespace, config: ConfigManager, kwin_manager: KWinManager) -> int:
    """Set a KWin shortcut for a toggle script.

    Args:
        args: The parsed command-line arguments
        config: The configuration manager instance
        kwin_manager: The KWin manager instance

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    # Check if script exists
    if not config.get_script(args.name):
        print(f"Toggle script '{args.name}' not found.")
        return 1

    # Set shortcut
    success, message = kwin_manager.set_shortcut(args.name, args.shortcut)

    if success:
        print(f"Successfully set shortcut for '{args.name}': {args.shortcut}")
        return 0
    else:
        print(f"Failed to set shortcut: {message}")
        return 1


def cmd_kwin_rule(args: argparse.Namespace, config: ConfigManager, kwin_manager: KWinManager) -> int:
    """Open KWin window rules editor for a toggle script.

    Args:
        args: The parsed command-line arguments
        config: The configuration manager instance
        kwin_manager: The KWin manager instance

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    # Check if script exists
    if not config.get_script(args.name):
        print(f"Toggle script '{args.name}' not found.")
        return 1

    # Open window rules editor
    success, message = kwin_manager.open_window_rules(args.name)

    if success:
        print(message)
        return 0
    else:
        print(f"Failed to open window rules editor: {message}")
        return 1