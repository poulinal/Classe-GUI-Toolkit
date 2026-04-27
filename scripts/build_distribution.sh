#!/usr/bin/env bash
set -euo pipefail

# Build a standalone executable for CGTProject.
# Usage:
#   ./scripts/build_distribution.sh
# Output:
#   dist/CGTProjectApp/CGTProject (single-file executable)

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

python -m pip install --upgrade pip
python -m pip install -e ".[build]"

rm -rf build dist

pyinstaller \
  --noconfirm \
  --clean \
  --onefile \
  --windowed \
  --name CGTProject \
  --collect-submodules matplotlib \
  --collect-submodules scipy \
  --collect-submodules nexusformat \
  --hidden-import PyQt5.sip \
  --contents-directory . \
  CGTProject/main.py

mkdir -p dist/CGTProjectApp
cp -f dist/CGTProject dist/CGTProjectApp/CGTProject

cat <<'MSG'
Build complete.

Run from terminal:
  ./dist/CGTProjectApp/CGTProject
MSG
