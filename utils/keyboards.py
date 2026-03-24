# utils/keyboards.py

import os
from datetime import datetime
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
)


# =========================
# MINI APP URL
# =========================

def _get_mini_app_url() -> str:
    base_url = os.getenv("MINI_APP_URL", "").strip().rstrip("/")
    if not base_url:
        base_url = os.getenv("SITE_URL", "http://127.0.0.1:8000").strip().rstrip("/")
    return f"{base_url}/miniapp/"


def _is_https_url(url: str) -> bool:
    return url.startswith("https://")


# =========================
# ГЛАВНОЕ МЕНЮ
# =========================

def main_menu() -> ReplyKeyboardMarkup:
    keyboard_rows = [
        [
            KeyboardButton(text="💰 Баланс"),
            KeyboardButton(text="📜 Последние операции"),
        ],
        [
            KeyboardButton(text="📥 Импорт выписки"),
            KeyboardButton(text="📁 Экспорт в Excel"),
        ],
        [
            KeyboardButton(text="📱 Открыть Mini App"),
            KeyboardButton(text="⚙️ Настройки"),
        ],
    ]

    return ReplyKeyboardMarkup(
        keyboard=keyboard_rows,
        resize_keyboard=True,
        input_field_placeholder="Например: +100000 зарплата вчера 21:21 или -500 бензин сегодня",
    )


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


def back_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True,
    )


# =========================
# MINI APP
# =========================

def mini_app_inline_keyboard() -> InlineKeyboardMarkup:
    mini_app_url = _get_mini_app_url()

    if _is_https_url(mini_app_url):
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📱 Открыть Mini App",
                        web_app=WebAppInfo(url=mini_app_url),
                    )
                ]
            ]
        )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⚠️ Mini App требует HTTPS",
                    callback_data="miniapp_https_required",
                )
            ]
        ]
    )


# =========================
# ВСПОМОГАТЕЛЬНЫЕ КЛАВИАТУРЫ
# НУЖНЫ ДЛЯ СОВМЕСТИМОСТИ СО СТАРЫМИ HANDLERS
# =========================

def skip_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏭ Пропустить")],
            [KeyboardButton(text="🔙 Назад")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def confirm_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Подтвердить")],
            [KeyboardButton(text="❌ Отмена")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def yes_no_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Да"), KeyboardButton(text="❌ Нет")],
            [KeyboardButton(text="🔙 Назад")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def month_keyboard(year: int | None = None) -> InlineKeyboardMarkup:
    current_year = datetime.now().year
    current_month = datetime.now().month
    year = year or current_year

    months = [
        ("Янв", 1), ("Фев", 2), ("Мар", 3),
        ("Апр", 4), ("Май", 5), ("Июн", 6),
        ("Июл", 7), ("Авг", 8), ("Сен", 9),
        ("Окт", 10), ("Ноя", 11), ("Дек", 12),
    ]

    rows = []
    row = []

    for label, month_num in months:
        if year > current_year or (year == current_year and month_num > current_month):
            callback_data = f"ignore_month_{year}_{month_num}"
        else:
            callback_data = f"month_{year}_{month_num}"

        row.append(
            InlineKeyboardButton(
                text=label,
                callback_data=callback_data
            )
        )

        if len(row) == 3:
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    rows.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_years")
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def year_keyboard(start_year: int | None = None, end_year: int | None = None) -> InlineKeyboardMarkup:
    now = datetime.now()
    current_year = now.year

    if start_year is None:
        start_year = current_year - 5
    if end_year is None:
        end_year = current_year

    years = list(range(end_year, start_year - 1, -1))

    rows = []
    row = []

    for year in years:
        row.append(
            InlineKeyboardButton(
                text=str(year),
                callback_data=f"year_{year}"
            )
        )
        if len(row) == 3:
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    rows.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def categories_inline_keyboard(categories, prefix: str = "cat") -> InlineKeyboardMarkup:
    rows = []
    for category in categories:
        if isinstance(category, dict):
            cat_id = category.get("id")
            cat_name = category.get("name", "Без названия")
        else:
            cat_id = category["id"]
            cat_name = category["name"]

        rows.append([
            InlineKeyboardButton(
                text=str(cat_name),
                callback_data=f"{prefix}_{cat_id}"
            )
        ])

    rows.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data=f"{prefix}_back")
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def notifications_keyboard(enabled: bool = True) -> ReplyKeyboardMarkup:
    if enabled:
        keyboard = [
            [KeyboardButton(text="⏰ Изменить время")],
            [KeyboardButton(text="🔕 Выключить напоминания")],
            [KeyboardButton(text="🔙 Назад")],
        ]
    else:
        keyboard = [
            [KeyboardButton(text="🔔 Включить напоминания")],
            [KeyboardButton(text="🔙 Назад")],
        ]

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
    )


def export_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 Экспорт за месяц")],
            [KeyboardButton(text="🗓 Экспорт за период")],
            [KeyboardButton(text="📦 Экспорт всех операций")],
            [KeyboardButton(text="🔙 Назад")],
        ],
        resize_keyboard=True,
    )


def import_statement_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📄 Загрузить выписку")],
            [KeyboardButton(text="🔙 Назад")],
        ],
        resize_keyboard=True,
    )