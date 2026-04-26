"""Background scheduler for periodic maintenance.

Currently runs the RI recalculator every RI_RECALC_INTERVAL_SECONDS. We
use asyncio rather than APScheduler/Celery to keep the dep tree small;
upgrade if more jobs land here.
"""

import asyncio
import logging
import os

from app.database import SessionLocal
from app.services.reliability import recalculate_pending

logger = logging.getLogger("integrity_shield.background")

RI_RECALC_INTERVAL_SECONDS = int(os.getenv("RI_RECALC_INTERVAL_SECONDS", "30"))


async def ri_recalc_loop() -> None:
    while True:
        try:
            db = SessionLocal()
            try:
                changes = recalculate_pending(db)
                if changes:
                    logger.info("RI recalc applied %d change(s).", len(changes))
            finally:
                db.close()
        except Exception:
            logger.exception("RI recalc loop iteration failed; will retry.")
        await asyncio.sleep(RI_RECALC_INTERVAL_SECONDS)


_task: asyncio.Task | None = None


def start() -> None:
    global _task
    if _task is None or _task.done():
        _task = asyncio.create_task(ri_recalc_loop(), name="ri_recalc_loop")


def stop() -> None:
    global _task
    if _task and not _task.done():
        _task.cancel()
        _task = None
