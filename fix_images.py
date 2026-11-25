import os
import shutil
import sys

from PIL import Image, ImageChops

CANVAS_W, CANVAS_H = 800, 600   # قەبارەی کۆتایی (٤:٣)
FILL = 0.88                     # کاڵاکە ٨٨٪ی کانڤاسەکە پڕ دەکاتەوە
THRESH = 12                     # چەندە لە سپی جیاواز بێت بە "کاڵا" بژمێردرێت

BASE = os.path.join("static", "images", "products")
BACKUP = "image_backup"


def fix_one(path, backup_path):
    os.makedirs(os.path.dirname(backup_path), exist_ok=True)
    if not os.path.exists(backup_path):
        shutil.copy2(path, backup_path)

    img = Image.open(backup_path).convert("RGBA")
    white = Image.new("RGBA", img.size, (255, 255, 255, 255))
    flat = Image.alpha_composite(white, img).convert("RGB")

    diff = ImageChops.difference(flat, Image.new("RGB", flat.size, (255, 255, 255)))
    bbox = diff.convert("L").point(lambda p: 255 if p > THRESH else 0).getbbox()
    if not bbox:
        return "بەتاڵ (بەبێ گۆڕین)"

    cropped = flat.crop(bbox)
    scale = min(CANVAS_W * FILL / cropped.width, CANVAS_H * FILL / cropped.height)
    size = (max(1, int(cropped.width * scale)), max(1, int(cropped.height * scale)))
    cropped = cropped.resize(size, Image.LANCZOS)

    canvas = Image.new("RGB", (CANVAS_W, CANVAS_H), (255, 255, 255))
    canvas.paste(cropped, ((CANVAS_W - size[0]) // 2, (CANVAS_H - size[1]) // 2))

    ext = os.path.splitext(path)[1].lower()
    if ext == ".webp":
        canvas.save(path, "WEBP", quality=90)
    elif ext in (".jpg", ".jpeg"):
        canvas.save(path, "JPEG", quality=92)
    else:
        canvas.save(path, "PNG")

    return "ئاگاداری: وێنەکە بچووکە و لەوانەیە تەلخ بێت" if scale > 2.5 else "باشە"


def main():
    if len(sys.argv) < 2:
        print("بەکارهێنان: python fix_images.py chairs")
        return
    folder = sys.argv[1]
    src_dir = os.path.join(BASE, folder)
    if not os.path.isdir(src_dir):
        print("فۆڵدەرەکە نەدۆزرایەوە:", src_dir)
        return

    for name in sorted(os.listdir(src_dir)):
        if not name.lower().endswith((".webp", ".jpg", ".jpeg", ".png")):
            continue
        path = os.path.join(src_dir, name)
        backup_path = os.path.join(BACKUP, folder, name)
        try:
            print(f"{name}: {fix_one(path, backup_path)}")
        except Exception as e:
            print(f"{name}: هەڵە - {e}")


if __name__ == "__main__":
    main()