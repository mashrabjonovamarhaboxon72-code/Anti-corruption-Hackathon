from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app import config
from app.database import get_db
from app.services.demo_seed import reset_database, seed_demo_state

router = APIRouter(prefix="/admin", tags=["admin"])


@router.api_route(
    "/demo-setup",
    methods=["GET", "POST"],
    status_code=status.HTTP_200_OK,
)
def demo_setup(response: Response, db: Session = Depends(get_db)):
    """Wipe the data plane and re-seed a known demo state.

    Gated by the DEMO_MODE env var — refuses to run unless explicitly
    enabled. NEVER set DEMO_MODE in production: this endpoint is
    destructive and unauthenticated by design (you can't auth before
    any users exist).

    Accepts GET as well as POST so a presenter can fire it from the
    address bar in the middle of a demo. The trade-off: GET is normally
    "safe" in HTTP semantics (no side effects) and this endpoint
    decidedly is not. Cache-Control headers below tell browsers and
    CDNs not to cache the response — so the back-button doesn't silently
    re-fire a wipe — but the GET path remains exposed to link-preview
    bots, browser pre-fetch, and CSRF. Keep DEMO_MODE off in any
    environment where you don't want any of those triggering a wipe.
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

    # Block every layer of caching that could re-serve a stale "ok" without
    # actually re-running the wipe — protects the back-button and any CDN.
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"

    cleared = reset_database(db)
    state = seed_demo_state(db)
    return {
        "cleared": cleared,
        "demo_state": state,
        "warning": "All previous data has been deleted. This response carries the only copy of the recovery mnemonic.",
    }
