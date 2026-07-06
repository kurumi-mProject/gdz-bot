# 📚 GDZ Bot — Telegram Bot for Homework Solutions

Telegram-бот для поиска готовых домашних заданий с сайта gdz.ru. Принимает запрос в свободной форме, ищет нужный учебник через DuckDuckGo, парсит страницу с ответом через Playwright и отправляет скриншот пользователю.

## Возможности

- **Поиск по запросу** — достаточно написать `математика 5 класс 123 упр`
- **Автоматический парсинг** — поиск учебника через DuckDuckGo + парсинг gdz.ru через Playwright
- **Скриншот ответа** — возвращает изображение с решением задания
- **Выбор учебника** — если найдено несколько вариантов, предлагает выбор

## Стек

- Python 3.11+
- [aiogram 3](https://docs.aiogram.dev/)
- [Playwright](https://playwright.dev/python/) — headless-браузер для парсинга
- Pillow — обработка изображений

## Установка

```bash
git clone https://github.com/kurumi-mProject/gdz-bot.git
cd gdz-bot
python -m venv venv
source venv/bin/activate
pip install aiogram Pillow playwright
playwright install chromium
```

Вставь токен бота в `bot.py` или вынеси в `.env`:
```python
BOT_TOKEN = "your_token_here"
```

Запуск:
```bash
python bot.py
# или
bash run.sh
```

## Использование

Отправь боту запрос в формате:

```
математика 5 класс 123 упр
русский язык 7 класс 45 упр
физика 9 класс 12 упр
```

Бот найдёт учебник, откроет страницу с ответом и пришлёт скриншот.

## Структура проекта

```
gdz-bot/
├── bot.py          # Основная логика бота и парсинга
├── send_promo.py   # Рассылка промо-сообщений
└── run.sh          # Скрипт запуска
```
