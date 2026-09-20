"""Minimalist Floating HUD Overlay with Soundwave Visualizer for JARVIS (FR-3).

Features:
- Translucent glowing pill with dynamic soundwave visualizer (PyQt6)
- Non-intrusive click-through behavior (WindowTransparentForInput)
- Responsive states: Idle (hidden), Listening, Thinking, Speaking
- Placed bottom-center of the primary monitor
"""

import math
from typing import Optional

try:
    from PyQt6.QtCore import Qt, QTimer, QRectF, pyqtSignal
    from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QLinearGradient, QFont
    from PyQt6.QtWidgets import QWidget, QApplication
    HAS_PYQT6 = True
except ImportError:
    HAS_PYQT6 = False

class HUDOverlay(QWidget if HAS_PYQT6 else object):
    if HAS_PYQT6:
        state_signal = pyqtSignal(str)
        energy_signal = pyqtSignal(float)

    def __init__(
        self,
        width: int = 320,
        height: int = 68,
        theme_color: str = "#00f0ff",
        opacity: float = 0.92,
        parent: Optional[QWidget] = None
    ):
        if not HAS_PYQT6:
            return

        super().__init__(parent)
        self.hud_width = width
        self.hud_height = height
        self.theme_color = theme_color
        self.hud_opacity = opacity

        self.current_state = "idle"  # idle, listening, thinking, speaking
        self.energy_level = 0.0      # 0.0 to 1.0 (from audio RMS)
        self._animation_phase = 0.0

        # Connect thread-safe signals to slots
        self.state_signal.connect(self._safe_set_state)
        self.energy_signal.connect(self._safe_set_energy)

        self._init_ui()

        # 60 FPS animation timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_tick)
        self.timer.start(16)

    def _init_ui(self):
        """Configure frameless, click-through, always-on-top window flags."""
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
        )
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self.resize(self.hud_width, self.hud_height)
        self.reposition_to_bottom_center()
        self.hide()

    def reposition_to_bottom_center(self):
        """Center the HUD horizontally near the bottom of primary screen."""
        screen = QApplication.primaryScreen()
        if screen:
            screen_geo = screen.geometry()
            x = (screen_geo.width() - self.hud_width) // 2
            y = screen_geo.height() - self.hud_height - 60
            self.move(x, y)

    def set_state(self, state: str):
        """Thread-safe update of display state: 'idle', 'listening', 'thinking', 'speaking'."""
        if HAS_PYQT6:
            self.state_signal.emit(state)

    def _safe_set_state(self, state: str):
        """Internal slot running strictly on GUI main thread."""
        self.current_state = state.lower()
        if self.current_state == "idle":
            self.hide()
        else:
            if not self.isVisible():
                self.show()
        self.update()

    def set_energy(self, energy: float):
        """Thread-safe update of real-time voice amplitude level."""
        if HAS_PYQT6:
            self.energy_signal.emit(energy)

    def _safe_set_energy(self, energy: float):
        """Internal slot running strictly on GUI main thread."""
        boosted = min(1.0, (energy ** 0.5) * 5.0)
        self.energy_level = max(0.0, min(1.0, self.energy_level * 0.4 + boosted * 0.6))

    def _on_tick(self):
        """Animation update loop."""
        self._animation_phase += 0.08
        if self._animation_phase > 2 * math.pi:
            self._animation_phase -= 2 * math.pi
        if self.isVisible():
            self.update()

    def paintEvent(self, event):
        """Custom paint for glowing pill and animated audio wave bars."""
        if not HAS_PYQT6 or self.current_state == "idle":
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(4, 4, self.width() - 8, self.height() - 8)
        radius = rect.height() / 2

        # 1. Background Pill Container (Dark glassmorphic)
        bg_brush = QBrush(QColor(10, 15, 26, int(220 * self.hud_opacity)))
        painter.setBrush(bg_brush)

        # Border glow according to state
        if self.current_state == "listening":
            glow_color = QColor(0, 240, 255, 200)      # Cyan
            if self.energy_level > 0.08:
                state_text = f"LISTENING ({int(self.energy_level * 100)}%)"
            else:
                state_text = "LISTENING"
        elif self.current_state == "thinking":
            glow_color = QColor(160, 80, 255, 220)    # Violet
            state_text = "PROCESSING"
        elif self.current_state == "speaking":
            glow_color = QColor(0, 255, 170, 220)      # Mint green
            state_text = "JARVIS"
        else:
            glow_color = QColor(100, 120, 150, 150)
            state_text = "STANDBY"

        pen = QPen(glow_color, 1.8)
        painter.setPen(pen)
        painter.drawRoundedRect(rect, radius, radius)

        # 2. Status Indicator Circle
        dot_radius = 5.0
        dot_x = rect.left() + 24
        dot_y = rect.center().y()
        pulse = 0.5 + 0.5 * math.sin(self._animation_phase * 2)
        dot_color = QColor(glow_color.red(), glow_color.green(), glow_color.blue(), int(160 + 95 * pulse))
        painter.setBrush(QBrush(dot_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(dot_x - dot_radius, dot_y - dot_radius, dot_radius * 2, dot_radius * 2))

        # 3. Label Text
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        painter.setPen(QPen(QColor(220, 235, 245, 230)))
        painter.drawText(int(dot_x + 14), int(dot_y + 4), state_text)

        # 4. Animated Sound Waveform Bars
        num_bars = 14
        bars_start_x = rect.left() + 150
        bar_width = 3.5
        spacing = 7.0
        center_y = rect.center().y()

        for i in range(num_bars):
            # Calculate dynamic height based on sine wave + energy level
            offset = i * 0.45
            wave = math.sin(self._animation_phase * 3 + offset)
            base_amp = 4.0
            if self.current_state == "listening":
                amp = base_amp + (self.energy_level * 22.0) * abs(wave)
            elif self.current_state == "speaking":
                amp = base_amp + (max(0.2, self.energy_level) * 20.0) * abs(wave)
            elif self.current_state == "thinking":
                amp = base_amp + 10.0 * abs(math.sin(self._animation_phase * 4 + offset))
            else:
                amp = 2.0

            bar_x = bars_start_x + (i * spacing)
            bar_y1 = center_y - amp
            bar_y2 = center_y + amp
            bar_color = QColor(glow_color.red(), glow_color.green(), glow_color.blue(), 230)
            painter.setPen(QPen(bar_color, bar_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(int(bar_x), int(bar_y1), int(bar_x), int(bar_y2))

        painter.end()
