"""
Interactive Handout Generator
Primary application entry point.
"""
import sys
import platform
import tkinter as tk
from gui.app import HandoutGeneratorApp


def _enable_dpi_awareness():
    """Enable per-monitor DPI awareness on Windows so the UI is crisp on high-DPI displays."""
    if platform.system() != "Windows":
        return
    try:
        import ctypes
        # Try per-monitor V2 awareness (Windows 10 Creators Update+)
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            import ctypes
            # Fallback: system DPI aware (Windows Vista+)
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def main():
    _enable_dpi_awareness()
    root = tk.Tk()
    app = HandoutGeneratorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
