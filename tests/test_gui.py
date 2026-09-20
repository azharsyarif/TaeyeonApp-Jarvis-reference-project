"""Unit tests for HUD Overlay and System Tray components."""

import os
import sys
import pytest

from src.gui.hud_overlay import HUDOverlay, HAS_PYQT6
from src.gui.system_tray import JARVISTray

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@pytest.fixture(scope="session")
def qapp():
    if not HAS_PYQT6:
        pytest.skip("PyQt6 not available")
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app

def test_hud_overlay_lifecycle(qapp):
    hud = HUDOverlay(width=300, height=60)
    assert hud.current_state == "idle"
    
    # Test state updates
    hud.set_state("listening")
    assert hud.current_state == "listening"
    
    hud.set_energy(0.75)
    assert hud.energy_level > 0.0
    
    hud.set_state("thinking")
    assert hud.current_state == "thinking"
    
    hud.set_state("speaking")
    assert hud.current_state == "speaking"
    
    hud.set_state("idle")
    assert hud.current_state == "idle"
    hud.close()

def test_tray_initialization(qapp):
    icon_path = os.path.join(BASE_DIR, "assets", "tray_icon.png")
    tray = JARVISTray(icon_path=icon_path)
    assert tray.tray_icon is not None
    tray.update_status("Online (Testing)")
    assert "Testing" in tray.status_action.text()
