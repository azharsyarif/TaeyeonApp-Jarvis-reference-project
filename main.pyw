"""JARVIS Windows Native Voice Assistant - Windowless Daemon Entry Point.

Can be run via pythonw.exe to suppress console/terminal window (FR-1.1).
"""

from main import JarvisDaemon

if __name__ == "__main__":
    daemon = JarvisDaemon()
    daemon.start()
