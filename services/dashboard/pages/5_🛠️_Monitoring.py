from datetime import datetime, timezone
import pandas as pd
import streamlit as st

from _common import get_ingest_runs

st.title("🛠️ Monitoring")

try:
    runs = get_ingest_runs(limit=50)
except Exception as e:  # noqa: BLE001
    st.error(f"Не удалось получить логи ingestor: {e}")
    st.stop()

if not runs:
    st.info("Ingestor ещё не делал запусков.")
    st.stop()

df = pd.DataFrame(runs)
df["started_at"] = pd.to_datetime(df["started_at"], utc=True)
df["finished_at"] = pd.to_datetime(df["finished_at"], utc=True)

st.subheader("Статус источников")
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
        delta = now - row["started_at"]
        hours = delta.total_seconds() / 3600
        st.metric(
            f"{emoji} {row['source']}",
            row["status"],
            help=f"{hours:.1f} часов назад · вставлено {row['rows_inserted']} строк",
        )

st.subheader("Последние 50 запусков")
df_show = df[["source", "started_at", "finished_at", "status", "rows_inserted", "error"]].copy()
st.dataframe(df_show, use_container_width=True)
