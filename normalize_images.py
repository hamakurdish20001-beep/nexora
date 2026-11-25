import os
import shutil
import sys

from PIL import Image, ImageChops

Image.MAX_IMAGE_PIXELS = None   # بۆ وێنە زۆر گەورەکان

SIZE = 1000        # قەبارەی کۆتایی: 1000 x 1000 (چوارگۆشە)
FILL = 0.94        # کاڵاکە چەندی کانڤاسەکە پڕ بکاتەوە
THRESH = 12        # چەندە لە سپی جیاواز بێت بە "کاڵا" بژمێردرێت
BASE = os.path.join("static", "images", "products")
BACKUP = "image_backup"
EXTS = (".webp", ".jpg", ".jpeg", ".png")


def prepare_backup(path, backup, use_backup):
    """ئەسڵی وێنەکە پاشەکەوت دەکات. ئەگەر وێنەکە گۆڕدرابێت، ئەسڵی نوێ وەردەگرێت."""
    os.makedirs(os.path.dirname(backup), exist_ok=True)
    if not os.path.exists(backup):
        shutil.copy2(path, backup)
        return
    if use_backup:
        return
    # ئەگەر وێنەکە دوای پرۆسێسکردن دانرابێت، کاتی گۆڕینەکەی جیاوازە
    if abs(os.path.getmtime(path) - os.path.getmtime(backup)) > 2:
        shutil.copy2(path, backup)


def render(src, cover):
    img = Image.open(src)
    img.thumbnail((4000, 4000))
    img = img.convert("RGBA")
    white = Image.new("RGBA", img.size, (255, 255, 255, 255))
    flat = Image.alpha_composite(white, img).convert("RGB")

    if cover:
        # بڕینی ناوەڕاست بۆ چوارگۆشە (بێ دەوروبەری سپی)
        w, h = flat.size
        s = min(w, h)
        left, top = (w - s) // 2, (h - s) // 2
        flat = flat.crop((left, top, left + s, top + s))
        return flat.resize((SIZE, SIZE), Image.LANCZOS), SIZE / s

    # بڕینی بۆشایی سپی
    diff = ImageChops.difference(flat, Image.new("RGB", flat.size, (255, 255, 255)))
    bbox = diff.convert("L").point(lambda p: 255 if p > THRESH else 0).getbbox()
    if bbox:
        flat = flat.crop(bbox)

    scale = min(SIZE * FILL / flat.width, SIZE * FILL / flat.height)
    new = (max(1, round(flat.width * scale)), max(1, round(flat.height * scale)))
    flat = flat.resize(new, Image.LANCZOS)

    canvas = Image.new("RGB", (SIZE, SIZE), (255, 255, 255))
    canvas.paste(flat, ((SIZE - new[0]) // 2, (SIZE - new[1]) // 2))
    return canvas, scale


def process_folder(folder, cover, use_backup):
    src_dir = os.path.join(BASE, folder)
    for name in sorted(os.listdir(src_dir)):
        if not name.lower().endswith(EXTS):
            continue
        path = os.path.join(src_dir, name)
        backup = os.path.join(BACKUP, folder, name)
        try:
            prepare_backup(path, backup, use_backup)
            out, scale = render(backup, cover)

            ext = os.path.splitext(name)[1].lower()
            if ext == ".webp":
                out.save(path, "WEBP", quality=90)
            elif ext in (".jpg", ".jpeg"):
                out.save(path, "JPEG", quality=92)
            else:
                out.save(path, "PNG")

            # کاتی فایلەکە وەک پاشەکەوتەکە دەکەین، بۆ ئەوەی بزانین گۆڕدراوە یان نا
            t = os.path.getmtime(backup)
            os.utime(path, (t, t))

            note = "OK" if scale <= 2.5 else "SMALL - may look blurry"
            print(f"{folder}/{name}: {note}")
        except Exception as e:
            print(f"{folder}/{name}: ERROR - {e}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    cover = "--cover" in sys.argv
    use_backup = "--use-backup" in sys.argv

    if not args:
        print("python normalize_images.py all")
        print("python normalize_images.py chairs")
        print("python normalize_images.py led-lights --cover")
        return

    if args[0] == "all":
        folders = sorted(d for d in os.listdir(BASE) if os.path.isdir(os.path.join(BASE, d)))
    else:
        folders = [args[0]]

    for f in folders:
        if not os.path.isdir(os.path.join(BASE, f)):
            print("folder not found:", f)
            continue
        process_folder(f, cover, use_backup)


if __name__ == "__main__":
    main()