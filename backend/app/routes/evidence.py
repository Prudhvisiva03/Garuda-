import uuid
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from fastapi.responses import FileResponse

from backend.app.config import settings
from backend.app.database import get_db, record_audit_event
from backend.app.models import EvidenceResponse, IntegrityCheckResponse
from backend.app.services.file_validator import validate_and_save_upload
from backend.app.services.hashing import calculate_sha256_bytes, verify_file_integrity

router = APIRouter(prefix="/evidence", tags=["Evidence Management"])

@router.post("/upload", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED)
def upload_evidence(
    file: UploadFile = File(...),
    case_id: str = Form("CASE-2026-001"),
):
    """
    Ingest a new digital evidence image.
    Validates file signature, dimensions, limits, calculates SHA-256,
    stores original in isolated evidence vault, and creates persistent database record.
    """
    validated = validate_and_save_upload(file)

    # Calculate authoritative intake hash from the accepted byte stream
    intake_hash = calculate_sha256_bytes(validated.raw_bytes)
    created_at = datetime.now(timezone.utc).isoformat()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO evidence (
                id, case_id, original_filename, stored_filename,
                mime_type, file_size, width, height, sha256_intake, created_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                validated.evidence_id,
                case_id,
                validated.original_filename,
                validated.stored_filename,
                validated.mime_type,
                validated.file_size,
                validated.width,
                validated.height,
                intake_hash,
                created_at,
                "ingested",
            ),
        )

    # Immediately perform secondary read to independently verify disk write integrity
    matches, _ = verify_file_integrity(validated.stored_path, intake_hash)
    if not matches:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Storage disk write verification failed. Stored byte stream does not match intake digest.",
        )

    # Immutable audit log entry (Section 65B compliance)
    record_audit_event(
        action="evidence.ingest",
        resource_type="evidence",
        resource_id=validated.evidence_id,
        details=f"Ingested and SHA-256 verified '{validated.original_filename}' ({validated.mime_type}, {validated.file_size} bytes) under case {case_id}. Digest: {intake_hash[:16]}…",
    )

    return EvidenceResponse(
        id=validated.evidence_id,
        case_id=case_id,
        original_filename=validated.original_filename,
        mime_type=validated.mime_type,
        file_size=validated.file_size,
        width=validated.width,
        height=validated.height,
        sha256_intake=intake_hash,
        created_at=created_at,
        status="ingested",
    )

@router.get("", response_model=list[EvidenceResponse])
def list_evidence():
    """Retrieve all persisted evidence records."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM evidence ORDER BY created_at DESC;")
        rows = cursor.fetchall()
        return [
            EvidenceResponse(
                id=row["id"],
                case_id=row["case_id"],
                original_filename=row["original_filename"],
                mime_type=row["mime_type"],
                file_size=row["file_size"],
                width=row["width"],
                height=row["height"],
                sha256_intake=row["sha256_intake"],
                created_at=row["created_at"],
                status=row["status"],
            )
            for row in rows
        ]

@router.get("/{evidence_id}", response_model=EvidenceResponse)
def get_evidence(evidence_id: str):
    """Retrieve single evidence item by ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM evidence WHERE id = ?;", (evidence_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Evidence with ID '{evidence_id}' not found.",
            )
        return EvidenceResponse(
            id=row["id"],
            case_id=row["case_id"],
            original_filename=row["original_filename"],
            mime_type=row["mime_type"],
            file_size=row["file_size"],
            width=row["width"],
            height=row["height"],
            sha256_intake=row["sha256_intake"],
            created_at=row["created_at"],
            status=row["status"],
        )

@router.post("/{evidence_id}/verify-hash", response_model=IntegrityCheckResponse)
def verify_evidence_hash(evidence_id: str):
    """
    Cryptographic integrity recheck operation.
    Independently reads the stored evidence file, calculates the current SHA-256 digest,
    and compares it to the original recorded intake digest.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM evidence WHERE id = ?;", (evidence_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Evidence with ID '{evidence_id}' not found.",
            )

        stored_path = settings.EVIDENCE_DIR / row["stored_filename"]
        matches, current_hash = verify_file_integrity(stored_path, row["sha256_intake"])
        checked_at = datetime.now(timezone.utc).isoformat()

        # Log check event
        check_id = f"chk_{uuid.uuid4().hex[:10]}"
        cursor.execute(
            """
            INSERT INTO integrity_checks (id, evidence_id, calculated_hash, matches_intake, checked_at)
            VALUES (?, ?, ?, ?, ?);
            """,
            (check_id, evidence_id, current_hash, 1 if matches else 0, checked_at),
        )

        # Audit trail entry
        record_audit_event(
            action="evidence.integrity_check",
            resource_type="evidence",
            resource_id=evidence_id,
            details=f"SHA-256 re-verification for '{row['original_filename']}'. Result: {'MATCH' if matches else 'MISMATCH'}. Current: {current_hash[:16]}…",
        )

        return IntegrityCheckResponse(
            evidence_id=evidence_id,
            intake_hash=row["sha256_intake"],
            current_hash=current_hash,
            matches=matches,
            algorithm="SHA-256",
            checked_at=checked_at,
            status_label="Verified Match" if matches else "Integrity Mismatch Detected",
            message=(
                "Stored file byte stream exactly matches intake digest."
                if matches
                else "CRITICAL: Stored file bytes differ from the intake digest! Possible tampering or corruption."
            ),
        )

@router.get("/{evidence_id}/file")
def get_evidence_file(evidence_id: str):
    """Stream raw evidence file for display in investigator preview."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM evidence WHERE id = ?;", (evidence_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Evidence with ID '{evidence_id}' not found.",
            )
        file_path = settings.EVIDENCE_DIR / row["stored_filename"]
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Underlying evidence file missing from storage.",
            )
        return FileResponse(
            path=str(file_path),
            media_type=row["mime_type"],
            filename=row["original_filename"],
        )

@router.get("/{evidence_id}/artifact/{artifact_type}")
def get_artifact_file(evidence_id: str, artifact_type: str):
    """Stream derived analysis artifact (e.g. ELA visual PNG)."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM artifacts WHERE evidence_id = ? AND analysis_type = ? ORDER BY created_at DESC LIMIT 1;",
            (evidence_id, artifact_type),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact of type '{artifact_type}' for evidence '{evidence_id}' not found.",
            )
        file_path = Path(row["file_path"])
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Artifact file missing from storage.",
            )
        return FileResponse(
            path=str(file_path),
            media_type=row["mime_type"],
            filename=row["artifact_name"],
        )
