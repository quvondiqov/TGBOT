import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from database.db import add_user
from keyboards.kb import gender_kb, skip_photo_kb, main_menu_kb
from states.states import Registration

logger = logging.getLogger(__name__)
router = Router()

GENDER_MAP = {"👨 Erkak": "male", "👩 Ayol": "female"}


@router.message(Registration.gender)
async def process_gender(message: Message, state: FSMContext):
    gender = GENDER_MAP.get(message.text)
    if not gender:
        await message.answer("Iltimos, tugmalardan birini tanlang 👇", reply_markup=gender_kb())
        return

    await state.update_data(gender=gender)
    await state.set_state(Registration.name)
    await message.answer(
        "✨ Ajoyib! Endi <b>ismingizni</b> kiriting:",
        parse_mode="HTML"
    )


@router.message(Registration.name)
async def process_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2 or len(name) > 50:
        await message.answer("Ism 2-50 ta belgidan iborat bo'lishi kerak. Qaytadan kiriting:")
        return

    await state.update_data(name=name)
    await state.set_state(Registration.age)
    await message.answer(
        f"🎉 Salom, <b>{name}</b>!\n\n"
        "Yoshingizni kiriting (14-60):",
        parse_mode="HTML"
    )


@router.message(Registration.age)
async def process_age(message: Message, state: FSMContext):
    try:
        age = int(message.text.strip())
        if age < 14 or age > 60:
            raise ValueError
    except ValueError:
        await message.answer("Iltimos, to'g'ri yosh kiriting (14-60):")
        return

    await state.update_data(age=age)
    await state.set_state(Registration.bio)
    await message.answer(
        "📝 O'zingiz haqingizda qisqacha yozing\n"
        "<i>(maksimal 300 ta belgi)</i>:",
        parse_mode="HTML"
    )


@router.message(Registration.bio)
async def process_bio(message: Message, state: FSMContext):
    bio = message.text.strip()
    if len(bio) > 300:
        await message.answer("Bio juda uzun! 300 ta belgidan kam yozing:")
        return

    await state.update_data(bio=bio)
    await state.set_state(Registration.photo)
    await message.answer(
        "🤳 Rasmingizni yuboring:\n"
        "<i>(Ro'yxatdan o'tish uchun rasm yuborish majburiy!)</i>",
        reply_markup=None,
        parse_mode="HTML"
    )


@router.message(Registration.photo, F.photo)
async def process_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_id)
    await state.set_state(Registration.city)
    await message.answer(
        "🏙 Shahringizni kiriting:",
        reply_markup=None
    )


@router.message(Registration.photo)
async def process_photo_wrong(message: Message):
    await message.answer("⚠️ Ro'yxatdan o'tish uchun rasm yuborishingiz shart! Iltimos, rasmingizni yuboring:")


@router.message(Registration.city)
async def process_city(message: Message, state: FSMContext):
    city = message.text.strip()
    if len(city) > 50:
        await message.answer("Shahar nomi juda uzun. Qaytadan kiriting:")
        return

    data = await state.update_data(city=city)
    await state.clear()

    # Foydalanuvchini bazaga saqlash
    await add_user(
        user_id=message.from_user.id,
        gender=data["gender"],
        name=data["name"],
        age=data["age"],
        bio=data.get("bio"),
        photo_id=data.get("photo_id"),
        city=city
    )

    gender_text = "👨 Erkak" if data["gender"] == "male" else "👩 Ayol"
    await message.answer(
        f"✅ <b>Ro'yxatdan o'tdingiz!</b>\n\n"
        f"📛 Ism: <b>{data['name']}</b>\n"
        f"🎂 Yosh: <b>{data['age']}</b>\n"
        f"🏙 Shahar: <b>{city}</b>\n"
        f"⚧ Jins: <b>{gender_text}</b>\n\n"
        "Endi profillarni ko'rishingiz mumkin! 🔥",
        reply_markup=main_menu_kb(),
        parse_mode="HTML"
    )
