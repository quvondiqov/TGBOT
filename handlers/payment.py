import uuid
import logging
from aiogram import Router, F, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from config import PROFILE_PRICE_UZS, TAPS_URL, ADMIN_ID
from database.db import (
    get_user, create_purchase, get_purchase, get_purchase_by_pay_id,
    update_purchase_status, is_profile_purchased
)
from keyboards.kb import taps_payment_kb, full_profile_kb, admin_approval_kb
from utils.taps_helper import auto_verify_taps_payment, get_taps_payment_link
from states.states import Payment

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data.startswith("buy:"))
async def handle_buy(callback: CallbackQuery, state: FSMContext, bot: Bot):
    target_id = int(callback.data.split(":")[1])
    buyer_id = callback.from_user.id

    buyer = await get_user(buyer_id)
    if not buyer:
        await callback.answer("Ro'yxatdan o'tmagansiz!", show_alert=True)
        return

    # Allaqachon sotib olinganmi?
    if await is_profile_purchased(buyer_id, target_id):
        await callback.answer("Bu profil akkauntini allaqachon sotib olgansiz!", show_alert=True)
        await _send_full_profile(bot, buyer_id, target_id)
        return

    # Mavjud to'lov bormi?
    existing = await get_purchase(buyer_id, target_id)
    if existing and existing["status"] == "paid":
        await callback.answer("✅ To'lov allaqachon bajarilgan!", show_alert=True)
        await _send_full_profile(bot, buyer_id, target_id)
        return

    # Yangi yoki mavjud pay_id
    if existing and existing["status"] in ["pending", "waiting_check"]:
        pay_id = existing["pay_id"]
    else:
        pay_id = f"pay_{buyer_id}_{target_id}_{uuid.uuid4().hex[:6]}"
        await create_purchase(buyer_id, target_id, pay_id)

    await state.set_state(Payment.waiting_payment)
    await state.update_data(pay_id=pay_id, target_id=target_id)

    payment_url = get_taps_payment_link(pay_id)

    await callback.answer("💳 Taps.uz to'lov havolasi tayyor!")

    await callback.message.answer(
        f"💳 <b>Akkauntni Olish Uchun To'lov (Taps.uz)</b>\n\n"
        f"Foydalanuvchi akkauntini olish narxi: <b>{PROFILE_PRICE_UZS:,} UZS</b>\n"
        f"Havola: <a href='{payment_url}'>{payment_url}</a>\n\n"
        f"📸 <b>DIQQAT:</b> To'lovni amalga oshirganingizdan so'ng, to'lov cheki (skrinshot) rasmini ushbu chatga yuboring!\n\n"
        f"<i>Bot chek rasmini admin'ga yuboradi va tasdiqlangach profil ochiladi.</i>",
        reply_markup=taps_payment_kb(payment_url, target_id),
        parse_mode="HTML"
    )


@router.message(Payment.waiting_payment, F.photo)
async def process_payment_screenshot(message: Message, state: FSMContext, bot: Bot):
    """Foydalanuvchi to'lov cheki rasmini yuborganda adminga jo'natish"""
    data = await state.get_data()
    pay_id = data.get("pay_id")
    target_id = data.get("target_id")
    buyer_id = message.from_user.id

    if not pay_id or not target_id:
        await message.answer("To'lov jarayoni topilmadi. Qaytadan urinib ko'ring.")
        await state.clear()
        return

    buyer = await get_user(buyer_id)
    target = await get_user(target_id)
    photo_id = message.photo[-1].file_id

    await update_purchase_status(pay_id, "waiting_check")
    await state.clear()

    buyer_name = buyer["name"] if buyer else "Noma'lum"
    target_name = target["name"] if target else "Noma'lum"

    # Adminga yuborish
    if ADMIN_ID and ADMIN_ID != 0:
        try:
            caption = (
                f"🧾 <b>Yangi To'lov Cheki (Skrinshot)</b>\n\n"
                f"🆔 Pay ID: <code>{pay_id}</code>\n"
                f"👤 Xaridor: <b>{buyer_name}</b> (ID: <code>{buyer_id}</code>)\n"
                f"🎯 Maqsadli profil: <b>{target_name}</b> (ID: <code>{target_id}</code>)\n"
                f"💰 Summa: <b>{PROFILE_PRICE_UZS:,} UZS</b>"
            )
            await bot.send_photo(
                chat_id=ADMIN_ID,
                photo=photo_id,
                caption=caption,
                reply_markup=admin_approval_kb(pay_id),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Adminga to'lov chekini yuborishda xato: {e}")

    await message.answer(
        "✅ <b>To'lov cheki (skrinshot) qabul qilindi!</b>\n\n"
        "Admin tekshirib tasdiqlagach, ushbu foydalanuvchining to'liq profil ma'lumotlari va Telegram akkaunti sizga taqdim etiladi. ⏳",
        parse_mode="HTML"
    )


@router.message(Payment.waiting_payment)
async def process_payment_screenshot_wrong(message: Message):
    await message.answer("📸 Iltimos, to'lov muvaffaqiyatli bajarilganini tasdiqlovchi <b>rasm (skrinshot)</b> yuboring!", parse_mode="HTML")


@router.callback_query(F.data.startswith("check_pay:"))
async def handle_check_payment(callback: CallbackQuery, state: FSMContext, bot: Bot):
    target_id = int(callback.data.split(":")[1])
    buyer_id = callback.from_user.id

    purchase = await get_purchase(buyer_id, target_id)
    if not purchase:
        await callback.answer("To'lov topilmadi.", show_alert=True)
        return

    if purchase["status"] == "paid":
        await callback.answer("✅ To'lov tasdiqlangan!", show_alert=True)
        await _send_full_profile(bot, buyer_id, target_id)
        return

    if purchase["status"] == "waiting_check":
        await callback.answer("⏳ Chekingiz admin tomonidan tekshirilmoqda. Iltimos biroz kuting!", show_alert=True)
        await callback.message.answer(
            "⏳ <b>To'lov chekingiz admin tomonidan tekshirilmoqda.</b>\n"
            "Admin tasdiqlagach, ushbu foydalanuvchining to'liq profil ma'lumotlari sizga yuboriladi.",
            parse_mode="HTML"
        )
        return

    await state.set_state(Payment.waiting_payment)
    await state.update_data(pay_id=purchase["pay_id"], target_id=target_id)

    await callback.answer("📸 Chek skrinshotini yuboring!")
    await callback.message.answer(
        "📸 <b>To'lov Skrinshotini Yuboring</b>\n\n"
        "Taps.uz orqali to'lovni amalga oshirganingizdan so'ng, to'lov cheki (skrinshot) rasmini ushbu chatga yuboring!\n\n"
        "<i>Bot chek rasmini admin'ga yuboradi va admin tasdiqlagach profil ochiladi.</i>",
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("approve_pay:"))
async def handle_approve_pay(callback: CallbackQuery, bot: Bot):
    pay_id = callback.data.split(":", 1)[1]
    purchase = await get_purchase_by_pay_id(pay_id)

    if not purchase:
        await callback.answer("To'lov ma'lumoti topilmadi.", show_alert=True)
        return

    if purchase["status"] == "paid":
        await callback.answer("Ushbu to'lov allaqachon tasdiqlangan!", show_alert=True)
        return

    await update_purchase_status(pay_id, "paid")
    buyer_id = purchase["buyer_id"]
    target_id = purchase["target_id"]

    # Admin xabarini yangilash
    try:
        await callback.message.edit_caption(
            caption=callback.message.caption + "\n\n✅ <b>TASDIQLANDI</b>",
            reply_markup=None,
            parse_mode="HTML"
        )
    except Exception:
        pass

    await callback.answer("✅ To'lov tasdiqlandi!")

    # Xaridorga profilni yuborish
    try:
        await bot.send_message(
            buyer_id,
            "🎉 <b>To'lovingiz admin tomonidan tasdiqlandi!</b>\n"
            "To'liq profil ma'lumotlari va Telegram akkaunti taqdim etildi 👇",
            parse_mode="HTML"
        )
        await _send_full_profile(bot, buyer_id, target_id)
    except Exception as e:
        logger.error(f"Xaridorga to'liq profilni yuborishda xato: {e}")


@router.callback_query(F.data.startswith("reject_pay:"))
async def handle_reject_pay(callback: CallbackQuery, bot: Bot):
    pay_id = callback.data.split(":", 1)[1]
    purchase = await get_purchase_by_pay_id(pay_id)

    if not purchase:
        await callback.answer("To'lov ma'lumoti topilmadi.", show_alert=True)
        return

    await update_purchase_status(pay_id, "rejected")
    buyer_id = purchase["buyer_id"]

    try:
        await callback.message.edit_caption(
            caption=callback.message.caption + "\n\n❌ <b>RAD ETILDI</b>",
            reply_markup=None,
            parse_mode="HTML"
        )
    except Exception:
        pass

    await callback.answer("❌ To'lov rad etildi.")

    try:
        await bot.send_message(
            buyer_id,
            "❌ <b>Yuborgan to'lov chekingiz (skrinshot) rad etildi.</b>\n"
            "Iltimos, to'g'ri to'lov chekini yuboring yoki qaytadan to'lov qiling.",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Xaridorga rad etish xabarini yuborishda xato: {e}")


async def _send_full_profile(bot: Bot, buyer_id: int, target_id: int):
    """To'liq profilni foydalanuvchiga yuborish"""
    target = await get_user(target_id)
    if not target:
        await bot.send_message(buyer_id, "❌ Profil topilmadi.")
        return

    city_val = target.get("city") or "Noma'lum"
    bio_val = target.get("bio") or "Yo'q"
    tg_link = f"tg://user?id={target_id}"

    caption = (
        f"✅ <b>To'liq profil ochildi!</b>\n\n"
        f"📛 Ism: <b>{target['name']}</b>\n"
        f"🎂 Yosh: <b>{target['age']}</b>\n"
        f"🏙 Shahar: <b>{city_val}</b>\n"
        f"📝 Bio: <i>{bio_val}</i>\n\n"
        f"💬 Murojaat: <a href='{tg_link}'>Telegram'da yozish</a>"
    )

    photo_id = target.get("photo_id")
    if photo_id:
        try:
            await bot.send_photo(
                buyer_id,
                photo=photo_id,
                caption=caption,
                reply_markup=full_profile_kb(target_id),
                parse_mode="HTML"
            )
        except TelegramBadRequest as e:
            logger.warning(f"_send_full_profile: noto'g'ri file_id ({e}). Matn yuborilmoqda.")
            await bot.send_message(
                buyer_id,
                caption,
                reply_markup=full_profile_kb(target_id),
                parse_mode="HTML"
            )
    else:
        await bot.send_message(
            buyer_id,
            caption,
            reply_markup=full_profile_kb(target_id),
            parse_mode="HTML"
        )


