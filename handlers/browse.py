import logging
from aiogram import Router, F, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database.db import (
    get_user, get_next_profile, mark_viewed, clear_viewed,
    add_like, is_profile_purchased
)
from keyboards.kb import browse_kb, main_menu_kb, full_profile_kb
from states.states import Browse

logger = logging.getLogger(__name__)
router = Router()

TARGET_GENDER = {"male": "female", "female": "male"}


async def send_profile(message_or_callback, bot: Bot, user: dict, profile: dict, is_purchased: bool):
    """Profilni ko'rsatish: rasm + inner inline keyboard (Akkauntini olish)"""
    city_val = profile.get("city") or "Noma'lum"
    bio_val = profile.get("bio") or "Yo'q"
    target_id = profile["user_id"]

    if isinstance(message_or_callback, CallbackQuery):
        chat_id = message_or_callback.from_user.id
    else:
        chat_id = message_or_callback.chat.id

    if is_purchased:
        # To'liq profil
        tg_link = f"tg://user?id={target_id}"
        caption = (
            f"💌 <b>To'liq profil</b>\n\n"
            f"📛 Ism: <b>{profile['name']}</b>\n"
            f"🎂 Yosh: <b>{profile['age']}</b>\n"
            f"🏙 Shahar: <b>{city_val}</b>\n"
            f"📝 Bio: <i>{bio_val}</i>\n\n"
            f"💬 Murojaat: <a href='{tg_link}'>Telegram'da yozish</a>"
        )
        kb = full_profile_kb(target_id)
    else:
        # Qisman profil
        bio_short = profile.get("bio") or "Bio yo'q"
        caption = (
            f"👤 <b>{profile['name']}</b>, {profile['age']} yosh\n"
            f"🏙 <b>{city_val}</b>\n"
            f"📝 <i>{bio_short}</i>\n\n"
            f"🔒 Telegram akkauntini olish narxi — <b>15,000 UZS</b>"
        )
        kb = browse_kb(target_id, is_purchased=False)

    photo_id = profile.get("photo_id")
    if photo_id:
        try:
            await bot.send_photo(
                chat_id=chat_id,
                photo=photo_id,
                caption=caption,
                reply_markup=kb,
                parse_mode="HTML"
            )
        except TelegramBadRequest as e:
            logger.warning(f"send_photo xatosi (noto'g'ri file_id): {e}. Matn ko'rinishida yuborilmoqda.")
            await bot.send_message(
                chat_id=chat_id,
                text=caption,
                reply_markup=kb,
                parse_mode="HTML"
            )
    else:
        await bot.send_message(
            chat_id=chat_id,
            text=caption,
            reply_markup=kb,
            parse_mode="HTML"
        )


@router.message(F.text == "❤️ Profillarni ko'rish")
async def browse_profiles(message: Message, state: FSMContext, bot: Bot):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Ro'yxatdan o'tmagansiz. /register yuboring.")
        return

    target_gender = TARGET_GENDER.get(user["gender"])
    profile = await get_next_profile(message.from_user.id, target_gender)

    if not profile:
        # No unviewed profiles left; reset view history and try again
        await clear_viewed(message.from_user.id)
        profile = await get_next_profile(message.from_user.id, target_gender)
        if not profile:
            await message.answer(
                "😔 Hozircha ko'radigan profil yo'q.\n" 
                "Keyinroq qayta urinib ko'ring!",
                reply_markup=main_menu_kb()
            )
            return

    await mark_viewed(message.from_user.id, profile["user_id"])
    await state.set_state(Browse.browsing)
    await state.update_data(current_profile=profile["user_id"])

    purchased = await is_profile_purchased(message.from_user.id, profile["user_id"])
    await send_profile(message, bot, user, profile, purchased)


@router.callback_query(F.data.startswith("like:"))
async def handle_like(callback: CallbackQuery, state: FSMContext, bot: Bot):
    target_id = int(callback.data.split(":")[1])
    viewer = await get_user(callback.from_user.id)
    if not viewer:
        await callback.answer("Ro'yxatdan o'tmagansiz!", show_alert=True)
        return

    is_match = await add_like(callback.from_user.id, target_id)

    if is_match:
        # O'zaro like — match! (Akkauntini faqat to'lov orqali olish mumkin)
        target = await get_user(target_id)

        # Kuzatuvchiga xabar
        await bot.send_message(
            callback.from_user.id,
            f"🎉 <b>Match!</b> {target['name']} ham sizni yoqtirdi!\n"
            f"💬 Uning Telegram akkauntini olish uchun pastdagi <b>\"💳 Akkauntini olish\"</b> tugmasini bosing.",
            parse_mode="HTML"
        )
        # Maqsadga xabar
        await bot.send_message(
            target_id,
            f"🎉 <b>Match!</b> {viewer['name']} ham sizni yoqtirdi!",
            parse_mode="HTML"
        )
        await callback.answer("💘 Match!", show_alert=True)
    else:
        await callback.answer("❤️ Like qo'yildi!")

    # Keyingi profilga o'tish
    await _next_profile(callback, state, bot, viewer)


@router.callback_query(F.data.startswith("skip:"))
async def handle_skip(callback: CallbackQuery, state: FSMContext, bot: Bot):
    viewer = await get_user(callback.from_user.id)
    if not viewer:
        await callback.answer("Ro'yxatdan o'tmagansiz!", show_alert=True)
        return
    await callback.answer("👎 O'tkazib yuborildi")
    await _next_profile(callback, state, bot, viewer)


async def _next_profile(callback: CallbackQuery, state: FSMContext, bot: Bot, viewer: dict):
    """Keyingi profilni yuborish"""
    target_gender = TARGET_GENDER.get(viewer["gender"])
    profile = await get_next_profile(callback.from_user.id, target_gender)

    if not profile:
        # No unviewed profiles left; reset view history and try again
        await clear_viewed(callback.from_user.id)
        profile = await get_next_profile(callback.from_user.id, target_gender)
        if not profile:
            await callback.message.answer(
                "😔 Yangi profil qolmadi. Keyinroq qaytib keling!",
                reply_markup=main_menu_kb()
            )
            await state.clear()
            return

    await mark_viewed(callback.from_user.id, profile["user_id"])
    await state.update_data(current_profile=profile["user_id"])

    purchased = await is_profile_purchased(callback.from_user.id, profile["user_id"])
    await send_profile(callback, bot, viewer, profile, purchased)
