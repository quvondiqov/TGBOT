import os
from dotenv import load_dotenv

load_dotenv()

def _safe_int(val: str, default: int) -> int:
    try:
        return int(val)
    except (ValueError, TypeError):
        return default

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

# Taps.uz sozlamalari
TAPS_URL: str = os.getenv("TAPS_URL", "https://taps.uz/topkinone")

# Narx (so'mda)
PROFILE_PRICE_UZS: int = _safe_int(os.getenv("PROFILE_PRICE_UZS", "15000"), 15000)

ADMIN_ID: int = _safe_int(os.getenv("ADMIN_ID", "0"), 0)
