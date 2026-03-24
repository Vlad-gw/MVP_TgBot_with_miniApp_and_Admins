import os

from aiogram import Router, F
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    FSInputFile,
)

from config import ADMIN_IDS
from database.db import db
from services.export import export_user_to_excel

router = Router(name=__name__)


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def _get_admin_site_url() -> str:
    base_url = os.getenv("ADMIN_SITE_URL", "").strip().rstrip("/")
    if not base_url:
        base_url = os.getenv("SITE_URL", "").strip().rstrip("/")
    if not base_url:
        base_url = "http://127.0.0.1:8000"
    return f"{base_url}/admin/"


def _admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🌐 Открыть сайт админки",
                    url=_get_admin_site_url(),
                )
            ]
        ]
    )


@router.message(F.text == "/admin")
async def admin_menu(message: Message):
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ У вас нет прав администратора.")

    await message.answer(
        "🛠 <b>Админ-панель</b>\n\n"
        "• /stats — статистика\n"
        "• /users — последние пользователи\n"
        "• /all_transactions — топ 10 транзакций\n"
        "• /user [telegram_id] — карточка пользователя\n\n"
        "Нажми кнопку ниже, чтобы открыть веб-админку.",
        parse_mode="HTML",
        reply_markup=_admin_menu_keyboard(),
    )


@router.message(F.text == "/stats")
async def show_stats(message: Message):
    if not is_admin(message.from_user.id):
        return

    users = await db.execute("SELECT COUNT(*) FROM users", fetchval=True)
    txs = await db.execute("SELECT COUNT(*) FROM transactions", fetchval=True)
    budgets = await db.execute("SELECT COUNT(*) FROM budgets", fetchval=True)
    templates = await db.execute("SELECT COUNT(*) FROM transaction_templates", fetchval=True)

    await message.answer(
        "📊 <b>Статистика</b>\n"
        f"Пользователей: <b>{users}</b>\n"
        f"Транзакций: <b>{txs}</b>\n"
        f"Бюджетов: <b>{budgets}</b>\n"
        f"Шаблонов: <b>{templates}</b>",
        parse_mode="HTML",
    )


@router.message(F.text == "/users")
async def show_users(message: Message):
    if not is_admin(message.from_user.id):
        return

    rows = await db.execute(
        """
        SELECT telegram_id, username, first_name
        FROM users
        ORDER BY id DESC
        LIMIT 50
        """,
        fetch=True,
    )

    if not rows:
        return await message.answer("👥 Пользователей пока нет.")

    text_lines = []
    for row in rows:
        if row["username"]:
            text_lines.append(f"• @{row['username']} — <code>{row['telegram_id']}</code>")
        else:
            text_lines.append(f"• {row['first_name'] or 'без имени'} — <code>{row['telegram_id']}</code>")

    await message.answer(
        "👥 <b>Последние пользователи</b>\n\n" + "\n".join(text_lines),
        parse_mode="HTML",
    )


@router.message(F.text == "/all_transactions")
async def show_transactions(message: Message):
    if not is_admin(message.from_user.id):
        return

    rows = await db.execute(
        """
        SELECT t.id, t.amount, t.type, t.date, t.note,
               c.name AS category_name,
               u.username, u.telegram_id
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        LEFT JOIN users u ON t.user_id = u.id
        ORDER BY t.amount DESC
        LIMIT 10
        """,
        fetch=True,
    )

    if not rows:
        return await message.answer("🧾 Нет транзакций.")

    text_lines = []
    for row in rows:
        icon = "🟢" if row["type"] == "income" else "🔴"
        user_info = f"@{row['username']}" if row["username"] else f"id:{row['telegram_id']}"
        line = (
            f"{icon} <b>#{row['id']}</b> — {row['amount']} ₽\n"
            f"👤 {user_info}\n"
            f"📂 {row['category_name'] or 'Без категории'}\n"
            f"📅 {row['date'].strftime('%d.%m.%Y')}"
        )
        if row["note"]:
            line += f"\n💬 {row['note']}"
        text_lines.append(line)

    await message.answer(
        "🧾 <b>Топ 10 транзакций</b>\n\n" + "\n\n".join(text_lines),
        parse_mode="HTML",
    )


@router.message(F.text.startswith("/user"))
async def get_user_info(message: Message):
    if not is_admin(message.from_user.id):
        return

    parts = message.text.strip().split()
    if len(parts) != 2 or not parts[1].isdigit():
        return await message.answer("❗ Использование: /user [telegram_id]")

    telegram_id = int(parts[1])

    user = await db.execute(
        "SELECT * FROM users WHERE telegram_id = $1",
        telegram_id,
        fetchrow=True,
    )
    if not user:
        return await message.answer("❌ Пользователь не найден.")

    text = (
        f"👤 <b>Информация о пользователе</b>\n"
        f"<b>Telegram ID:</b> <code>{user['telegram_id']}</code>\n"
        f"<b>Username:</b> @{user['username'] or '—'}\n"
        f"<b>Имя:</b> {user.get('first_name') or '—'}\n"
        f"<b>Дата регистрации:</b> "
        f"{user['created_at'].strftime('%Y-%m-%d %H:%M') if user['created_at'] else '—'}"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📤 Экспортировать", callback_data=f"export_user:{telegram_id}")],
            [InlineKeyboardButton(text="❌ Удалить", callback_data=f"delete_user:{telegram_id}")],
            [InlineKeyboardButton(text="🌐 Открыть сайт админки", url=_get_admin_site_url())],
        ]
    )

    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("export_user:"))
async def export_user(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    telegram_id = int(callback.data.split(":")[1])
    path = await export_user_to_excel(telegram_id)
    await callback.message.answer_document(FSInputFile(path))
    await callback.answer("Файл выгружен")


@router.callback_query(F.data.startswith("delete_user:"))
async def delete_user(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    telegram_id = int(callback.data.split(":")[1])

    user_id = await db.execute(
        "SELECT id FROM users WHERE telegram_id = $1",
        telegram_id,
        fetchval=True,
    )
    if not user_id:
        return await callback.message.edit_text("❌ Пользователь не найден.")

    await db.execute("DELETE FROM transactions WHERE user_id = $1", user_id, execute=True)
    await db.execute("DELETE FROM categories WHERE user_id = $1", user_id, execute=True)
    await db.execute("DELETE FROM users WHERE id = $1", user_id, execute=True)

    await callback.message.edit_text("✅ Пользователь и его данные удалены.")
    await callback.answer("Удалено")