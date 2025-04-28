"""
Icon selector dialog for Toggleman application.

This module provides a dialog for selecting icons for toggle scripts.
"""

import os
import sys
import glob
from typing import Dict, List, Optional, Any, Tuple

from PyQt5.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QPushButton, QLabel, QCheckBox, QLineEdit, QTabWidget, QFileDialog,
    QSpinBox, QComboBox, QDialogButtonBox, QSizePolicy, QMessageBox,
    QListWidget, QListWidgetItem, QAbstractItemView, QScrollArea, QFrame,
    QGridLayout
)
from PyQt5.QtGui import QIcon, QFont, QPixmap
from PyQt5.QtCore import Qt, QSize, pyqtSignal, pyqtSlot

from toggleman.core.debug import get_logger

logger = get_logger(__name__)


class IconButton(QPushButton):
    """Custom icon button for the icon selector dialog."""

    selected = pyqtSignal(str)

    def __init__(self, icon_path: str, size: int = 48, parent=None):
        """Initialize the icon button.

        Args:
            icon_path: The path to the icon
            size: The size of the icon
            parent: The parent widget
        """
        super().__init__(parent)

        self.icon_path = icon_path
        self.setIcon(QIcon(icon_path))
        self.setIconSize(QSize(size, size))
        self.setFixedSize(size + 10, size + 10)
        self.setFlat(True)
        self.setToolTip(os.path.basename(icon_path))

        # Connect signals
        self.clicked.connect(self._on_clicked)

    def _on_clicked(self):
        """Handle button click."""
        self.selected.emit(self.icon_path)


class IconSelectorDialog(QDialog):
    """Dialog for selecting an icon."""

    def __init__(self, current_icon: str = "", parent=None):
        """Initialize the icon selector dialog.

        Args:
            current_icon: The current icon path
            parent: The parent widget
        """
        super().__init__(parent)

        self.current_icon = current_icon
        self.selected_icon = current_icon

        # Set up the UI
        self._setup_ui()

        logger.debug("Icon selector dialog initialized")

    def _setup_ui(self):
        """Set up the dialog UI."""
        # Dialog properties
        self.setWindowTitle("Select Icon")
        self.setWindowIcon(QIcon.fromTheme("preferences-desktop-icons"))
        self.resize(600, 400)

        # Create main layout
        main_layout = QVBoxLayout(self)

        # Create tab widget
        tab_widget = QTabWidget()

        # Create system icons tab
        system_tab = QWidget()
        system_layout = QVBoxLayout(system_tab)

        # Create search layout
        search_layout = QHBoxLayout()

        search_label = QLabel("Search:")
        search_layout.addWidget(search_label)

        self.search_edit = QLineEdit()
        self.search_edit.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(self.search_edit)

        system_layout.addLayout(search_layout)

        # Create icon categories
        categories = self._get_icon_categories()

        # Create scroll area for icons
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # Add icon categories
        for category, icons in categories.items():
            # Skip empty categories
            if not icons:
                continue

            # Create category group
            group = QGroupBox(category)
            group_layout = QGridLayout(group)
            group_layout.setSpacing(2)

            # Add icons to grid
            row, col = 0, 0
            max_cols = 8

            for icon_path in icons:
                icon_button = IconButton(icon_path)
                icon_button.selected.connect(self._on_icon_selected)
                group_layout.addWidget(icon_button, row, col)

                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1

            # Add category group to layout
            scroll_layout.addWidget(group)

        # Add stretch
        scroll_layout.addStretch()

        # Set scroll widget
        scroll_area.setWidget(scroll_widget)

        # Add scroll area to layout
        system_layout.addWidget(scroll_area)

        # Add system tab to tab widget
        tab_widget.addTab(system_tab, "System Icons")

        # Create custom icon tab
        custom_tab = QWidget()
        custom_layout = QVBoxLayout(custom_tab)

        # Create icon path layout
        icon_path_layout = QHBoxLayout()

        icon_path_label = QLabel("Icon Path:")
        icon_path_layout.addWidget(icon_path_label)

        self.icon_path_edit = QLineEdit()
        self.icon_path_edit.setText(self.current_icon)
        icon_path_layout.addWidget(self.icon_path_edit)

        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self._on_browse_icon)
        icon_path_layout.addWidget(browse_button)

        custom_layout.addLayout(icon_path_layout)

        # Create icon preview
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)

        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(128, 128)
        preview_layout.addWidget(self.preview_label)

        # Add preview group to layout
        custom_layout.addWidget(preview_group)

        # Add spacer
        custom_layout.addStretch()

        # Add custom tab to tab widget
        tab_widget.addTab(custom_tab, "Custom Icon")

        # Connect tab changes
        tab_widget.currentChanged.connect(self._on_tab_changed)

        # Add tab widget to main layout
        main_layout.addWidget(tab_widget)

        # Create button box
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        # Add button box to main layout
        main_layout.addWidget(button_box)

        # Update preview
        self._update_preview()

        # Focus search box
        self.search_edit.setFocus()

    def _get_icon_categories(self) -> Dict[str, List[str]]:
        """Get system icon categories.

        Returns:
            A dictionary mapping category names to lists of icon paths
        """
        categories = {
            "Applications": [],
            "Places": [],
            "Devices": [],
            "Actions": [],
            "Status": [],
            "MimeTypes": [],
            "Categories": [],
            "Emblems": [],
            "Other": []
        }

        # Get icons from system icon theme
        icon_dirs = [
            "/usr/share/icons/hicolor",
            "/usr/share/icons/gnome",
            "/usr/share/icons/oxygen",
            "/usr/share/icons/breeze",
            "/usr/share/icons/breeze-dark",
            "/usr/share/pixmaps",
            os.path.expanduser("~/.local/share/icons")
        ]

        for icon_dir in icon_dirs:
            if not os.path.exists(icon_dir):
                continue

            # Get icon sizes (sort by size descending)
            icon_sizes = []
            for size_dir in glob.glob(os.path.join(icon_dir, "*")):
                if os.path.isdir(size_dir):
                    size_name = os.path.basename(size_dir)
                    if size_name.isdigit():
                        icon_sizes.append((int(size_name), size_name))
                    elif "x" in size_name:
                        try:
                            width, height = size_name.split("x")
                            icon_sizes.append((int(width), size_name))
                        except Exception:
                            icon_sizes.append((0, size_name))
                    else:
                        icon_sizes.append((0, size_name))

            icon_sizes.sort(reverse=True)
            icon_sizes = [s[1] for s in icon_sizes]

            # Process each category
            for category in categories.keys():
                category_lower = category.lower()

                # Try each size
                for size in icon_sizes:
                    category_dir = os.path.join(icon_dir, size, category_lower)
                    if not os.path.exists(category_dir):
                        continue

                    # Get icons from this category directory
                    for ext in ["png", "svg", "xpm"]:
                        for icon_path in glob.glob(os.path.join(category_dir, f"*.{ext}")):
                            if icon_path not in categories[category]:
                                categories[category].append(icon_path)

        return categories

    def _update_preview(self):
        """Update the icon preview."""
        # Get icon path
        icon_path = self.icon_path_edit.text()

        if icon_path and os.path.exists(icon_path):
            # Create pixmap
            pixmap = QPixmap(icon_path)

            if not pixmap.isNull():
                # Scale pixmap if necessary
                if pixmap.width() > 128 or pixmap.height() > 128:
                    pixmap = pixmap.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation)

                # Set pixmap
                self.preview_label.setPixmap(pixmap)
                return

        # Clear preview if no valid icon
        self.preview_label.setText("No icon selected")

    def _on_browse_icon(self):
        """Handle browsing for a custom icon."""
        # Open file dialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Icon",
            os.path.expanduser("~"),
            "Image Files (*.png *.jpg *.svg *.xpm);;All Files (*)"
        )

        if file_path:
            # Set icon path
            self.icon_path_edit.setText(file_path)
            self.selected_icon = file_path

            # Update preview
            self._update_preview()

    def _on_search_changed(self, text: str):
        """Handle search text changes.

        Args:
            text: The search text
        """
        # TODO: Implement icon search
        pass

    def _on_icon_selected(self, icon_path: str):
        """Handle icon selection.

        Args:
            icon_path: The selected icon path
        """
        # Set selected icon
        self.selected_icon = icon_path

        # Update custom icon path
        self.icon_path_edit.setText(icon_path)

        # Update preview
        self._update_preview()

        # Switch to custom tab
        tab_widget = self.findChild(QTabWidget)
        if tab_widget:
            tab_widget.setCurrentIndex(1)

    def _on_tab_changed(self, index: int):
        """Handle tab changes.

        Args:
            index: The new tab index
        """
        # Update preview when switching to custom tab
        if index == 1:
            self._update_preview()

    def accept(self):
        """Handle dialog acceptance."""
        # Use the custom icon path as the selected icon
        self.selected_icon = self.icon_path_edit.text()

        # Accept dialog
        super().accept()