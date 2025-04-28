#!/usr/bin/env python3
"""
Main entry point for Toggleman application.
Provides both CLI and GUI interfaces.
"""

import sys
import os
import argparse
from PyQt5.QtWidgets import QApplication

from toggleman.core.config import ConfigManager
from toggleman.core.debug import setup_logging, get_logger
from toggleman.gui.main_window import MainWindow
from toggleman.cli.commands import process_command

logger = get_logger(__name__)


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Toggleman - Application toggle script manager for KDE")

    # General options
    parser.add_argument("--version", action="store_true", help="Show version information")
    parser.add_argument("--init", action="store_true", help="Initialize default configuration")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    # GUI options
    parser.add_argument("--gui", action="store_true", help="Launch GUI (default if no other arguments)")
    parser.add_argument("--tray", action="store_true", help="Start in system tray only")

    # CLI options
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # List command
    list_parser = subparsers.add_parser("list", help="List all toggle scripts")

    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new toggle script")
    create_parser.add_argument("name", help="Name of the toggle script")
    create_parser.add_argument("--app-command", help="Command to launch the application")
    create_parser.add_argument("--window-class", help="Window class to match")
    create_parser.add_argument("--icon", help="Path to icon file")

    # Edit command
    edit_parser = subparsers.add_parser("edit", help="Edit an existing toggle script")
    edit_parser.add_argument("name", help="Name of the toggle script")
    edit_parser.add_argument("--app-command", help="Command to launch the application")
    edit_parser.add_argument("--window-class", help="Window class to match")
    edit_parser.add_argument("--icon", help="Path to icon file")

    # Remove command
    remove_parser = subparsers.add_parser("remove", help="Remove a toggle script")
    remove_parser.add_argument("name", help="Name of the toggle script")

    # Toggle command
    toggle_parser = subparsers.add_parser("toggle", help="Toggle an application window")
    toggle_parser.add_argument("name", help="Name of the toggle script")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run an application from a toggle script")
    run_parser.add_argument("name", help="Name of the toggle script")

    # Kwin commands
    kwin_parser = subparsers.add_parser("kwin", help="KWin integration commands")
    kwin_subparsers = kwin_parser.add_subparsers(dest="kwin_command", help="KWin commands")

    # Shortcut command
    shortcut_parser = kwin_subparsers.add_parser("shortcut", help="Set a KWin shortcut for a toggle script")
    shortcut_parser.add_argument("name", help="Name of the toggle script")
    shortcut_parser.add_argument("shortcut", help="Shortcut key sequence (e.g., 'Meta+Alt+C')")

    # Window rule command
    rule_parser = kwin_subparsers.add_parser("rule", help="Open KWin window rules editor for a toggle script")
    rule_parser.add_argument("name", help="Name of the toggle script")

    return parser.parse_args()


def main():
    """Main entry point for the application."""
    args = parse_args()

    # Setup logging
    setup_logging(debug=args.debug)

    # Create config manager
    config = ConfigManager()

    # Initialize if requested
    if args.init:
        logger.info("Initializing default configuration")
        config.initialize_default()
        return 0

    # Show version if requested
    if args.version:
        from toggleman import __version__
        print(f"Toggleman version {__version__}")
        return 0

    # Process CLI commands if specified
    if args.command:
        return process_command(args, config)

    # Default to GUI if no command specified
    if not args.tray:
        args.gui = True

    # Launch GUI if requested
    if args.gui or args.tray:
        app = QApplication(sys.argv)
        app.setApplicationName("Toggleman")
        app.setQuitOnLastWindowClosed(False)  # Allow running in system tray

        main_window = MainWindow(config, start_minimized=args.tray)

        if not args.tray:
            main_window.show()

        return app.exec_()

    # If no arguments provided, show help
    print("No arguments provided. Use --help for options.")
    return 1


if __name__ == "__main__":
    sys.exit(main())