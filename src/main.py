"""
Clean, focused main entry point.
Simple orchestration of the application components.
"""
import tkinter as tk
import sys
import os
import logging
from pathlib import Path

# Add src directory to Python path for imports
src_dir = Path(__file__).parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# Import from absolute paths within src
from ui.main_window_clean import MainWindowClean
from services.logger_service import setup_logging


def main():
    """Application entry point."""
    try:
        # Create and run the main application
        root = tk.Tk()
        app = MainWindowClean(root)
        
        # Configure window
        root.title("Submarine Color Correction Tool v2.0")
        root.geometry("1200x900")
        root.minsize(800, 600)
        
        # Start the application
        root.mainloop()
        
    except Exception as e:
        print(f"Fatal error starting application: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
