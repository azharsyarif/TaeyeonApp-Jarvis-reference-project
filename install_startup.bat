@echo off
setlocal

echo [JARVIS] Installing JARVIS to Windows Startup...

set "SCRIPT_DIR=%~dp0"
set "MAIN_SCRIPT=%SCRIPT_DIR%main.pyw"
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT_PATH=%STARTUP_FOLDER%\JARVIS.vbs"

echo Creating background launcher at "%SHORTCUT_PATH%"...

(
echo Set WshShell = CreateObject^("WScript.Shell"^)
echo WshShell.Run "pythonw.exe """ ^& "%MAIN_SCRIPT%" ^& """", 0, False
) > "%SHORTCUT_PATH%"

if exist "%SHORTCUT_PATH%" (
    echo [SUCCESS] JARVIS background startup launcher installed successfully!
    echo Location: %SHORTCUT_PATH%
) else (
    echo [ERROR] Failed to create startup launcher.
)

pause
