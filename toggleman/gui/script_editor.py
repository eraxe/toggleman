"""
Script editor dialog for Toggleman application.

This module provides a dialog for creating and editing toggle scripts.
"""

import os
import sys
import subprocess
from typing import Dict, List, Optional, Any, Tuple

from PyQt5.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QPushButton, QLabel, QCheckBox, QLineEdit, QTabWidget, QFileDialog,
    QSpinBox, QComboBox, QDialogButtonBox, QSizePolicy, QMessageBox,
    QTextEdit, QApplication, QToolButton, QAction
)
from PyQt5.QtGui import QIcon, QFont, QTextOption
from PyQt5.QtCore import Qt, QSize, pyqtSignal, pyqtSlot

from toggleman.core.config import ConfigManager
from toggleman.core.toggle_manager import ToggleManager
from toggleman.core.debug import get_logger
from toggleman.core.web_app_detector import WebAppDetector, WebApp
from toggleman.gui.web_app_selector import WebAppSelectorDialog
from toggleman.gui.icon_selector import IconSelectorDialog

logger = get_logger(__name__)


class ScriptEditorDialog(QDialog):
    """Dialog for creating and editing toggle scripts."""

    def __init__(self, config_manager: ConfigManager, script_name: Optional[str] = None, parent=None):
        """Initialize the script editor dialog.

        Args:
            config_manager: The configuration manager instance
            script_name: Optional name of script to edit (None for new script)
            parent: The parent widget
        """
        super().__init__(parent)

        self.config_manager = config_manager
        self.toggle_manager = ToggleManager(config_manager)
        self.script_name = script_name
        self.editing_mode = script_name is not None

        # Set up the UI
        self._setup_ui()

        # Load script data if editing
        if self.editing_mode:
            self._load_script_data()

        logger.debug(f"Script editor dialog initialized (editing: {self.editing_mode})")

    def _setup_ui(self):
        """Set up the dialog UI."""
        # Dialog properties
        self.setWindowTitle("Edit Toggle Script" if self.editing_mode else "New Toggle Script")
        self.setWindowIcon(QIcon.fromTheme("document-edit" if self.editing_mode else "document-new"))
        self.resize(600, 500)

        # Create main layout
        main_layout = QVBoxLayout(self)

        # Create tab widget
        tab_widget = QTabWidget()

        # Create basic settings tab
        basic_tab = QWidget()
        basic_layout = QVBoxLayout(basic_tab)

        # Create basic settings group
        basic_group = QGroupBox("Basic Settings")
        basic_form = QFormLayout(basic_group)

        # Add name field
        self.name_edit = QLineEdit()
        if self.editing_mode:
            self.name_edit.setText(self.script_name)
            self.name_edit.setReadOnly(True)
        basic_form.addRow("Name:", self.name_edit)

        # Add description field
        self.description_edit = QLineEdit()
        basic_form.addRow("Description:", self.description_edit)

        # Add application command field
        self.app_command_edit = QLineEdit()
        basic_form.addRow("Application Command:", self.app_command_edit)

        # Add application process field
        self.app_process_edit = QLineEdit()
        basic_form.addRow("Application Process Pattern:", self.app_process_edit)

        # Add window class field
        self.window_class_edit = QLineEdit()
        capture_layout = QHBoxLayout()
        capture_layout.addWidget(self.window_class_edit)

        capture_button = QPushButton("Capture")
        capture_button.clicked.connect(self._on_capture_window)
        capture_layout.addWidget(capture_button)

        # Add scan web apps button
        scan_button = QPushButton("Scan Web Apps...")
        scan_button.setIcon(QIcon.fromTheme("applications-internet"))
        scan_button.clicked.connect(self._on_scan_web_apps)
        capture_layout.addWidget(scan_button)

        basic_form.addRow("Window Class:", capture_layout)

        # Add icon field
        self.icon_path_edit = QLineEdit()
        self.icon_path_edit.setReadOnly(True)
        icon_layout = QHBoxLayout()
        icon_layout.addWidget(self.icon_path_edit)

        icon_button = QPushButton("Choose...")
        icon_button.clicked.connect(self._on_choose_icon)
        icon_layout.addWidget(icon_button)

        basic_form.addRow("Icon:", icon_layout)

        # Add basic group to layout
        basic_layout.addWidget(basic_group)

        # Create options group
        options_group = QGroupBox("Options")
        options_form = QFormLayout(options_group)

        # Add options
        self.notifications_checkbox = QCheckBox("Show notifications")
        self.notifications_checkbox.setChecked(True)
        options_form.addRow("", self.notifications_checkbox)

        self.debug_checkbox = QCheckBox("Enable debug logging")
        options_form.addRow("", self.debug_checkbox)

        # Add options group to layout
        basic_layout.addWidget(options_group)

        # Add spacer
        basic_layout.addStretch()

        # Add basic tab to tab widget
        tab_widget.addTab(basic_tab, "Basic")

        # Create advanced settings tab
        advanced_tab = QWidget()
        advanced_layout = QVBoxLayout(advanced_tab)

        # Create Chrome app settings group
        chrome_group = QGroupBox("Chrome Web App Settings")
        chrome_form = QFormLayout(chrome_group)

        # Add Chrome executable field
        self.chrome_exec_edit = QLineEdit()
        chrome_exec_layout = QHBoxLayout()
        chrome_exec_layout.addWidget(self.chrome_exec_edit)

        chrome_exec_button = QPushButton("Browse...")
        chrome_exec_button.clicked.connect(self._on_browse_chrome_exec)
        chrome_exec_layout.addWidget(chrome_exec_button)

        chrome_form.addRow("Chrome Executable:", chrome_exec_layout)

        # Add Chrome profile field
        self.chrome_profile_edit = QLineEdit()
        self.chrome_profile_edit.setPlaceholderText("Default")
        chrome_form.addRow("Chrome Profile:", self.chrome_profile_edit)

        # Add Chrome app ID field
        self.app_id_edit = QLineEdit()
        chrome_form.addRow("App ID:", self.app_id_edit)

        chrome_help_label = QLabel(
            "These settings are only needed for Chrome Web Apps.\nFor other applications, you can leave them empty.")
        chrome_help_label.setWordWrap(True)
        chrome_form.addRow("", chrome_help_label)

        # Add Chrome group to layout
        advanced_layout.addWidget(chrome_group)

        # Create output group
        output_group = QGroupBox("Output Settings")
        output_form = QFormLayout(output_group)

        # Add script path field
        self.script_path_edit = QLineEdit()
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.script_path_edit)

        path_button = QPushButton("Browse...")
        path_button.clicked.connect(self._on_browse_script_path)
        path_layout.addWidget(path_button)

        output_form.addRow("Script Path:", path_layout)

        # Add tray name field
        self.tray_name_edit = QLineEdit()
        output_form.addRow("Tray Name:", self.tray_name_edit)

        # Add output group to layout
        advanced_layout.addWidget(output_group)

        # Add spacer
        advanced_layout.addStretch()

        # Add advanced tab to tab widget
        tab_widget.addTab(advanced_tab, "Advanced")

        # Create test tab
        test_tab = QWidget()
        test_layout = QVBoxLayout(test_tab)

        # Create test group
        test_group = QGroupBox("Test Toggle Script")
        test_group_layout = QVBoxLayout(test_group)

        # Add test button
        test_button = QPushButton("Test Script")
        test_button.clicked.connect(self._on_test_script)
        test_group_layout.addWidget(test_button)

        # Add output label
        test_output_label = QLabel("Test Output:")
        test_group_layout.addWidget(test_output_label)

        # Add output text edit
        self.test_output_edit = QTextEdit()
        self.test_output_edit.setReadOnly(True)
        self.test_output_edit.setFont(QFont("Monospace", 10))
        self.test_output_edit.setWordWrapMode(QTextOption.NoWrap)
        test_group_layout.addWidget(self.test_output_edit)

        # Add test group to layout
        test_layout.addWidget(test_group)

        # Add help text
        help_label = QLabel(
            "Testing allows you to verify that your toggle script works correctly. "
            "The test will run the script and show the output."
        )
        help_label.setWordWrap(True)
        test_layout.addWidget(help_label)

        # Add test tab to tab widget
        tab_widget.addTab(test_tab, "Test")

        # Add tab widget to main layout
        main_layout.addWidget(tab_widget)

        # Create button box
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        # Add button box to main layout
        main_layout.addWidget(button_box)

    def _load_script_data(self):
        """Load script data when editing an existing script."""
        # Get script configuration
        script_config = self.config_manager.get_script(self.script_name)
        if not script_config:
            logger.error(f"Script configuration not found for {self.script_name}")
            QMessageBox.critical(self, "Error", f"Script configuration not found for {self.script_name}")
            self.reject()
            return

        # Load basic settings
        self.description_edit.setText(script_config.get("description", ""))
        self.app_command_edit.setText(script_config.get("app_command", ""))
        self.app_process_edit.setText(script_config.get("app_process", ""))
        self.window_class_edit.setText(script_config.get("window_class", ""))
        self.icon_path_edit.setText(script_config.get("icon_path", ""))

        # Load options
        self.notifications_checkbox.setChecked(script_config.get("notifications", True))
        self.debug_checkbox.setChecked(script_config.get("debug", False))

        # Load Chrome app settings
        self.chrome_exec_edit.setText(script_config.get("chrome_exec", ""))
        self.chrome_profile_edit.setText(script_config.get("chrome_profile", ""))
        self.app_id_edit.setText(script_config.get("app_id", ""))

        # Load output settings
        self.script_path_edit.setText(script_config.get("script_path", ""))
        self.tray_name_edit.setText(script_config.get("tray_name", ""))

    def _get_script_data(self) -> Dict[str, Any]:
        """Get script data from the UI.

        Returns:
            A dictionary of script data
        """
        # Create script data dictionary
        script_data = {}

        # Add basic settings
        script_data["name"] = self.name_edit.text()
        script_data["description"] = self.description_edit.text()
        script_data["app_command"] = self.app_command_edit.text()
        script_data["app_process"] = self.app_process_edit.text()
        script_data["window_class"] = self.window_class_edit.text()
        script_data["icon_path"] = self.icon_path_edit.text()

        # Add options
        script_data["notifications"] = self.notifications_checkbox.isChecked()
        script_data["debug"] = self.debug_checkbox.isChecked()

        # Add Chrome app settings
        script_data["chrome_exec"] = self.chrome_exec_edit.text()
        script_data["chrome_profile"] = self.chrome_profile_edit.text()
        script_data["app_id"] = self.app_id_edit.text()

        # Add output settings
        script_data["script_path"] = self.script_path_edit.text()
        script_data["tray_name"] = self.tray_name_edit.text() or f"{script_data['name']} Toggle"

        return script_data

    def _validate_script_data(self, script_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate script data.

        Args:
            script_data: The script data to validate

        Returns:
            Tuple of (valid, error_message)
        """
        # Check if name is provided (always required)
        if not script_data["name"]:
            return False, "Name is required"

        # Check name format (only allow alphanumeric, dash, underscore)
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', script_data["name"]):
            return False, "Name can only contain letters, numbers, dashes, and underscores"

        # Check if name already exists (only if creating new script)
        if not self.editing_mode and self.config_manager.get_script(script_data["name"]):
            return False, f"A toggle script with the name '{script_data['name']}' already exists"

        # Check if this is a draft (missing required fields)
        is_draft = not script_data["app_command"] or not script_data["window_class"]
        script_data["is_draft"] = is_draft

        return True, ""

    def _on_capture_window(self):
        """Handle capturing a window to get its class."""
        # Show instructions
        QMessageBox.information(
            self,
            "Capture Window",
            "Click OK, then click on the window you want to toggle. "
            "The window class will be automatically filled in."
        )

        # Hide this dialog
        self.hide()

        # Wait for a moment to ensure dialog is hidden
        QApplication.processEvents()

        try:
            # Use xprop to capture window class
            import subprocess
            process = subprocess.Popen(
                ["xprop", "WM_CLASS"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            stdout, stderr = process.communicate()

            if process.returncode == 0 and stdout:
                # Parse window class
                import re
                match = re.search(r'WM_CLASS\(\w+\) = "([^"]+)", "([^"]+)"', stdout)

                if match:
                    # Get the second class (usually more specific)
                    window_class = match.group(2)

                    # Set window class
                    self.window_class_edit.setText(window_class)
                else:
                    QMessageBox.warning(self, "Capture Failed", "Failed to parse window class.")
            else:
                QMessageBox.warning(self, "Capture Failed", "Failed to capture window class.")

        except Exception as e:
            logger.error(f"Error capturing window: {e}")
            QMessageBox.critical(self, "Error", f"Error capturing window: {str(e)}")

        finally:
            # Show this dialog again
            self.show()

    def _on_scan_web_apps(self):
        """Handle scanning for web apps."""
        # Show scanning dialog
        dialog = WebAppSelectorDialog(parent=self)

        if dialog.exec_() == QDialog.Accepted:
            # Get selected web app
            web_app = dialog.get_selected_web_app()
            if not web_app:
                return

            # Populate fields with web app data
            self.name_edit.setText(web_app.name if not self.editing_mode else self.name_edit.text())
            self.description_edit.setText(f"Web app toggle for {web_app.name}")

            # Set application command based on browser
            if web_app.browser in ["chrome", "chromium", "brave", "edge", "opera", "vivaldi"]:
                # For Chrome-like browsers, use the app ID
                self.chrome_exec_edit.setText(web_app.browser_path)
                self.chrome_profile_edit.setText(web_app.profile)
                self.app_id_edit.setText(web_app.app_id)

                # Set app command to use the browser with app-id
                self.app_command_edit.setText(f"{web_app.browser_path} --profile-directory=\"{web_app.profile}\" --app-id={web_app.app_id}")

                # Set app process pattern
                self.app_process_edit.setText(f"{os.path.basename(web_app.browser_path)}.*--app-id={web_app.app_id}")

            elif web_app.browser in ["firefox", "librewolf"]:
                # For Firefox, use the URL directly
                firefox_app_cmd = f"{web_app.browser_path} -P \"{web_app.profile}\" --new-window {web_app.url}"
                self.app_command_edit.setText(firefox_app_cmd)

                # Set app process pattern
                self.app_process_edit.setText(f"{os.path.basename(web_app.browser_path)}.*{web_app.profile}.*{web_app.url}")

            # Set window class
            self.window_class_edit.setText(web_app.window_class)

            # Set icon path if available
            if web_app.icon_path and os.path.exists(web_app.icon_path):
                self.icon_path_edit.setText(web_app.icon_path)

            # Set script path if empty
            if not self.script_path_edit.text():
                default_dir = self.config_manager.get_setting("general", "default_script_dir",
                                                           str(os.path.expanduser("~/.local/bin")))
                sanitized_name = "".join(c for c in web_app.name if c.isalnum() or c in ["-", "_"]).lower()
                self.script_path_edit.setText(os.path.join(default_dir, f"toggle-{sanitized_name}.sh"))

            # Set tray name if empty
            if not self.tray_name_edit.text():
                self.tray_name_edit.setText(f"{web_app.name} Toggle")

            QMessageBox.information(
                self,
                "Web App Detected",
                f"Successfully populated fields from {web_app.browser.capitalize()} web app: {web_app.name}"
            )

    def _on_choose_icon(self):
        """Handle choosing an icon."""
        # Show icon selector dialog
        dialog = IconSelectorDialog(self.icon_path_edit.text(), parent=self)

        if dialog.exec_() == QDialog.Accepted:
            # Set icon path
            self.icon_path_edit.setText(dialog.selected_icon)

    def _on_browse_chrome_exec(self):
        """Handle browsing for Chrome executable."""
        # Open file dialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Chrome Executable",
            "/opt/google/chrome" if os.path.exists("/opt/google/chrome") else "/usr/bin",
            "Executables (*.exe);;All Files (*)"
        )

        if file_path:
            self.chrome_exec_edit.setText(file_path)

    def _on_browse_script_path(self):
        """Handle browsing for script path."""
        # Get default directory
        default_dir = self.config_manager.get_setting("general", "default_script_dir",
                                                      str(os.path.expanduser("~/.local/bin")))

        # Get suggested filename
        script_name = self.name_edit.text() or "toggle-script"
        suggested_path = os.path.join(default_dir, f"toggle-{script_name.lower()}.sh")

        # Open file dialog
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Select Script Path",
            suggested_path,
            "Shell Scripts (*.sh);;All Files (*)"
        )

        if file_path:
            self.script_path_edit.setText(file_path)

    def _on_test_script(self):
        """Handle testing the script."""
        # Clear output
        self.test_output_edit.clear()

        # Get script data
        script_data = self._get_script_data()

        # Validate script data
        valid, error = self._validate_script_data(script_data)
        if not valid:
            self.test_output_edit.setTextColor(Qt.red)
            self.test_output_edit.append(f"Error: {error}")
            return

        # Set temporary script name if creating new script
        script_name = self.script_name
        if not script_name:
            script_name = script_data["name"]

            # Save temporary script configuration
            self.config_manager.save_script(script_name, script_data)

        # Run test
        self.test_output_edit.setTextColor(Qt.blue)
        self.test_output_edit.append("Running test...\n")

        success, message, details = self.toggle_manager.test_toggle(script_name)

        # Show test results
        self.test_output_edit.setTextColor(Qt.green if success else Qt.red)
        self.test_output_edit.append(f"Test {'succeeded' if success else 'failed'}: {message}\n")

        # Show stdout
        self.test_output_edit.setTextColor(Qt.black)
        self.test_output_edit.append("--- Standard Output ---")
        self.test_output_edit.append(details.get("stdout", ""))

        # Show stderr if any
        if details.get("stderr"):
            self.test_output_edit.setTextColor(Qt.red)
            self.test_output_edit.append("\n--- Error Output ---")
            self.test_output_edit.append(details.get("stderr", ""))

        # Remove temporary script configuration if creating new script
        if not self.script_name:
            self.config_manager.delete_script(script_name)

    def accept(self):
        """Handle dialog acceptance."""
        # Get script data
        script_data = self._get_script_data()

        # Validate script data
        valid, error = self._validate_script_data(script_data)
        if not valid:
            QMessageBox.critical(self, "Validation Error", error)
            return

        # Create default paths if not specified
        if not script_data["script_path"]:
            # Get default directory
            default_dir = self.config_manager.get_setting("general", "default_script_dir",
                                                          str(os.path.expanduser("~/.local/bin")))

            # Set script path
            script_data["script_path"] = os.path.join(default_dir, f"toggle-{script_data['name'].lower()}.sh")

        # Create or update toggle script
        if self.editing_mode:
            success, message = self.toggle_manager.update_toggle(self.script_name, script_data)
        else:
            success, message = self.toggle_manager.create_toggle(script_data["name"], script_data)

        if success:
            # Accept dialog
            super().accept()
        else:
            # Show error message
            QMessageBox.critical(self, "Error",
                                 f"Failed to {'update' if self.editing_mode else 'create'} toggle script: {message}")