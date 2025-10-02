# Building a macOS .app with PyInstaller

This document describes building a `.app` bundle for the Tkinter UI using PyInstaller.

Prerequisites
- macOS with Python installed (python.org or pyenv-built with Tk support recommended)
- Xcode command line tools: `xcode-select --install`
- Homebrew (optional, for dependencies)

Quick build (recommended)
1. From the repo root run:
```bash
./build_app.sh
```
2. The built app will be in `dist/CombinedProcessor.app`.

Notes
- The script creates a venv at `.venv-pyinstaller` and installs `pyinstaller`.
- PyInstaller must be run with the same Python that has Tk support.
- The script includes `Inter-Bold.ttf` as a data file so the app can find the font.
- If you need a custom icon, replace `Inter-Bold.ttf` in `build_app.sh` with an `.icns` file and add `--icon path/to/icon.icns` to the PyInstaller args.

Troubleshooting
- If the built app fails to launch due to missing libraries, ensure the venv's Python has Tk installed and matches the system architecture (Intel vs Apple Silicon).
- Use `--clean` to remove previous build artifacts:
```bash
./build_app.sh --clean
```
