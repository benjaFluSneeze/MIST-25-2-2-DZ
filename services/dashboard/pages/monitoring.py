from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from common import get_ingest_runs, source_ru

SOURCE_LABELS = {
    "open_meteo_backfill": "Open-Meteo: историческая выгрузка",
    "recent": "Open-Meteo + OpenWeather: свежие данные",
    "gismeteo": "Gismeteo: парсинг прогноза",
}

STATUS_RU = {"ok": "успех", "error": "ошибка", "running": "выполняется"}


def _source_label(name: str) -> str:
    return SOURCE_LABELS.get(name, source_ru(name))


from theme import eyebrow

eyebrow("Мониторинг")
st.markdown('<h2 style="margin: 0 0 24px;">Статус источников данных</h2>',
            unsafe_allow_html=True)

try:
    runs = get_ingest_runs(limit=50)
except Exception as e:  # noqa: BLE001
    st.error(f"Не удалось получить журнал сбора: {e}")
    st.stop()

if not runs:
    st.info("Сборщик данных ещё не делал запусков.")
    st.stop()

df = pd.DataFrame(runs)
df["started_at"] = pd.to_datetime(df["started_at"], utc=True)
df["finished_at"] = pd.to_datetime(df["finished_at"], utc=True)

st.subheader("Статус источников данных")
status_per_source = (
    df.sort_values("started_at", ascending=False)
    .groupby("source")
    .first()
    .reset_index()
)
cols = st.columns(len(status_per_source))
now = datetime.now(timezone.utc)
for i, row in status_per_source.iterrows():
    with cols[i]:
        ok = row["status"] == "ok"
        emoji = "🟢" if ok else "🔴"
        hours_ago = (now - row["started_at"]).total_seconds() / 3600
        st.metric(
            f"{emoji} {_source_label(row['source'])}",
            STATUS_RU.get(row["status"], row["status"]),
            help=f"{hours_ago:.1f} ч назад · добавлено строк: {row['rows_inserted']}",
        )

st.subheader("Последние 50 запусков")
df_show = df[["source", "started_at", "finished_at", "status", "rows_inserted", "error"]].copy()
df_show["source"] = df_show["source"].map(_source_label)
df_show["status"] = df_show["status"].map(lambda s: STATUS_RU.get(s, s))
df_show = df_show.rename(
    columns={
        "source": "Источник",
        "started_at": "Начало",
        "finished_at": "Завершение",
        "status": "Статус",
        "rows_inserted": "Добавлено строк",
        "error": "Ошибка",
    }
)
st.dataframe(df_show, use_container_width=True, hide_index=True)
