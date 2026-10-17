#!/usr/bin/env bash
set -euo pipefail

# Install a desktop launcher for the built CGTProject binary.
# Usage:
#   ./scripts/install_desktop_launcher.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_BIN="$ROOT_DIR/dist/CGTProjectApp/CGTProject"
DESKTOP_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$DESKTOP_DIR/cgtproject.desktop"

if [[ ! -x "$APP_BIN" ]]; then
  echo "Built binary not found or not executable: $APP_BIN"
  echo "Run ./scripts/build_distribution.sh first."
  exit 1
fi

mkdir -p "$DESKTOP_DIR"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=CGTProject
Comment=GUI Application Toolkit for CLASSE
Exec=$APP_BIN
Terminal=false
Categories=Science;
StartupNotify=true
EOF

chmod +x "$DESKTOP_FILE"

echo "Desktop launcher installed: $DESKTOP_FILE"
echo "You can now launch CGTProject from your application menu."
