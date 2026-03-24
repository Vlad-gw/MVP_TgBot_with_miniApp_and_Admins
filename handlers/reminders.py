# handlers/reminders.py

from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

from database.db import db

router = Router()


def settings_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Профиль")],
            [KeyboardButton(text="🔔 Напоминания")],
            [KeyboardButton(text="🔙 Назад")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выбери действие в настройках",
    )


def reminders_inline_keyboard(enabled: bool) -> InlineKeyboardMarkup:
    status_text = "✅ Включены" if enabled else "❌ Выключены"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"Статус: {status_text}",
                    callback_data="reminder_status_info",
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ Включить",
                    callback_data="reminder_enable",
                ),
                InlineKeyboardButton(
                    text="❌ Выключить",
                    callback_data="reminder_disable",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔙 К настройкам",
                    callback_data="reminder_back_to_settings",
                )
            ],
        ]
    )


def format_reminder_text(enabled: bool, remind_time) -> str:
    time_str = remind_time.strftime("%H:%M") if remind_time else "20:00"
    status_text = "✅ Включены" if enabled else "❌ Выключены"

    return (
        "🔔 <b>Напоминания</b>\n\n"
        f"<b>Статус:</b> {status_text}\n"
        f"<b>Время напоминания:</b> {time_str}\n\n"
        "Бот отправит напоминание добавить транзакции, "
        "если за текущий день ещё нет записей."
    )


async def _get_or_create_user(message_or_callback) -> dict:
    tg_user = message_or_callback.from_user

    user = await db.get_user_by_telegram_id(tg_user.id)
    if not user:
        user = await db.create_user(
            telegram_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name,
        )

    return user


@router.message(F.text == "🔔 Напоминания")
async def open_reminders_menu(message: Message):
    user = await _get_or_create_user(message)
    reminder = await db.get_reminder_settings(user["id"])

    await message.answer(
        format_reminder_text(
            enabled=reminder["enabled"],
            remind_time=reminder["remind_time"],
        ),
        reply_markup=reminders_inline_keyboard(reminder["enabled"]),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "reminder_enable")
async def enable_reminders(callback: CallbackQuery):
    user = await _get_or_create_user(callback)
    reminder = await db.set_reminder_enabled(user["id"], True)

    await callback.message.edit_text(
        format_reminder_text(
            enabled=reminder["enabled"],
            remind_time=reminder["remind_time"],
        ),
        reply_markup=reminders_inline_keyboard(reminder["enabled"]),
        parse_mode="HTML",
    )
    await callback.answer("Напоминания включены")


@router.callback_query(F.data == "reminder_disable")
async def disable_reminders(callback: CallbackQuery):
    user = await _get_or_create_user(callback)
    reminder = await db.set_reminder_enabled(user["id"], False)

    await callback.message.edit_text(
        format_reminder_text(
            enabled=reminder["enabled"],
            remind_time=reminder["remind_time"],
        ),
        reply_markup=reminders_inline_keyboard(reminder["enabled"]),
        parse_mode="HTML",
    )
    await callback.answer("Напоминания выключены")


@router.callback_query(F.data == "reminder_status_info")
async def reminder_status_info(callback: CallbackQuery):
    await callback.answer("Здесь показан текущий статус напоминаний")


@router.callback_query(F.data == "reminder_back_to_settings")
async def reminder_back_to_settings(callback: CallbackQuery):
    await callback.message.answer(
        "⚙️ <b>Настройки</b>\n\n"
        "Здесь можно открыть профиль или настроить напоминания.",
        reply_markup=settings_menu(),
        parse_mode="HTML",
    )
    await callback.answer()