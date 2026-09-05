# PhotoEditor

> **Stack:** Tier-2 leaf (standalone). Parent/router: [global](~/.claude/CLAUDE.md). Leaf → no `wiki/` tree.

Batch photo and video processor for product photography. Removes backgrounds, resizes to 1000x1000, and adds filename banners.

## Repository

- **Canonical (upstream):** `jaded423/photoEditor` — owned by Joshua, source of truth. Local `origin` points here.
- **Fork:** `Elevated-Trading-LLC/photoEditor` — a GitHub fork of upstream. Local remote `elevated`. Org devs work here and PR up to upstream `main`; pull upstream changes back via GitHub "Sync fork".
- **Archive:** `Elevated-Trading-LLC/photoEditor-archive` — read-only pre-fork history (the n8n webhook edition). The full webhook app is also recoverable at the `webhook-edition` tag on upstream.
- **Branch convention:** Feature branches with PRs to upstream `main`.

## Architecture

```
photoEditor/
├── combined_processor.py    # Core processing engine (batch, resize, banner, video)
├── focal_cut.py             # Scene-aware held-bud isolation (cues → SAM → BiRefNet → defringe)
├── tk_app/
│   └── app.py               # Tkinter GUI
├── build_app.sh             # PyInstaller build script
├── PhotoEditor.icns         # App icon
├── Inter-Bold.ttf           # Bundled banner font
└── requirements.txt         # Python dependencies (37 packages)
```

## Processing Pipeline

Per photo (`combined_processor.process_photo`), EXIF-upright first, then:

1. **Focal cut** (`focal_cut.py`, 2026-09-04) — scene-aware isolation of the ONE held bud.
   Cheap cues at 640px (colour classes: red bucket / dark or blue-sheen glove / bud-coloured;
   sharpness; texture) pick the raised, in-focus bud and reject the pile (touches the bottom
   edge), bucket-rim glare, the ULINE box (touches the top). A bud sitting ON the pile is carved
   out by sharpness × height-in-frame. Then **SAM** (rembg's `sam_vit_b` ONNX pair) is prompted
   with +bud / −glove / −pile / −red points on a tight crop → object mask that excludes the glove;
   **BiRefNet** mattes the same crop (1024² on a crop ≈ 3–4× the edge resolution of a full-frame
   pass) and is gated by the SAM region; glove fingertips / bucket-red slivers on the rim are
   peeled; 2px erode + feather + colour decontamination kills the red fringe.
   Returns `None` (→ step 2) when no held bud is found (piles, smalls, bulk), when SAM's object is
   a sliver of the crop (one nug out of a pile), or on any exception — the old path is the safety net.
   Gotcha: rembg's SAM decoder is baked to a 684×1024 frame — see brain `rembg-sam-onnx-684x1024-frame`.
2. **Full-frame fallback** (unchanged old path): `rembg` `birefnet-general`; `Smalls` prefix skips removal.
   Coverage >85% → bulk/pile, use original; <5% → use original. Component cleanup (keep near the
   main subject, drop distant fragments, alpha>30 boosted to opaque), post-cleanup <5% → original.
3. **Resize**: isolated subject → bbox-fit into 900² on a 1000² canvas (`smart_resize_1000x1000`);
   full-frame originals → centre-crop fill (`resize_fill_1000x1000`).
4. **Outputs** (contract consumed by elevatedWeb / inventory — do not change): `pendingProducts/`
   (clean, no banner — WP product image), `edited/` (banner — InStock share), `original/` (source moved).
   Videos: banner only → `edited/`.

Models auto-download to `~/.u2net/` on first run: `birefnet-general.onnx` (~930MB) +
`sam_vit_b_01ec64.{encoder,decoder}.onnx` (~375MB). ~15–20s/photo on an M-series CPU.
Kill switch: `FOCAL_CUT_ENABLED = False` in `combined_processor.py`.

## Photo Types Handled

| Type | Example | Behavior |
|------|---------|----------|
| Held bud (red bucket + glove + pile behind, or steel bowl) | The photographer's standard shot | Focal cut: bud only — glove, pile, bucket gone |
| Single subject, no glove | Jar on white bg | Focal cut if a bud is found, else full-frame rembg |
| Bulk/pile | Smalls, Exotic Mids (product fills frame) | Focal cut declines → skip bg removal, fill the tile |
| Middle ground | Jar with scattered product | Full-frame path, keeps scattered pieces |

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

- `rembg` + `onnxruntime` — BiRefNet matte + SAM ViT-B object mask (ONNX, download to `~/.u2net/`)
- `opencv-python` — video processing
- `scipy` — connected component analysis, bulk photo detection
- `pillow` + `pillow-heif` — image handling including iPhone HEIC

## Changelog

See [docs/changelog.md](docs/changelog.md)
