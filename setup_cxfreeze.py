from cx_Freeze import setup, Executable
import sys
import os

# Build options
build_options = {
    'packages': ['cv2', 'numpy', 'PIL', 'tkinter'],
    'excludes': ['test', 'unittest'],
    'include_files': [],
    'optimize': 2,
}

# Base for Windows GUI application
base = None
if sys.platform == "win32":
    base = "Win32GUI"

# Executable configuration
executables = [
    Executable(
        script="src/main.py",
        base=base,
        target_name="SubmarineColorCorrection2.0.exe"
    )
]

setup(
    name="SubmarineColorCorrection",
    version="2.0",
    description="Advanced color correction for submarine and underwater images",
    options={'build_exe': build_options},
    executables=executables
)
