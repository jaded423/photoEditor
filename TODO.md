# photoEditor TODO

- [x] **Rebuild + redistribute PhotoEditor.app with the focal cut** (added 2026-09-04) — DONE 2026-09-04: rebuilt from `385d894`+tuning commit, `dist/PhotoEditor.zip` (133MB, sha256 e42b0ced…) written over Drive `Product Pics and Vids/PhotoEditor/PhotoEditor.zip` (same file ID `1lYKUEKkYuxqeKA9tPAtJjoo1VXgiX-K_`, Drive keeps it as a new version). Joshua has Cynthia download it next week; recipient runs `xattr -cr PhotoEditor.app`; first run downloads ~375MB of SAM weights next to BiRefNet.
- [ ] **Optional: red colour cast from the bucket** (added 2026-09-04). The red tray reflects onto the bud; a gentle bud-only white balance (gray-world on the matte, capped) would neutralise it. Cosmetic; decide after seeing the new cutouts on the site.

- [x] **Gitignore `.claude/`** — `.claude/settings.local.json` (local machine settings) shows as untracked on every push-all sweep. Add `.claude/` to `.gitignore`. Elevated-Trading-LLC repo (branch `main`) → PR workflow, not direct push. (surfaced by push-all 2026-06-20) — DONE (`.claude/` present in .gitignore; no longer shows as untracked)
