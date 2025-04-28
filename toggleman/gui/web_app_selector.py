"""
Web App Selector dialog for Toggleman.

This module provides a dialog for selecting web apps detected on the system.
"""

import os
from typing import List, Optional

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QSizePolicy, QDialogButtonBox,
    QApplication, QTabWidget, QWidget, QCheckBox, QRadioButton,
    QButtonGroup, QGroupBox, QTextEdit, QLineEdit, QStyle
)
from PyQt5.QtGui import QIcon, QPixmap, QFont
from PyQt5.QtCore import Qt, QSize

from toggleman.core.web_app_detector import WebAppDetector, WebApp
from toggleman.core.debug import get_logger

logger = get_logger(__name__)


class WebAppSelectorDialog(QDialog):
    """Dialog for selecting web apps detected on the system."""

    def __init__(self, parent=None):
        """Initialize the web app selector dialog.

        Args:
            parent: The parent widget
        """
        super().__init__(parent)

        self.detector = WebAppDetector()
        self.web_apps = []
        self.selected_app = None

        # Connect signals
        self.accepted.connect(self.on_accepted)

        # Set up the UI
        self._setup_ui()

        logger.debug("Web App Selector dialog initialized")

    def _setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Select Web App")
        self.setWindowIcon(QIcon.fromTheme("application-x-executable"))
        self.resize(800, 600)

        # Create layout
        main_layout = QVBoxLayout(self)

        # Create filter controls
        filter_layout = QHBoxLayout()

        # Browser filter
        self.browser_combo = QComboBox()
        self.browser_combo.addItem("All Browsers", "")
        self.browser_combo.addItem("Chrome", "chrome")
        self.browser_combo.addItem("Chromium", "chromium")
        self.browser_combo.addItem("Firefox", "firefox")
        self.browser_combo.addItem("Brave", "brave")
        self.browser_combo.addItem("Edge", "edge")
        self.browser_combo.addItem("Opera", "opera")
        self.browser_combo.addItem("Vivaldi", "vivaldi")
        self.browser_combo.currentIndexChanged.connect(self._apply_filters)

        filter_layout.addWidget(QLabel("Browser:"))
        filter_layout.addWidget(self.browser_combo)
        filter_layout.addSpacing(20)

        # Search filter
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search by name...")
        self.search_edit.textChanged.connect(self._apply_filters)

        filter_layout.addWidget(QLabel("Search:"))
        filter_layout.addWidget(self.search_edit)
        filter_layout.addStretch()

        # Refresh button
        refresh_button = QPushButton("Refresh")
        refresh_button.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        refresh_button.clicked.connect(self._refresh_web_apps)
        filter_layout.addWidget(refresh_button)

        main_layout.addLayout(filter_layout)

        # Create web apps table
        self.web_apps_table = QTableWidget(0, 4)  # Rows, Columns
        self.web_apps_table.setHorizontalHeaderLabels(["Name", "Browser", "Profile", "URL"])
        self.web_apps_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.web_apps_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.web_apps_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.web_apps_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.web_apps_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.web_apps_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.web_apps_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.web_apps_table.setAlternatingRowColors(True)
        self.web_apps_table.doubleClicked.connect(self._on_double_click)
        self.web_apps_table.setShowGrid(True)

        main_layout.addWidget(self.web_apps_table)

        # Create preview section
        preview_layout = QHBoxLayout()

        # Create app info group
        info_group = QGroupBox("Web App Information")
        info_form = QFormLayout(info_group)

        self.app_name_label = QLabel("")
        info_form.addRow("Name:", self.app_name_label)

        self.app_id_label = QLabel("")
        info_form.addRow("App ID:", self.app_id_label)

        self.app_browser_label = QLabel("")
        info_form.addRow("Browser:", self.app_browser_label)

        self.app_profile_label = QLabel("")
        info_form.addRow("Profile:", self.app_profile_label)

        self.app_url_label = QLabel("")
        self.app_url_label.setWordWrap(True)
        info_form.addRow("URL:", self.app_url_label)

        self.app_window_class_label = QLabel("")
        info_form.addRow("Window Class:", self.app_window_class_label)

        preview_layout.addWidget(info_group)

        # Create icon preview group
        icon_group = QGroupBox("Icon")
        icon_layout = QVBoxLayout(icon_group)

        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setMinimumSize(128, 128)
        icon_layout.addWidget(self.icon_label)

        preview_layout.addWidget(icon_group)

        main_layout.addLayout(preview_layout)

        # Create button box
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        main_layout.addWidget(button_box)

        # Load web apps
        self._refresh_web_apps()

    def _refresh_web_apps(self):
        """Refresh the list of web apps."""
        # Show "Loading..." message
        self.web_apps_table.setRowCount(1)
        self.web_apps_table.setSpan(0, 0, 1, 4)
        loading_item = QTableWidgetItem("Loading web apps, please wait...")
        loading_item.setTextAlignment(Qt.AlignCenter)
        self.web_apps_table.setItem(0, 0, loading_item)

        # Process events to update the UI
        QApplication.processEvents()

        # Clear preview
        self._clear_preview()

        # Get web apps
        self.web_apps = self.detector.get_all_web_apps()

        # Load web apps into table
        self._populate_table(self.web_apps)

    def _populate_table(self, web_apps):
        """Populate the table with web apps.

        Args:
            web_apps: List of WebApp objects
        """
        # Clear table
        self.web_apps_table.clearContents()
        self.web_apps_table.setRowCount(0)
        self.web_apps_table.clearSpans()

        if not web_apps:
            # Show "No web apps found" message
            self.web_apps_table.setRowCount(1)
            self.web_apps_table.setSpan(0, 0, 1, 4)
            no_apps_item = QTableWidgetItem("No web apps found. Click Refresh to try again.")
            no_apps_item.setTextAlignment(Qt.AlignCenter)
            self.web_apps_table.setItem(0, 0, no_apps_item)
            return

        # Add web apps to table
        for app in web_apps:
            row = self.web_apps_table.rowCount()
            self.web_apps_table.insertRow(row)

            # Name
            name_item = QTableWidgetItem(app.name)
            if app.icon_path and os.path.exists(app.icon_path):
                name_item.setIcon(QIcon(app.icon_path))
            self.web_apps_table.setItem(row, 0, name_item)

            # Browser
            browser_item = QTableWidgetItem(app.browser.capitalize())
            self.web_apps_table.setItem(row, 1, browser_item)

            # Profile
            profile_item = QTableWidgetItem(app.profile)
            self.web_apps_table.setItem(row, 2, profile_item)

            # URL
            url_item = QTableWidgetItem(app.url)
            self.web_apps_table.setItem(row, 3, url_item)

        # Resize columns
        self.web_apps_table.resizeColumnsToContents()

    def _apply_filters(self):
        """Apply filters to the web apps list."""
        # Get filter values
        browser_filter = self.browser_combo.currentData()
        search_filter = self.search_edit.text().lower()

        # Filter web apps
        filtered_apps = []
        for app in self.web_apps:
            # Apply browser filter
            if browser_filter and app.browser != browser_filter:
                continue

            # Apply search filter
            if search_filter and search_filter not in app.name.lower():
                continue

            filtered_apps.append(app)

        # Update table
        self._populate_table(filtered_apps)

    def _on_double_click(self, index):
        """Handle double-click on a web app.

        Args:
            index: The index of the clicked item
        """
        self._update_preview(index.row())
        self.accept()

    def _update_preview(self, row):
        """Update the preview with the selected web app.

        Args:
            row: The row index of the selected web app
        """
        # Get the app index from the table (consider the filtered list)
        app_name = self.web_apps_table.item(row, 0).text()
        app_browser = self.web_apps_table.item(row, 1).text().lower()
        app_profile = self.web_apps_table.item(row, 2).text()

        # Find the corresponding app in the full list
        for app in self.web_apps:
            if (app.name == app_name and
                    app.browser == app_browser and
                    app.profile == app_profile):
                self.selected_app = app
                break
        else:
            self.selected_app = None
            self._clear_preview()
            return

        # Update preview
        self.app_name_label.setText(app.name)
        self.app_id_label.setText(app.app_id)
        self.app_browser_label.setText(app.browser.capitalize())
        self.app_profile_label.setText(app.profile)
        self.app_url_label.setText(app.url)
        self.app_window_class_label.setText(app.window_class)

        # Update icon
        if app.icon_path and os.path.exists(app.icon_path):
            pixmap = QPixmap(app.icon_path)
            if not pixmap.isNull():
                # Scale pixmap if necessary
                if pixmap.width() > 128 or pixmap.height() > 128:
                    pixmap = pixmap.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.icon_label.setPixmap(pixmap)
                return

        # Clear icon if no valid icon found
        self.icon_label.clear()
        self.icon_label.setText("No icon")

    def _clear_preview(self):
        """Clear the preview."""
        self.app_name_label.setText("")
        self.app_id_label.setText("")
        self.app_browser_label.setText("")
        self.app_profile_label.setText("")
        self.app_url_label.setText("")
        self.app_window_class_label.setText("")
        self.icon_label.clear()
        self.icon_label.setText("No web app selected")

    def get_selected_web_app(self) -> Optional[WebApp]:
        """Get the selected web app.

        Returns:
            The selected WebApp object, or None if no app is selected
        """
        return self.selected_app

    def on_selection_changed(self):
        """Handle selection change in the web apps table."""
        selected_rows = self.web_apps_table.selectionModel().selectedRows()
        if selected_rows:
            self._update_preview(selected_rows[0].row())
        else:
            self._clear_preview()

    def on_accepted(self):
        """Handle dialog acceptance."""
        # Ensure we have the selected app
        selected_rows = self.web_apps_table.selectionModel().selectedRows()
        if selected_rows:
            self._update_preview(selected_rows[0].row())