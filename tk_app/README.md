# Tkinter Scaffold for Combined Processor

This small Tkinter app launches a GUI to run `combined_processor.process_media_batch` on a chosen folder.

Prerequisites
- Python 3.10+ with `tkinter` support
- `Pillow`, `opencv-python`, and other dependencies used by `combined_processor.py` (see root `requirements.txt`)

Run

```bash
cd /path/to/pic_and_video_editor
python3 tk_app/app.py
```

Usage
- Click `Browse` to choose the `raw/` folder containing your media files.
- Click `Start Processing`. Progress updates, a counter and progress bar will update as files are processed.
- A `Done` message will be shown in the status area when complete.

Notes
- Stopping mid-run is not implemented; the Stop button will show an informational message.
- For photo processing you must have `rembg` and `scipy` installed; otherwise photos will be skipped.
