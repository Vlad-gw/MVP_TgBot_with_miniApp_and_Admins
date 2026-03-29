from __future__ import annotations

from datetime import datetime
import re

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from database.db import db
from database.repository import TransactionRepository
from services.income_category_resolver import resolve_income_category
from services.ml.classifier.predict import predict_category
from services.text_transaction_parser import (
    QuickParseError,
    combine_to_datetime,
    parse_quick_transaction,
)
from states.transaction_states import QuickExpenseState
from handlers.transactions.keyboards import (
    build_category_keyboard,
    quick_expense_confirm_keyboard,
)

router = Router()

FALLBACK_EXPENSE_CATEGORY = "Прочее"

LIKELY_TRANSACTION_WITHOUT_SIGN_RE = re.compile(
    r"^\s*\d+(?:[.,]\d{1,2})?(?:\s+\S.*)?$"
)

MENU_BUTTON_TEXTS = {
    "💰 Баланс",
    "📜 Последние операции",
    "📥 Импорт выписки",
    "📁 Экспорт в Excel",
    "📱 Открыть Mini App",
    "⚙️ Настройки",
    "👤 Профиль",
    "🔔 Напоминания",
    "🔙 Назад",
}


def build_quick_add_help_text(error_text: str | None = None) -> str:
    text = (
        "Не удалось распознать запись.\n\n"
        "Как вводить правильно:\n"
        "• <code>+100000 зарплата вчера 21:21</code>\n"
        "• <code>+100000 зп 03.03.2026</code>\n"
        "• <code>-500 бензин сегодня</code>\n"
        "• <code>-1200 кафе вчера 19:15</code>\n\n"
        "Правила:\n"
        "• <b>+</b> — доход\n"
        "• <b>-</b> — расход\n"
        "• сначала сумма, потом описание\n"
        "• дата и время — необязательно\n"
        "• без времени — текущее время\n"
    )

    if error_text:
        text += f"\nОшибка: <b>{error_text}</b>"

    return text


def build_plain_text_hint() -> str:
    return (
        "Похоже, это не запись дохода или расхода.\n\n"
        "Для быстрого добавления используй такой формат:\n"
        "• <code>+100000 зарплата</code>\n"
        "• <code>-500 бензин сегодня</code>\n"
        "• <code>-1200 кафе вчера 19:15</code>\n\n"
        "Где:\n"
        "• <b>+</b> — доход\n"
        "• <b>-</b> — расход"
    )


@router.message(F.text.startswith("+"))
@router.message(F.text.startswith("-"))
async def quick_add_transaction(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is not None:
        return

    text = (message.text or "").strip()

    try:
        parsed = parse_quick_transaction(text)
        tx_dt = combine_to_datetime(parsed)
    except QuickParseError as e:
        await message.answer(build_quick_add_help_text(str(e)))
        return

    telegram_id = message.from_user.id
    user_id = await TransactionRepository.get_user_id(telegram_id)

    if not user_id:
        await message.answer("Сначала нажми /start, чтобы зарегистрироваться в системе.")
        return

    time_status = "указано" if parsed.time_provided else "текущее"

    if parsed.tx_type == "income":
        income_category_name = resolve_income_category(parsed.note)

        category_id = await TransactionRepository.get_category_id(
            user_id=user_id,
            category_name=income_category_name,
            type_="income",
        )

        if not category_id:
            category_id = await TransactionRepository.create_category(
                user_id=user_id,
                category_name=income_category_name,
                type_="income",
            )

        await TransactionRepository.add_transaction(
            user_id=user_id,
            category_id=category_id,
            amount=float(parsed.amount),
            datetime_=tx_dt,
            type_="income",
            note=parsed.note,
            suggested_category_id=None,
            is_category_accepted=True,
        )

        await message.answer(
            "✅ Доход добавлен\n\n"
            f"<b>Сумма:</b> {parsed.amount}\n"
            f"<b>Описание:</b> {parsed.note}\n"
            f"<b>Категория:</b> {income_category_name}\n"
            f"<b>Дата:</b> {parsed.tx_date.strftime('%d.%m.%Y')}\n"
            f"<b>Время:</b> {parsed.tx_time.strftime('%H:%M')} ({time_status})"
        )
        return

    predicted_name = None
    conf = 0.0

    try:
        predicted_name, conf, _ = predict_category(
            parsed.note,
            float(parsed.amount),
            top_k=3,
        )
    except Exception as e:
        print("ML quick_add error:", e)
        predicted_name, conf = None, 0.0

    expense_category_name = predicted_name or FALLBACK_EXPENSE_CATEGORY

    suggested_category_id = await TransactionRepository.get_category_id(
        user_id=user_id,
        category_name=expense_category_name,
        type_="expense",
    )

    if not suggested_category_id:
        suggested_category_id = await TransactionRepository.create_category(
            user_id=user_id,
            category_name=expense_category_name,
            type_="expense",
        )

    await state.update_data(
        quick_expense_user_id=user_id,
        quick_expense_amount=float(parsed.amount),
        quick_expense_note=parsed.note,
        quick_expense_datetime=tx_dt.isoformat(),
        quick_expense_category_name=expense_category_name,
        quick_expense_category_id=suggested_category_id,
        quick_expense_confidence=conf,
        quick_expense_date_str=parsed.tx_date.strftime("%d.%m.%Y"),
        quick_expense_time_str=parsed.tx_time.strftime("%H:%M"),
        quick_expense_time_status=time_status,
        quick_expense_has_prediction=bool(predicted_name),
    )

    if predicted_name:
        await state.set_state(QuickExpenseState.confirming_ml_category)
        await message.answer(
            "🤖 Проверь категорию расхода\n\n"
            f"<b>Сумма:</b> {parsed.amount}\n"
            f"<b>Описание:</b> {parsed.note}\n"
            f"<b>ML-категория:</b> {expense_category_name}\n"
            f"<b>Уверенность:</b> {conf:.2%}\n"
            f"<b>Дата:</b> {parsed.tx_date.strftime('%d.%m.%Y')}\n"
            f"<b>Время:</b> {parsed.tx_time.strftime('%H:%M')} ({time_status})",
            reply_markup=quick_expense_confirm_keyboard(),
        )
        return

    rows = await db.execute(
        "SELECT name FROM categories WHERE user_id=$1 AND type='expense' ORDER BY name",
        user_id,
        fetch=True,
    )
    categories = [r["name"] for r in rows]

    await state.set_state(QuickExpenseState.choosing_manual_category)
    await message.answer(
        "Не смог определить категорию. Выбери вручную:",
        reply_markup=build_category_keyboard(categories, "quick_expense_cat_"),
    )


@router.message(F.text.regexp(LIKELY_TRANSACTION_WITHOUT_SIGN_RE.pattern))
async def quick_add_without_sign_hint(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is not None:
        return

    text = (message.text or "").strip()

    if text.startswith("/"):
        return

    if text in MENU_BUTTON_TEXTS:
        return

    await message.answer(
        "Похоже, ты пытаешься быстро добавить операцию, но не указал тип.\n\n"
        "Используй:\n"
        "• <b>+</b> перед суммой для дохода\n"
        "• <b>-</b> перед суммой для расхода\n\n"
        "Примеры:\n"
        "<code>+100000 зарплата</code>\n"
        "<code>-500 бензин сегодня</code>"
    )


@router.message(F.text)
async def quick_add_plain_text_fallback(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is not None:
        return

    text = (message.text or "").strip()

    if not text:
        return

    if text.startswith("/"):
        return

    if text in MENU_BUTTON_TEXTS:
        return

    if text.startswith("+") or text.startswith("-"):
        return

    if LIKELY_TRANSACTION_WITHOUT_SIGN_RE.match(text):
        return

    await message.answer(build_plain_text_hint())


@router.callback_query(F.data == "quick_expense_confirm", QuickExpenseState.confirming_ml_category)
async def quick_expense_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()

    await TransactionRepository.add_transaction(
        user_id=data["quick_expense_user_id"],
        category_id=data["quick_expense_category_id"],
        amount=data["quick_expense_amount"],
        datetime_=datetime.fromisoformat(data["quick_expense_datetime"]),
        type_="expense",
        note=data["quick_expense_note"],
        suggested_category_id=data["quick_expense_category_id"],
        is_category_accepted=True,
    )

    await state.clear()
    await callback.answer("Сохранено")
    await callback.message.answer(
        "💸 Расход добавлен\n\n"
        f"<b>Сумма:</b> {data['quick_expense_amount']}\n"
        f"<b>Описание:</b> {data['quick_expense_note']}\n"
        f"<b>Категория:</b> {data['quick_expense_category_name']}\n"
        f"<b>Дата:</b> {data['quick_expense_date_str']}\n"
        f"<b>Время:</b> {data['quick_expense_time_str']} ({data['quick_expense_time_status']})"
    )


@router.callback_query(F.data == "quick_expense_other", QuickExpenseState.confirming_ml_category)
async def quick_expense_other(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    user_id = data["quick_expense_user_id"]

    rows = await db.execute(
        "SELECT name FROM categories WHERE user_id=$1 AND type='expense' ORDER BY name",
        user_id,
        fetch=True,
    )
    categories = [r["name"] for r in rows]

    await state.set_state(QuickExpenseState.choosing_manual_category)
    await callback.answer()
    await callback.message.answer(
        "Выбери категорию вручную:",
        reply_markup=build_category_keyboard(categories, "quick_expense_cat_"),
    )


@router.callback_query(F.data == "quick_expense_cancel", QuickExpenseState.confirming_ml_category)
async def quick_expense_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer("Отменено")
    await callback.message.answer("❌ Добавление расхода отменено.")


@router.callback_query(F.data.startswith("quick_expense_cat_"), QuickExpenseState.choosing_manual_category)
async def quick_expense_manual_category(callback: CallbackQuery, state: FSMContext) -> None:
    category_name = callback.data.removeprefix("quick_expense_cat_")
    data = await state.get_data()
    user_id = data["quick_expense_user_id"]

    category_id = await TransactionRepository.get_category_id(
        user_id=user_id,
        category_name=category_name,
        type_="expense",
    )

    if not category_id:
        category_id = await TransactionRepository.create_category(
            user_id=user_id,
            category_name=category_name,
            type_="expense",
        )

    suggested_category_id = data.get("quick_expense_category_id") if data.get("quick_expense_has_prediction") else None

    await TransactionRepository.add_transaction(
        user_id=user_id,
        category_id=category_id,
        amount=data["quick_expense_amount"],
        datetime_=datetime.fromisoformat(data["quick_expense_datetime"]),
        type_="expense",
        note=data["quick_expense_note"],
        suggested_category_id=suggested_category_id,
        is_category_accepted=(category_id == suggested_category_id) if suggested_category_id else False,
    )

    await state.clear()
    await callback.answer("Сохранено")
    await callback.message.answer(
        "💸 Расход добавлен\n\n"
        f"<b>Сумма:</b> {data['quick_expense_amount']}\n"
        f"<b>Описание:</b> {data['quick_expense_note']}\n"
        f"<b>Категория:</b> {category_name}\n"
        f"<b>Дата:</b> {data['quick_expense_date_str']}\n"
        f"<b>Время:</b> {data['quick_expense_time_str']} ({data['quick_expense_time_status']})"
    )