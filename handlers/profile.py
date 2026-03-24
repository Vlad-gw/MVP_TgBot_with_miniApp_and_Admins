# handlers/profile.py

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from database.db import db
from utils.keyboards import mini_app_inline_keyboard

router = Router()


async def _build_profile_text(tg_id: int) -> str | None:
    user = await db.execute(
        """
        SELECT id, username, first_name, created_at
        FROM users
        WHERE telegram_id = $1
        """,
        tg_id,
        fetchrow=True
    )

    if not user:
        return None

    income = await db.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE user_id = $1 AND type = 'income'
        """,
        user["id"],
        fetchval=True
    )

    expense = await db.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE user_id = $1 AND type = 'expense'
        """,
        user["id"],
        fetchval=True
    )

    count = await db.execute(
        """
        SELECT COUNT(*)
        FROM transactions
        WHERE user_id = $1
        """,
        user["id"],
        fetchval=True
    )

    username = user["username"] if user["username"] else None
    username_str = f"@{username}" if username else "—"

    created_at = user["created_at"]
    created_str = created_at.strftime("%d.%m.%Y") if created_at else "—"

    income_value = float(income or 0)
    expense_value = float(expense or 0)
    balance_value = income_value - expense_value

    text = (
        "👤 <b>Профиль</b>\n\n"
        f"<b>Имя:</b> {user['first_name'] or '—'}\n"
        f"<b>Username:</b> {username_str}\n"
        f"<b>Дата регистрации:</b> {created_str}\n\n"
        "📊 <b>Статистика</b>\n"
        f"• Транзакций: {int(count or 0)}\n"
        f"• Доходы: {income_value:.2f} ₽\n"
        f"• Расходы: {expense_value:.2f} ₽\n"
        f"• Баланс: {balance_value:.2f} ₽\n\n"
        "Подробная информация и полный анализ доступны в Mini App."
    )

    return text


@router.message(Command("profile"))
async def profile_command(message: Message):
    text = await _build_profile_text(message.from_user.id)

    if text is None:
        await message.answer("Сначала нажми /start, чтобы зарегистрироваться.")
        return

    await message.answer(
        text,
        reply_markup=mini_app_inline_keyboard()
    )


@router.message(F.text == "👤 Профиль")
async def show_profile(message: Message):
    text = await _build_profile_text(message.from_user.id)

    if text is None:
        await message.answer("Сначала нажми /start, чтобы зарегистрироваться.")
        return

    await message.answer(
        text,
        reply_markup=mini_app_inline_keyboard()
    )