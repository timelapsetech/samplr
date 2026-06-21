# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-06-21

### Added

- PyInstaller packaging to build a standalone macOS app (`Samplr.app`)
- `samplr.spec` for reproducible macOS builds
- `scripts/build-macos.sh` one-command build script
- `scripts/release-macos.sh` to publish a locally built macOS app to GitHub Releases
- `scripts/generate-macos-icon.sh` to build `assets/samplr_icon.icns` from the app logo
- App logo (`assets/samplr_logo.png`) bundled as the macOS app icon and window icon
- Desktop GUI progress bar with per-file status while sampling runs on a background thread
- Directory safety checks: source and destination must be different, non-nested folders
- `packaging` optional dependency extra with PyInstaller
- README instructions for building and installing the macOS app

### Changed

- App version bumped to 0.2.0
- `setup.py` now reads the package version from `samplr.__version__`
- `.gitignore` updated to keep `samplr.spec` in version control
- Desktop GUI accepts any positive integer for “every Nth image” (not limited to two digits)
- PyInstaller spec bundles only the PyQt6 modules Samplr uses, reducing app size and build warnings

### Fixed

- “Closest to time each day” now selects one image per day when EXIF timestamps are present (EXIF `YYYY:MM:DD HH:MM:SS` dates are parsed correctly instead of being misread as today’s date)

## [0.1.0] - 2025-05-10

### Added

- CLI for sampling images by every Nth frame, closest daily time, or Nth frame in a time range
- PyQt6 desktop GUI (`python -m samplr.desktop_ui`)
- EXIF-aware image timestamp handling with file modification time fallback
- Sequential output renaming with optional custom base name
- Development tooling: pytest, black, mypy, and ruff

[0.2.0]: https://github.com/timelapsetech/samplr/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/timelapsetech/samplr/releases/tag/v0.1.0
