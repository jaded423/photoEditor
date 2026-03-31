# Changelog

All notable changes to this project are documented here.

Format: Each entry includes date, summary, and details.

---

## 2026-03-19 - Photo Quality Overhaul and App Rename

**What changed:**
- Upgraded background removal model from `isnet-general-use` to `birefnet-general` (rembg)
- Added automatic bulk/pile photo detection (`is_bulk_photo()`) using local variance analysis
- Reworked connected component cleanup: keeps all components near the main subject, only removes small isolated distant fragments
- Boosted kept subject pixels to full opacity to eliminate washed-out partial transparency artifacts
- Lowered component detection alpha threshold from 128 to 30 to catch partially transparent subject areas
- Added post-cleanup safety net: falls back to original if coverage drops below 5%
- Simplified `smart_resize_1000x1000`: crops to subject bounding box, scales to fill 900x900 with 50px border on all sides
- Removed duplicate `process_media_batch()` call in CLI `main()`
- Renamed app from CombinedProcessor to PhotoEditor (build script, window title)
- Added custom steampunk camera icon (PhotoEditor.icns)
- Renamed "Create Products" button to "Create Products (Elevated)"

**Why:**
- `isnet-general-use` model produced milky halos and poor edges on glass jars and scattered product
- Bulk/pile photos (Exotic Mids) were being destroyed by background removal — rembg treated product as background
- "Middle ground" photos (jar with scattered product) had pieces stripped by cleanup keeping only largest component
- Products appeared too small on product pages with old resize logic
- App name didn't reflect its purpose

**Files modified:**
- `combined_processor.py` - New `is_bulk_photo()` function, BiRefNet model swap, reworked component cleanup, simplified smart resize
- `tk_app/app.py` - Window title and button text updates
- `build_app.sh` - Renamed to PhotoEditor, added icon support
- `PhotoEditor.icns` - New app icon

**Technical notes:**
- Bulk detection uses `scipy.ndimage.uniform_filter` to compute local variance. Bulk photos have ~0% smooth area, single-subject photos have 5%+. Threshold of 3% cleanly separates them (tested on 61 product photos).
- BiRefNet model (~500MB) downloads on first run to `~/.u2net/`
- ViTMatte two-stage pipeline was tested but rejected — BiRefNet alone produced crisper results
- Post-cleanup fallback threshold set to 5% (not 30% — legitimate single-subject photos can be 15-30% coverage)
- Settings persist at `~/Library/Application Support/CombinedProcessor/settings.json` (path unchanged despite rename)

---

## 2026-03-19 - Repository Migration

**What changed:**
- Remote changed from `Charisma-18/picandvideoeditor` to `Elevated-Trading-LLC/photoEditor`
- PR workflow established on Elevated-Trading-LLC org
- Excluded photoEditor from jaded423 autobackup script (`~/scripts/bin/gitBackup.sh`)

**Why:**
- App is now maintained under Elevated Trading LLC organization
- Autobackup was configured for personal repos, not org repos

---
