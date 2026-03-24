import xlsxwriter
import os
import uuid
from datetime import datetime


def generate_excel(transactions):
    filename = f"transactions_{uuid.uuid4().hex}.xlsx"
    path = os.path.join("/tmp", filename)

    workbook = xlsxwriter.Workbook(path)
    worksheet = workbook.add_worksheet("Transactions")

    headers = ["Тип", "Категория", "Сумма", "Дата", "Комментарий"]
    for col, header in enumerate(headers):
        worksheet.write(0, col, header)

    for row_idx, tx in enumerate(transactions, start=1):
        worksheet.write(row_idx, 0, tx['type'])
        worksheet.write(row_idx, 1, tx['name'])
        worksheet.write(row_idx, 2, float(tx['amount']))
        worksheet.write(row_idx, 3, tx['date'].strftime("%Y-%m-%d"))
        worksheet.write(row_idx, 4, tx['note'] or "")

    workbook.close()
    return path
