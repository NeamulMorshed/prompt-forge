import logging
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from app.db.base import SessionLocal
from app.learning.calibrator import calibrate_crs_weights, calibrate_scorer

logger = logging.getLogger(__name__)


def weekly_learning_job():
    """Run weekly calibration across all active domains."""
    db: Session | None = None
    try:
        db = SessionLocal()
        domains = ["marketing_content", "writing_academic"]
        for domain in domains:
            logger.info(f"Calibrating CRS weights for {domain}")
            calibrate_crs_weights(db, domain)
        logger.info("Calibrating scorer dimensions")
        calibrate_scorer(db)
    except Exception as e:
        logger.exception(f"Learning job failed: {e}")
    finally:
        if db:
            db.close()


def start_scheduler() -> BackgroundScheduler:
    """Start background scheduler for learning loop.

    Runs every Sunday at 2 AM UTC.
    """
    scheduler = BackgroundScheduler()
    scheduler.add_job(weekly_learning_job, "cron", day_of_week=6, hour=2, minute=0)
    scheduler.start()
    logger.info("Learning loop scheduler started (runs Sundays 02:00 UTC)")
    return scheduler
