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
            # Opera paths
            f"{self.home_dir}/.config/opera",
            # Vivaldi paths
            f"{self.home_dir}/.config/vivaldi",
        ]

        # Firefox paths
        self.firefox_paths = [
            f"{self.home_dir}/.mozilla/firefox",
            f"{self.home_dir}/.mozilla/firefox-esr",
            f"{self.home_dir}/.librewolf",  # LibreWolf is a Firefox fork
        ]

        # Browser executables
        self.browser_executables = {
            "chrome": [
                "/usr/bin/google-chrome",
                "/usr/bin/google-chrome-stable",
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

            # Find browser executable
            browser_path = self._find_browser_executable(browser_type)
            if not browser_path:
                logger.warning(f"Could not find {browser_type} executable. Using placeholder.")
                browser_path = f"/usr/bin/{browser_type}"

            # Find profiles
            profiles = self._get_chrome_profiles(chrome_path)

            for profile in profiles:
                profile_path = os.path.join(chrome_path, profile)

                # Find web apps directory
                web_app_dir = os.path.join(profile_path, "Web Applications")
                if not os.path.exists(web_app_dir):
                    continue

                # Get the browser type for this profile
                extensions_dir = os.path.join(profile_path, "Extensions")
                if os.path.exists(extensions_dir):
                    web_apps.extend(self._parse_chrome_web_apps(web_app_dir, browser_type, profile, browser_path))

        return web_apps

    def _get_chrome_profiles(self, chrome_path: str) -> List[str]:
        """Get Chrome/Chromium profiles.

        Args:
            chrome_path: Path to Chrome/Chromium config directory

        Returns:
            List of profile names
        """
        profiles = []

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
                with open(local_state_path, 'r') as f:
                    local_state = json.load(f)

                if "profile" in local_state and "info_cache" in local_state["profile"]:
                    for profile_id, profile_info in local_state["profile"]["info_cache"].items():
                        if profile_id not in profiles:
                            profiles.append(profile_id)
            except Exception as e:
                logger.error(f"Error reading Chrome Local State: {e}")

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

            # Skip directories that don't match the expected pattern
            app_dir_name = os.path.basename(app_dir)
            if not re.match(r'^[a-zA-Z0-9_]+_[a-zA-Z0-9_]+$', app_dir_name):
                continue

            # Get app ID from the directory name (last part after underscore)
            app_id = app_dir_name.split('_')[-1]

            # Look for manifest.json
            manifest_path = os.path.join(app_dir, "manifest.json")
            if not os.path.exists(manifest_path):
                continue

            try:
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)

                name = manifest.get("name", "Unknown Web App")
                description = manifest.get("description", "")
                start_url = manifest.get("start_url", "")

                # Find icon
                icon_path = ""
                icons = []

                # Look for icon files in the app directory
                for icon_file in glob.glob(os.path.join(app_dir, "*.png")):
                    icons.append(icon_file)

                # If we found icons, use the first one
                if icons:
                    # Sort by size (assuming larger is better)
                    icons.sort(key=lambda x: os.path.getsize(x), reverse=True)
                    icon_path = icons[0]

                # Determine window class based on browser type
                window_class = ""
                if browser_type == "chrome":
                    window_class = f"crx_{app_id}"
                elif browser_type == "chromium":
                    window_class = f"crx_{app_id}"
                elif browser_type == "brave":
                    window_class = f"crx_{app_id}"
                elif browser_type == "edge":
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

            except Exception as e:
                logger.error(f"Error parsing Chrome web app manifest {manifest_path}: {e}")

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

            # Determine browser type
            browser_type = "firefox"
            if "librewolf" in firefox_path.lower():
                browser_type = "librewolf"

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

            for profile_path, profile_name in profiles:
                # Look for Progressive Web Apps extension
                pwa_extension_id = "pwas-for-firefox@filips.si"  # Extension ID for PWAs for Firefox

                # Check multiple possible locations for the extension data
                pwa_data_paths = [
                    os.path.join(profile_path, "browser-extension-data", pwa_extension_id),
                    os.path.join(profile_path, "storage", "default", pwa_extension_id),
                    os.path.join(profile_path, "extension-data", pwa_extension_id),
                ]

                for pwa_data_path in pwa_data_paths:
                    if os.path.exists(pwa_data_path):
                        web_apps.extend(self._parse_firefox_pwa_data(pwa_data_path, browser_type, profile_name, browser_path))

                # Also look for the manifest storage in IndexedDB
                storage_path = os.path.join(profile_path, "storage", "default", "moz-extension+++")
                if os.path.exists(storage_path):
                    # Find the extension directory
                    for ext_dir in os.listdir(storage_path):
                        if os.path.isdir(os.path.join(storage_path, ext_dir)):
                            # Look for idb files
                            idb_path = os.path.join(storage_path, ext_dir, "idb")
                            if os.path.exists(idb_path):
                                web_apps.extend(self._parse_firefox_idb_data(idb_path, browser_type, profile_name, browser_path))

                # Also check for Site-Specific Browser (SSB) configurations in prefs.js
                prefs_path = os.path.join(profile_path, "prefs.js")
                if os.path.exists(prefs_path):
                    web_apps.extend(self._parse_firefox_ssb_data(prefs_path, browser_type, profile_name, browser_path))

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

    def _parse_firefox_pwa_data(self, pwa_data_path: str, browser_type: str, profile: str, browser_path: str) -> List[WebApp]:
        """Parse Firefox PWA data.

        Args:
            pwa_data_path: Path to PWA extension data
            browser_type: Type of browser (firefox, librewolf, etc.)
            profile: Profile name
            browser_path: Path to browser executable

        Returns:
            List of WebApp objects
        """
        web_apps = []

        # Look for storage.js file
        storage_js_path = os.path.join(pwa_data_path, "storage.js")
        if os.path.exists(storage_js_path):
            try:
                with open(storage_js_path, 'r') as f:
                    data = f.read()

                # Extract JSON data
                match = re.search(r'\{.*\}', data, re.DOTALL)
                if match:
                    storage_data = json.loads(match.group(0))

                    if "manifests" in storage_data:
                        for app_id, app_data in storage_data["manifests"].items():
                            name = app_data.get("name", "Unknown PWA")
                            description = app_data.get("description", "")
                            start_url = app_data.get("start_url", "")

                            # Generate a window class
                            # Firefox PWAs typically use a window class based on the URL
                            window_class = self._generate_firefox_window_class(start_url)

                            # Look for icon
                            icon_path = ""
                            if "icons" in app_data and len(app_data["icons"]) > 0:
                                # Save the icon to a temp location
                                temp_dir = os.path.join(os.path.expanduser("~"), ".cache", "toggleman", "icons")
                                os.makedirs(temp_dir, exist_ok=True)

                                # Take the largest icon
                                icon_data = sorted(app_data["icons"], key=lambda x: x.get("sizes", "0x0").split("x")[0], reverse=True)[0]
                                icon_url = icon_data.get("src", "")

                                if icon_url.startswith("data:image"):
                                    # Base64 encoded image
                                    icon_path = os.path.join(temp_dir, f"{app_id}.png")
                                    # We would need to decode and save the image here
                                    # But this is complex and outside the scope
                                elif icon_url.startswith("http"):
                                    # Remote image
                                    icon_path = os.path.join(temp_dir, f"{app_id}.png")
                                    # We would need to download the image here
                                    # But this is complex and outside the scope

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

            except Exception as e:
                logger.error(f"Error parsing Firefox PWA data: {e}")

        # Look for JSON storage
        storage_json_path = os.path.join(pwa_data_path, "storage.json")
        if os.path.exists(storage_json_path):
            try:
                with open(storage_json_path, 'r') as f:
                    storage_data = json.load(f)

                if "manifests" in storage_data:
                    for app_id, app_data in storage_data["manifests"].items():
                        name = app_data.get("name", "Unknown PWA")
                        description = app_data.get("description", "")
                        start_url = app_data.get("start_url", "")

                        # Generate a window class
                        window_class = self._generate_firefox_window_class(start_url)

                        # Look for icon (similar to above)
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

            except Exception as e:
                logger.error(f"Error parsing Firefox PWA JSON data: {e}")

        return web_apps

    def _parse_firefox_idb_data(self, idb_path: str, browser_type: str, profile: str, browser_path: str) -> List[WebApp]:
        """Parse Firefox IndexedDB data.

        Args:
            idb_path: Path to IndexedDB directory
            browser_type: Type of browser (firefox, librewolf, etc.)
            profile: Profile name
            browser_path: Path to browser executable

        Returns:
            List of WebApp objects
        """
        web_apps = []

        # Look for SQLite databases
        for db_file in glob.glob(os.path.join(idb_path, "*.sqlite")):
            try:
                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()

                # Check if the database has a table for PWA manifests
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [table[0] for table in cursor.fetchall()]

                pwa_tables = [table for table in tables if "manifest" in table.lower()]

                for table in pwa_tables:
                    try:
                        cursor.execute(f"SELECT * FROM {table}")
                        rows = cursor.fetchall()

                        for row in rows:
                            # Extract manifest data
                            # This is highly dependent on the specific database schema
                            # We'll need to adapt this based on the actual structure

                            # Just a placeholder for demonstration purposes
                            name = "Firefox PWA"
                            description = ""
                            start_url = ""
                            app_id = os.path.basename(db_file).split(".")[0]

                            # Generate a window class
                            window_class = self._generate_firefox_window_class(start_url)

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

                    except Exception as e:
                        logger.error(f"Error parsing Firefox IDB table {table}: {e}")

                conn.close()

            except Exception as e:
                logger.error(f"Error opening Firefox IDB database {db_file}: {e}")

        return web_apps

    def _parse_firefox_ssb_data(self, prefs_path: str, browser_type: str, profile: str, browser_path: str) -> List[WebApp]:
        """Parse Firefox Site-Specific Browser (SSB) data.

        Args:
            prefs_path: Path to prefs.js file
            browser_type: Type of browser (firefox, librewolf, etc.)
            profile: Profile name
            browser_path: Path to browser executable

        Returns:
            List of WebApp objects
        """
        web_apps = []

        try:
            with open(prefs_path, 'r') as f:
                prefs_data = f.read()

            # Look for SSB preferences
            ssb_regex = r'user_pref\("ssb\.([^"]+)", "([^"]+)"\);'
            ssb_matches = re.findall(ssb_regex, prefs_data)

            ssb_data = {}
            for key, value in ssb_matches:
                parts = key.split('.')
                if len(parts) >= 2:
                    app_id = parts[0]
                    attr = parts[1]

                    if app_id not in ssb_data:
                        ssb_data[app_id] = {}

                    ssb_data[app_id][attr] = value

            for app_id, app_data in ssb_data.items():
                name = app_data.get("name", "Unknown SSB")
                start_url = app_data.get("url", "")
                description = ""

                # Generate a window class
                window_class = self._generate_firefox_window_class(start_url)

                # Look for icon
                icon_path = app_data.get("icon", "")

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

        except Exception as e:
            logger.error(f"Error parsing Firefox SSB data: {e}")

        return web_apps

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
            path_expanded = os.path.expanduser(path)
            # Check for exact match
            if os.path.isfile(path_expanded) and os.access(path_expanded, os.X_OK):
                return path_expanded

            # Check for glob pattern
            for match in glob.glob(path_expanded):
                if os.path.isfile(match) and os.access(match, os.X_OK):
                    return match

        # Try using which
        try:
            result = subprocess.run(["which", browser_type],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    text=True)
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