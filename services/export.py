import os
import xlsxwriter
from database.db import db

async def export_user_to_excel(telegram_id: int) -> str:
    user_id = await db.execute("SELECT id FROM users WHERE telegram_id = $1", telegram_id, fetchval=True)
    if not user_id:
        raise Exception("Пользователь не найден")

    rows = await db.execute(
        "SELECT amount, type, category_id, date FROM transactions WHERE user_id = $1 ORDER BY date DESC",
        user_id,
        fetch=True
    )

    path = f"user_{telegram_id}_export.xlsx"
    workbook = xlsxwriter.Workbook(path)
    sheet = workbook.add_worksheet("Транзакции")

    sheet.write_row(0, 0, ["Сумма", "Тип", "Категория ID", "Дата"])
    for i, row in enumerate(rows, 1):
        sheet.write(i, 0, float(row["amount"]))
        sheet.write(i, 1, row["type"])
        sheet.write(i, 2, row["category_id"])
        sheet.write(i, 3, row["date"].strftime("%Y-%m-%d"))

    workbook.close()
    return path
