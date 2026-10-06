import os
import sys
import math
import platform
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pymupdf
from PIL import Image, ImageDraw, ImageFont, ImageTk

class HandoutGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Interactive Handout Generator")
        self.root.geometry("1000x650")
        
        # Modernize UI styling
        self.style = ttk.Style()
        if platform.system() == "Windows":
            self.style.theme_use("vista")
        else:
            self.style.theme_use("clam")

        # Variables
        self.input_mode_var = tk.StringVar(value="folder")
        self.input_path_var = tk.StringVar(value=os.path.abspath("./input"))
        self.output_dir_var = tk.StringVar(value=os.path.abspath("./handouts_output"))
        self.output_name_var = tk.StringVar(value="Interactive_Handout.pdf")
        self.cols_var = tk.IntVar(value=4)
        self.rows_var = tk.IntVar(value=3)
        self.landscape_var = tk.BooleanVar(value=True)
        self.human_filter_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="Ready")

        self.create_widgets()
        self.update_preview()

    def create_widgets(self):
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- LEFT FRAME: CONTROLS ---
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=1)

        ttk.Label(left_frame, text="Input Selection", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 10))
        
        mode_frame = ttk.Frame(left_frame)
        mode_frame.grid(row=1, column=0, columnspan=3, sticky="w", pady=5)
        ttk.Radiobutton(mode_frame, text="Select Folder", variable=self.input_mode_var, value="folder", command=self.clear_input).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(mode_frame, text="Select Specific Files", variable=self.input_mode_var, value="files", command=self.clear_input).pack(side=tk.LEFT)

        ttk.Entry(left_frame, textvariable=self.input_path_var, width=40).grid(row=2, column=0, columnspan=2, sticky="ew", pady=5)
        ttk.Button(left_frame, text="Browse", command=self.browse_input).grid(row=2, column=2, padx=5, pady=5)

        ttk.Separator(left_frame, orient="horizontal").grid(row=3, column=0, columnspan=3, sticky="ew", pady=15)

        ttk.Label(left_frame, text="Output Settings", font=("Arial", 12, "bold")).grid(row=4, column=0, sticky="w", pady=(0, 10))
        
        ttk.Label(left_frame, text="Output Directory:").grid(row=5, column=0, sticky="w", pady=5)
        ttk.Entry(left_frame, textvariable=self.output_dir_var, width=30).grid(row=5, column=1, sticky="ew", pady=5)
        ttk.Button(left_frame, text="Browse", command=self.browse_output).grid(row=5, column=2, padx=5, pady=5)

        ttk.Label(left_frame, text="Output Filename:").grid(row=6, column=0, sticky="w", pady=5)
        ttk.Entry(left_frame, textvariable=self.output_name_var, width=30).grid(row=6, column=1, sticky="ew", pady=5)

        ttk.Separator(left_frame, orient="horizontal").grid(row=7, column=0, columnspan=3, sticky="ew", pady=15)

        ttk.Label(left_frame, text="Layout & Processing", font=("Arial", 12, "bold")).grid(row=8, column=0, sticky="w", pady=(0, 10))

        grid_frame = ttk.Frame(left_frame)
        grid_frame.grid(row=9, column=0, columnspan=3, sticky="w")
        ttk.Label(grid_frame, text="Columns:").pack(side=tk.LEFT, padx=(0, 5))
        cols_spin = ttk.Spinbox(grid_frame, from_=1, to=10, textvariable=self.cols_var, width=5, command=self.update_preview)
        cols_spin.pack(side=tk.LEFT, padx=(0, 20))
        cols_spin.bind('<KeyRelease>', lambda e: self.update_preview())
        
        ttk.Label(grid_frame, text="Rows:").pack(side=tk.LEFT, padx=(0, 5))
        rows_spin = ttk.Spinbox(grid_frame, from_=1, to=10, textvariable=self.rows_var, width=5, command=self.update_preview)
        rows_spin.pack(side=tk.LEFT)
        rows_spin.bind('<KeyRelease>', lambda e: self.update_preview())

        ttk.Checkbutton(left_frame, text="Landscape Mode", variable=self.landscape_var, command=self.update_preview).grid(row=10, column=0, columnspan=3, sticky="w", pady=10)
        ttk.Checkbutton(left_frame, text="Enable Manual Slide Selection (Human Filter)", variable=self.human_filter_var).grid(row=11, column=0, columnspan=3, sticky="w", pady=5)

        self.generate_btn = ttk.Button(left_frame, text="Generate Handout", command=self.process_pdfs)
        self.generate_btn.grid(row=12, column=0, columnspan=3, sticky="ew", pady=20, ipady=10)

        # --- RIGHT FRAME: PREVIEW ---
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=2)
        
        ttk.Label(right_frame, text="Layout Preview", font=("Arial", 12, "bold")).pack(pady=(0, 10))
        self.preview_lbl = tk.Label(right_frame, bg="#e8eaed", relief="sunken")
        self.preview_lbl.pack(expand=True, fill=tk.BOTH)
        
        # Status bar
        ttk.Label(self.root, textvariable=self.status_var, relief="sunken", anchor="w").pack(side=tk.BOTTOM, fill=tk.X)

        left_frame.columnconfigure(1, weight=1)

    def clear_input(self):
        self.input_path_var.set("")

    def browse_input(self):
        if self.input_mode_var.get() == "folder":
            path = filedialog.askdirectory(title="Select Folder with PDFs")
            if path: self.input_path_var.set(path)
        else:
            files = filedialog.askopenfilenames(title="Select PDF Files", filetypes=[("PDF Files", "*.pdf")])
            if files: self.input_path_var.set(";".join(files))

    def browse_output(self):
        path = filedialog.askdirectory(title="Select Output Folder")
        if path: self.output_dir_var.set(path)

    def update_preview(self, *args):
        try:
            cols, rows = self.cols_var.get(), self.rows_var.get()
        except tk.TclError:
            return

        if cols < 1: cols = 1
        if rows < 1: rows = 1
        landscape = self.landscape_var.get()

        A4_W, A4_H = (3508, 2480) if landscape else (2480, 3508)
        canvas = Image.new('RGB', (A4_W, A4_H), 'white')
        draw = ImageDraw.Draw(canvas)

        MARGIN_X, MARGIN_TOP, MARGIN_BOTTOM = 30, 40, 70
        PADDING_X, PADDING_Y = 15, 15

        slot_w = (A4_W - (2 * MARGIN_X) - (cols - 1) * PADDING_X) // cols
        slot_h = (A4_H - MARGIN_TOP - MARGIN_BOTTOM - (rows - 1) * PADDING_Y) // rows

        try:
            font = ImageFont.truetype("arial.ttf", 60)
            sub_font = ImageFont.truetype("arial.ttf", 40)
        except IOError:
            font = ImageFont.load_default()
            sub_font = font

        draw.rectangle([0, 0, A4_W - 1, A4_H - 1], outline="black", width=5)

        for r in range(rows):
            for c in range(cols):
                x = MARGIN_X + c * (slot_w + PADDING_X)
                y = MARGIN_TOP + r * (slot_h + PADDING_Y)
                draw.rectangle([x, y, x + slot_w, y + slot_h], outline="#1a73e8", width=4, fill="#f8f9fa")

                if r == 0 and c == 0:
                    draw.text((x + 20, y + 15), "[Title Preview]", fill="darkblue", font=font)
                    slide_y = y + 80
                    slide_h = slot_h - 80
                else:
                    slide_y = y + 10
                    slide_h = slot_h - 20

                draw.rectangle([x + 10, slide_y, x + slot_w - 10, slide_y + slide_h], outline="#80868b", width=2, fill="#e8eaed")
                
                label = f"Slide ({r+1},{c+1})"
                try:
                    bbox = draw.textbbox((0, 0), label, font=sub_font)
                    txt_w = bbox[2] - bbox[0]
                except AttributeError:
                    txt_w = draw.textsize(label, font=sub_font)[0]
                draw.text((x + (slot_w - txt_w) // 2, slide_y + (slide_h // 2) - 20), label, fill="#3c4043", font=sub_font)

        page_lbl = "- Page 1 -"
        try:
            bbox = draw.textbbox((0, 0), page_lbl, font=font)
            txt_w = bbox[2] - bbox[0]
        except AttributeError:
            txt_w = draw.textsize(page_lbl, font=font)[0]
        draw.text(((A4_W - txt_w) // 2, A4_H - 60), page_lbl, fill="black", font=font)

        canvas.thumbnail((600, 600))
        self.tk_preview = ImageTk.PhotoImage(canvas)
        self.preview_lbl.config(image=self.tk_preview)

    def process_pdfs(self):
        input_data = self.input_path_var.get()
        if not input_data:
            messagebox.showerror("Error", "Please select input folder or files.")
            return

        pdf_paths = []
        if self.input_mode_var.get() == "folder":
            if not os.path.isdir(input_data):
                messagebox.showerror("Error", "Invalid input directory.")
                return
            pdf_paths = [os.path.join(input_data, f) for f in sorted(os.listdir(input_data)) if f.lower().endswith('.pdf')]
        else:
            pdf_paths = input_data.split(";")

        if not pdf_paths:
            messagebox.showwarning("Warning", "No PDF files found to process.")
            return

        self.status_var.set("Extracting slides from PDFs...")
        self.root.update_idletasks()

        raw_slides = []
        for file_path in pdf_paths:
            file_name = os.path.basename(file_path)
            try:
                doc = pymupdf.open(file_path)
                for slide_idx in range(len(doc)):
                    page = doc.load_page(slide_idx)
                    pix = page.get_pixmap(dpi=300)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    raw_slides.append({
                        "img": img,
                        "file_name": file_name,
                        "slide_num": slide_idx + 1
                    })
            except Exception as e:
                messagebox.showerror("PDF Error", f"Failed to read {file_name}:\n{str(e)}")

        if not raw_slides:
            self.status_var.set("Ready")
            return

        if self.human_filter_var.get():
            self.open_reviewer(raw_slides)
        else:
            self.compile_pdf(raw_slides)

    def open_reviewer(self, slides):
        ReviewerWindow(self, slides)

    def compile_pdf(self, slides_to_process):
        self.status_var.set("Compiling Handout PDF...")
        self.root.update_idletasks()
        
        # --- FIX TITLE ASSIGNMENT: Assign title to the first KEPT slide per PDF ---
        final_slides = []
        seen_pdfs = set()
        for slide in slides_to_process:
            fname = slide["file_name"]
            if fname not in seen_pdfs:
                title = fname.replace('.pdf', '')
                seen_pdfs.add(fname)
            else:
                title = ""
            final_slides.append({
                "img": slide["img"],
                "title": title
            })
        
        if not final_slides:
            messagebox.showinfo("Cancelled", "No slides were selected for compilation.")
            self.status_var.set("Ready")
            return

        cols, rows = self.cols_var.get(), self.rows_var.get()
        landscape = self.landscape_var.get()
        A4_W, A4_H = (3508, 2480) if landscape else (2480, 3508)
        MARGIN_X, MARGIN_TOP, MARGIN_BOTTOM = 30, 40, 70
        PADDING_X, PADDING_Y = 15, 15

        try:
            font = ImageFont.truetype("arial.ttf", 45)
            page_font = ImageFont.truetype("arial.ttf", 40)
        except IOError:
            font = ImageFont.load_default()
            page_font = font

        total_slides = len(final_slides)
        slides_per_page = cols * rows
        total_pages = math.ceil(total_slides / slides_per_page)

        slot_w = (A4_W - (2 * MARGIN_X) - (cols - 1) * PADDING_X) // cols
        slot_h = (A4_H - MARGIN_TOP - MARGIN_BOTTOM - (rows - 1) * PADDING_Y) // rows

        out_images = []

        for p in range(total_pages):
            canvas = Image.new('RGB', (A4_W, A4_H), 'white')
            draw = ImageDraw.Draw(canvas)

            for i in range(slides_per_page):
                global_idx = p * slides_per_page + i
                if global_idx >= total_slides:
                    break

                slide = final_slides[global_idx]
                img, title = slide["img"], slide["title"]
                
                # Create a copy so we don't modify the original image object if re-run
                display_img = img.copy() 
                display_img.thumbnail((slot_w, slot_h))

                r, c = i // cols, i % cols
                x = MARGIN_X + c * (slot_w + PADDING_X)
                y = MARGIN_TOP + r * (slot_h + PADDING_Y)
                x_offset = x + (slot_w - display_img.width) // 2

                if title:
                    try:
                        bbox = draw.textbbox((0, 0), title, font=font)
                        text_w = bbox[2] - bbox[0]
                    except AttributeError:
                        text_w = draw.textsize(title, font=font)[0]
                    
                    text_x = x + (slot_w - text_w) // 2
                    draw.text((text_x, y), title, fill="darkblue", font=font)
                    y_offset = y + 55
                else:
                    y_offset = y + (slot_h - display_img.height) // 2

                canvas.paste(display_img, (x_offset, y_offset))

            page_text = f"- {p + 1} -"
            try:
                bbox = draw.textbbox((0, 0), page_text, font=page_font)
                text_w = bbox[2] - bbox[0]
            except AttributeError:
                text_w = draw.textsize(page_text, font=page_font)[0]
            draw.text(((A4_W - text_w) // 2, A4_H - 50), page_text, fill="black", font=page_font)
            out_images.append(canvas)

        out_dir = self.output_dir_var.get()
        os.makedirs(out_dir, exist_ok=True)
        output_path = os.path.join(out_dir, self.output_name_var.get())

        if out_images:
            out_images[0].save(output_path, save_all=True, append_images=out_images[1:])
            self.status_var.set(f"Done! Saved to {output_path}")
            
            # Open output folder automatically without closing app
            abs_output_dir = os.path.abspath(out_dir)
            try:
                if platform.system() == "Windows":
                    os.startfile(abs_output_dir)
                elif platform.system() == "Darwin":
                    subprocess.call(["open", abs_output_dir])
                else:
                    subprocess.call(["xdg-open", abs_output_dir])
            except Exception as e:
                print(f"Could not open output folder: {e}")


class ReviewerWindow:
    def __init__(self, parent_app, slides):
        self.parent_app = parent_app
        self.slides = slides
        self.selections = [True] * len(slides)  # Default to keeping all
        self.current_idx = 0

        self.window = tk.Toplevel(parent_app.root)
        self.window.title("Slide Reviewer")
        self.window.geometry("900x700")
        self.window.grab_set()  # Make window modal

        # Top Control Bar
        top_frame = ttk.Frame(self.window)
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.title_lbl = ttk.Label(top_frame, font=("Arial", 14, "bold"))
        self.title_lbl.pack(side=tk.LEFT)

        self.status_lbl = ttk.Label(top_frame, font=("Arial", 12))
        self.status_lbl.pack(side=tk.RIGHT)

        # Image Display
        self.img_lbl = tk.Label(self.window, bg="#333333")
        self.img_lbl.pack(expand=True, fill=tk.BOTH, padx=10, pady=5)

        # Bottom Control Bar
        bottom_frame = ttk.Frame(self.window)
        bottom_frame.pack(fill=tk.X, padx=10, pady=15)

        ttk.Button(bottom_frame, text="⬅ Previous (Left Arrow)", command=self.prev_slide).pack(side=tk.LEFT, padx=5)
        
        self.toggle_btn = ttk.Button(bottom_frame, text="Toggle Keep/Discard (Space)", command=self.toggle_keep)
        self.toggle_btn.pack(side=tk.LEFT, expand=True, padx=5)

        ttk.Button(bottom_frame, text="Next ➡ (Right Arrow)", command=self.next_slide).pack(side=tk.LEFT, padx=5)

        ttk.Button(bottom_frame, text="Finish & Compile", command=self.finish_review).pack(side=tk.RIGHT, padx=20)

        # Keybinds
        self.window.bind("<Left>", lambda e: self.prev_slide())
        self.window.bind("<Right>", lambda e: self.next_slide())
        self.window.bind("<space>", lambda e: self.toggle_keep())
        self.window.bind("<Return>", lambda e: self.finish_review())

        self.update_view()

    def update_view(self):
        slide = self.slides[self.current_idx]
        self.title_lbl.config(text=f"File: {slide['file_name']} | Slide {slide['slide_num']}")
        self.status_lbl.config(text=f"{self.current_idx + 1} / {len(self.slides)}")

        # Outline color based on selection state
        is_kept = self.selections[self.current_idx]
        bg_color = "#4CAF50" if is_kept else "#F44336"  # Green for keep, Red for discard
        self.img_lbl.config(bg=bg_color)
        
        btn_text = "✔ Kept (Press Space to Discard)" if is_kept else "✖ Discarded (Press Space to Keep)"
        self.toggle_btn.config(text=btn_text)

        display_img = slide['img'].copy()
        display_img.thumbnail((850, 550))
        self.tk_img = ImageTk.PhotoImage(display_img)
        self.img_lbl.config(image=self.tk_img)

    def next_slide(self):
        if self.current_idx < len(self.slides) - 1:
            self.current_idx += 1
            self.update_view()

    def prev_slide(self):
        if self.current_idx > 0:
            self.current_idx -= 1
            self.update_view()

    def toggle_keep(self):
        self.selections[self.current_idx] = not self.selections[self.current_idx]
        self.next_slide() # Auto-advance on toggle to speed up manual review
        if self.current_idx == len(self.slides) - 1:
            self.update_view() # Ensure visual updates if we hit the end

    def finish_review(self):
        filtered_slides = [s for i, s in enumerate(self.slides) if self.selections[i]]
        self.window.destroy()
        self.parent_app.compile_pdf(filtered_slides)


if __name__ == "__main__":
    root = tk.Tk()
    app = HandoutGeneratorApp(root)
    root.mainloop()