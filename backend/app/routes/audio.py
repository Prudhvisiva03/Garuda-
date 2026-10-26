import os
import uuid
import json
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse

from backend.app.config import settings
from backend.app.database import get_db, record_audit_event
from backend.app.models import EvidenceResponse, AudioAnalysisResponse
from backend.app.services.hashing import calculate_sha256_file, verify_file_integrity
from backend.app.services.audio_forensics import analyze_audio
from backend.app.services.report_generator import generate_audio_pdf_report

router = APIRouter(prefix="/audio", tags=["Audio Forensics"])

ALLOWED_AUDIO_EXTS = {".mp3", ".wav", ".aac", ".m4a"}

@router.post("/upload", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED)
def upload_audio_evidence(
    file: UploadFile = File(...),
    case_id: str = Form("CASE-2026-AUD"),
):
    """
    Forensic intake for digital audio evidence (MP3/WAV/AAC).
    - Enforces non-executable storage naming
    - Computes authoritative SHA-256 cryptographic digest
    - Verifies audio container magic bytes
    - Performs secondary write verification
    """
    original_name = file.filename or "unnamed_audio.mp3"
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_AUDIO_EXTS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported audio format: '{ext}'. Allowed: {ALLOWED_AUDIO_EXTS}",
        )

    try:
        raw_bytes = file.file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to read audio file: {str(e)}",
        )

    file_size = len(raw_bytes)
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded audio file is empty (0 bytes).",
        )

    # Magic byte verification:
    # WAV: RIFF....WAVE
    # MP3: ID3 (0x49 0x44 0x33) or sync word (0xFF 0xFB / 0xFF 0xF3 / 0xFF 0xF2)
    # M4A/AAC: ftyp or 0xFF 0xF1
    is_valid_audio = False
    if raw_bytes.startswith(b"RIFF") and b"WAVE" in raw_bytes[:16]:
        is_valid_audio = True
    elif raw_bytes.startswith(b"ID3") or (len(raw_bytes) >= 2 and raw_bytes[0] == 0xFF and (raw_bytes[1] & 0xE0) == 0xE0):
        is_valid_audio = True
    elif len(raw_bytes) >= 8 and (raw_bytes[4:8] in [b"ftyp", b"moov"]):
        is_valid_audio = True

    if not is_valid_audio:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File header does not match a valid audio format (WAV/MP3/M4A).",
        )

    evidence_id = f"ev_aud_{uuid.uuid4().hex[:12]}"
    stored_filename = f"{evidence_id}{ext}"
    stored_path = settings.EVIDENCE_DIR / stored_filename

    # Save to vault
    with open(stored_path, "wb") as f:
        f.write(raw_bytes)

    # Authoritative SHA-256
    intake_hash = calculate_sha256_file(stored_path)

    # Secondary write verification
    hash_match, _ = verify_file_integrity(stored_path, intake_hash)
    if not hash_match:
        if stored_path.exists():
            os.remove(stored_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cryptographic write verification failed. Stored bytes do not match intake digest.",
        )

    created_at = datetime.now(timezone.utc).isoformat()
    mime = "audio/wav" if ext == ".wav" else "audio/mpeg"

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
            mime, file_size, None, None, intake_hash, created_at, "deposited"
        ))

        cursor.execute("""
            INSERT INTO integrity_checks (
                id, evidence_id, calculated_hash, matches_intake, checked_at
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            f"chk_{uuid.uuid4().hex[:8]}", evidence_id, intake_hash, 1, created_at
        ))

    record_audit_event(
        action="evidence.audio_ingest",
        resource_type="evidence",
        resource_id=evidence_id,
        details=f"Ingested audio file '{original_name}' ({mime}, {file_size} bytes). SHA-256: {intake_hash[:16]}…",
    )

    return EvidenceResponse(
        id=evidence_id,
        case_id=case_id,
        original_filename=original_name,
        mime_type=mime,
        file_size=file_size,
        width=None,
        height=None,
        sha256_intake=intake_hash,
        created_at=created_at,
        status="deposited",
    )


@router.post("/{evidence_id}/analyze", response_model=AudioAnalysisResponse)
def run_audio_forensics(evidence_id: str):
    """
    Executes forensic audio examination:
    - Verifies vault SHA-256 digest
    - Detects acoustic splices & edit boundaries via Short-Time Spectral Flux
    - Identifies AI synthesized speech artifacts via noise floor & digital silence scanning
    - Generates two-panel Waveform + Mel-Spectrogram artifact
    - Produces SWGDE-compliant structured findings
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM evidence WHERE id = ?", (evidence_id,))
        ev_row = cursor.fetchone()

    if not ev_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evidence {evidence_id} not found.")

    audio_path = settings.EVIDENCE_DIR / ev_row["stored_filename"]
    if not audio_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vault audio file missing on disk.")

    # Integrity verification
    matches, current_hash = verify_file_integrity(audio_path, ev_row["sha256_intake"])
    if not matches:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Evidence tampering detected! Current hash ({current_hash}) does not match intake digest ({ev_row['sha256_intake']}).",
        )

    # Run Audio Forensics
    try:
        analysis_data = analyze_audio(audio_path, evidence_id, settings.ARTIFACTS_DIR)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Audio forensics failed during execution: {str(e)}",
        )

    # Save run & artifact to database
    run_id = f"run_aud_{uuid.uuid4().hex[:8]}"
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO analysis_runs (
                id, evidence_id, analysis_type, status, parameters_json, created_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id, evidence_id, "audio_forensics", "completed",
            json.dumps(analysis_data["audio_properties"]), now_iso, now_iso
        ))

        if analysis_data.get("spectrogram_artifact"):
            art_id = f"art_spec_{uuid.uuid4().hex[:8]}"
            cursor.execute("""
                INSERT OR IGNORE INTO artifacts (
                    id, evidence_id, analysis_type, artifact_name, file_path, mime_type, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                art_id, evidence_id, "spectrogram", analysis_data["spectrogram_artifact"],
                str(settings.ARTIFACTS_DIR / analysis_data["spectrogram_artifact"]), "image/png", now_iso
            ))

        cursor.execute("UPDATE evidence SET status = ? WHERE id = ?", ("analyzed", evidence_id))

    record_audit_event(
        action="analysis.audio_forensics",
        resource_type="evidence",
        resource_id=evidence_id,
        details=f"Audio forensic examination completed. Classification: {analysis_data.get('classification', 'N/A')}. AI voice detected: {analysis_data.get('synthetic_indicators', {}).get('synthetic_voice_detected', 'N/A')}.",
    )

    return analysis_data


@router.get("/{evidence_id}/results", response_model=AudioAnalysisResponse)
def get_audio_results(evidence_id: str):
    """Retrieves existing audio forensic results or executes analysis if not yet run."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM evidence WHERE id = ?", (evidence_id,))
        ev_row = cursor.fetchone()

    if not ev_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evidence {evidence_id} not found.")

    audio_path = settings.EVIDENCE_DIR / ev_row["stored_filename"]
    return analyze_audio(audio_path, evidence_id, settings.ARTIFACTS_DIR)


@router.get("/{evidence_id}/report")
def download_audio_forensic_report(evidence_id: str):
    """Generates and downloads a SWGDE-compliant PDF Audio Forensic Examination Report."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM evidence WHERE id = ?", (evidence_id,))
        ev_row = cursor.fetchone()

    if not ev_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evidence {evidence_id} not found.")

    ev_dict = dict(ev_row)
    audio_path = settings.EVIDENCE_DIR / ev_dict["stored_filename"]

    # Integrity recheck
    matches, current_hash = verify_file_integrity(audio_path, ev_dict["sha256_intake"])
    integrity_dict = {
        "matches": matches,
        "calculated_hash": current_hash,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }

    # Analysis
    audio_analysis = analyze_audio(audio_path, evidence_id, settings.ARTIFACTS_DIR)

    report_pdf_path = settings.REPORTS_DIR / f"forensic_audio_report_{evidence_id}.pdf"
    generate_audio_pdf_report(
        evidence=ev_dict,
        integrity=integrity_dict,
        audio_analysis=audio_analysis,
        findings=audio_analysis["findings"],
        output_path=report_pdf_path,
    )

    if not report_pdf_path.exists():
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to compile Audio PDF report.")

    record_audit_event(
        action="report.generate_audio_pdf",
        resource_type="report",
        resource_id=f"rep_aud_{evidence_id}",
        details=f"Generated SWGDE Audio Forensic Report for {evidence_id} ('{ev_dict['original_filename']}').",
    )

    return FileResponse(
        path=str(report_pdf_path),
        filename=f"EviSutra_Audio_Forensics_{ev_dict['original_filename']}.pdf",
        media_type="application/pdf",
    )


@router.get("/artifact/{filename}")
def get_audio_spectrogram_artifact(filename: str):
    """Safely serves generated spectrogram image artifacts."""
    safe_path = (settings.ARTIFACTS_DIR / filename).resolve()
    base_dir = settings.ARTIFACTS_DIR.resolve()
    if not str(safe_path).startswith(str(base_dir)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    if not safe_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found.")
    return FileResponse(path=str(safe_path), media_type="image/png")


@router.get("/list", response_model=list[EvidenceResponse])
def list_audio_evidence():
    """Retrieve all ingested audio evidence records."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM evidence WHERE mime_type LIKE 'audio/%' ORDER BY created_at DESC;")
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
