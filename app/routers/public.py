from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.config import PUBLIC_STATS_TTL_SECONDS
from app.database import get_db
from app.services.public_stats import get_cache

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/stats")
def public_stats(response: Response, db: Session = Depends(get_db)):
    """Aggregated, non-identifying dashboard stats. Cached for
    PUBLIC_STATS_TTL_SECONDS to absorb traffic spikes.
    """
    stats = get_cache().get(db)
    response.headers["Cache-Control"] = f"public, max-age={PUBLIC_STATS_TTL_SECONDS}"
    return stats.to_dict()
