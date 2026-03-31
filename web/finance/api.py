from __future__ import annotations

import calendar
import hashlib
import hmac
import json
import os
import re
import sys
from datetime import date, datetime, time as dtime, timedelta
from pathlib import Path

from django.utils import timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from urllib.parse import parse_qsl

from django.db import IntegrityError
from django.db.models import Count, Q, Sum
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from .auth import generate_api_key, get_user_from_request
from .models import Budget, Category, Transaction, TransactionTemplate, User
from .serializers import BudgetSerializer, CategorySerializer, TransactionSerializer, TransactionTemplateSerializer

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.ml_forecast import linear_regression_forecast


# ============================================================================
# Common helpers
# ============================================================================

RUS_MONTHS = {
    "янв": 1,
    "фев": 2,
    "мар": 3,
    "апр": 4,
    "мая": 5,
    "май": 5,
    "июн": 6,
    "июл": 7,
    "авг": 8,
    "сен": 9,
    "сент": 9,
    "окт": 10,
    "ноя": 11,
    "дек": 12,
}

QUICK_ADD_TIME_RE = re.compile(r"(?<!\d)(\d{1,2}):(\d{2})(?!\d)")
QUICK_ADD_SIGNED_AMOUNT_RE = re.compile(
    r"^\s*([+-])\s*([0-9]+(?:[.,][0-9]{1,2})?)\s*(.*)$",
    flags=re.UNICODE,
)


@api_view(["GET"])
def health(_request: Request) -> Response:
    return Response({"ok": True})


def _parse_date(s: str):
    return datetime.strptime(s, "%Y-%m-%d").date()


def _parse_month_value(value: str | None) -> date:
    if not value:
        today = datetime.now().date()
        return date(today.year, today.month, 1)

    raw = str(value).strip()

    try:
        if len(raw) == 7:
            parsed = datetime.strptime(raw, "%Y-%m").date()
            return date(parsed.year, parsed.month, 1)

        parsed = datetime.strptime(raw, "%Y-%m-%d").date()
        return date(parsed.year, parsed.month, 1)
    except ValueError as exc:
        raise ValueError("Некорректный month. Используй YYYY-MM или YYYY-MM-DD") from exc


def _month_bounds(month_value: date) -> tuple[datetime, datetime]:
    start_dt = datetime.combine(month_value, dtime.min)

    if month_value.month == 12:
        next_month = date(month_value.year + 1, 1, 1)
    else:
        next_month = date(month_value.year, month_value.month + 1, 1)

    end_dt = datetime.combine(next_month, dtime.min)
    return start_dt, end_dt


def _add_months(month_value: date, months: int) -> date:
    y = month_value.year + (month_value.month - 1 + months) // 12
    m = (month_value.month - 1 + months) % 12 + 1
    return date(y, m, 1)


def _parse_datetime_value(value: str | None) -> datetime:
    if not value:
        raise ValueError("Поле date обязательно")

    raw = str(value).strip()
    normalized = raw.replace(" ", "T")

    try:
        return datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(
            "Некорректная дата. Используй формат YYYY-MM-DDTHH:MM или YYYY-MM-DD HH:MM"
        ) from exc


def _parse_amount_value(value) -> Decimal:
    if value is None or str(value).strip() == "":
        raise ValueError("Поле amount обязательно")

    raw = str(value).strip().replace(",", ".")

    try:
        amount = Decimal(raw)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Некорректная сумма") from exc

    if amount <= 0:
        raise ValueError("Сумма должна быть больше 0")

    return amount.quantize(Decimal("0.01"))


def _to_decimal(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value or 0))


def _money_str(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return _to_decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP).__str__()


def _month_label(month_value: date) -> str:
    return f"{month_value.year}-{month_value.month:02d}"


def _get_category_for_user(
    user: User,
    category_id,
    tx_type: str,
) -> Category | None:
    if category_id in (None, "", 0, "0"):
        return None

    try:
        category_id_int = int(category_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("Некорректный category_id") from exc

    category = Category.objects.filter(
        id=category_id_int,
        user=user,
    ).first()

    if not category:
        raise ValueError("Категория не найдена")

    if category.type != tx_type:
        raise ValueError("Категория не соответствует типу транзакции")

    return category


def _get_expense_category_for_user(user: User, category_id) -> Category:
    try:
        category_id_int = int(category_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("Некорректный category_id") from exc

    category = Category.objects.filter(
        id=category_id_int,
        user=user,
        type="expense",
    ).first()

    if not category:
        raise ValueError("Категория расходов не найдена")

    return category


def _serialize_transaction(tx: Transaction) -> dict:
    return TransactionSerializer(tx).data


def _get_template_for_user(user: User, template_id) -> TransactionTemplate:
    try:
        template_id_int = int(template_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("Некорректный template_id") from exc

    template = TransactionTemplate.objects.filter(
        id=template_id_int,
        user=user,
    ).select_related("category").first()

    if not template:
        raise ValueError("Шаблон не найден")

    return template


def _category_delta_rows(current_breakdown: list[dict], prev_breakdown: list[dict]) -> list[dict]:
    prev_map = {item["category_id"]: _to_decimal(item["amount"]) for item in prev_breakdown}
    rows = []
    for item in current_breakdown:
        current_amount = _to_decimal(item["amount"])
        prev_amount = prev_map.get(item["category_id"], Decimal("0"))
        delta_amount = current_amount - prev_amount
        delta_percent = _pct_change(current_amount, prev_amount)
        rows.append(
            {
                "category_id": item["category_id"],
                "category_name": item["category_name"],
                "current_amount": _money_str(current_amount),
                "previous_amount": _money_str(prev_amount),
                "delta_amount": _money_str(delta_amount),
                "delta_percent": _money_str(delta_percent),
            }
        )
    rows.sort(key=lambda x: abs(_to_decimal(x["delta_amount"])), reverse=True)
    return rows


def _top_spending_day(daily_rows: list[dict]) -> dict | None:
    if not daily_rows:
        return None
    best = max(daily_rows, key=lambda item: _to_decimal(item["amount"]))
    return {
        "date": best["date"],
        "amount": best["amount"],
    }


def _average_expense_check(qs) -> Decimal:
    expense_qs = qs.filter(type="expense")
    agg = expense_qs.aggregate(total=Sum("amount"), count=Count("id"))
    total = agg["total"] or Decimal("0")
    count = agg["count"] or 0
    if count <= 0:
        return Decimal("0")
    return (Decimal(str(total)) / Decimal(count)).quantize(Decimal("0.01"))


def _serialize_budget(user: User, budget: Budget) -> dict:
    data = BudgetSerializer(budget).data

    start_dt, end_dt = _month_bounds(budget.month)

    spent = (
        Transaction.objects.filter(
            user=user,
            type="expense",
            category_id=budget.category_id,
            date__gte=start_dt,
            date__lt=end_dt,
        ).aggregate(s=Sum("amount"))["s"]
        or Decimal("0")
    )

    limit_amount = Decimal(str(budget.limit_amount))
    remaining = limit_amount - spent

    if limit_amount > 0:
        usage_percent = (spent / limit_amount) * Decimal("100")
    else:
        usage_percent = Decimal("0")

    usage_percent = usage_percent.quantize(Decimal("0.01"))

    if spent > limit_amount:
        status_value = "exceeded"
        status_label = "Превышен"
    elif usage_percent >= Decimal("80.00"):
        status_value = "warning"
        status_label = "Почти исчерпан"
    else:
        status_value = "normal"
        status_label = "Норма"

    data.update(
        {
            "spent_amount": _money_str(spent),
            "remaining_amount": _money_str(remaining),
            "usage_percent": _money_str(usage_percent),
            "status": status_value,
            "status_label": status_label,
        }
    )
    return data


# ============================================================================
# Telegram mini app auth
# ============================================================================

def _build_check_string(init_data_raw: str) -> tuple[str, str]:
    pairs = parse_qsl(init_data_raw, keep_blank_values=True)

    data = []
    received_hash = None

    for key, value in pairs:
        if key == "hash":
            received_hash = value
        else:
            data.append((key, value))

    data.sort(key=lambda item: item[0])
    check_string = "\n".join(f"{key}={value}" for key, value in data)

    return check_string, received_hash or ""


def _validate_telegram_init_data(init_data_raw: str, bot_token: str) -> dict | None:
    if not init_data_raw or not bot_token:
        return None

    check_string, received_hash = _build_check_string(init_data_raw)
    if not received_hash:
        return None

    secret_key = hmac.new(
        key=b"WebAppData",
        msg=bot_token.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()

    calculated_hash = hmac.new(
        key=secret_key,
        msg=check_string.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        return None

    parsed = dict(parse_qsl(init_data_raw, keep_blank_values=True))
    user_raw = parsed.get("user")
    if not user_raw:
        return None

    try:
        return json.loads(user_raw)
    except json.JSONDecodeError:
        return None


# ============================================================================
# Transaction filtering / analytics
# ============================================================================

def _filtered_transactions_queryset(request: Request, user: User):
    qs = Transaction.objects.filter(user=user).select_related("category", "suggested_category")

    tx_type = request.query_params.get("type")
    if tx_type in ("income", "expense"):
        qs = qs.filter(type=tx_type)

    category_id = request.query_params.get("category_id")
    if category_id:
        try:
            qs = qs.filter(category_id=int(category_id))
        except ValueError as exc:
            raise ValueError("Некорректный category_id") from exc

    date_from = request.query_params.get("from")
    date_to = request.query_params.get("to")
    search = (request.query_params.get("q") or "").strip()

    if date_from:
        try:
            d1 = _parse_date(date_from)
            qs = qs.filter(date__gte=datetime.combine(d1, dtime.min))
        except ValueError as exc:
            raise ValueError("Некорректный параметр from. Ожидается YYYY-MM-DD") from exc

    if date_to:
        try:
            d2 = _parse_date(date_to)
            qs = qs.filter(date__lte=datetime.combine(d2, dtime.max))
        except ValueError as exc:
            raise ValueError("Некорректный параметр to. Ожидается YYYY-MM-DD") from exc

    if search:
        qs = qs.filter(Q(note__icontains=search) | Q(category__name__icontains=search))

    return qs


def _get_period_summary(qs) -> tuple[Decimal, Decimal, Decimal, int]:
    income = qs.filter(type="income").aggregate(s=Sum("amount"))["s"] or Decimal("0")
    expense = qs.filter(type="expense").aggregate(s=Sum("amount"))["s"] or Decimal("0")
    balance = income - expense
    return income, expense, balance, qs.count()


def _get_previous_period_bounds(date_from: date | None, date_to: date | None) -> tuple[datetime, datetime] | None:
    if not date_from and not date_to:
        today = datetime.now().date()
        current_from = today.replace(day=1)
        current_to = today
    elif date_from and date_to:
        current_from = date_from
        current_to = date_to
    elif date_from:
        current_from = date_from
        current_to = datetime.now().date()
    else:
        current_to = date_to
        current_from = current_to.replace(day=1)

    days = (current_to - current_from).days + 1
    if days <= 0:
        return None

    prev_to = current_from - timedelta(days=1)
    prev_from = prev_to - timedelta(days=days - 1)
    return datetime.combine(prev_from, dtime.min), datetime.combine(prev_to, dtime.max)


def _category_expense_breakdown(qs):
    expense_qs = qs.filter(type="expense")
    total = expense_qs.aggregate(s=Sum("amount"))["s"] or Decimal("0")
    rows = []

    grouped = (
        expense_qs.values("category_id", "category__name")
        .annotate(total=Sum("amount"))
        .order_by("-total", "category__name")
    )

    for item in grouped:
        amount = _to_decimal(item["total"])
        percent = Decimal("0")
        if total > 0:
            percent = ((amount / total) * Decimal("100")).quantize(Decimal("0.01"))

        rows.append(
            {
                "category_id": item["category_id"],
                "category_name": item["category__name"] or "Без категории",
                "amount": _money_str(amount),
                "percent": _money_str(percent),
            }
        )

    return rows


def _daily_expense_series(qs):
    grouped = (
        qs.filter(type="expense")
        .values("date__date")
        .annotate(total=Sum("amount"))
        .order_by("date__date")
    )

    return [
        {
            "date": item["date__date"].isoformat(),
            "amount": _money_str(item["total"] or Decimal("0")),
        }
        for item in grouped
    ]


def _monthly_series(user: User, months: int = 6):
    current_month = date.today().replace(day=1)
    start_month = _add_months(current_month, -(months - 1))
    start_dt = datetime.combine(start_month, dtime.min)

    qs = Transaction.objects.filter(user=user, date__gte=start_dt)
    grouped = (
        qs.values("date__year", "date__month", "type")
        .annotate(total=Sum("amount"))
        .order_by("date__year", "date__month", "type")
    )

    buckets: dict[str, dict] = {}
    for i in range(months):
        month = _add_months(start_month, i)
        label = _month_label(month)
        buckets[label] = {
            "month": label,
            "income": Decimal("0"),
            "expense": Decimal("0"),
        }

    for item in grouped:
        month = date(int(item["date__year"]), int(item["date__month"]), 1)
        label = _month_label(month)
        if label not in buckets:
            continue
        buckets[label][item["type"]] = _to_decimal(item["total"])

    rows = []
    for label in sorted(buckets.keys()):
        bucket = buckets[label]
        rows.append(
            {
                "month": label,
                "income": _money_str(bucket["income"]),
                "expense": _money_str(bucket["expense"]),
                "balance": _money_str(bucket["income"] - bucket["expense"]),
            }
        )
    return rows


def _weighted_forecast(values: list[Decimal]) -> Decimal:
    m = values[-3:]
    if not m:
        return Decimal("0")
    if len(m) == 1:
        return m[0]
    if len(m) == 2:
        return m[0] * Decimal("0.4") + m[1] * Decimal("0.6")
    return m[0] * Decimal("0.2") + m[1] * Decimal("0.3") + m[2] * Decimal("0.5")


def _median(values: list[Decimal]) -> Decimal:
    if not values:
        return Decimal("0")
    values = sorted(values)
    n = len(values)
    mid = n // 2
    if n % 2:
        return values[mid]
    return (values[mid - 1] + values[mid]) / Decimal("2")


def _robust_interval(history: list[Decimal], point: Decimal) -> tuple[Decimal, Decimal]:
    if not history:
        return Decimal("0"), Decimal("0")

    med = _median(history)
    mad = _median([abs(v - med) for v in history])
    sigma = mad * Decimal("1.4826")

    if sigma == 0 and point > 0:
        sigma = point * Decimal("0.1")

    low = max(Decimal("0"), point - sigma)
    high = point + sigma

    if point > 0:
        low = max(low, point * Decimal("0.7"))
        high = min(high, point * Decimal("1.3"))

    return low, high


def _pct_change(current: Decimal, previous: Decimal) -> Decimal | None:
    if previous == 0:
        return None
    return (((current - previous) / previous) * Decimal("100")).quantize(Decimal("0.01"))


def _expense_forecast_payload(user: User) -> dict:
    current_month = date.today().replace(day=1)
    full_months = [_add_months(current_month, -i) for i in range(1, 7)]
    full_months = list(sorted(full_months))

    history = []
    history_values: list[Decimal] = []
    for month_value in full_months:
        start_dt, end_dt = _month_bounds(month_value)
        total = (
            Transaction.objects.filter(
                user=user,
                type="expense",
                date__gte=start_dt,
                date__lt=end_dt,
            ).aggregate(s=Sum("amount"))["s"]
            or Decimal("0")
        )
        total_dec = _to_decimal(total)
        history_values.append(total_dec)
        history.append({"month": _month_label(month_value), "amount": _money_str(total_dec)})

    non_zero_history = [value for value in history_values if value > 0]
    if len(non_zero_history) < 2:
        return {
            "ok": False,
            "detail": "Недостаточно данных для прогноза. Нужны минимум 2 полных месяца расходов.",
            "history": history,
            "ml": {
                "enabled": False,
                "reason": "not_enough_data",
            },
        }

    ml_res = linear_regression_forecast(non_zero_history)
    ml_point = _to_decimal(ml_res.predicted)
    baseline_point = _weighted_forecast(non_zero_history)

    if ml_point <= 0:
        ml_point = Decimal("0")

    point = ml_point if ml_point > 0 else baseline_point
    low, high = _robust_interval(non_zero_history[-6:], point)

    last = non_zero_history[-1]
    prev = non_zero_history[-2]
    trend_pct = _pct_change(last, prev)

    last_month = _add_months(current_month, -1)
    last_start_dt, last_end_dt = _month_bounds(last_month)
    grouped = (
        Transaction.objects.filter(
            user=user,
            type="expense",
            date__gte=last_start_dt,
            date__lt=last_end_dt,
        )
        .values("category_id", "category__name")
        .annotate(total=Sum("amount"))
        .order_by("-total", "category__name")
    )

    top_category = None
    grouped_list = list(grouped)
    if grouped_list:
        total_last = sum(_to_decimal(item["total"]) for item in grouped_list)
        first = grouped_list[0]
        share = Decimal("0")
        if total_last > 0:
            share = ((_to_decimal(first["total"]) / total_last) * Decimal("100")).quantize(Decimal("0.01"))

        top_category = {
            "category_id": first["category_id"],
            "category_name": first["category__name"] or "Без категории",
            "amount": _money_str(first["total"] or Decimal("0")),
            "share_percent": _money_str(share),
            "month": _month_label(last_month),
        }

    confidence = "unknown"
    if ml_res.r2 is None:
        confidence = "unknown"
    elif ml_res.r2 < Decimal("0.20"):
        confidence = "low"
    elif ml_res.r2 < Decimal("0.50"):
        confidence = "medium"
    else:
        confidence = "high"

    use_ml = confidence in {"medium", "high"} and ml_point > 0
    point = ml_point if use_ml else baseline_point
    low, high = _robust_interval(non_zero_history[-6:], point)

    if trend_pct is None:
        trend_direction = "unknown"
    elif trend_pct > Decimal("10"):
        trend_direction = "up_fast"
    elif trend_pct > Decimal("3"):
        trend_direction = "up"
    elif trend_pct < Decimal("-10"):
        trend_direction = "down_fast"
    elif trend_pct < Decimal("-3"):
        trend_direction = "down"
    else:
        trend_direction = "stable"

    forecast_method = "ml" if use_ml else "baseline"
    forecast_method_title = "Умный прогноз" if use_ml else "Надёжный расчёт"

    if use_ml:
        method_description = (
            "Прогноз рассчитан по вашей истории расходов. Последние месяцы ведут себя достаточно "
            "стабильно, поэтому здесь используется более точный умный расчёт."
        )
        if trend_direction in {"up_fast", "up"}:
            method_tip = "Есть признаки роста расходов. Лучше заранее оставить запас в бюджете."
        elif trend_direction in {"down_fast", "down"}:
            method_tip = "Расходы снижаются. Есть шанс уложиться в меньшую сумму, чем обычно."
        else:
            method_tip = "Траты выглядят достаточно ровными. На такой прогноз можно ориентироваться при планировании."
    else:
        method_description = (
            "Умный прогноз был проверен, но его уверенность пока недостаточна. Поэтому итоговая сумма "
            "сейчас считается надёжным базовым способом — по предыдущим месяцам."
        )
        method_tip = "Когда накопится больше стабильной истории расходов, прогноз станет точнее."

    if trend_direction in {"up_fast", "up"}:
        trend_user_note = "Расходы растут относительно прошлого месяца."
    elif trend_direction in {"down_fast", "down"}:
        trend_user_note = "Расходы снижаются относительно прошлого месяца."
    elif trend_direction == "stable":
        trend_user_note = "Расходы остаются примерно на одном уровне."
    else:
        trend_user_note = "Пока недостаточно данных, чтобы уверенно оценить динамику."

    return {
        "ok": True,
        "history": history,
        "forecast": {
            "next_month": _month_label(_add_months(current_month, 1)),
            "predicted_amount": _money_str(point),
            "low_amount": _money_str(low),
            "high_amount": _money_str(high),
            "trend_percent": _money_str(trend_pct),
            "last_month_amount": _money_str(last),
            "previous_month_amount": _money_str(prev),
            "method": forecast_method,
            "trend_direction": trend_direction,
            "trend_user_note": trend_user_note,
        },
        "ml": {
            "enabled": True,
            "used_for_result": use_ml,
            "model_name": ml_res.model_name,
            "r2": _money_str(ml_res.r2),
            "slope": _money_str(ml_res.slope),
            "intercept": _money_str(ml_res.intercept),
            "confidence": confidence,
            "history_months_used": len(non_zero_history),
            "method_title": forecast_method_title,
            "method_description": method_description,
            "method_tip": method_tip,
            "fallback_reason": "low_confidence" if not use_ml else None,
        },
        "top_category": top_category,
    }


def _insights_payload(user: User, month_value: date) -> dict:
    start_dt, end_dt = _month_bounds(month_value)
    today = datetime.now().date()
    days_in_month = calendar.monthrange(month_value.year, month_value.month)[1]

    spent = (
        Transaction.objects.filter(
            user=user,
            type="expense",
            date__gte=start_dt,
            date__lt=end_dt,
        ).aggregate(s=Sum("amount"))["s"]
        or Decimal("0")
    )

    income = (
        Transaction.objects.filter(
            user=user,
            type="income",
            date__gte=start_dt,
            date__lt=end_dt,
        ).aggregate(s=Sum("amount"))["s"]
        or Decimal("0")
    )

    total_limit = (
        Budget.objects.filter(user=user, month=month_value).aggregate(s=Sum("limit_amount"))["s"]
        or Decimal("0")
    )

    day_number = 1
    remaining_days = days_in_month

    if month_value.year == today.year and month_value.month == today.month:
        day_number = today.day
        remaining_days = max(days_in_month - today.day, 0)
    elif month_value < today.replace(day=1):
        day_number = days_in_month
        remaining_days = 0

    avg_per_day = spent / Decimal(day_number) if day_number > 0 else Decimal("0")

    safe_daily_limit = Decimal("0")
    if total_limit > 0:
        safe_daily_limit = max(total_limit - spent, Decimal("0"))
        safe_daily_limit = (safe_daily_limit / Decimal(max(remaining_days, 1))) if remaining_days > 0 else safe_daily_limit

    budget_status = "no_budget"
    if total_limit > 0:
        if spent > total_limit:
            budget_status = "exceeded"
        elif ((spent / total_limit) * Decimal("100")) >= Decimal("80"):
            budget_status = "warning"
        else:
            budget_status = "normal"

    return {
        "month": _month_label(month_value),
        "days_in_month": days_in_month,
        "days_passed": day_number,
        "days_remaining": remaining_days,
        "spent_amount": _money_str(spent),
        "income_amount": _money_str(income),
        "budget_limit": _money_str(total_limit),
        "average_daily_expense": _money_str(avg_per_day),
        "safe_daily_limit": _money_str(safe_daily_limit),
        "budget_status": budget_status,
    }


# ============================================================================
# Quick Add helpers
# ============================================================================

def _normalize_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def _extract_time_fragment(value: str) -> tuple[dtime | None, str]:
    match = QUICK_ADD_TIME_RE.search(value)
    if not match:
        return None, value

    hh = int(match.group(1))
    mm = int(match.group(2))

    if hh > 23 or mm > 59:
        raise ValueError("Некорректное время в быстром вводе")

    parsed_time = dtime(hour=hh, minute=mm)
    remaining = (value[: match.start()] + " " + value[match.end() :]).strip()
    return parsed_time, _normalize_spaces(remaining)


def _extract_date_fragment(value: str) -> tuple[date | None, str]:
    text = f" {value.strip()} "
    today = datetime.now().date()

    replacements = [
        (r"\sсегодня\s", today),
        (r"\sвчера\s", today - timedelta(days=1)),
        (r"\sпозавчера\s", today - timedelta(days=2)),
    ]

    for pattern, parsed in replacements:
        if re.search(pattern, text, flags=re.IGNORECASE):
            cleaned = re.sub(pattern, " ", text, flags=re.IGNORECASE).strip()
            return parsed, _normalize_spaces(cleaned)

    m = re.search(r"(?<!\d)(\d{1,2})\.(\d{1,2})(?:\.(\d{2,4}))?(?!\d)", text)
    if m:
        dd = int(m.group(1))
        mm = int(m.group(2))
        yy_raw = m.group(3)
        year = today.year
        if yy_raw:
            year = int(yy_raw)
            if year < 100:
                year += 2000
        parsed = date(year, mm, dd)
        cleaned = (text[: m.start()] + " " + text[m.end() :]).strip()
        return parsed, _normalize_spaces(cleaned)

    month_alt = "|".join(sorted(RUS_MONTHS.keys(), key=len, reverse=True))
    m = re.search(rf"(?<!\d)(\d{{1,2}})\s+({month_alt})(?:\s+(\d{{4}}))?(?!\d)", text, flags=re.IGNORECASE)
    if m:
        dd = int(m.group(1))
        month_key = m.group(2).lower()
        year = int(m.group(3)) if m.group(3) else today.year
        parsed = date(year, RUS_MONTHS[month_key], dd)
        cleaned = (text[: m.start()] + " " + text[m.end() :]).strip()
        return parsed, _normalize_spaces(cleaned)

    return None, _normalize_spaces(value)


def _guess_category(user: User, tx_type: str, note: str, amount: Decimal | None) -> tuple[Category | None, list[dict]]:
    text = (note or "").lower()

    categories = list(Category.objects.filter(user=user, type=tx_type).order_by("name"))
    if not categories:
        return None, []

    keyword_map = {
        "expense": {
            "еда": ["еда", "продукт", "магазин", "пятерочка", "магнит", "перекресток", "вкусвилл", "кофе", "кафе", "ресторан", "обед", "ужин", "завтрак"],
            "транспорт": ["такси", "метро", "автобус", "бензин", "заправка", "транспорт", "дорога", "uber", "yandex go"],
            "дом": ["квартира", "аренда", "жкх", "коммун", "свет", "вода", "газ", "интернет", "ремонт"],
            "здоровье": ["аптека", "лекар", "врач", "анализ", "здоров", "стомат", "мед"],
            "развлечения": ["кино", "игра", "подписка", "netflix", "spotify", "развлеч", "досуг"],
            "покупки": ["одеж", "обув", "wildberries", "ozon", "маркет", "покупк", "товар"],
        },
        "income": {
            "зарплата": ["зарплата", "аванс", "salary", "оклад"],
            "перевод": ["перевод", "возврат", "вернули", "долг", "поступление"],
            "подарок": ["подарок", "донат", "бонус"],
        },
    }

    candidates: list[tuple[int, Category]] = []
    rules = keyword_map.get(tx_type, {})

    for category in categories:
        score = 0
        category_name = (category.name or "").lower()

        if category_name in text:
            score += 120

        for rule_name, words in rules.items():
            if rule_name in category_name:
                for word in words:
                    if word in text:
                        score += 20

        for part in re.split(r"[\s/_-]+", category_name):
            part = part.strip()
            if len(part) >= 3 and part in text:
                score += 15

        if amount is not None and tx_type == "expense":
            if amount <= Decimal("300") and any(w in category_name for w in ["кофе", "еда", "кафе"]):
                score += 5
            if amount >= Decimal("3000") and any(w in category_name for w in ["дом", "арен", "жкх"]):
                score += 5

        if score > 0:
            candidates.append((score, category))

    candidates.sort(key=lambda x: (-x[0], x[1].name.lower()))

    top = []
    for score, category in candidates[:3]:
        top.append(
            {
                "id": category.id,
                "name": category.name,
                "score": score,
            }
        )

    suggested = candidates[0][1] if candidates else None
    return suggested, top


def _parse_quick_add_input(raw_text: str) -> dict:
    text = _normalize_spaces(raw_text)
    if not text:
        raise ValueError("Пустая строка быстрого ввода")

    amount_match = QUICK_ADD_SIGNED_AMOUNT_RE.match(text)
    if not amount_match:
        raise ValueError("Используй формат вроде: -500 кофе сегодня 14:30 или +30000 зарплата")

    sign = amount_match.group(1)
    amount_raw = amount_match.group(2)
    rest = _normalize_spaces(amount_match.group(3))

    tx_type = "income" if sign == "+" else "expense"
    amount = _parse_amount_value(amount_raw)

    parsed_time, rest = _extract_time_fragment(rest)
    parsed_date, rest = _extract_date_fragment(rest)

    note = _normalize_spaces(rest)
    if not note:
        note = None

    final_date = parsed_date or datetime.now().date()
    final_time = parsed_time or datetime.now().time().replace(second=0, microsecond=0)

    return {
        "type": tx_type,
        "amount": amount,
        "date": datetime.combine(final_date, final_time),
        "note": note,
        "raw_text": raw_text,
        "parsed_date": final_date.isoformat(),
        "parsed_time": final_time.strftime("%H:%M"),
    }


def _quick_add_payload(user: User, raw_text: str) -> dict:
    parsed = _parse_quick_add_input(raw_text)
    suggested_category, top_categories = _guess_category(
        user=user,
        tx_type=parsed["type"],
        note=parsed["note"] or "",
        amount=parsed["amount"],
    )

    return {
        "raw_text": parsed["raw_text"],
        "type": parsed["type"],
        "amount": _money_str(parsed["amount"]),
        "date": parsed["date"].isoformat(timespec="minutes"),
        "parsed_date": parsed["parsed_date"],
        "parsed_time": parsed["parsed_time"],
        "note": parsed["note"],
        "suggested_category_id": suggested_category.id if suggested_category else None,
        "suggested_category_name": suggested_category.name if suggested_category else None,
        "category_candidates": top_categories,
    }


# ============================================================================
# API views
# ============================================================================

@api_view(["POST"])
def miniapp_auth(request: Request) -> Response:
    init_data = (request.data.get("initData") or "").strip()
    bot_token = os.getenv("BOT_TOKEN", "").strip()

    if not init_data:
        return Response(
            {"detail": "Missing initData"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not bot_token:
        return Response(
            {"detail": "BOT_TOKEN is not configured on server"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    tg_user = _validate_telegram_init_data(init_data, bot_token)
    if not tg_user:
        return Response(
            {"detail": "Invalid Telegram initData"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    telegram_id = tg_user.get("id")
    if not telegram_id:
        return Response(
            {"detail": "Telegram user id not found"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    username = tg_user.get("username")
    first_name = tg_user.get("first_name")

    user = User.objects.filter(telegram_id=telegram_id).first()

    if not user:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
        )

    changed = False

    if username and user.username != username:
        user.username = username
        changed = True

    if first_name and user.first_name != first_name:
        user.first_name = first_name
        changed = True

    if not getattr(user, "api_key", None):
        user.api_key = generate_api_key()
        changed = True

    if changed or not user.pk:
        user.save()

    return Response(
        {
            "api_key": user.api_key,
            "user_id": user.id,
            "telegram_id": user.telegram_id,
            "username": user.username,
            "first_name": user.first_name,
        }
    )


@api_view(["GET"])
def me(request: Request) -> Response:
    user = get_user_from_request(request)
    return Response(
        {
            "id": user.id,
            "telegram_id": user.telegram_id,
            "username": user.username,
            "first_name": user.first_name,
            "created_at": user.created_at,
        }
    )


@api_view(["GET", "POST"])
def categories(request: Request) -> Response:
    user = get_user_from_request(request)

    if request.method == "GET":
        tx_type = request.query_params.get("type")
        qs = Category.objects.filter(user=user).order_by("type", "name", "id")

        if tx_type in ("income", "expense"):
            qs = qs.filter(type=tx_type)

        return Response(CategorySerializer(qs, many=True).data)

    name = (request.data.get("name") or "").strip()
    tx_type = (request.data.get("type") or "").strip()

    if not name:
        return Response({"detail": "Название категории обязательно"}, status=status.HTTP_400_BAD_REQUEST)

    if tx_type not in ("income", "expense"):
        return Response({"detail": "Поле type должно быть income или expense"}, status=status.HTTP_400_BAD_REQUEST)

    duplicate = Category.objects.filter(user=user, type=tx_type, name__iexact=name).first()
    if duplicate:
        return Response({"detail": "Категория с таким названием уже существует"}, status=status.HTTP_400_BAD_REQUEST)

    category = Category.objects.create(user=user, name=name, type=tx_type)
    return Response(CategorySerializer(category).data, status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH", "DELETE"])
def category_detail(request: Request, category_id: int) -> Response:
    user = get_user_from_request(request)
    category = Category.objects.filter(id=category_id, user=user).first()

    if not category:
        return Response({"detail": "Категория не найдена"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        return Response(CategorySerializer(category).data)

    if request.method == "DELETE":
        category.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    name = (request.data.get("name", category.name) or "").strip()
    tx_type = (request.data.get("type", category.type) or "").strip()

    if not name:
        return Response({"detail": "Название категории обязательно"}, status=status.HTTP_400_BAD_REQUEST)
    if tx_type not in ("income", "expense"):
        return Response({"detail": "Поле type должно быть income или expense"}, status=status.HTTP_400_BAD_REQUEST)

    duplicate = Category.objects.filter(user=user, type=tx_type, name__iexact=name).exclude(id=category.id).first()
    if duplicate:
        return Response({"detail": "Категория с таким названием уже существует"}, status=status.HTTP_400_BAD_REQUEST)

    category.name = name
    category.type = tx_type
    category.save(update_fields=["name", "type"])
    return Response(CategorySerializer(category).data)


@api_view(["GET", "POST"])
def templates(request: Request) -> Response:
    user = get_user_from_request(request)

    if request.method == "GET":
        tx_type = request.query_params.get("type")
        qs = TransactionTemplate.objects.filter(user=user).select_related("category").order_by("-usage_count", "-last_used_at", "name", "id")
        if tx_type in ("income", "expense"):
            qs = qs.filter(type=tx_type)
        return Response(TransactionTemplateSerializer(qs, many=True).data)

    name = (request.data.get("name") or "").strip()
    tx_type = (request.data.get("type") or "").strip()
    if not name:
        return Response({"detail": "Название шаблона обязательно"}, status=status.HTTP_400_BAD_REQUEST)
    if tx_type not in ("income", "expense"):
        return Response({"detail": "Поле type должно быть income или expense"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        amount = None
        if request.data.get("amount") not in (None, ""):
            amount = _parse_amount_value(request.data.get("amount"))
        category = _get_category_for_user(user=user, category_id=request.data.get("category_id"), tx_type=tx_type)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    note = (request.data.get("note") or "").strip() or None
    now = timezone.now()
    template = TransactionTemplate.objects.create(
        user=user,
        name=name,
        type=tx_type,
        amount=amount,
        category=category,
        note=note,
        usage_count=0,
        created_at=now,
        updated_at=now,
        last_used_at=None,
    )
    template = TransactionTemplate.objects.select_related("category").get(id=template.id)
    return Response(TransactionTemplateSerializer(template).data, status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH", "DELETE"])
def template_detail(request: Request, template_id: int) -> Response:
    user = get_user_from_request(request)
    template = TransactionTemplate.objects.filter(id=template_id, user=user).select_related("category").first()

    if not template:
        return Response({"detail": "Шаблон не найден"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        return Response(TransactionTemplateSerializer(template).data)

    if request.method == "DELETE":
        template.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    tx_type = (request.data.get("type", template.type) or "").strip()
    name = (request.data.get("name", template.name) or "").strip()
    if not name:
        return Response({"detail": "Название шаблона обязательно"}, status=status.HTTP_400_BAD_REQUEST)
    if tx_type not in ("income", "expense"):
        return Response({"detail": "Поле type должно быть income или expense"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        amount = template.amount
        raw_amount = request.data.get("amount", template.amount)
        if raw_amount not in (None, ""):
            amount = _parse_amount_value(raw_amount)
        category = _get_category_for_user(
            user=user,
            category_id=request.data.get("category_id", template.category_id if template.category_id else None),
            tx_type=tx_type,
        )
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    note = request.data.get("note", template.note)
    note = (str(note).strip() if note is not None else None) or None

    template.type = tx_type
    template.name = name
    template.amount = amount
    template.category = category
    template.note = note
    template.updated_at = timezone.now()
    template.save()

    template = TransactionTemplate.objects.filter(id=template.id, user=user).select_related("category").first()
    return Response(TransactionTemplateSerializer(template).data)


@api_view(["POST"])
def use_template(request: Request, template_id: int) -> Response:
    user = get_user_from_request(request)
    template = TransactionTemplate.objects.filter(id=template_id, user=user).select_related("category").first()

    if not template:
        return Response({"detail": "Шаблон не найден"}, status=status.HTTP_404_NOT_FOUND)

    tx = Transaction.objects.create(
        user=user,
        category=template.category,
        amount=template.amount or Decimal("0.00"),
        type=template.type,
        note=template.note or template.name,
        date=timezone.now(),
    )

    template.usage_count = (template.usage_count or 0) + 1
    template.last_used_at = timezone.now()
    template.updated_at = timezone.now()
    template.save(update_fields=["usage_count", "last_used_at", "updated_at"])

    tx = Transaction.objects.select_related("category").get(id=tx.id)
    return Response(TransactionSerializer(tx).data, status=status.HTTP_201_CREATED)


@api_view(["GET", "POST"])
def transactions(request: Request) -> Response:
    user = get_user_from_request(request)

    if request.method == "GET":
        try:
            qs = _filtered_transactions_queryset(request, user).order_by("-date", "-id")
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        limit_raw = request.query_params.get("limit", "500")
        try:
            limit = max(1, min(int(limit_raw), 1000))
        except ValueError:
            return Response(
                {"detail": "Некорректный параметр limit"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = TransactionSerializer(qs[:limit], many=True).data
        return Response(data)

    tx_type = (request.data.get("type") or "").strip()
    if tx_type not in ("income", "expense"):
        return Response(
            {"detail": "Поле type должно быть income или expense"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        amount = _parse_amount_value(request.data.get("amount"))
        tx_date = _parse_datetime_value(request.data.get("date"))
        category = _get_category_for_user(
            user=user,
            category_id=request.data.get("category_id"),
            tx_type=tx_type,
        )
    except ValueError as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    note = (request.data.get("note") or "").strip() or None
    template_id = request.data.get("template_id")

    tx = Transaction.objects.create(
        user=user,
        category=category,
        amount=amount,
        date=tx_date,
        type=tx_type,
        note=note,
        is_category_accepted=True,
    )

    tx = Transaction.objects.select_related(
        "category",
        "suggested_category",
    ).get(id=tx.id)

    if template_id not in (None, "", 0, "0"):
        try:
            template = _get_template_for_user(user, template_id)
            template.last_used_at = datetime.now()
            template.save(update_fields=["last_used_at"])
        except ValueError:
            pass

    return Response(
        _serialize_transaction(tx),
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
def quick_add_preview(request: Request) -> Response:
    user = get_user_from_request(request)
    raw_text = request.data.get("text")

    try:
        payload = _quick_add_payload(user, raw_text)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response(payload)


@api_view(["POST"])
def quick_add_create(request: Request) -> Response:
    user = get_user_from_request(request)
    raw_text = request.data.get("text")

    try:
        payload = _quick_add_payload(user, raw_text)
        tx_type = payload["type"]
        tx_date = _parse_datetime_value(payload["date"])
        amount = _parse_amount_value(payload["amount"])

        category_id = request.data.get("category_id")
        if category_id in (None, "", 0, "0"):
            category_id = payload["suggested_category_id"]

        category = _get_category_for_user(
            user=user,
            category_id=category_id,
            tx_type=tx_type,
        )
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    note = payload["note"]

    tx = Transaction.objects.create(
        user=user,
        category=category,
        amount=amount,
        date=tx_date,
        type=tx_type,
        note=note,
        suggested_category_id=payload["suggested_category_id"],
        is_category_accepted=bool(category and category.id == payload["suggested_category_id"]),
    )

    tx = Transaction.objects.select_related("category", "suggested_category").get(id=tx.id)

    return Response(
        {
            "preview": payload,
            "transaction": _serialize_transaction(tx),
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
def repeat_transaction(request: Request, tx_id: int) -> Response:
    user = get_user_from_request(request)
    tx = Transaction.objects.filter(id=tx_id, user=user).select_related("category").first()

    if not tx:
        return Response({"detail": "Транзакция не найдена"}, status=status.HTTP_404_NOT_FOUND)

    new_tx = Transaction.objects.create(
        user=user,
        category=tx.category,
        amount=tx.amount,
        type=tx.type,
        note=tx.note,
        date=timezone.now(),
    )

    new_tx = Transaction.objects.select_related("category").get(id=new_tx.id)
    return Response(TransactionSerializer(new_tx).data, status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH", "DELETE"])
def transaction_detail(request: Request, tx_id: int) -> Response:
    user = get_user_from_request(request)

    tx = (
        Transaction.objects.select_related("category", "suggested_category")
        .filter(id=tx_id, user=user)
        .first()
    )

    if not tx:
        return Response(
            {"detail": "Транзакция не найдена"},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":
        return Response(_serialize_transaction(tx))

    if request.method == "DELETE":
        tx.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    new_type = request.data.get("type", tx.type)
    if new_type not in ("income", "expense"):
        return Response(
            {"detail": "Поле type должно быть income или expense"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        amount = _parse_amount_value(request.data.get("amount", tx.amount))
        tx_date = _parse_datetime_value(request.data.get("date", tx.date))
        category = _get_category_for_user(
            user=user,
            category_id=request.data.get(
                "category_id",
                tx.category_id if tx.category_id else None,
            ),
            tx_type=new_type,
        )
    except ValueError as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    note = request.data.get("note", tx.note)
    note = (str(note).strip() if note is not None else None) or None

    tx.type = new_type
    tx.amount = amount
    tx.date = tx_date
    tx.category = category
    tx.note = note
    tx.is_category_accepted = True
    tx.save()

    tx = (
        Transaction.objects.select_related("category", "suggested_category")
        .filter(id=tx.id, user=user)
        .first()
    )

    return Response(_serialize_transaction(tx))


@api_view(["GET"])
def summary(request: Request) -> Response:
    user = get_user_from_request(request)

    try:
        qs = _filtered_transactions_queryset(request, user)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    income, expense, balance, tx_count = _get_period_summary(qs)

    return Response(
        {
            "income": _money_str(income),
            "expense": _money_str(expense),
            "balance": _money_str(balance),
            "transactions_count": tx_count,
        }
    )


@api_view(["GET"])
def analytics_overview(request: Request) -> Response:
    user = get_user_from_request(request)

    try:
        qs = _filtered_transactions_queryset(request, user)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    income, expense, balance, tx_count = _get_period_summary(qs)
    breakdown = _category_expense_breakdown(qs)
    daily_expenses = _daily_expense_series(qs)
    top_day = _top_spending_day(daily_expenses)
    avg_expense_check = _average_expense_check(qs)
    top_category = breakdown[0] if breakdown else None

    date_from_raw = request.query_params.get("from")
    date_to_raw = request.query_params.get("to")
    date_from = _parse_date(date_from_raw) if date_from_raw else None
    date_to = _parse_date(date_to_raw) if date_to_raw else None

    prev_bounds = _get_previous_period_bounds(date_from, date_to)
    previous = None
    category_deltas = []

    if prev_bounds:
        prev_from_dt, prev_to_dt = prev_bounds
        prev_qs = Transaction.objects.filter(
            user=user,
            date__gte=prev_from_dt,
            date__lte=prev_to_dt,
        )
        prev_income, prev_expense, prev_balance, prev_count = _get_period_summary(prev_qs)
        prev_breakdown = _category_expense_breakdown(prev_qs)

        previous = {
            "from": prev_from_dt.date().isoformat(),
            "to": prev_to_dt.date().isoformat(),
            "income": _money_str(prev_income),
            "expense": _money_str(prev_expense),
            "balance": _money_str(prev_balance),
            "transactions_count": prev_count,
            "expense_change_percent": _money_str(_pct_change(expense, prev_expense)),
        }
        category_deltas = _category_delta_rows(breakdown[:7], prev_breakdown)

    return Response(
        {
            "summary": {
                "income": _money_str(income),
                "expense": _money_str(expense),
                "balance": _money_str(balance),
                "transactions_count": tx_count,
                "average_expense_check": _money_str(avg_expense_check),
            },
            "top_expense_categories": breakdown[:7],
            "daily_expenses": daily_expenses,
            "previous_period": previous,
            "top_spending_day": top_day,
            "top_expense_category": top_category,
            "category_deltas": category_deltas[:5],
        }
    )


@api_view(["GET"])
def analytics_series(request: Request) -> Response:
    user = get_user_from_request(request)

    months_raw = request.query_params.get("months", "6")
    try:
        months = max(2, min(int(months_raw), 24))
    except ValueError:
        return Response(
            {"detail": "Некорректный параметр months"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(
        {
            "months": months,
            "items": _monthly_series(user, months=months),
        }
    )


@api_view(["GET"])
def forecast_expenses(request: Request) -> Response:
    user = get_user_from_request(request)
    return Response(_expense_forecast_payload(user))


@api_view(["GET"])
def insights(request: Request) -> Response:
    user = get_user_from_request(request)

    try:
        month_value = _parse_month_value(request.query_params.get("month"))
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response(_insights_payload(user, month_value))


@api_view(["GET", "POST"])
def budgets(request: Request) -> Response:
    user = get_user_from_request(request)

    if request.method == "GET":
        try:
            month_value = _parse_month_value(request.query_params.get("month"))
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = Budget.objects.filter(
            user=user,
            month=month_value,
        ).select_related("category").order_by("category__name", "id")

        category_id = request.query_params.get("category_id")
        if category_id:
            try:
                qs = qs.filter(category_id=int(category_id))
            except ValueError:
                return Response(
                    {"detail": "Некорректный category_id"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        data = [_serialize_budget(user, budget) for budget in qs]
        return Response(data)

    try:
        category = _get_expense_category_for_user(
            user=user,
            category_id=request.data.get("category_id"),
        )
        month_value = _parse_month_value(request.data.get("month"))
        limit_amount = _parse_amount_value(request.data.get("limit_amount"))
    except ValueError as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    budget, _created = Budget.objects.update_or_create(
        user=user,
        category=category,
        month=month_value,
        defaults={
            "limit_amount": limit_amount,
        },
    )

    budget = Budget.objects.select_related("category").get(id=budget.id)
    return Response(
        _serialize_budget(user, budget),
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET", "PATCH", "DELETE"])
def budget_detail(request: Request, budget_id: int) -> Response:
    user = get_user_from_request(request)

    budget = (
        Budget.objects.select_related("category")
        .filter(id=budget_id, user=user)
        .first()
    )

    if not budget:
        return Response(
            {"detail": "Бюджет не найден"},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "GET":
        return Response(_serialize_budget(user, budget))

    if request.method == "DELETE":
        budget.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    try:
        category = _get_expense_category_for_user(
            user=user,
            category_id=request.data.get("category_id", budget.category_id),
        )
        month_value = _parse_month_value(request.data.get("month", budget.month))
        limit_amount = _parse_amount_value(
            request.data.get("limit_amount", budget.limit_amount)
        )
    except ValueError as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    budget.category = category
    budget.month = month_value
    budget.limit_amount = limit_amount

    try:
        budget.save()
    except IntegrityError:
        return Response(
            {"detail": "Бюджет для этой категории и месяца уже существует"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    budget = Budget.objects.select_related("category").get(id=budget.id)
    return Response(_serialize_budget(user, budget))


@api_view(["GET"])
def budgets_summary(request: Request) -> Response:
    user = get_user_from_request(request)

    try:
        month_value = _parse_month_value(request.query_params.get("month"))
    except ValueError as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    budgets_qs = Budget.objects.filter(
        user=user,
        month=month_value,
    ).select_related("category").order_by("category__name", "id")

    budget_items = [_serialize_budget(user, budget) for budget in budgets_qs]

    total_limit = Decimal("0")
    total_spent = Decimal("0")
    total_remaining = Decimal("0")
    exceeded_count = 0
    warning_count = 0
    normal_count = 0

    for item in budget_items:
        total_limit += Decimal(item["limit_amount"])
        total_spent += Decimal(item["spent_amount"])
        total_remaining += Decimal(item["remaining_amount"])

        if item["status"] == "exceeded":
            exceeded_count += 1
        elif item["status"] == "warning":
            warning_count += 1
        else:
            normal_count += 1

    days_in_month = calendar.monthrange(month_value.year, month_value.month)[1]
    month_label = _month_label(month_value)

    return Response(
        {
            "month": str(month_value),
            "month_label": month_label,
            "days_in_month": days_in_month,
            "budgets_count": len(budget_items),
            "total_limit": _money_str(total_limit),
            "total_spent": _money_str(total_spent),
            "total_remaining": _money_str(total_remaining),
            "exceeded_count": exceeded_count,
            "warning_count": warning_count,
            "normal_count": normal_count,
            "items": budget_items,
        }
    )
