import sys
import os
from cx_Freeze import setup, Executable

# Add the src directory to sys.path
sys.path.insert(0, 'src')

# Base for Windows GUI application
base = "Win32GUI" if sys.platform == "win32" else None

# Build options
build_exe_options = {
    "packages": ["cv2", "PIL", "numpy", "tkinter", "pathlib"],
    "excludes": ["test", "unittest", "distutils", "setuptools"],
    "include_files": [],
    "optimize": 2
}

# Create executable
executable = Executable(
    script="src/main.py",
    base=base,
    target_name="SubmarineColorCorrection2.0_SingleFile.exe",
    icon=None
)

setup(
    name="SubmarineColorCorrection2.0",
    version="2.0",
    description="Submarine Color Correction Tool",
    author="Your Name",
    executables=[executable],
    options={"build_exe": build_exe_options}
)
