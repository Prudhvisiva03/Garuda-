from fastapi import APIRouter
from pydantic import BaseModel
from backend.app.database import get_db

router = APIRouter(prefix="/audit", tags=["Audit Trail"])

class AuditEventResponse(BaseModel):
    id: str
    timestamp: str
    userId: str
    userName: str
    action: str
    resourceType: str
    resourceId: str
    details: str
    ipAddress: str
    isDemo: bool = False

@router.get("", response_model=list[AuditEventResponse])
def list_audit_events():
    """Retrieve immutable chain of custody audit logs ordered by latest first."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC;")
        rows = cursor.fetchall()
        return [
            AuditEventResponse(
                id=r["id"],
                timestamp=r["timestamp"],
                userId=r["user_id"],
                userName=r["user_name"],
                action=r["action"],
                resourceType=r["resource_type"],
                resourceId=r["resource_id"],
                details=r["details"],
                ipAddress=r["ip_address"],
                isDemo=False,
            )
            for r in rows
        ]
