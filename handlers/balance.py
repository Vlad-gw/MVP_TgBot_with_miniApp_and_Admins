# handlers/balance.py

from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message

from database.db import db
from utils.keyboards import mini_app_inline_keyboard

router = Router()


@router.message(F.text == "💰 Баланс")
async def show_balance(message: Message):
    telegram_id = message.from_user.id

    user_id = await db.execute(
        "SELECT id FROM users WHERE telegram_id = $1",
        telegram_id,
        fetchval=True
    )

    if not user_id:
        await message.answer("Сначала нажми /start, чтобы зарегистрироваться.")
        return

    total_income = await db.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE user_id = $1 AND type = 'income'
        """,
        user_id,
        fetchval=True
    )

    total_expense = await db.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE user_id = $1 AND type = 'expense'
        """,
        user_id,
        fetchval=True
    )

    now = datetime.now()
    month_start = datetime(now.year, now.month, 1)

    month_income = await db.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE user_id = $1
          AND type = 'income'
          AND date >= $2
        """,
        user_id,
        month_start,
        fetchval=True
    )

    month_expense = await db.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE user_id = $1
          AND type = 'expense'
          AND date >= $2
        """,
        user_id,
        month_start,
        fetchval=True
    )

    balance = float(total_income) - float(total_expense)

    await message.answer(
        "💰 <b>Баланс</b>\n\n"
        f"<b>Текущий баланс:</b> {balance:.2f} ₽\n\n"
        f"<b>За всё время:</b>\n"
        f"📈 Доходы: {float(total_income):.2f} ₽\n"
        f"📉 Расходы: {float(total_expense):.2f} ₽\n\n"
        f"<b>За текущий месяц:</b>\n"
        f"📈 Доходы: {float(month_income):.2f} ₽\n"
        f"📉 Расходы: {float(month_expense):.2f} ₽\n\n"
        "Подробная аналитика доступна в Mini App.",
        reply_markup=mini_app_inline_keyboard(),
    )