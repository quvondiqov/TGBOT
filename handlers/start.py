import asyncio
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database.db import get_user
from keyboards.kb import main_menu_kb, confirm_edit_kb
from states.states import Registration

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = await get_user(message.from_user.id)

    if user:
        gender_emoji = "👨" if user["gender"] == "male" else "👩"
        await message.answer(
            f"Xush kelibsiz, {gender_emoji} <b>{user['name']}</b>!\n\n"
            f"Siz allaqachon ro'yxatdan o'tgansiz.\n"
            f"Profillarni ko'rish uchun tugmani bosing 👇",
            reply_markup=main_menu_kb(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "👋 <b>Tanishuv Botiga Xush Kelibsiz!</b>\n\n"
            "🔥 Bu yerda yangi tanishliklar va do'stlar topa olasiz.\n\n"
            "Boshlash uchun /register ni bosing.",
            parse_mode="HTML"
        )


@router.message(Command("register"))
async def cmd_register(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if user:
        await message.answer(
            "Siz allaqachon ro'yxatdan o'tgansiz.\n"
            "Profilingizni tahrirlashni xohlaysizmi?",
            reply_markup=confirm_edit_kb()
        )
        return

    from keyboards.kb import gender_kb
    await state.set_state(Registration.gender)
    await message.answer(
        "🌟 <b>Ro'yxatdan o'tish</b>\n\n"
        "Jinsingizni tanlang:",
        reply_markup=gender_kb(),
        parse_mode="HTML"
    )


@router.message(Command("myprofile"))
async def cmd_myprofile(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Siz ro'yxatdan o'tmagansiz. /register buyrug'ini yuboring.")
        return
    await show_my_profile(message, user)


@router.message(F.text == "👤 Mening profilim")
async def my_profile_btn(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Ro'yxatdan o'tmagansiz. /register yuboring.")
        return
    await show_my_profile(message, user)


@router.message(F.text == "✏️ Profilni tahrirlash")
async def edit_profile_btn(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Ro'yxatdan o'tmagansiz.")
        return
    from keyboards.kb import gender_kb
    await state.set_state(Registration.gender)
    await message.answer(
        "✏️ Profilni yangilash. Jinsingizni tanlang:",
        reply_markup=gender_kb()
    )


@router.callback_query(F.data == "edit_profile")
async def edit_profile_cb(callback: CallbackQuery, state: FSMContext):
    from keyboards.kb import gender_kb
    await state.set_state(Registration.gender)
    await callback.message.answer(
        "✏️ Profilni yangilaylik. Jinsingizni tanlang:",
        reply_markup=gender_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "cancel_edit")
async def cancel_edit_cb(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer("Bekor qilindi.")


async def show_my_profile(message: Message, user: dict):
    gender_text = "Erkak 👨" if user["gender"] == "male" else "Ayol 👩"
    text = (
        f"👤 <b>Mening profilim</b>\n\n"
        f"📛 Ism: <b>{user['name']}</b>\n"
        f"🎂 Yosh: <b>{user['age']}</b>\n"
        f"🏙 Shahar: <b>{user.get('city') or 'Ko\'rsatilmagan'}</b>\n"
        f"⚧ Jins: <b>{gender_text}</b>\n"
        f"📝 Bio: <i>{user.get('bio') or 'Yo\'q'}</i>"
    )
    if user.get("photo_id"):
        await message.answer_photo(
            photo=user["photo_id"],
            caption=text,
            reply_markup=main_menu_kb(),
            parse_mode="HTML"
        )
    else:
        await message.answer(text, reply_markup=main_menu_kb(), parse_mode="HTML")
