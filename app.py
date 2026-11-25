import os
import json
import math
import time
import datetime
from collections import defaultdict
from datetime import timedelta
from functools import wraps
from flask import Flask, render_template, request, abort, jsonify, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db, init_db
from telegram_bot import send_order
from config import USD_TO_IQD, DELIVERY_FEE_IQD, SECRET_KEY, ITEMS_PER_PAGE

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", SECRET_KEY)
app.config.update(
    SEND_FILE_MAX_AGE_DEFAULT=0,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
)

# ڕاگرتنی هێرشی زۆرلێکردن (Rate Limiting بۆ هاک نەکردن)
LOGIN_ATTEMPTS = defaultdict(list)
ORDER_ATTEMPTS = defaultdict(list)

def is_rate_limited(ip, storage, max_attempts=5, window_seconds=300):
    now = time.time()
    storage[ip] = [t for t in storage[ip] if now - t < window_seconds]
    return len(storage[ip]) >= max_attempts

def record_attempt(ip, storage):
    storage[ip].append(time.time())

@app.after_request
def set_security_headers(response):
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


def format_iqd(usd):
    """دۆلار یان دینار بە ڕێکی فۆرمات دەکات:
    ئەگەر نرخەکە بە دۆلار بێت (کەمتر لە ١٠،٠٠٠)، دەیگۆڕێت بۆ دینار: 159 -> 242,000 IQD
    ئەگەر لە پێشتردا بە دینار بێت (١٠،٠٠٠ یان زیاتر)، ڕاستەوخۆ فۆرماتی دەکات بەبێ ئەوەی لە ١٥٢٠ بداتەوە
    """
    try:
        val = float(usd)
        if val >= 10000:
            iqd = round(val, -3)
        else:
            iqd = round(val * USD_TO_IQD, -3)
        return f"{int(iqd):,} IQD"
    except (ValueError, TypeError):
        return "0 IQD"


def format_iqd_direct(iqd_val):
    """تەنها بۆ فۆرماتکردنی ئەو ژمارانەی لە پێشتردا بە دینارن: 1,307,000 IQD"""
    try:
        iqd = round(float(iqd_val), -3)
        return f"{int(iqd):,} IQD"
    except (ValueError, TypeError):
        return "0 IQD"


def to_iqd_num(usd):
    """نرخی دۆلار دەکاتە ژمارەی دینار"""
    try:
        return int(round(float(usd) * USD_TO_IQD, -3))
    except (ValueError, TypeError):
        return 0


@app.template_filter("iqd")
def iqd_filter(usd):
    return format_iqd(usd)


@app.template_filter("iqd_fmt")
def iqd_fmt_filter(iqd_val):
    return format_iqd_direct(iqd_val)


@app.template_filter("iqd_num")
def iqd_num_filter(usd):
    return to_iqd_num(usd)


@app.template_filter("from_json")
def from_json_filter(val):
    if not val:
        return []
    try:
        return json.loads(val)
    except Exception:
        return []


ICONS = {
    "laptops": "💻", "monitors": "🖥️", "mouse": "🖱️", "keyboards": "⌨️",
    "mousepads": "🟪", "chairs": "💺", "desks": "🪑", "headsets": "🎧",
    "controllers": "🎮", "microphones": "🎙️", "webcams": "📷",
    "led-lights": "💡", "figures": "🗿", "handhelds": "🕹️",
}


@app.context_processor
def inject_globals():
    """زانیاری گشتی بە هەموو تێمپلەیتەکان دەدات"""
    conn = get_db()
    cats = conn.execute("SELECT * FROM categories ORDER BY id").fetchall()
    brands = conn.execute("SELECT * FROM brands ORDER BY name").fetchall()
    conn.close()
    return {
        "all_categories": cats,
        "all_brands": brands,
        "category_icons": ICONS,
        "delivery_fee_iqd": DELIVERY_FEE_IQD,
        "usd_to_iqd": USD_TO_IQD,
        "is_admin": "admin_id" in session,
        "admin_username": session.get("admin_user", ""),
    }


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "admin_id" not in session:
            return redirect(url_for("admin_login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function


# ==========================================
# ڕووتە سەرەکییەکان (Public Routes)
# ==========================================

@app.route("/")
def home():
    conn = get_db()
    categories = conn.execute("SELECT * FROM categories ORDER BY id").fetchall()

    # نوێترین کاڵاکان بۆ شریتی جووڵاوی Marquee (تەنها بەرهەمی بێ داشکاندن بە نرخی بنەڕەتی)
    recent_products = conn.execute(
        """SELECT p.*, b.name AS brand_name
           FROM products p JOIN brands b ON p.brand_id = b.id
           WHERE p.discount_percent = 0
           ORDER BY p.id DESC LIMIT 12"""
    ).fetchall()

    # بەرهەمە داشکێنراوەکان (Discounted Products)
    discounted_raw = conn.execute(
        """SELECT p.*, b.name AS brand_name, c.slug AS cat_slug
           FROM products p
           JOIN brands b ON p.brand_id = b.id
           JOIN categories c ON p.category_id = c.id
           WHERE p.discount_percent > 0
           ORDER BY p.discount_percent DESC, p.id DESC"""
    ).fetchall()
    discounted_products = []
    for p in discounted_raw:
        d = dict(p)
        pct = d.get("discount_percent", 0)
        d["discount_price"] = round(d["price"] * (1 - pct / 100.0), 2)
        discounted_products.append(d)

    # کاڵا تایبەتەکان
    featured = conn.execute(
        """SELECT p.*, b.name AS brand_name
           FROM products p JOIN brands b ON p.brand_id = b.id
           ORDER BY p.id LIMIT 8"""
    ).fetchall()

    # کاڵاکان بۆ هەر هاوپۆلێک (بۆ بەشە ئاسۆییەکانی خوارەوە تا هاندهێڵد)
    category_sections = []
    for c in categories:
        prods = conn.execute(
            """SELECT p.*, b.name AS brand_name
               FROM products p JOIN brands b ON p.brand_id = b.id
               WHERE p.category_id = ?
               ORDER BY p.id LIMIT 8""",
            (c["id"],)
        ).fetchall()
        if prods:
            category_sections.append({"category": c, "products": prods})

    conn.close()
    return render_template(
        "index.html",
        categories=categories,
        featured=featured,
        recent_products=recent_products,
        discounted_products=discounted_products,
        category_sections=category_sections,
        icons=ICONS,
    )


@app.route("/products")
def all_products():
    """پەڕەی هەموو بەشەکان (فلتەر، گەڕان، ڕیزکردن، پەڕەبەندی)"""
    conn = get_db()

    q = request.args.get("q", "").strip()
    brand = request.args.get("brand", "").strip()
    category_slug = request.args.get("category", "").strip()
    sort = request.args.get("sort", "").strip()
    min_price = request.args.get("min_price", "").strip()
    max_price = request.args.get("max_price", "").strip()

    try:
        page = max(1, int(request.args.get("page", 1)))
    except (ValueError, TypeError):
        page = 1

    query = """
        SELECT p.*, b.name AS brand_name, c.slug AS cat_slug,
               c.name_ku AS cat_ku, c.name_ar AS cat_ar, c.name_en AS cat_en
        FROM products p
        JOIN brands b ON p.brand_id = b.id
        JOIN categories c ON p.category_id = c.id
        WHERE 1=1
    """
    count_query = """
        SELECT COUNT(*)
        FROM products p
        JOIN brands b ON p.brand_id = b.id
        JOIN categories c ON p.category_id = c.id
        WHERE 1=1
    """
    params = []

    if q:
        query += " AND (p.name LIKE ? OR b.name LIKE ? OR c.name_ku LIKE ? OR c.name_en LIKE ? OR p.specs_en LIKE ?)"
        count_query += " AND (p.name LIKE ? OR b.name LIKE ? OR c.name_ku LIKE ? OR c.name_en LIKE ? OR p.specs_en LIKE ?)"
        pattern = f"%{q}%"
        params.extend([pattern, pattern, pattern, pattern, pattern])

    if brand:
        query += " AND b.name = ?"
        count_query += " AND b.name = ?"
        params.append(brand)

    selected_cat = None
    if category_slug:
        query += " AND c.slug = ?"
        count_query += " AND c.slug = ?"
        params.append(category_slug)
        selected_cat = conn.execute("SELECT * FROM categories WHERE slug = ?", (category_slug,)).fetchone()

    # مەودای نرخ (بە دینار داواکراوە: 1000 تا 10,000,000 IQD)
    # لە داتابەیس بە دۆلارە، کەواتە دەیگۆڕینەوە بۆ دۆلار
    if min_price:
        try:
            min_usd = float(min_price) / USD_TO_IQD
            query += " AND p.price >= ?"
            count_query += " AND p.price >= ?"
            params.append(min_usd)
        except (ValueError, ZeroDivisionError):
            pass

    if max_price:
        try:
            max_usd = float(max_price) / USD_TO_IQD
            query += " AND p.price <= ?"
            count_query += " AND p.price <= ?"
            params.append(max_usd)
        except (ValueError, ZeroDivisionError):
            pass

    # ڕیزکردن
    if sort == "price_asc":
        query += " ORDER BY p.price ASC"
    elif sort == "price_desc":
        query += " ORDER BY p.price DESC"
    elif sort == "name_asc":
        query += " ORDER BY p.name ASC"
    elif sort == "name_desc":
        query += " ORDER BY p.name DESC"
    else:
        query += " ORDER BY p.id ASC"

    # کۆی هەموو کاڵا دۆزراوەکان
    total_count = conn.execute(count_query, params).fetchone()[0]
    total_pages = max(1, math.ceil(total_count / ITEMS_PER_PAGE))
    if page > total_pages:
        page = total_pages

    # سنوردارکردن بۆ پەڕە (Pagination)
    offset = (page - 1) * ITEMS_PER_PAGE
    query += " LIMIT ? OFFSET ?"
    query_params = list(params) + [ITEMS_PER_PAGE, offset]

    products = conn.execute(query, query_params).fetchall()
    categories = conn.execute("SELECT * FROM categories ORDER BY id").fetchall()
    brands = conn.execute("SELECT * FROM brands ORDER BY name").fetchall()
    conn.close()

    return render_template(
        "all_products.html",
        products=products,
        categories=categories,
        brands=brands,
        selected_brand=brand,
        selected_category=category_slug,
        selected_cat=selected_cat,
        selected_sort=sort,
        search_query=q,
        min_price=min_price,
        max_price=max_price,
        page=page,
        total_pages=total_pages,
        total_count=total_count,
        icons=ICONS,
    )


@app.route("/category/<slug>")
def category(slug):
    conn = get_db()
    cat = conn.execute("SELECT * FROM categories WHERE slug = ?", (slug,)).fetchone()
    if cat is None:
        conn.close()
        abort(404)

    brand = request.args.get("brand", "")
    condition = request.args.get("condition", "")
    sort = request.args.get("sort", "")

    brands = conn.execute(
        """SELECT DISTINCT b.name FROM brands b
           JOIN products p ON p.brand_id = b.id
           WHERE p.category_id = ? ORDER BY b.name""",
        (cat["id"],),
    ).fetchall()

    query = """SELECT p.*, b.name AS brand_name
               FROM products p JOIN brands b ON p.brand_id = b.id
               WHERE p.category_id = ?"""
    params = [cat["id"]]

    if brand:
        query += " AND b.name = ?"
        params.append(brand)
    if condition in ("new", "used"):
        query += " AND p.condition = ?"
        params.append(condition)

    if sort == "price_asc":
        query += " ORDER BY p.price ASC"
    elif sort == "price_desc":
        query += " ORDER BY p.price DESC"
    elif sort == "name_asc":
        query += " ORDER BY p.name ASC"
    elif sort == "name_desc":
        query += " ORDER BY p.name DESC"
    else:
        query += " ORDER BY p.id"

    products = conn.execute(query, params).fetchall()
    conn.close()

    return render_template(
        "category.html", cat=cat, products=products, brands=brands,
        selected_brand=brand, selected_condition=condition, selected_sort=sort, icons=ICONS,
    )


@app.route("/product/<int:product_id>")
def product(product_id):
    conn = get_db()

    p = conn.execute(
        """SELECT p.*, b.name AS brand_name,
                  c.name_ku AS cat_ku, c.name_ar AS cat_ar, c.name_en AS cat_en,
                  c.slug AS cat_slug
           FROM products p
           JOIN brands b ON p.brand_id = b.id
           JOIN categories c ON p.category_id = c.id
           WHERE p.id = ?""",
        (product_id,),
    ).fetchone()

    if p is None:
        conn.close()
        abort(404)

    images = conn.execute(
        "SELECT image FROM product_images WHERE product_id = ? ORDER BY sort_order",
        (product_id,),
    ).fetchall()

    related = conn.execute(
        """SELECT p.*, b.name AS brand_name
           FROM products p JOIN brands b ON p.brand_id = b.id
           WHERE p.category_id = ? AND p.id != ?
           ORDER BY p.id LIMIT 4""",
        (p["category_id"], product_id),
    ).fetchall()

    other_products = conn.execute(
        """SELECT p.*, b.name AS brand_name
           FROM products p JOIN brands b ON p.brand_id = b.id
           WHERE p.category_id != ?
           ORDER BY RANDOM() LIMIT 4""",
        (p["category_id"],),
    ).fetchall()
    conn.close()

    specs = [s.strip() for s in (p["specs_en"] or "").split(",") if s.strip()]

    p_dict = dict(p)
    pct = p_dict.get("discount_percent", 0) or 0
    if pct > 0:
        p_dict["discount_price"] = round(p_dict["price"] * (1 - pct / 100.0), 2)
    else:
        p_dict["discount_price"] = p_dict["price"]

    return render_template("product.html", p=p_dict, images=images,
                           related=related, other_products=other_products,
                           specs=specs, icons=ICONS)


@app.route("/cart")
def cart():
    return render_template("cart.html")


@app.route("/wishlist")
def wishlist():
    return render_template("wishlist.html")


# ==========================================
# ئەپی ئای (APIs)
# ==========================================

@app.route("/api/cart-items", methods=["POST"])
def cart_items():
    """ID ی کاڵاکان وەردەگرێت و زانیاری ڕاستەقینەیان لە داتابەیسەوە دەگەڕێنێتەوە"""
    ids = request.get_json(silent=True) or []
    ids = [int(i) for i in ids if str(i).isdigit()]
    if not ids:
        return jsonify([])

    conn = get_db()
    marks = ",".join("?" * len(ids))
    rows = conn.execute(
        f"""SELECT p.id, p.name, p.price, p.discount_percent, p.image, p.variants_json, b.name AS brand_name,
                   c.slug AS cat_slug
            FROM products p
            JOIN brands b ON p.brand_id = b.id
            JOIN categories c ON p.category_id = c.id
            WHERE p.id IN ({marks})""",
        ids,
    ).fetchall()
    conn.close()
    items = []
    for r in rows:
        d = dict(r)
        pct = d.get("discount_percent", 0) or 0
        d["original_price"] = d["price"]
        if pct > 0:
            d["price"] = round(d["price"] * (1 - pct / 100.0), 2)
            d["has_discount"] = True
        else:
            d["has_discount"] = False
        items.append(d)
    return jsonify(items)


@app.route("/offline.html")
def offline_html():
    return render_template("offline.html")


@app.route("/sw.js")
def service_worker():
    from flask import make_response, send_from_directory
    response = make_response(send_from_directory("static", "sw.js"))
    response.headers["Content-Type"] = "application/javascript"
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Cache-Control"] = "no-cache"
    return response


@app.route("/api/search")
def search_api():
    """گەڕانی خێرا بۆ مۆداڵی سەرەوە و هێدەر لەگەڵ یەکەم پیت"""
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])

    conn = get_db()
    prefix_pattern = f"{q}%"
    contains_pattern = f"%{q}%"

    rows = conn.execute(
        """SELECT p.id, p.name, p.price, p.image, b.name AS brand_name, c.name_ku AS cat_ku
           FROM products p
           JOIN brands b ON p.brand_id = b.id
           JOIN categories c ON p.category_id = c.id
           WHERE p.name LIKE ? OR b.name LIKE ? OR c.name_ku LIKE ? OR c.name_en LIKE ?
           ORDER BY
               CASE
                   WHEN LOWER(p.name) LIKE LOWER(?) THEN 1
                   WHEN LOWER(b.name) LIKE LOWER(?) THEN 2
                   WHEN LOWER(p.name) LIKE LOWER(?) THEN 3
                   ELSE 4
               END,
               p.name ASC
           LIMIT 10""",
        (
            contains_pattern, contains_pattern, contains_pattern, contains_pattern,
            prefix_pattern, prefix_pattern, contains_pattern
        )
    ).fetchall()
    conn.close()

    results = []
    for r in rows:
        results.append({
            "id": r["id"],
            "name": r["name"],
            "price": r["price"],
            "price_iqd": format_iqd(r["price"]),
            "image": r["image"],
            "brand": r["brand_name"],
            "brand_name": r["brand_name"],
            "category": r["cat_ku"]
        })
    return jsonify(results)


@app.route("/api/order", methods=["POST"])
def create_order():
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()
    if is_rate_limited(client_ip, ORDER_ATTEMPTS, max_attempts=5, window_seconds=60):
        return jsonify({"ok": False, "error": "تکایە کەمێک چاوەڕێ بکە پێش ناردنی داواکاری نوێ."}), 429
    record_attempt(client_ip, ORDER_ATTEMPTS)

    data = request.get_json(silent=True) or {}

    full_name = (data.get("full_name") or "").strip()
    phone = (data.get("phone") or "").strip()
    city = (data.get("city") or "").strip()
    neighborhood = (data.get("neighborhood") or "").strip()
    cart_list = data.get("items") or []

    if not (full_name and phone and city and neighborhood and cart_list):
        return jsonify({"ok": False, "error": "هەموو خانەکان پڕ بکەرەوە"}), 400

    conn = get_db()
    lines = []
    total_usd = 0
    for item in cart_list:
        try:
            pid, qty = int(item["id"]), max(1, int(item["qty"]))
        except (KeyError, ValueError, TypeError):
            continue
        row = conn.execute("SELECT name, price, discount_percent FROM products WHERE id = ?", (pid,)).fetchone()
        if row:
            pct = row["discount_percent"] if ("discount_percent" in row.keys() and row["discount_percent"]) else 0
            unit_price = round(row["price"] * (1 - pct / 100.0), 2) if pct > 0 else row["price"]
            total_usd += unit_price * qty
            lines.append({"name": row["name"], "price": unit_price, "qty": qty})

    if not lines:
        conn.close()
        return jsonify({"ok": False, "error": "سەبەتە بەتاڵە"}), 400

    conn.execute(
        """INSERT INTO orders (full_name, phone, city, neighborhood, items, total, delivery_fee, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')""",
        (full_name, phone, city, neighborhood, json.dumps(lines, ensure_ascii=False), total_usd, DELIVERY_FEE_IQD),
    )
    conn.commit()
    order_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()

    # ناردنی ئۆردەر بۆ بۆتی تیلیگرام بە وردەکاری کرێی گەیاندن (5,000 IQD)
    sent = send_order(order_id, full_name, phone, city, neighborhood, lines, total_usd, DELIVERY_FEE_IQD)
    if not sent:
        print(f"⚠️ ئۆردەری #{order_id} نەنێردرا بۆ تیلیگرام")

    return jsonify({"ok": True, "order_id": order_id})


# ==========================================
# سیستەمی بەڕێوبەرایەتی (Admin System)
# ==========================================

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if "admin_id" in session:
        return redirect(url_for("admin_dashboard"))

    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()
    error = None

    if request.method == "POST":
        if is_rate_limited(client_ip, LOGIN_ATTEMPTS, max_attempts=5, window_seconds=300):
            error = "هەوڵە هەڵەکان زۆر بوون. تکایە ٥ خولەک چاوەڕێ بکە پێش هەوڵدانەوە (پاراستن لە هێرشی Brute-Force)."
            return render_template("admin_login.html", error=error), 429

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        conn = get_db()
        user = conn.execute("SELECT * FROM admin_users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            LOGIN_ATTEMPTS.pop(client_ip, None)
            session["admin_id"] = user["id"]
            session["admin_user"] = user["username"]
            session["admin_role"] = user["role"]
            next_url = request.args.get("next")
            # پاراستن لە هێرشی Open Redirect
            if next_url and (not next_url.startswith("/") or next_url.startswith("//") or "://" in next_url):
                next_url = url_for("admin_dashboard")
            return redirect(next_url or url_for("admin_dashboard"))
        else:
            record_attempt(client_ip, LOGIN_ATTEMPTS)
            remaining = max(0, 5 - len(LOGIN_ATTEMPTS[client_ip]))
            error = f"ناوی بەکارهێنەر یان وشەی نهێنی هەڵەیە. هەوڵی ماوە: {remaining}"

    return render_template("admin_login.html", error=error)


@app.route("/admin/signup", methods=["GET", "POST"])
def admin_signup():
    if "admin_id" in session:
        return redirect(url_for("admin_dashboard"))

    conn = get_db()
    admin_count = conn.execute("SELECT COUNT(*) FROM admin_users").fetchone()[0]
    conn.close()

    # ئەگەر ئەدمین هەبێت لە داتابەیس، تۆمارکردنی دەرەکی بە تەواوی دادەخرێت بۆ پاراستن لە هاک
    if admin_count > 0:
        return render_template(
            "admin_login.html",
            error="تۆمارکردنی ئەدمینی نوێ لە دەرەوە داخراوە بۆ پاراستنی وێبسایت. تەنها لە ڕێگەی ناوەوەی داشبۆرد دەتوانیت ئەدمین زیاد بکەیت."
        )

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or len(username) < 3:
            error = "ناوی بەکارهێنەر دەبێت لانیکەم ٣ پیت بێت"
        elif not password or len(password) < 6:
            error = "وشەی نهێنی دەبێت لانیکەم ٦ پیت بێت"
        else:
            conn = get_db()
            exist = conn.execute("SELECT id FROM admin_users WHERE username = ?", (username,)).fetchone()
            if exist:
                error = "ئەم ناوە پێشتر تۆمار کراوە"
                conn.close()
            else:
                p_hash = generate_password_hash(password)
                conn.execute("INSERT INTO admin_users (username, password_hash, role) VALUES (?, ?, 'admin')", (username, p_hash))
                conn.commit()
                new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                conn.close()

                session["admin_id"] = new_id
                session["admin_user"] = username
                session["admin_role"] = "admin"
                return redirect(url_for("admin_dashboard"))

    return render_template("admin_signup.html", error=error)


@app.route("/admin/logout", methods=["GET", "POST"])
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.route("/admin")
@admin_required
def admin_dashboard():
    conn = get_db()

    # ئۆردەرەکان
    orders_raw = conn.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    orders = []
    total_sales_iqd = 0
    for o in orders_raw:
        item_list = []
        try:
            item_list = json.loads(o["items"])
        except Exception:
            pass
        subtotal_iqd = to_iqd_num(o["total"])
        delivery = o["delivery_fee"] if "delivery_fee" in o.keys() and o["delivery_fee"] is not None else DELIVERY_FEE_IQD
        grand_total = subtotal_iqd + int(delivery)
        if o["status"] != "cancelled":
            total_sales_iqd += grand_total

        orders.append({
            "id": o["id"],
            "full_name": o["full_name"],
            "phone": o["phone"],
            "city": o["city"],
            "neighborhood": o["neighborhood"],
            "order_items": item_list,
            "subtotal_iqd": subtotal_iqd,
            "delivery_fee": int(delivery),
            "grand_total": grand_total,
            "status": o["status"] if "status" in o.keys() else "pending",
            "created_at": o["created_at"],
        })

    # ڕاپۆرتە خولییەکان (ڕۆژانە، هەفتانە، مانگانە، ساڵانە)
    now = datetime.datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    curr_month_str = now.strftime("%Y-%m")
    curr_year_str = now.strftime("%Y")
    seven_days_ago = (now - datetime.timedelta(days=7)).strftime("%Y-%m-%d")

    # ١. ڕۆژانە (ئەمڕۆ)
    today_orders = [o for o in orders if str(o["created_at"])[:10] == today_str]
    today_sales_iqd = sum(o["grand_total"] for o in today_orders if o["status"] != "cancelled")
    today_completed = sum(1 for o in today_orders if o["status"] == "completed")
    today_pending = sum(1 for o in today_orders if o["status"] == "pending")

    # ٢. هەفتانە (٧ ڕۆژی ڕابردوو)
    week_orders = [o for o in orders if str(o["created_at"])[:10] >= seven_days_ago]
    week_sales_iqd = sum(o["grand_total"] for o in week_orders if o["status"] != "cancelled")
    week_completed = sum(1 for o in week_orders if o["status"] == "completed")
    week_pending = sum(1 for o in week_orders if o["status"] == "pending")

    # ٣. مانگانە (ئەم مانگە)
    month_orders = [o for o in orders if str(o["created_at"])[:7] == curr_month_str]
    month_sales_iqd = sum(o["grand_total"] for o in month_orders if o["status"] != "cancelled")
    month_completed = sum(1 for o in month_orders if o["status"] == "completed")
    month_pending = sum(1 for o in month_orders if o["status"] == "pending")

    # ٤. ساڵانە (ئەمساڵ)
    year_orders = [o for o in orders if str(o["created_at"])[:4] == curr_year_str]
    year_sales_iqd = sum(o["grand_total"] for o in year_orders if o["status"] != "cancelled")
    year_completed = sum(1 for o in year_orders if o["status"] == "completed")
    year_pending = sum(1 for o in year_orders if o["status"] == "pending")

    # چارتێکی visual بۆ ٧ ڕۆژی ڕابردوو
    day_names_ku = {
        0: "دووشەممە",
        1: "سێشەممە",
        2: "چوارشەممە",
        3: "پێنجشەممە",
        4: "هەینی",
        5: "شەممە",
        6: "یەکشەممە"
    }
    chart_days = []
    max_day_sales = 1
    for i in range(6, -1, -1):
        day_dt = now - datetime.timedelta(days=i)
        d_str = day_dt.strftime("%Y-%m-%d")
        d_orders = [o for o in orders if str(o["created_at"])[:10] == d_str]
        d_sales = sum(o["grand_total"] for o in d_orders if o["status"] != "cancelled")
        if d_sales > max_day_sales:
            max_day_sales = d_sales
        chart_days.append({
            "date": d_str,
            "day_name": day_names_ku.get(day_dt.weekday(), d_str),
            "sales": d_sales,
            "orders_count": len(d_orders)
        })
    for d in chart_days:
        d["percent"] = max(10, int((d["sales"] / max_day_sales) * 100)) if max_day_sales > 0 else 10

    # پڕفرۆشترین کاڵاکان
    product_sales = {}
    for o in orders:
        if o["status"] != "cancelled":
            for item in o.get("order_items", []):
                p_name = item.get("name", "کاڵا")
                p_qty = int(item.get("qty", 1))
                p_price = to_iqd_num(item.get("price", 0))
                if p_name not in product_sales:
                    product_sales[p_name] = {"name": p_name, "qty": 0, "total": 0}
                product_sales[p_name]["qty"] += p_qty
                product_sales[p_name]["total"] += p_price * p_qty
    top_products = sorted(product_sales.values(), key=lambda x: x["qty"], reverse=True)[:8]

    # دابەشبوونی فرۆش بەپێی شار
    city_sales = {}
    for o in orders:
        c_name = o["city"] or "دیاری نەکراو"
        if c_name not in city_sales:
            city_sales[c_name] = {"city": c_name, "orders_count": 0, "total": 0}
        city_sales[c_name]["orders_count"] += 1
        if o["status"] != "cancelled":
            city_sales[c_name]["total"] += o["grand_total"]
    top_cities = sorted(city_sales.values(), key=lambda x: x["orders_count"], reverse=True)

    # کاڵاکان
    products = conn.execute(
        """SELECT p.*, b.name AS brand_name, c.name_ku AS cat_name
           FROM products p
           JOIN brands b ON p.brand_id = b.id
           JOIN categories c ON p.category_id = c.id
           ORDER BY p.id DESC"""
    ).fetchall()

    # هاوپۆلەکان
    categories = conn.execute(
        """SELECT c.*, COUNT(p.id) AS prod_count
           FROM categories c LEFT JOIN products p ON p.category_id = c.id
           GROUP BY c.id ORDER BY c.id"""
    ).fetchall()

    # بڕاندەکان
    brands = conn.execute(
        """SELECT b.*, COUNT(p.id) AS prod_count
           FROM brands b LEFT JOIN products p ON p.brand_id = b.id
           GROUP BY b.id ORDER BY b.name"""
    ).fetchall()

    # بەڕێوبەران
    users = conn.execute("SELECT id, username, role, created_at FROM admin_users ORDER BY id").fetchall()

    # بەرهەمە داشکێنراوەکان بۆ بەشی ئەدمین
    discounted_raw = conn.execute(
        """SELECT p.*, b.name AS brand_name, c.name_ku AS cat_name
           FROM products p
           JOIN brands b ON p.brand_id = b.id
           JOIN categories c ON p.category_id = c.id
           WHERE p.discount_percent > 0
           ORDER BY p.discount_percent DESC, p.id DESC"""
    ).fetchall()
    discounted_products = []
    for p in discounted_raw:
        d = dict(p)
        pct = d.get("discount_percent", 0) or 0
        d["discount_price"] = round(d["price"] * (1 - pct / 100.0), 2)
        discounted_products.append(d)

    # کۆمپانیاکانی براندەکان، گەیاندن و خزمەتگوزارییەکان
    brand_partners = conn.execute("SELECT * FROM brand_partners ORDER BY id DESC").fetchall()
    delivery_companies = conn.execute("SELECT * FROM delivery_companies ORDER BY id DESC").fetchall()
    service_suppliers = conn.execute("SELECT * FROM service_suppliers ORDER BY id DESC").fetchall()

    conn.close()

    return render_template(
        "admin_dashboard.html",
        orders=orders,
        products=products,
        discounted_products=discounted_products,
        categories=categories,
        brands=brands,
        users=users,
        total_sales_iqd=total_sales_iqd,
        total_orders=len(orders),
        total_products=len(products),
        today_sales_iqd=today_sales_iqd,
        today_orders=today_orders,
        today_completed=today_completed,
        today_pending=today_pending,
        week_sales_iqd=week_sales_iqd,
        week_orders=week_orders,
        week_completed=week_completed,
        week_pending=week_pending,
        month_sales_iqd=month_sales_iqd,
        month_orders=month_orders,
        month_completed=month_completed,
        month_pending=month_pending,
        year_sales_iqd=year_sales_iqd,
        year_orders=year_orders,
        year_completed=year_completed,
        year_pending=year_pending,
        chart_days=chart_days,
        top_products=top_products,
        top_cities=top_cities,
        brand_partners=brand_partners,
        delivery_companies=delivery_companies,
        service_suppliers=service_suppliers
    )


# دۆخی ئۆردەر
@app.route("/admin/orders/status/<int:order_id>", methods=["POST"])
@admin_required
def admin_order_status(order_id):
    new_status = request.form.get("status", "pending")
    conn = get_db()
    conn.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_dashboard") + "#orders")


@app.route("/admin/orders/delete/<int:order_id>", methods=["POST"])
@admin_required
def admin_order_delete(order_id):
    conn = get_db()
    conn.execute("DELETE FROM orders WHERE id = ?", (order_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_dashboard") + "#orders")


# کاڵاکان CRUD
@app.route("/admin/products/add", methods=["POST"])
@admin_required
def admin_product_add():
    cat_id = int(request.form.get("category_id"))
    brand_id = int(request.form.get("brand_id"))
    name = request.form.get("name", "").strip()
    price_iqd = float(request.form.get("price_iqd", 0))
    price_usd = price_iqd / USD_TO_IQD
    discount_percent = int(request.form.get("discount_percent") or 0)
    discount_percent = max(0, min(90, discount_percent))
    condition = request.form.get("condition", "new")
    image = request.form.get("image", "").strip()
    specs = request.form.get("specs_en", "").strip()
    desc_ku = request.form.get("desc_ku", "").strip()
    video_id = request.form.get("video_id", "").strip() or None

    conn = get_db()
    conn.execute(
        """INSERT INTO products (category_id, brand_id, name, price, discount_percent, condition, image, specs_en, desc_ku, video_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (cat_id, brand_id, name, price_usd, discount_percent, condition, image, specs, desc_ku, video_id)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("admin_dashboard") + "#products")


@app.route("/admin/product/discount/<int:product_id>", methods=["POST"])
@admin_required
def admin_product_discount(product_id):
    """داشکاندنی بەرهەمێک لەلایەن بەڕێوبەرەوە (0 تا 90%)"""
    try:
        percent = int(request.form.get("discount_percent", 0))
        percent = max(0, min(90, percent))
    except (ValueError, TypeError):
        percent = 0

    conn = get_db()
    conn.execute(
        "UPDATE products SET discount_percent = ? WHERE id = ?",
        (percent, product_id)
    )
    conn.commit()
    conn.close()
    from_tab = request.form.get("from_tab", "discounts")
    return redirect(url_for("admin_dashboard") + f"#{from_tab}")


@app.route("/admin/products/edit/<int:product_id>", methods=["POST"])
@admin_required
def admin_product_edit(product_id):
    name = request.form.get("name", "").strip()
    price_iqd = float(request.form.get("price_iqd", 0))
    price_usd = price_iqd / USD_TO_IQD
    condition = request.form.get("condition", "new")
    image = request.form.get("image", "").strip()
    specs = request.form.get("specs_en", "").strip()
    desc_ku = request.form.get("desc_ku", "").strip()

    conn = get_db()
    conn.execute(
        """UPDATE products
           SET name = ?, price = ?, condition = ?, image = ?, specs_en = ?, desc_ku = ?
           WHERE id = ?""",
        (name, price_usd, condition, image, specs, desc_ku, product_id)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("admin_dashboard") + "#products")


@app.route("/admin/products/delete/<int:product_id>", methods=["POST"])
@admin_required
def admin_product_delete(product_id):
    conn = get_db()
    conn.execute("DELETE FROM product_images WHERE product_id = ?", (product_id,))
    conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_dashboard") + "#products")


# هاوپۆلەکان CRUD
@app.route("/admin/categories/add", methods=["POST"])
@admin_required
def admin_category_add():
    slug = request.form.get("slug", "").strip()
    name_ku = request.form.get("name_ku", "").strip()
    name_ar = request.form.get("name_ar", "").strip()
    name_en = request.form.get("name_en", "").strip()

    if slug and name_ku:
        conn = get_db()
        conn.execute(
            "INSERT OR IGNORE INTO categories (slug, name_ku, name_ar, name_en) VALUES (?, ?, ?, ?)",
            (slug, name_ku, name_ar, name_en)
        )
        conn.commit()
        conn.close()
    return redirect(url_for("admin_dashboard") + "#categories")


@app.route("/admin/categories/delete/<int:cat_id>", methods=["POST"])
@admin_required
def admin_category_delete(cat_id):
    conn = get_db()
    conn.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_dashboard") + "#categories")


# بڕاندەکان CRUD
@app.route("/admin/brands/add", methods=["POST"])
@admin_required
def admin_brand_add():
    name = request.form.get("name", "").strip()
    if name:
        conn = get_db()
        conn.execute("INSERT OR IGNORE INTO brands (name) VALUES (?)", (name,))
        conn.commit()
        conn.close()
    return redirect(url_for("admin_dashboard") + "#brands")


@app.route("/admin/brands/delete/<int:brand_id>", methods=["POST"])
@admin_required
def admin_brand_delete(brand_id):
    conn = get_db()
    conn.execute("DELETE FROM brands WHERE id = ?", (brand_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_dashboard") + "#brands")


# بەڕێوبەران
@app.route("/admin/users/add", methods=["POST"])
@admin_required
def admin_user_add():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    if username and password:
        conn = get_db()
        p_hash = generate_password_hash(password)
        conn.execute("INSERT OR IGNORE INTO admin_users (username, password_hash, role) VALUES (?, ?, 'admin')", (username, p_hash))
        conn.commit()
        conn.close()
    return redirect(url_for("admin_dashboard") + "#users")


@app.route("/admin/users/delete/<int:user_id>", methods=["POST"])
@admin_required
def admin_user_delete(user_id):
    # ناهێڵین خۆی بسڕێتەوە
    if user_id != session.get("admin_id"):
        conn = get_db()
        conn.execute("DELETE FROM admin_users WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
    return redirect(url_for("admin_dashboard") + "#users")


# =====================================================
# کۆمپانیاکانی براندەکان، گەیاندن و خزمەتگوزارییەکان
# =====================================================

# ١. کۆمپانیاکانی براندەکان
@app.route("/admin/brand-partners/add", methods=["POST"])
@admin_required
def admin_brand_partner_add():
    brand_name = request.form.get("brand_name", "").strip()
    company_name = request.form.get("company_name", "").strip()
    contact_person = request.form.get("contact_person", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip()
    city = request.form.get("city", "").strip()
    address = request.form.get("address", "").strip()
    notes = request.form.get("notes", "").strip()
    if brand_name and company_name and phone:
        conn = get_db()
        conn.execute("""
            INSERT INTO brand_partners (brand_name, company_name, contact_person, phone, email, city, address, notes, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active')
        """, (brand_name, company_name, contact_person, phone, email, city, address, notes))
        conn.commit()
        conn.close()
    return redirect(url_for("admin_dashboard") + "#companies")


@app.route("/admin/brand-partners/delete/<int:partner_id>", methods=["POST"])
@admin_required
def admin_brand_partner_delete(partner_id):
    conn = get_db()
    conn.execute("DELETE FROM brand_partners WHERE id = ?", (partner_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_dashboard") + "#companies")


# ٢. کۆمپانیاکانی گەیاندن
@app.route("/admin/delivery-companies/add", methods=["POST"])
@admin_required
def admin_delivery_company_add():
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    coverage_cities = request.form.get("coverage_cities", "").strip()
    try:
        fee_iqd = int(request.form.get("fee_iqd", 5000) or 5000)
    except Exception:
        fee_iqd = 5000
    contact_person = request.form.get("contact_person", "").strip()
    delivery_time = request.form.get("delivery_time", "").strip()
    notes = request.form.get("notes", "").strip()
    if name and phone:
        conn = get_db()
        conn.execute("""
            INSERT INTO delivery_companies (name, phone, coverage_cities, fee_iqd, contact_person, delivery_time, tracking_support, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, 1, 'active', ?)
        """, (name, phone, coverage_cities, fee_iqd, contact_person, delivery_time, notes))
        conn.commit()
        conn.close()
    return redirect(url_for("admin_dashboard") + "#companies")


@app.route("/admin/delivery-companies/delete/<int:company_id>", methods=["POST"])
@admin_required
def admin_delivery_company_delete(company_id):
    conn = get_db()
    conn.execute("DELETE FROM delivery_companies WHERE id = ?", (company_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_dashboard") + "#companies")


# ٣. دابینکەرانی خزمەتگوزاری و پێداویستییەکان
@app.route("/admin/service-suppliers/add", methods=["POST"])
@admin_required
def admin_service_supplier_add():
    name = request.form.get("name", "").strip()
    service_type = request.form.get("service_type", "").strip()
    contact_person = request.form.get("contact_person", "").strip()
    phone = request.form.get("phone", "").strip()
    address = request.form.get("address", "").strip()
    notes = request.form.get("notes", "").strip()
    if name and phone:
        conn = get_db()
        conn.execute("""
            INSERT INTO service_suppliers (name, service_type, contact_person, phone, address, notes, status)
            VALUES (?, ?, ?, ?, ?, ?, 'active')
        """, (name, service_type, contact_person, phone, address, notes))
        conn.commit()
        conn.close()
    return redirect(url_for("admin_dashboard") + "#companies")


@app.route("/admin/service-suppliers/delete/<int:supplier_id>", methods=["POST"])
@admin_required
def admin_service_supplier_delete(supplier_id):
    conn = get_db()
    conn.execute("DELETE FROM service_suppliers WHERE id = ?", (supplier_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_dashboard") + "#companies")


if __name__ == "__main__":
    init_db()
    is_debug = os.environ.get("FLASK_DEBUG", "0").lower() in ["1", "true"]
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=is_debug)
