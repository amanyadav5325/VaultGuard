"""
Clipboard fallback — tries pyperclip first, falls back silently.
"""

def copy(text: str):
    try:
        import pyperclip
        pyperclip.copy(text)
    except Exception:
        pass  # Tkinter's clipboard_append is used as primary fallback in GUI
