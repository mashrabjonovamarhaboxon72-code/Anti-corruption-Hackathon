from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import config
from app.database import get_db
from app.services.demo_seed import reset_database, seed_demo_state

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/demo-setup", status_code=status.HTTP_200_OK)
def demo_setup(db: Session = Depends(get_db)):
    """Wipe the data plane and re-seed a known demo state.

    Gated by the DEMO_MODE env var — refuses to run unless explicitly
    enabled. NEVER set DEMO_MODE in production: this endpoint is
    destructive and unauthenticated by design (you can't auth before
    any users exist).
    """
    if not config.DEMO_MODE:
        raise HTTPException(
            status_code=403,
            detail=(
                "Demo setup is disabled. Set DEMO_MODE=1 in the environment "
                "to enable. This endpoint wipes all data and must never run "
                "in production."
            ),
        )

    cleared = reset_database(db)
    state = seed_demo_state(db)
    return {
        "cleared": cleared,
        "demo_state": state,
        "warning": "All previous data has been deleted. This response carries the only copy of the recovery mnemonic.",
    }
