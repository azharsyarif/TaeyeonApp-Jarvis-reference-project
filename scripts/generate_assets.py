import os
import math
import struct
import wave
from PIL import Image, ImageDraw

def generate_chime(file_path: str, is_chime_in: bool = True):
    sample_rate = 44100
    duration = 0.28  # seconds
    n_samples = int(sample_rate * duration)
    
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with wave.open(file_path, 'wb') as wav_file:
        wav_file.setnchannels(1)        # mono
        wav_file.setsampwidth(2)       # 16-bit
        wav_file.setframerate(sample_rate)
        
        frames = bytearray()
        for i in range(n_samples):
            t = i / sample_rate
            # Upward dual chord for chime_in, downward for chime_out
            if is_chime_in:
                # Frequencies: E5 (659.25Hz) and B5 (987.77Hz)
                freq1 = 659.25
                freq2 = 987.77
            else:
                # Frequencies: B5 (987.77Hz) and G5 (783.99Hz)
                freq1 = 987.77
                freq2 = 659.25
            
            # Smooth attack and decay envelope
            envelope = math.sin(math.pi * (i / n_samples)) ** 0.8
            # Gentle exponential decay
            decay = math.exp(-3.5 * t)
            env = envelope * decay
            
            val1 = math.sin(2.0 * math.pi * freq1 * t)
            val2 = 0.6 * math.sin(2.0 * math.pi * freq2 * t)
            val = (val1 + val2) * 0.5 * env
            
            sample = int(val * 24000.0)
            sample = max(-32768, min(32767, sample))
            frames.extend(struct.pack('<h', sample))
            
        wav_file.writeframes(frames)
    print(f"Generated chime audio: {file_path}")

def generate_tray_icon(file_path: str):
    size = (64, 64)
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    center = 32
    # Outer glow
    draw.ellipse([8, 8, 56, 56], outline=(0, 240, 255, 180), width=3)
    # Inner ring
    draw.ellipse([16, 16, 48, 48], outline=(0, 200, 255, 230), width=2)
    # Center core (Arc reactor vibe)
    draw.ellipse([24, 24, 40, 40], fill=(0, 255, 255, 255))
    # 4 reactor segments
    draw.line([(32, 10), (32, 22)], fill=(0, 240, 255, 255), width=2)
    draw.line([(32, 42), (32, 54)], fill=(0, 240, 255, 255), width=2)
    draw.line([(10, 32), (22, 32)], fill=(0, 240, 255, 255), width=2)
    draw.line([(42, 32), (54, 32)], fill=(0, 240, 255, 255), width=2)
    
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    image.save(file_path, "PNG")
    print(f"Generated tray icon: {file_path}")

if __name__ == "__main__":
    assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
    generate_chime(os.path.join(assets_dir, "chime_in.wav"), is_chime_in=True)
    generate_chime(os.path.join(assets_dir, "chime_out.wav"), is_chime_in=False)
    generate_tray_icon(os.path.join(assets_dir, "tray_icon.png"))
