import json
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from backend.app.database import get_db, record_audit_event

router = APIRouter(prefix="/cases", tags=["Case Management"])

class CaseCreateRequest(BaseModel):
    case_number: str = Field(..., description="Unique FIR / Case identifier, e.g. FIR-2026-112/CYBER")
    title: str = Field(..., description="Investigation subject / title")
    description: str = Field("", description="Summary of allegations or seized media source")
    priority: str = Field("high", description="'low' | 'medium' | 'high'")
    category: str = Field("Image Forensics", description="'Image Forensics' | 'Video Forensics' | 'Audio Forensics'")
    assigned_to: list[str] = Field(default_factory=lambda: ["Inspector S. Verma"])
    organization_id: str = Field("State Cyber Crime Investigation Division")

class CaseResponse(BaseModel):
    id: str
    case_number: str
    title: str
    description: str
    status: str
    priority: str
    category: str
    assigned_to: list[str]
    organization_id: str
    created_at: str
    updated_at: str
    evidence_count: int = 0

@router.get("", response_model=list[CaseResponse])
def list_cases():
    """List all registered forensic cases with live evidence counts from SQLite."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cases ORDER BY created_at DESC;")
        case_rows = cursor.fetchall()

        # Count evidence items per case
        cursor.execute("SELECT case_id, COUNT(*) as cnt FROM evidence GROUP BY case_id;")
        ev_counts = {row["case_id"]: row["cnt"] for row in cursor.fetchall()}

        result = []
        for c in case_rows:
            assigned = json.loads(c["assigned_to"]) if c["assigned_to"] else []
            count = ev_counts.get(c["case_number"], 0) or ev_counts.get(c["id"], 0)
            result.append(
                CaseResponse(
                    id=c["id"],
                    case_number=c["case_number"],
                    title=c["title"],
                    description=c["description"],
                    status=c["status"],
                    priority=c["priority"],
                    category=c["category"],
                    assigned_to=assigned,
                    organization_id=c["organization_id"],
                    created_at=c["created_at"],
                    updated_at=c["updated_at"],
                    evidence_count=count,
                )
            )
        return result

@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
def create_case(payload: CaseCreateRequest):
    """Register a new law enforcement case record in the SQLite database."""
    now_iso = datetime.now(timezone.utc).isoformat()
    case_id = f"case-bih-{uuid.uuid4().hex[:8]}"

    with get_db() as conn:
        cursor = conn.cursor()
        # Check uniqueness of case_number
        cursor.execute("SELECT id FROM cases WHERE case_number = ?;", (payload.case_number,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Case number '{payload.case_number}' already exists.",
            )

        cursor.execute("""
            INSERT INTO cases (
                id, case_number, title, description, status, priority,
                category, assigned_to, organization_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            case_id,
            payload.case_number,
            payload.title,
            payload.description,
            "open",
            payload.priority,
            payload.category,
            json.dumps(payload.assigned_to),
            payload.organization_id,
            now_iso,
            now_iso,
        ))

    return CaseResponse(
        id=case_id,
        case_number=payload.case_number,
        title=payload.title,
        description=payload.description,
        status="open",
        priority=payload.priority,
        category=payload.category,
        assigned_to=payload.assigned_to,
        organization_id=payload.organization_id,
        created_at=now_iso,
        updated_at=now_iso,
        evidence_count=0,
    )

@router.get("/{case_id}/evidence")
def list_case_evidence(case_id: str):
    """List all evidence items linked to a specific case (by case ID or case number)."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cases WHERE id = ? OR case_number = ?;", (case_id, case_id))
        case_row = cursor.fetchone()
        if not case_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")
        cursor.execute(
            "SELECT * FROM evidence WHERE case_id = ? OR case_id = ? ORDER BY created_at DESC;",
            (case_row["id"], case_row["case_number"]),
        )
        rows = cursor.fetchall()
        return [
            {
                "id": r["id"],
                "case_id": r["case_id"],
                "original_filename": r["original_filename"],
                "mime_type": r["mime_type"],
                "file_size": r["file_size"],
                "sha256_intake": r["sha256_intake"],
                "created_at": r["created_at"],
                "status": r["status"],
            }
            for r in rows
        ]

@router.get("/{case_id}", response_model=CaseResponse)
def get_case(case_id: str):
    """Retrieve details of a specific case by ID or case number."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cases WHERE id = ? OR case_number = ?;", (case_id, case_id))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")

        cursor.execute("SELECT COUNT(*) FROM evidence WHERE case_id = ? OR case_id = ?;", (row["id"], row["case_number"]))
        cnt = cursor.fetchone()[0]

        assigned = json.loads(row["assigned_to"]) if row["assigned_to"] else []
        return CaseResponse(
            id=row["id"],
            case_number=row["case_number"],
            title=row["title"],
            description=row["description"],
            status=row["status"],
            priority=row["priority"],
            category=row["category"],
            assigned_to=assigned,
            organization_id=row["organization_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            evidence_count=cnt,
        )
