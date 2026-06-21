#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -d venv ]]; then
  python3 -m venv venv
fi

# shellcheck source=/dev/null
source venv/bin/activate

pip install -q --upgrade pip
pip install -q -e ".[gui,packaging]"

"$ROOT/scripts/generate-macos-icon.sh"
pyinstaller --noconfirm samplr.spec

echo ""
echo "Built: $ROOT/dist/Samplr.app"
echo "Install: cp -r dist/Samplr.app /Applications/"
echo "Test:    open dist/Samplr.app"
