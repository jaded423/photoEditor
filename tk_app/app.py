import threading
import queue
import time
import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import threading
import queue
import time
import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk

# Ensure we can import the processor from parent folder
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from combined_processor import process_media_batch


class ProcessorThread(threading.Thread):
    def __init__(self, folder, progress_queue, stop_event):
        super().__init__()
        self.folder = folder
        self.progress_queue = progress_queue
        self.stop_event = stop_event

    def run(self):
        def cb(processed_count, total_files, filename, message):
            # Put progress updates into the queue for the main thread
            self.progress_queue.put((processed_count, total_files, filename, message))

        try:
            process_media_batch(self.folder, progress_callback=cb, stop_event=self.stop_event)
            # Signal completion
            if not (self.stop_event is not None and self.stop_event.is_set()):
                self.progress_queue.put(('done', None, None, 'Done'))
            else:
                self.progress_queue.put(('done', None, None, 'Stopped'))
        except Exception as e:
            self.progress_queue.put(('error', None, None, str(e)))


class App:
    def __init__(self, root):
        self.root = root
        root.title('Combined Processor - Tk')
        self.progress_queue = queue.Queue()

        frm = ttk.Frame(root, padding=12)
        frm.grid()

        ttk.Label(frm, text='Choose raw folder:').grid(column=0, row=0, sticky='w')
        self.folder_var = tk.StringVar()
        folder_entry = ttk.Entry(frm, textvariable=self.folder_var, width=60)
        folder_entry.grid(column=0, row=1, columnspan=2, sticky='we', pady=6)

        ttk.Button(frm, text='Browse', command=self.browse_folder).grid(column=2, row=1, sticky='e')

        self.start_btn = ttk.Button(frm, text='Start Processing', command=self.start_processing)
        self.start_btn.grid(column=0, row=2, pady=8)

        self.stop_btn = ttk.Button(frm, text='Stop', command=self.stop_processing, state='disabled')
        self.stop_btn.grid(column=1, row=2, pady=8)

        self.progress = ttk.Progressbar(frm, orient='horizontal', length=400, mode='determinate')
        self.progress.grid(column=0, row=3, columnspan=3, pady=6)

        self.counter_label = ttk.Label(frm, text='Processed: 0 / 0')
        self.counter_label.grid(column=0, row=4, columnspan=3, sticky='w')

        self.status_text = tk.Text(frm, height=8, width=80, state='disabled')
        self.status_text.grid(column=0, row=5, columnspan=3, pady=8)

        self.worker = None
        self.stop_event = None
        self.root.after(200, self.poll_queue)

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_var.set(folder)

    def start_processing(self):
        folder = self.folder_var.get().strip()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror('Error', 'Please select a valid folder')
            return

        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.progress['value'] = 0
        self.counter_label.config(text='Processed: 0 / 0')
        self.clear_status()

        # Create a stop event for cooperative cancellation
        self.stop_event = threading.Event()
        self.worker = ProcessorThread(folder, self.progress_queue, self.stop_event)
        self.worker.start()

    def stop_processing(self):
        if self.worker and self.worker.is_alive():
            if messagebox.askyesno('Confirm', 'Stop processing? This will attempt to cancel after the current file.'):
                # Signal the processing thread to stop
                if self.stop_event:
                    self.stop_event.set()
                self.append_status('Stop requested — will stop after current file.')
                self.stop_btn.config(state='disabled')
        else:
            messagebox.showinfo('Info', 'No active processing to stop.')

    def poll_queue(self):
        try:
            while True:
                item = self.progress_queue.get_nowait()
                self.handle_progress(item)
        except queue.Empty:
            pass
        finally:
            self.root.after(200, self.poll_queue)

    def handle_progress(self, item):
        processed_count, total_files, filename, message = item
        if processed_count == 'done':
            self.append_status('All done')
            self.start_btn.config(state='normal')
            self.stop_btn.config(state='disabled')
            self.progress['value'] = 100
            return

        if processed_count == 'error':
            self.append_status(f"Error: {message}")
            self.start_btn.config(state='normal')
            self.stop_btn.config(state='disabled')
            return

        # Update counter and progress bar
        total = total_files or 0
        self.counter_label.config(text=f'Processed: {processed_count} / {total}')
        if total > 0:
            percent = int((processed_count / total) * 100)
            self.progress['value'] = percent

        if filename:
            self.append_status(message)

    def append_status(self, text):
        self.status_text.config(state='normal')
        self.status_text.insert('end', text + '\n')
        self.status_text.see('end')
        self.status_text.config(state='disabled')

    def clear_status(self):
        self.status_text.config(state='normal')
        self.status_text.delete('1.0', 'end')
        self.status_text.config(state='disabled')


def main():
    root = tk.Tk()
    app = App(root)
    root.mainloop()


if __name__ == '__main__':
    main()
