"""Unit tests for JARVIS Gemini Live API Client configuration and dispatch."""

from src.core.live_client import LiveClient

def test_live_client_declarations():
    states = []
    client = LiveClient(
        api_key="mock_test_key",
        model="gemini-3.1-flash-live-preview",
        voice_name="Puck",
        system_instruction="Test Prompt",
        on_state_change=lambda s: states.append(s)
    )
    
    decls = client._build_function_declarations()
    assert len(decls) == 12
    
    decl_names = [d["name"] for d in decls]
    assert "set_volume" in decl_names
    assert "lock_workstation" in decl_names
    assert "system_power" in decl_names
    assert "get_system_status" in decl_names
    assert "launch_application" in decl_names
    assert "open_url" in decl_names
    assert "capture_screen" in decl_names
    assert "execute_powershell" in decl_names
    assert "open_path" in decl_names
    assert "dismiss_session" in decl_names
    assert "write_to_notepad" in decl_names
    assert "type_text" in decl_names

    # Every declared tool must be resolvable by the dispatcher registry
    from src.tools import TOOL_FUNCTIONS
    for name in decl_names:
        assert name in TOOL_FUNCTIONS, f"Declared tool '{name}' missing from dispatcher"

    # Test state transitions
    client.set_state("listening")
    client.set_state("thinking")
    client.set_state("speaking")
    client.set_state("idle")
    
    assert states == ["listening", "thinking", "speaking", "idle"]
