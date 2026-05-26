# Финансовый помощник — Telegram Bot + Mini App

Проект представляет собой систему для учета, анализа и прогнозирования личных финансов.  
Пользователь может быстро добавлять доходы и расходы через Telegram-бота, просматривать баланс, историю операций, аналитику, импортировать банковские выписки и использовать Mini App для более удобной работы с финансовыми данными.

## О проекте

Финансовый помощник помогает пользователю вести личный бюджет в привычном интерфейсе Telegram.  
Бот используется для быстрого добавления операций, а Mini App — для просмотра подробной аналитики, графиков, бюджетов и прогноза расходов.

Основная идея проекта — объединить простой ввод данных, хранение операций в базе данных, автоматическую категоризацию и визуальную аналитику в одной системе.

## Возможности

- регистрация пользователя через Telegram;
- добавление доходов и расходов;
- быстрый ввод операций текстом;
- автоматическое определение категории операции;
- просмотр текущего баланса;
- просмотр истории операций;
- импорт банковских PDF-выписок;
- экспорт операций в Excel;
- настройка напоминаний;
- просмотр аналитики в Mini App;
- работа с бюджетами и лимитами;
- прогнозирование расходов;
- административная панель.

Пример быстрого ввода:

```text
-500 бензин сегодня
+30000 зарплата
-1200 продукты
```

## Технологии

В проекте используются:

- Python;
- aiogram 3;
- Django;
- Django REST Framework;
- PostgreSQL;
- asyncpg;
- HTML, CSS, JavaScript;
- scikit-learn;
- pandas;
- openpyxl;
- pdfplumber;
- matplotlib.

## Структура проекта

```text
finance_bot/
│
├── main.py                 # запуск Telegram-бота
├── config.py               # настройки проекта
├── requirements.txt        # зависимости бота
│
├── database/               # подключение к базе данных и SQL-скрипты
├── handlers/               # обработчики Telegram-бота
├── services/               # бизнес-логика, импорт, экспорт, аналитика, ML
├── states/                 # FSM-состояния
├── utils/                  # клавиатуры и вспомогательные функции
├── scripts/                # скрипты для тестовых данных
│
└── web/                    # Django Mini App и веб-админка
```

## База данных

В качестве базы данных используется PostgreSQL.

Основные таблицы:

- `users` — пользователи;
- `categories` — категории операций;
- `transactions` — доходы и расходы;
- `budgets` — бюджеты и лимиты;
- `reminders` — напоминания;
- `statement_imports` — импортированные выписки;
- `transaction_templates` — шаблоны операций.

SQL-скрипт для создания таблиц находится в файле:

```text
database/init_db.sql
```

## Переменные окружения

В корне проекта нужно создать файл `.env`.

Пример:

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

Файл `.env` нельзя загружать в открытый GitHub-репозиторий.

## Запуск Telegram-бота

Клонировать проект:

```bash
git clone https://github.com/your-username/your-repository.git
cd your-repository
```

Создать виртуальное окружение:

```bash
python3 -m venv .venv
```

Активировать окружение:

```bash
source .venv/bin/activate
```

Для Windows:

```bash
.venv\Scripts\activate
```

Установить зависимости:

```bash
pip install -r requirements.txt
```

Создать базу данных PostgreSQL и выполнить SQL-скрипт:

```bash
psql -U postgres -d finance_bot -f database/init_db.sql
```

Запустить бота:

```bash
python main.py
```

## Запуск Mini App

Перейти в папку веб-приложения:

```bash
cd web
```

Установить зависимости:

```bash
pip install -r requirements.txt
```

Запустить Django-сервер:

```bash
python manage.py runserver
```

После запуска будут доступны:

```text
http://127.0.0.1:8000/admin/
http://127.0.0.1:8000/miniapp/
http://127.0.0.1:8000/api/health/
```

Для входа в админ-панель нужно создать администратора:

```bash
python manage.py createsuperuser
```

## ML-модуль категоризации

В проекте реализована автоматическая категоризация операций.  
Модель анализирует текстовое описание операции и предлагает подходящую категорию.

ML-модуль находится в папке:

```text
services/ml/classifier/
```

Основные файлы:

```text
train.py      # обучение модели
predict.py    # предсказание категории
rules.py      # правила по ключевым словам
```

Для обучения используется TF-IDF-векторизация и модель логистической регрессии.

Запуск обучения:

```bash
python services/ml/classifier/train.py
```

## Полезные команды

```text
/start              запуск бота
/admin              админ-панель
/stats              статистика проекта
/users              список пользователей
/user [id]          информация о пользователе
/all_transactions   просмотр транзакций
```

## Перед публикацией на GitHub

Перед загрузкой проекта рекомендуется удалить или добавить в `.gitignore`:

```text
.env
web/.env
.venv/
web/.venv/
__pycache__/
.DS_Store
temp/
*.log
*.xlsx
```

Пример `.gitignore`:

```gitignore
.venv/
web/.venv/
.env
web/.env
__pycache__/
.DS_Store
temp/
*.log
*.xlsx
```

## Автор

Проект разработан в рамках выпускной квалификационной работы по теме учета, анализа и прогнозирования личных финансов на основе Telegram-бота и Mini App.

## Основные возможности

### Telegram-бот

В Telegram-боте реализованы следующие функции:

- регистрация пользователя через команду `/start`;
- добавление доходов и расходов;
- быстрый ввод операций текстом, например:

```text
-500 бензин сегодня
+30000 зарплата
-1200 продукты 12:30
```

- автоматический разбор суммы, типа операции, даты, времени и описания;
- подбор категории расхода по тексту операции;
- подтверждение или ручной выбор категории;
- просмотр текущего баланса;
- просмотр последних операций;
- импорт банковских выписок;
- экспорт операций в Excel;
- профиль пользователя;
- настройка напоминаний;
- административные команды для владельца проекта.

### Telegram Mini App

Mini App используется как расширенный интерфейс для работы с финансами. Через него можно просматривать данные в более удобном веб-формате.

В проекте реализованы:

- страница Mini App;
- API для получения данных пользователя;
- список категорий;
- список транзакций;
- добавление операций через быстрый ввод;
- шаблоны операций;
- аналитика;
- динамика расходов;
- прогноз расходов;
- бюджетные лимиты;
- Django-админка для просмотра данных.

### Импорт банковских выписок

В проекте есть модуль импорта банковских PDF-выписок. Поддерживаются парсеры для:

- Сбербанка;
- Альфа-Банка.

Импорт выполняет следующие действия:

- извлекает операции из PDF-файла;
- определяет дату, сумму, описание и тип операции;
- пытается сопоставить операцию с категорией;
- проверяет дубликаты;
- сохраняет операции в базу данных;
- сохраняет информацию об импортированной выписке.

### Экспорт в Excel

Пользователь может выгрузить операции в Excel:

- за весь период;
- за выбранный месяц.

Экспорт формируется в виде файла и отправляется пользователю прямо в Telegram.

### Аналитика и прогнозирование

В проекте реализованы функции аналитики:

- подсчет доходов;
- подсчет расходов;
- расчет баланса;
- группировка расходов по категориям;
- динамика расходов по дням и месяцам;
- определение крупных расходов;
- прогноз будущих расходов;
- предупреждения и рекомендации по бюджету.

## Технологический стек

### Backend Telegram-бота

- Python
- aiogram 3
- asyncpg
- PostgreSQL
- python-dotenv
- openpyxl / XlsxWriter
- pdfplumber
- matplotlib
- scikit-learn

### Web / Mini App

- Django
- Django REST Framework
- django-cors-headers
- PostgreSQL
- HTML
- CSS
- JavaScript
- Django Admin

### Машинное обучение

- scikit-learn
- TF-IDF-векторизация текстового описания операции
- Logistic Regression
- rule-based fallback для ключевых слов
- сохранение обученных артефактов через pickle

## Структура проекта

```text
finance_bot_final_for_diplom/
│
├── main.py                         # Точка входа Telegram-бота
├── config.py                       # Загрузка токена и админских ID
├── requirements.txt                # Зависимости Telegram-бота
├── .env                            # Переменные окружения
│
├── database/
│   ├── db.py                       # Подключение к PostgreSQL и методы работы с БД
│   ├── repository.py               # Репозиторий для операций с транзакциями
│   └── init_db.sql                 # SQL-скрипт создания таблиц
│
├── handlers/
│   ├── start.py                    # Команда /start и главное меню
│   ├── balance.py                  # Просмотр баланса
│   ├── history.py                  # Последние операции
│   ├── quick_add.py                # Быстрое добавление операций текстом
│   ├── import_statement.py         # Импорт банковских выписок
│   ├── export.py                   # Экспорт операций в Excel
│   ├── profile.py                  # Профиль пользователя
│   ├── reminders.py                # Напоминания
│   ├── admin.py                    # Админ-команды
│   └── transactions/               # Модули добавления доходов и расходов
│
├── services/
│   ├── charts.py                   # Построение графиков
│   ├── excel.py                    # Генерация Excel-файлов
│   ├── export.py                   # Экспорт пользовательских данных
│   ├── forecast.py                 # Формирование прогноза расходов
│   ├── forecast_math.py            # Математика прогноза
│   ├── ml_forecast.py              # ML-прогнозирование
│   ├── reminder_scheduler.py       # Планировщик напоминаний
│   ├── text_transaction_parser.py  # Разбор текстовых операций
│   │
│   ├── bank_import/
│   │   ├── alfa_pdf.py             # Парсер PDF-выписок Альфа-Банка
│   │   ├── sber_pdf.py             # Парсер PDF-выписок Сбербанка
│   │   ├── importer.py             # Общая логика импорта
│   │   ├── models.py               # Модели импортируемых операций
│   │   └── preview.py              # Предпросмотр результата импорта
│   │
│   └── ml/
│       └── classifier/
│           ├── train.py            # Обучение классификатора категорий
│           ├── predict.py          # Предсказание категории
│           ├── rules.py            # Правила по ключевым словам
│           ├── featurize.py        # Подготовка признаков
│           └── artifacts/          # Сохраненные ML-модели
│
├── states/
│   ├── transaction_states.py       # FSM-состояния для операций
│   ├── export_states.py            # FSM-состояния для экспорта
│   └── budget.py                   # FSM-состояния для бюджета
│
├── utils/
│   ├── keyboards.py                # Клавиатуры Telegram-бота
│   ├── budget_keyboards.py         # Клавиатуры для бюджета
│   └── helpers.py                  # Вспомогательные функции
│
├── scripts/
│   ├── generate_test_transactions.py
│   └── generate_test_budgets.py
│
└── web/
    ├── manage.py                   # Точка входа Django-проекта
    ├── requirements.txt            # Зависимости веб-части
    ├── .env                        # Переменные окружения для Django
    │
    ├── config/
    │   ├── settings.py             # Настройки Django
    │   ├── urls.py                 # Главные маршруты Django
    │   ├── asgi.py
    │   └── wsgi.py
    │
    └── finance/
        ├── models.py               # Django-модели поверх существующих таблиц
        ├── api.py                  # REST API для Mini App
        ├── urls.py                 # API-маршруты
        ├── views.py                # Представления Mini App
        ├── web_urls.py             # Веб-маршруты Mini App
        ├── admin.py                # Настройка Django Admin
        ├── serializers.py          # DRF-сериализаторы
        ├── auth.py                 # Авторизация пользователей
        ├── templates/              # HTML-шаблоны
        └── static/                 # Статические файлы
```

## База данных

В качестве основной базы данных используется PostgreSQL.

SQL-скрипт для создания и обновления структуры базы находится здесь:

```text
database/init_db.sql
```

Основные таблицы:

| Таблица | Назначение |
|---|---|
| `users` | Пользователи Telegram-бота |
| `categories` | Категории доходов и расходов |
| `transactions` | Финансовые операции |
| `budgets` | Бюджеты и лимиты по категориям |
| `reminders` | Пользовательские напоминания |
| `budget_forecast` | Прогноз бюджета |
| `statement_imports` | История импортированных банковских выписок |
| `transaction_templates` | Шаблоны повторяющихся операций |
| `auth_codes` | Коды авторизации для Mini App |

Для создания таблиц нужно выполнить файл `database/init_db.sql` в базе PostgreSQL.

Например через терминал:

```bash
psql -U postgres -d finance_bot -f database/init_db.sql
```

Или через pgAdmin:

1. Создать базу данных.
2. Открыть Query Tool.
3. Вставить содержимое файла `database/init_db.sql`.
4. Выполнить SQL-скрипт.

## Переменные окружения

В корне проекта должен быть файл `.env`.

Пример:

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

Для Django-части аналогичный файл `.env` должен находиться в папке `web/`.

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

### Описание переменных

| Переменная | Назначение |
|---|---|
| `BOT_TOKEN` | Токен Telegram-бота, полученный через BotFather |
| `DB_HOST` | Хост PostgreSQL |
| `DB_PORT` | Порт PostgreSQL |
| `DB_NAME` | Название базы данных |
| `DB_USER` | Пользователь PostgreSQL |
| `DB_PASS` | Пароль пользователя PostgreSQL |
| `ADMIN_IDS` | Telegram ID администраторов через запятую |
| `AUTH_CODE_PEPPER` | Секретная строка для дополнительной защиты кодов авторизации |
| `SITE_URL` | Базовый адрес Django-сервера |
| `MINI_APP_URL` | Ссылка на Mini App |

## Установка и запуск Telegram-бота

### 1. Клонировать репозиторий

```bash
git clone https://github.com/your-username/your-repository.git
cd your-repository
```

### 2. Создать виртуальное окружение

```bash
python3 -m venv .venv
```

### 3. Активировать виртуальное окружение

Для macOS / Linux:

```bash
source .venv/bin/activate
```

Для Windows:

```bash
.venv\Scripts\activate
```

### 4. Установить зависимости

```bash
pip install -r requirements.txt
```

### 5. Создать базу данных PostgreSQL

Пример через `psql`:

```bash
createdb -U postgres finance_bot
```

После создания базы выполнить SQL-скрипт:

```bash
psql -U postgres -d finance_bot -f database/init_db.sql
```

### 6. Создать файл `.env`

В корне проекта создать файл `.env` и заполнить его по примеру из раздела [Переменные окружения](#переменные-окружения).

### 7. Запустить Telegram-бота

```bash
python main.py
```

Если все настроено правильно, в терминале появится сообщение о запуске бота.

## Запуск Mini App и веб-админки

Веб-часть проекта находится в папке `web`.

### 1. Перейти в папку `web`

```bash
cd web
```

### 2. Создать виртуальное окружение для веб-части

```bash
python3 -m venv .venv
```

### 3. Активировать окружение

Для macOS / Linux:

```bash
source .venv/bin/activate
```

Для Windows:

```bash
.venv\Scripts\activate
```

### 4. Установить зависимости Django

```bash
pip install -r requirements.txt
```

### 5. Создать `.env` в папке `web`

Файл `web/.env` должен содержать те же параметры подключения к базе данных, что и основной `.env`.

### 6. Запустить Django-сервер

```bash
python manage.py runserver
```

После запуска будут доступны:

```text
http://127.0.0.1:8000/admin/
http://127.0.0.1:8000/miniapp/
http://127.0.0.1:8000/api/health/
```

### 7. Создать администратора Django

```bash
python manage.py createsuperuser
```

После этого можно открыть:

```text
http://127.0.0.1:8000/admin/
```

## API Mini App

Основные API-маршруты:

| Метод | URL | Назначение |
|---|---|---|
| `GET` | `/api/health/` | Проверка работы API |
| `POST` | `/api/miniapp/auth/` | Авторизация Mini App |
| `GET` | `/api/me/` | Данные текущего пользователя |
| `GET` | `/api/categories/` | Получение категорий |
| `GET / POST` | `/api/transactions/` | Получение и создание транзакций |
| `POST` | `/api/transactions/quick-add/preview/` | Предпросмотр быстрого добавления |
| `POST` | `/api/transactions/quick-add/create/` | Создание операции из текстового ввода |
| `GET` | `/api/summary/` | Общая финансовая сводка |
| `GET` | `/api/analytics/overview/` | Аналитика по расходам и доходам |
| `GET` | `/api/analytics/series/` | Динамика операций |
| `GET` | `/api/forecast/` | Прогноз расходов |
| `GET` | `/api/insights/` | Финансовые рекомендации |
| `GET / POST` | `/api/budgets/` | Работа с бюджетами |
| `GET` | `/api/budgets/summary/` | Сводка по бюджетам |
| `GET / POST` | `/api/templates/` | Работа с шаблонами операций |

## ML-модуль категоризации

В проекте реализована автоматическая категоризация операций по текстовому описанию.

ML-модуль расположен в папке:

```text
services/ml/classifier/
```

Основные файлы:

| Файл | Назначение |
|---|---|
| `train.py` | Обучение модели на пользовательских транзакциях |
| `predict.py` | Предсказание категории для новой операции |
| `rules.py` | Словарь правил по ключевым словам |
| `featurize.py` | Подготовка текстовых признаков |
| `artifacts/` | Сохраненные модель, векторизатор и карта категорий |

Для обучения используется:

- текстовое описание операции;
- сумма операции;
- категория, подтвержденная пользователем;
- TF-IDF-векторизация;
- модель логистической регрессии.

Запуск обучения:

```bash
python services/ml/classifier/train.py
```

После обучения в папке `artifacts` сохраняются:

```text
model.pkl
vectorizer.pkl
label_map.pkl
```

При добавлении операции бот может предложить категорию автоматически. Если пользователь подтверждает предложенную категорию, эта информация может использоваться как обучающий пример для дальнейшего улучшения модели.

## Полезные команды бота

| Команда / кнопка | Назначение |
|---|---|
| `/start` | Запуск бота и регистрация пользователя |
| `/admin` | Админ-панель для администратора |
| `💰 Баланс` | Показать текущий баланс |
| `📜 Последние операции` | Показать последние транзакции |
| `📁 Экспорт в Excel` | Выгрузить операции в Excel |
| `📥 Импорт выписки` | Импортировать банковскую выписку |
| `👤 Профиль` | Показать профиль пользователя |
| `🔔 Напоминания` | Настроить напоминания |
| `📱 Открыть Mini App` | Открыть веб-интерфейс Mini App |

Административные команды:

| Команда | Назначение |
|---|---|
| `/admin` | Открыть меню администратора |
| `/stats` | Показать общую статистику |
| `/users` | Показать последних пользователей |
| `/all_transactions` | Показать топ транзакций |
| `/user [telegram_id]` | Показать карточку пользователя |

## Тестовые данные

В проекте есть скрипты для генерации тестовых данных:

```text
scripts/generate_test_transactions.py
scripts/generate_test_budgets.py
```

Их можно использовать для заполнения базы демонстрационными транзакциями и бюджетами.

Пример запуска:

```bash
python scripts/generate_test_transactions.py
python scripts/generate_test_budgets.py
```

## Рекомендации перед публикацией на GitHub

Перед загрузкой проекта на GitHub рекомендуется удалить из репозитория:

```text
.env
web/.env
.venv/
web/.venv/
__pycache__/
.DS_Store
web/db.sqlite3
temp/imports/
```

Также стоит добавить файл `.gitignore`.

Пример `.gitignore`:

```gitignore
# Python
__pycache__/
*.py[cod]
*.pyo
*.pyd

# Virtual environments
.venv/
venv/
env/

# Environment variables
.env
web/.env

# IDE
.idea/
.vscode/

# macOS
.DS_Store

# Local database / temp files
web/db.sqlite3
temp/
*.log

# Generated files
*.xlsx
*.png
```

## Примечания

- Для полноценной работы Mini App в Telegram обычно требуется HTTPS-адрес. При локальной разработке можно использовать `localhost`, а для демонстрации в Telegram — домен сервера или туннель.
- Telegram-бот и Django Mini App используют одну и ту же PostgreSQL-базу данных.
- Django-модели в проекте настроены поверх существующих таблиц PostgreSQL.
- Основной сценарий добавления операций реализован через Telegram-бота, а расширенная аналитика — через Mini App.
- Для работы импорта PDF-выписок необходимы библиотеки `pdfplumber` и `pdfminer.six`.
- Токены, пароли и секретные ключи нельзя публиковать в открытом репозитории.

## Автор

Проект разработан в рамках учебной работы по теме автоматизации учета, анализа и прогнозирования личных финансов.
