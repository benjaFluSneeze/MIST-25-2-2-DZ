# WeatherML

Семестровый проект MISIS_2025 (season 2) — **WeatherML: Прогноз погоды**.

Сервис собирает погодные данные из нескольких источников, обучает CatBoost-модели
на 8 горизонтов вперёд и показывает прогнозы в интерактивном дашборде. Разворачивается одной командой.

## Скриншоты

| | |
|:-:|:-:|
| ![Home](docs/screenshots/01_home.png) | ![Overview](docs/screenshots/02_overview.png) |
| ![Predictions](docs/screenshots/03_predictions.png) | ![Analytics](docs/screenshots/04_analytics.png) |
| ![Data](docs/screenshots/05_data.png) | ![Monitoring](docs/screenshots/06_monitoring.png) |

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

- **Города**: Москва, СПб, Екатеринбург, Новосибирск, Казань, Сочи, Владивосток (`services/ingestor/src/cities.py`).
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

После того как ingestor собрал данные, обучите модели локально:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r ml/requirements.txt

export DATABASE_URL=postgresql+psycopg2://weather:weather@localhost:5432/weatherml
python -m ml.training.train
```

Под каждый из 8 горизонтов (3, 6, 9, 12, 15, 18, 21, 24 ч) и под каждую из
3 задач обучается своя CatBoost-модель — итого 24 модели. Артефакты появятся
в `ml/artifacts/` (`temp_models.joblib`, `rain_models.joblib`,
`condition_models.joblib`, `metrics.json`). API смонтирует папку только для
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
- `POST /predict` — прогноз нашей модели (`{"city_id": 1, "horizon_hours": 6}`)
- `POST /predict/manual` — прогноз по введённым значениям (для what-if формы)
- `GET /predict/horizons` — список доступных горизонтов и горизонт по умолчанию
- `GET /predict/metrics` — CV-метрики моделей
- `GET /predict/feature-importance/{model_name}` — важность признаков
  (`temperature` / `rain` / `condition`)

## Страницы дашборда

1. **Главная** — лендинг с навигацией
2. **Обзор города** — KPI и графики за неделю
3. **Прогноз** — наш прогноз vs Gismeteo, метрики, feature importance, what-if форма
4. **Аналитика** — сравнение городов, сезонность, аномалии
5. **Данные** — таблица сырых наблюдений с фильтрами и поиском
6. **Мониторинг** — статус источников данных и логи ingestor

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
│   └── dashboard/    # Streamlit (6 страниц)
├── ml/
│   ├── features.py        # общая логика признаков
│   ├── training/train.py  # обучение 24 моделей (8 горизонтов × 3 задачи)
│   ├── notebooks/01_eda.ipynb
│   └── artifacts/         # *.joblib (монтируется в api только на чтение)
└── tests/
```

## Деплой на VPS (с HTTPS)

`docker-compose.prod.yml` поднимает [Caddy](https://caddyserver.com) как reverse-proxy
с автоматическим Let's Encrypt и прячет внутренние сервисы (api, dashboard, db) от
публичного интернета — наружу торчат только 80/443.

**Что нужно от VPS:** 4 GB RAM, 20 GB диск, открытые порты 80 и 443.
Доменное имя не обязательно — `nip.io` даёт wildcard-резолв по IP.

```bash
# 1. На VPS:
git clone <публичный-репозиторий-url> weatherml && cd weatherml
cp .env.example .env
nano .env   # обязательно: DOMAIN_BASE, DB_PASSWORD, LETSENCRYPT_EMAIL
# Пример DOMAIN_BASE: 203.0.113.42.nip.io

# 2. Поднимаем стек:
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# 3. Ждём первый бэкфилл (~5-10 мин), обучаем модели (~10 мин):
docker compose logs -f ingestor   # Ctrl+C когда увидите "Scheduler started"
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
    run --rm -v "$PWD/ml:/app/ml" api python -m ml.training.train

# 4. Перегружаем модели в API:
docker compose exec api python -c "import urllib.request; \
    urllib.request.urlopen('http://localhost:8000/admin/reload-models', data=b'')"
```

Открывай:

* `https://weather.<DOMAIN_BASE>/` — дашборд
* `https://api.<DOMAIN_BASE>/docs` — Swagger

Первый раз Caddy получит SSL-сертификат от Let's Encrypt за ~30 секунд.
Если нужен свой домен — создаёшь A-записи `weather.example.com` и
`api.weather.example.com` на IP VPS, в `.env` ставишь `DOMAIN_BASE=weather.example.com`.

## Известные ограничения

- Парсер Gismeteo может ломаться при изменении вёрстки сайта; БД хранит ранее собранные прогнозы.
- OpenWeatherMap опционален — без ключа в `.env` источник просто пропускается.
- Первая загрузка истории — единоразово; повторные запуски ingestor её не дублируют.
