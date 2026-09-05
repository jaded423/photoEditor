# photoEditor TODO

- [ ] **Rebuild + redistribute PhotoEditor.app with the focal cut** (added 2026-09-04). `./build_app.sh`, zip `dist/PhotoEditor.app`, upload to the Elevated Drive copy ("Manage versions" → v3), send the photographer the one-liner `xattr -cr PhotoEditor.app`. First run on her Mac downloads ~375MB of SAM weights next to BiRefNet.
      verify: ls -d dist/PhotoEditor.app && grep -l focal_cut dist/PhotoEditor.app/Contents/Resources/focal_cut.py
      resume: code + docs landed 2026-09-04; only the build/ship step remains. Memory note: BiRefNet already peaked ~9.5GB/photo on the old path, new path 4–8GB — no regression, but don't run two batches at once.
- [ ] **Optional: red colour cast from the bucket** (added 2026-09-04). The red tray reflects onto the bud; a gentle bud-only white balance (gray-world on the matte, capped) would neutralise it. Cosmetic; decide after seeing the new cutouts on the site.

- [x] **Gitignore `.claude/`** — `.claude/settings.local.json` (local machine settings) shows as untracked on every push-all sweep. Add `.claude/` to `.gitignore`. Elevated-Trading-LLC repo (branch `main`) → PR workflow, not direct push. (surfaced by push-all 2026-06-20) — DONE (`.claude/` present in .gitignore; no longer shows as untracked)
