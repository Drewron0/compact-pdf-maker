import os
import math
from typing import List, Dict, Any, Tuple
import pymupdf
from PIL import Image, ImageDraw, ImageFont


_EXTRACT_DPI = 110


def load_slides_from_files(pdf_paths: List[str]) -> List[Dict[str, Any]]:
    """
    Extracts pages as PIL Images from the provided PDF file paths.
    Returns a list of slide dicts: {'img', 'file_name', 'slide_num', 'kept'}
    """
    raw_slides = []
    for file_path in pdf_paths:
        if not os.path.exists(file_path):
            continue
        file_name = os.path.basename(file_path)
        doc = pymupdf.open(file_path)
        try:
            for slide_idx in range(len(doc)):
                page = doc.load_page(slide_idx)
                pix = page.get_pixmap(dpi=_EXTRACT_DPI)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                raw_slides.append({
                    "img": img,
                    "file_name": file_name,
                    "slide_num": slide_idx + 1,
                    "kept": True
                })
        finally:
            doc.close()
    return raw_slides


def generate_layout_preview(cols: int, rows: int, landscape: bool, max_size: Tuple[int, int] = (600, 600)) -> Image.Image:
    """
    Generates a visual diagram representing the handout layout grid.
    """
    cols = max(1, cols)
    rows = max(1, rows)
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
                slide_y, slide_h = y + 80, slot_h - 80
            else:
                slide_y, slide_h = y + 10, slot_h - 20

            draw.rectangle(
                [x + 10, slide_y, x + slot_w - 10, slide_y + slide_h],
                outline="#80868b", width=2, fill="#e8eaed"
            )
            label = f"Slide ({r+1},{c+1})"
            try:
                bbox = draw.textbbox((0, 0), label, font=sub_font)
                txt_w = bbox[2] - bbox[0]
            except AttributeError:
                txt_w = draw.textsize(label, font=sub_font)[0]
            draw.text(
                (x + (slot_w - txt_w) // 2, slide_y + (slide_h // 2) - 20),
                label, fill="#3c4043", font=sub_font
            )

    page_lbl = "- Page 1 -"
    try:
        bbox = draw.textbbox((0, 0), page_lbl, font=font)
        txt_w = bbox[2] - bbox[0]
    except AttributeError:
        txt_w = draw.textsize(page_lbl, font=font)[0]
    draw.text(((A4_W - txt_w) // 2, A4_H - 60), page_lbl, fill="black", font=font)

    canvas.thumbnail(max_size, Image.Resampling.LANCZOS)
    return canvas


def compile_handout_pdf(
    slides: List[Dict[str, Any]],
    output_path: str,
    cols: int,
    rows: int,
    landscape: bool
) -> int:
    """
    Compiles the kept slides into a printable grid PDF.
    Returns total pages generated (0 if nothing to compile).
    """
    final_slides = []
    seen_pdfs: set = set()
    for slide in slides:
        if slide.get('kept', True):
            fname = slide["file_name"]
            title = os.path.splitext(fname)[0] if fname not in seen_pdfs else ""
            seen_pdfs.add(fname)
            final_slides.append({"img": slide["img"], "title": title})

    if not final_slides:
        return 0

    cols = max(1, cols)
    rows = max(1, rows)
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
            display_img = slide["img"].copy()
            display_img.thumbnail((slot_w, slot_h), Image.Resampling.LANCZOS)

            r, c = i // cols, i % cols
            x = MARGIN_X + c * (slot_w + PADDING_X)
            y = MARGIN_TOP + r * (slot_h + PADDING_Y)
            x_offset = x + (slot_w - display_img.width) // 2

            if slide["title"]:
                try:
                    bbox = draw.textbbox((0, 0), slide["title"], font=font)
                    text_w = bbox[2] - bbox[0]
                except AttributeError:
                    text_w = draw.textsize(slide["title"], font=font)[0]
                draw.text((x + (slot_w - text_w) // 2, y), slide["title"], fill="darkblue", font=font)
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

    out_dir = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(out_dir, exist_ok=True)

    if out_images:
        out_images[0].save(
            output_path,
            save_all=True,
            append_images=out_images[1:],
            resolution=150.0,
            quality=82,
            optimize=True,
        )

    return total_pages
