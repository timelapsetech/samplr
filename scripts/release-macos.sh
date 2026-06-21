#!/usr/bin/env bash
# Build Samplr locally and publish dist/Samplr.app to GitHub Releases.
#
# Prerequisites:
#   brew install gh
#   gh auth login
#
# Usage:
#   ./scripts/release-macos.sh           # build, tag, and publish
#   SKIP_BUILD=1 ./scripts/release-macos.sh   # publish an existing build

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v gh >/dev/null; then
  echo "GitHub CLI is required. Install with: brew install gh" >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "Log in to GitHub first: gh auth login" >&2
  exit 1
fi

VERSION="$(
  python3 -c "from samplr import __version__; print(__version__)" 2>/dev/null \
    || grep -E '^__version__ = ' samplr/__init__.py | sed -E 's/.*"([^"]+)".*/\1/'
)"
TAG="v${VERSION}"
APP="dist/Samplr.app"
ZIP="dist/Samplr-${VERSION}-macos.zip"
NOTES_FILE="$(mktemp)"
trap 'rm -f "$NOTES_FILE"' EXIT

if [[ "${SKIP_BUILD:-}" != "1" ]]; then
  "$ROOT/scripts/build-macos.sh"
fi

if [[ ! -d "$APP" ]]; then
  echo "Missing $APP. Run ./scripts/build-macos.sh first." >&2
  exit 1
fi

echo "Packaging $APP..."
rm -f "$ZIP"
ditto -c -k --sequesterRsrc --keepParent "$APP" "$ZIP"

awk -v ver="$VERSION" '
  index($0, "## [" ver "]") == 1 { capture = 1; next }
  /^## \[/ { if (capture) exit }
  capture { print }
' CHANGELOG.md | sed '/./,$!d' > "$NOTES_FILE"

if [[ ! -s "$NOTES_FILE" ]]; then
  echo "No CHANGELOG.md section found for version ${VERSION}." >&2
  exit 1
fi

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [[ -n "$(git status --porcelain)" ]]; then
  echo "Working tree has uncommitted changes. Commit before releasing." >&2
  exit 1
fi

echo "Pushing branch ${BRANCH}..."
git push origin "HEAD:${BRANCH}"

if git rev-parse "$TAG" >/dev/null 2>&1; then
  echo "Tag ${TAG} already exists locally."
else
  git tag -a "$TAG" -m "Release ${TAG}"
fi

echo "Pushing tag ${TAG}..."
git push origin "$TAG"

if gh release view "$TAG" >/dev/null 2>&1; then
  echo "Updating release ${TAG}..."
  gh release upload "$TAG" "$ZIP" --clobber
  gh release edit "$TAG" --notes-file "$NOTES_FILE" --title "Samplr ${VERSION}"
else
  echo "Creating release ${TAG}..."
  gh release create "$TAG" "$ZIP" \
    --title "Samplr ${VERSION}" \
    --notes-file "$NOTES_FILE"
fi

echo ""
echo "Published: $(gh release view "$TAG" --json url -q .url)"
echo "Asset:     ${ZIP}"
