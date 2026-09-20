"""Unit tests for JARVIS Audio Pipeline and Audio Manager."""

import struct
from src.core.audio_manager import calculate_rms, AudioManager

def test_calculate_rms_silence():
    # 1024 samples of zero PCM
    silence = b'\x00\x00' * 1024
    rms = calculate_rms(silence)
    assert rms == 0.0

def test_calculate_rms_signal():
    # 512 samples with maximum amplitude
    max_pcm = struct.pack("<512h", *[30000] * 512)
    rms = calculate_rms(max_pcm)
    assert rms > 0.8

def test_calculate_rms_empty():
    assert calculate_rms(b'') == 0.0

def test_audio_manager_queue_and_interrupt():
    am = AudioManager(input_rate=16000, output_rate=24000)
    
    # Enqueue audio
    test_pcm = b'\x01\x00' * 2048
    am.play_audio(test_pcm)
    assert am.is_playing is True
    assert not am._output_queue.empty()
    
    # Trigger barge-in interrupt
    am.interrupt()
    assert am.is_playing is False
    assert am._output_queue.empty()
    
    am.stop()
