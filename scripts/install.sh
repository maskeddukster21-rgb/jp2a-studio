#!/usr/bin/env bash
# One-line installer for jp2a Studio on Linux / WSL:
#   curl -fsSL https://raw.githubusercontent.com/<owner>/<repo>/main/scripts/install.sh | bash
#
# Installs the app to ~/.local/share/jp2a-studio and a launcher to
# ~/.local/bin/jp2a-studio. Prefers your distro's package manager for jp2a
# itself rather than bundling a binary.
set -euo pipefail

REPO_SLUG="${JP2A_STUDIO_REPO:-maskeddukster21-rgb/jp2a-studio}"
REPO_URL="https://github.com/${REPO_SLUG}"
INSTALL_DIR="${JP2A_STUDIO_INSTALL_DIR:-$HOME/.local/share/jp2a-studio}"
BIN_DIR="${JP2A_STUDIO_BIN_DIR:-$HOME/.local/bin}"

info()  { printf '\033[1;36m==>\033[0m %s\n' "$1"; }
warn()  { printf '\033[1;33m!!\033[0m %s\n' "$1" >&2; }
die()   { printf '\033[1;31mERROR:\033[0m %s\n' "$1" >&2; exit 1; }

command -v python3 >/dev/null 2>&1 || die "python3 is required but was not found."

# ---- jp2a itself -----------------------------------------------------------
if ! command -v jp2a >/dev/null 2>&1; then
  info "jp2a not found, trying to install it with your package manager..."
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update && sudo apt-get install -y jp2a
  elif command -v pacman >/dev/null 2>&1; then
    sudo pacman -Sy --noconfirm jp2a
  elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y jp2a
  elif command -v zypper >/dev/null 2>&1; then
    sudo zypper install -y jp2a
  elif command -v brew >/dev/null 2>&1; then
    brew install jp2a
  else
    warn "Don't know your package manager. Install jp2a yourself, then re-run this script."
  fi
fi
command -v jp2a >/dev/null 2>&1 || warn "jp2a still isn't on PATH — the app will run but conversions will fail until it is."

# ---- Pillow ------------------------------------------------------------
if ! python3 -c "import PIL" >/dev/null 2>&1; then
  info "Installing the Pillow Python package for image format support..."
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get install -y python3-pil || python3 -m pip install --user Pillow
  elif command -v pacman >/dev/null 2>&1; then
    sudo pacman -Sy --noconfirm python-pillow
  else
    python3 -m pip install --user Pillow
  fi
fi

# ---- app files --------------------------------------------------------
info "Downloading jp2a Studio from ${REPO_URL}..."
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
curl -fsSL "${REPO_URL}/archive/refs/heads/main.tar.gz" -o "$TMP/src.tar.gz" \
  || die "Could not download ${REPO_URL} — check JP2A_STUDIO_REPO / your network."
tar -xzf "$TMP/src.tar.gz" -C "$TMP"
SRC_APP_DIR="$(find "$TMP" -maxdepth 2 -type d -name app | head -n1)"
[ -n "$SRC_APP_DIR" ] || die "Downloaded archive didn't contain an app/ directory."

rm -rf "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cp -r "$SRC_APP_DIR"/. "$INSTALL_DIR"/

mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/jp2a-studio" <<EOF
#!/usr/bin/env bash
exec python3 "$INSTALL_DIR/server.py" "\$@"
EOF
chmod +x "$BIN_DIR/jp2a-studio"

info "Installed to $INSTALL_DIR"
case ":$PATH:" in
  *":$BIN_DIR:"*) info "Run it with: jp2a-studio" ;;
  *)
    warn "$BIN_DIR is not on your PATH."
    echo "  Add this to your shell profile:  export PATH=\"$BIN_DIR:\$PATH\""
    echo "  Then run: jp2a-studio"
    ;;
esac
