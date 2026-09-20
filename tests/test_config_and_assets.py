"""Unit tests for JARVIS configuration and assets."""

import json
import os
import wave
from PIL import Image

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def test_settings_json():
    settings_path = os.path.join(BASE_DIR, "config", "settings.json")
    assert os.path.exists(settings_path), "settings.json does not exist"
    
    with open(settings_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    assert "activation" in data
    assert "gemini" in data
    assert "audio" in data
    assert "hud" in data
    assert "tools" in data
    
    assert data["activation"]["hotkey"] == "alt+space"
    assert data["gemini"]["model"] == "gemini-3.1-flash-live-preview"
    assert data["audio"]["input_sample_rate"] == 16000
    assert data["audio"]["output_sample_rate"] == 24000

def test_system_prompt():
    prompt_path = os.path.join(BASE_DIR, "config", "system_prompt.txt")
    assert os.path.exists(prompt_path), "system_prompt.txt does not exist"
    
    with open(prompt_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    assert len(content) > 50
    assert "JARVIS" in content
    assert "Sir" in content

def test_chime_in_audio():
    chime_path = os.path.join(BASE_DIR, "assets", "chime_in.wav")
    assert os.path.exists(chime_path), "chime_in.wav does not exist"
    
    with wave.open(chime_path, "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 44100
        assert wf.getnframes() > 0

def test_chime_out_audio():
    chime_path = os.path.join(BASE_DIR, "assets", "chime_out.wav")
    assert os.path.exists(chime_path), "chime_out.wav does not exist"
    
    with wave.open(chime_path, "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 44100
        assert wf.getnframes() > 0

def test_tray_icon():
    icon_path = os.path.join(BASE_DIR, "assets", "tray_icon.png")
    assert os.path.exists(icon_path), "tray_icon.png does not exist"
    
    with Image.open(icon_path) as img:
        assert img.format == "PNG"
        assert img.size == (64, 64)
        assert img.mode == "RGBA"
