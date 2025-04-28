"""
Settings dialog for Toggleman application.

This module provides the settings dialog for configuring the application.
"""

import os
import sys
from typing import Dict, List, Optional, Any

from PyQt5.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QPushButton, QLabel, QCheckBox, QLineEdit, QTabWidget, QFileDialog,
    QSpinBox, QComboBox, QDialogButtonBox, QSizePolicy, QMessageBox
)
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtCore import Qt, QSize, QSettings

from toggleman.core.config import ConfigManager
from toggleman.core.debug import get_logger, set_debug_mode, is_debug_enabled

logger = get_logger(__name__)


class SettingsDialog(QDialog):
    """Settings dialog for the Toggleman application."""

    def __init__(self, config_manager: ConfigManager, parent=None):
        """Initialize the settings dialog.

        Args:
            config_manager: The configuration manager instance
            parent: The parent widget
        """
        super().__init__(parent)

        self.config_manager = config_manager
        self.original_settings = {}
        self.changed_settings = {}

        # Store original settings
        self._store_original_settings()

        # Set up the UI
        self._setup_ui()

        # Load settings into the UI
        self._load_settings()

        logger.debug("Settings dialog initialized")

    def _setup_ui(self):
        """Set up the dialog UI."""
        # Dialog properties
        self.setWindowTitle("Settings")
        self.setWindowIcon(QIcon.fromTheme("configure"))
        self.resize(500, 400)

        # Create layout
        main_layout = QVBoxLayout(self)

        # Create tab widget
        tab_widget = QTabWidget()

        # Create general tab
        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)

        # Create general settings group
        general_group = QGroupBox("General")
        general_form = QFormLayout(general_group)

        # Create settings
        self.start_minimized_checkbox = QCheckBox("Start minimized to system tray")
        general_form.addRow("", self.start_minimized_checkbox)

        self.autostart_checkbox = QCheckBox("Start automatically at login")
        general_form.addRow("", self.autostart_checkbox)

        self.script_dir_edit = QLineEdit()
        self.script_dir_edit.setReadOnly(True)
        script_dir_layout = QHBoxLayout()
        script_dir_layout.addWidget(self.script_dir_edit)

        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self._on_browse_script_dir)
        script_dir_layout.addWidget(browse_button)

        general_form.addRow("Default script directory:", script_dir_layout)

        # Add general group to tab
        general_layout.addWidget(general_group)

        # Create appearance group
        appearance_group = QGroupBox("Appearance")
        appearance_form = QFormLayout(appearance_group)

        # Create settings
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("System")
        self.theme_combo.addItem("Light")
        self.theme_combo.addItem("Dark")
        appearance_form.addRow("Theme:", self.theme_combo)

        self.icon_size_spin = QSpinBox()
        self.icon_size_spin.setMinimum(16)
        self.icon_size_spin.setMaximum(64)
        self.icon_size_spin.setSingleStep(8)
        appearance_form.addRow("Icon size:", self.icon_size_spin)

        # Add appearance group to tab
        general_layout.addWidget(appearance_group)

        # Add spacer
        general_layout.addStretch()

        # Add general tab to tab widget
        tab_widget.addTab(general_tab, "General")

        # Create behavior tab
        behavior_tab = QWidget()
        behavior_layout = QVBoxLayout(behavior_tab)

        # Create behavior settings group
        behavior_group = QGroupBox("Behavior")
        behavior_form = QFormLayout(behavior_group)

        # Create settings
        self.confirm_delete_checkbox = QCheckBox("Confirm before deleting toggle scripts")
        behavior_form.addRow("", self.confirm_delete_checkbox)

        self.auto_refresh_checkbox = QCheckBox("Automatically refresh toggle script status")
        behavior_form.addRow("", self.auto_refresh_checkbox)

        self.refresh_interval_spin = QSpinBox()
        self.refresh_interval_spin.setMinimum(1)
        self.refresh_interval_spin.setMaximum(60)
        self.refresh_interval_spin.setSuffix(" seconds")
        behavior_form.addRow("Refresh interval:", self.refresh_interval_spin)

        self.minimize_to_tray_checkbox = QCheckBox("Minimize to system tray when closing")
        behavior_form.addRow("", self.minimize_to_tray_checkbox)

        self.notifications_checkbox = QCheckBox("Show notifications")
        behavior_form.addRow("", self.notifications_checkbox)

        # Add behavior group to tab
        behavior_layout.addWidget(behavior_group)

        # Create KWin settings group
        kwin_group = QGroupBox("KWin Integration")
        kwin_form = QFormLayout(kwin_group)

        # Create settings
        self.enable_shortcuts_checkbox = QCheckBox("Enable keyboard shortcuts")
        kwin_form.addRow("", self.enable_shortcuts_checkbox)

        self.enable_rules_checkbox = QCheckBox("Enable window rules")
        kwin_form.addRow("", self.enable_rules_checkbox)

        # Add KWin group to tab
        behavior_layout.addWidget(kwin_group)

        # Add spacer
        behavior_layout.addStretch()

        # Add behavior tab to tab widget
        tab_widget.addTab(behavior_tab, "Behavior")

        # Create debug tab
        debug_tab = QWidget()
        debug_layout = QVBoxLayout(debug_tab)

        # Create debug settings group
        debug_group = QGroupBox("Debug Settings")
        debug_form = QFormLayout(debug_group)

        # Create settings
        self.debug_checkbox = QCheckBox("Enable debug logging")
        debug_form.addRow("", self.debug_checkbox)

        # Add debug group to tab
        debug_layout.addWidget(debug_group)

        # Create logging group
        logging_group = QGroupBox("Logging")
        logging_form = QFormLayout(logging_group)

        # Create settings
        self.log_dir_edit = QLineEdit()
        self.log_dir_edit.setReadOnly(True)
        log_dir_layout = QHBoxLayout()
        log_dir_layout.addWidget(self.log_dir_edit)

        log_browse_button = QPushButton("Browse...")
        log_browse_button.clicked.connect(self._on_browse_log_dir)
        log_dir_layout.addWidget(log_browse_button)

        logging_form.addRow("Log directory:", log_dir_layout)

        view_logs_button = QPushButton("View Logs")
        view_logs_button.clicked.connect(self._on_view_logs)
        logging_form.addRow("", view_logs_button)

        # Add logging group to tab
        debug_layout.addWidget(logging_group)

        # Add spacer
        debug_layout.addStretch()

        # Add debug tab to tab widget
        tab_widget.addTab(debug_tab, "Debug")

        # Add tab widget to main layout
        main_layout.addWidget(tab_widget)

        # Create button box
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.Apply).clicked.connect(self._apply_settings)

        # Add button box to main layout
        main_layout.addWidget(button_box)

    def _store_original_settings(self):
        """Store the original settings for comparison."""
        # General settings
        self.original_settings["start_minimized"] = self.config_manager.get_setting("general", "start_minimized", False)
        self.original_settings["autostart"] = self.config_manager.get_setting("general", "autostart", False)
        self.original_settings["default_script_dir"] = self.config_manager.get_setting("general", "default_script_dir",
                                                                                       str(os.path.expanduser(
                                                                                           "~/.local/bin")))

        # Appearance settings
        self.original_settings["theme"] = self.config_manager.get_setting("appearance", "theme", "system")
        self.original_settings["icon_size"] = self.config_manager.get_setting("appearance", "icon_size", 32)

        # Behavior settings
        self.original_settings["confirm_delete"] = self.config_manager.get_setting("behavior", "confirm_delete", True)
        self.original_settings["auto_refresh"] = self.config_manager.get_setting("behavior", "auto_refresh", True)
        self.original_settings["refresh_interval"] = self.config_manager.get_setting("behavior", "refresh_interval", 5)
        self.original_settings["minimize_to_tray"] = self.config_manager.get_setting("behavior", "minimize_to_tray",
                                                                                     True)
        self.original_settings["notifications"] = self.config_manager.get_setting("behavior", "notifications", True)

        # KWin settings
        self.original_settings["enable_shortcuts"] = self.config_manager.get_setting("kwin", "enable_shortcuts", True)
        self.original_settings["enable_rules"] = self.config_manager.get_setting("kwin", "enable_rules", True)

        # Debug settings
        self.original_settings["debug"] = self.config_manager.get_setting("general", "debug", False)
        self.original_settings["log_dir"] = self.config_manager.get_setting("general", "log_dir",
                                                                            str(os.path.expanduser(
                                                                                "~/.config/toggleman/logs")))

    def _load_settings(self):
        """Load settings into the UI."""
        # General settings
        self.start_minimized_checkbox.setChecked(self.original_settings["start_minimized"])
        self.autostart_checkbox.setChecked(self.original_settings["autostart"])
        self.script_dir_edit.setText(self.original_settings["default_script_dir"])

        # Appearance settings
        theme_index = {"system": 0, "light": 1, "dark": 2}.get(self.original_settings["theme"].lower(), 0)
        self.theme_combo.setCurrentIndex(theme_index)
        self.icon_size_spin.setValue(self.original_settings["icon_size"])

        # Behavior settings
        self.confirm_delete_checkbox.setChecked(self.original_settings["confirm_delete"])
        self.auto_refresh_checkbox.setChecked(self.original_settings["auto_refresh"])
        self.refresh_interval_spin.setValue(self.original_settings["refresh_interval"])
        self.minimize_to_tray_checkbox.setChecked(self.original_settings["minimize_to_tray"])
        self.notifications_checkbox.setChecked(self.original_settings["notifications"])

        # KWin settings
        self.enable_shortcuts_checkbox.setChecked(self.original_settings["enable_shortcuts"])
        self.enable_rules_checkbox.setChecked(self.original_settings["enable_rules"])

        # Debug settings
        self.debug_checkbox.setChecked(self.original_settings["debug"])
        self.log_dir_edit.setText(self.original_settings["log_dir"])

    def _get_current_settings(self) -> Dict[str, Any]:
        """Get the current settings from the UI.

        Returns:
            A dictionary of current settings
        """
        # Create settings dictionary
        settings = {}

        # General settings
        settings["start_minimized"] = self.start_minimized_checkbox.isChecked()
        settings["autostart"] = self.autostart_checkbox.isChecked()
        settings["default_script_dir"] = self.script_dir_edit.text()

        # Appearance settings
        theme_index = self.theme_combo.currentIndex()
        settings["theme"] = ["system", "light", "dark"][theme_index]
        settings["icon_size"] = self.icon_size_spin.value()

        # Behavior settings
        settings["confirm_delete"] = self.confirm_delete_checkbox.isChecked()
        settings["auto_refresh"] = self.auto_refresh_checkbox.isChecked()
        settings["refresh_interval"] = self.refresh_interval_spin.value()
        settings["minimize_to_tray"] = self.minimize_to_tray_checkbox.isChecked()
        settings["notifications"] = self.notifications_checkbox.isChecked()

        # KWin settings
        settings["enable_shortcuts"] = self.enable_shortcuts_checkbox.isChecked()
        settings["enable_rules"] = self.enable_rules_checkbox.isChecked()

        # Debug settings
        settings["debug"] = self.debug_checkbox.isChecked()
        settings["log_dir"] = self.log_dir_edit.text()

        return settings

    def _apply_settings(self):
        """Apply the current settings."""
        # Get current settings
        current_settings = self._get_current_settings()

        # Find changed settings
        self.changed_settings = {}
        for key, value in current_settings.items():
            if value != self.original_settings.get(key):
                self.changed_settings[key] = value

        # Apply changed settings
        if self.changed_settings:
            # Update config manager
            for key, value in self.changed_settings.items():
                # Determine which section the setting belongs to
                if key in ["start_minimized", "autostart", "default_script_dir", "debug", "log_dir"]:
                    section = "general"
                elif key in ["theme", "icon_size"]:
                    section = "appearance"
                elif key in ["confirm_delete", "auto_refresh", "refresh_interval", "minimize_to_tray", "notifications"]:
                    section = "behavior"
                elif key in ["enable_shortcuts", "enable_rules"]:
                    section = "kwin"
                else:
                    logger.warning(f"Unknown setting: {key}")
                    continue

                # Update the setting
                self.config_manager.set_setting(section, key, value)

            # Save the config
            self.config_manager.save_config()

            # Handle special cases
            if "debug" in self.changed_settings:
                # Update debug mode
                set_debug_mode(self.changed_settings["debug"])

            if "autostart" in self.changed_settings:
                # Update autostart
                self._update_autostart(self.changed_settings["autostart"])

            # Update original settings
            self.original_settings.update(self.changed_settings)
            self.changed_settings = {}

            # Show success message
            QMessageBox.information(self, "Settings Applied", "Settings have been applied successfully.")

    def _update_autostart(self, enabled: bool):
        """Update autostart setting.

        Args:
            enabled: Whether to enable autostart
        """
        # Get autostart file path
        autostart_dir = os.path.expanduser("~/.config/autostart")
        autostart_file = os.path.join(autostart_dir, "toggleman.desktop")

        # Create or remove autostart entry
        if enabled:
            # Ensure directory exists
            os.makedirs(autostart_dir, exist_ok=True)

            # Copy desktop file from system
            system_desktop_file = "/usr/share/applications/toggleman.desktop"
            if os.path.exists(system_desktop_file):
                import shutil
                shutil.copy2(system_desktop_file, autostart_file)
            else:
                # Create desktop file manually
                with open(autostart_file, 'w') as f:
                    f.write("""[Desktop Entry]
Version=1.0
Type=Application
Name=Toggleman
Comment=Manager for application toggle scripts
Exec=toggleman --tray
Icon=toggleman
Terminal=false
Categories=Utility;System;
StartupNotify=true
X-GNOME-Autostart-enabled=true
""")
        else:
            # Remove autostart file if it exists
            if os.path.exists(autostart_file):
                os.remove(autostart_file)

    def _on_browse_script_dir(self):
        """Handle browsing for script directory."""
        # Open directory dialog
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Default Script Directory",
            self.script_dir_edit.text(),
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )

        if directory:
            self.script_dir_edit.setText(directory)

    def _on_browse_log_dir(self):
        """Handle browsing for log directory."""
        # Open directory dialog
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Log Directory",
            self.log_dir_edit.text(),
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )

        if directory:
            self.log_dir_edit.setText(directory)

    def _on_view_logs(self):
        """Handle viewing logs."""
        # Check if log directory exists
        log_dir = self.log_dir_edit.text()
        if not os.path.exists(log_dir):
            QMessageBox.warning(self, "Log Directory Not Found", "Log directory not found or not yet created.")
            return

        # Open log directory in file manager
        from PyQt5.QtGui import QDesktopServices
        from PyQt5.QtCore import QUrl

        QDesktopServices.openUrl(QUrl.fromLocalFile(log_dir))

    def accept(self):
        """Handle dialog acceptance."""
        # Apply settings
        self._apply_settings()

        # Accept dialog
        super().accept()