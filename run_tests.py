"""JARVIS Test Runner & Diagnostic Suite.

Runs all unit tests, verifies system components, and prints a comprehensive health summary.
"""

import sys
import subprocess
import os

def run_diagnostics():
    print("=" * 60)
    print("   JARVIS WINDOWS VOICE ASSISTANT - DIAGNOSTIC & TEST RUNNER")
    print("=" * 60)
    
    # 1. Environment Check
    print("\n[1/3] Environment & Dependency Check:")
    deps = [
        ("google.genai", "Google GenAI SDK"),
        ("sounddevice", "PortAudio / sounddevice"),
        ("mss", "Fast Screen Capture"),
        ("PyQt6", "PyQt6 GUI Framework"),
        ("PIL", "Pillow Image Processing"),
        ("psutil", "System Resource Monitor"),
        ("keyboard", "Global Hotkey Hook"),
        ("pytest", "Testing Framework")
    ]
    
    all_deps_ok = True
    for mod, label in deps:
        try:
            __import__(mod)
            print(f"  [OK] {label} ({mod})")
        except ImportError:
            print(f"  [FAIL] {label} ({mod}) is NOT installed.")
            all_deps_ok = False

    # 2. Config & Assets Check
    print("\n[2/3] Asset & Configuration Check:")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    required_files = [
        "config/settings.json",
        "config/system_prompt.txt",
        "assets/chime_in.wav",
        "assets/chime_out.wav",
        "assets/tray_icon.png",
        "main.py",
        "main.pyw",
        "install_startup.bat"
    ]
    for rel_path in required_files:
        full_path = os.path.join(base_dir, rel_path)
        if os.path.exists(full_path):
            print(f"  [OK] {rel_path}")
        else:
            print(f"  [FAIL] Missing {rel_path}")

    # 3. Pytest Execution
    print("\n[3/3] Executing Automated Pytest Suite:")
    print("-" * 60)
    cmd = [sys.executable, "-m", "pytest", "tests", "-v", "--tb=short"]
    result = subprocess.run(cmd)
    
    print("-" * 60)
    if result.returncode == 0:
        print("[SUCCESS] All JARVIS tests passed flawlessly!")
    else:
        print(f"[FAIL] Test execution finished with exit code {result.returncode}")
        
    return result.returncode

if __name__ == "__main__":
    sys.exit(run_diagnostics())
