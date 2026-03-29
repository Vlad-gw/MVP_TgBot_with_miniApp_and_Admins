from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, date, time, timedelta
from decimal import Decimal, InvalidOperation
from typing import Optional


@dataclass
class ParsedQuickTransaction:
    tx_type: str
    amount: Decimal
    note: str
    tx_date: date
    tx_time: time
    time_provided: bool
    raw_text: str


class QuickParseError(ValueError):
    pass


_DATE_WORDS = {"сегодня", "вчера", "позавчера"}

_TIME_RE = re.compile(r"^(?P<hour>\d{1,2}):(?P<minute>\d{2})$")
_DATE_RE = re.compile(r"^(?P<day>\d{2})\.(?P<month>\d{2})\.(?P<year>\d{4})$")
_AMOUNT_RE = re.compile(r"^(?P<sign>[+-])\s*(?P<amount>\d+(?:[.,]\d{1,2})?)\s*(?P<tail>.*)$")

_SIGN_ONLY_RE = re.compile(r"^[+-]\s*$")
_SIGN_AND_NOT_AMOUNT_RE = re.compile(r"^[+-]\s*[^\d\s].*$")
_SEEMS_LIKE_DATE_RE = re.compile(r"^\d{1,2}\.\d{1,2}\.\d{2,4}$")
_SEEMS_LIKE_TIME_RE = re.compile(r"^\d{1,2}:\d{1,2}$")


def parse_quick_transaction(text: str, now: Optional[datetime] = None) -> ParsedQuickTransaction:
    if now is None:
        now = datetime.now()

    if text is None:
        raise QuickParseError("Пустое сообщение.")

    raw_text = text
    text = " ".join(text.strip().split())

    if not text:
        raise QuickParseError("Пустое сообщение.")

    if _SIGN_ONLY_RE.match(text):
        raise QuickParseError(
            "После знака <b>+</b> или <b>-</b> нужно указать сумму и описание.\n"
            "Пример: <code>-500 бензин сегодня</code>"
        )

    if _SIGN_AND_NOT_AMOUNT_RE.match(text):
        raise QuickParseError(
            "После знака <b>+</b> или <b>-</b> сначала должна идти сумма.\n"
            "Пример: <code>+100000 зарплата вчера 21:21</code>"
        )

    match = _AMOUNT_RE.match(text)
    if not match:
        raise QuickParseError(
            "Неверный формат записи.\n"
            "Сначала укажи <b>+</b> или <b>-</b>, потом сумму и описание.\n"
            "Пример: <code>+100000 зарплата вчера 21:21</code>"
        )

    sign = match.group("sign")
    amount_str = match.group("amount")
    tail = (match.group("tail") or "").strip()

    tx_type = "income" if sign == "+" else "expense"

    try:
        amount = Decimal(amount_str.replace(",", "."))
    except InvalidOperation:
        raise QuickParseError("Не удалось распознать сумму.")

    if amount <= 0:
        raise QuickParseError("Сумма должна быть больше нуля.")

    if not tail:
        op_word = "дохода" if tx_type == "income" else "расхода"
        example = "+100000 зарплата" if tx_type == "income" else "-500 бензин сегодня"
        raise QuickParseError(
            f"Ты указал только сумму, но не написал описание {op_word}.\n"
            f"Пример: <code>{example}</code>"
        )

    tokens = tail.split()

    parsed_time = now.replace(second=0, microsecond=0).time()
    time_provided = False
    parsed_date = now.date()

    if tokens:
        maybe_time = tokens[-1].lower()
        if _looks_like_time(maybe_time):
            parsed_time = _parse_time_token(maybe_time)
            time_provided = True
            tokens.pop()
        elif _seems_like_time(maybe_time):
            raise QuickParseError(
                f"Неверный формат времени: <code>{maybe_time}</code>\n"
                "Используй формат <b>ЧЧ:ММ</b>, например <code>21:21</code>."
            )

    if tokens:
        maybe_date = tokens[-1].lower()
        if maybe_date in _DATE_WORDS or _looks_like_date(maybe_date):
            parsed_date = _parse_date_token(maybe_date, now.date())
            tokens.pop()
        elif _seems_like_date(maybe_date):
            raise QuickParseError(
                f"Неверный формат даты: <code>{maybe_date}</code>\n"
                "Используй формат <b>ДД.ММ.ГГГГ</b>, например <code>03.03.2026</code>."
            )

    note = " ".join(tokens).strip()

    if not note:
        op_word = "дохода" if tx_type == "income" else "расхода"
        example = "+100000 зарплата" if tx_type == "income" else "-500 бензин сегодня"
        raise QuickParseError(
            f"Не удалось распознать описание {op_word}.\n"
            f"Пример: <code>{example}</code>"
        )

    return ParsedQuickTransaction(
        tx_type=tx_type,
        amount=amount,
        note=note,
        tx_date=parsed_date,
        tx_time=parsed_time,
        time_provided=time_provided,
        raw_text=raw_text,
    )


def combine_to_datetime(parsed: ParsedQuickTransaction) -> datetime:
    return datetime.combine(parsed.tx_date, parsed.tx_time)


def _looks_like_time(value: str) -> bool:
    return bool(_TIME_RE.match(value))


def _seems_like_time(value: str) -> bool:
    return bool(_SEEMS_LIKE_TIME_RE.match(value))


def _parse_time_token(value: str) -> time:
    match = _TIME_RE.match(value)
    if not match:
        raise QuickParseError(f"Неверный формат времени: {value}")

    hour = int(match.group("hour"))
    minute = int(match.group("minute"))

    if not (0 <= hour <= 23):
        raise QuickParseError(f"Часы должны быть от 0 до 23: {value}")
    if not (0 <= minute <= 59):
        raise QuickParseError(f"Минуты должны быть от 0 до 59: {value}")

    return time(hour, minute)


def _looks_like_date(value: str) -> bool:
    return bool(_DATE_RE.match(value))


def _seems_like_date(value: str) -> bool:
    return bool(_SEEMS_LIKE_DATE_RE.match(value))


def _parse_date_token(value: str, today: date) -> date:
    value = value.lower()

    if value == "сегодня":
        return today
    if value == "вчера":
        return today - timedelta(days=1)
    if value == "позавчера":
        return today - timedelta(days=2)

    match = _DATE_RE.match(value)
    if not match:
        raise QuickParseError(f"Неверный формат даты: {value}")

    day = int(match.group("day"))
    month = int(match.group("month"))
    year = int(match.group("year"))

    try:
        return date(year, month, day)
    except ValueError:
        raise QuickParseError(f"Некорректная дата: {value}")