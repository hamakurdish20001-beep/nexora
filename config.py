import os

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8737141887:AAG1LDRqCJoqFm3LWdkSEN03REWjr5hicYg")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "1222226684")
# ڕێژەی گۆڕین: ١ دۆلار = چەند دینار
USD_TO_IQD = int(os.environ.get("USD_TO_IQD", 1310))
# کرێی گەیاندن بە دینار
DELIVERY_FEE_IQD = int(os.environ.get("DELIVERY_FEE_IQD", 5000))
# کلیلی سڕی بۆ سێشنەکان (لە سێرڤەر بە Environment Variable دادەنرێت بۆ پاراستن لە هاک)
SECRET_KEY = os.environ.get("SECRET_KEY", "nexora_sec_key_2026_super_safe_mane_9837a4b2c1d0e")
# ژمارەی کاڵا لە هەر پەڕەیەک لە بەشی هەموو کاڵاکان
ITEMS_PER_PAGE = int(os.environ.get("ITEMS_PER_PAGE", 16))
