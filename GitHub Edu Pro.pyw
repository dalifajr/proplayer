#!/usr/bin/env pythonw
"""Double-click launcher for GitHub Edu Pro Tool.
.pyw extension runs with pythonw.exe — no console window on Windows."""
import os, sys

# Ensure working directory is the script's folder
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Add script directory to Python path
if os.path.dirname(os.path.abspath(__file__)) not in sys.path:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import main

if __name__ == "__main__":
    main()
