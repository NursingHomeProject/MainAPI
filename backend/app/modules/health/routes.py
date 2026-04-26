from fastapi import APIRouter

from app.db.session import check_database_connection

router = APIRouter()


@router.get("/health", summary="Application health check")
def health_check() -> dict[str, str | bool]:
    database_ok = check_database_connection()
    return {
        "status": "ok" if database_ok else "degraded",
        "database": database_ok,
    }
