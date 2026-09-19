"""JARVIS Windows Native Voice Assistant - Main Application Daemon.

Coordinates:
- Background Core Engine
- Low-Latency Audio Streaming (sounddevice)
- Google Gemini Multimodal Live API (WebSocket)
- Floating Waveform HUD & System Tray (PyQt6)
- Global Hotkeys & Activation (keyboard)
- OS Automation Tools (pc_control, app_launcher, screen_capture, system_exec)
"""

import asyncio
import json
import os
import sys
import threading
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

from src.core.audio_manager import AudioManager
from src.core.live_client import LiveClient
from src.core.wakeword_engine import WakeWordEngine
from src.gui.hud_overlay import HUDOverlay, HAS_PYQT6
from src.gui.system_tray import JARVISTray

# Try importing PyQt6 QApplication
if HAS_PYQT6:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import QTimer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

def load_settings():
    settings_path = os.path.join(CONFIG_DIR, "settings.json")
    if os.path.exists(settings_path):
        with open(settings_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def load_system_prompt():
    prompt_path = os.path.join(CONFIG_DIR, "system_prompt.txt")
    if os.path.exists(prompt_path):
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return "You are JARVIS, a concise, polite Windows voice assistant."

class JarvisDaemon:
    def __init__(self):
        self.settings = load_settings()
        self.system_prompt = load_system_prompt()
        self.app = None
        self.hud = None
        self.tray = None

        self.audio_settings = self.settings.get("audio", {})
        self.activation_settings = self.settings.get("activation", {})
        self.gemini_settings = self.settings.get("gemini", {})
        self.hud_settings = self.settings.get("hud", {})

        # Async event loop for LiveClient
        self.async_loop = asyncio.new_event_loop()
        self._async_thread = None
        self._live_task = None

        # Setup audio manager
        self.audio_manager = AudioManager(
            input_rate=self.audio_settings.get("input_sample_rate", 16000),
            output_rate=self.audio_settings.get("output_sample_rate", 24000),
            channels=self.audio_settings.get("channels", 1),
            chunk_size=self.audio_settings.get("chunk_size", 1024),
            vad_threshold=self.audio_settings.get("vad_energy_threshold", 0.015),
            preferred_input_device=self.audio_settings.get("input_device"),
            on_rms_callback=self._on_audio_rms,
            on_standby_audio_callback=self._on_standby_audio,
        )

        # Setup Live Client
        self.live_client = LiveClient(
            api_key=os.getenv("GEMINI_API_KEY"),
            model=self.gemini_settings.get("model", "gemini-3.1-flash-live-preview"),
            voice_name=self.gemini_settings.get("voice", "Puck"),
            system_instruction=self.system_prompt,
            audio_manager=self.audio_manager,
            on_state_change=self._on_client_state_change,
            on_transcript=self._on_transcript,
            on_dismiss=self.cancel_session,
        )

        # Setup WakeWord & Hotkey Engine
        self.wakeword_engine = WakeWordEngine(
            hotkey=self.activation_settings.get("hotkey", "alt+space"),
            secondary_hotkey=self.activation_settings.get("secondary_hotkey", "windows+shift+j"),
            cancel_hotkey="escape",
            wake_word=self.activation_settings.get("wake_word", "hey jarvis"),
            wake_word_enabled=self.activation_settings.get("wake_word_enabled", True),
            on_activate=self.activate_session,
            on_cancel=self.cancel_session,
        )
        self._is_active = False

    def _on_standby_audio(self, data_bytes: bytes):
        """Pass standby microphone audio to local wake word engine."""
        if hasattr(self, "wakeword_engine") and self.wakeword_engine:
            self.wakeword_engine.on_standby_audio(data_bytes)

    def _on_audio_rms(self, rms: float, stream_type: str):
        """Pass audio energy to HUD visualizer."""
        if self.hud:
            self.hud.set_energy(rms)

    def _on_client_state_change(self, state: str):
        """Update HUD and Tray when agent state changes."""
        if self.hud:
            self.hud.set_state(state)
        if self.tray:
            self.tray.update_status(state.capitalize())

    def _on_transcript(self, role: str, text: str):
        """Print or log real-time speech transcripts."""
        print(f"[{role}]: {text}")

    def cancel_session(self):
        """Immediately abort active session and reset to standby."""
        print("[JARVIS] Cancelling active session...")
        self._is_active = False
        self.live_client.stop()
        self.audio_manager.interrupt()
        self.audio_manager.stop_session_streaming()
        
        if self._live_task and not self._live_task.done():
            self._live_task.cancel()
        self._live_task = None
        
        chime_out_path = os.path.join(ASSETS_DIR, "chime_out.wav")
        self.audio_manager.play_sound_effect(chime_out_path)
        
        if self.hud:
            self.hud.set_state("idle")
        if self.tray:
            self.tray.update_status("Standby")

    def activate_session(self):
        """Trigger activation: chime cue + connect Live API."""
        print("[JARVIS] Activation triggered!")
        
        # Audio cue chime_in
        chime_in_path = os.path.join(ASSETS_DIR, "chime_in.wav")
        self.audio_manager.play_sound_effect(chime_in_path)

        if self.hud:
            self.hud.set_state("listening")

        # If live session is already active, interrupt any speech and ensure fresh listening
        if self._is_active and self._live_task is not None and not self._live_task.done():
            print("[JARVIS] Live session active. Switching to listening mode for user.")
            self.audio_manager.interrupt()
            self.audio_manager.start_session_streaming()
            return

        self._is_active = True
        self.audio_manager.start_session_streaming()

        # Launch live session task in background async loop
        self._live_task = asyncio.run_coroutine_threadsafe(
            self._safe_run_client(),
            self.async_loop
        )

    async def _safe_run_client(self):
        """Run LiveClient session with exception safety."""
        try:
            await self.live_client.run()
        except Exception as e:
            print(f"[JARVIS] Session error: {e}")
        finally:
            self._is_active = False
            self._live_task = None
            self.audio_manager.stop_session_streaming()
            self.live_client.resumption_handle = None
            chime_out_path = os.path.join(ASSETS_DIR, "chime_out.wav")
            self.audio_manager.play_sound_effect(chime_out_path)
            if self.hud:
                self.hud.set_state("idle")
            if self.tray:
                self.tray.update_status("Standby")

    def _run_async_loop(self):
        """Background thread target running the asyncio event loop."""
        asyncio.set_event_loop(self.async_loop)
        self.audio_manager.start(self.async_loop)
        self.async_loop.run_forever()

    def start(self):
        """Start all services and run UI application loop."""
        # 1. Start Async Loop Thread
        self._async_thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self._async_thread.start()

        # 2. Start Hotkey Engine
        self.wakeword_engine.start()

        # 3. Setup GUI if PyQt6 is available
        if HAS_PYQT6:
            self.app = QApplication.instance() or QApplication(sys.argv)
            self.app.setQuitOnLastWindowClosed(False)

            # Floating HUD
            if self.hud_settings.get("enabled", True):
                self.hud = HUDOverlay(
                    width=self.hud_settings.get("width", 320),
                    height=self.hud_settings.get("height", 68),
                    opacity=self.hud_settings.get("opacity", 0.92)
                )

            # System Tray
            tray_icon_path = os.path.join(ASSETS_DIR, "tray_icon.png")
            self.tray = JARVISTray(
                icon_path=tray_icon_path,
                on_activate=self.activate_session,
                on_quit=self.stop
            )

            print("[JARVIS] Running background daemon with HUD and System Tray.")
            sys.exit(self.app.exec())
        else:
            print("[JARVIS] Running in headless mode (Press Ctrl+C to exit).")
            try:
                while True:
                    threading.Event().wait(1.0)
            except KeyboardInterrupt:
                self.stop()

    def stop(self):
        """Clean shutdown of all resources."""
        print("[JARVIS] Shutting down daemon...")
        self.wakeword_engine.stop()
        self.live_client.stop()
        self.audio_manager.stop()

        if self.async_loop.is_running():
            self.async_loop.call_soon_threadsafe(self.async_loop.stop)

        if self.app:
            self.app.quit()

if __name__ == "__main__":
    daemon = JarvisDaemon()
    daemon.start()
