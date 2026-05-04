# -*- mode: python ; coding: utf-8 -*-
# cli.spec — DevSync CLI  (onefile)
#
# Output: dist\cli\cli.exe
# Copy the whole dist\cli\ folder next to DevSyncGUI.exe after building.

a = Analysis(
    ["devsync.py"],
    pathex=["."],           # cli/ is the working directory when this spec runs
    binaries=[],
    datas=[],
    hiddenimports=[
        # watchdog uses late-binding platform observers
        "watchdog.observers",
        "watchdog.observers.winapi",    # Windows
        "watchdog.observers.inotify",   # Linux (ignored on Windows, harmless)
        "watchdog.observers.fsevents",  # macOS (ignored on Windows, harmless)
        "watchdog.events",
        "watchdog.tricks",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # GUI packages have no place in the CLI binary
        "customtkinter",
        "tkinter",
    ],
    noarchive=False,
    optimize=2,             # strips docstrings; bytecode is not human-readable
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="cli",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,           # CLI must keep its console so the GUI can read stdout
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
