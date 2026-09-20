"""Sanitized PowerShell Execution Tool for JARVIS.

Executes developer command line tasks securely with guardrails and timeouts (FR-5.3 & Section 8).
"""

import re
import subprocess
from typing import Dict, Any

# Dangerous command patterns blocked in safe mode
DANGEROUS_PATTERNS = [
    r"\brmdir\s+/[sq]\b",
    r"\bdel\s+/[sqf]\b",
    r"\bformat\s+[a-z]:\b",
    r"\bremove-item\s+.*-recurse\s+.*c:\\\b",
    r"\bdiskpart\b",
    r"\bdrop\s+database\b",
    r"\bshutdown\s+/[sr]\b"  # Must use pc_control instead
]

def execute_powershell(command: str, timeout_seconds: int = 15, safe_mode: bool = True) -> Dict[str, Any]:
    """Execute a PowerShell command with security safeguards.
    
    Args:
        command: PowerShell command to run
        timeout_seconds: Execution timeout
        safe_mode: Enforce blocklist against destructive system commands
    """
    clean_command = command.strip()
    
    if safe_mode:
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, clean_command, re.IGNORECASE):
                return {
                    "status": "blocked",
                    "command": clean_command,
                    "message": "Command was blocked for safety reasons, Sir. Destructive operations require manual confirmation."
                }
                
    try:
        process = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", clean_command],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            encoding="utf-8",
            errors="replace"
        )
        
        stdout = process.stdout.strip()
        stderr = process.stderr.strip()
        
        # Limit output length for concise voice readout
        max_chars = 1000
        truncated_out = stdout[:max_chars] + ("... [truncated]" if len(stdout) > max_chars else "")
        
        if process.returncode == 0:
            return {
                "status": "success",
                "return_code": 0,
                "output": truncated_out or "Command executed successfully with no output.",
                "message": f"Command executed successfully, Sir."
            }
        else:
            return {
                "status": "error",
                "return_code": process.returncode,
                "output": stderr or truncated_out,
                "message": f"Command returned exit code {process.returncode}: {stderr[:200]}"
            }
            
    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "message": f"Command timed out after {timeout_seconds} seconds, Sir."
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to execute command: {str(e)}"
        }
