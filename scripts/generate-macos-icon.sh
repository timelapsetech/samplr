#!/usr/bin/env bash
# Build assets/samplr_icon.icns from assets/samplr_logo.png (macOS only).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/assets/samplr_logo.png"
ICONSET="$ROOT/assets/samplr_icon.iconset"
ICNS="$ROOT/assets/samplr_icon.icns"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "macOS icon generation requires Darwin (iconutil)." >&2
  exit 1
fi

if [[ ! -f "$SRC" ]]; then
  echo "Missing logo: $SRC" >&2
  exit 1
fi

if [[ ! -d "$ROOT/venv" ]]; then
  python3 -m venv "$ROOT/venv"
fi
# shellcheck source=/dev/null
source "$ROOT/venv/bin/activate"
pip install -q Pillow

rm -rf "$ICONSET"
mkdir -p "$ICONSET"

python3 - "$SRC" "$ICONSET" <<'PY'
import sys
from pathlib import Path

from PIL import Image

src = Path(sys.argv[1])
iconset = Path(sys.argv[2])
img = Image.open(src).convert("RGBA")
sizes = [
    ("icon_16x16.png", 16),
    ("icon_16x16@2x.png", 32),
    ("icon_32x32.png", 32),
    ("icon_32x32@2x.png", 64),
    ("icon_128x128.png", 128),
    ("icon_128x128@2x.png", 256),
    ("icon_256x256.png", 256),
    ("icon_256x256@2x.png", 512),
    ("icon_512x512.png", 512),
    ("icon_512x512@2x.png", 1024),
]
for name, size in sizes:
    resized = img.resize((size, size), Image.Resampling.LANCZOS)
    resized.save(iconset / name)
PY

iconutil -c icns "$ICONSET" -o "$ICNS"
rm -rf "$ICONSET"

echo "Generated: $ICNS"
