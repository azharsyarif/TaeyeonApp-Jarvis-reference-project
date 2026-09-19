"""Low-Latency PCM Audio Streamer and Audio Manager for JARVIS.

Handles:
- FR-2.1: 16kHz Mono 16-bit PCM input streaming & 24kHz Mono 16-bit PCM output playback
- FR-2.2: Barge-in / Interruption handling (instant flush on user speech)
- FR-2.3: Voice Activity Detection (VAD) via RMS energy threshold
- FR-1.5: Audio chime cue playback (chime_in, chime_out)
"""

import asyncio
import collections
import math
import os
import queue
import struct
import threading
import wave
from typing import Optional, Callable, AsyncGenerator

import numpy as np

try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except Exception:
    HAS_SOUNDDEVICE = False

def calculate_rms(pcm_data: bytes) -> float:
    """Calculate normalized RMS energy (0.0 - 1.0) of 16-bit mono PCM audio."""
    if not pcm_data:
        return 0.0
    count = len(pcm_data) // 2
    if count == 0:
        return 0.0
    try:
        shorts = struct.unpack(f"<{count}h", pcm_data[:count * 2])
        sum_squares = sum(s * s for s in shorts)
        rms = math.sqrt(sum_squares / count)
        return min(1.0, rms / 32768.0)
    except Exception:
        return 0.0

def find_best_input_device(preferred_name: Optional[str] = None):
    """Intelligently select a working real physical microphone, testing opening it first."""
    if not HAS_SOUNDDEVICE:
        return None, "Mock"
    try:
        devices = sd.query_devices()

        def is_openable(idx):
            try:
                sd.check_input_settings(device=idx, channels=1, samplerate=16000)
                return True
            except Exception:
                return False

        # 1. If preferred name specified, match it
        if preferred_name:
            for i, d in enumerate(devices):
                if d['max_input_channels'] > 0 and preferred_name.lower() in d['name'].lower():
                    if is_openable(i):
                        return i, d['name']

        # 2. Priority match for physical headsets/microphones on working host APIs
        keywords = ['microphone array', 'realtek', 'soundcore', 'headset', 'mic']
        for kw in keywords:
            for i, d in enumerate(devices):
                name = d['name'].lower()
                if d['max_input_channels'] > 0 and kw in name and not any(v in name for v in ['cable', 'virtual', 'stereo mix', 'steam']):
                    if is_openable(i):
                        return i, d['name']

        # 3. Fallback to default if openable and not virtual cable
        default_in = sd.default.device[0]
        if default_in is not None and default_in >= 0:
            def_name = devices[default_in]['name'].lower()
            if not any(v in def_name for v in ['cable', 'virtual', 'stereo mix']) and is_openable(default_in):
                return default_in, devices[default_in]['name']

        # 4. Any openable non-virtual device
        for i, d in enumerate(devices):
            name = d['name'].lower()
            if d['max_input_channels'] > 0 and not any(v in name for v in ['cable', 'virtual', 'stereo mix']) and is_openable(i):
                return i, d['name']

        return default_in, devices[default_in]['name'] if default_in is not None else "Default"
    except Exception:
        return None, "Default"

class AudioManager:
    def __init__(
        self,
        input_rate: int = 16000,
        output_rate: int = 24000,
        channels: int = 1,
        chunk_size: int = 1024,
        vad_threshold: float = 0.015,
        preferred_input_device: Optional[str] = None,
        on_rms_callback: Optional[Callable[[float, str], None]] = None,
        on_standby_audio_callback: Optional[Callable[[bytes], None]] = None,
    ):
        self.input_rate = input_rate
        self.output_rate = output_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.vad_threshold = vad_threshold
        self.preferred_input_device = preferred_input_device
        self.on_rms_callback = on_rms_callback
        self.on_standby_audio_callback = on_standby_audio_callback
        self.input_device_index = None
        self.input_device_name = "Default"

        self._input_stream = None
        self._output_stream = None
        self._output_queue = queue.Queue()
        self._input_async_queue = None
        
        self.is_recording = False
        self.is_playing = False
        self._is_session_active = False
        self._stop_event = threading.Event()
        self._loop = None
        
        # Current energy level for UI visualizer
        self.current_input_rms = 0.0
        self.current_output_rms = 0.0

    def start_session_streaming(self):
        """Enable queuing audio for Gemini Live and purge any stale chunks."""
        self._is_session_active = True
        if self._input_async_queue:
            while not self._input_async_queue.empty():
                try:
                    self._input_async_queue.get_nowait()
                except Exception:
                    break

    def stop_session_streaming(self):
        """Disable queuing audio when standby."""
        self._is_session_active = False
        if self._input_async_queue:
            while not self._input_async_queue.empty():
                try:
                    self._input_async_queue.get_nowait()
                except Exception:
                    break

    def start(self, loop: Optional[asyncio.AbstractEventLoop] = None):
        """Initialize and start background audio streams."""
        self._loop = loop or asyncio.get_event_loop()
        self._input_async_queue = asyncio.Queue()
        self._stop_event.clear()
        
        if not HAS_SOUNDDEVICE:
            print("[AudioManager] sounddevice not available. Running in mock audio mode.")
            return

        try:
            # Setup output playback stream (24kHz Mono 16-bit)
            self._output_stream = sd.RawOutputStream(
                samplerate=self.output_rate,
                channels=self.channels,
                dtype='int16',
                blocksize=self.chunk_size,
                callback=self._output_callback
            )
            self._output_stream.start()

            # Detect best physical microphone
            dev_idx, dev_name = find_best_input_device(self.preferred_input_device)
            self.input_device_index = dev_idx
            self.input_device_name = dev_name
            print(f"[AudioManager] Using microphone: [{dev_idx}] {dev_name}")

            # Setup input recording stream (16kHz Mono 16-bit)
            self._input_stream = sd.RawInputStream(
                samplerate=self.input_rate,
                channels=self.channels,
                dtype='int16',
                blocksize=self.chunk_size,
                device=self.input_device_index,
                callback=self._input_callback
            )
            self._input_stream.start()
            self.is_recording = True
        except Exception as e:
            print(f"[AudioManager] Warning initializing audio hardware: {e}. Fallback to simulated mode.")

    def _input_callback(self, indata, frames, time_info, status):
        """Callback invoked by PortAudio thread for new input audio frames."""
        if status:
            pass
        data_bytes = bytes(indata)
        rms = calculate_rms(data_bytes)
        self.current_input_rms = rms
        
        if self.on_rms_callback:
            self.on_rms_callback(rms, "input")

        # Acoustic Echo Suppression:
        # When JARVIS is speaking out of the laptop speakers,
        # ignore speaker audio so it doesn't pollute Gemini input.
        if self.is_playing:
            if rms > 0.12:
                # User is speaking loudly over JARVIS: trigger barge-in
                self.interrupt()
            else:
                # Speaker feedback: suppress
                return
            
        # Put into async queue for Gemini Live consumer ONLY when session is active!
        if self._is_session_active and self._loop and self._input_async_queue and not self._stop_event.is_set():
            self._loop.call_soon_threadsafe(self._input_async_queue.put_nowait, data_bytes)
        elif not self._is_session_active and self.on_standby_audio_callback and not self._stop_event.is_set():
            self.on_standby_audio_callback(data_bytes)

    def _output_callback(self, outdata, frames, time_info, status):
        """Callback invoked by PortAudio thread to fill speaker buffer."""
        bytes_needed = frames * 2 * self.channels
        out_bytes = bytearray()
        
        while len(out_bytes) < bytes_needed:
            try:
                chunk = self._output_queue.get_nowait()
                out_bytes.extend(chunk)
            except queue.Empty:
                break
                
        if len(out_bytes) < bytes_needed:
            # Pad with silence if buffer underrun
            out_bytes.extend(b'\x00' * (bytes_needed - len(out_bytes)))
            self.is_playing = False
        else:
            self.is_playing = True
            
        rms = calculate_rms(bytes(out_bytes))
        self.current_output_rms = rms
        if self.on_rms_callback:
            self.on_rms_callback(rms, "output")
            
        outdata[:] = bytes(out_bytes[:bytes_needed])

    async def stream_input(self) -> AsyncGenerator[bytes, None]:
        """Async generator yielding incoming 16kHz PCM audio bytes."""
        while not self._stop_event.is_set():
            if self._input_async_queue:
                chunk = await self._input_async_queue.get()
                yield chunk
            else:
                await asyncio.sleep(0.05)

    def play_audio(self, pcm_bytes: bytes):
        """Enqueue 24kHz PCM audio chunks received from Gemini for playback."""
        if not pcm_bytes:
            return
        self.is_playing = True
        # Chunk into reasonable sizes for the queue
        step = self.chunk_size * 2
        for i in range(0, len(pcm_bytes), step):
            self._output_queue.put(pcm_bytes[i:i + step])

    def interrupt(self):
        """Barge-in: Immediately stop playing and purge queued audio buffer."""
        # Drain the output queue instantly
        while not self._output_queue.empty():
            try:
                self._output_queue.get_nowait()
            except queue.Empty:
                break
        self.is_playing = False
        self.current_output_rms = 0.0

    def play_sound_effect(self, wav_path: str):
        """Play a WAV audio file (e.g. chime_in.wav or chime_out.wav) in background."""
        if not os.path.exists(wav_path):
            return

        def _worker():
            try:
                with wave.open(wav_path, 'rb') as wf:
                    channels = wf.getnchannels()
                    rate = wf.getframerate()
                    data = wf.readframes(wf.getnframes())
                    if HAS_SOUNDDEVICE:
                        audio_arr = np.frombuffer(data, dtype=np.int16)
                        if channels > 1:
                            audio_arr = audio_arr.reshape(-1, channels)
                        sd.play(audio_arr, samplerate=rate, blocking=True)
            except Exception as e:
                print(f"[AudioManager] Error playing sound effect: {e}")

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    def stop(self):
        """Gracefully stop and close audio streams."""
        self._stop_event.set()
        self.interrupt()
        if self._input_stream:
            try:
                self._input_stream.stop()
                self._input_stream.close()
            except Exception:
                pass
        if self._output_stream:
            try:
                self._output_stream.stop()
                self._output_stream.close()
            except Exception:
                pass
        self.is_recording = False
        self.is_playing = False
