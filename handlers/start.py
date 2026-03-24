# handlers/start.py

import os

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    CallbackQuery,
)

from database.db import db
from utils.keyboards import main_menu, mini_app_inline_keyboard, settings_menu

router = Router()


def _get_mini_app_url() -> str:
    base_url = os.getenv("MINI_APP_URL", "").strip().rstrip("/")
    if not base_url:
        base_url = os.getenv("SITE_URL", "http://127.0.0.1:8000").strip().rstrip("/")
    return f"{base_url}/miniapp/"


def _is_https_url(url: str) -> bool:
    return url.startswith("https://")


def _start_text(first_name: str, mini_app_ready: bool) -> str:
    mini_app_text = (
        "Нажми кнопку ниже — <b>📱 Открыть Mini App</b>"
        if mini_app_ready
        else "Mini App временно недоступен (нужен HTTPS)"
    )

    return (
        f"Привет, <b>{first_name}</b> 👋\n\n"
        f"Я — твой финансовый помощник.\n"
        f"Помогаю учитывать доходы и расходы за пару секунд.\n\n"

        f"<b>⚡ Быстрый ввод:</b>\n"
        f"<code>+100000 зарплата вчера</code>\n"
        f"<code>-500 бензин сегодня</code>\n\n"

        f"<b>🤖 В боте:</b>\n"
        f"• быстрый ввод операций\n"
        f"• баланс и история\n"
        f"• импорт выписки\n"
        f"• экспорт в Excel\n"
        f"• настройки\n\n"

        f"<b>📱 В Mini App:</b>\n"
        f"• удобный интерфейс\n"
        f"• аналитика и графики\n"
        f"• фильтры и поиск\n"
        f"• бюджеты и прогноз\n\n"

        f"<b>👉 Mini App:</b>\n"
        f"{mini_app_text}\n\n"

        f"<b>Подсказка:</b>\n"
        f"• <b>+</b> — доход, <b>-</b> — расход\n"
        f"• без даты — сегодня\n"
        f"• без времени — текущее время"
    )


@router.message(CommandStart())
async def cmd_start(message: Message):
    tg_id = message.from_user.id

    user = await db.execute(
        """
        SELECT id
        FROM users
        WHERE telegram_id = $1
        """,
        tg_id,
        fetchval=True
    )

    if not user:
        await db.execute(
            """
            INSERT INTO users (telegram_id, username, first_name)
            VALUES ($1, $2, $3)
            """,
            tg_id,
            message.from_user.username,
            message.from_user.first_name,
            execute=True
        )

    mini_app_ready = _is_https_url(_get_mini_app_url())

    await message.answer(
        _start_text(message.from_user.first_name, mini_app_ready),
        reply_markup=main_menu()
    )

    await message.answer(
        "📱 <b>Открыть Mini App</b>",
        reply_markup=mini_app_inline_keyboard()
    )


@router.message(F.text == "⚙️ Настройки")
async def open_settings(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "⚙️ <b>Настройки</b>\n\n"
        "Здесь можно открыть профиль или настроить напоминания.",
        reply_markup=settings_menu()
    )


@router.message(F.text == "🔙 Назад")
async def go_back(message: Message, state: FSMContext):
    await state.clear()

    mini_app_ready = _is_https_url(_get_mini_app_url())

    text = (
        "🔁 <b>Главное меню</b>\n\n"
        "<b>Быстрый ввод:</b>\n"
        "<code>+100000 зарплата вчера 21:21</code>\n"
        "<code>-500 бензин сегодня</code>\n\n"
        "<b>В боте:</b> быстрый ввод, баланс, последние операции, импорт, экспорт и настройки.\n"
        "<b>В Mini App:</b> полная история, аналитика, бюджеты, прогноз и удобное управление."
    )

    if mini_app_ready:
        text += "\n\nДля полного управления финансами используй кнопку <b>📱 Открыть Mini App</b>."
    else:
        text += "\n\nMini App пока недоступен: нужен <b>HTTPS</b>."

    await message.answer(
        text,
        reply_markup=main_menu()
    )

    await message.answer(
        "📱 <b>Открыть Mini App</b>",
        reply_markup=mini_app_inline_keyboard()
    )


@router.message(F.text == "📱 Открыть Mini App")
async def mini_app_hint(message: Message):
    await message.answer(
        "Для полного управления финансами открой <b>Mini App</b> кнопкой ниже.",
        reply_markup=mini_app_inline_keyboard()
    )


@router.callback_query(F.data == "miniapp_https_required")
async def miniapp_https_required(callback: CallbackQuery):
    await callback.answer(
        "Mini App пока недоступен: нужен HTTPS URL.",
        show_alert=True
    )