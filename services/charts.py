# Построение графиков через matplotlib
import matplotlib.pyplot as plt
import os
import uuid
from collections import defaultdict
from datetime import datetime


def generate_bar_chart(transactions):
    daily = defaultdict(float)
    for tx in transactions:
        day = tx['date'].day
        amount = float(tx['amount']) if tx['type'] == 'income' else -float(tx['amount'])
        daily[day] += amount

    days = sorted(daily)
    values = [daily[day] for day in days]

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(days, values, color=['green' if val >= 0 else 'red' for val in values])

    # Подписи над столбиками
    for bar in bars:
        height = bar.get_height()
        ax.annotate(
            f'{height:.0f}',
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 5),
            textcoords="offset points",
            ha='center',
            fontsize=10
        )

    ax.set_title("Доходы/Расходы по дням", fontsize=14)
    ax.set_xlabel("День месяца", fontsize=12)
    ax.set_ylabel("Сумма, ₽", fontsize=12)
    ax.set_xticks(days)
    ax.grid(True, linestyle='--', alpha=0.5)

    filename = f"bar_{uuid.uuid4().hex}.png"
    path = os.path.join("/tmp", filename)
    plt.tight_layout()
    plt.savefig(path)
    plt.close()
    return path


def generate_pie_chart(transactions):
    by_category = defaultdict(float)
    for tx in transactions:
        if tx['type'] == 'expense':
            by_category[tx['name']] += float(tx['amount'])

    labels = list(by_category.keys())
    sizes = list(by_category.values())

    fig, ax = plt.subplots(figsize=(7, 7))
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
    ax.set_title("Расходы по категориям", fontsize=14)
    ax.axis('equal')  # Круглая диаграмма

    filename = f"pie_{uuid.uuid4().hex}.png"
    path = os.path.join("/tmp", filename)
    plt.tight_layout()
    plt.savefig(path)
    plt.close()
    return path
