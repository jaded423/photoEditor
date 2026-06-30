# PhotoEditor

Batch photo and video processor for product photography. Removes backgrounds, resizes to 1000x1000, and adds filename banners.

## Repository

- **Canonical (upstream):** `jaded423/photoEditor` — owned by Joshua, source of truth. Local `origin` points here.
- **Fork:** `Elevated-Trading-LLC/photoEditor` — a GitHub fork of upstream. Local remote `elevated`. Org devs work here and PR up to upstream `main`; pull upstream changes back via GitHub "Sync fork".
- **Archive:** `Elevated-Trading-LLC/photoEditor-archive` — read-only pre-fork history (the n8n webhook edition). The full webhook app is also recoverable at the `webhook-edition` tag on upstream.
- **Branch convention:** Feature branches with PRs to upstream `main`.

## Architecture

```
photoEditor/
├── combined_processor.py    # Core processing engine
├── tk_app/
│   └── app.py               # Tkinter GUI
├── build_app.sh             # PyInstaller build script
├── PhotoEditor.icns         # App icon
├── Inter-Bold.ttf           # Bundled banner font
└── requirements.txt         # Python dependencies (37 packages)
```

## Processing Pipeline

1. **Background removal**: `rembg` with `birefnet-general` model. Smalls filename prefix skips removal.
2. **Post-rembg bulk detection**: If rembg kept >85% coverage, treat as a bulk/pile and use the original (no clear subject found). <5% coverage falls back to original too.
3. **Component cleanup**: Keeps all components near main subject, removes only small distant fragments. Alpha > 30 threshold, pixels boosted to full opacity.
4. **Post-cleanup safety net**: Falls back to original if coverage < 5%
5. **Smart resize**: Crops to subject bounding box, scales to 900x900 (50px border), centered on 1000x1000 canvas
6. **Outputs**: `pendingProducts/` (no banner), `edited/` (with banner), `original/` (source moved here)

## Photo Types Handled

| Type | Example | Behavior |
|------|---------|----------|
| Single subject | Hand-held flower, jar on white bg | Full pipeline: bg removal + resize |
| Bulk/pile | Smalls, Exotic Mids (product fills frame) | Skip bg removal, resize only |
| Middle ground | Jar with scattered product | Full pipeline, keeps scattered pieces |

## Building

```bash
./build_app.sh           # Build dist/PhotoEditor.app
./build_app.sh --clean   # Clean all build artifacts first
```

Requires Python 3.13 at `/Library/Frameworks/Python.framework/Versions/3.13/`. Build creates a venv at `.venv-pyinstaller`.

## Distribution

- **Not code-signed** — recipients must run `xattr -cr PhotoEditor.app` after downloading
- $99/year Apple Developer ID needed for frictionless distribution (not yet set up)

## Key Dependencies

- `rembg` + `onnxruntime` — background removal (BiRefNet model, ~500MB, downloads to `~/.u2net/`)
- `opencv-python` — video processing
- `scipy` — connected component analysis, bulk photo detection
- `pillow` + `pillow-heif` — image handling including iPhone HEIC

## Changelog

See [docs/changelog.md](docs/changelog.md)
