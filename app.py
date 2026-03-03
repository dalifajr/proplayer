#!/usr/bin/env python3
"""GitHub Edu Pro — pywebview entry point."""
import os, sys, webview
from urllib.request import pathname2url

# Ensure working dir is the project root (writable files: sessions, settings, logs)
if getattr(sys, 'frozen', False):
    BASE = os.path.dirname(sys.executable)
    # Bundled data (ui/, keywords.txt) lives in the temp extraction dir
    _BUNDLE = sys._MEIPASS
else:
    BASE = os.path.dirname(os.path.abspath(__file__))
    _BUNDLE = BASE
os.chdir(BASE)

from api import Api

def main():
    api = Api()
    ui_dir = os.path.join(_BUNDLE, "ui")
    index_path = os.path.join(ui_dir, "index.html")
    # Convert file path to proper file:// URL (handles spaces and special chars)
    index_url = "file:///" + pathname2url(index_path).lstrip("/")

    window = webview.create_window(
        "GitHub Edu Pro 🚀 by Dzul",
        url=index_url,
        js_api=api,
        width=860,
        height=920,
        min_size=(720, 600),
        text_select=True,
    )
    api._window = window
    webview.start(debug=("--debug" in sys.argv))

if __name__ == "__main__":
    main()
