import logging
import os
import time

from apscheduler.schedulers.background import BackgroundScheduler

from .db import engine
from .models import Base
from .service import backfill_history, ingest_external_forecast, ingest_recent

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s | %(message)s")
log = logging.getLogger("ingestor")


def main():
    log.info("creating tables if not exist")
    Base.metadata.create_all(engine)

    log.info("running initial backfill (this can take a while on first run)")
    backfill_history()
    ingest_recent()
    ingest_external_forecast()

    current_interval = int(os.environ.get("INGEST_CURRENT_INTERVAL_MIN", "60"))
    forecast_interval = int(os.environ.get("INGEST_FORECAST_INTERVAL_HOURS", "6"))

    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(ingest_recent, "interval", minutes=current_interval, id="recent")
    scheduler.add_job(
        ingest_external_forecast, "interval", hours=forecast_interval, id="gismeteo"
    )
    scheduler.start()
    log.info(
        "scheduler started: recent every %dmin, gismeteo every %dh",
        current_interval, forecast_interval,
    )

    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()


if __name__ == "__main__":
    main()
