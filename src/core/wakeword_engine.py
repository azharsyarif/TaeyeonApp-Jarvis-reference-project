"""Wake Word and Global Hotkey Activation Engine for JARVIS (FR-1).

Provides:
- Global system hotkey registration (default: 'alt+space' or 'windows+shift+j')
- Local offline acoustic trigger / speech activation detector using openWakeWord ('hey jarvis')
- Seamless activation callback triggering Live Session & audio chime
"""

import queue
import threading
import time
from typing import Callable, Optional
import numpy as np

try:
    import keyboard
    HAS_KEYBOARD = True
except Exception:
    HAS_KEYBOARD = False

try:
    import openwakeword
    from openwakeword.model import Model as OWWModel
    HAS_OPENWAKEWORD = True
except Exception:
    HAS_OPENWAKEWORD = False

class WakeWordEngine:
    def __init__(
        self,
        hotkey: str = "alt+space",
        secondary_hotkey: Optional[str] = "windows+shift+j",
        cancel_hotkey: Optional[str] = "escape",
        wake_word: str = "hey jarvis",
        wake_word_enabled: bool = True,
        threshold: float = 0.5,
        on_activate: Optional[Callable[[], None]] = None,
        on_cancel: Optional[Callable[[], None]] = None,
    ):
        self.hotkey = hotkey
        self.secondary_hotkey = secondary_hotkey
        self.cancel_hotkey = cancel_hotkey
        self.wake_word = wake_word
        self.wake_word_enabled = wake_word_enabled
        self.threshold = threshold
        self.on_activate = on_activate
        self.on_cancel = on_cancel

        self._running = False
        self._last_trigger_time = 0.0
        self._wake_word_active = False
        self._model = None
        self._audio_buffer = []
        self._audio_queue = queue.Queue(maxsize=30)
        self._worker_thread = None

    def start(self):
        """Register global hotkeys and start trigger listeners."""
        self._running = True
        self._register_hotkeys()
        if self.wake_word_enabled:
            self._start_wake_word_listener()

    def _start_wake_word_listener(self):
        """Initialize offline acoustic wake-word detector using openWakeWord."""
        if not HAS_OPENWAKEWORD:
            print(
                f"[WakeWordEngine] wake_word_enabled=true but 'openwakeword' is not installed. "
                f"'{self.wake_word}' detection is inactive; use hotkey ({self.hotkey})."
            )
            return

        try:
            # Load hey_jarvis model
            self._model = OWWModel(wakeword_models=["hey_jarvis"], inference_framework="onnx")
            self._wake_word_active = True
            self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self._worker_thread.start()
            print(f"[WakeWordEngine] Offline wake word detector active: '{self.wake_word}' (threshold: {self.threshold})")
        except Exception as e:
            print(f"[WakeWordEngine] Error loading wake word model: {e}")
            self._wake_word_active = False

    def on_standby_audio(self, data_bytes: bytes):
        """Receive 16kHz 16-bit PCM audio chunks non-blockingly without delaying the audio callback."""
        if not self._running or not self._wake_word_active:
            return

        try:
            self._audio_queue.put_nowait(data_bytes)
        except queue.Full:
            try:
                self._audio_queue.get_nowait()
                self._audio_queue.put_nowait(data_bytes)
            except Exception:
                pass

    def _worker_loop(self):
        """Dedicated background thread executing ONNX inference safely off the audio thread."""
        while self._running:
            try:
                data_bytes = self._audio_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if not self._wake_word_active or not self._model:
                continue

            try:
                samples = np.frombuffer(data_bytes, dtype=np.int16)
                self._audio_buffer.extend(samples)

                # openWakeWord expects chunks of 1280 samples (80ms at 16kHz)
                while len(self._audio_buffer) >= 1280:
                    chunk = np.array(self._audio_buffer[:1280], dtype=np.int16)
                    del self._audio_buffer[:1280]

                    scores = self._model.predict(chunk)
                    for name, score in scores.items():
                        if "jarvis" in name.lower() and score >= self.threshold:
                            print(f"[WakeWordEngine] Wake word detected: '{name}' (confidence: {score:.2f})")
                            self._audio_buffer.clear()
                            # Purge remaining queue to start fresh
                            while not self._audio_queue.empty():
                                try:
                                    self._audio_queue.get_nowait()
                                except Exception:
                                    break
                            self._trigger()
                            break
            except Exception:
                pass

    def _trigger(self):
        """Handle activation with debounce."""
        now = time.time()
        # 0.8s debounce period
        if now - self._last_trigger_time < 0.8:
            return
        self._last_trigger_time = now

        if self.on_activate:
            self.on_activate()

    def _trigger_cancel(self):
        """Handle cancel request."""
        if self.on_cancel:
            self.on_cancel()

    def _register_hotkeys(self):
        """Register system-wide hotkeys via keyboard library."""
        if not HAS_KEYBOARD:
            print("[WakeWordEngine] 'keyboard' module not available. Hotkeys disabled.")
            return

        try:
            if self.hotkey:
                keyboard.add_hotkey(self.hotkey, self._trigger, suppress=False)
                print(f"[WakeWordEngine] Global hotkey registered: {self.hotkey}")
        except Exception as e:
            print(f"[WakeWordEngine] Could not register primary hotkey ({self.hotkey}): {e}")

        try:
            if self.secondary_hotkey:
                keyboard.add_hotkey(self.secondary_hotkey, self._trigger, suppress=False)
                print(f"[WakeWordEngine] Secondary hotkey registered: {self.secondary_hotkey}")
        except Exception as e:
            print(f"[WakeWordEngine] Could not register secondary hotkey ({self.secondary_hotkey}): {e}")

        try:
            if self.cancel_hotkey:
                keyboard.add_hotkey(self.cancel_hotkey, self._trigger_cancel, suppress=False)
                print(f"[WakeWordEngine] Cancel hotkey registered: {self.cancel_hotkey}")
        except Exception as e:
            print(f"[WakeWordEngine] Could not register cancel hotkey ({self.cancel_hotkey}): {e}")

    def stop(self):
        """Unregister hotkeys and stop engine."""
        self._running = False
        self._wake_word_active = False
        self._audio_buffer.clear()
        if HAS_KEYBOARD:
            try:
                keyboard.unhook_all()
            except Exception:
                pass
