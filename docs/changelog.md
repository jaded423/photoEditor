# Changelog

All notable changes to this project are documented here.

Format: Each entry includes date, summary, and details.

---

## 2026-04-14 - Fix Sideways Photos and Bulk Misclassification

**What changed:**
- Added `ImageOps.exif_transpose()` at every `Image.open` site in `combined_processor.py`. Input bytes are re-encoded as PNG at read time so the rotation is baked in before `rembg` / `cv2` see them (neither library honors EXIF on its own).
- Replaced the variance-based `is_bulk_photo()` pre-classifier with a post-rembg coverage check. Always runs rembg (except `Smalls` filename fast-path); decides based on the resulting mask:
  - `coverage > 85%` → no clear subject, treat as bulk pile, use original
  - `coverage < 5%` → rembg destroyed the image, fall back to original
  - otherwise → trust the mask
- Deleted dead `is_bulk_photo()` function and its `scipy.ndimage` variance code.
- Updated processing-pipeline section in `CLAUDE.md` to describe the new flow.

**Why:**
- User reported product photos coming out sideways. Root cause: iPhone/Samsung cameras save landscape pixels + EXIF orientation=6 (rotate 90° CW). Finder/Photos/browsers honor the flag; the processor was reading raw pixels and feeding them straight to rembg.
- After the rotation fix, 4 of 5 photos still came back with background intact. Root cause: `is_bulk_photo()` was misclassifying hand-held bud photos as bulk because the jar-of-buds background has the same texture density as the subject. Measured smooth ratios 0.4%–2.5% (all under the 3% threshold); only one photo with a smaller subject passed at 4.1%.
- rembg itself handles these photos perfectly (25%–45% coverage on the 5 test cases). Using its output as ground truth eliminates the flaky heuristic.

**Files modified:**
- `combined_processor.py` - Added `ImageOps` import; `exif_transpose` at read; pipeline rewrite in `process_photo`; removed `is_bulk_photo`
- `CLAUDE.md` - Updated processing-pipeline bullet list

**Technical notes:**
- Verified on `/tmp/photoEditor-test/in/` (5 JPGs from Apr 16 run): all 5 now come out upright with clean white backgrounds, coverage 25.5%–44.8%.
- `Smalls` filename prefix is still a user-declared fast-path skip.
- MOV pipeline unchanged — `.mov` files weren't rotated sideways (the rotation atom is either absent or handled correctly by cv2 in this codebase's usage). User's "missing MOVs" concern was a false alarm — all 5 from the affected batch were in `edited/`; the `_1`/`_2` suffix mismatch between `edited/` and `originals/` comes from the rename-on-move collision logic, not a processing failure.
- App rebuilt clean via `./build_app.sh`.

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
