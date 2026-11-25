import sqlite3
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "nexora.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT UNIQUE NOT NULL,
            name_ku TEXT NOT NULL,
            name_ar TEXT NOT NULL,
            name_en TEXT NOT NULL,
            has_used INTEGER DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS brands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            brand_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            price REAL NOT NULL DEFAULT 0,
            discount_percent INTEGER DEFAULT 0,
            condition TEXT NOT NULL DEFAULT 'new',
            image TEXT,
            specs_en TEXT,
            desc_ku TEXT,
            desc_ar TEXT,
            desc_en TEXT,
            video_id TEXT,
            variants_json TEXT,
            FOREIGN KEY (category_id) REFERENCES categories(id),
            FOREIGN KEY (brand_id) REFERENCES brands(id)
        )
    """)

    # وێنەکانی هەر کاڵایەک (گەلەری)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS product_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            image TEXT NOT NULL,
            sort_order INTEGER DEFAULT 0,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            city TEXT NOT NULL,
            neighborhood TEXT NOT NULL,
            items TEXT NOT NULL,
            total REAL NOT NULL,
            delivery_fee REAL DEFAULT 5000,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'admin',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # خشتەی کۆمپانیا و دابەشکەرانی براندەکان
    cur.execute("""
        CREATE TABLE IF NOT EXISTS brand_partners (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand_name TEXT NOT NULL,
            company_name TEXT NOT NULL,
            contact_person TEXT,
            phone TEXT NOT NULL,
            email TEXT,
            city TEXT,
            address TEXT,
            notes TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # خشتەی کۆمپانیاکانی گەیاندن
    cur.execute("""
        CREATE TABLE IF NOT EXISTS delivery_companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            coverage_cities TEXT NOT NULL,
            fee_iqd INTEGER DEFAULT 5000,
            contact_person TEXT,
            delivery_time TEXT,
            tracking_support INTEGER DEFAULT 1,
            status TEXT DEFAULT 'active',
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # خشتەی خزمەتگوزاری و دابینکەرە پێویستەکان
    cur.execute("""
        CREATE TABLE IF NOT EXISTS service_suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            service_type TEXT NOT NULL,
            contact_person TEXT,
            phone TEXT NOT NULL,
            address TEXT,
            notes TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ئەگەر ستوونی variants_json نەبوو لە products زیادی دەکەین
    cur.execute("PRAGMA table_info(products)")
    p_cols = [row["name"] for row in cur.fetchall()]
    if "variants_json" not in p_cols:
        cur.execute("ALTER TABLE products ADD COLUMN variants_json TEXT")

    # ئەگەر خشتەی orders پێشتر دروست کرابێت بەبێ ستوونە نوێیەکان، زیادیان دەکەین
    cur.execute("PRAGMA table_info(orders)")
    cols = [row["name"] for row in cur.fetchall()]
    if "delivery_fee" not in cols:
        cur.execute("ALTER TABLE orders ADD COLUMN delivery_fee REAL DEFAULT 5000")
    if "status" not in cols:
        cur.execute("ALTER TABLE orders ADD COLUMN status TEXT DEFAULT 'pending'")

    # ئەگەر ئەدمین نەبوو، هەژمارێکی سەرەتایی دروست دەکەین
    from werkzeug.security import generate_password_hash
    cur.execute("SELECT COUNT(*) FROM admin_users")
    if cur.fetchone()[0] == 0:
        cur.execute(
            "INSERT INTO admin_users (username, password_hash, role) VALUES (?, ?, ?)",
            ("admin", generate_password_hash("admin123"), "admin")
        )

    # داتای سەرەتایی بۆ کۆمپانیاکانی براندەکان
    cur.execute("SELECT COUNT(*) FROM brand_partners")
    if cur.fetchone()[0] == 0:
        sample_brand_partners = [
            ("Logitech G", "Logitech Iraq Official Distributor", "کاک کاروان حەسیب", "0750 111 2233", "logitech.iq@distributor.com", "هەولێر", "شەقامی ٦٠ مەتری - بەرامبەر پیشانگای نێودەوڵەتی", "دابینکەری سەرەکی ماوس و کیبۆرد و هێدسێت بە گەرەنتی ١ ساڵ", "active"),
            ("Razer", "Razer Middle East Hub (Iraq Agent)", "ئارام کامەران", "0770 222 3344", "razer.iraq@sales.net", "بەغدا / هەولێر", "گەڕەکی وەزیریا - ئۆفیسی سەرەکی", "دابینکەری ماوسپاد و دەسک و بیستۆکی گەیمینگی ڕەیزەر", "active"),
            ("ASUS ROG", "ASUS Republic of Gamers Distribution", "هێمن فەرهاد", "0750 333 4455", "rog.erbil@asus-dealer.com", "هەولێر", "ئیمپایەر وۆرڵد - تاوەری T2", "مۆنیتەر و ماوس و دەسکی گەیمینگی ئەسۆس", "active"),
            ("MSI", "MSI Gaming Kurdistan", "ڕەوا جەبار", "0751 444 5566", "msi.support@krdtech.com", "سلێمانی", "شەقامی سەهۆڵەکە - باڵەخانەی تەکنەلۆژیا", "دابینکەری کەلوپەل و کارتی شاشە و مۆنیتەری ئێم ئێس ئای", "active"),
            ("Corsair", "Corsair & Elgato Authorized Channel", "دانا عەزیز", "0750 555 6677", "corsair.krd@channel.com", "هەولێر", "شەقامی کەرکووک - کۆمەڵگەی کۆمپیوتەر", "دابینکەری کیبۆردی میکانیکی و ستریم دێک و مایک", "active"),
            ("HyperX", "HyperX Gaming Gear Co.", "محەممەد بەکر", "0770 777 8899", "hyperx@gear-iq.com", "دهۆک", "سەنتەری شار - بازاڕی مۆدێرن", "دابینکەری هێدسێتی Cloud و مایکڕۆفۆنی QuadCast", "active")
        ]
        cur.executemany("""
            INSERT INTO brand_partners (brand_name, company_name, contact_person, phone, email, city, address, notes, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, sample_brand_partners)

    # داتای سەرەتایی بۆ کۆمپانیاکانی گەیاندن
    cur.execute("SELECT COUNT(*) FROM delivery_companies")
    if cur.fetchone()[0] == 0:
        sample_delivery = [
            ("فست دلیڤەری (Fast Delivery)", "0750 888 1122", "هەولێر، سلێمانی، دهۆک، کەرکووک، بەغدا", 5000, "سەروەر عەلی - مودیری ئۆپەراسیۆن", "٢٤ بۆ ٤٨ کاتژمێر", 1, "active", "گرێبەستی فەرمی - پارەدان لە کاتی وەرگرتن (COD)"),
            ("لیزۆ ئێکسپرێس (Lezzoo Express)", "0750 777 3344", "هەولێر، سلێمانی، دهۆک", 4000, "بەهمەن جەمال", "هەمان ڕۆژ لە هەولێر - بۆ شارەکانی تر ٢٤ کاتژمێر", 1, "active", "سیستەمی ڕاستەوخۆی شوێنپێهەڵگرتن بە GPS"),
            ("کوردستان دلیڤەری (Kurdistan Courier)", "0770 666 4455", "سەرجەم شار و قەزاکانی هەرێمی کوردستان", 5000, "ئاری مەحموود", "٢٤ بۆ ٧٢ کاتژمێر", 1, "active", "گەیاندنی خێرا بۆ هەڵەبجە، زاخۆ، گەرمیان و سۆران"),
            ("ڤی ئای پی ئێکسپرێس (VIP Gaming Delivery)", "0750 999 0011", "هەولێر، بەغدا، بەسڕە", 6000, "شوان مەریوان", "٢٤ کاتژمێر بە پارێزراوی تایبەت", 1, "active", "تایبەت بە کاڵای بەنرخ و مۆنیتەر و کەیسی گەیمینگ بە کارتۆنی تۆکمە")
        ]
        cur.executemany("""
            INSERT INTO delivery_companies (name, phone, coverage_cities, fee_iqd, contact_person, delivery_time, tracking_support, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, sample_delivery)

    # داتای سەرەتایی بۆ خزمەتگوزاری و دابینکەرە پێویستەکان
    cur.execute("SELECT COUNT(*) FROM service_suppliers")
    if cur.fetchone()[0] == 0:
        sample_services = [
            ("سەنتەری چاککردنەوەی تەکنیکی هاردوێر و لاپتۆپ", "چاککردنەوە و گەرەنتی", "ئەندازیار ڕێبوار", "0750 123 7890", "هەولێر - شەقامی ٤٠ مەتری", "چاککردنەوەی کارتی گرافیک، گۆڕینی کلیل و پاتری لاپتۆپی گەیمینگ", "active"),
            ("دابینکەری کارتۆن و باکێجینگی تۆکمەی گەیمینگ", "پاکێجینگ و کارتۆن", "حاجی عومەر تەها", "0750 456 1234", "هەولێر - ناوچەی پیشەسازی باکوور", "دابینکردنی کارتۆنی دژە زەبر و بڵقی پارێزەر بۆ گەیاندنی کاڵاکان", "active"),
            ("کۆمپانیای دابینکردنی کەیبڵ و ئەداپتەری پلە یەک", "پارچەی یەدەگ و ئەکسسوارات", "زانا سالار", "0770 987 6543", "سلێمانی - بازاڕی مەولەوی", "کەیبڵی Type-C، کێبڵی مۆنیتەر DisplayPort 1.4 و HDMI 2.1 ئەسڵی", "active")
        ]
        cur.executemany("""
            INSERT INTO service_suppliers (name, service_type, contact_person, phone, address, notes, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, sample_services)

    conn.commit()

    # پشکنینی ستوونی discount_percent بۆ کاڵاکان
    prod_cols = [r[1] for r in cur.execute("PRAGMA table_info(products)").fetchall()]
    if "discount_percent" not in prod_cols:
        cur.execute("ALTER TABLE products ADD COLUMN discount_percent INTEGER DEFAULT 0")
        conn.commit()

    conn.close()
    print("✅ داتابەیس و خشتەکان دروست کران")


if __name__ == "__main__":
    init_db()