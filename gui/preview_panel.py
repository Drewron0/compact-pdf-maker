import tkinter as tk
from tkinter import ttk
from PIL import ImageTk
from core.pdf_processor import generate_layout_preview


class LayoutPreviewPanel(ttk.Frame):
    """
    Displays an interactive layout diagram preview that dynamically
    scales to fit the available window dimensions.
    """
    def __init__(self, parent, get_layout_config_fn):
        super().__init__(parent)
        self.get_layout_config_fn = get_layout_config_fn
        self._current_pil_img = None
        self._tk_img = None
        self._resize_timer = None

        self._build_ui()

    def _build_ui(self):
        self.container = tk.Frame(self, bg="#e8eaed", relief="sunken", bd=1)
        self.container.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.preview_lbl = tk.Label(self.container, bg="#e8eaed")
        self.preview_lbl.pack(fill=tk.BOTH, expand=True)

        self.container.bind("<Configure>", self._on_resize)

    def _on_resize(self, event):
        # Debounce resize event by 50ms to prevent lag during window drag
        if self._resize_timer:
            self.after_cancel(self._resize_timer)
        self._resize_timer = self.after(60, self.refresh_preview)

    def refresh_preview(self):
        cols, rows, landscape = self.get_layout_config_fn()
        
        avail_w = max(200, self.container.winfo_width() - 20)
        avail_h = max(200, self.container.winfo_height() - 20)
        
        pil_img = generate_layout_preview(cols, rows, landscape, max_size=(avail_w, avail_h))
        self._tk_img = ImageTk.PhotoImage(pil_img)
        self.preview_lbl.config(image=self._tk_img)
