from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback
from datetime import datetime
from states.export_states import AnalyticsState
from database.db import db
from services.charts import generate_bar_chart, generate_pie_chart
from utils.keyboards import year_keyboard, main_menu, back_keyboard
import os

router = Router()

# ▶️ Запуск аналитики
@router.message(F.text == "📊 Аналитика")
async def start_analytics(message: Message, state: FSMContext):
    await state.set_state(AnalyticsState.choosing_year)
    await message.answer("📊 Вы вошли в раздел аналитики.\nНажмите 🔙 Назад, чтобы выйти.", reply_markup=back_keyboard())
    await message.answer("Выберите год для анализа:", reply_markup=year_keyboard())

# 📆 Выбор года
@router.callback_query(F.data.startswith("year_"), AnalyticsState.choosing_year)
async def choose_year(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    year = int(callback.data.removeprefix("year_"))
    await state.update_data(year=year)

    user_id = await db.execute(
        "SELECT id FROM users WHERE telegram_id = $1",
        callback.from_user.id,
        fetchval=True
    )

    start_dt = datetime(year, 1, 1)
    end_dt = datetime(year + 1, 1, 1)

    transactions = await db.execute(
        """
        SELECT t.type, c.name, t.amount, t.date
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = $1 AND t.date >= $2 AND t.date < $3
        """,
        user_id, start_dt, end_dt, fetch=True
    )

    if not transactions:
        await callback.message.answer(f"Нет данных за <b>{year}</b> год.")
    else:
        await callback.message.answer(f"📊 <b>Аналитика за {year} год:</b>")

        bar_path = generate_bar_chart(transactions)
        pie_path = generate_pie_chart(transactions)

        await callback.message.answer_photo(FSInputFile(bar_path), caption="📊 Доходы/расходы по месяцам")
        await callback.message.answer_photo(FSInputFile(pie_path), caption="📊 Распределение по категориям")

        os.remove(bar_path)
        os.remove(pie_path)

    await state.set_state(AnalyticsState.choosing_start_date)
    await callback.message.answer(
        "📅 Теперь выберите <b>начальную дату</b> периода:",
        reply_markup=await SimpleCalendar().start_calendar()
    )

# 📅 Выбор начальной даты
@router.callback_query(SimpleCalendarCallback.filter(), AnalyticsState.choosing_start_date)
async def choose_start_date(callback: CallbackQuery, callback_data: SimpleCalendarCallback, state: FSMContext):
    selected, start_date = await SimpleCalendar().process_selection(callback, callback_data)
    if selected:
        await callback.answer()
        await state.update_data(start_date=start_date)
        await state.set_state(AnalyticsState.choosing_end_date)
        await callback.message.answer(
            "📅 Выберите <b>конечную дату</b> периода:",
            reply_markup=await SimpleCalendar().start_calendar()
        )

# 📅 Выбор конечной даты
@router.callback_query(SimpleCalendarCallback.filter(), AnalyticsState.choosing_end_date)
async def choose_end_date(callback: CallbackQuery, callback_data: SimpleCalendarCallback, state: FSMContext):
    selected, end_date = await SimpleCalendar().process_selection(callback, callback_data)
    if selected:
        await callback.answer()
        data = await state.get_data()

        start_dt = datetime.combine(data["start_date"], datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())
        year = data["year"]

        readable_start = data["start_date"].strftime("%d %B %Y")
        readable_end = end_date.strftime("%d %B %Y")
        await callback.message.answer(
            f"📅 <b>Период:</b> с <b>{readable_start}</b> по <b>{readable_end}</b>\n"
            f"🗓 <b>Год:</b> {year}"
        )

        user_id = await db.execute(
            "SELECT id FROM users WHERE telegram_id = $1",
            callback.from_user.id,
            fetchval=True
        )

        transactions = await db.execute(
            """
            SELECT t.type, c.name, t.amount, t.date
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE t.user_id = $1 AND t.date BETWEEN $2 AND $3
            """,
            user_id, start_dt, end_dt, fetch=True
        )

        if not transactions:
            await callback.message.answer("Нет данных за выбранный период.")
            await state.clear()
            return

        bar_path = generate_bar_chart(transactions)
        pie_path = generate_pie_chart(transactions)

        await callback.message.answer_photo(FSInputFile(bar_path), caption="📊 Доходы/расходы по дням")
        await callback.message.answer_photo(FSInputFile(pie_path), caption="📊 Распределение расходов по категориям")

        os.remove(bar_path)
        os.remove(pie_path)
        await state.clear()

# 🔙 Обработка кнопки "Назад"
@router.message(F.text == "🔙 Назад")
async def go_back_from_analytics(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🔁 Главное меню:", reply_markup=main_menu())
