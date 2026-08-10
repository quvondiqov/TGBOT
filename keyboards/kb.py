from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)


# ──────────────────── REPLY KEYBOARDS ────────────────────

def gender_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👨 Erkak"), KeyboardButton(text="👩 Ayol")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def skip_photo_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⏭ O'tkazib yuborish")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❤️ Profillarni ko'rish")],
            [KeyboardButton(text="👤 Mening profilim"), KeyboardButton(text="✏️ Profilni tahrirlash")]
        ],
        resize_keyboard=True
    )


# ──────────────────── INLINE KEYBOARDS ────────────────────

def browse_kb(target_id: int, is_purchased: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="❤️ Like", callback_data=f"like:{target_id}"),
            InlineKeyboardButton(text="👎 Skip", callback_data=f"skip:{target_id}"),
        ]
    ]
    if not is_purchased:
        buttons.append([
            InlineKeyboardButton(
                text="💳 Akkauntini olish — 15,000 UZS",
                callback_data=f"buy:{target_id}"
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def taps_payment_kb(taps_url: str, target_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💳 To'lash (Taps.uz)", url=taps_url)
        ],
        [
            InlineKeyboardButton(text="🔄 To'lovni tekshirish", callback_data=f"check_pay:{target_id}")
        ]
    ])


def full_profile_kb(target_id: int) -> InlineKeyboardMarkup:
    """Keyboard for full profile view, includes contact button."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✉️ Yozish", url=f"tg://user?id={target_id}")
        ]
    ])


def admin_approval_kb(pay_id: str) -> InlineKeyboardMarkup:
    """Admin to'lovni tasdiqlash / rad etish tugmalari."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_pay:{pay_id}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_pay:{pay_id}")
        ]
    ])


def confirm_edit_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Ha, tahrirlash", callback_data="edit_profile"),
            InlineKeyboardButton(text="❌ Yo'q", callback_data="cancel_edit")
        ]
    ])
