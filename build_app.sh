#!/usr/bin/env bash
set -euo pipefail

# Build a macOS .app bundle for the Tkinter UI using PyInstaller.
# Usage: ./build_app.sh [--clean]

HERE=$(cd "$(dirname "$0")" && pwd)
VENV_DIR="$HERE/.venv-pyinstaller"
APP_NAME="CombinedProcessor"
ENTRY_POINT="$HERE/tk_app/app.py"
ICON_PATH="$HERE/Inter-Bold.ttf"  # not a real icon, but ensure font is included

if [[ "${1:-}" == "--clean" ]]; then
  rm -rf dist build "$VENV_DIR" ${APP_NAME}.spec
  echo "Cleaned build artifacts"
  exit 0
fi

echo "Creating venv at $VENV_DIR"
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip setuptools wheel
pip install pyinstaller

# Ensure requirements are available (optional)
if [[ -f "$HERE/requirements.txt" ]]; then
  pip install -r "$HERE/requirements.txt" || true
fi

echo "Running PyInstaller..."

# Include the font and the entire tk_app folder as data
DATA_ARGS=(
  --add-data "$HERE/Inter-Bold.ttf:."
  --add-data "$HERE/tk_app:tk_app"
  --add-data "$HERE/combined_processor.py:."  # include main processor module
)

# Add repo root to PyInstaller search path so imports from project root are discovered
PY_PATH_ARGS=(--paths "$HERE")

pyinstaller --noconfirm --clean --windowed --name "$APP_NAME" \
  "${PY_PATH_ARGS[@]}" "${DATA_ARGS[@]}" "$ENTRY_POINT"

echo "Build complete. App bundle is in dist/${APP_NAME}.app"
echo "Activate venv with: source ${VENV_DIR}/bin/activate" 
