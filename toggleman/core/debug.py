"""
Debug utilities for Toggleman.

This module provides logging functionality and debugging tools for Toggleman.
"""

import os
import sys
import logging
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict, List, Optional, Any

# Global log level
_DEBUG_MODE = False
_LOG_LEVEL = logging.INFO
_LOG_FORMAT = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
_LOG_DIR = None
_LOG_FILE = None


def setup_logging(debug: bool = False, log_dir: Optional[str] = None) -> None:
    """Set up logging for the application.

    Args:
        debug: Whether to enable debug logging
        log_dir: Optional directory to store log files
    """
    global _DEBUG_MODE, _LOG_LEVEL, _LOG_DIR, _LOG_FILE

    _DEBUG_MODE = debug
    _LOG_LEVEL = logging.DEBUG if debug else logging.INFO

    # Set up log directory
    if log_dir:
        _LOG_DIR = Path(log_dir)
    else:
        _LOG_DIR = Path(os.path.expanduser("~/.config/toggleman/logs"))

    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Set up log file
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    _LOG_FILE = _LOG_DIR / f"toggleman-{timestamp}.log"

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(_LOG_LEVEL)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create and add handlers
    formatter = logging.Formatter(_LOG_FORMAT)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(_LOG_LEVEL)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler
    file_handler = RotatingFileHandler(_LOG_FILE, maxBytes=1024 * 1024 * 5, backupCount=5)
    file_handler.setLevel(_LOG_LEVEL)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Log initial message
    root_logger.info(f"Logging initialized (level: {'DEBUG' if debug else 'INFO'})")
    if debug:
        root_logger.debug(f"Debug mode enabled")
    root_logger.debug(f"Log file: {_LOG_FILE}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name.

    Args:
        name: The name of the logger (usually __name__)

    Returns:
        A configured logger instance
    """
    return logging.getLogger(name)


def get_log_file() -> Optional[str]:
    """Get the path to the current log file.

    Returns:
        The path to the current log file, or None if not set
    """
    global _LOG_FILE
    return str(_LOG_FILE) if _LOG_FILE else None


def get_log_files() -> List[str]:
    """Get a list of all log files.

    Returns:
        A list of paths to all log files
    """
    global _LOG_DIR
    if not _LOG_DIR:
        return []

    log_files = list(_LOG_DIR.glob("toggleman-*.log"))
    return [str(f) for f in sorted(log_files, key=lambda x: x.stat().st_mtime, reverse=True)]


def is_debug_enabled() -> bool:
    """Check if debug mode is enabled.

    Returns:
        True if debug mode is enabled, False otherwise
    """
    global _DEBUG_MODE
    return _DEBUG_MODE


def set_debug_mode(enabled: bool) -> None:
    """Set debug mode.

    Args:
        enabled: Whether to enable debug mode
    """
    global _DEBUG_MODE, _LOG_LEVEL

    _DEBUG_MODE = enabled
    _LOG_LEVEL = logging.DEBUG if enabled else logging.INFO

    # Update log levels for all handlers
    root_logger = logging.getLogger()
    root_logger.setLevel(_LOG_LEVEL)

    for handler in root_logger.handlers:
        handler.setLevel(_LOG_LEVEL)

    root_logger.info(f"Debug mode {'enabled' if enabled else 'disabled'}")


def get_debug_info() -> Dict[str, Any]:
    """Get debugging information about the application environment.

    Returns:
        A dictionary containing debugging information
    """
    import platform
    import sys
    import psutil

    # Get basic system info
    info = {
        "platform": platform.platform(),
        "python_version": sys.version,
        "python_path": sys.executable,
        "cpu_count": os.cpu_count(),
        "memory": {
            "total": psutil.virtual_memory().total,
            "available": psutil.virtual_memory().available,
            "percent": psutil.virtual_memory().percent
        },
        "disk": {
            "total": psutil.disk_usage('/').total,
            "used": psutil.disk_usage('/').used,
            "free": psutil.disk_usage('/').free,
            "percent": psutil.disk_usage('/').percent
        },
        "env_vars": {k: v for k, v in os.environ.items() if not k.startswith('_')}
    }

    # Check for KDE/Wayland
    info["kde_version"] = _get_kde_version()
    info["wayland"] = os.environ.get("XDG_SESSION_TYPE") == "wayland"

    # Check for required commands
    commands = ["qdbus", "xdotool", "notify-send", "kwriteconfig5", "kwin"]
    info["commands"] = {}

    for cmd in commands:
        info["commands"][cmd] = _check_command(cmd)

    return info


def _get_kde_version() -> Optional[str]:
    """Get the KDE version.

    Returns:
        The KDE version, or None if not available
    """
    try:
        import subprocess
        result = subprocess.run(["plasmashell", "--version"],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                encoding='utf-8')

        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return None
    except Exception:
        return None


def _check_command(command: str) -> Dict[str, Any]:
    """Check if a command is available and get its version.

    Args:
        command: The command to check

    Returns:
        A dictionary with information about the command
    """
    import subprocess
    import shutil

    result = {
        "available": False,
        "path": None,
        "version": None
    }

    # Check if command exists
    path = shutil.which(command)
    if path:
        result["available"] = True
        result["path"] = path

        # Try to get version
        try:
            version_proc = subprocess.run([command, "--version"],
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE,
                                          encoding='utf-8',
                                          timeout=1)

            if version_proc.returncode == 0:
                result["version"] = version_proc.stdout.strip()
            else:
                # Some commands use -v instead
                version_proc = subprocess.run([command, "-v"],
                                              stdout=subprocess.PIPE,
                                              stderr=subprocess.PIPE,
                                              encoding='utf-8',
                                              timeout=1)

                if version_proc.returncode == 0:
                    result["version"] = version_proc.stdout.strip()
        except Exception:
            pass

    return result