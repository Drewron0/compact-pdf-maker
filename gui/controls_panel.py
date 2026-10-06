import os
import platform
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Callable, List


class ControlsPanel(ttk.Frame):
    """
    Left controls panel containing:
    1. Input selection (Folder vs. Files roster) - permanently anchored at the top
    2. Output settings
    3. Layout settings (Columns, Rows, Orientation)
    4. Action trigger to load PDFs
    """
    def __init__(self, parent, on_load_callback: Callable[[], None], on_layout_change_callback: Callable[[], None]):
        super().__init__(parent)
        self.on_load_callback = on_load_callback
        self.on_layout_change_callback = on_layout_change_callback

        # Persisted state variables
        self.saved_folder_path = os.path.abspath("./input")
        self.saved_files_list: List[str] = []

        # UI state variables
        self.input_mode_var = tk.StringVar(value="folder")
        self.folder_path_var = tk.StringVar(value=self.saved_folder_path)
        self.output_dir_var = tk.StringVar(value=os.path.abspath("./handouts_output"))
        self.output_name_var = tk.StringVar(value="handout.pdf")
        self.cols_var = tk.IntVar(value=4)
        self.rows_var = tk.IntVar(value=3)
        self.landscape_var = tk.BooleanVar(value=True)

        self._build_ui()

    def _build_ui(self):
        # Scrollable canvas setup to handle small window heights responsively
        canvas = tk.Canvas(self, bd=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scroll_content = ttk.Frame(canvas, padding=8)

        scroll_content.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas_window = canvas.create_window((0, 0), window=scroll_content, anchor="nw")

        def _on_canvas_configure(e):
            canvas.itemconfig(canvas_window, width=e.width)

        canvas.bind("<Configure>", _on_canvas_configure)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Mousewheel scroll support
        def _on_mousewheel(e):
            if platform.system() == "Windows":
                canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
            elif platform.system() == "Darwin":
                canvas.yview_scroll(int(-1 * e.delta), "units")
            else:
                if e.num == 4:
                    canvas.yview_scroll(-1, "units")
                elif e.num == 5:
                    canvas.yview_scroll(1, "units")

        self.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        self.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        # --- SECTION 1: INPUT SELECTION (TOP) ---
        ttk.Label(scroll_content, text="1. Input Selection", style="Header.TLabel").pack(anchor="w", pady=(0, 4))

        mode_frame = ttk.Frame(scroll_content)
        mode_frame.pack(fill=tk.X, pady=(0, 6))
        ttk.Radiobutton(
            mode_frame, text="Select Folder", variable=self.input_mode_var,
            value="folder", command=self._on_mode_change
        ).pack(side=tk.LEFT, padx=(0, 12))
        ttk.Radiobutton(
            mode_frame, text="Select Specific Files", variable=self.input_mode_var,
            value="files", command=self._on_mode_change
        ).pack(side=tk.LEFT)

        # Container: fixed position so mode switch never repositions it
        self.input_container = ttk.Frame(scroll_content)
        self.input_container.pack(fill=tk.X, pady=(0, 10))

        # Sub-panel A: Folder Input
        self.folder_frame = ttk.Frame(self.input_container)
        self.folder_frame.pack(fill=tk.X)

        folder_row = ttk.Frame(self.folder_frame)
        folder_row.pack(fill=tk.X)
        self.folder_entry = ttk.Entry(folder_row, textvariable=self.folder_path_var)
        self.folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(folder_row, text="Browse...", command=self._browse_folder).pack(side=tk.RIGHT)

        # Sub-panel B: Specific Files Roster (hidden initially)
        self.roster_frame = ttk.Frame(self.input_container)

        roster_header = ttk.Frame(self.roster_frame)
        roster_header.pack(fill=tk.X, pady=(0, 2))
        self.roster_count_lbl = ttk.Label(roster_header, text="Selected Files (0):", font=("Arial", 9, "bold"))
        self.roster_count_lbl.pack(side=tk.LEFT)

        roster_list_frame = ttk.Frame(self.roster_frame)
        roster_list_frame.pack(fill=tk.X, pady=2)

        self.roster_listbox = tk.Listbox(roster_list_frame, selectmode=tk.EXTENDED, height=5)
        roster_scroll = ttk.Scrollbar(roster_list_frame, orient="vertical", command=self.roster_listbox.yview)
        self.roster_listbox.configure(yscrollcommand=roster_scroll.set)
        self.roster_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        roster_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        roster_btn_frame = ttk.Frame(self.roster_frame)
        roster_btn_frame.pack(fill=tk.X, pady=(4, 0))
        ttk.Button(roster_btn_frame, text="Add Files", command=self._add_files_to_roster).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(roster_btn_frame, text="Remove", command=self._remove_from_roster).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(roster_btn_frame, text="Clear", command=self._clear_roster).pack(side=tk.RIGHT)

        ttk.Separator(scroll_content, orient="horizontal").pack(fill=tk.X, pady=10)

        # --- SECTION 2: OUTPUT SETTINGS ---
        ttk.Label(scroll_content, text="2. Output Settings", style="Header.TLabel").pack(anchor="w", pady=(0, 4))
        ttk.Label(scroll_content, text="Output Directory:").pack(anchor="w")

        out_dir_frame = ttk.Frame(scroll_content)
        out_dir_frame.pack(fill=tk.X, pady=(2, 6))
        ttk.Entry(out_dir_frame, textvariable=self.output_dir_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(out_dir_frame, text="Browse...", command=self._browse_output).pack(side=tk.RIGHT)

        ttk.Label(scroll_content, text="Output Filename:").pack(anchor="w")
        ttk.Entry(scroll_content, textvariable=self.output_name_var).pack(fill=tk.X, pady=(2, 10))

        ttk.Separator(scroll_content, orient="horizontal").pack(fill=tk.X, pady=10)

        # --- SECTION 3: LAYOUT & PROCESSING ---
        ttk.Label(scroll_content, text="3. Layout & Processing", style="Header.TLabel").pack(anchor="w", pady=(0, 4))

        grid_frame = ttk.Frame(scroll_content)
        grid_frame.pack(fill=tk.X, pady=4)

        ttk.Label(grid_frame, text="Cols:").pack(side=tk.LEFT, padx=(0, 4))
        cols_spin = ttk.Spinbox(
            grid_frame, from_=1, to=10, textvariable=self.cols_var, width=4,
            command=self.on_layout_change_callback
        )
        cols_spin.pack(side=tk.LEFT, padx=(0, 15))
        cols_spin.bind('<KeyRelease>', lambda e: self.on_layout_change_callback())

        ttk.Label(grid_frame, text="Rows:").pack(side=tk.LEFT, padx=(0, 4))
        rows_spin = ttk.Spinbox(
            grid_frame, from_=1, to=10, textvariable=self.rows_var, width=4,
            command=self.on_layout_change_callback
        )
        rows_spin.pack(side=tk.LEFT)
        rows_spin.bind('<KeyRelease>', lambda e: self.on_layout_change_callback())

        ttk.Checkbutton(
            scroll_content, text="Landscape Orientation", variable=self.landscape_var,
            command=self.on_layout_change_callback
        ).pack(anchor="w", pady=6)

        self.load_btn = ttk.Button(
            scroll_content, text="Load PDFs & Review Slides",
            command=self.on_load_callback,
            takefocus=0
        )
        self.load_btn.pack(fill=tk.X, pady=(12, 10), ipady=6)

    def _on_mode_change(self):
        mode = self.input_mode_var.get()
        if mode == "folder":
            self.roster_frame.pack_forget()
            self.folder_frame.pack(fill=tk.X)
            self.folder_path_var.set(self.saved_folder_path)
        else:
            curr_val = self.folder_path_var.get().strip()
            if curr_val:
                self.saved_folder_path = curr_val
            self.folder_frame.pack_forget()
            self.roster_frame.pack(fill=tk.X)
            self._refresh_roster_view()

    def _browse_folder(self):
        path = filedialog.askdirectory(title="Select Folder with PDFs", initialdir=self.saved_folder_path)
        if path:
            abs_path = os.path.abspath(path)
            self.saved_folder_path = abs_path
            self.folder_path_var.set(abs_path)

    def _add_files_to_roster(self):
        initial_dir = self.saved_folder_path if os.path.isdir(self.saved_folder_path) else os.getcwd()
        files = filedialog.askopenfilenames(
            title="Select PDF Files to Add to Roster",
            initialdir=initial_dir,
            filetypes=[("PDF Files", "*.pdf")]
        )
        if files:
            for f in files:
                abs_f = os.path.abspath(f)
                if abs_f not in self.saved_files_list:
                    self.saved_files_list.append(abs_f)
            self._refresh_roster_view()

    def _remove_from_roster(self):
        selected_indices = list(self.roster_listbox.curselection())
        if not selected_indices:
            return
        for idx in reversed(selected_indices):
            del self.saved_files_list[idx]
        self._refresh_roster_view()

    def _clear_roster(self):
        self.saved_files_list.clear()
        self._refresh_roster_view()

    def _refresh_roster_view(self):
        self.roster_listbox.delete(0, tk.END)
        for f in self.saved_files_list:
            self.roster_listbox.insert(tk.END, os.path.basename(f))
        self.roster_count_lbl.config(text=f"Selected Files ({len(self.saved_files_list)}):")

    def _browse_output(self):
        path = filedialog.askdirectory(title="Select Output Folder", initialdir=self.output_dir_var.get())
        if path:
            self.output_dir_var.set(os.path.abspath(path))

    def get_selected_pdf_paths(self) -> List[str]:
        """Returns list of PDF file paths based on active input mode."""
        mode = self.input_mode_var.get()
        if mode == "folder":
            folder = self.folder_path_var.get().strip()
            self.saved_folder_path = folder
            if not os.path.isdir(folder):
                messagebox.showerror("Invalid Folder", f"The folder does not exist:\n{folder}")
                return []
            pdfs = [
                os.path.join(folder, f)
                for f in sorted(os.listdir(folder))
                if f.lower().endswith('.pdf')
            ]
            return pdfs
        else:
            return [f for f in self.saved_files_list if os.path.exists(f)]

    def get_layout_config(self):
        try:
            cols = max(1, self.cols_var.get())
            rows = max(1, self.rows_var.get())
        except tk.TclError:
            cols, rows = 4, 3
        return cols, rows, self.landscape_var.get()

    def get_output_config(self):
        return self.output_dir_var.get().strip(), self.output_name_var.get().strip()
