from fastapi import APIRouter
from PIL import __version__ as pillow_version
from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models import HealthResponse

router = APIRouter(prefix="/health", tags=["Health & Diagnostics"])

@router.get("", response_model=HealthResponse)
def check_health():
    db_ok = False
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1;")
            db_ok = True
    except Exception:
        db_ok = False

    storage_ok = (
        settings.EVIDENCE_DIR.exists()
        and settings.ARTIFACTS_DIR.exists()
        and settings.REPORTS_DIR.exists()
    )

    return HealthResponse(
        status="operational" if (db_ok and storage_ok) else "degraded",
        app_name=settings.APP_NAME,
        version=settings.VERSION,
        pillow_version=pillow_version,
        database_status="connected" if db_ok else "error",
        storage_accessible=storage_ok,
        upload_limit_bytes=settings.MAX_UPLOAD_SIZE,
    )
