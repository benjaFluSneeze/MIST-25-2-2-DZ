# WeatherML

Семестровый проект MISIS_2025 (season 2) — тема **WeatherML: Прогноз погоды**.

Веб-сервис собирает погодные данные из нескольких источников, обучает ML-модели и
показывает их прогнозы в интерактивном дашборде. Всё разворачивается одной командой.

## Скриншоты

| | |
|:-:|:-:|
| ![Home](docs/screenshots/01_home.png) | ![Overview](docs/screenshots/02_overview.png) |
| Главная страница | Overview — KPI и графики |
| ![Predictions](docs/screenshots/03_predictions.png) | ![Analytics](docs/screenshots/04_analytics.png) |
| Predictions — what-if форма | Analytics — сравнение городов |
| ![Data](docs/screenshots/05_data.png) | ![Monitoring](docs/screenshots/06_monitoring.png) |
| Data — таблица с фильтрами | Monitoring — статус источников |

## Стек

- **Data**: `requests`, `BeautifulSoup4`, `APScheduler`, Open-Meteo / OpenWeatherMap / Gismeteo
- **Storage**: PostgreSQL 16, SQLAlchemy 2.0
- **ML**: pandas, scikit-learn, CatBoost, joblib
- **API**: FastAPI + Pydantic + uvicorn
- **UI**: Streamlit + Plotly
- **Infra**: Docker, docker-compose, pytest

## Архитектура

```
+-----------+      +------------+      +-----------+      +-------------+
| ingestor  | ---> | PostgreSQL | <--- |   api     | <--- |  dashboard  |
| (sched.)  |      |            |      | (FastAPI) |      |  (Streamlit)|
+-----------+      +------------+      +-----------+      +-------------+
       |                                                         |
       v                                                         v
Open-Meteo (archive + recent)                          http://localhost:8501
OpenWeatherMap (current)                               http://localhost:8000/docs
Gismeteo (BeautifulSoup parser)
```

## Что собирается

- **Города**: Москва, СПб, Екатеринбург, Новосибирск, Казань, Сочи, Владивосток (см. `services/ingestor/src/cities.py`).
- **Глубина истории**: 2 года (настраивается через `INGEST_BACKFILL_YEARS`).
- **Источники**:
  - Open-Meteo Archive API — историческая часовая погода (основа обучения)
  - Open-Meteo Forecast API — свежая погода (раз в час)
  - OpenWeatherMap — текущая погода (если задан `OPENWEATHER_API_KEY`)
  - Gismeteo — официальный прогноз на завтра через парсинг (для сравнения)

## Быстрый старт

```bash
cp .env.example .env
# при желании — впишите OPENWEATHER_API_KEY (бесплатный)
docker compose up --build
```

После старта:

- API: <http://localhost:8000>, Swagger: <http://localhost:8000/docs>
- Dashboard: <http://localhost:8501>

Первый запуск занимает 5–15 минут — ingestor качает 2 года истории по 7 городам.

## Обучение моделей

После того как ingestor собрал данные, обучите модели локально (внутри проекта или в venv):

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r ml/requirements.txt

export DATABASE_URL=postgresql+psycopg2://weather:weather@localhost:5432/weatherml
python -m ml.training.train
```

Артефакты появятся в `ml/artifacts/` (`temp_model.joblib`, `rain_model.joblib`,
`condition_model.joblib`, `metrics.json`). API смонтирует эту папку только для
чтения и подхватит модели. Чтобы перезагрузить без рестарта:

```bash
curl -X POST http://localhost:8000/admin/reload-models
```

## Эндпоинты API

- `GET /health` — статус БД и моделей
- `GET /data/cities` — список городов
- `GET /data/observations?city_id=&hours=&source=` — часовые наблюдения
- `GET /data/forecasts?city_id=` — внешние прогнозы (Gismeteo)
- `GET /data/ingest-runs` — журнал работы ingestor
- `POST /predict` — прогноз нашей модели (тело: `{"city_id": 1, "horizon_hours": 6}`)
- `GET /predict/metrics` — CV-метрики моделей
- `GET /predict/feature-importance/{model_name}` — важность признаков
  (`model_name` ∈ `temperature` / `rain` / `condition`)

## Страницы дашборда

1. **Overview** — KPI и графики выбранного города за неделю
2. **Predictions** — наш прогноз vs Gismeteo, метрики, feature importance
3. **Analytics** — сравнение городов, сезонность, аномалии
4. **Data** — таблица сырых наблюдений с фильтрами и поиском
5. **Monitoring** — статус источников данных и логи ingestor

## ML-задачи

| Задача | Тип | Метрика | Naive baseline |
|---|---|---|---|
| Температура через N часов | Регрессия (CatBoost) | MAE / RMSE | `T(t+H) = T(t)` |
| Будет ли дождь через N часов | Бинарная классификация | Accuracy / F1 | majority-class |
| Тип погоды через N часов | Мультикласс | Accuracy / macro-F1 | `condition(t+H) = condition(t)` |

Валидация — `TimeSeriesSplit` (4 фолда), чтобы не было утечек будущего.

## Тесты

```bash
pip install pytest
pytest tests/
```

Тесты — smoke-уровня (feature engineering, парсер Open-Meteo), без сетевых вызовов.

## Структура проекта

```
.
├── docker-compose.yml
├── .env.example
├── services/
│   ├── ingestor/     # сбор данных + APScheduler
│   ├── api/          # FastAPI: /health, /data, /predict
│   └── dashboard/    # Streamlit (5 страниц)
├── ml/
│   ├── features.py        # общая логика признаков
│   ├── training/train.py  # обучение 3 моделей
│   ├── notebooks/01_eda.ipynb
│   └── artifacts/         # сохранённые .joblib (монтируется в api)
└── tests/
```

## Деплой на VPS (с HTTPS)

Дополнительный compose-файл `docker-compose.prod.yml` поднимает [Caddy](https://caddyserver.com)
как reverse-proxy с автоматическим Let's Encrypt и прячет внутренние сервисы
(api, dashboard, db) от публичного интернета — наружу торчат только 80/443.

**Что нужно от VPS:** 4 GB RAM, 20 GB диск, открытые порты 80 и 443.
Доменное имя не обязательно — `nip.io` даёт бесплатное wildcard-резолвление
по IP-адресу.

```bash
# 1. На VPS, в свободной директории:
git clone <публичный-репозиторий-url> weatherml
cd weatherml

# 2. Готовим .env (замените значения):
cp .env.example .env
nano .env   # обязательно: DOMAIN_BASE, DB_PASSWORD, OPENWEATHER_API_KEY
# Пример:
#   DOMAIN_BASE=203.0.113.42.nip.io
#   DB_PASSWORD=<длинный-случайный-пароль>
#   LETSENCRYPT_EMAIL=you@example.com

# 3. Поднимаем стек с прод-оверлеем:
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# 4. Ждём первый бэкфилл (~5-10 минут):
docker compose logs -f ingestor   # Ctrl+C когда увидите "Scheduler started"

# 5. Обучаем модели (~10 минут на VPS):
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
    run --rm -v "$PWD/ml:/app/ml" api python -m ml.training.train

# 6. Перегружаем модели в API (curl изнутри сети, наружу /admin не нужен):
docker compose exec api python -c "import urllib.request; \
    urllib.request.urlopen('http://localhost:8000/admin/reload-models', data=b'')"
```

Готово. Открывай в браузере:

* `https://weather.<DOMAIN_BASE>/` — это и есть ссылка для препода
* `https://api.<DOMAIN_BASE>/docs` — Swagger

Первый раз Caddy получит SSL-сертификат от Let's Encrypt за ~30 секунд.

### Если хочешь свой нормальный домен

Создаёшь A-запись `weather.example.com → <IP-VPS>` и `api.weather.example.com → <IP-VPS>`,
в `.env` ставишь `DOMAIN_BASE=weather.example.com`. Дальше идентично.

## Известные ограничения

- Парсер Gismeteo может ломаться при изменении вёрстки сайта — это допустимо для
  учебного проекта, БД хранит все ранее собранные прогнозы.
- OpenWeatherMap опционален — без ключа в `.env` источник просто пропускается.
- Первая загрузка истории — единоразово; повторные запуски ingestor её не дублируют.
