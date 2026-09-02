#!/usr/bin/env bash
# Builds jp2a-studio_<version>_all.deb from the app/ sources.
# Usage: packaging/linux/build-deb.sh [version]
set -euo pipefail

VERSION="${1:-1.0.0}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PKG_SRC="$REPO_ROOT/packaging/linux/debian"
APP_SRC="$REPO_ROOT/app"
ASSETS="$REPO_ROOT/assets"
HOMEPAGE="${JP2A_STUDIO_HOMEPAGE:-https://github.com/maskeddukster21-rgb/jp2a-studio}"

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

mkdir -p \
  "$STAGE/DEBIAN" \
  "$STAGE/usr/bin" \
  "$STAGE/usr/share/jp2a-studio" \
  "$STAGE/usr/share/applications" \
  "$STAGE/usr/share/icons/hicolor/256x256/apps" \
  "$STAGE/usr/share/doc/jp2a-studio"

sed -e "s/__VERSION__/$VERSION/" -e "s#__HOMEPAGE__#$HOMEPAGE#" \
  "$PKG_SRC/control" > "$STAGE/DEBIAN/control"

cp "$PKG_SRC/copyright" "$STAGE/usr/share/doc/jp2a-studio/copyright"
cp "$PKG_SRC/jp2a-studio.desktop" "$STAGE/usr/share/applications/jp2a-studio.desktop"
cp "$ASSETS/icon-256.png" "$STAGE/usr/share/icons/hicolor/256x256/apps/jp2a-studio.png"

install -m 755 "$PKG_SRC/jp2a-studio.wrapper" "$STAGE/usr/bin/jp2a-studio"

cp "$APP_SRC/server.py" "$STAGE/usr/share/jp2a-studio/server.py"
cp -r "$APP_SRC/static" "$STAGE/usr/share/jp2a-studio/static"

find "$STAGE" -type d -exec chmod 755 {} \;
find "$STAGE" -type f -not -path "*/DEBIAN/*" -exec chmod 644 {} \;
chmod 755 "$STAGE/usr/bin/jp2a-studio"

OUT_DIR="$REPO_ROOT/dist"
mkdir -p "$OUT_DIR"
OUT_FILE="$OUT_DIR/jp2a-studio_${VERSION}_all.deb"

dpkg-deb --root-owner-group --build "$STAGE" "$OUT_FILE"
echo "Built: $OUT_FILE"
