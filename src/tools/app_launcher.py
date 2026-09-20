"""Application and URL Launcher Tool for JARVIS.

Handles opening system applications, default web browsers, specific URLs,
and Explorer directories.
"""

import os
import subprocess
import webbrowser
from typing import Dict, Any, Optional

# Common Web Applications & Friendly URL Shortcuts
WEB_APPS = {
    "yt": "https://www.youtube.com",
    "youtube": "https://www.youtube.com",
    "gmail": "https://mail.google.com",
    "google": "https://www.google.com",
    "github": "https://github.com",
    "chatgpt": "https://chatgpt.com",
    "twitter": "https://x.com",
    "x": "https://x.com",
    "reddit": "https://www.reddit.com",
    "netflix": "https://www.netflix.com",
    "instagram": "https://www.instagram.com",
    "whatsapp": "https://web.whatsapp.com",
    "wa": "https://web.whatsapp.com",
}

# Common Windows App Shortcuts & Executables
KNOWN_APPS = {
    "vscode": "code",
    "vs code": "code",
    "visual studio code": "code",
    "chrome": "chrome",
    "google chrome": "chrome",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "firefox": "firefox",
    "spotify": "spotify",
    "notepad": "notepad",
    "calc": "calc",
    "calculator": "calc",
    "terminal": "wt",
    "windows terminal": "wt",
    "cmd": "cmd",
    "powershell": "powershell",
    "explorer": "explorer",
    "file explorer": "explorer",
    "taskmgr": "taskmgr",
    "task manager": "taskmgr",
    "settings": "start ms-settings:",
    "moza pit house": "MOZA Pit House",
    "moza": "MOZA Pit House",
    "pit house": "MOZA Pit House",
    "discord": "discord",
    "steam": "steam",
    "obs": "obs64",
    "obs studio": "obs64",
    "youtube": "https://www.youtube.com",
    "yt": "https://www.youtube.com",
}

def find_start_menu_app(app_name: str) -> Optional[str]:
    """Search for matching .lnk or .url shortcut in Windows Start Menu directories."""
    search_dirs = [
        os.path.expandvars(r"%ProgramData%\Microsoft\Windows\Start Menu\Programs"),
        os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
    ]
    app_clean = "".join(c for c in app_name.lower() if c.isalnum())
    # Prevent short abbreviations (e.g. 'yt') from matching unrelated software (like 'python')
    if len(app_clean) < 3:
        return None

    for sdir in search_dirs:
        if not os.path.exists(sdir):
            continue
        for root, _, files in os.walk(sdir):
            for f in files:
                if f.lower().endswith((".lnk", ".url")):
                    base = os.path.splitext(f)[0]
                    base_clean = "".join(c for c in base.lower() if c.isalnum())
                    if app_clean == base_clean or (len(app_clean) >= 4 and (app_clean in base_clean or base_clean in app_clean)):
                        return os.path.join(root, f)
    return None

def launch_application(app_name: str) -> Dict[str, Any]:
    """Launch a desktop application or web app by name with intelligent shortcut discovery.
    
    Args:
        app_name: Name of application (e.g. 'chrome', 'vscode', 'yt', 'youtube', 'moza pit house', 'spotify', 'calculator')
    """
    cleaned_name = app_name.lower().strip()
    
    # 0. Check web app aliases first
    if cleaned_name in WEB_APPS:
        target_url = WEB_APPS[cleaned_name]
        try:
            webbrowser.open(target_url)
            return {
                "status": "success",
                "app": app_name,
                "url": target_url,
                "message": f"Opening {app_name} in your browser, Sir."
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to open {app_name}: {str(e)}"}

    # 1. Check known aliases
    if cleaned_name in KNOWN_APPS:
        executable = KNOWN_APPS[cleaned_name]
        try:
            if executable.startswith(("http://", "https://")):
                webbrowser.open(executable)
                return {
                    "status": "success",
                    "app": app_name,
                    "url": executable,
                    "message": f"Opening {app_name} in your browser, Sir."
                }
            elif executable.startswith("start "):
                subprocess.Popen(f"cmd.exe /c {executable}", shell=True)
            else:
                subprocess.Popen(f'cmd.exe /c start "" "{executable}"', shell=True)
            return {
                "status": "success",
                "app": app_name,
                "message": f"Opening {app_name}, Sir."
            }
        except Exception:
            pass

    # 2. Check Windows Start Menu shortcuts (.lnk)
    shortcut_path = find_start_menu_app(cleaned_name)
    if shortcut_path and os.path.exists(shortcut_path):
        try:
            os.startfile(shortcut_path)
            return {
                "status": "success",
                "app": app_name,
                "message": f"Launching {app_name} from Start Menu, Sir."
            }
        except Exception as e:
            pass

    # 3. Fallback: attempt direct shell execution
    try:
        subprocess.Popen(f'cmd.exe /c start "" "{cleaned_name}"', shell=True)
        return {
            "status": "success",
            "app": app_name,
            "message": f"Opening {app_name}, Sir."
        }
    except Exception as e:
        return {
            "status": "error",
            "app": app_name,
            "message": f"Failed to launch {app_name}: {str(e)}"
        }

def open_url(url: str) -> Dict[str, Any]:
    """Open a website or URL in the default web browser.
    
    Args:
        url: Web URL or site name (e.g. 'https://github.com', 'google.com', 'youtube.com', 'yt', 'youtube')
    """
    cleaned_url = url.strip().lower()
    
    # Check friendly shortcuts
    if cleaned_url in WEB_APPS:
        target_url = WEB_APPS[cleaned_url]
    else:
        target_url = url.strip()
        if not target_url.startswith(("http://", "https://")):
            if "." not in target_url:
                target_url = f"https://www.{target_url}.com"
            else:
                target_url = f"https://{target_url}"
        
    try:
        webbrowser.open(target_url)
        return {
            "status": "success",
            "url": target_url,
            "message": f"Navigating to {target_url}, Sir."
        }
    except Exception as e:
        return {
            "status": "error",
            "url": target_url,
            "message": f"Failed to open {target_url}: {str(e)}"
        }

def open_path(path: str) -> Dict[str, Any]:
    """Open a file or directory in Windows File Explorer.
    
    Args:
        path: Absolute or relative file/directory path
    """
    resolved_path = os.path.abspath(os.path.expanduser(os.path.expandvars(path)))
    if not os.path.exists(resolved_path):
        return {
            "status": "error",
            "path": path,
            "message": f"Path '{path}' does not exist, Sir."
        }
        
    try:
        os.startfile(resolved_path)
        return {
            "status": "success",
            "path": resolved_path,
            "message": f"Opening folder {os.path.basename(resolved_path)}, Sir."
        }
    except Exception as e:
        return {
            "status": "error",
            "path": path,
            "message": f"Failed to open path: {str(e)}"
        }

def write_to_notepad(text: str, title: str = "JARVIS_Note") -> Dict[str, Any]:
    """Create or update a text note and open it in Windows Notepad.
    
    Args:
        text: The text content to write into Notepad.
        title: Optional title or filename for the note.
    """
    try:
        desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        if not os.path.exists(desktop_dir):
            desktop_dir = os.path.expanduser("~")

        safe_title = "".join(c for c in (title or "JARVIS_Note") if c.isalnum() or c in " ._-").strip()
        if not safe_title:
            safe_title = "JARVIS_Note"
        if not safe_title.endswith(".txt"):
            safe_title += ".txt"

        file_path = os.path.join(desktop_dir, safe_title)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)

        subprocess.Popen(["notepad.exe", file_path])
        return {
            "status": "success",
            "file": file_path,
            "message": f"Written to {safe_title} and opened in Notepad, Sir."
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to write to Notepad: {str(e)}"}

def type_text(text: str) -> Dict[str, Any]:
    """Simulate keyboard typing of text into the currently active focused window.
    
    Args:
        text: The text string to type into the active window.
    """
    try:
        import keyboard
        keyboard.write(text)
        return {
            "status": "success",
            "text": text,
            "message": f"Typed text into active window, Sir."
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to type text: {str(e)}"}

