# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the Samplr macOS desktop app.
# Build: pyinstaller samplr.spec

from PyInstaller.utils.hooks import collect_all

from samplr import __version__

pyqt6_datas, pyqt6_binaries, pyqt6_hiddenimports = collect_all("PyQt6")

a = Analysis(
    ["samplr/desktop_ui.py"],
    pathex=[],
    binaries=pyqt6_binaries,
    datas=pyqt6_datas,
    hiddenimports=pyqt6_hiddenimports + ["samplr.core"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Samplr",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Samplr",
)
app = BUNDLE(
    coll,
    name="Samplr.app",
    icon=None,
    bundle_identifier="com.timelapsetech.samplr",
    version=__version__,
)
