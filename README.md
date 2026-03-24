# 🤖 Финансовый помощник – Telegram Бот

Бот на Aiogram 3 + PostgreSQL (asyncpg) для учёта личных финансов.  
Работает с категориями, транзакциями, аналитикой, экспортом в Excel.

## 📦 Установка на macOS

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Создайте `.env` файл:

```
BOT_TOKEN=ваш_токен
DB_HOST=localhost
DB_PORT=5432
DB_NAME=finance_bot
DB_USER=postgres
DB_PASS=ваш_пароль
```

## 🚀 Запуск бота

```bash
python main.py
```

## 🗄 Создание БД

Скопируйте SQL из `database/init_db.sql` и выполните в pgAdmin.
