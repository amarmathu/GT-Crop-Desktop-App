# setup.py
import sys
from cx_Freeze import setup, Executable

# Dependencies are automatically detected, but you may need to include some manually
build_exe_options = {
    "packages": ["PIL", "tkinter", "customtkinter", "tkinterdnd2"],
    "include_files": [
        "background.png",   # if used
        "gtcrop_config.json",  # optional: include default config
        # Add any other data files your app needs
    ],
    "excludes": ["tkinter.test", "unittest"],
    "optimize": 2,
}

# MSI-specific options
bdist_msi_options = {
    "upgrade_code": "{304fb34a-a356-46cc-a91f-8ca2e4bbd68a}",  # ⚠️ Generate your own GUID!
    "add_to_path": False,
    "initial_target_dir": r"[ProgramFilesFolder]\GT Crop",
    "target_name": "gtcrop.msi",
}

base = "Win32GUI" if sys.platform == "win32" else None

executables = [
    Executable(
        "main.py",
        base=base,
        target_name="gtcrop.exe",
        icon="icon.ico"  # optional: add an .ico file
    )
]

setup(
    name="GT Crop",
    version="1.0.0",
    description="GT Crop – Image Processing Tool",
    options={
        "build_exe": build_exe_options,
        "bdist_msi": bdist_msi_options,
    },
    executables=executables
)