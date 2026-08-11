from fastapi import APIRouter

router = APIRouter()


@router.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Liveness check used by local dev, and later by container/K8s probes."""
    return {"status": "ok"}
