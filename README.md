<div align="center">

```
██████╗ ██╗  ██╗ ██████╗ ████████╗ ██████╗ ███████╗██████╗ ██╗████████╗ ██████╗ ██████╗
██╔══██╗██║  ██║██╔═══██╗╚══██╔══╝██╔═══██╗██╔════╝██╔══██╗██║╚══██╔══╝██╔═══██╗██╔══██╗
██████╔╝███████║██║   ██║   ██║   ██║   ██║█████╗  ██║  ██║██║   ██║   ██║   ██║██████╔╝
██╔═══╝ ██╔══██║██║   ██║   ██║   ██║   ██║██╔══╝  ██║  ██║██║   ██║   ██║   ██║██╔══██╗
██║     ██║  ██║╚██████╔╝   ██║   ╚██████╔╝███████╗██████╔╝██║   ██║   ╚██████╔╝██║  ██║
╚═╝     ╚═╝  ╚═╝ ╚═════╝    ╚═╝    ╚═════╝ ╚══════╝╚═════╝ ╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝
```

# 🐍 PhotoEditor

**Batch product-photo processor · macOS Tkinter app · scene-aware subject cut (SAM + BiRefNet) · auto-resize · SKU banner**

[jadedviber.com](https://jadedviber.com) · [github.com/jaded423](https://github.com/jaded423) · [Installation guide →](INSTALL.md)

*Hundreds of product photos. One folder. One button. Square-cropped, background-removed, banner-stamped, ready to ship.*

![macOS](https://img.shields.io/badge/macOS-12+-000000?style=for-the-badge&logo=apple&logoColor=white)
![Python](https://img.shields.io/badge/python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Tkinter](https://img.shields.io/badge/UI-Tkinter-bd93f9?style=for-the-badge)
![License](https://img.shields.io/badge/license-MIT-cba6f7?style=for-the-badge)

</div>

---

```bash
$ whoami
joshua brown — vibe coder · homelab tinkerer · AI-driven dev

$ cat /problem.md
product photography for a multi-SKU catalog. dozens of new SKUs per week.
each photo needs: background removed, square-cropped, scaled to 1000×1000,
optionally banner-stamped with the SKU filename. doing it by hand in
photoshop = death.

PhotoEditor: point at a folder, hit "Process". 200 photos → 5 minutes.

$ ls outputs/
pendingProducts/   # no banner — clean for catalog upload
edited/            # with banner — filename overlay for review
original/          # source moved here (recoverable)
```

---

## ✨ What it does

**Input:** a folder of product photos / videos (mixed formats — JPG, PNG, MP4).

**Pipeline:**

1. **Focal cut** (`focal_cut.py`) — finds the ONE hand-held product in the frame from cheap cues (colour classes, sharpness, texture, position), prompts **SAM** at it with negative points on the hand/glove, the pile behind, and the backdrop, then mattes a tight crop with **BiRefNet** for fine edges and defringes the backdrop colour. Hands, gloves, the pile behind and the tray/bucket are excluded. Declines (→ step 2) on pile shots or anything it isn't sure about.
2. **Full-frame fallback** — `rembg` `birefnet-general` on the whole frame; filename prefix `smalls` skips it (bulk product fills the frame). If rembg kept >85% coverage (no clear subject) OR <5% (over-removed), falls back to the original. Saves the "pile of nugs" case
3. **Component cleanup** — keeps everything connected to the main subject. Strips only small distant fragments (alpha > 30 threshold)
4. **Smart resize** — crops to subject bounding box, scales to 900×900, centers on a 1000×1000 transparent canvas with a 50px border
5. **Outputs**:
   - `pendingProducts/` — clean square PNG, no banner (catalog-ready)
   - `edited/` — same image + SKU filename banner overlaid (review-ready)
   - `original/` — source files moved here (nothing destroyed)

**UI:** native macOS Tkinter. Pick folder, hit Process. Progress bar + log window.

---

## 🧠 Why it exists

Product photography pipeline for a multi-brand catalog. Built originally for an internal team that ships hundreds of new product photos per week. Open-sourced because the pattern is generic — anyone running a catalog with manual photo-prep grind can use it as-is or adapt.

The "bulk detection" heuristic in step 2 came out of real-world failure modes: `rembg` would over-remove on photos of piled product (no clear subject to keep) and produce empty PNGs. The coverage-percentage fallback turned a manual triage step into one heuristic.

---

## 📦 Photo type matrix

| Type | Example filename | Behavior |
|---|---|---|
| Hand-held product over a tray / pile | `aaa-strain.jpg` | Focal cut: product only, hand + pile + tray removed |
| Single subject | `jar-001.jpg` | Focal cut, else full-frame bg removal + resize + banner |
| Bulk / pile | `smalls-batch-3.jpg` | Focal cut declines → skip bg removal, resize only |
| Middle-ground (scattered) | `jar-with-scatter.jpg` | Full pipeline, keeps scattered pieces (component cleanup tuned to not strip them) |
| Over-removed by rembg | (auto-detected) | Falls back to original |

---

## 🏗️ Architecture

```
photoEditor/
├── combined_processor.py    # Core pipeline: focal cut → (fallback rembg → cleanup) → resize → banner
├── focal_cut.py             # Scene-aware subject isolation: cues → SAM prompt → BiRefNet crop matte → defringe
├── tk_app/
│   └── app.py               # Tkinter GUI
├── build_app.sh             # PyInstaller build script (→ dist/PhotoEditor.app)
├── PhotoEditor.icns         # App icon
├── PhotoEditor.spec         # PyInstaller spec (bundled font, model, etc.)
├── Inter-Bold.ttf           # Bundled banner font
└── requirements.txt         # 37 deps (rembg, Pillow, tkinter, requests, ...)
```

**Logs:** `~/Library/Logs/CombinedProcessor/` — rolling debug logs.

---

## 🚀 Install

**End users (Mac, no Python required):** see [INSTALL.md](INSTALL.md) for the .app download + macOS Gatekeeper walkthrough.

**Developers (build from source):**

```bash
git clone https://github.com/jaded423/photoEditor.git
cd photoEditor

# Requires Python 3.13 at /Library/Frameworks/Python.framework/Versions/3.13/
./build_app.sh           # → dist/PhotoEditor.app
./build_app.sh --clean   # clean build artifacts first

# Or run directly without packaging
./run_python.sh
```

---

## 🤖 AI-assisted, end-to-end

Built through iterative dialogue with Claude (Anthropic). The hardest part wasn't `rembg` — it was the heuristic for "did the background-removal step actually work, or did it make things worse?" That came out of pairing on real failure cases.

Same approach behind everything at [jadedviber.com](https://jadedviber.com).

---

## 🐛 Troubleshooting

| Issue | Fix |
|---|---|
| App won't open after install | See [INSTALL.md](INSTALL.md) — Gatekeeper walkthrough |
| "PhotoEditor.app is damaged" | Re-download the zip; archive corrupted during transfer |
| All photos coming out empty | Check `~/Library/Logs/CombinedProcessor/` — likely a model download issue on first launch |
| First photo hangs for minutes | Normal on first-ever launch — rembg downloads the `birefnet-general` model (~928MB) and the SAM ViT-B pair (~375MB) to `~/.u2net/`. Later photos are fast |
| Crashes on launch | Ensure macOS 12+ (Monterey or later) |

---

## 🔗 Resources

- **Install for end users:** [INSTALL.md](INSTALL.md)
- **Internal architecture notes:** [CLAUDE.md](CLAUDE.md)
- Pairs with the rest of the catalog automation stack on [jadedviber.com](https://jadedviber.com)

---

## 📝 License

MIT — see [LICENSE](LICENSE) (if absent, treat as MIT pending file)

---

<div align="center">

```
$ open dist/PhotoEditor.app
[ready] watching folder...
```

*<sub>maintained by [@jaded423](https://github.com/jaded423) · built end-to-end through dialogue with AI · cyberpunk-styled · monospace everything</sub>*

**[jadedviber.com](https://jadedviber.com)** · *All vibe. No grind.* 🐍

</div>
