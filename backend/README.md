# SafeCall backend

Бэкенд для приложения SafeCall (Flutter/Android). Защищает от телефонных мошенников **без
прослушивания звонков**: телефон проверяет входящий номер по локальной базе, а сервер
собирает репорты пользователей, считает риск, объединяет номера в «кампании» и раздаёт
приложению дельта-обновления базы.

- Аудио и содержимое разговоров не собираются. Нет имён, email, контактов: устройство
  идентифицируется только случайным UUID, который генерирует приложение.
- Текст жалобы (`free_text`) используется только для построения fingerprint и не сохраняется.
  В БД пишется лишь HMAC от него.
- Номер без данных получает статус `UNKNOWN`. Это не «безопасный» номер и не «мошенник».
- Пока на номер пожаловались меньше 3 разных устройств, его уровень не поднимается выше `MEDIUM`.

Стек: Python 3.12, FastAPI, SQLAlchemy 2 (async), Alembic, PostgreSQL, APScheduler, slowapi,
python-jose, phonenumbers, Gemini API (`google-genai`, по умолчанию `gemini-3.8-flash`).

Всё работает одним процессом. Risk engine и campaign engine раньше были заглушками в отдельных
сервисах `services/*`, теперь это модули в `app/services/`. Схемой БД управляет только Alembic,
SQL-файла инициализации больше нет.

## Структура

```
backend/
├── app/
│   ├── main.py              # FastAPI app, CORS, лимиты, обработчики ошибок, планировщик
│   ├── config.py            # pydantic-settings (.env)
│   ├── db.py                # async engine / sessions
│   ├── models.py            # devices, numbers, reports, campaigns, campaign_numbers, feedback
│   ├── schemas.py           # Pydantic-схемы запросов/ответов (OpenAPI → Dart-клиент)
│   ├── security.py          # device_id → JWT, admin-JWT по X-Admin-Key
│   ├── errors.py            # единый формат ошибок {"error": {"code", "message"}}
│   ├── limiter.py           # slowapi, ключ = device_id из JWT (или IP)
│   ├── jobs.py              # периодический пересчёт рисков и кампаний
│   ├── routers/             # auth, numbers, reports, sync, campaigns, feedback, assistant, admin
│   └── services/
│       ├── risk_engine.py   # чистая функция скоринга + запись в БД
│       ├── campaign_engine.py  # Жаккар, привязка к кампаниям, кластеризация
│       ├── fingerprint.py   # словарь тегов, LLM + fallback, кэш (LRU + Redis)
│       ├── phone.py         # E.164 нормализация, маскирование для логов
│       ├── report_service.py   # сценарий приёма репорта
│       ├── assistant.py     # ИИ-помощник: системный промпт, диалог → Gemini
│       └── gemini.py        # общий клиент Gemini
├── alembic/                 # миграции (async)
├── scripts/seed.py          # демо-данные и демо-сценарий
└── tests/                   # pytest: движки, fingerprint, API
```

## Запуск

### Docker (весь стек)

`docker-compose.yml` и `.env.example` лежат в **корне репозитория**, команды запускаются оттуда.
Compose поднимает четыре сервиса: `api` (эта папка), `postgres`, `redis` и `dashboard`.

```bash
cp .env.example .env          # поменяйте JWT_SECRET и ADMIN_API_KEY, при желании задайте GEMINI_API_KEY
docker compose up --build -d  # api :8000, dashboard :3000, postgres :5432, redis :6379
docker compose exec api python -m scripts.seed --reset
```

Миграции применяются при старте контейнера (`alembic upgrade head`). Swagger лежит на
http://localhost:8000/docs, OpenAPI-схема на http://localhost:8000/openapi.json.

Если `docker` отвечает `permission denied ... docker.sock`, добавьте себя в группу:
`sudo usermod -aG docker $USER`, затем перелогиньтесь.

### Локально без Docker

Нужен Python 3.12+. Настройки читаются из переменных окружения и из `.env` **в текущей папке**,
поэтому корневой `.env` нужно подключить симлинком или задать переменные через `export`.

```bash
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

# PostgreSQL из compose, API локально с --reload
(cd .. && docker compose up -d postgres redis)
ln -sf ../.env .env      # DATABASE_URL из .env.example уже смотрит на localhost:5432

# Если Docker недоступен, для быстрой пробы подойдёт SQLite:
# export DATABASE_URL=sqlite+aiosqlite:///./safecall.db

alembic upgrade head
python -m scripts.seed --reset
uvicorn app.main:app --reload
```

### Тесты

Подробности, маркеры, нагрузка, демо-скрипт и список найденных багов — в [tests/README.md](tests/README.md).
Тестовые зависимости не входят в Docker-образ, тесты запускаются локально или в CI.

```bash
cd backend && pip install -r requirements-dev.txt
pytest -m "unit or api"   # быстрый набор, ~16 с
pytest                    # всё: unit, api, security, perf, e2e
```

### Генерация Dart-клиента

```bash
curl -s http://localhost:8000/openapi.json -o openapi.json
openapi-generator-cli generate -i openapi.json -g dart-dio -o safecall_api
```

`operationId` равен имени функции эндпоинта, а методы раскладываются по классам по тегам.
В клиенте получается так:

| Класс | Методы |
|---|---|
| `AuthApi` | `authDevice` |
| `NumbersApi` | `checkNumber`, `listNumbers` |
| `ReportsApi` | `createReport` |
| `SyncApi` | `syncNumbers` |
| `FeedbackApi` | `createFeedback` |
| `AssistantApi` | `chat` |
| `CampaignsApi` | `listCampaigns`, `getCampaign` |
| `AdminApi` | `adminToken`, `getStats`, `listReports`, `activity`, `recalculate`, `removeNumber`, `restoreNumber` |

Имена закреплены тестом `test_openapi_operation_ids_are_short_and_unique`: переименование функции
эндпоинта меняет API клиента, и тест это поймает.

## Как это работает

### Risk engine (`services/risk_engine.py`)

Скоринг написан правилами, без ML. Каждое устройство даёт один голос с весом
`reputation`, который ограничен диапазоном 0..2. Устройство с `reputation = 0` не учитывается.
Репутация устройств-репортеров корректируется по обратной связи (`POST /feedback`):
подтверждение предупреждения (`was_correct = true`) дает +0.1 (до 2.0), а сообщение
о ложном срабатывании (`was_correct = false`) дает -0.2 (до 0.0). При обнулении репутации
жалобы устройства перестают влиять на оценку рисков.
Feedback ограничен до 20 запросов в час на устройство, один device может оставить только
один голос на номер (повторная отправка идемпотентна), а устройство не может оценивать
собственный репорт. Ограничения настраиваются через `RATE_LIMIT_FEEDBACK`.

| Сигнал | Баллы |
|---|---|
| Уникальные жалобщики (взвешенно): 0 / 1–2 / 3–5 / 6–10 / >10 | 0 / 10 / 20 / 30 / 40 |
| Сходство жалоб (доля с одинаковыми категорией и действиями, нужно ≥ 2 жалобы) | до 20 |
| Привязка к кампании: `30 × campaign.risk_score / 100` | до 30 |

Уровни: 0–29 `LOW`, 30–59 `MEDIUM`, 60–100 `HIGH`. Если нет ни репортов, ни кампании,
уровень `UNKNOWN`. Пока уникальных жалобщиков меньше 3, итог не выше `MEDIUM` (score режется до 59).

Жалобы стареют. Первые `REPORT_GRACE_DAYS` (30) дней жалоба весит полностью, затем вес
уменьшается вдвое каждые `REPORT_HALF_LIFE_DAYS` (90) дней. Голос с весом меньше 0.1
(примерно через год) не учитывается. Номер без свежих жалоб постепенно опускается до `UNKNOWN`,
и клиент получает `removed: true` в `/sync`.

### Fingerprint (`services/fingerprint.py`)

Словарь тегов закрытый. Категории: `BANK POLICE DELIVERY RELATIVE INVESTMENT OTHER`.
Действия: `SUSPICIOUS_TRANSACTION OTP CARD_DATA TRANSFER INSTALL_APP URGENCY THREAT`.

- Если пришли только чекбоксы, fingerprint собирается из `{category} ∪ actions`, LLM не вызывается.
- Если есть `free_text`, текст уходит в Gemini с системной инструкцией и JSON Schema ответа
  (structured output: категория и теги только из словаря). Ответ всё равно разбирается защитно: снимаются ```` ```json ````-ограждения, неизвестные теги отбрасываются,
  мусорный ответ даёт `None`. Теги LLM добавляются к чекбоксам. Категорию пользователя LLM
  может уточнить только если пользователь выбрал `OTHER`.
- Ошибка, таймаут (`LLM_TIMEOUT_SECONDS`), ошибка API Gemini (например, квота) или пустой `GEMINI_API_KEY`
  приводят к fallback на чекбоксы.
- Результат кэшируется по HMAC текста в два слоя: локальный LRU процесса и общий Redis
  (TTL `LLM_CACHE_TTL_SECONDS`, по умолчанию 7 дней). Так одинаковый текст не уходит в Gemini
  повторно ни с одного воркера. Если Redis недоступен, работает только локальный слой.

### Campaign engine (`services/campaign_engine.py`)

- Сходство считается коэффициентом Жаккара по множествам тегов, порог 0.7.
- Номер привязывается к существующей кампании, только если **минимум 2 разных устройства**
  прислали репорты, похожие на fingerprint кампании.
- Новая кампания создаётся, когда есть ≥ 3 номера без кампании с похожими доминирующими
  fingerprint'ами (у каждого ≥ 2 согласных жалобщика). Fingerprint кампании состоит из тегов,
  которые встречаются хотя бы у половины номеров. Название генерируется автоматически,
  например «Bank impersonation + OTP, URGENCY».
- Жалобы категории `OTHER` без action-тегов не считаются паттерном: из них нельзя создать
  кампанию или присоединить номер к существующей кампании.
- `risk_score` кампании растёт с числом номеров и жалоб, опасные действия
  (OTP/CARD_DATA/TRANSFER/INSTALL_APP) дают +10.
- Кампании обслуживаются автоматически. Номер, снятый модерацией, покидает кампанию.
  Кампании с похожими fingerprint'ами (Жаккар ≥ 0.7) сливаются: остаётся та, где больше номеров,
  при равенстве — более старая, поэтому id, известные клиентам, не меняются. Кампания, в которой
  осталось меньше 2 номеров, расформировывается.
- Создание и слияние кампаний идут под advisory-lock PostgreSQL (`pg_advisory_xact_lock`), так что
  два одновременных репорта не создадут две одинаковые кампании.

### Фоновые задачи (`jobs.py`)

- **Инкрементальный пересчёт** раз в `RECALC_INTERVAL_MINUTES` (5 мин): репутации по feedback,
  поиск и обслуживание кампаний. Скоринг пересчитывается только для затронутых номеров: на которые
  жаловались устройства с изменившейся репутацией, номера в кампаниях и только что отвязанные.
- **Полный пересчёт** раз в сутки в `FULL_RECALC_HOUR_UTC` (03:00 UTC): все номера, чтобы
  срабатывало затухание жалоб. Вручную: `POST /api/v1/admin/recalculate`.
- При нескольких воркерах каждая задача выполняется только в одном из них: перед запуском
  ставится блокировка в Redis (`SET NX EX`), снимается она только своим токеном. Без Redis
  задача просто запускается; если Redis недоступен, тоже запускается — задачи идемпотентны.
- Номера пересчитываются пачками по 500: два запроса на пачку вместо двух на каждый номер.

### ИИ-помощник (`services/assistant.py`)

`POST /assistant/chat` принимает весь диалог (`role`: `user` | `assistant`, до 20 сообщений,
каждое до 1000 символов, последнее от пользователя) и возвращает `{"reply": "..."}`.
Ответ даёт Gemini (`GEMINI_MODEL`) с системным промптом SafeCall:

- отвечает по-русски, а если пользователь пишет по-румынски, то по-румынски; коротко и просто,
  с расчётом на пожилых людей;
- объясняет статусы номеров (UNKNOWN — «нет данных», а не «безопасно») и напоминает, что банк
  и полиция никогда не просят коды из SMS, данные карты, перевод на «безопасный счёт» и установку
  приложений;
- если человек уже назвал код или перевёл деньги: позвонить в банк по номеру на карте,
  заблокировать карту, обратиться в полицию (112), сохранить доказательства;
- не утверждает, что номер точно мошеннический, и не просит присылать коды и пароли в чат.

Диалоги не сохраняются в БД и не попадают в логи: при ошибке пишется только код ответа Gemini или
тип исключения. Нет ключа, Gemini недоступен или вернул пустой ответ → `503 ASSISTANT_UNAVAILABLE`,
и приложение показывает свои статичные советы. Таймаут `ASSISTANT_TIMEOUT_SECONDS` (20 с),
лимит 20 запросов в час на устройство (`RATE_LIMIT_ASSISTANT`).

### Синхронизация (`GET /sync`)

1. Первый запуск: `GET /sync` без `since` отдаёт полный снимок (только номера с данными, без UNKNOWN).
2. Листайте по `next_cursor`, пока `has_more = true`. Параметр `since` при этом не меняйте.
3. Сохраните `server_time` **первой** страницы и передавайте его как `since` в следующий раз.
4. В дельте приходят все изменившиеся номера. `removed: true` значит, что номер надо удалить
   из локальной БД: его сняли модерацией или у него больше нет данных.

`server_time` специально сдвинут на 10 секунд назад, чтобы не терять записи, которые
коммитятся параллельно. Поэтому несколько строк могут прийти повторно, и на клиенте нужен upsert.

## API

Все эндпоинты живут под `/api/v1` и требуют `Authorization: Bearer <JWT>`, кроме `/auth/device`
и `/health`. Для `/admin/*` нужен отдельный admin-JWT: его выдаёт `POST /admin/token`
в обмен на заголовок `X-Admin-Key` (живёт `ADMIN_TOKEN_EXPIRE_HOURS`, 12 ч; лимит 10 запросов
в минуту). Токен устройства в админку не пускает (403), admin-токен не работает как токен
устройства. Ответы сжимаются gzip, если клиент шлёт `Accept-Encoding: gzip` (полный `/sync`
уменьшается примерно в 10 раз).
Ошибки всегда приходят в одном формате:

```json
{"error": {"code": "DUPLICATE_REPORT", "message": "This device already reported this number today"}}
```

Коды ошибок: `UNAUTHORIZED` 401, `FORBIDDEN` 403, `NOT_FOUND` 404, `DUPLICATE_REPORT` 409,
`VALIDATION_ERROR` / `INVALID_PHONE` 422, `INVALID_CURSOR` 400, `RATE_LIMITED` 429,
`ASSISTANT_UNAVAILABLE` 503.

Лимиты считаются на устройство: `/report` 10 в час, `/check-number` 60 в минуту,
`/assistant/chat` 20 в час, остальное 120 в минуту, общие для всех воркеров через Redis. Номера можно присылать в любом формате (`069 123 456`, `+373 69 123456`).
По умолчанию используется регион MD, в БД хранится только E.164.

```bash
B=http://localhost:8000/api/v1
ADMIN_API_KEY=change-me-admin-key   # значение из .env

# Здоровье
curl -s http://localhost:8000/health

# Регистрация устройства → JWT
TOKEN=$(curl -s -X POST $B/auth/device -H 'Content-Type: application/json' \
  -d '{"device_id":"6f1c2a1e-1111-4a3b-9c1d-000000000001"}' | jq -r .access_token)
AUTH="Authorization: Bearer $TOKEN"

# Проверка номера
curl -s -X POST $B/check-number -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"phone":"069000777"}'
# {"phone":"+37369000777","risk_level":"UNKNOWN","risk_score":0,"campaign_id":null,"campaign_type":null,"reports_count":0}

# Репорт (free_text необязателен и не сохраняется)
curl -s -X POST $B/report -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"phone":"069000777","category":"BANK","actions":["OTP","URGENCY"],"free_text":"Звонили из банка, просили код из СМС"}'
# {"status":"accepted"}

# Синхронизация: полный снимок, страницы, дельта
curl -s "$B/sync?limit=500" -H "$AUTH"
curl -s "$B/sync?limit=500&cursor=<next_cursor>" -H "$AUTH"
curl -s "$B/sync?since=2026-10-03T10:00:00Z" -H "$AUTH"

# ИИ-помощник: приложение каждый раз шлёт весь диалог (до 20 сообщений по 1000 символов),
# последнее сообщение — от пользователя. Диалог не сохраняется и не логируется.
curl -s -X POST $B/assistant/chat -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"Мне позвонили из банка и просят код из SMS. Что делать?"}]}'
# {"reply":"Это мошенники: банк никогда не просит коды из SMS. Положите трубку ..."}

# Обратная связь по предупреждению
curl -s -X POST $B/feedback -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"phone":"069000777","was_correct":true}'

# Кампании
curl -s "$B/campaigns" -H "$AUTH"
curl -s "$B/campaigns/1" -H "$AUTH"

# Номера с фильтрами
curl -s "$B/numbers?risk_level=HIGH&limit=20&offset=0" -H "$AUTH"
curl -s "$B/numbers?campaign_id=1" -H "$AUTH"

# Админка
ADMIN="Authorization: Bearer $(curl -s -X POST $B/admin/token -H "X-Admin-Key: $ADMIN_API_KEY" | jq -r .access_token)"
curl -s $B/admin/stats -H "$ADMIN"
curl -s "$B/admin/reports?category=BANK&limit=20" -H "$ADMIN"     # лента жалоб (фильтры: category, phone, campaign_id, since)
curl -s "$B/admin/activity?days=30" -H "$ADMIN"                    # жалобы, жалобщики и новые номера по дням
curl -s -X POST $B/admin/recalculate -H "$ADMIN"
curl -s -X POST $B/admin/numbers/+37369000777/remove -H "$ADMIN"   # ложное срабатывание
curl -s -X POST $B/admin/numbers/+37369000777/restore -H "$ADMIN"
```

## Демо-сценарий

Seed создаёт 90 номеров (12 в трёх кампаниях, 8 явных мошенников, 30 подозрительных,
40 обычных с одной жалобой) и печатает 10 неизвестных номеров. Кампании
(Bank + OTP, Police + TRANSFER, Delivery + CARD_DATA) находит сам campaign engine,
в сид они не зашиты. Демо-номер `+37369000777` остаётся без данных.

```bash
docker compose exec api python -m scripts.seed --reset     # локально: python -m scripts.seed --reset
```

**Шаг 1. Новый номер неизвестен.**

```bash
B=http://localhost:8000/api/v1
AUTH="Authorization: Bearer $(curl -s -X POST $B/auth/device -H 'Content-Type: application/json' \
  -d '{"device_id":"00000000-0000-4000-8000-0000000000de"}' | jq -r .access_token)"
curl -s -X POST $B/check-number -H "$AUTH" -H 'Content-Type: application/json' -d '{"phone":"+37369000777"}'
# risk_level: UNKNOWN
```

**Шаг 2. Первая жалоба от пользователя A** (Bank + OTP). Одной жалобы мало для кампании, уровень LOW.

```bash
TA=$(curl -s -X POST $B/auth/device -H 'Content-Type: application/json' -d '{"device_id":"aaaaaaaa-0000-4000-8000-000000000001"}' | jq -r .access_token)
curl -s -X POST $B/report -H "Authorization: Bearer $TA" -H 'Content-Type: application/json' \
  -d '{"phone":"+37369000777","category":"BANK","actions":["OTP","URGENCY"]}'
# check-number → LOW, score 10, campaign_id null
```

**Шаг 3. Похожая жалоба от независимого пользователя B.** Теперь 2 независимых похожих
репорта, номер привязывается к кампании «Bank impersonation + OTP, URGENCY». Уровень MEDIUM:
анти-накрутка не даёт HIGH, пока жалобщиков меньше трёх.

```bash
TB=$(curl -s -X POST $B/auth/device -H 'Content-Type: application/json' -d '{"device_id":"bbbbbbbb-0000-4000-8000-000000000002"}' | jq -r .access_token)
curl -s -X POST $B/report -H "Authorization: Bearer $TB" -H 'Content-Type: application/json' \
  -d '{"phone":"+37369000777","category":"BANK","actions":["OTP"],"free_text":"Сказали, что карта заблокирована, просили код"}'
# check-number → MEDIUM, score 59, campaign_id 1, campaign_type BANK
```

**Шаг 4. Приложение получает обновление.**

```bash
curl -s "$B/sync?since=<server_time из прошлой синхронизации>" -H "$AUTH"
# {"phone":"+37369000777","risk_level":"MEDIUM","campaign_type":"BANK","removed":false,...}
```

**Шаг 5 (по желанию).** Третий жалобщик, и номер становится HIGH. Проверить, что повторный
репорт с того же устройства отклоняется: снова отправить шаг 2, получить `409 DUPLICATE_REPORT`.

Без curl те же шаги 2, 3 и 5 выполняет `--demo-step`: каждый вызов добавляет жалобу
от нового устройства и печатает результат проверки.

```bash
docker compose exec api python -m scripts.seed --demo-step   # локально: python -m scripts.seed --demo-step
```

Флаги seed: `--reset` очищает БД перед заполнением, `--seed N` задаёт другой набор случайных
номеров, `--create-tables` создаёт таблицы без Alembic (быстрый старт на SQLite).

## Конфигурация

Все переменные перечислены в корневом `.env.example`. Самые важные:
`DATABASE_URL`, `JWT_SECRET`, `ADMIN_API_KEY`, `GEMINI_API_KEY`, `GEMINI_MODEL`,
`REDIS_URL`, `RATE_LIMIT_*`, `RECALC_INTERVAL_MINUTES`, `FULL_RECALC_HOUR_UTC`,
`REPORT_GRACE_DAYS`, `REPORT_HALF_LIFE_DAYS`, `SCHEDULER_ENABLED`.

При `APP_ENV=production` сервер не запустится, если `JWT_SECRET` или `ADMIN_API_KEY` содержат
`change-me` или короче 32 символов.

Для дашборда: CORS открыт (`CORS_ORIGINS`). Дашборд получает admin-JWT через `/admin/token`
и берёт данные из `/admin/stats` (карточки), `/admin/activity` (график), `/admin/reports`
(раздел Complaints). Сейчас дашборд показывает захардкоженные данные и к API не подключён.

## Ограничения (хакатон)

- `device_id` выдаёт себе сам клиент. От массовой накрутки защищают лимиты, один голос на
  устройство, взвешивание по `reputation` и потолок MEDIUM. Для продакшена нужна аттестация
  устройства (Play Integrity).
- Лимиты и кэш fingerprint'ов хранятся в Redis, если задан `REDIS_URL`; без него — в памяти
  процесса, и тогда при нескольких воркерах каждый считает лимиты сам. Если Redis падает,
  лимиты временно считаются в памяти, жалобы продолжают приниматься. Redis без persistence:
  при рестарте счётчики и кэш обнуляются, это допустимо.
- Feedback учитывается в `reputation` репортеров (подтверждение +0.1, ложное срабатывание -0.2)
  и немедленно пересчитывает скоринг номера. Самооценка репорта отклоняется, а уникальность
  голоса дополнительно гарантируется ограничением в базе данных.
