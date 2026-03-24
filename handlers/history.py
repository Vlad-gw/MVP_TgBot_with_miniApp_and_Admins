# handlers/history.py

from aiogram import Router, F
from aiogram.types import Message

from database.db import db
from utils.keyboards import mini_app_inline_keyboard

router = Router()


@router.message(F.text == "📜 Последние операции")
async def show_recent_transactions(message: Message):
    telegram_id = message.from_user.id

    user_id = await db.execute(
        "SELECT id FROM users WHERE telegram_id = $1",
        telegram_id,
        fetchval=True
    )

    if not user_id:
        await message.answer("Сначала нажми /start, чтобы зарегистрироваться.")
        return

    transactions = await db.execute(
        """
        SELECT
            t.type,
            COALESCE(c.name, 'Без категории') AS category_name,
            t.amount,
            t.date,
            t.note
        FROM transactions t
        LEFT JOIN categories c ON c.id = t.category_id
        WHERE t.user_id = $1
        ORDER BY t.date DESC
        LIMIT 10
        """,
        user_id,
        fetch=True
    )

    if not transactions:
        await message.answer(
            "Пока нет операций.\n\n"
            "Добавь первую запись сообщением, например:\n"
            "<code>-350 кофе</code>\n"
            "<code>+5000 зарплата</code>"
        )
        return

    lines = ["📜 <b>Последние операции</b>\n"]

    for tx in transactions:
        icon = "🟢" if tx["type"] == "income" else "🔴"
        sign = "+" if tx["type"] == "income" else "-"
        date_str = tx["date"].strftime("%d.%m.%Y %H:%M")

        line = (
            f"{icon} <b>{sign}{float(tx['amount']):.2f} ₽</b> — "
            f"{tx['category_name']} "
            f"(<i>{date_str}</i>)"
        )

        if tx["note"]:
            line += f"\n💬 {tx['note']}"

        lines.append(line)

    lines.append("\nПолная история, фильтры и управление записями доступны в Mini App.")

    await message.answer(
        "\n\n".join(lines),
        reply_markup=mini_app_inline_keyboard(),
    )