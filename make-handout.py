import pymupdf  # Replaced deprecated fitz import
from PIL import Image, ImageDraw, ImageFont, ImageTk
import math
import os
import sys
import platform
import subprocess
from tkinter import filedialog

# Try importing tkinter for the GUI human filter
try:
    import tkinter as tk
    from tkinter import messagebox
    HAS_TKINTER = True
except ImportError:
    HAS_TKINTER = False


def create_preview_image(cols, rows, landscape):
    """Generates a mockup layout preview image to be displayed inside the GUI."""
    if cols < 1: cols = 1
    if rows < 1: rows = 1
    
    A4_W, A4_H = (3508, 2480) if landscape else (2480, 3508)
    MARGIN_X, MARGIN_TOP, MARGIN_BOTTOM = 30, 40, 70
    PADDING_X, PADDING_Y = 15, 15

    canvas = Image.new('RGB', (A4_W, A4_H), 'white')
    draw = ImageDraw.Draw(canvas)

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

    return canvas

def run_config_gui():
    """Tkinter GUI for configuration with side-by-side dynamic preview."""
    if not HAS_TKINTER:
        print("[Error] Tkinter not available. Please install it to use the GUI.")
        sys.exit(1)

    config = {}
    root = tk.Tk()
    root.title("Handout Generator Configuration")
    root.geometry("900x550")

    # Variables
    input_var = tk.StringVar(value="./input")
    output_var = tk.StringVar(value="./handouts_output")
    filename_var = tk.StringVar(value="Interactive_Handout.pdf")
    cols_var = tk.IntVar(value=4)
    rows_var = tk.IntVar(value=3)
    landscape_var = tk.BooleanVar(value=True)
    human_filter_var = tk.BooleanVar(value=False)

    # Layout Frames
    left_frame = tk.Frame(root, padx=20, pady=20)
    left_frame.pack(side="left", fill="both", expand=True)

    right_frame = tk.Frame(root, padx=20, pady=20, bg="#e8eaed")
    right_frame.pack(side="right", fill="both", expand=True)

    # Dynamic Preview Updater
    preview_lbl = tk.Label(right_frame, bg="#e8eaed")
    preview_lbl.pack(expand=True)

    def update_preview(*args):
        try:
            c, r = cols_var.get(), rows_var.get()
        except tk.TclError:
            return  # Handle empty spinbox during typing
        
        img = create_preview_image(c, r, landscape_var.get())
        img.thumbnail((450, 450))
        tk_img = ImageTk.PhotoImage(img)
        preview_lbl.config(image=tk_img)
        preview_lbl.image = tk_img

    cols_var.trace_add("write", update_preview)
    rows_var.trace_add("write", update_preview)
    landscape_var.trace_add("write", update_preview)

    # UI Controls
    tk.Label(left_frame, text="Input Directory:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", pady=5)
    tk.Entry(left_frame, textvariable=input_var, width=30).grid(row=0, column=1, pady=5)
    tk.Button(left_frame, text="Browse", command=lambda: input_var.set(filedialog.askdirectory() or input_var.get())).grid(row=0, column=2, padx=5)

    tk.Label(left_frame, text="Output Directory:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w", pady=5)
    tk.Entry(left_frame, textvariable=output_var, width=30).grid(row=1, column=1, pady=5)
    tk.Button(left_frame, text="Browse", command=lambda: output_var.set(filedialog.askdirectory() or output_var.get())).grid(row=1, column=2, padx=5)

    tk.Label(left_frame, text="Output Filename:", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky="w", pady=5)
    tk.Entry(left_frame, textvariable=filename_var, width=30).grid(row=2, column=1, pady=5)

    tk.Label(left_frame, text="Columns:", font=("Arial", 10, "bold")).grid(row=3, column=0, sticky="w", pady=5)
    tk.Spinbox(left_frame, from_=1, to=10, textvariable=cols_var, width=5).grid(row=3, column=1, sticky="w", pady=5)

    tk.Label(left_frame, text="Rows:", font=("Arial", 10, "bold")).grid(row=4, column=0, sticky="w", pady=5)
    tk.Spinbox(left_frame, from_=1, to=10, textvariable=rows_var, width=5).grid(row=4, column=1, sticky="w", pady=5)

    tk.Checkbutton(left_frame, text="Landscape Mode", variable=landscape_var, font=("Arial", 10, "bold")).grid(row=5, column=0, columnspan=2, sticky="w", pady=10)
    tk.Checkbutton(left_frame, text="Enable Human Filter (Manual Review)", variable=human_filter_var, font=("Arial", 10, "bold")).grid(row=6, column=0, columnspan=2, sticky="w", pady=5)

    def submit():
        config.update({
            "input_dir": input_var.get(),
            "output_dir": output_var.get(),
            "output_name": filename_var.get(),
            "cols": cols_var.get(),
            "rows": rows_var.get(),
            "landscape": landscape_var.get(),
            "preview_grid": False, # Handled internally by GUI now
            "human_filter": human_filter_var.get()
        })
        root.destroy()

    tk.Button(left_frame, text="Generate Handout", command=submit, bg="#4CAF50", fg="white", font=("Arial", 12, "bold"), width=20).grid(row=7, column=0, columnspan=3, pady=30)

    update_preview() # Initial draw
    root.mainloop()

    if not config:
        print("Configuration cancelled by user.")
        sys.exit(0)
    return config


def apply_human_filter_gui(all_slides):
    """Tkinter-based GUI to let users manually include/exclude slides."""
    if not HAS_TKINTER:
        print("[Warning] Tkinter not available. Falling back to terminal filter.")
        return apply_human_filter_terminal(all_slides)

    filtered_slides = []
    current_idx = 0

    root = tk.Tk()
    root.title("Slide Reviewer - Human Filter")
    root.geometry("800x650")

    label_title = tk.Label(root, text="", font=("Arial", 14, "bold"))
    label_title.pack(pady=10)

    # Fixed: Changed px/py to padx/pady
    img_label = tk.Label(root)
    img_label.pack(expand=True, fill="both", padx=10, pady=10)

    status_lbl = tk.Label(root, text="", font=("Arial", 10))
    status_lbl.pack(pady=5)

    def update_view():
        nonlocal current_idx
        if current_idx >= len(all_slides):
            root.destroy()
            return

        img, file_name, slide_num, title = all_slides[current_idx]
        
        title_text = f"File: {file_name} | Slide {slide_num}"
        if title:
            title_text += f" (Start of presentation: '{title}')"
        label_title.config(text=title_text)

        display_img = img.copy()
        display_img.thumbnail((750, 450))
        tk_img = ImageTk.PhotoImage(display_img)
        img_label.config(image=tk_img)
        img_label.image = tk_img  

        status_lbl.config(text=f"Progress: Slide {current_idx + 1} of {len(all_slides)}")

    def keep_slide():
        nonlocal current_idx
        filtered_slides.append(all_slides[current_idx])
        current_idx += 1
        update_view()

    def discard_slide():
        nonlocal current_idx
        current_idx += 1
        update_view()

    def keep_all_remaining():
        nonlocal current_idx
        filtered_slides.extend(all_slides[current_idx:])
        root.destroy()

    btn_frame = tk.Frame(root)
    btn_frame.pack(side="bottom", fill="x", pady=15)

    btn_keep = tk.Button(btn_frame, text="✔ Keep Slide (K)", bg="#4CAF50", fg="white", font=("Arial", 11, "bold"), width=15, command=keep_slide)
    btn_keep.pack(side="left", padx=20, expand=True)

    btn_discard = tk.Button(btn_frame, text="✖ Discard Slide (D)", bg="#f44336", fg="white", font=("Arial", 11, "bold"), width=15, command=discard_slide)
    btn_discard.pack(side="left", padx=20, expand=True)

    btn_all = tk.Button(btn_frame, text="⏩ Keep All Remaining", bg="#2196F3", fg="white", font=("Arial", 11, "bold"), width=20, command=keep_all_remaining)
    btn_all.pack(side="right", padx=20, expand=True)

    root.bind("k", lambda e: keep_slide())
    root.bind("d", lambda e: discard_slide())
    root.bind("a", lambda e: keep_all_remaining())

    update_view()
    root.mainloop()

    print(f"[Human Filter] Filtered out {len(all_slides) - len(filtered_slides)} slides. Kept {len(filtered_slides)} slides.")
    return filtered_slides


def apply_human_filter_terminal(all_slides):
    """Terminal fallback for slide filtering."""
    filtered_slides = []
    print("\n--- Terminal Human Filter ---")
    print("Press 'y' to keep, 'n' to discard, 'all' to keep all remaining.")

    for idx, item in enumerate(all_slides):
        img, file_name, slide_num, title = item
        img.show(title=f"{file_name} - Slide {slide_num}")

        choice = input(f"[{idx + 1}/{len(all_slides)}] Keep {file_name} Slide {slide_num}? (y/n/all) [y]: ").strip().lower()
        if choice == 'all':
            filtered_slides.extend(all_slides[idx:])
            break
        elif choice in ['', 'y', 'yes']:
            filtered_slides.append(item)

    return filtered_slides


def generate_handout_pdf(config):
    """Main execution pipeline."""
    input_dir = config["input_dir"]
    output_dir = config["output_dir"]
    output_name = config["output_name"]
    cols = config["cols"]
    rows = config["rows"]
    landscape = config["landscape"]

    if not os.path.exists(input_dir):
        print(f"Error: Input directory '{input_dir}' does not exist.")
        return

    pdf_files = sorted([f for f in os.listdir(input_dir) if f.lower().endswith('.pdf')])
    if not pdf_files:
        print(f"No PDF files found in '{input_dir}'.")
        return

    print(f"\nExtracting slides from {len(pdf_files)} PDF file(s)...")
    raw_slides = []

    for pdf_file in pdf_files:
        file_path = os.path.join(input_dir, pdf_file)
        doc = pymupdf.open(file_path)  # Updated to use pymupdf

        for slide_idx in range(len(doc)):
            page = doc.load_page(slide_idx)
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            title = pdf_file.replace('.pdf', '') if slide_idx == 0 else ""
            raw_slides.append((img, pdf_file, slide_idx + 1, title))

    if config["human_filter"]:
        slides_to_process = apply_human_filter_gui(raw_slides)
    else:
        slides_to_process = raw_slides

    if not slides_to_process:
        print("No slides left to process. Exiting.")
        return

    A4_W, A4_H = (3508, 2480) if landscape else (2480, 3508)
    MARGIN_X, MARGIN_TOP, MARGIN_BOTTOM = 30, 40, 70
    PADDING_X, PADDING_Y = 15, 15

    try:
        font = ImageFont.truetype("arial.ttf", 45)
        page_font = ImageFont.truetype("arial.ttf", 40)
    except IOError:
        font = ImageFont.load_default()
        page_font = font

    total_slides = len(slides_to_process)
    slides_per_page = cols * rows
    total_pages = math.ceil(total_slides / slides_per_page)

    slot_w = (A4_W - (2 * MARGIN_X) - (cols - 1) * PADDING_X) // cols
    slot_h = (A4_H - MARGIN_TOP - MARGIN_BOTTOM - (rows - 1) * PADDING_Y) // rows

    out_images = []

    print(f"Compiling {total_slides} slides into {total_pages} page(s)...")
    for p in range(total_pages):
        canvas = Image.new('RGB', (A4_W, A4_H), 'white')
        draw = ImageDraw.Draw(canvas)

        for i in range(slides_per_page):
            global_idx = p * slides_per_page + i
            if global_idx >= total_slides:
                break

            img, _, _, title = slides_to_process[global_idx]
            img.thumbnail((slot_w, slot_h))

            r = i // cols
            c = i % cols

            x = MARGIN_X + c * (slot_w + PADDING_X)
            y = MARGIN_TOP + r * (slot_h + PADDING_Y)

            x_offset = x + (slot_w - img.width) // 2

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
                y_offset = y + (slot_h - img.height) // 2

            canvas.paste(img, (x_offset, y_offset))

        page_text = f"- {p + 1} -"
        try:
            bbox = draw.textbbox((0, 0), page_text, font=page_font)
            text_w = bbox[2] - bbox[0]
        except AttributeError:
            text_w = draw.textsize(page_text, font=page_font)[0]

        draw.text(((A4_W - text_w) // 2, A4_H - 50), page_text, fill="black", font=page_font)
        out_images.append(canvas)

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, output_name)

    if out_images:
        out_images[0].save(
            output_path,
            save_all=True,
            append_images=out_images[1:]
        )
        print(f"\n Output saved to: {output_path}")

        abs_output_dir = os.path.abspath(output_dir)
        try:
            if platform.system() == "Windows":
                os.startfile(abs_output_dir)
            elif platform.system() == "Darwin":
                subprocess.call(["open", abs_output_dir])
            else:
                subprocess.call(["xdg-open", abs_output_dir])
        except Exception as e:
            print(f"Could not open output folder automatically: {e}")


if __name__ == "__main__":
    user_config = run_config_gui()
    generate_handout_pdf(user_config)