"""
cx_Freeze setup for JJClicker Windows MSI installer.

Usage (run on Windows):
    pip install cx_Freeze pystray pillow pynput
    python setup_cx_freeze.py bdist_msi
"""
import sys
from pathlib import Path
from cx_Freeze import setup, Executable

# Packages to include explicitly
build_exe_options = {
    "packages": [
        "tkinter",
        "pynput",
        "pystray",
        "PIL",
        "threading",
        "json",
        "pathlib",
        "ctypes",
    ],
    "excludes": ["AppKit", "Quartz"],
    "include_files": [],
    "optimize": 1,
}

# MSI installer options
bdist_msi_options = {
    "upgrade_code":       "{12345678-ABCD-1234-ABCD-1234567890AB}",  # keep stable across versions
    "add_to_path":        False,
    "initial_target_dir": r"[ProgramFilesFolder]\JJClicker",
    "install_icon":       None,   # set to "icon.ico" if you have one
}

setup(
    name="JJClicker",
    version="1.0.0",
    description="Free & open-source macro automation",
    author="Juraj Jajčaj",
    options={
        "build_exe":  build_exe_options,
        "bdist_msi":  bdist_msi_options,
    },
    executables=[
        Executable(
            script="JJClicker.py",
            base="Win32GUI",          # hides the console window
            target_name="JJClicker.exe",
            icon=None,                # set to "icon.ico" if you have one
            shortcut_name="JJClicker",
            shortcut_dir="DesktopFolder",
        )
    ],
)
