"""Tools registry and dispatcher for JARVIS AI assistant."""

from typing import Dict, Any, Callable
from .pc_control import set_volume, lock_workstation, system_power, get_system_status, dismiss_session
from .app_launcher import launch_application, open_url, open_path, write_to_notepad, type_text
from .screen_capture import capture_screen
from .system_exec import execute_powershell

TOOL_FUNCTIONS: Dict[str, Callable] = {
    "set_volume": set_volume,
    "lock_workstation": lock_workstation,
    "system_power": system_power,
    "get_system_status": get_system_status,
    "dismiss_session": dismiss_session,
    "launch_application": launch_application,
    "open_url": open_url,
    "open_path": open_path,
    "write_to_notepad": write_to_notepad,
    "type_text": type_text,
    "capture_screen": capture_screen,
    "execute_powershell": execute_powershell,
}

def get_tool_callables():
    """Return list of tool functions directly compatible with google-genai LiveConnectConfig."""
    return list(TOOL_FUNCTIONS.values())

def dispatch_tool_call(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a registered tool by name with arguments and return result."""
    func = TOOL_FUNCTIONS.get(tool_name)
    if not func:
        return {"status": "error", "message": f"Unknown tool: {tool_name}"}
    try:
        return func(**args)
    except Exception as e:
        return {"status": "error", "message": f"Error executing {tool_name}: {str(e)}"}
