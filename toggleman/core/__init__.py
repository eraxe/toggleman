"""
Core package for Toggleman application.

This package provides the core functionality for managing toggle scripts.
"""

from toggleman.core.config import ConfigManager
from toggleman.core.toggle_manager import ToggleManager
from toggleman.core.script_generator import ScriptGenerator
from toggleman.core.kwin import KWinManager
from toggleman.core.debug import get_logger, setup_logging
from toggleman.core.web_app_detector import WebAppDetector, WebApp, get_web_app_detector, scan_web_apps_in_background