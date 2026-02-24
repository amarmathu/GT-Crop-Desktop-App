from PIL import Image, ImageFile, ImageDraw
import os

ImageFile.LOAD_TRUNCATED_IMAGES = True

# Constants
dpi = 300
margin_inch = 0.5

# Paper sizes available for printing (width, height) in inches
available_papers = [
    (10, 16),
    (12, 16),
    (13, 19),
    (9.5, 13)
]

# Approved sheet sizes (any orientation) in inches
approved_sheets = {
    (8, 24),
    (9, 24),
    (10, 15),
    (10, 24),
    (10, 30),
    (12, 15),
    (12, 16),
    (12, 18),
    (12, 17),
    (12, 24),
    (12, 30),
    (12, 36),
    (14, 24),
    (15, 24),
    (16, 24),
    (17, 24),
    (18, 24)
}

def normalize_size(w_in, h_in):
    w = round(w_in, 2)
    h = round(h_in, 2)
    return tuple(sorted((w, h)))

def is_valid_sheet(w_in, h_in):
    detected = normalize_size(w_in, h_in)
    approved_normalized = {tuple(sorted((round(w,2), round(h,2)))) for w, h in approved_sheets}
    return detected in approved_normalized

def find_best_paper_for_half_sheet(half_w_in, half_h_in, papers):
    candidates = []
    for pw, ph in papers:
        if pw >= half_w_in and ph >= half_h_in:
            candidates.append((pw, ph, False))
        if ph >= half_w_in and pw >= half_h_in:
            candidates.append((ph, pw, True))
    if not candidates:
        pw, ph = max(papers, key=lambda x: x[0] * x[1])
        return (pw, ph), False
    best = min(candidates, key=lambda x: x[0] * x[1])
    return (best[0], best[1]), best[2]

def process_sheet(image_path, output_folder):
    try:
        img = Image.open(image_path).convert("RGB")
    except Exception as e:
        return False, f"Cannot open: {e}"

    w_px, h_px = img.size
    w_in = w_px / dpi
    h_in = h_px / dpi

    if not is_valid_sheet(w_in, h_in):
        return False, f"Invalid size: {w_in:.2f}×{h_in:.2f} (not in approved list)"

    if w_in > h_in:
        split_vertical = True
        half_w_in = w_in / 2
        half_h_in = h_in
        if w_px % 2 != 0:
            w_px -= 1
            img = img.crop((0, 0, w_px, h_px))
        mid = w_px // 2
        half1 = img.crop((0, 0, mid, h_px))
        half2 = img.crop((mid, 0, w_px, h_px))
    else:
        split_vertical = False
        half_w_in = w_in
        half_h_in = h_in / 2
        if h_px % 2 != 0:
            h_px -= 1
            img = img.crop((0, 0, w_px, h_px))
        mid = h_px // 2
        half1 = img.crop((0, 0, w_px, mid))
        half2 = img.crop((0, mid, w_px, h_px))

    # >>>>>>>>>>>> NEW LOGIC: Force 13x19 for 14x24, 15x24, 16x24 <<<<<<<<<<<<
    original_norm = normalize_size(w_in, h_in)
    large_sheets_for_13x19 = {(14.0, 24.0), (15.0, 24.0), (16.0, 24.0)}

    if original_norm in large_sheets_for_13x19:
        paper_w, paper_h = 13, 19
    else:
        (paper_w, paper_h), _ = find_best_paper_for_half_sheet(half_w_in, half_h_in, available_papers)
    # >>>>>>>>>>>> END NEW LOGIC <<<<<<<<<<<<

    target_w_px = int(paper_w * dpi)
    target_h_px = int(paper_h * dpi)
    margin_px = int(margin_inch * dpi)
    printable_w_px = target_w_px - 2 * margin_px
    printable_h_px = target_h_px

    def resize_to_fit(im, max_w, max_h):
        im_w, im_h = im.size
        if im_w == 0 or im_h == 0:
            return im
        scale = min(max_w / im_w, max_h / im_h)
        return im.resize((int(im_w * scale), int(im_h * scale)), Image.Resampling.LANCZOS)

    half1_resized = resize_to_fit(half1, printable_w_px, printable_h_px)
    half2_resized = resize_to_fit(half2, printable_w_px, printable_h_px)

    def paste_centered(bg, im):
        bg_w, bg_h = bg.size
        im_w, im_h = im.size
        x = (bg_w - im_w) // 2
        y = (bg_h - im_h) // 2
        bg.paste(im, (x, y))

    canvas1 = Image.new("RGB", (target_w_px, target_h_px), (255, 255, 255))
    canvas2 = Image.new("RGB", (target_w_px, target_h_px), (255, 255, 255))
    paste_centered(canvas1, half1_resized)
    paste_centered(canvas2, half2_resized)

    base_name = os.path.splitext(os.path.basename(image_path))[0]
    save_kwargs = {"quality": 98, "optimize": True, "subsampling": 0}
    canvas1.save(os.path.join(output_folder, f"{base_name}_page1.jpg"), **save_kwargs)
    canvas2.save(os.path.join(output_folder, f"{base_name}_page2.jpg"), **save_kwargs)

    return True, f"✅ Success: {paper_w}×{paper_h}\" pages"

def crop_and_mark_sheet(image_path, output_folder):
    """For 12x24 or 10x24 sheets: split vertically, place each half on 12x16 or 10x16 canvas with red margin lines."""
    try:
        img = Image.open(image_path).convert("RGB")
    except Exception as e:
        return False, f"Cannot open: {e}"

    w_px, h_px = img.size
    w_in = w_px / dpi
    h_in = h_px / dpi

    # Accept any orientation of 12x24 or 10x24
    if not (
        (abs(w_in - 12) < 0.1 and abs(h_in - 24) < 0.1) or   # 12x24
        (abs(w_in - 24) < 0.1 and abs(h_in - 12) < 0.1) or   # 24x12
        (abs(w_in - 10) < 0.1 and abs(h_in - 24) < 0.1) or   # 10x24
        (abs(w_in - 24) < 0.1 and abs(h_in - 10) < 0.1)      # 24x10
    ):
        return False, f"Sheet {w_in:.2f}×{h_in:.2f}\" is not 12x24 or 10x24 — skipping."

    # Determine paper size
    if abs(w_in - 12) < 0.1 or abs(h_in - 12) < 0.1:
        paper_w, paper_h = 16, 12
    elif abs(w_in - 10) < 0.1 or abs(h_in - 10) < 0.1:
        paper_w, paper_h = 16, 10
    else:
        return False, f"Cannot determine paper size"

    target_w_px = int(paper_w * dpi)
    target_h_px = int(paper_h * dpi)

    # Split the sheet: always split the LONGER dimension
    if w_in > h_in:
        # Landscape (e.g., 24x12): split width → two 12x12 or 12x10
        if w_px % 2 != 0:
            w_px -= 1
        mid = w_px // 2
        half1 = img.crop((0, 0, mid, h_px))
        half2 = img.crop((mid, 0, w_px, h_px))
    else:
        # Portrait (e.g., 12x24): split height → two 12x12 or 10x12
        if h_px % 2 != 0:
            h_px -= 1
        mid = h_px // 2
        half1 = img.crop((0, 0, w_px, mid))
        half2 = img.crop((0, mid, w_px, h_px))

    results = []
    for i, half in enumerate([half1, half2], 1):
        # Resize to fit within the target canvas (full height, constrained width)
        def resize_to_fit(im, max_w, max_h):
            im_w, im_h = im.size
            scale = min(max_w / im_w, max_h / im_h)
            return im.resize((int(im_w * scale), int(im_h * scale)), Image.Resampling.LANCZOS)

        resized = resize_to_fit(half, target_w_px, target_h_px)

        # Create white canvas
        canvas = Image.new("RGB", (target_w_px, target_h_px), (255, 255, 255))

        # Center image
        x = (target_w_px - resized.width) // 2
        y = (target_h_px - resized.height) // 2
        canvas.paste(resized, (x, y))

        # Draw black margin lines at 1.0" from left/right edges of the image area
        margin_px = int(1.0 * dpi)
        draw = ImageDraw.Draw(canvas)

        left_line_x = x - margin_px 
        right_line_x = x + resized.width + margin_px 

        # Only draw if the image is wide enough to have distinct margins
        if resized.width >= int(1.0 * dpi):  # at least 1" wide
            draw.line([(left_line_x, y), (left_line_x, y + resized.height)], fill="Black", width=2)
            draw.line([(right_line_x, y), (right_line_x, y + resized.height)], fill="Black", width=2)

        # Save
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        save_kwargs = {"quality": 98, "optimize": True, "subsampling": 0}
        output_path = os.path.join(output_folder, f"{base_name}_page{i}.jpg")
        canvas.save(output_path, **save_kwargs)
        results.append(output_path)

    return True, f"✅ Crop & Mark: {results[0]}, {results[1]}"

def rotate_images_in_folder(folder_path):
    """
    Rotates images in a folder:
    - Odd-numbered (1st, 3rd, ...) → 90° left (counter-clockwise)
    - Even-numbered (2nd, 4th, ...) → 90° right (clockwise)
    Overwrites original files.
    Returns (success_count, total_count, errors)
    """
    image_extensions = {'.jpg', '.jpeg', '.png'}
    files = [f for f in os.listdir(folder_path) if any(f.lower().endswith(ext) for ext in image_extensions)]
    files.sort()  # Ensure consistent order (e.g., alphabetical)

    if not files:
        return 0, 0, ["No image files found."]

    success_count = 0
    errors = []

    for idx, filename in enumerate(files):
        file_path = os.path.join(folder_path, filename)
        try:
            with Image.open(file_path) as img:
                # Determine rotation
                if (idx + 1) % 2 == 1:  # Odd position (1-based)
                    rotated = img.transpose(Image.ROTATE_90)   # Counter-clockwise
                else:  # Even position
                    rotated = img.transpose(Image.ROTATE_270)  # Clockwise

                # Preserve format and quality
                save_kwargs = {}
                if img.format == 'JPEG':
                    save_kwargs = {"quality": 98, "optimize": True, "subsampling": 0}
                elif img.format == 'PNG':
                    save_kwargs = {"optimize": True}

                rotated.save(file_path, **save_kwargs)
                success_count += 1

        except Exception as e:
            errors.append(f"{filename}: {str(e)}")

    return success_count, len(files), errors

def convert_to_300dpi(image_path, output_folder):
    try:
        img = Image.open(image_path)
        
        # Get current DPI
        current_dpi = img.info.get('dpi', (72, 72))
        if isinstance(current_dpi, tuple):
            current_dpi = current_dpi[0]
            
        # Calculate physical size in inches
        w_in = img.width / current_dpi
        h_in = img.height / current_dpi
        
        # Calculate new pixel dimensions for 300 DPI
        new_w = int(w_in * 300)
        new_h = int(h_in * 300)
        
        # Resize
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # Save
        filename = os.path.basename(image_path)
        output_path = os.path.join(output_folder, filename)
        
        save_kwargs = {}
        if img.format == 'JPEG':
            save_kwargs = {"quality": 98, "optimize": True, "subsampling": 0, "dpi": (300, 300)}
        elif img.format == 'PNG':
             save_kwargs = {"optimize": True, "dpi": (300, 300)}
        else:
             save_kwargs = {"dpi": (300, 300)}
             
        img.save(output_path, **save_kwargs)
        return True, f"Converted {filename}"
    except Exception as e:
        return False, f"Error converting {os.path.basename(image_path)}: {e}"