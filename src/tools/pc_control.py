"""PC and OS Control Tool for JARVIS.

Handles Windows system tasks:
- Volume control (up, down, mute, set level)
- Screen/workstation locking
- System power control (sleep, shutdown, restart, cancel shutdown)
- System status (CPU, RAM, Battery)
"""

import ctypes
import os
import subprocess
import psutil
from typing import Dict, Any

# Windows Virtual Key Codes for Audio
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002

def _send_key(vk_code: int):
    """Simulate a media key press and release on Windows."""
    ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY, 0)
    ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)

def set_volume(action: str, steps: int = 5) -> Dict[str, Any]:
    """Control system volume.
    
    Args:
        action: 'up', 'down', 'mute', or 'unmute'
        steps: Number of steps to increment/decrement (each step is typically 2% on Windows)
    """
    action = action.lower().strip()
    try:
        if action == "up":
            for _ in range(max(1, steps)):
                _send_key(VK_VOLUME_UP)
            return {"status": "success", "message": f"Volume increased by {steps} steps, Sir."}
        elif action == "down":
            for _ in range(max(1, steps)):
                _send_key(VK_VOLUME_DOWN)
            return {"status": "success", "message": f"Volume decreased by {steps} steps, Sir."}
        elif action in ("mute", "unmute", "toggle_mute"):
            _send_key(VK_VOLUME_MUTE)
            return {"status": "success", "message": "System mute toggled, Sir."}
        else:
            return {"status": "error", "message": f"Unknown volume action: '{action}'."}
    except Exception as e:
        return {"status": "error", "message": f"Failed to adjust volume: {str(e)}"}

def lock_workstation() -> Dict[str, Any]:
    """Lock the Windows workstation immediately."""
    try:
        result = ctypes.windll.user32.LockWorkStation()
        if result:
            return {"status": "success", "message": "Workstation locked successfully, Sir."}
        else:
            return {"status": "error", "message": "Unable to lock workstation."}
    except Exception as e:
        return {"status": "error", "message": f"Lock error: {str(e)}"}

def system_power(action: str, confirm: bool = False) -> Dict[str, Any]:
    """Manage workstation power states.
    
    Args:
        action: 'sleep', 'shutdown', 'restart', or 'cancel_shutdown'
        confirm: Confirmation flag for destructive actions
    """
    action = action.lower().strip()
    try:
        if action == "sleep":
            # SetSuspendState(bHibernate=0, bForce=0, bWakeupEventsDisabled=0)
            ctypes.windll.PowrProf.SetSuspendState(0, 0, 0)
            return {"status": "success", "message": "Entering sleep mode, Sir."}
        
        elif action == "cancel_shutdown":
            subprocess.run(["shutdown", "/a"], capture_output=True, check=False)
            return {"status": "success", "message": "Pending shutdown has been cancelled, Sir."}
        
        elif action in ("shutdown", "restart"):
            if not confirm:
                return {
                    "status": "confirmation_required",
                    "message": f"Sir, please confirm if you really wish to {action} the system."
                }
            
            flag = "/s" if action == "shutdown" else "/r"
            # 30 second grace period to allow aborting
            subprocess.run(["shutdown", flag, "/t", "30", "/c", "JARVIS initiated system power sequence"], check=False)
            return {"status": "success", "message": f"System {action} initiated with a 30 second countdown, Sir."}
        
        else:
            return {"status": "error", "message": f"Unknown power action: '{action}'"}
    except Exception as e:
        return {"status": "error", "message": f"Power control failed: {str(e)}"}

def get_system_status() -> Dict[str, Any]:
    """Retrieve current system resource usage: CPU, RAM, and Battery status."""
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        battery = psutil.sensors_battery()
        
        battery_info = "Desktop / No battery detected"
        if battery:
            plugged_str = "Plugged in" if battery.power_plugged else "On battery"
            battery_info = f"{battery.percent}% ({plugged_str})"
            
        return {
            "status": "success",
            "cpu_percent": cpu,
            "ram_used_gb": round(mem.used / (1024 ** 3), 2),
            "ram_total_gb": round(mem.total / (1024 ** 3), 2),
            "ram_percent": mem.percent,
            "battery": battery_info,
            "message": f"CPU is at {cpu}%, RAM utilization is at {mem.percent}%, and battery is {battery_info}, Sir."
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to retrieve system status: {str(e)}"}

def dismiss_session(farewell_phrase: str = "User concluded session", **kwargs) -> Dict[str, Any]:
    """Put JARVIS into standby mode when the user says goodbye or finishes conversation.
    
    Args:
        farewell_phrase: The parting words spoken by user or reason for ending.
    """
    return {
        "status": "success",
        "action": "dismiss",
        "farewell_phrase": farewell_phrase,
        "message": f"Entering standby mode: {farewell_phrase}"
    }

