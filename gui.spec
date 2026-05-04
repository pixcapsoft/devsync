# -*- mode: python ; coding: utf-8 -*-
# gui.spec — DevSync GUI  (onefile, no CLI code inside)
#
# Output: dist\gui\DevSyncGUI.exe
# At runtime the GUI looks for cli\cli.exe next to itself.

from PyInstaller.utils.hooks import collect_data_files

# customtkinter ships JSON themes and PNG images — they must travel with the exe
ctk_datas = collect_data_files("customtkinter")

a = Analysis(
    ["gui.py"],
    pathex=[],
    binaries=[],
    datas=ctk_datas,
    hiddenimports=[
        # tkinter extras sometimes missed on some Python installs
        "tkinter",
        "tkinter.filedialog",
        "tkinter.messagebox",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Explicitly exclude CLI packages — they live in cli.exe, not here
    excludes=["watchdog", "devsync", "adb_bridge", "http_bridge", "watcher"],
    noarchive=False,
    optimize=2,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="DevSyncGUI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,                  # windowed — no black terminal pops up
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
