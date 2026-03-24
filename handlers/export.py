# handlers/export.py

from datetime import date

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, FSInputFile

from database.db import db
from services.excel import generate_excel
from states.export_states import ExportState
from utils.keyboards import main_menu, back_keyboard

router = Router()


def export_choice_keyboard():
    return back_keyboard()


async def _get_user_id_by_tg(telegram_id: int):
    return await db.execute(
        "SELECT id FROM users WHERE telegram_id = $1",
        telegram_id,
        fetchval=True,
    )


async def _fetch_transactions_for_all_time(user_id: int):
    return await db.execute(
        """
        SELECT
            t.type,
            COALESCE(c.name, 'Без категории') AS name,
            t.amount,
            t.date,
            t.note
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = $1
        ORDER BY t.date
        """,
        user_id,
        fetch=True,
    )


async def _fetch_transactions_for_month(user_id: int, year: int, month: int):
    start_date = date(year, month, 1)
    end_date = date(year + (month == 12), (month % 12) + 1, 1)

    return await db.execute(
        """
        SELECT
            t.type,
            COALESCE(c.name, 'Без категории') AS name,
            t.amount,
            t.date,
            t.note
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = $1
          AND t.date >= $2
          AND t.date < $3
        ORDER BY t.date
        """,
        user_id,
        start_date,
        end_date,
        fetch=True,
    )


@router.message(F.text == "📁 Экспорт в Excel")
async def start_export(message: Message, state: FSMContext):
    await state.set_state(ExportState.choosing_period_type)
    await message.answer(
        "📁 <b>Экспорт в Excel</b>\n\n"
        "Выбери вариант:\n"
        "1 — выгрузить все транзакции\n"
        "2 — выгрузить за конкретный месяц",
        reply_markup=export_choice_keyboard(),
    )


@router.message(ExportState.choosing_period_type)
async def choose_type(message: Message, state: FSMContext):
    text = (message.text or "").strip()

    if text == "🔙 Назад":
        await state.clear()
        await message.answer(
            "🔁 <b>Главное меню</b>",
            reply_markup=main_menu(),
        )
        return

    user_id = await _get_user_id_by_tg(message.from_user.id)
    if not user_id:
        await state.clear()
        await message.answer(
            "Сначала нажми /start, чтобы зарегистрироваться.",
            reply_markup=main_menu(),
        )
        return

    if text == "1":
        transactions = await _fetch_transactions_for_all_time(user_id)

        if not transactions:
            await state.clear()
            await message.answer(
                "Нет транзакций для экспорта.",
                reply_markup=main_menu(),
            )
            return

        file_path = generate_excel(transactions)
        await message.answer_document(
            FSInputFile(file_path),
            caption="📁 Все транзакции",
        )
        await state.clear()
        await message.answer(
            "Готово. Выгрузка отправлена.",
            reply_markup=main_menu(),
        )
        return

    if text == "2":
        await state.set_state(ExportState.choosing_year)
        await message.answer(
            "Введите год, например: <b>2026</b>",
            reply_markup=back_keyboard(),
        )
        return

    await message.answer(
        "Введите <b>1</b> или <b>2</b>.",
        reply_markup=back_keyboard(),
    )


@router.message(ExportState.choosing_year)
async def choose_year(message: Message, state: FSMContext):
    text = (message.text or "").strip()

    if text == "🔙 Назад":
        await state.set_state(ExportState.choosing_period_type)
        await message.answer(
            "📁 <b>Экспорт в Excel</b>\n\n"
            "Выбери вариант:\n"
            "1 — выгрузить все транзакции\n"
            "2 — выгрузить за конкретный месяц",
            reply_markup=back_keyboard(),
        )
        return

    try:
        year = int(text)
        if year < 2000 or year > 2100:
            raise ValueError
    except ValueError:
        await message.answer(
            "Введите корректный год, например: <b>2026</b>",
            reply_markup=back_keyboard(),
        )
        return

    await state.update_data(year=year)
    await state.set_state(ExportState.choosing_month)
    await message.answer(
        "Введите месяц числом от <b>1</b> до <b>12</b>.\n"
        "Например: <b>3</b> или <b>03</b>",
        reply_markup=back_keyboard(),
    )


@router.message(ExportState.choosing_month)
async def choose_month(message: Message, state: FSMContext):
    text = (message.text or "").strip()

    if text == "🔙 Назад":
        await state.set_state(ExportState.choosing_year)
        await message.answer(
            "Введите год, например: <b>2026</b>",
            reply_markup=back_keyboard(),
        )
        return

    try:
        month = int(text)
        if month < 1 or month > 12:
            raise ValueError
    except ValueError:
        await message.answer(
            "Введите корректный месяц от <b>1</b> до <b>12</b>.",
            reply_markup=back_keyboard(),
        )
        return

    user_id = await _get_user_id_by_tg(message.from_user.id)
    if not user_id:
        await state.clear()
        await message.answer(
            "Сначала нажми /start, чтобы зарегистрироваться.",
            reply_markup=main_menu(),
        )
        return

    data = await state.get_data()
    year = data["year"]

    try:
        transactions = await _fetch_transactions_for_month(user_id, year, month)

        if not transactions:
            await state.clear()
            await message.answer(
                f"Нет транзакций за {month:02d}.{year}.",
                reply_markup=main_menu(),
            )
            return

        file_path = generate_excel(transactions)
        await message.answer_document(
            FSInputFile(file_path),
            caption=f"📁 Транзакции за {month:02d}.{year}",
        )
        await state.clear()
        await message.answer(
            "Готово. Выгрузка отправлена.",
            reply_markup=main_menu(),
        )

    except Exception as e:
        await message.answer(
            f"⚠️ Ошибка при экспорте: {e}",
            reply_markup=back_keyboard(),
        )