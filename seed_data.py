from database import get_db, init_db
from data.categories import CATEGORIES
from data.mouse import MOUSE
from data.laptops import LAPTOPS
from data.monitors import MONITORS
from data.keyboards import KEYBOARDS
from data.mousepads import MOUSEPADS
from data.chairs import CHAIRS
from data.desks import DESKS
from data.headsets import HEADSETS
from data.controllers import CONTROLLERS
from data.microphones import MICROPHONES
from data.webcams import WEBCAMS
from data.led_lights import LED_LIGHTS
from data.figures import FIGURES
from data.handhelds import HANDHELDS
import os
import re

IMG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "static", "images", "products")
ALL_PRODUCTS = {
    "mouse": MOUSE,
    "laptops": LAPTOPS,
    "monitors": MONITORS,
    "keyboards": KEYBOARDS,
    "mousepads": MOUSEPADS,
    "chairs": CHAIRS,
    "desks": DESKS,
    "headsets": HEADSETS,
    "controllers": CONTROLLERS,
    "microphones": MICROPHONES,
    "webcams": WEBCAMS,
    "led-lights": LED_LIGHTS,
    "figures": FIGURES,
    "handhelds": HANDHELDS,
}

def build_images(p):
    """هەموو وێنەکانی کاڵا لە فۆڵدەرەکە دەدۆزێتەوە (-1، -2، -3 ... هەر چەند بن)"""
    if p.get("images"):
        return p["images"]

    folder, filename = os.path.split(p["image"])       # chairs , chair-01-1.webp
    m = re.match(r"^(.*)-1\.(\w+)$", filename)
    if not m:
        return [p["image"]]

    base, ext = m.groups()
    found = []
    path = os.path.join(IMG_DIR, folder)
    if os.path.isdir(path):
        for f in os.listdir(path):
            mm = re.match(rf"^{re.escape(base)}-(\d+)\.{re.escape(ext)}$", f)
            if mm:
                found.append((int(mm.group(1)), f"{folder}/{f}"))

    found.sort()
    return [x[1] for x in found] or [p["image"]]


def seed():
    init_db()
    conn = get_db()
    cur = conn.cursor()

    cur.execute("DELETE FROM product_images")
    cur.execute("DELETE FROM products")
    cur.execute("DELETE FROM brands")
    cur.execute("DELETE FROM categories")

    category_ids = {}
    for c in CATEGORIES:
        cur.execute(
            "INSERT INTO categories (slug, name_ku, name_ar, name_en, has_used) VALUES (?, ?, ?, ?, ?)",
            (c["slug"], c["name_ku"], c["name_ar"], c["name_en"], c["has_used"]),
        )
        category_ids[c["slug"]] = cur.lastrowid

    brand_ids = {}
    count = 0
    for slug, products in ALL_PRODUCTS.items():
        for p in products:
            if p["brand"] not in brand_ids:
                cur.execute("INSERT INTO brands (name) VALUES (?)", (p["brand"],))
                brand_ids[p["brand"]] = cur.lastrowid

            v_json = p.get("variants_json") or (json.dumps(p["variants"], ensure_ascii=False) if p.get("variants") else None)
            cur.execute(
                """INSERT INTO products
                   (category_id, brand_id, name, price, condition, image,
                    specs_en, desc_ku, desc_ar, desc_en, video_id, variants_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    category_ids[slug], brand_ids[p["brand"]], p["name"], p["price"],
                    p["condition"], p["image"], p["specs_en"],
                    p["desc_ku"], p["desc_ar"], p["desc_en"], p.get("video_id"),
                    v_json
                ),
            )
            product_id = cur.lastrowid

            for order, img in enumerate(build_images(p)):
                cur.execute(
                    "INSERT INTO product_images (product_id, image, sort_order) VALUES (?, ?, ?)",
                    (product_id, img, order),
                )
            count += 1

    conn.commit()
    conn.close()
    print(f"✅ {len(CATEGORIES)} هاوپۆل، {len(brand_ids)} بڕاند، {count} کاڵا زیاد کران")


if __name__ == "__main__":
    seed()
