# Тесты SafeCall backend

394 теста: 165 unit, 180 api, 30 security, 10 perf, 9 e2e. Восемь из них помечены
`xfail(strict=True)` с пометкой `BUG:`. Это найденные дефекты, тесты под них не подгонялись.
Когда баг исправят, тест начнёт проходить, а `strict=True` уронит прогон, пока не снимут пометку.

Сети в тестах нет: pytest-socket пропускает только loopback. Gemini подменён: если тест дойдёт
до настоящего клиента, он упадёт. Время управляется через фикстуру `clock` (freezegun),
случайность зафиксирована: Hypothesis запускается с `derandomize`, генераторы — с явным seed.

## Структура

```
tests/
├── conftest.py            # БД на каждый тест, запрет реального Gemini, clock, limiter_on, auth-хелперы
├── factories.py           # устройства, номера, жалобы, кампании; хелперы API
├── check_coverage.py      # пороги покрытия (ядро ≥ 95%, всё ≥ 85%)
├── unit/                  # движки риска/кампаний, fingerprint, нормализация, общие векторы, Hypothesis
├── api/                   # каждый эндпоинт: позитивные, граничные, ≥ 3 негативных; контракт OpenAPI
├── security/              # SQL-инъекции, лимиты со сбросом по времени, накрутка, приватность логов и БД
├── perf/                  # N+1 (счётчик SQL), индексы, задержки на 100 000 номеров; locustfile.py
└── e2e/                   # alembic up/down, seed, демо-сценарий через публичный API
../../shared/test_vectors.json   # общие векторы номеров, маскирования, Жаккара и рисков для Python/Dart/Kotlin
../scripts/demo_e2e.py           # тот же демо-сценарий против живого сервера
```

## Запуск

```bash
cd backend
pip install -r requirements-dev.txt

pytest -m "unit or api"            # быстрый набор, ~16 с (лимит в CI — 60 с)
pytest -m security
pytest -m e2e
pytest -m perf                     # 100k номеров, ~10 с на SQLite
pytest                             # всё

pytest --cov=app --cov-report=json && python tests/check_coverage.py coverage.json
ruff check app scripts tests && mypy app
```

На PostgreSQL (как в CI, джоб `test-postgres`):

```bash
docker compose up -d postgres
TEST_DATABASE_URL=postgresql+asyncpg://safecall:safecall@localhost:5432/safecall pytest -m "not perf and not e2e"
```

Тесты пересоздают таблицы в этой базе, поэтому используйте отдельную базу, не рабочую.

## Демо перед защитой

```bash
docker compose exec api python -m scripts.seed --reset
python -m scripts.demo_e2e --base-url http://localhost:8000 --admin-key "$ADMIN_API_KEY"
```

Каждый шаг проверяется утверждением. При первой ошибке скрипт печатает `DEMO FAILED: …` и
завершается с кодом 1, при успехе печатает `DEMO OK`. Шаги: кампания из seed → номер кампании
🔴 → новый номер ⚪ → две жалобы с разных устройств → привязка к кампании, MEDIUM →
синк → 🟠 «Номер новый, но обнаружены признаки…».

## Нагрузка

```bash
RATE_LIMIT_ENABLED=false uvicorn app.main:app --workers 2 &
locust -f tests/perf/locustfile.py --host http://localhost:8000 \
       --users 200 --spawn-rate 20 --run-time 3m --headless --csv perf
```

Смесь запросов: 70% check-number, 20% sync-дельта, 10% report. Критерии: нет 5xx,
p95 check-number < 200 мс, p95 sync < 500 мс. В CI это ручной workflow `perf (manual)`
на PostgreSQL, критерии он проверяет сам. Локальный прогон (30 пользователей, SQLite)
показал 0 ошибок и p95 check-number 6 мс.

## Golden-файлы, Flutter, Kotlin

В репозитории пока нет ни Flutter-приложения, ни Android-модуля, поэтому разделы B и C плана
(widget/golden/integration-тесты, Robolectric) писать не к чему. Когда код появится, они должны
гонять `shared/test_vectors.json`: тот же вход обязан давать тот же E.164 и тот же уровень риска,
иначе номер из локальной базы не найдётся во время звонка.

## Найденные баги и риски

| Приоритет | Что | Где проверяется |
|---|---|---|
| Высокий | Отзывы (feedback) обеляют номер: 5 новых `device_id` с «ложным срабатыванием» сбрасывают репутацию жалобщиков, и номер опускается с MEDIUM | `security/test_abuse.py::test_feedback_cannot_whitewash_a_scam_number` (xfail) |
| Высокий | 50 согласованных новых устройств выводят легальный (банковский) номер в HIGH: нет allowlist и аттестации устройств | `security/test_abuse.py::test_fifty_coordinated_…` (xfail) |
| Высокий | Номер целиком попадает в логи: текст ошибки SQLAlchemy содержит параметры запроса (`hide_parameters=True`) | `security/test_privacy.py::test_database_errors_do_not_carry_phone_numbers` (xfail) |
| Высокий | Номер в URL админских эндпоинтов (`/admin/numbers/{phone}/…`, `?phone=`) — uvicorn access log пишет его целиком | `security/test_privacy.py::test_no_endpoint_takes_a_phone_number_in_the_url` (xfail) |
| Высокий | Жалобы «Другое» без действий собираются в кампанию «Phone scam» (риск 70, +21 балл посторонним номерам) | `unit/test_campaign_rules.py::test_other_without_actions_never_forms_a_campaign` (xfail) |
| Средний | Риск не монотонен: новая непохожая жалоба снижает долю сходства (3 одинаковые = 40, плюс 4-я другая = 35) | `unit/test_risk_properties.py::test_new_unique_report_never_lowers_risk` (xfail, найдено Hypothesis) |
| Средний | N+1 в `/report`: жалоба на номер из кампании пересчитывает каждого участника по отдельности (2 запроса на номер) | `perf/test_query_counts.py::test_report_into_a_campaign_uses_constant_queries` (xfail) |
| Средний | Противоречие в ТЗ демо: жалобы «BANK + OTP + SUSPICIOUS_TRANSACTION» не похожи на кампанию {BANK, OTP, URGENCY} (Жаккар 0.5), а 3 жалобщика по правилу 4 дают HIGH, а не MEDIUM | `e2e/test_demo_scenario.py::test_demo_as_written_in_the_brief` (xfail) |
| Средний | Гонка счётчиков на PostgreSQL: при READ COMMITTED параллельные жалобы могут не увидеть друг друга в `reports_count`. На SQLite не воспроизводится | `api/test_report.py::test_twenty_parallel_reports_on_one_new_number` — запускается в джобе `test-postgres` |
| Низкий | При `LOG_LEVEL=debug` или `DB_ECHO=true` драйверы пишут SQL с параметрами, то есть номера целиком | вручную: не включать в production |
| Низкий | Короткие номера (112, 900, короткие коды банков) не нормализуются (422): на них нельзя пожаловаться | `shared/test_vectors.json` |
| Низкий | У feedback нет уникального ключа (устройство, номер): два параллельных запроса на PostgreSQL создадут дубль, и он посчитается дважды. На SQLite не воспроизводится, тест появится вместе с миграцией | см. трекер в отчёте |

## Что проверяется только вручную

- Реальные ответы Gemini (качество тегов, тон помощника, румынский язык): в тестах Gemini подменён.
- Работа под нагрузкой на настоящем железе и PostgreSQL (`perf (manual)` в CI даёт только ориентир).
- Логи uvicorn/прокси в развёрнутом окружении: тесты проверяют логи приложения, но не access log сервера.
- Ротация `JWT_SECRET` и `ADMIN_API_KEY`, выход из строя Redis в production.
- Всё, что касается приложения и Android: роль call screening, уведомления, работа без сети, матрица Android 10/12/13/14.
