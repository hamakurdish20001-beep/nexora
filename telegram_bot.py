import html
import requests
from config import BOT_TOKEN, CHAT_ID, USD_TO_IQD, DELIVERY_FEE_IQD


def to_iqd(usd):
    """نرخی دۆلار دەکات بە دینار (نزیکترین هەزار)"""
    return int(round(float(usd) * USD_TO_IQD, -3))


def send_order(order_id, full_name, phone, city, neighborhood, lines, items_total_usd, delivery_fee=DELIVERY_FEE_IQD):
    """ئۆردەرەکە بۆ تیلیگرام دەنێرێت. ئەگەر سەرکەوتوو بوو True دەگەڕێنێتەوە"""

    items_text = ""
    subtotal_iqd = 0
    for l in lines:
        unit = to_iqd(l["price"])
        line_total = unit * l["qty"]
        subtotal_iqd += line_total
        items_text += (
            f"• {html.escape(l['name'])}\n"
            f"   {l['qty']} × {unit:,} = {line_total:,} IQD\n"
        )

    grand_total_iqd = subtotal_iqd + int(delivery_fee)

    text = (
        f"🛒 <b>داواکاری نوێ #{order_id}</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"👤 <b>ناو:</b> {html.escape(full_name)}\n"
        f"📞 <b>تەلەفۆن:</b> <code>{html.escape(phone)}</code>\n"
        f"📍 <b>شار:</b> {html.escape(city)}\n"
        f"🏘 <b>گەڕەک:</b> {html.escape(neighborhood)}\n"
        f"━━━━━━━━━━━━━━\n"
        f"📦 <b>کاڵاکان:</b>\n{items_text}"
        f"━━━━━━━━━━━━━━\n"
        f"💵 <b>کۆی کاڵاکان:</b> {subtotal_iqd:,} IQD\n"
        f"🚚 <b>کرێی گەیاندن:</b> {int(delivery_fee):,} IQD\n"
        f"💰 <b>کۆی گشتی کۆتایی: {grand_total_iqd:,} IQD</b>"
    )

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(
            url,
            json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        return r.ok
    except requests.RequestException:
        return False
