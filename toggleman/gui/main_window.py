"""
Main window for Toggleman application.

This module provides the main GUI window for managing toggle scripts.
"""

import os
import sys
import stat
from typing import Dict, List, Optional, Any, Tuple

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QAction, QMenu, QMenuBar, QToolBar, QStatusBar,
    QSystemTrayIcon, QStyle, QDialog, QMessageBox, QFileDialog, QSplitter,
    QTabWidget, QTextEdit, QSizePolicy, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QGroupBox, QCheckBox, QFrame, QComboBox,
    QApplication, QInputDialog
)
from PyQt5.QtGui import QIcon, QPixmap, QFont, QDesktopServices, QColor
from PyQt5.QtCore import Qt, QSize, QTimer, QUrl, pyqtSignal, pyqtSlot

from toggleman.core.config import ConfigManager
from toggleman.core.toggle_manager import ToggleManager
from toggleman.core.kwin import KWinManager
from toggleman.core.debug import get_logger, get_log_file
from toggleman.gui.settings_dialog import SettingsDialog
from toggleman.gui.script_editor import ScriptEditorDialog

logger = get_logger(__name__)


class MainWindow(QMainWindow):
    """Main window for the Toggleman application."""

    def __init__(self, config_manager: ConfigManager, start_minimized: bool = False):
        """Initialize the main window.

        Args:
            config_manager: The configuration manager instance
            start_minimized: Whether to start minimized to system tray
        """
        super().__init__()

        self.config_manager = config_manager
        self.toggle_manager = ToggleManager(config_manager)
        self.kwin_manager = KWinManager(config_manager)

        self.scripts_table = None
        self.status_bar = None
        self.refresh_timer = None
        self.tray_icon = None

        # Set up the UI
        self._setup_ui()

        # Create tray icon
        self._setup_tray_icon()

        # Load toggle scripts
        self._load_scripts()

        # Set up auto refresh if enabled
        auto_refresh = self.config_manager.get_setting("behavior", "auto_refresh", True)
        if auto_refresh:
            self._setup_refresh_timer()

        # Start minimized if requested
        if start_minimized:
            self.hide()

        logger.info("Main window initialized")

    def _setup_ui(self):
        """Set up the main window UI."""
        # Window properties
        self.setWindowTitle("Toggleman")
        self.setWindowIcon(self._get_app_icon())
        self.resize(800, 600)

        # Create central widget and layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)

        # Create toolbar
        toolbar = QToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Add actions to toolbar
        new_action = QAction(self.style().standardIcon(QStyle.SP_FileIcon), "New Toggle", self)
        new_action.triggered.connect(self._on_new_script)
        toolbar.addAction(new_action)

        edit_action = QAction(self.style().standardIcon(QStyle.SP_FileDialogDetailedView), "Edit Toggle", self)
        edit_action.triggered.connect(self._on_edit_script)
        toolbar.addAction(edit_action)

        duplicate_action = QAction(self.style().standardIcon(QStyle.SP_FileLinkIcon), "Duplicate Toggle", self)
        duplicate_action.triggered.connect(self._on_duplicate_script)
        toolbar.addAction(duplicate_action)

        remove_action = QAction(self.style().standardIcon(QStyle.SP_TrashIcon), "Remove Toggle", self)
        remove_action.triggered.connect(self._on_remove_script)
        toolbar.addAction(remove_action)

        toolbar.addSeparator()

        run_action = QAction(self.style().standardIcon(QStyle.SP_MediaPlay), "Run Toggle", self)
        run_action.triggered.connect(self._on_run_script)
        toolbar.addAction(run_action)

        toolbar.addSeparator()

        refresh_action = QAction(self.style().standardIcon(QStyle.SP_BrowserReload), "Refresh", self)
        refresh_action.triggered.connect(self._load_scripts)
        toolbar.addAction(refresh_action)

        settings_action = QAction(self.style().standardIcon(QStyle.SP_FileDialogInfoView), "Settings", self)
        settings_action.triggered.connect(self._on_settings)
        toolbar.addAction(settings_action)

        # Create scripts table
        self.scripts_table = QTableWidget(0, 4)  # Rows, Columns
        self.scripts_table.setHorizontalHeaderLabels(["Name", "Description", "Status", "Shortcut"])
        self.scripts_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.scripts_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.scripts_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.scripts_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.scripts_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.scripts_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.scripts_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.scripts_table.setAlternatingRowColors(True)
        self.scripts_table.doubleClicked.connect(self._on_script_double_clicked)

        # Add context menu to scripts table
        self.scripts_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.scripts_table.customContextMenuRequested.connect(self._on_scripts_context_menu)

        # Add key press event handler
        self.scripts_table.keyPressEvent = self._scripts_key_press_event

        # Add scripts table to layout
        main_layout.addWidget(self.scripts_table)

        # Create action buttons
        action_layout = QHBoxLayout()

        run_button = QPushButton("Run Toggle")
        run_button.clicked.connect(self._on_run_script)
        action_layout.addWidget(run_button)

        edit_button = QPushButton("Edit Toggle")
        edit_button.clicked.connect(self._on_edit_script)
        action_layout.addWidget(edit_button)

        duplicate_button = QPushButton("Duplicate Toggle")
        duplicate_button.clicked.connect(self._on_duplicate_script)
        action_layout.addWidget(duplicate_button)

        shortcut_button = QPushButton("Set Shortcut")
        shortcut_button.clicked.connect(self._on_set_shortcut)
        action_layout.addWidget(shortcut_button)

        rule_button = QPushButton("Set Window Rule")
        rule_button.clicked.connect(self._on_set_window_rule)
        action_layout.addWidget(rule_button)

        main_layout.addLayout(action_layout)

        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        # Set central widget
        self.setCentralWidget(central_widget)

        # Create menus
        self._create_menus()

    def _create_menus(self):
        """Create the application menu bars."""
        # Create menu bar
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("&File")

        new_action = QAction("&New Toggle", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._on_new_script)
        file_menu.addAction(new_action)

        import_action = QAction("&Import Toggle Script", self)
        import_action.triggered.connect(self._on_import_script)
        file_menu.addAction(import_action)

        export_action = QAction("&Export Toggle Script", self)
        export_action.triggered.connect(self._on_export_script)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        settings_action = QAction("&Settings", self)
        settings_action.triggered.connect(self._on_settings)
        file_menu.addAction(settings_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.quit_application)
        file_menu.addAction(exit_action)

        # Toggle menu
        toggle_menu = menu_bar.addMenu("&Toggle")

        run_action = QAction("&Run Toggle", self)
        run_action.triggered.connect(self._on_run_script)
        toggle_menu.addAction(run_action)

        edit_action = QAction("&Edit Toggle", self)
        edit_action.triggered.connect(self._on_edit_script)
        toggle_menu.addAction(edit_action)

        duplicate_action = QAction("Du&plicate Toggle", self)
        duplicate_action.triggered.connect(self._on_duplicate_script)
        toggle_menu.addAction(duplicate_action)

        remove_action = QAction("&Remove Toggle", self)
        remove_action.triggered.connect(self._on_remove_script)
        toggle_menu.addAction(remove_action)

        toggle_menu.addSeparator()

        shortcut_action = QAction("Set &Keyboard Shortcut", self)
        shortcut_action.triggered.connect(self._on_set_shortcut)
        toggle_menu.addAction(shortcut_action)

        rule_action = QAction("Set Window &Rule", self)
        rule_action.triggered.connect(self._on_set_window_rule)
        toggle_menu.addAction(rule_action)

        # View menu
        view_menu = menu_bar.addMenu("&View")

        refresh_action = QAction("&Refresh", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self._load_scripts)
        view_menu.addAction(refresh_action)

        # Help menu
        help_menu = menu_bar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

        log_action = QAction("View &Log", self)
        log_action.triggered.connect(self._on_view_log)
        help_menu.addAction(log_action)

    def _setup_tray_icon(self):
        """Set up the system tray icon."""
        # Create tray icon
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self._get_app_icon())
        self.tray_icon.setToolTip("Toggleman")

        # Create tray icon menu
        tray_menu = QMenu()

        # Add scripts to menu
        for name in self.config_manager.get_all_scripts().keys():
            script_action = QAction(name, self)
            script_action.setIcon(self._get_script_icon(name))  # Set script-specific icon
            script_action.triggered.connect(lambda checked, n=name: self._on_tray_run_script(n))
            tray_menu.addAction(script_action)

        if self.config_manager.get_all_scripts():
            tray_menu.addSeparator()

        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)

        hide_action = QAction("Hide", self)
        hide_action.triggered.connect(self.hide)
        tray_menu.addAction(hide_action)

        tray_menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(quit_action)

        # Set the tray icon menu
        self.tray_icon.setContextMenu(tray_menu)

        # Connect signal for tray icon activation
        self.tray_icon.activated.connect(self._on_tray_activated)

        # Show the tray icon
        self.tray_icon.show()

    def _setup_refresh_timer(self):
        """Set up the auto-refresh timer."""
        # Create timer
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._load_scripts)

        # Get refresh interval from settings (in seconds)
        refresh_interval = self.config_manager.get_setting("behavior", "refresh_interval", 5)

        # Start timer (convert seconds to milliseconds)
        self.refresh_timer.start(refresh_interval * 1000)

        logger.debug(f"Refresh timer started with interval: {refresh_interval} seconds")

    def _load_scripts(self):
        """Load and display toggle scripts while preserving selection."""
        # Get all scripts
        scripts = self.config_manager.get_all_scripts()

        # Get running toggles
        running_toggles = self.toggle_manager.get_running_toggles()

        # Store current selection
        current_selected_row = -1
        selected_rows = self.scripts_table.selectionModel().selectedRows()
        if selected_rows:
            current_selected_row = selected_rows[0].row()
            current_selected_name = self.scripts_table.item(current_selected_row, 0).text() if current_selected_row >= 0 else None
        else:
            current_selected_name = None

        # Block signals temporarily to prevent selection change signals
        self.scripts_table.blockSignals(True)

        # Get current row count
        current_row_count = self.scripts_table.rowCount()

        # Check if we have the same scripts as before
        if current_row_count == len(scripts):
            # Update existing rows instead of clearing and rebuilding
            for row, (name, config) in enumerate(scripts.items()):
                # Update name
                name_item = self.scripts_table.item(row, 0)
                if name_item and name_item.text() != name:
                    name_item.setText(name)
                    name_item.setIcon(self._get_script_icon(name))

                elif not name_item:
                    name_item = QTableWidgetItem(name)
                    name_item.setIcon(self._get_script_icon(name))
                    self.scripts_table.setItem(row, 0, name_item)

                # Update description
                desc_item = self.scripts_table.item(row, 1)
                desc_text = config.get("description", "")
                if desc_item and desc_item.text() != desc_text:
                    desc_item.setText(desc_text)
                elif not desc_item:
                    desc_item = QTableWidgetItem(desc_text)
                    self.scripts_table.setItem(row, 1, desc_item)

                # Update status
                is_draft = config.get("is_draft", False)
                if is_draft:
                    status = "Draft"
                    status_color = QColor("blue")
                elif name in running_toggles:
                    status = "Running"
                    status_color = QColor("green")
                else:
                    status = "Stopped"
                    status_color = QColor("red")

                status_item = self.scripts_table.item(row, 2)
                if status_item and status_item.text() != status:
                    status_item.setText(status)
                    status_item.setForeground(status_color)
                elif not status_item:
                    status_item = QTableWidgetItem(status)
                    status_item.setForeground(status_color)
                    status_item.setTextAlignment(Qt.AlignCenter)
                    self.scripts_table.setItem(row, 2, status_item)

                # Update shortcut
                shortcut = config.get("kwin_shortcut", "")
                shortcut_item = self.scripts_table.item(row, 3)
                if shortcut_item and shortcut_item.text() != shortcut:
                    shortcut_item.setText(shortcut)
                elif not shortcut_item:
                    shortcut_item = QTableWidgetItem(shortcut)
                    self.scripts_table.setItem(row, 3, shortcut_item)

                # Check if this was the selected script
                if name == current_selected_name:
                    current_selected_row = row
        else:
            # Scripts have changed, need to rebuild table
            self.scripts_table.setRowCount(0)

            # Add scripts to table
            for row, (name, config) in enumerate(scripts.items()):
                self.scripts_table.insertRow(row)

                # Name
                name_item = QTableWidgetItem(name)
                name_item.setIcon(self._get_script_icon(name))
                self.scripts_table.setItem(row, 0, name_item)

                # Description
                desc_item = QTableWidgetItem(config.get("description", ""))
                self.scripts_table.setItem(row, 1, desc_item)

                # Status
                is_draft = config.get("is_draft", False)
                if is_draft:
                    status = "Draft"
                    status_color = QColor("blue")
                elif name in running_toggles:
                    status = "Running"
                    status_color = QColor("green")
                else:
                    status = "Stopped"
                    status_color = QColor("red")

                status_item = QTableWidgetItem(status)
                status_item.setForeground(status_color)
                status_item.setTextAlignment(Qt.AlignCenter)
                self.scripts_table.setItem(row, 2, status_item)

                # Shortcut
                shortcut = config.get("kwin_shortcut", "")
                shortcut_item = QTableWidgetItem(shortcut)
                self.scripts_table.setItem(row, 3, shortcut_item)

                # Check if this was the selected script
                if name == current_selected_name:
                    current_selected_row = row

        # Update tray icon menu (similar approach to preserve the structure)
        self._update_tray_menu(scripts)

        # Update status bar
        count = len(scripts)
        running = len(running_toggles)
        self.status_bar.showMessage(f"{count} toggle scripts ({running} running)")

        # Restore selection if possible
        if current_selected_row >= 0 and current_selected_row < self.scripts_table.rowCount():
            self.scripts_table.selectRow(current_selected_row)

        # Unblock signals
        self.scripts_table.blockSignals(False)

    def _update_tray_menu(self, scripts):
        """Update the tray icon menu without recreating it."""
        if not self.tray_icon:
            return

        # Get existing menu
        tray_menu = self.tray_icon.contextMenu()
        if not tray_menu:
            # If no menu exists, create a new one
            self._setup_tray_icon()
            return

        # Clear the entire menu and rebuild from scratch
        tray_menu.clear()

        # Add scripts to menu
        for name in scripts.keys():
            script_action = QAction(name, self)
            script_action.setIcon(self._get_script_icon(name))
            script_action.triggered.connect(lambda checked, n=name: self._on_tray_run_script(n))
            tray_menu.addAction(script_action)

        # Add separator if there are scripts
        if scripts:
            tray_menu.addSeparator()

        # Add standard actions
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)

        hide_action = QAction("Hide", self)
        hide_action.triggered.connect(self.hide)
        tray_menu.addAction(hide_action)

        tray_menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(quit_action)

        # Re-set the menu
        self.tray_icon.setContextMenu(tray_menu)

    def _get_selected_script(self) -> Optional[str]:
        """Get the currently selected script name.

        Returns:
            The name of the selected script, or None if no script is selected
        """
        # Get selected row
        selected_rows = self.scripts_table.selectionModel().selectedRows()
        if not selected_rows:
            return None

        # Get row index
        row = selected_rows[0].row()

        # Get script name
        return self.scripts_table.item(row, 0).text()

    def _get_app_icon(self) -> QIcon:
        """Get the application icon.

        Returns:
            The application icon
        """
        # First check if there's a custom icon from settings
        custom_icon = self.config_manager.get_setting("appearance", "custom_icon_path", "")
        if custom_icon and os.path.exists(custom_icon):
            return QIcon(custom_icon)

        # Try to find the default icon
        icon_paths = [
            "/usr/share/icons/hicolor/128x128/apps/toggleman.png",
            "/usr/share/icons/hicolor/128x128/apps/toggleman.svg",
            "/opt/toggleman/icons/toggleman.svg",
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "icons", "toggleman.svg")
        ]

        for path in icon_paths:
            if os.path.exists(path):
                return QIcon(path)

        # Fallback to system icon
        return self.style().standardIcon(QStyle.SP_DesktopIcon)

    def _get_script_icon(self, script_name: str) -> QIcon:
        """Get the icon for a specific toggle script.

        Args:
            script_name: The name of the toggle script

        Returns:
            The script icon
        """
        # Get script configuration
        script_config = self.config_manager.get_script(script_name)
        if not script_config:
            return self._get_app_icon()

        # Get icon path from configuration
        icon_path = script_config.get("icon_path", "")
        if icon_path and os.path.exists(icon_path):
            return QIcon(icon_path)

        # If this is a Chrome app, try to get the Chrome app icon
        if script_config.get("chrome_exec") and script_config.get("app_id"):
            chrome_profile = script_config.get("chrome_profile", "Default")
            app_id = script_config.get("app_id")

            # Look for icon in Chrome app directory
            chrome_app_dir = os.path.expanduser(f"~/.config/google-chrome/{chrome_profile}/Web Applications")
            if os.path.exists(chrome_app_dir):
                import glob
                icon_files = glob.glob(f"{chrome_app_dir}/*{app_id}*/*.png")
                if icon_files:
                    # Use the first (probably largest) icon
                    return QIcon(icon_files[0])

        # Fallback to app icon
        return self._get_app_icon()

    def _on_new_script(self):
        """Handle creating a new toggle script."""
        # Open script editor dialog
        dialog = ScriptEditorDialog(self.config_manager, parent=self)

        if dialog.exec_() == QDialog.Accepted:
            # Reload scripts
            self._load_scripts()

            # Show success message
            self.status_bar.showMessage("Toggle script created successfully")

    def _on_edit_script(self):
        """Handle editing a toggle script."""
        # Get selected script
        script_name = self._get_selected_script()
        if not script_name:
            QMessageBox.warning(self, "No Selection", "Please select a toggle script to edit.")
            return

        # Open script editor dialog
        dialog = ScriptEditorDialog(self.config_manager, script_name, parent=self)

        if dialog.exec_() == QDialog.Accepted:
            # Reload scripts
            self._load_scripts()

            # Show success message
            self.status_bar.showMessage(f"Toggle script '{script_name}' updated successfully")

    def _on_duplicate_script(self):
        """Handle duplicating a toggle script."""
        # Get selected script
        script_name = self._get_selected_script()
        if not script_name:
            QMessageBox.warning(self, "No Selection", "Please select a toggle script to duplicate.")
            return

        # Ask for new name
        new_name, ok = QInputDialog.getText(
            self,
            "Duplicate Toggle Script",
            "Enter a name for the duplicate:",
            text=f"{script_name}_copy"
        )

        if not ok or not new_name:
            return

        # Duplicate the script
        success, message = self.toggle_manager.duplicate_toggle(script_name, new_name)

        if success:
            # Reload scripts
            self._load_scripts()

            # Show success message
            self.status_bar.showMessage(f"Toggle script '{script_name}' duplicated as '{new_name}'")
        else:
            # Show error message
            QMessageBox.critical(self, "Error", f"Failed to duplicate toggle script: {message}")

    def _on_remove_script(self):
        """Handle removing a toggle script."""
        # Get selected script
        script_name = self._get_selected_script()
        if not script_name:
            QMessageBox.warning(self, "No Selection", "Please select a toggle script to remove.")
            return

        # Confirm removal
        confirm = QMessageBox.question(
            self,
            "Confirm Removal",
            f"Are you sure you want to remove the toggle script '{script_name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if confirm != QMessageBox.Yes:
            return

        # Remove the script
        success, message = self.toggle_manager.delete_toggle(script_name)

        if success:
            # Reload scripts
            self._load_scripts()

            # Show success message
            self.status_bar.showMessage(f"Toggle script '{script_name}' removed successfully")
        else:
            # Show error message
            QMessageBox.critical(self, "Error", f"Failed to remove toggle script: {message}")

    def _on_run_script(self):
        """Handle running a toggle script."""
        # Get selected script
        script_name = self._get_selected_script()
        if not script_name:
            QMessageBox.warning(self, "No Selection", "Please select a toggle script to run.")
            return

        # Run the script
        success, message = self.toggle_manager.run_toggle(script_name)

        if success:
            # Show success message
            self.status_bar.showMessage(f"Running toggle script '{script_name}'")

            # Reload scripts after a delay
            QTimer.singleShot(1000, self._load_scripts)
        else:
            # Show error message
            QMessageBox.critical(self, "Error", f"Failed to run toggle script: {message}")

    def _on_set_shortcut(self):
        """Handle setting a keyboard shortcut for a toggle script."""
        # Get selected script
        script_name = self._get_selected_script()
        if not script_name:
            QMessageBox.warning(self, "No Selection", "Please select a toggle script to set a shortcut for.")
            return

        # Get current shortcut
        script_config = self.config_manager.get_script(script_name)
        current_shortcut = script_config.get("kwin_shortcut", "")

        # Ask for new shortcut
        shortcut, ok = QInputDialog.getText(
            self,
            "Set Keyboard Shortcut",
            "Enter the keyboard shortcut (e.g., Meta+Alt+C):",
            text=current_shortcut
        )

        if not ok or not shortcut:
            return

        # Set the shortcut
        success, message = self.kwin_manager.set_shortcut(script_name, shortcut)

        if success:
            # Reload scripts
            self._load_scripts()

            # Show information message
            QMessageBox.information(
                self,
                "Set Shortcut",
                message
            )
        else:
            # Show error message
            QMessageBox.critical(self, "Error", f"Failed to set shortcut: {message}")


    def _on_set_window_rule(self):
        """Handle setting a window rule for a toggle script."""
        # Get selected script
        script_name = self._get_selected_script()
        if not script_name:
            QMessageBox.warning(self, "No Selection", "Please select a toggle script to set a window rule for.")
            return

        # Open KWin window rules dialog
        success, message = self.kwin_manager.open_window_rules(script_name)

        if success:
            # Show information message
            QMessageBox.information(
                self,
                "Set Window Rule",
                message
            )
        else:
            # Show error message
            QMessageBox.critical(self, "Error", f"Failed to open window rules: {message}")

    def _on_import_script(self):
        """Handle importing a toggle script."""
        # Open file dialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Toggle Script",
            os.path.expanduser("~"),
            "Shell Scripts (*.sh)"
        )

        if not file_path:
            return

        # TODO: Implement importing script
        QMessageBox.information(self, "Not Implemented", "Import functionality is not yet implemented.")

    def _on_export_script(self):
        """Handle exporting a toggle script."""
        # Get selected script
        script_name = self._get_selected_script()
        if not script_name:
            QMessageBox.warning(self, "No Selection", "Please select a toggle script to export.")
            return

        # Open file dialog
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Toggle Script",
            os.path.expanduser(f"~/toggle-{script_name.lower()}.sh"),
            "Shell Scripts (*.sh)"
        )

        if not file_path:
            return

        # Export the script
        success, message = self.toggle_manager.export_toggle(script_name, file_path)

        if success:
            # Show success message
            self.status_bar.showMessage(f"Exported toggle script '{script_name}' to {file_path}")
        else:
            # Show error message
            QMessageBox.critical(self, "Error", f"Failed to export toggle script: {message}")

    def _on_settings(self):
        """Handle opening the settings dialog."""
        # Open settings dialog
        dialog = SettingsDialog(self.config_manager, parent=self)

        if dialog.exec_() == QDialog.Accepted:
            # Reload scripts
            self._load_scripts()

            # Update refresh timer if needed
            auto_refresh = self.config_manager.get_setting("behavior", "auto_refresh", True)
            refresh_interval = self.config_manager.get_setting("behavior", "refresh_interval", 5)

            if auto_refresh and not self.refresh_timer:
                self._setup_refresh_timer()
            elif auto_refresh and self.refresh_timer:
                # Update interval
                self.refresh_timer.setInterval(refresh_interval * 1000)
            elif not auto_refresh and self.refresh_timer:
                self.refresh_timer.stop()
                self.refresh_timer = None

            # Show success message
            self.status_bar.showMessage("Settings updated successfully")

    def _on_about(self):
        """Handle showing the about dialog."""
        # Show about message
        QMessageBox.about(
            self,
            "About Toggleman",
            "Toggleman 1.0.0\n\n"
            "A manager for application toggle scripts on KDE Wayland.\n\n"
            "Created by the Toggleman Team.\n\n"
            "Licensed under the GPL v3."
        )

    def _on_view_log(self):
        """Handle viewing the log file."""
        # Get log file path
        log_file = get_log_file()
        if not log_file or not os.path.exists(log_file):
            QMessageBox.warning(self, "Log File Not Found", "Log file not found or not yet created.")
            return

        # Open log file viewer
        #from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton

        dialog = QDialog(self)
        dialog.setWindowTitle("Log Viewer")
        dialog.resize(800, 600)

        layout = QVBoxLayout(dialog)

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setFont(QFont("Monospace", 10))

        try:
            with open(log_file, 'r') as f:
                text_edit.setText(f.read())
        except Exception as e:
            text_edit.setText(f"Error reading log file: {str(e)}")

        layout.addWidget(text_edit)

        button_layout = QHBoxLayout()

        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(lambda: self._refresh_log_view(text_edit, log_file))
        button_layout.addWidget(refresh_button)

        open_button = QPushButton("Open in Editor")
        open_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(log_file)))
        button_layout.addWidget(open_button)

        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

        dialog.exec_()

    def _refresh_log_view(self, text_edit: QTextEdit, log_file: str):
        """Refresh the log view.

        Args:
            text_edit: The text edit widget to update
            log_file: The path to the log file
        """
        try:
            with open(log_file, 'r') as f:
                text_edit.setText(f.read())
        except Exception as e:
            text_edit.setText(f"Error reading log file: {str(e)}")

    def _on_script_double_clicked(self, index):
        """Handle double-clicking a toggle script.

        Args:
            index: The index of the clicked item
        """
        # Run the toggle script
        script_name = self.scripts_table.item(index.row(), 0).text()

        if script_name:
            success, message = self.toggle_manager.run_toggle(script_name)

            if success:
                # Show success message
                self.status_bar.showMessage(f"Running toggle script '{script_name}'")

                # Reload scripts after a delay
                QTimer.singleShot(1000, self._load_scripts)
            else:
                # Show error message
                QMessageBox.critical(self, "Error", f"Failed to run toggle script: {message}")

    def _on_tray_activated(self, reason):
        """Handle tray icon activation.

        Args:
            reason: The reason for activation
        """
        if reason == QSystemTrayIcon.DoubleClick:
            # Show or hide window on double-click
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.activateWindow()

    def _on_tray_run_script(self, script_name: str):
        """Handle running a toggle script from the tray menu.

        Args:
            script_name: The name of the toggle script to run
        """
        if script_name:
            success, message = self.toggle_manager.run_toggle(script_name)

            if success:
                # Reload scripts after a delay
                QTimer.singleShot(1000, self._load_scripts)

    def _scripts_key_press_event(self, event):
        """Handle key press events in the scripts table.

        Args:
            event: The key press event
        """
        # Store the original event handler
        original_handler = self.scripts_table.keyPressEvent

        # Handle Enter/Return key to run the selected script
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            script_name = self._get_selected_script()
            if script_name:
                self._on_run_script()
                return

        # Handle Delete key to remove the selected script
        elif event.key() == Qt.Key_Delete:
            script_name = self._get_selected_script()
            if script_name:
                self._on_remove_script()
                return

        # Handle F2 key to edit the selected script
        elif event.key() == Qt.Key_F2:
            script_name = self._get_selected_script()
            if script_name:
                self._on_edit_script()
                return

        # Call the original event handler for other keys
        original_handler(event)

    def _on_scripts_context_menu(self, pos):
        """Show context menu for scripts table.

        Args:
            pos: The position where the context menu was requested
        """
        # Get the global position
        global_pos = self.scripts_table.viewport().mapToGlobal(pos)

        # Get the item at position
        item = self.scripts_table.itemAt(pos)
        if not item:
            return

        # Get the script name
        row = item.row()
        script_name = self.scripts_table.item(row, 0).text()

        # Create context menu
        menu = QMenu(self)

        # Add actions
        run_action = QAction("Run", self)
        run_action.triggered.connect(lambda: self._on_run_script())
        menu.addAction(run_action)

        edit_action = QAction("Edit", self)
        edit_action.triggered.connect(lambda: self._on_edit_script())
        menu.addAction(edit_action)

        duplicate_action = QAction("Duplicate", self)
        duplicate_action.triggered.connect(lambda: self._on_duplicate_script())
        menu.addAction(duplicate_action)

        shortcut_action = QAction("Set Shortcut", self)
        shortcut_action.triggered.connect(lambda: self._on_set_shortcut())
        menu.addAction(shortcut_action)

        rule_action = QAction("Set Window Rule", self)
        rule_action.triggered.connect(lambda: self._on_set_window_rule())
        menu.addAction(rule_action)

        menu.addSeparator()

        remove_action = QAction("Remove", self)
        remove_action.triggered.connect(lambda: self._on_remove_script())
        menu.addAction(remove_action)

        # Show menu
        menu.exec_(global_pos)

    def quit_application(self):
        """Completely quit the application regardless of tray settings."""
        # Clean up
        if self.refresh_timer:
            self.refresh_timer.stop()

        if self.tray_icon:
            self.tray_icon.hide()

        # Actually quit the application
        QApplication.quit()

    def closeEvent(self, event):
        """Handle window close event.

        Args:
            event: The close event
        """
        # Check if we should minimize to tray instead of closing
        minimize_to_tray = self.config_manager.get_setting("behavior", "minimize_to_tray", True)

        if minimize_to_tray and self.tray_icon and self.tray_icon.isVisible():
            # Hide window instead of closing
            event.ignore()
            self.hide()

            # Show notification
            self.tray_icon.showMessage(
                "Toggleman",
                "Toggleman is still running in the system tray.",
                QSystemTrayIcon.Information,
                2000
            )
        else:
            # Actually quit the application
            self.quit_application()