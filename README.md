# Финансовый помощник

Проект представляет собой систему для учета личных финансов на основе Telegram-бота и Mini App.

Через Telegram-бота пользователь может быстро добавлять доходы и расходы, смотреть баланс, историю операций, импортировать банковские выписки и выгружать данные в Excel.  
Mini App используется для более удобного просмотра аналитики, бюджета, графиков и прогноза расходов.

## Материалы проекта

- [Отчет по ВКР](ВКР%20Гаврилова%20Владислава%20Сергеевича.pdf)
- [Презентация по ВКР](Презентация%20ВКР.pdf)

## Как запустить проект

### 1. Клонировать проект

```bash
git clone https://github.com/Vlad-gw/VP_TgBot_with_miniApp_and_Admins.git
cd VP_TgBot_with_miniApp_and_Admins
```

### 2. Создать виртуальное окружение

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Для Windows:

```bash
.venv\Scripts\activate
```

### 3. Установить зависимости

```bash
pip install -r requirements.txt
```

### 4. Создать базу данных PostgreSQL

Создать базу данных:

```bash
createdb -U postgres finance_bot
```

Выполнить SQL-скрипт:

```bash
psql -U postgres -d finance_bot -f database/init_db.sql
```

### 5. Создать файл `.env`

В корне проекта создать файл `.env`:

```env
BOT_TOKEN=your_telegram_bot_token

DB_HOST=localhost
DB_PORT=5432
DB_NAME=finance_bot
DB_USER=postgres
DB_PASS=your_password

ADMIN_IDS=123456789

AUTH_CODE_PEPPER=your_secret_pepper
SITE_URL=http://127.0.0.1:8000
MINI_APP_URL=http://127.0.0.1:8000/miniapp/
```

### 6. Запустить Telegram-бота

```bash
python main.py
```

## Как запустить Mini App

Перейти в папку веб-приложения:

```bash
cd web
```

Установить зависимости:

```bash
pip install -r requirements.txt
```

Создать файл `.env` в папке `web` с такими же настройками базы данных.

Запустить сервер:

```bash
python manage.py runserver
```

После запуска Mini App и админ-панель будут доступны по адресам:

```text
http://127.0.0.1:8000/miniapp/
http://127.0.0.1:8000/admin/
```
