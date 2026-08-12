from fastapi import APIRouter

from app.api.v1.races import router as races_router
from app.api.v1.simulate import router as simulate_router

router = APIRouter()
router.include_router(races_router)
router.include_router(simulate_router)


@router.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Liveness check used by local dev, and later by container/K8s probes."""
    return {"status": "ok"}
