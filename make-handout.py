import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont
import math
import os

def process_maximized_handout(input_dir, output_dir, output_name, cols=4, rows=3, landscape=True):
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, output_name)

    pdf_files = sorted([f for f in os.listdir(input_dir) if f.lower().endswith('.pdf')])
    
    if not pdf_files:
        print(f"No PDF files found in '{input_dir}'.")
        return

    # Canvas dimensions for 300 DPI
    if landscape:
        A4_WIDTH, A4_HEIGHT = 3508, 2480
    else:
        A4_WIDTH, A4_HEIGHT = 2480, 3508
    
    # Ultra-tight spacing to maximize image size
    MARGIN_X = 30
    MARGIN_TOP = 40
    MARGIN_BOTTOM = 70  # Slightly larger to accommodate page numbers
    PADDING_X = 15
    PADDING_Y = 15      # Minimal space between rows

    try:
        font = ImageFont.truetype("arial.ttf", 45)
        page_font = ImageFont.truetype("arial.ttf", 40)
    except IOError:
        font = ImageFont.load_default()
        page_font = font

    all_slides = []

    # 1. Extract slides and flag the start of each file with its title
    for pdf_file in pdf_files:
        file_path = os.path.join(input_dir, pdf_file)
        doc = fitz.open(file_path)

        for slide_idx in range(len(doc)):
            page = doc.load_page(slide_idx)
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            title = pdf_file.replace('.pdf', '') if slide_idx == 0 else ""
            all_slides.append((img, title))

    total_slides = len(all_slides)
    slides_per_page = cols * rows
    total_pages = math.ceil(total_slides / slides_per_page)

    out_images = []

    # Calculate absolute maximum slot dimensions
    slot_w = (A4_WIDTH - (2 * MARGIN_X) - (cols - 1) * PADDING_X) // cols
    slot_h = (A4_HEIGHT - MARGIN_TOP - MARGIN_BOTTOM - (rows - 1) * PADDING_Y) // rows

    # 2. Render slides into grid
    for p in range(total_pages):
        canvas = Image.new('RGB', (A4_WIDTH, A4_HEIGHT), 'white')
        draw = ImageDraw.Draw(canvas)

        for i in range(slides_per_page):
            global_idx = p * slides_per_page + i
            if global_idx >= total_slides:
                break

            img, title = all_slides[global_idx]

            # Scale slide to the absolute limits of the slot (no artificial subtraction)
            img.thumbnail((slot_w, slot_h))

            row = i // cols
            col = i % cols

            x = MARGIN_X + col * (slot_w + PADDING_X)
            y = MARGIN_TOP + row * (slot_h + PADDING_Y)

            x_offset = x + (slot_w - img.width) // 2
            
            # If it's a title slide, pin the image to the bottom of the slot and draw text above
            if title:
                try:
                    bbox = draw.textbbox((0, 0), title, font=font)
                    text_w = bbox[2] - bbox[0]
                except AttributeError:
                    text_w = draw.textsize(title, font=font)[0]
                
                text_x = x + (slot_w - text_w) // 2
                draw.text((text_x, y), title, fill="darkblue", font=font)
                
                # Shift image down slightly to clear the title text
                y_offset = y + 55
            else:
                # Vertically center normal slides within the slot
                y_offset = y + (slot_h - img.height) // 2

            canvas.paste(img, (x_offset, y_offset))

        # 3. Add page numbers at the bottom center
        page_text = f"- {p + 1} -"
        try:
            bbox = draw.textbbox((0, 0), page_text, font=page_font)
            text_w = bbox[2] - bbox[0]
        except AttributeError:
            text_w = draw.textsize(page_text, font=page_font)[0]
            
        draw.text(((A4_WIDTH - text_w) // 2, A4_HEIGHT - 50), page_text, fill="black", font=page_font)

        out_images.append(canvas)

    # 4. Export consolidated document
    if out_images:
        out_images[0].save(
            output_path,
            save_all=True,
            append_images=out_images[1:]
        )
        print(f"Success! Processed {total_slides} slides into {total_pages} page(s). Saved to: {output_path}")


# Configuration Setup
INPUT_DIRECTORY = "./input"
OUTPUT_DIRECTORY = "./handouts_output"
OUTPUT_NAME = "Maximized_Course_Handout_Landscape.pdf"

process_maximized_handout(
    input_dir=INPUT_DIRECTORY,
    output_dir=OUTPUT_DIRECTORY,
    output_name=OUTPUT_NAME,
    cols=4,         
    rows=5,         
    landscape=True  
)