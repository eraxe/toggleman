"""
Web App Detector for Toggleman.

This module provides functionality to detect web applications installed
on the system from different browsers (Chrome/Chromium, Firefox, etc.)
and extract information needed to create toggle scripts.
"""

import os
import json
import glob
import re
import shutil
import sqlite3
import configparser
import subprocess
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, NamedTuple

from toggleman.core.debug import get_logger

logger = get_logger(__name__)

# This is included in core/__init__.py
# from toggleman.core.web_app_detector import WebAppDetector, WebApp, get_web_app_detector


class WebApp(NamedTuple):
    """Represents a detected web application."""
    name: str
    browser: str  # chrome, chromium, firefox, etc.
    profile: str
    app_id: str
    url: str
    description: str
    window_class: str
    icon_path: str
    browser_path: str


class WebAppDetector:
    """Detects web applications installed on the system."""

    def __init__(self):
        """Initialize the web app detector."""
        self.home_dir = os.path.expanduser("~")

        # Chrome/Chromium paths
        self.chrome_paths = [
            # Chrome paths
            f"{self.home_dir}/.config/google-chrome",
            f"{self.home_dir}/.config/chrome",
            # Chromium paths
            f"{self.home_dir}/.config/chromium",
            # Brave paths
            f"{self.home_dir}/.config/BraveSoftware/Brave-Browser",
            # Edge paths
            f"{self.home_dir}/.config/microsoft-edge",
            f"{self.home_dir}/.config/microsoft-edge-beta",
            f"{self.home_dir}/.config/microsoft-edge-dev",
            # Opera paths
            f"{self.home_dir}/.config/opera",
            f"{self.home_dir}/.config/opera-beta",
            f"{self.home_dir}/.config/opera-developer",
            # Vivaldi paths
            f"{self.home_dir}/.config/vivaldi",
            # Ungoogled Chromium paths
            f"{self.home_dir}/.config/ungoogled-chromium",
        ]

        # Firefox paths
        self.firefox_paths = [
            f"{self.home_dir}/.mozilla/firefox",
            f"{self.home_dir}/.mozilla/firefox-esr",
            f"{self.home_dir}/.librewolf",  # LibreWolf is a Firefox fork
            f"{self.home_dir}/.waterfox",   # Waterfox is another Firefox fork
        ]

        # Browser executables
        self.browser_executables = {
            "chrome": [
                "/usr/bin/google-chrome",
                "/usr/bin/google-chrome-stable",
                "/usr/bin/google-chrome-beta",
                "/usr/bin/google-chrome-unstable",
                "/opt/google/chrome/google-chrome",
                "/snap/bin/google-chrome",
                "/var/lib/flatpak/app/com.google.Chrome/*/active/files/bin/google-chrome",
                f"{self.home_dir}/.local/share/flatpak/app/com.google.Chrome/*/active/files/bin/google-chrome",
            ],
            "chromium": [
                "/usr/bin/chromium",
                "/usr/bin/chromium-browser",
                "/snap/bin/chromium",
                "/var/lib/flatpak/app/org.chromium.Chromium/*/active/files/bin/chromium",
                f"{self.home_dir}/.local/share/flatpak/app/org.chromium.Chromium/*/active/files/bin/chromium",
            ],
            "brave": [
                "/usr/bin/brave",
                "/usr/bin/brave-browser",
                "/opt/brave.com/brave/brave",
                "/snap/bin/brave",
                "/var/lib/flatpak/app/com.brave.Browser/*/active/files/bin/brave",
                f"{self.home_dir}/.local/share/flatpak/app/com.brave.Browser/*/active/files/bin/brave",
            ],
            "edge": [
                "/usr/bin/microsoft-edge",
                "/usr/bin/microsoft-edge-stable",
                "/usr/bin/microsoft-edge-beta",
                "/usr/bin/microsoft-edge-dev",
                "/opt/microsoft/msedge/microsoft-edge",
                "/snap/bin/microsoft-edge",
            ],
            "firefox": [
                "/usr/bin/firefox",
                "/usr/bin/firefox-esr",
                "/usr/lib/firefox/firefox",
                "/snap/bin/firefox",
                "/var/lib/flatpak/app/org.mozilla.firefox/*/active/files/bin/firefox",
                f"{self.home_dir}/.local/share/flatpak/app/org.mozilla.firefox/*/active/files/bin/firefox",
            ],
            "librewolf": [
                "/usr/bin/librewolf",
                "/opt/librewolf/librewolf",
                "/var/lib/flatpak/app/io.gitlab.librewolf-community/*/active/files/bin/librewolf",
                f"{self.home_dir}/.local/share/flatpak/app/io.gitlab.librewolf-community/*/active/files/bin/librewolf",
            ],
            "opera": [
                "/usr/bin/opera",
                "/usr/bin/opera-beta",
                "/usr/bin/opera-developer",
                "/usr/lib/x86_64-linux-gnu/opera/opera",
                "/snap/bin/opera",
                "/var/lib/flatpak/app/com.opera.Opera/*/active/files/bin/opera",
                f"{self.home_dir}/.local/share/flatpak/app/com.opera.Opera/*/active/files/bin/opera",
            ],
            "vivaldi": [
                "/usr/bin/vivaldi",
                "/usr/bin/vivaldi-stable",
                "/opt/vivaldi/vivaldi",
                "/snap/bin/vivaldi",
                "/var/lib/flatpak/app/com.vivaldi.Vivaldi/*/active/files/bin/vivaldi",
                f"{self.home_dir}/.local/share/flatpak/app/com.vivaldi.Vivaldi/*/active/files/bin/vivaldi",
            ],
        }

    def get_all_web_apps(self) -> List[WebApp]:
        """Get all web apps from all supported browsers.

        Returns:
            List of WebApp objects
        """
        all_apps = []

        # Detect Chrome/Chromium web apps
        chrome_apps = self.detect_chrome_web_apps()
        all_apps.extend(chrome_apps)

        # Detect Firefox web apps
        firefox_apps = self.detect_firefox_web_apps()
        all_apps.extend(firefox_apps)

        return all_apps

    def detect_chrome_web_apps(self) -> List[WebApp]:
        """Detect Chrome/Chromium web apps.

        Returns:
            List of WebApp objects
        """
        web_apps = []

        for chrome_path in self.chrome_paths:
            if not os.path.exists(chrome_path):
                continue

            try:
                # Determine browser type from path
                browser_type = "chrome"
                if "chromium" in chrome_path.lower():
                    browser_type = "chromium"
                elif "brave" in chrome_path.lower():
                    browser_type = "brave"
                elif "edge" in chrome_path.lower():
                    browser_type = "edge"
                elif "opera" in chrome_path.lower():
                    browser_type = "opera"
                elif "vivaldi" in chrome_path.lower():
                    browser_type = "vivaldi"

                logger.debug(f"Checking for web apps in {browser_type} at {chrome_path}")

                # Find browser executable
                browser_path = self._find_browser_executable(browser_type)
                if not browser_path:
                    logger.warning(f"Could not find {browser_type} executable. Using placeholder.")
                    browser_path = f"/usr/bin/{browser_type}"

                # Find profiles
                profiles = self._get_chrome_profiles(chrome_path)
                logger.debug(f"Found {len(profiles)} profiles in {chrome_path}: {profiles}")

                for profile in profiles:
                    profile_path = os.path.join(chrome_path, profile)
                    
                    # Path might include /Default or /Profile 1 as part of the Local State
                    if not os.path.exists(profile_path):
                        if profile.startswith('/'):
                            # This is a full path
                            profile_path = os.path.join(chrome_path + profile)
                            if not os.path.exists(profile_path):
                                continue
                            # Extract the profile name for later use
                            profile = os.path.basename(profile)
                        else:
                            continue

                    # Check if profile directory exists
                    if not os.path.isdir(profile_path):
                        continue

                    # Find web apps directory - it might be in the profile root or in a subdirectory
                    web_app_dirs = [
                        os.path.join(profile_path, "Web Applications"),
                        os.path.join(profile_path, "Extensions"),
                    ]
                    
                    for web_app_dir in web_app_dirs:
                        if os.path.exists(web_app_dir):
                            logger.debug(f"Found web app directory: {web_app_dir}")
                            # Parse web apps in this directory
                            apps = self._parse_chrome_web_apps(web_app_dir, browser_type, profile, browser_path)
                            web_apps.extend(apps)
                    
                    # Also look for PWAs in the preferences
                    pref_file = os.path.join(profile_path, "Preferences")
                    if os.path.exists(pref_file):
                        try:
                            with open(pref_file, 'r', encoding='utf-8') as f:
                                prefs = json.load(f)
                                
                            # Look for PWAs in different locations based on browser/version
                            pwa_locations = [
                                prefs.get("apps", {}).get("shortcuts", []),
                                prefs.get("web_apps", {}).get("web_app_ids", {}),
                                prefs.get("web_app_ids", {}),
                            ]
                            
                            for pwa_location in pwa_locations:
                                if pwa_location:
                                    logger.debug(f"Found PWAs in preferences")
                                    apps = self._parse_chrome_prefs_web_apps(pwa_location, browser_type, profile, browser_path, profile_path)
                                    web_apps.extend(apps)
                        except Exception as e:
                            logger.error(f"Error parsing Chrome preferences: {e}")
            except Exception as e:
                logger.error(f"Error processing Chrome path {chrome_path}: {e}")

        return web_apps

    def _get_chrome_profiles(self, chrome_path: str) -> List[str]:
        """Get Chrome/Chromium profiles.

        Args:
            chrome_path: Path to Chrome/Chromium config directory

        Returns:
            List of profile names
        """
        profiles = []

        try:
            # Always check for Default profile
            if os.path.isdir(os.path.join(chrome_path, "Default")):
                profiles.append("Default")

            # Check for numbered profiles
            for profile_dir in glob.glob(os.path.join(chrome_path, "Profile *")):
                profile_name = os.path.basename(profile_dir)
                profiles.append(profile_name)

            # Look for Local State file to find profile names
            local_state_path = os.path.join(chrome_path, "Local State")
            if os.path.exists(local_state_path):
                try:
                    with open(local_state_path, 'r', encoding='utf-8') as f:
                        local_state = json.load(f)

                    if "profile" in local_state and "info_cache" in local_state["profile"]:
                        for profile_id, profile_info in local_state["profile"]["info_cache"].items():
                            # Skip profiles we already found
                            if profile_id in profiles:
                                continue
                                
                            # Check if this is a path or just a profile name
                            if "/" in profile_id:
                                # This is a path, add it directly
                                profiles.append(profile_id)
                            else:
                                profiles.append(profile_id)
                except Exception as e:
                    logger.error(f"Error reading Chrome Local State: {e}")
        except Exception as e:
            logger.error(f"Error getting Chrome profiles: {e}")

        return profiles

    def _parse_chrome_web_apps(self, web_app_dir: str, browser_type: str, profile: str, browser_path: str) -> List[WebApp]:
        """Parse Chrome/Chromium web apps.

        Args:
            web_app_dir: Path to Web Applications directory
            browser_type: Type of browser (chrome, chromium, etc.)
            profile: Profile name
            browser_path: Path to browser executable

        Returns:
            List of WebApp objects
        """
        web_apps = []

        # Each subdirectory in the Web Applications directory corresponds to a web app
        for app_dir in glob.glob(os.path.join(web_app_dir, "*")):
            if not os.path.isdir(app_dir):
                continue

            try:
                # Skip directories that don't match the expected pattern for app directories
                app_dir_name = os.path.basename(app_dir)
                
                # We need to handle different directory patterns based on whether this is
                # Web Applications or Extensions directory
                app_id = ""
                
                if web_app_dir.endswith("Web Applications"):
                    # Web Applications directory - app_dir should match pattern like "app_id_<ID>"
                    # Get app ID from the directory name (last part after underscore)
                    parts = app_dir_name.split('_')
                    if len(parts) > 1:
                        app_id = parts[-1]
                    else:
                        continue
                elif web_app_dir.endswith("Extensions"):
                    # Extensions directory - app_dir should be the app ID directly
                    # Skip directories that don't look like extension IDs
                    if not re.match(r'^[a-z]{32}$', app_dir_name):
                        continue
                    app_id = app_dir_name
                else:
                    # Unknown directory type
                    continue

                # Look for manifest.json in current directory and subdirectories
                manifest_paths = [
                    os.path.join(app_dir, "manifest.json"),
                ]
                
                # Also check version subdirectories for Extensions
                for version_dir in glob.glob(os.path.join(app_dir, "*")):
                    if os.path.isdir(version_dir):
                        manifest_paths.append(os.path.join(version_dir, "manifest.json"))
                
                # Find the first valid manifest
                manifest_path = None
                for path in manifest_paths:
                    if os.path.exists(path):
                        manifest_path = path
                        break
                
                if not manifest_path:
                    continue

                # Read the manifest
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)

                # Extract information
                name = manifest.get("name", "")
                if name.startswith("__MSG_"):
                    # Handle localized names by using app_id as fallback
                    name = f"Web App {app_id[:8]}"
                    
                    # Try to find localized name in _locales directory
                    locales_dir = os.path.join(os.path.dirname(manifest_path), "_locales")
                    if os.path.exists(locales_dir):
                        # Check default locale
                        default_locale = manifest.get("default_locale", "en")
                        locale_path = os.path.join(locales_dir, default_locale, "messages.json")
                        if os.path.exists(locale_path):
                            try:
                                with open(locale_path, 'r', encoding='utf-8') as f:
                                    locales = json.load(f)
                                
                                # Extract message ID from __MSG_*__
                                msg_id = name[6:-2]
                                if msg_id in locales:
                                    name = locales[msg_id].get("message", name)
                            except Exception as e:
                                logger.error(f"Error reading locale file: {e}")

                description = manifest.get("description", "")
                start_url = manifest.get("start_url", "")
                
                # For browser extensions, also check app.getDetails() for a launch URL
                if not start_url and "background" in manifest:
                    # This might be an extension with a launch URL
                    start_url = manifest.get("homepage_url", "")

                # Find icon
                icon_path = ""
                icons = []

                # Look for icon files in the app directory and parent directories
                for icon_file in glob.glob(os.path.join(app_dir, "*.png")):
                    icons.append(icon_file)
                
                # Also look in the manifest path directory
                manifest_dir = os.path.dirname(manifest_path)
                for icon_file in glob.glob(os.path.join(manifest_dir, "*.png")):
                    icons.append(icon_file)
                    
                # Look for icons in icons directory or subdirectories
                for icon_dir in ["icons", "icon", "images", "image"]:
                    icon_path_dir = os.path.join(manifest_dir, icon_dir)
                    if os.path.exists(icon_path_dir):
                        for icon_file in glob.glob(os.path.join(icon_path_dir, "*.png")):
                            icons.append(icon_file)

                # If icons are specified in manifest, try to find them
                if "icons" in manifest:
                    for size, icon_url in manifest["icons"].items():
                        # Skip data URLs
                        if icon_url.startswith("data:"):
                            continue
                            
                        # Handle absolute and relative paths
                        if icon_url.startswith("/"):
                            icon_full_path = os.path.join(manifest_dir, icon_url.lstrip("/"))
                        else:
                            icon_full_path = os.path.join(manifest_dir, icon_url)
                            
                        if os.path.exists(icon_full_path):
                            icons.append(icon_full_path)

                # If we found icons, use the first one
                if icons:
                    # Sort by size (assuming larger is better)
                    icons.sort(key=lambda x: os.path.getsize(x), reverse=True)
                    icon_path = icons[0]

                # Determine window class based on browser type and app ID
                window_class = ""
                if browser_type in ["chrome", "chromium", "brave", "edge", "vivaldi", "opera"]:
                    window_class = f"crx_{app_id}"
                else:
                    # Generic fallback
                    window_class = f"crx_{app_id}"

                web_app = WebApp(
                    name=name,
                    browser=browser_type,
                    profile=profile,
                    app_id=app_id,
                    url=start_url,
                    description=description,
                    window_class=window_class,
                    icon_path=icon_path,
                    browser_path=browser_path
                )

                web_apps.append(web_app)
                logger.debug(f"Found Chrome web app: {name} ({app_id})")
            except Exception as e:
                logger.error(f"Error parsing Chrome web app in {app_dir}: {e}")

        return web_apps

    def _parse_chrome_prefs_web_apps(self, pwa_data, browser_type: str, profile: str, browser_path: str, profile_path: str) -> List[WebApp]:
        """Parse Chrome/Chromium web apps from preferences.

        Args:
            pwa_data: Web app data from preferences
            browser_type: Type of browser (chrome, chromium, etc.)
            profile: Profile name
            browser_path: Path to browser executable
            profile_path: Path to profile directory

        Returns:
            List of WebApp objects
        """
        web_apps = []
        
        try:
            # Handle different data formats
            if isinstance(pwa_data, list):
                # Shortcuts format
                for app in pwa_data:
                    try:
                        name = app.get("name", "Unknown Web App")
                        app_id = app.get("app_id", "")
                        if not app_id:
                            continue
                            
                        url = app.get("url", "")
                        description = app.get("description", "")
                        
                        # Handle icon
                        icon_path = ""
                        if "icon" in app:
                            # Check if icon is a path or data URL
                            icon = app["icon"]
                            if isinstance(icon, str) and not icon.startswith("data:"):
                                icon_path = os.path.join(profile_path, icon)
                                if not os.path.exists(icon_path):
                                    icon_path = ""
                                    
                        # Determine window class
                        window_class = f"crx_{app_id}"
                        
                        web_app = WebApp(
                            name=name,
                            browser=browser_type,
                            profile=profile,
                            app_id=app_id,
                            url=url,
                            description=description,
                            window_class=window_class,
                            icon_path=icon_path,
                            browser_path=browser_path
                        )
                        
                        web_apps.append(web_app)
                        logger.debug(f"Found Chrome web app from preferences: {name} ({app_id})")
                    except Exception as e:
                        logger.error(f"Error parsing Chrome web app from preferences: {e}")
            elif isinstance(pwa_data, dict):
                # Web app IDs format
                for app_id, app_data in pwa_data.items():
                    try:
                        # Skip non-dict entries
                        if not isinstance(app_data, dict):
                            continue
                            
                        name = app_data.get("name", f"Web App {app_id[:8]}")
                        url = app_data.get("start_url", "")
                        description = app_data.get("description", "")
                        
                        # Handle icon - check the Web Applications directory
                        icon_path = ""
                        web_app_dir = os.path.join(profile_path, "Web Applications")
                        if os.path.exists(web_app_dir):
                            # Look for app directory
                            for app_dir in glob.glob(os.path.join(web_app_dir, f"*_{app_id}")):
                                if os.path.isdir(app_dir):
                                    # Look for icon files
                                    for icon_file in glob.glob(os.path.join(app_dir, "*.png")):
                                        icon_path = icon_file
                                        break
                                        
                        # Determine window class
                        window_class = f"crx_{app_id}"
                        
                        web_app = WebApp(
                            name=name,
                            browser=browser_type,
                            profile=profile,
                            app_id=app_id,
                            url=url,
                            description=description,
                            window_class=window_class,
                            icon_path=icon_path,
                            browser_path=browser_path
                        )
                        
                        web_apps.append(web_app)
                        logger.debug(f"Found Chrome web app from preferences: {name} ({app_id})")
                    except Exception as e:
                        logger.error(f"Error parsing Chrome web app from preferences: {e}")
        except Exception as e:
            logger.error(f"Error parsing Chrome preferences web apps: {e}")
            
        return web_apps

    def detect_firefox_web_apps(self) -> List[WebApp]:
        """Detect Firefox web apps.

        Returns:
            List of WebApp objects
        """
        web_apps = []

        # Find Firefox profiles
        for firefox_path in self.firefox_paths:
            if not os.path.exists(firefox_path):
                continue

            try:
                # Determine browser type
                browser_type = "firefox"
                if "librewolf" in firefox_path.lower():
                    browser_type = "librewolf"
                elif "waterfox" in firefox_path.lower():
                    browser_type = "waterfox"

                logger.debug(f"Checking for web apps in {browser_type} at {firefox_path}")

                # Find browser executable
                browser_path = self._find_browser_executable(browser_type)
                if not browser_path:
                    logger.warning(f"Could not find {browser_type} executable. Using placeholder.")
                    browser_path = f"/usr/bin/{browser_type}"

                # Read profiles.ini
                profiles_ini = os.path.join(firefox_path, "profiles.ini")
                if not os.path.exists(profiles_ini):
                    continue

                profiles = self._get_firefox_profiles(profiles_ini)
                logger.debug(f"Found {len(profiles)} profiles in {firefox_path}")

                for profile_path, profile_name in profiles:
                    # Handle various Firefox PWA extensions
                    self._check_firefox_pwa_extensions(profile_path, profile_name, browser_type, browser_path, web_apps)
                    
                    # Check for SSB (Site-Specific Browser) profiles
                    self._check_firefox_ssb(profile_path, profile_name, browser_type, browser_path, web_apps)
            except Exception as e:
                logger.error(f"Error processing Firefox path {firefox_path}: {e}")

        return web_apps

    def _get_firefox_profiles(self, profiles_ini: str) -> List[Tuple[str, str]]:
        """Get Firefox profiles.

        Args:
            profiles_ini: Path to profiles.ini file

        Returns:
            List of tuples (profile_path, profile_name)
        """
        profiles = []

        try:
            config = configparser.ConfigParser()
            config.read(profiles_ini)

            for section in config.sections():
                if section.startswith("Profile"):
                    # Get profile path
                    if config.has_option(section, "Path"):
                        profile_path = config.get(section, "Path")
                        isRelative = config.getboolean(section, "IsRelative", fallback=True)

                        if isRelative:
                            profile_path = os.path.join(os.path.dirname(profiles_ini), profile_path)

                        # Get profile name
                        profile_name = config.get(section, "Name", fallback=os.path.basename(profile_path))

                        profiles.append((profile_path, profile_name))

        except Exception as e:
            logger.error(f"Error reading Firefox profiles.ini: {e}")

        return profiles

    def _check_firefox_pwa_extensions(self, profile_path: str, profile_name: str, browser_type: str, browser_path: str, web_apps: List[WebApp]):
        """Check for Firefox PWA extensions in profile.

        Args:
            profile_path: Path to Firefox profile
            profile_name: Name of Firefox profile
            browser_type: Type of browser (firefox, librewolf, etc.)
            browser_path: Path to browser executable
            web_apps: List to append web apps to
        """
        # Check for common PWA extensions
        pwa_extension_ids = [
            "pwas-for-firefox@filips.si",  # PWAs for Firefox
            "@pwa-for-firefox",            # Progressive Web Apps for Firefox
            "firefoxpwa@filips.si",        # Firefox PWA
            "@smartpwa",                   # Smart PWA
            "@progressive-web-apps",       # Progressive Web Apps
            "webapps@mozilla.org",         # Mozilla Web Apps
        ]
        
        # Check for each extension
        for ext_id in pwa_extension_ids:
            # Check multiple possible locations for the extension data
            ext_data_paths = [
                os.path.join(profile_path, "browser-extension-data", ext_id),
                os.path.join(profile_path, "storage", "default", ext_id),
                os.path.join(profile_path, "extension-data", ext_id),
            ]
            
            for ext_data_path in ext_data_paths:
                if os.path.exists(ext_data_path):
                    logger.debug(f"Found Firefox PWA extension data: {ext_data_path}")
                    # Look for storage data
                    self._parse_firefox_pwa_data(ext_data_path, browser_type, profile_name, browser_path, web_apps)
        
        # Also look for the manifest storage in IndexedDB
        storage_path = os.path.join(profile_path, "storage", "default")
        if os.path.exists(storage_path):
            for ext_dir in os.listdir(storage_path):
                if ext_dir.startswith("moz-extension+++"):
                    ext_storage_path = os.path.join(storage_path, ext_dir)
                    if os.path.isdir(ext_storage_path):
                        # Look for idb files and other storage
                        for subdir in ["idb", "ls", "default"]:
                            subdir_path = os.path.join(ext_storage_path, subdir)
                            if os.path.exists(subdir_path):
                                self._parse_firefox_idb_data(subdir_path, browser_type, profile_name, browser_path, web_apps)

    def _parse_firefox_pwa_data(self, pwa_data_path: str, browser_type: str, profile: str, browser_path: str, web_apps: List[WebApp]):
        """Parse Firefox PWA data.

        Args:
            pwa_data_path: Path to PWA extension data
            browser_type: Type of browser (firefox, librewolf, etc.)
            profile: Profile name
            browser_path: Path to browser executable
            web_apps: List to append web apps to
        """
        # Look for various storage files
        storage_files = [
            os.path.join(pwa_data_path, "storage.js"),
            os.path.join(pwa_data_path, "storage.json"),
            os.path.join(pwa_data_path, "manifests.json"),
            os.path.join(pwa_data_path, "webapps.json"),
        ]
        
        for storage_file in storage_files:
            if os.path.exists(storage_file):
                try:
                    logger.debug(f"Found Firefox PWA storage file: {storage_file}")
                    
                    with open(storage_file, 'r', encoding='utf-8') as f:
                        data = f.read()
                    
                    # Extract JSON data - either direct JSON or embedded in JS
                    json_data = None
                    if storage_file.endswith(".json"):
                        json_data = json.loads(data)
                    else:
                        # Try to extract JSON from JS
                        match = re.search(r'\{.*\}', data, re.DOTALL)
                        if match:
                            json_data = json.loads(match.group(0))
                    
                    if not json_data:
                        continue
                    
                    # Look for manifests/web apps in the data
                    manifests = None
                    if "manifests" in json_data:
                        manifests = json_data["manifests"]
                    elif "webapps" in json_data:
                        manifests = json_data["webapps"]
                    elif "apps" in json_data:
                        manifests = json_data["apps"]
                        
                    if not manifests:
                        continue
                        
                    # Process each web app
                    for app_id, app_data in manifests.items():
                        try:
                            name = app_data.get("name", "Unknown PWA")
                            description = app_data.get("description", "")
                            start_url = app_data.get("start_url", "")
                            if not start_url and "url" in app_data:
                                start_url = app_data["url"]
                                
                            if not start_url:
                                continue

                            # Generate a window class
                            window_class = self._generate_firefox_window_class(start_url)

                            # Look for icon
                            icon_path = ""
                            if "icons" in app_data and app_data["icons"]:
                                # Try to find a usable icon
                                if isinstance(app_data["icons"], list):
                                    for icon in app_data["icons"]:
                                        if isinstance(icon, dict) and "src" in icon:
                                            icon_url = icon["src"]
                                            # Skip data URLs for now
                                            if isinstance(icon_url, str) and not icon_url.startswith("data:"):
                                                # Try to find a local file
                                                if icon_url.startswith("/"):
                                                    local_path = os.path.join(pwa_data_path, icon_url.lstrip("/"))
                                                else:
                                                    local_path = os.path.join(pwa_data_path, icon_url)
                                                    
                                                if os.path.exists(local_path):
                                                    icon_path = local_path
                                                    break
                                elif isinstance(app_data["icons"], dict):
                                    # Try the largest icon
                                    sizes = sorted(app_data["icons"].keys(), key=lambda x: int(x.split("x")[0]) if "x" in x else 0, reverse=True)
                                    if sizes:
                                        icon_url = app_data["icons"][sizes[0]]
                                        if isinstance(icon_url, str) and not icon_url.startswith("data:"):
                                            # Try to find a local file
                                            if icon_url.startswith("/"):
                                                local_path = os.path.join(pwa_data_path, icon_url.lstrip("/"))
                                            else:
                                                local_path = os.path.join(pwa_data_path, icon_url)
                                                
                                            if os.path.exists(local_path):
                                                icon_path = local_path

                            web_app = WebApp(
                                name=name,
                                browser=browser_type,
                                profile=profile,
                                app_id=app_id,
                                url=start_url,
                                description=description,
                                window_class=window_class,
                                icon_path=icon_path,
                                browser_path=browser_path
                            )

                            web_apps.append(web_app)
                            logger.debug(f"Found Firefox PWA: {name} ({app_id})")
                        except Exception as e:
                            logger.error(f"Error parsing Firefox PWA data for app {app_id}: {e}")
                except Exception as e:
                    logger.error(f"Error parsing Firefox PWA data file {storage_file}: {e}")

    def _parse_firefox_idb_data(self, idb_path: str, browser_type: str, profile: str, browser_path: str, web_apps: List[WebApp]):
        """Parse Firefox IndexedDB data.

        Args:
            idb_path: Path to IndexedDB directory
            browser_type: Type of browser (firefox, librewolf, etc.)
            profile: Profile name
            browser_path: Path to browser executable
            web_apps: List to append web apps to
        """
        # Look for SQLite databases and storage files
        try:
            # Check for JSON files first (simpler)
            for json_file in glob.glob(os.path.join(idb_path, "*.json")):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                    # Look for PWA data
                    if "manifests" in data or "webapps" in data or "apps" in data:
                        manifests = data.get("manifests", data.get("webapps", data.get("apps", {})))
                        
                        # Process each web app
                        for app_id, app_data in manifests.items():
                            try:
                                name = app_data.get("name", f"Web App {app_id[:8]}")
                                description = app_data.get("description", "")
                                start_url = app_data.get("start_url", app_data.get("url", ""))
                                
                                if not start_url:
                                    continue

                                # Generate a window class
                                window_class = self._generate_firefox_window_class(start_url)

                                # Look for icon - skip for simplicity
                                icon_path = ""

                                web_app = WebApp(
                                    name=name,
                                    browser=browser_type,
                                    profile=profile,
                                    app_id=app_id,
                                    url=start_url,
                                    description=description,
                                    window_class=window_class,
                                    icon_path=icon_path,
                                    browser_path=browser_path
                                )

                                web_apps.append(web_app)
                                logger.debug(f"Found Firefox PWA from storage: {name} ({app_id})")
                            except Exception as e:
                                logger.error(f"Error parsing Firefox PWA data for app {app_id}: {e}")
                except Exception as e:
                    logger.error(f"Error parsing Firefox storage file {json_file}: {e}")
            
            # Look for SQLite databases - more complex
            for db_file in glob.glob(os.path.join(idb_path, "*.sqlite")):
                try:
                    # Only try to parse if sqlite3 module is available
                    if not hasattr(sqlite3, "connect"):
                        logger.warning("sqlite3 module not available, skipping SQLite database parsing")
                        continue
                        
                    conn = sqlite3.connect(db_file)
                    cursor = conn.cursor()

                    # Check if the database has a table for PWA manifests
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = [table[0] for table in cursor.fetchall()]

                    # Look for manifest-related tables
                    pwa_tables = [table for table in tables if any(keyword in table.lower() for keyword in ["manifest", "webapp", "pwa", "app"])]

                    for table in pwa_tables:
                        try:
                            cursor.execute(f"SELECT * FROM {table}")
                            rows = cursor.fetchall()

                            for row in rows:
                                # We need to identify which columns contain what data
                                # This is very database-specific and hard to generalize
                                # Try a simple approach looking for JSON data
                                for col in row:
                                    if isinstance(col, str) and col.startswith("{") and col.endswith("}"):
                                        try:
                                            json_data = json.loads(col)
                                            if isinstance(json_data, dict) and ("name" in json_data or "manifest" in json_data):
                                                # This looks like a manifest or app data
                                                app_data = json_data.get("manifest", json_data)
                                                app_id = json_data.get("id", os.path.basename(db_file).split(".")[0])
                                                
                                                name = app_data.get("name", f"Web App {app_id[:8]}")
                                                description = app_data.get("description", "")
                                                start_url = app_data.get("start_url", app_data.get("url", ""))
                                                
                                                if not start_url:
                                                    continue
                                                    
                                                # Generate a window class
                                                window_class = self._generate_firefox_window_class(start_url)
                                                
                                                # Skip icon for simplicity
                                                icon_path = ""
                                                
                                                web_app = WebApp(
                                                    name=name,
                                                    browser=browser_type,
                                                    profile=profile,
                                                    app_id=app_id,
                                                    url=start_url,
                                                    description=description,
                                                    window_class=window_class,
                                                    icon_path=icon_path,
                                                    browser_path=browser_path
                                                )
                                                
                                                web_apps.append(web_app)
                                                logger.debug(f"Found Firefox PWA from database: {name} ({app_id})")
                                        except Exception:
                                            # Not valid JSON or not a manifest
                                            pass
                        except Exception as e:
                            logger.error(f"Error parsing Firefox IDB table {table}: {e}")

                    conn.close()
                except Exception as e:
                    logger.error(f"Error opening Firefox IDB database {db_file}: {e}")
        except Exception as e:
            logger.error(f"Error parsing Firefox IDB data: {e}")

    def _check_firefox_ssb(self, profile_path: str, profile_name: str, browser_type: str, browser_path: str, web_apps: List[WebApp]):
        """Check for Firefox Site-Specific Browser configurations.

        Args:
            profile_path: Path to Firefox profile
            profile_name: Name of Firefox profile
            browser_type: Type of browser (firefox, librewolf, etc.)
            browser_path: Path to browser executable
            web_apps: List to append web apps to
        """
        # Check prefs.js file
        prefs_path = os.path.join(profile_path, "prefs.js")
        if os.path.exists(prefs_path):
            self._parse_firefox_ssb_data(prefs_path, browser_type, profile_name, browser_path, web_apps)

    def _parse_firefox_ssb_data(self, prefs_path: str, browser_type: str, profile: str, browser_path: str, web_apps: List[WebApp]):
        """Parse Firefox Site-Specific Browser data.

        Args:
            prefs_path: Path to prefs.js file
            browser_type: Type of browser (firefox, librewolf, etc.)
            profile: Profile name
            browser_path: Path to browser executable
            web_apps: List to append web apps to
        """
        try:
            with open(prefs_path, 'r', encoding='utf-8') as f:
                prefs_data = f.read()

            # Look for SSB preferences - these are browser-specific and may vary
            ssb_patterns = [
                # General SSB pattern
                r'user_pref\("ssb\.([^"]+)", "([^"]+)"\);',
                # Firefox SSB
                r'user_pref\("browser\.ssb\.([^"]+)", "([^"]+)"\);',
                # WebApps pattern
                r'user_pref\("webapps\.([^"]+)", "([^"]+)"\);',
            ]
            
            # Try each pattern
            ssb_data = {}
            for pattern in ssb_patterns:
                ssb_matches = re.findall(pattern, prefs_data)
                
                for key, value in ssb_matches:
                    parts = key.split('.')
                    if len(parts) >= 2:
                        app_id = parts[0]
                        attr = parts[1]

                        if app_id not in ssb_data:
                            ssb_data[app_id] = {}

                        ssb_data[app_id][attr] = value

            # Process each SSB
            for app_id, app_data in ssb_data.items():
                # Skip if no name or URL
                if "name" not in app_data or ("url" not in app_data and "uri" not in app_data):
                    continue
                    
                name = app_data.get("name", f"SSB {app_id}")
                start_url = app_data.get("url", app_data.get("uri", ""))
                description = app_data.get("description", "")

                # Generate a window class
                window_class = self._generate_firefox_window_class(start_url)

                # Look for icon
                icon_path = app_data.get("icon", "")
                if icon_path and not os.path.exists(icon_path):
                    icon_path = ""

                web_app = WebApp(
                    name=name,
                    browser=browser_type,
                    profile=profile,
                    app_id=app_id,
                    url=start_url,
                    description=description,
                    window_class=window_class,
                    icon_path=icon_path,
                    browser_path=browser_path
                )

                web_apps.append(web_app)
                logger.debug(f"Found Firefox SSB: {name} ({app_id})")
        except Exception as e:
            logger.error(f"Error parsing Firefox SSB data: {e}")

    def _generate_firefox_window_class(self, url: str) -> str:
        """Generate a window class for Firefox PWAs based on URL.

        Args:
            url: The URL of the web app

        Returns:
            A window class string
        """
        if not url:
            return "firefox-pwa"

        try:
            # Extract the domain from the URL
            domain_match = re.search(r'https?://([^/]+)', url)
            if domain_match:
                domain = domain_match.group(1)
                # Remove www. prefix
                domain = re.sub(r'^www\.', '', domain)
                # Replace dots with hyphens
                domain = domain.replace('.', '-')
                return f"firefox-pwa-{domain}"
            else:
                return "firefox-pwa"
        except Exception:
            return "firefox-pwa"

    def _find_browser_executable(self, browser_type: str) -> Optional[str]:
        """Find the browser executable path.

        Args:
            browser_type: Type of browser (chrome, firefox, etc.)

        Returns:
            Path to browser executable, or None if not found
        """
        if browser_type not in self.browser_executables:
            return None

        for path in self.browser_executables[browser_type]:
            try:
                path_expanded = os.path.expanduser(path)
                # Check for exact match
                if os.path.isfile(path_expanded) and os.access(path_expanded, os.X_OK):
                    return path_expanded

                # Check for glob pattern
                for match in glob.glob(path_expanded):
                    if os.path.isfile(match) and os.access(match, os.X_OK):
                        return match
            except Exception:
                pass

        # Try using which
        try:
            result = subprocess.run(["which", browser_type],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    text=True,
                                    check=False)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass

        return None


def get_web_app_detector() -> WebAppDetector:
    """Get a WebAppDetector instance.

    Returns:
        WebAppDetector instance
    """
    return WebAppDetector()


# Thread-based scanning for use in background
def scan_web_apps_in_background(callback=None):
    """Scan for web apps in a background thread.

    Args:
        callback: Optional callback function to call with results

    Returns:
        The thread object that's performing the scan
    """
    def _scan_thread():
        detector = WebAppDetector()
        apps = detector.get_all_web_apps()
        if callback:
            callback(apps)

    thread = threading.Thread(target=_scan_thread)
    thread.daemon = True
    thread.start()
    return thread