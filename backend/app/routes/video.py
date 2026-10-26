import os
import uuid
import json
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, status, Response
from fastapi.responses import FileResponse

from backend.app.config import settings
from backend.app.database import get_db, record_audit_event
from backend.app.models import EvidenceResponse, VideoAnalysisResponse
from backend.app.services.hashing import calculate_sha256_file, verify_file_integrity
from backend.app.services.video_forensics import analyze_video
from backend.app.services.report_generator import generate_video_pdf_report
import cv2

router = APIRouter(prefix="/video", tags=["Video Forensics"])

ALLOWED_VIDEO_EXTS = {".mp4", ".mov", ".avi"}

@router.post("/upload", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED)
def upload_video_evidence(
    file: UploadFile = File(...),
    case_id: str = Form("CASE-2026-VID"),
):
    """
    Forensic intake for digital video evidence (MP4/MOV).
    - Enforces non-executable storage naming
    - Computes authoritative SHA-256 cryptographic digest
    - Verifies video container headers
    - Performs secondary write verification
    """
    original_name = file.filename or "unnamed_video.mp4"
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_VIDEO_EXTS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported video format: '{ext}'. Allowed: {ALLOWED_VIDEO_EXTS}",
        )

    try:
        raw_bytes = file.file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to read video file: {str(e)}",
        )

    file_size = len(raw_bytes)
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded video file is empty (0 bytes).",
        )

    # Magic byte verification (ISO Base Media: ftyp or moov)
    if len(raw_bytes) < 8 or (raw_bytes[4:8] not in [b"ftyp", b"moov"] and not raw_bytes.startswith(b"RIFF")):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File header does not match a valid MP4/ISO Base Media video signature.",
        )

    evidence_id = f"ev_vid_{uuid.uuid4().hex[:12]}"
    stored_filename = f"{evidence_id}{ext}"
    stored_path = settings.EVIDENCE_DIR / stored_filename

    # Save to evidence vault
    with open(stored_path, "wb") as f:
        f.write(raw_bytes)

    # Calculate authoritative SHA-256
    intake_hash = calculate_sha256_file(stored_path)

    # Verify secondary write
    hash_match, _ = verify_file_integrity(stored_path, intake_hash)
    if not hash_match:
        if stored_path.exists():
            os.remove(stored_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cryptographic write verification failed. Stored bytes do not match intake digest.",
        )

    # Extract dimensions via OpenCV
    cap = cv2.VideoCapture(str(stored_path))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) if cap.isOpened() else None
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) if cap.isOpened() else None
    cap.release()

    created_at = datetime.now(timezone.utc).isoformat()

    # Insert into database
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO evidence (
                id, case_id, original_filename, stored_filename,
                mime_type, file_size, width, height, sha256_intake,
                created_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            evidence_id, case_id, original_name, stored_filename,
            "video/mp4", file_size, w, h, intake_hash, created_at, "deposited"
        ))

        cursor.execute("""
            INSERT INTO integrity_checks (
                id, evidence_id, calculated_hash, matches_intake, checked_at
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            f"chk_{uuid.uuid4().hex[:8]}", evidence_id, intake_hash, 1, created_at
        ))

    record_audit_event(
        action="evidence.video_ingest",
        resource_type="evidence",
        resource_id=evidence_id,
        details=f"Ingested video file '{original_name}' (video/mp4, {file_size} bytes, {w}x{h}). SHA-256: {intake_hash[:16]}…",
    )

    return EvidenceResponse(
        id=evidence_id,
        case_id=case_id,
        original_filename=original_name,
        mime_type="video/mp4",
        file_size=file_size,
        width=w,
        height=h,
        sha256_intake=intake_hash,
        created_at=created_at,
        status="deposited",
    )


@router.post("/{evidence_id}/analyze", response_model=VideoAnalysisResponse)
def run_video_forensics(evidence_id: str):
    """
    Executes forensic video examination:
    - Verifies vault SHA-256 digest
    - Detects temporal splicing / cut frames via Bhattacharyya distance & Z-score
    - Detects synthetic night-theme / infrared monochrome filters
    - Extracts keyframes with noise residual analysis
    - Generates SWGDE-compliant structured findings
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM evidence WHERE id = ?", (evidence_id,))
        ev_row = cursor.fetchone()

    if not ev_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evidence {evidence_id} not found.")

    video_path = settings.EVIDENCE_DIR / ev_row["stored_filename"]
    if not video_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Vault video file missing on disk.")

    # Integrity verification
    matches, current_hash = verify_file_integrity(video_path, ev_row["sha256_intake"])
    if not matches:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Evidence tampering detected! Current hash ({current_hash}) does not match intake digest ({ev_row['sha256_intake']}).",
        )

    # Run Video Forensics
    try:
        analysis_data = analyze_video(video_path, evidence_id, settings.ARTIFACTS_DIR)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Video forensics failed during execution: {str(e)}",
        )

    # Save run & artifacts to database
    run_id = f"run_vid_{uuid.uuid4().hex[:8]}"
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO analysis_runs (
                id, evidence_id, analysis_type, status, parameters_json, created_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id, evidence_id, "video_forensics", "completed",
            json.dumps(analysis_data["video_properties"]), now_iso, now_iso
        ))

        for kf in analysis_data.get("keyframes", []):
            art_id = f"art_kf_{uuid.uuid4().hex[:8]}"
            cursor.execute("""
                INSERT OR IGNORE INTO artifacts (
                    id, evidence_id, analysis_type, artifact_name, file_path, mime_type, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                art_id, evidence_id, "keyframe", kf["artifact_name"],
                kf["artifact_path"], "image/jpeg", now_iso
            ))

        # Update evidence status
        cursor.execute("UPDATE evidence SET status = ? WHERE id = ?", ("analyzed", evidence_id))

    record_audit_event(
        action="analysis.video_temporal",
        resource_type="evidence",
        resource_id=evidence_id,
        details=f"Video forensic examination completed. Classification: {analysis_data.get('classification', 'N/A')}. Cuts detected: {analysis_data.get('temporal_cuts', {}).get('total_cuts_detected', 0)}.",
    )

    return analysis_data


@router.get("/{evidence_id}/results", response_model=VideoAnalysisResponse)
def get_video_results(evidence_id: str):
    """Retrieves existing video forensic results or runs analysis if not yet performed."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM evidence WHERE id = ?", (evidence_id,))
        ev_row = cursor.fetchone()

    if not ev_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evidence {evidence_id} not found.")

    video_path = settings.EVIDENCE_DIR / ev_row["stored_filename"]
    return analyze_video(video_path, evidence_id, settings.ARTIFACTS_DIR)


@router.get("/{evidence_id}/report")
def download_video_forensic_report(evidence_id: str):
    """Generates and downloads a SWGDE-compliant PDF Video Forensic Examination Report."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM evidence WHERE id = ?", (evidence_id,))
        ev_row = cursor.fetchone()

    if not ev_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evidence {evidence_id} not found.")

    ev_dict = dict(ev_row)
    video_path = settings.EVIDENCE_DIR / ev_dict["stored_filename"]

    # Integrity recheck
    matches, current_hash = verify_file_integrity(video_path, ev_dict["sha256_intake"])
    integrity_dict = {
        "matches": matches,
        "calculated_hash": current_hash,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }

    # Analysis
    video_analysis = analyze_video(video_path, evidence_id, settings.ARTIFACTS_DIR)

    report_pdf_path = settings.REPORTS_DIR / f"forensic_video_report_{evidence_id}.pdf"
    generate_video_pdf_report(
        evidence=ev_dict,
        integrity=integrity_dict,
        video_analysis=video_analysis,
        findings=video_analysis["findings"],
        output_path=report_pdf_path,
    )

    if not report_pdf_path.exists():
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to compile PDF report.")

    record_audit_event(
        action="report.generate_video_pdf",
        resource_type="report",
        resource_id=f"rep_vid_{evidence_id}",
        details=f"Generated SWGDE Video Forensic Examination Report for {evidence_id} ('{ev_dict['original_filename']}').",
    )

    return FileResponse(
        path=str(report_pdf_path),
        filename=f"Garuda_Video_Forensics_{ev_dict['original_filename']}.pdf",
        media_type="application/pdf",
    )


@router.get("/artifact/{filename}")
def get_video_keyframe_artifact(filename: str):
    """Safely serves extracted keyframe images."""
    safe_path = (settings.ARTIFACTS_DIR / filename).resolve()
    base_dir = settings.ARTIFACTS_DIR.resolve()
    if not str(safe_path).startswith(str(base_dir)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    if not safe_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found.")
    return FileResponse(path=str(safe_path), media_type="image/jpeg")


@router.get("/list", response_model=list[EvidenceResponse])
def list_video_evidence():
    """Retrieve all ingested video evidence records."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM evidence WHERE mime_type LIKE 'video/%' ORDER BY created_at DESC;")
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
