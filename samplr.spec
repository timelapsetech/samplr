# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the Samplr macOS desktop app.
# Build: pyinstaller samplr.spec
#
# PyQt6 hooks (QtWidgets/QtCore/QtGui) collect only the frameworks this app uses.
# Avoid collect_all("PyQt6") — it pulls optional plugins (3D, WebEngine, SQL, QML)
# that trigger harmless "Library not found" warnings and inflate the bundle.

from pathlib import Path

from samplr import __version__

SPEC_DIR = Path(SPECPATH)
LOGO = SPEC_DIR / "assets" / "samplr_logo.png"
ICON = SPEC_DIR / "assets" / "samplr_icon.icns"

if not ICON.is_file():
    raise SystemExit(
        f"Missing {ICON}. Run ./scripts/generate-macos-icon.sh or ./scripts/build-macos.sh."
    )

app_datas = [(str(LOGO), "assets")]

a = Analysis(
    ["samplr/desktop_ui.py"],
    pathex=[],
    binaries=[],
    datas=app_datas,
    hiddenimports=["samplr.core"],
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
    icon=str(ICON),
    bundle_identifier="com.timelapsetech.samplr",
    version=__version__,
)
