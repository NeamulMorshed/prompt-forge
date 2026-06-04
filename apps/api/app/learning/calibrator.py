import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db.models import OutcomeRating

logger = logging.getLogger(__name__)


def calibrate_crs_weights(db: Session, domain: str, lookback_days: int = 30) -> dict:
    """Analyze outcomes by domain to update slot weights.

    Phase 2: stub implementation. Phase 3 will implement ML-based weight adjustment
    based on correlation between slots and outcome quality.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    ratings = db.query(OutcomeRating).filter(
        OutcomeRating.created_at >= cutoff,
        OutcomeRating.domain == domain,
    ).all()

    if not ratings:
        logger.info(f"No outcomes for {domain} in past {lookback_days} days")
        return {}

    good_ratings = [r for r in ratings if r.rating > 0]
    if not good_ratings:
        logger.info(f"No positive outcomes for {domain}")
        return {}

    logger.info(f"Calibrated CRS for {domain}: {len(good_ratings)} good outcomes")
    return {}


def calibrate_scorer(db: Session, lookback_days: int = 30) -> dict:
    """Analyze correlation between scored dimensions and actual outcomes.

    Phase 2: stub implementation. Phase 3 will compute Pearson correlation
    between each score dimension and outcome label, adjust rubric weights.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    ratings = db.query(OutcomeRating).filter(OutcomeRating.created_at >= cutoff).all()

    if not ratings:
        logger.info("No outcomes for scorer calibration")
        return {}

    logger.info(f"Calibrated scorer: analyzed {len(ratings)} outcomes")
    return {}
