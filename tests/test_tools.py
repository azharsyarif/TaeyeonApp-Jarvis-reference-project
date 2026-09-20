"""Unit tests for JARVIS OS action tools."""

import io
from PIL import Image
from src.tools.pc_control import get_system_status, set_volume, system_power
from src.tools.app_launcher import launch_application, open_url, open_path
from src.tools.screen_capture import capture_screen, capture_screen_bytes
from src.tools.system_exec import execute_powershell
from src.tools import dispatch_tool_call, TOOL_FUNCTIONS

def test_system_status():
    status = get_system_status()
    assert status["status"] == "success"
    assert "cpu_percent" in status
    assert "ram_percent" in status
    assert "battery" in status
    assert "Sir" in status["message"]

def test_volume_control():
    res = set_volume("up", steps=1)
    assert res["status"] == "success"
    res_mute = set_volume("toggle_mute")
    assert res_mute["status"] == "success"
    res_err = set_volume("unknown_action")
    assert res_err["status"] == "error"

def test_system_power_safety():
    # Destructive power operations must require confirmation
    res_unconfirmed = system_power("shutdown", confirm=False)
    assert res_unconfirmed["status"] == "confirmation_required"
    assert "confirm" in res_unconfirmed["message"]

def test_app_launcher_dry():
    # Test valid handling of url
    res_url = open_url("https://example.com")
    assert res_url["status"] == "success"
    assert res_url["url"] == "https://example.com"
    
    # Test nonexistent path
    res_path = open_path("C:\\non_existent_folder_xyz_123")
    assert res_path["status"] == "error"

def test_screen_capture_in_memory():
    jpeg_bytes = capture_screen_bytes(quality=50, max_size=(640, 360))
    assert isinstance(jpeg_bytes, bytes)
    assert len(jpeg_bytes) > 0
    
    # Verify it is valid JPEG image data
    img = Image.open(io.BytesIO(jpeg_bytes))
    assert img.format == "JPEG"
    assert img.size[0] <= 640
    assert img.size[1] <= 360
    
    # Test tool endpoint
    tool_res = capture_screen(quality=50)
    assert tool_res["status"] == "success"
    assert tool_res["mime_type"] == "image/jpeg"
    assert "_bytes" in tool_res

def test_powershell_execution():
    res = execute_powershell("Write-Output 'Hello JARVIS'", safe_mode=True)
    assert res["status"] == "success"
    assert "Hello JARVIS" in res["output"]

def test_powershell_safety_guardrails():
    # Destructive command should be blocked
    res_blocked = execute_powershell("rmdir /s /q C:\\Windows", safe_mode=True)
    assert res_blocked["status"] == "blocked"
    assert "blocked" in res_blocked["message"]

def test_tool_dispatcher():
    # Test dispatcher integration
    res = dispatch_tool_call("get_system_status", {})
    assert res["status"] == "success"
    
    res_unknown = dispatch_tool_call("unknown_tool_xyz", {})
    assert res_unknown["status"] == "error"

def test_write_to_notepad_and_typing(tmp_path, monkeypatch):
    from src.tools.app_launcher import write_to_notepad, type_text
    
    # Mock Desktop dir to tmp_path
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    
    # Test write_to_notepad creates file
    res = write_to_notepad("Hello from JARVIS test!", title="test_note")
    assert res["status"] == "success"
    assert "test_note.txt" in res["file"]
    
    # Test typing simulation
    res_type = type_text("test typing")
    assert res_type["status"] == "success"

