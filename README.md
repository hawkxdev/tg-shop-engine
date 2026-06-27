# tg-shop-engine

Движок Telegram-бота для электронной коммерции на российском рынке. Один арендатор,
один магазин: весь путь **каталог -> корзина -> оформление -> оплата** проходит внутри
Telegram, а магазин управляется из админки Django. Разработка велась spec-first, на основе
формальной спецификации функций, модели данных и контрактов обработчиков и вебхуков.

## Возможности

- **Каталог**: категории и карточки товаров с изображениями, ценами и остатками;
  списки с пагинацией.
- **Корзина**: на основе FSM (aiogram FSM поверх Redis), изменение количества.
- **Оформление**: сбор имени, телефона (валидация российского формата) и адреса доставки,
  нормализация через [DaData](https://dadata.ru/).
- **Оплата**: [YooKassa](https://yookassa.ru/developers) (СБП) и Telegram Stars;
  заказ подтверждается по колбэку провайдера.
- **Промокоды**: срок действия, лимиты использования, минимальная сумма заказа,
  тип «бесплатная доставка».
- **Админка**: Django admin для товаров, заказов и промокодов с аналитикой по заказам.

## Технологический стек

- [aiogram 3](https://docs.aiogram.dev/): фреймворк Telegram-бота
- [Django 5](https://docs.djangoproject.com/): ORM и админка
- [PostgreSQL](https://www.postgresql.org/docs/) через [psycopg 3](https://www.psycopg.org/psycopg3/docs/)
- [Redis](https://redis.io/docs/): хранилище FSM
- [YooKassa SDK](https://github.com/yoomoney/yookassa-sdk-python), DaData через [httpx](https://www.python-httpx.org/)
- [structlog](https://www.structlog.org/), [Pillow](https://python-pillow.org/)
- Инструменты: [uv](https://docs.astral.sh/uv/), [ruff](https://docs.astral.sh/ruff/),
  [mypy](https://mypy.readthedocs.io/) (strict), [pytest](https://docs.pytest.org/) +
  pytest-django + factory-boy, Docker

## Требования

- Docker и Docker Compose v2
- Токен Telegram-бота (от [@BotFather](https://t.me/BotFather))
- Тестовые учётные данные YooKassa (Shop ID + секретный ключ)
- API-ключ и секрет DaData

## Быстрый старт

```bash
git clone https://github.com/hawkxdev/tg-shop-engine.git
cd tg-shop-engine
cp .env.example .env
```

Заполните `.env` (см. таблицу ниже), затем:

```bash
docker compose up --build -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

Админка доступна по адресу `http://localhost:8000/admin/`. Добавьте там категорию и товар,
после чего отправьте `/start` боту в Telegram. Для локальной доставки вебхуков откройте
`localhost:8000` через туннель вроде [ngrok](https://ngrok.com/) и задайте `WEBHOOK_URL`.

## Переменные окружения

Полный шаблон в [`.env.example`](.env.example). Основные переменные:

| Переменная | Описание |
|---|---|
| `BOT_TOKEN` | токен Telegram-бота от @BotFather |
| `SECRET_KEY` | секретный ключ Django |
| `DATABASE_URL` | DSN PostgreSQL |
| `REDIS_URL` | URL Redis для хранилища FSM |
| `WEBHOOK_URL` | публичный базовый URL для вебхука Telegram |
| `YUKASSA_SHOP_ID`, `YUKASSA_SECRET` | учётные данные YooKassa |
| `DADATA_API_KEY`, `DADATA_SECRET` | учётные данные DaData для нормализации адресов |
| `ADMIN_CHAT_ID` | ID чата Telegram для уведомлений администратора |
| `DELIVERY_COST` | стоимость доставки по умолчанию |

## Структура проекта

```
bot/        обработчики aiogram, клавиатуры, middleware, состояния FSM, сервисы
shop/       модели Django (Category, Product, Order, OrderItem, PromoCode), админка, сервисы
payments/   интеграция YooKassa и обработка вебхуков
core/        настройки Django, точки входа WSGI/ASGI
tests/      модульные и интеграционные тесты
```

Контейнеры: `web` (Django/gunicorn), `bot` (aiogram polling/webhook), `postgres`, `redis`.

## Тестирование

```bash
docker compose exec web pytest
docker compose exec web pytest --cov
```

## Статус

MVP завершён: основной путь покупки, промокоды и оплата через Telegram Stars.
Один арендатор по архитектуре. Текст бота для пользователя на русском (российский рынок).

## Лицензия

[MIT](LICENSE)

## Автор

Sergey Sokolkin, [github.com/hawkxdev](https://github.com/hawkxdev)
