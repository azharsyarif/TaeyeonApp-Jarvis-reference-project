"""Windows System Tray Integration for JARVIS (FR-1.2).

Provides tray icon notification area integration, status menu, manual triggers, and quit handler.
"""

import os
from typing import Optional, Callable

try:
    from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
    from PyQt6.QtGui import QIcon, QAction
    HAS_PYQT6 = True
except ImportError:
    HAS_PYQT6 = False

class JARVISTray:
    def __init__(
        self,
        icon_path: str,
        on_activate: Optional[Callable[[], None]] = None,
        on_quit: Optional[Callable[[], None]] = None,
        parent=None
    ):
        self.icon_path = icon_path
        self.on_activate = on_activate
        self.on_quit = on_quit
        self.tray_icon = None

        if HAS_PYQT6:
            self._init_tray(parent)

    def _init_tray(self, parent):
        if not os.path.exists(self.icon_path):
            print(f"[JARVISTray] Warning: Icon file not found at {self.icon_path}")
            icon = QIcon()
        else:
            icon = QIcon(self.icon_path)

        self.tray_icon = QSystemTrayIcon(icon, parent)
        self.tray_icon.setToolTip("J.A.R.V.I.S. Voice Assistant")

        menu = QMenu()

        # Status Header (Disabled)
        status_action = QAction("JARVIS: Online (Standby)", menu)
        status_action.setEnabled(False)
        menu.addAction(status_action)
        self.status_action = status_action

        menu.addSeparator()

        # Manual Activation
        activate_action = QAction("Activate JARVIS (Alt + Space)", menu)
        if self.on_activate:
            activate_action.triggered.connect(self.on_activate)
        menu.addAction(activate_action)

        menu.addSeparator()

        # Quit
        quit_action = QAction("Exit JARVIS", menu)
        if self.on_quit:
            quit_action.triggered.connect(self.on_quit)
        menu.addAction(quit_action)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()

    def update_status(self, status_text: str):
        """Update tray menu status label."""
        if hasattr(self, "status_action") and self.status_action:
            self.status_action.setText(f"JARVIS: {status_text}")

    def show_message(self, title: str, message: str):
        """Show Windows notification balloon/toast."""
        if self.tray_icon:
            self.tray_icon.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 2500)
