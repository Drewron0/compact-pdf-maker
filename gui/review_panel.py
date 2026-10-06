import platform
import tkinter as tk
from tkinter import ttk
from typing import List, Dict, Any, Callable, Set, Optional
from PIL import Image, ImageTk

# --- Color Palette ---
COLOR_KEPT_BADGE_BG   = "#dff0d8"
COLOR_KEPT_BADGE_FG   = "#2d6a2d"
COLOR_KEPT_VIEWER_BG  = "#e8f5e9"

COLOR_SKIP_BADGE_BG   = "#f8d7da"
COLOR_SKIP_BADGE_FG   = "#8b1a2a"
COLOR_SKIP_VIEWER_BG  = "#f8d7da"

COLOR_CARD_DEFAULT    = "#3c4043"
COLOR_CARD_SELECTED   = "#E1C16E"
COLOR_CARD_ACTIVE     = "#e65100"
COLOR_FILMSTRIP_BG    = "#2b2d30"


class SlideReviewPanel(ttk.Frame):
    """
    Slide review panel with responsive slide viewer, filmstrip, 
    multi-select, and action toolbar.
    """

    def __init__(self, parent, on_compile_callback: Callable[[], None], on_status_msg: Callable[[str], None]):
        super().__init__(parent, takefocus=True)
        self.on_compile_callback = on_compile_callback
        self.on_status_msg = on_status_msg

        self.raw_slides: List[Dict[str, Any]] = []
        self.current_idx: int = 0
        self.anchor_idx: int = 0
        self.selected_indices: Set[int] = set()
        self.drag_start_idx: Optional[int] = None
        self.is_dragging: bool = False

        self._thumb_img_refs: List[ImageTk.PhotoImage] = []
        self._big_tk_img: Optional[ImageTk.PhotoImage] = None
        self._resize_timer: Optional[str] = None

        self._build_ui()

    # --- Layout ---

    def _build_ui(self):
        # Horizontal scrollbar
        self.filmstrip_scrollbar = ttk.Scrollbar(self, orient=tk.HORIZONTAL)
        self.filmstrip_scrollbar.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=(0, 4))

        # Filmstrip canvas
        self.canvas = tk.Canvas(
            self, height=118, bg=COLOR_FILMSTRIP_BG, highlightthickness=0
        )
        self.canvas.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=(0, 2))

        self.filmstrip_scrollbar.config(command=self.canvas.xview)
        self.canvas.config(xscrollcommand=self.filmstrip_scrollbar.set)

        self.filmstrip_inner = tk.Frame(self.canvas, bg=COLOR_FILMSTRIP_BG)
        self._filmstrip_window = self.canvas.create_window((0, 0), window=self.filmstrip_inner, anchor="nw")

        self.filmstrip_inner.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")
        ))

        self.canvas.bind("<MouseWheel>", self._h_scroll)
        self.canvas.bind("<Shift-MouseWheel>", self._h_scroll)
        self.canvas.bind("<Button-4>", self._h_scroll)
        self.canvas.bind("<Button-5>", self._h_scroll)

        # Batch selection toolbar
        batch_bar = ttk.Frame(self)
        batch_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=(4, 2))

        self.sel_count_lbl = ttk.Label(batch_bar, text="No slides loaded", font=("Arial", 9))
        self.sel_count_lbl.pack(side=tk.LEFT, padx=(0, 12))

        ttk.Button(batch_bar, text="Select All", width=10, takefocus=0,
                   command=self.select_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(batch_bar, text="Clear", width=8, takefocus=0,
                   command=self.clear_selection).pack(side=tk.LEFT, padx=2)
        ttk.Button(batch_bar, text="Invert", width=8, takefocus=0,
                   command=self.invert_selection).pack(side=tk.LEFT, padx=2)

        ttk.Separator(batch_bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        ttk.Button(batch_bar, text="Keep Selected", takefocus=0,
                   command=lambda: self.set_selected_keep_state(True)).pack(side=tk.LEFT, padx=2)
        ttk.Button(batch_bar, text="Skip Selected", takefocus=0,
                   command=lambda: self.set_selected_keep_state(False)).pack(side=tk.LEFT, padx=2)

        # Main control bar
        ctrl_bar = ttk.Frame(self)
        ctrl_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=(4, 6))

        self.slide_info_lbl = ttk.Label(ctrl_bar, text="No slides loaded", font=("Arial", 10, "bold"))
        self.slide_info_lbl.pack(side=tk.LEFT, padx=(0, 12))

        self.toggle_btn = ttk.Button(
            ctrl_bar, text="Toggle Keep/Skip  (Space)", command=self.toggle_keep, takefocus=0
        )
        self.toggle_btn.pack(side=tk.LEFT, padx=5)

        self.compile_btn = ttk.Button(
            ctrl_bar, text="Finish & Compile PDF",
            command=self.on_compile_callback, state=tk.DISABLED, takefocus=0
        )
        self.compile_btn.pack(side=tk.RIGHT, padx=5, ipady=3)

        # Slide viewer
        self.viewer_container = tk.Frame(self, bg="#d0d0d0", relief="flat", bd=2)
        self.viewer_container.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=8, pady=(8, 4))

        self.big_img_lbl = tk.Label(self.viewer_container, bg="#d0d0d0", anchor="center")
        self.big_img_lbl.pack(fill=tk.BOTH, expand=True)

        self.viewer_container.bind("<Configure>", self._on_viewer_resize)

        for w in (self, self.viewer_container, self.big_img_lbl, self.canvas, self.filmstrip_inner, batch_bar, ctrl_bar):
            w.bind("<Button-1>", lambda e: self.clear_input_focus(), add="+")

        # Setup top-level window key bindings
        self.after(100, self._setup_global_keybindings)

    def _setup_global_keybindings(self):
        top = self.winfo_toplevel()
        for key_pattern in ("<Left>", "<Right>", "<Shift-Left>", "<Shift-Right>", 
                            "<Control-Shift-Left>", "<Control-Shift-Right>"):
            top.bind(key_pattern, self._handle_arrow_key, add="+")

    def _handle_arrow_key(self, event):
        if not self.raw_slides:
            return

        focused = self.focus_get()
        if isinstance(focused, (tk.Entry, ttk.Entry, tk.Text, ttk.Combobox)):
            return

        keysym = event.keysym
        if keysym not in ("Left", "Right"):
            return

        delta = -1 if keysym == "Left" else 1

        is_shift = bool(event.state & 0x0001)
        is_ctrl  = bool(event.state & 0x0004) or bool(event.state & 0x20000)

        self.nav_slide(delta, extend_selection=is_shift, preserve_ctrl=(is_shift and is_ctrl))
        return "break"

    def clear_input_focus(self):
        self.winfo_toplevel().focus_set()

    # --- Scroll Helpers ---

    def _h_scroll(self, event):
        if event.num == 4:
            self.canvas.xview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.xview_scroll(1, "units")
        elif hasattr(event, "delta"):
            if platform.system() == "Windows":
                self.canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
            else:
                self.canvas.xview_scroll(int(-1 * event.delta), "units")

    def _bind_filmstrip_scroll(self, widget: tk.Widget):
        widget.bind("<MouseWheel>", self._h_scroll)
        widget.bind("<Shift-MouseWheel>", self._h_scroll)
        widget.bind("<Button-4>", self._h_scroll)
        widget.bind("<Button-5>", self._h_scroll)
        for child in widget.winfo_children():
            self._bind_filmstrip_scroll(child)

    # --- Viewer Resize ---

    def _on_viewer_resize(self, event):
        if not self.raw_slides:
            return
        if self._resize_timer:
            self.after_cancel(self._resize_timer)
        self._resize_timer = self.after(50, self.update_active_slide_display)

    # --- Loading ---

    def load_slides(self, slides: List[Dict[str, Any]]):
        self.raw_slides = slides
        self.current_idx = 0
        self.anchor_idx = 0
        self.selected_indices = {0} if slides else set()

        if slides:
            self.compile_btn.config(state=tk.NORMAL)
            self._render_filmstrip()
            self.update_active_slide_display()
            self._scroll_to_active()
        else:
            self.compile_btn.config(state=tk.DISABLED)
            self.slide_info_lbl.config(text="No slides loaded")
            self.sel_count_lbl.config(text="No slides loaded")
            self.big_img_lbl.config(image="", bg="#d0d0d0")
            self._thumb_img_refs.clear()
            for w in self.filmstrip_inner.winfo_children():
                w.destroy()

    # --- Filmstrip Rendering ---

    def _render_filmstrip(self):
        for w in self.filmstrip_inner.winfo_children():
            w.destroy()
        self._thumb_img_refs.clear()

        for idx, slide in enumerate(self.raw_slides):
            is_kept = slide.get('kept', True)

            card = tk.Frame(self.filmstrip_inner, bd=3, relief="solid", bg=COLOR_CARD_DEFAULT, cursor="hand2")
            card.pack(side=tk.LEFT, padx=3, pady=4)

            thumb = slide['img'].copy()
            thumb.thumbnail((96, 70), Image.Resampling.LANCZOS)
            tk_thumb = ImageTk.PhotoImage(thumb)
            self._thumb_img_refs.append(tk_thumb)

            img_lbl = tk.Label(card, image=tk_thumb, bg="#1e1e1e", cursor="hand2")
            img_lbl.pack(padx=2, pady=(2, 0))

            badge_bg = COLOR_KEPT_BADGE_BG if is_kept else COLOR_SKIP_BADGE_BG
            badge_fg = COLOR_KEPT_BADGE_FG if is_kept else COLOR_SKIP_BADGE_FG
            badge_txt = f"{idx + 1}"
            status_lbl = tk.Label(
                card, text=badge_txt, bg=badge_bg, fg=badge_fg,
                font=("Arial", 8, "bold"), cursor="hand2", pady=1
            )
            status_lbl.pack(fill=tk.X, padx=2, pady=(0, 2))

            for w in (card, img_lbl, status_lbl):
                w.bind("<ButtonPress-1>",   lambda e, i=idx: self._on_thumb_press(e, i))
                w.bind("<B1-Motion>",        self._on_thumb_motion)
                w.bind("<ButtonRelease-1>",  self._on_thumb_release)

            self._bind_filmstrip_scroll(card)

            slide['thumb_card'] = card
            slide['status_lbl'] = status_lbl

        self._update_selection_visuals()

    # --- Mouse Selection ---

    def _on_thumb_press(self, event, idx: int):
        self.clear_input_focus()
        self.drag_start_idx = idx
        self.is_dragging = False

        is_shift = bool(event.state & 0x0001)
        is_ctrl  = bool(event.state & 0x0004) or bool(event.state & 0x20000)

        if is_shift:
            start = min(self.anchor_idx, idx)
            end   = max(self.anchor_idx, idx)
            new_range = set(range(start, end + 1))
            if is_ctrl:
                self.selected_indices.update(new_range)
            else:
                self.selected_indices = new_range
            self.current_idx = idx
        elif is_ctrl:
            if idx in self.selected_indices and len(self.selected_indices) > 1:
                self.selected_indices.discard(idx)
            else:
                self.selected_indices.add(idx)
            self.anchor_idx  = idx
            self.current_idx = idx
        else:
            self.selected_indices = {idx}
            self.anchor_idx  = idx
            self.current_idx = idx

        self.update_active_slide_display()

    def _on_thumb_motion(self, event):
        if self.drag_start_idx is None or not self.raw_slides:
            return
        self.is_dragging = True
        hovered = self._slide_at_x(event.x_root)
        if hovered is not None and hovered != self.current_idx:
            start = min(self.drag_start_idx, hovered)
            end   = max(self.drag_start_idx, hovered)
            self.selected_indices = set(range(start, end + 1))
            self.current_idx = hovered
            self.update_active_slide_display()
            self._scroll_to_active()

    def _on_thumb_release(self, event):
        if self.is_dragging:
            self.anchor_idx = self.current_idx
        self.drag_start_idx = None
        self.is_dragging = False

    def _slide_at_x(self, x_root: int) -> Optional[int]:
        for idx, slide in enumerate(self.raw_slides):
            card = slide.get('thumb_card')
            if card and card.winfo_exists():
                cx = card.winfo_rootx()
                if cx <= x_root <= cx + card.winfo_width():
                    return idx
        return None

    # --- Batch Actions ---

    def select_all(self):
        if not self.raw_slides:
            return
        self.selected_indices = set(range(len(self.raw_slides)))
        self._refresh_ui()

    def clear_selection(self):
        if not self.raw_slides:
            return
        self.selected_indices = {self.current_idx}
        self._refresh_ui()

    def invert_selection(self):
        if not self.raw_slides:
            return
        all_idx = set(range(len(self.raw_slides)))
        inverted = all_idx - self.selected_indices
        self.selected_indices = inverted if inverted else {self.current_idx}
        self._refresh_ui()

    def set_selected_keep_state(self, keep: bool):
        if not self.raw_slides:
            return
        for i in self.selected_indices:
            self.raw_slides[i]['kept'] = keep
        self._refresh_ui()

    def toggle_keep(self):
        if not self.raw_slides:
            return
        targets = self.selected_indices or {self.current_idx}
        all_kept = all(self.raw_slides[i]['kept'] for i in targets)
        new_state = not all_kept
        for i in targets:
            self.raw_slides[i]['kept'] = new_state
        self._refresh_ui()

    def nav_slide(self, delta: int, extend_selection: bool = False, preserve_ctrl: bool = False):
        if not self.raw_slides:
            return
        new_idx = self.current_idx + delta
        if 0 <= new_idx < len(self.raw_slides):
            self.current_idx = new_idx

            if extend_selection:
                start = min(self.anchor_idx, self.current_idx)
                end   = max(self.anchor_idx, self.current_idx)
                new_range = set(range(start, end + 1))

                if preserve_ctrl:
                    self.selected_indices.update(new_range)
                else:
                    self.selected_indices = new_range
            else:
                self.anchor_idx = new_idx
                self.selected_indices = {new_idx}

            self._refresh_ui()
            self._scroll_to_active()

    # --- Display Refresh ---

    def _refresh_ui(self):
        self.update_active_slide_display()
        self.filmstrip_inner.update_idletasks()

    def _scroll_to_active(self):
        if not self.raw_slides:
            return
        fraction = self.current_idx / len(self.raw_slides)
        self.canvas.xview_moveto(max(0.0, fraction - 0.08))

    def update_active_slide_display(self):
        if not self.raw_slides or not (0 <= self.current_idx < len(self.raw_slides)):
            return

        slide     = self.raw_slides[self.current_idx]
        total     = len(self.raw_slides)
        sel_count = len(self.selected_indices)

        info = f"{slide['file_name']}   Slide {slide['slide_num']}  ({self.current_idx + 1} / {total})"
        self.slide_info_lbl.config(text=info)

        if sel_count > 1:
            lo = min(self.selected_indices) + 1
            hi = max(self.selected_indices) + 1
            self.sel_count_lbl.config(text=f"{sel_count} selected  (#{lo} - #{hi})")
        elif sel_count == 1:
            self.sel_count_lbl.config(text=f"1 selected  (#{self.current_idx + 1})")
        else:
            self.sel_count_lbl.config(text="None selected")

        avail_w = max(120, self.viewer_container.winfo_width()  - 16)
        avail_h = max(120, self.viewer_container.winfo_height() - 16)

        display_img = slide['img'].copy()
        display_img.thumbnail((avail_w, avail_h), Image.Resampling.LANCZOS)
        self._big_tk_img = ImageTk.PhotoImage(display_img)

        is_kept  = slide['kept']
        viewer_bg = COLOR_KEPT_VIEWER_BG if is_kept else COLOR_SKIP_VIEWER_BG
        self.viewer_container.config(bg=viewer_bg)
        self.big_img_lbl.config(image=self._big_tk_img, bg=viewer_bg)

        self._update_selection_visuals()

    def _update_selection_visuals(self):
        for idx, slide in enumerate(self.raw_slides):
            card = slide.get('thumb_card')
            lbl  = slide.get('status_lbl')
            if not card or not lbl or not card.winfo_exists():
                continue

            is_kept   = slide['kept']
            badge_bg  = COLOR_KEPT_BADGE_BG if is_kept else COLOR_SKIP_BADGE_BG
            badge_fg  = COLOR_KEPT_BADGE_FG if is_kept else COLOR_SKIP_BADGE_FG
            badge_txt = str(idx + 1)
            lbl.config(bg=badge_bg, fg=badge_fg, text=badge_txt)

            if idx == self.current_idx:
                card.config(bg=COLOR_CARD_ACTIVE, bd=4, relief="solid")
            elif idx in self.selected_indices:
                card.config(bg=COLOR_CARD_SELECTED, bd=4, relief="solid")
            else:
                card.config(bg=COLOR_CARD_DEFAULT, bd=3, relief="solid")