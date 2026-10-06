import os
import platform
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

from core.pdf_processor import load_slides_from_files, compile_handout_pdf
from gui.controls_panel import ControlsPanel
from gui.preview_panel import LayoutPreviewPanel
from gui.review_panel import SlideReviewPanel


class HandoutGeneratorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Interactive Handout Generator")
        self.root.geometry("1150x800")
        self.root.minsize(850, 550)

        # Style configuration
        self.style = ttk.Style()
        if platform.system() == "Windows":
            self.style.theme_use("vista")
        else:
            self.style.theme_use("clam")

        self.style.configure("TButton", font=("Arial", 10))
        self.style.configure("Header.TLabel", font=("Arial", 10, "bold"))

        # Status variable
        self.status_var = tk.StringVar(value="Ready. Select input files/folder and click 'Load PDFs & Review Slides'.")

        self._build_layout()
        self._setup_keybindings()

    def _build_layout(self):
        # Bottom status bar
        self.status_bar = ttk.Label(
            self.root, textvariable=self.status_var, relief="sunken", anchor="w", padding=(6, 3)
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Main horizontal split
        self.main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Left panel: Controls
        self.controls_panel = ControlsPanel(
            self.main_paned,
            on_load_callback=self.on_load_pdfs,
            on_layout_change_callback=self.on_layout_changed
        )
        self.main_paned.add(self.controls_panel, weight=0)

        # Right panel: Notebook
        self.right_container = ttk.Frame(self.main_paned)
        self.main_paned.add(self.right_container, weight=1)

        self.notebook = ttk.Notebook(self.right_container)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Layout preview
        self.preview_panel = LayoutPreviewPanel(
            self.notebook,
            get_layout_config_fn=self.controls_panel.get_layout_config
        )
        self.notebook.add(self.preview_panel, text="1. Layout Settings")

        # Tab 2: Slide review
        self.review_panel = SlideReviewPanel(
            self.notebook,
            on_compile_callback=self.on_compile_pdf,
            on_status_msg=self.status_var.set
        )
        self.notebook.add(self.review_panel, text="2. Slide Review")

        # Initial preview rendering
        self.root.after(100, self.preview_panel.refresh_preview)

    def _setup_keybindings(self):
        try:
            self.root.unbind_class("TNotebook", "<Key-Left>")
            self.root.unbind_class("TNotebook", "<Key-Right>")
        except Exception as e:
            print(f"Notice: unbind_class TNotebook: {e}")

        # Bind Left, Right, Space at root level for slide review
        self.root.bind("<Left>", self._on_key_left)
        self.root.bind("<Right>", self._on_key_right)
        self.root.bind("<space>", self._on_key_space)

    def _is_text_input_focused(self) -> bool:
        focused = self.root.focus_get()
        if focused is None:
            return False
        return focused.winfo_class() in (
            "Entry", "TEntry", "Spinbox", "TSpinbox", "Text", "Listbox",
            "Button", "TButton",
        )

    def _on_key_left(self, event):
        if self._is_text_input_focused():
            return None
        if self.review_panel.raw_slides:
            # Switch to review tab if not already on it
            if self.notebook.select() != str(self.review_panel):
                self.notebook.select(self.review_panel)
            self.review_panel.nav_slide(-1)
            return "break"

    def _on_key_right(self, event):
        if self._is_text_input_focused():
            return None
        if self.review_panel.raw_slides:
            if self.notebook.select() != str(self.review_panel):
                self.notebook.select(self.review_panel)
            self.review_panel.nav_slide(1)
            return "break"

    def _on_key_space(self, event):
        if self._is_text_input_focused():
            return None
        if self.review_panel.raw_slides:
            self.review_panel.toggle_keep()
            return "break"

    def on_layout_changed(self):
        self.preview_panel.refresh_preview()

    def on_load_pdfs(self):
        pdf_paths = self.controls_panel.get_selected_pdf_paths()
        if not pdf_paths:
            messagebox.showwarning("No PDFs Found", "No PDF files were found from your selection.")
            return

        self.controls_panel.load_btn.config(state=tk.DISABLED)
        self.status_var.set(f"Extracting slides from {len(pdf_paths)} file(s). Please wait...")
        self.root.update_idletasks()

        try:
            slides = load_slides_from_files(pdf_paths)
            if not slides:
                messagebox.showwarning("Empty", "No slide pages could be extracted from the selected files.")
                self.status_var.set("Ready")
                return

            self.review_panel.load_slides(slides)
            self.notebook.select(self.review_panel)
            self.status_var.set(f"Loaded {len(slides)} slides from {len(pdf_paths)} PDF(s). Ready for review.")
        except Exception as e:
            messagebox.showerror("Error Loading PDFs", f"An error occurred while loading slides:\n{str(e)}")
            self.status_var.set("Error loading PDFs.")
        finally:
            self.controls_panel.load_btn.config(state=tk.NORMAL)

    def on_compile_pdf(self):
        output_dir, output_filename = self.controls_panel.get_output_config()
        if not output_dir or not output_filename:
            messagebox.showerror("Error", "Please provide a valid output directory and filename.")
            return

        if not output_filename.lower().endswith(".pdf"):
            output_filename += ".pdf"

        output_path = os.path.join(output_dir, output_filename)
        cols, rows, landscape = self.controls_panel.get_layout_config()

        self.review_panel.compile_btn.config(state=tk.DISABLED)
        self.status_var.set("Compiling Handout PDF...")
        self.root.update_idletasks()

        try:
            pages = compile_handout_pdf(
                self.review_panel.raw_slides,
                output_path,
                cols=cols,
                rows=rows,
                landscape=landscape
            )

            if pages == 0:
                messagebox.showinfo("Cancelled", "No slides were selected (kept) for handout generation.")
                self.status_var.set("Compilation cancelled: 0 slides kept.")
                return

            self.status_var.set(f"Handout compiled successfully! ({pages} page(s) -> {output_path})")
            messagebox.showinfo("Success", f"Handout compiled successfully!\nPages: {pages}\nSaved to:\n{output_path}")

            # Open folder in file explorer
            abs_dir = os.path.abspath(output_dir)
            try:
                if platform.system() == "Windows":
                    os.startfile(abs_dir)
                elif platform.system() == "Darwin":
                    subprocess.call(["open", abs_dir])
                else:
                    subprocess.call(["xdg-open", abs_dir])
            except Exception as e:
                print(f"Could not open directory: {e}")

        except Exception as e:
            messagebox.showerror("Compilation Error", f"Failed to compile PDF:\n{str(e)}")
            self.status_var.set("Compilation error.")
        finally:
            self.review_panel.compile_btn.config(state=tk.NORMAL)
