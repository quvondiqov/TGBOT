import logging
import urllib.parse
import aiohttp
from config import TAPS_URL, PROFILE_PRICE_UZS

logger = logging.getLogger(__name__)


def get_taps_payment_link(pay_id: str = "", amount_uzs: int = PROFILE_PRICE_UZS) -> str:
    """Taps.uz to'lov havolasini shakllantirish."""
    if not pay_id:
        return TAPS_URL

    base_url = TAPS_URL.rstrip('/')
    params = {
        "comment": pay_id,
        "amount": amount_uzs
    }
    query_string = urllib.parse.urlencode(params)
    return f"{base_url}?{query_string}"


async def auto_verify_taps_payment(pay_id: str, buyer_id: int) -> bool:
    """Taps.uz sayti orqali to'lov bajarilganini tekshirish algoritmi."""
    logger.info(f"🔍 [Taps.uz] To'lov tekshiruvi boshlandi: pay_id={pay_id}, buyer_id={buyer_id}")
    
    api_check_url = f"{TAPS_URL.rstrip('/')}/api/check"
    params = {"pay_id": pay_id, "account": buyer_id, "comment": pay_id}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_check_url, params=params, timeout=8) as resp:
                if resp.status == 200:
                    try:
                        data = await resp.json()
                        logger.info(f"✅ Taps API javobi: {data}")
                        if data.get("status") in ["paid", "success", "completed"] or data.get("paid") is True:
                            return True
                    except Exception:
                        html_text = await resp.text()
                        if any(word in html_text.lower() for word in ["paid", "success", "muvaffaqiyatli", "to'landi"]):
                            return True

            async with session.get(TAPS_URL, params={"pay_id": pay_id}, timeout=8) as resp2:
                if resp2.status == 200:
                    text = await resp2.text()
                    if pay_id in text and any(w in text.lower() for w in ["paid", "success", "to'landi"]):
                        return True

    except Exception as e:
        logger.warning(f"⚠️ Taps verification network check note: {e}")

    # Chek rasmiga tayanilgani sababli, avto-tekshiruv API javob bermasa False qaytaradi (xavfsiz rejim)
    return False
