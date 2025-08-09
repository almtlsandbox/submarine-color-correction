"""
Updated build configuration for the new modular structure.
"""
import sys
from cx_Freeze import setup, Executable
import os

# Get the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, "src")

# Build options
build_options = {
    'packages': [],  # Let cx_Freeze auto-detect
    'includes': ['tkinter', 'tkinter.filedialog', 'tkinter.messagebox', 'tkinter.ttk'],
    'excludes': [],
    'include_files': [],
    'build_exe': 'ReleaseColorCorrection/lib',  # Directory structure
    'path': [src_dir]  # Add src directory to path
}

# Define the executable
base = 'Win32GUI' if sys.platform == 'win32' else None
executable = Executable(
    script=os.path.join(src_dir, 'main.py'),
    base=base,
    target_name='SubmarineColorCorrectionV2.0_Modular.exe',
    icon=None
)

setup(
    name='Submarine Color Correction',
    version='2.0',
    description='Advanced underwater image color correction tool with modular architecture',
    author='Submarine Color Correction Team',
    options={'build_exe': build_options},
    executables=[executable]
)
