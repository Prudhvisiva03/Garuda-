import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from backend.app.config import settings
from backend.app.database import get_db, record_audit_event
from backend.app.services.hashing import verify_file_integrity
from backend.app.services.report_generator import generate_pdf_report

router = APIRouter(prefix="/reports", tags=["Forensic Reports"])

@router.post("/{evidence_id}/generate")
def generate_report(evidence_id: str):
    """
    Generates an official digital evidence examination PDF report from actual persisted analysis records.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM evidence WHERE id = ?;", (evidence_id,))
        evidence_row = cursor.fetchone()
        if not evidence_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Evidence with ID '{evidence_id}' not found.",
            )

        # Retrieve metadata
        cursor.execute("SELECT * FROM metadata_records WHERE evidence_id = ?;", (evidence_id,))
        meta_row = cursor.fetchone()
        raw_tags = json.loads(meta_row["raw_json"]) if meta_row and meta_row["raw_json"] else {}
        metadata_dict = {
            "has_exif": bool(meta_row and (meta_row["make"] or raw_tags)),
            "make": meta_row["make"] if meta_row else None,
            "model": meta_row["model"] if meta_row else None,
            "datetime_original": meta_row["datetime_original"] if meta_row else None,
            "software": meta_row["software"] if meta_row else None,
            "gps_lat": meta_row["gps_lat"] if meta_row else None,
            "gps_lon": meta_row["gps_lon"] if meta_row else None,
            "raw_tags": raw_tags,
        }

        # Retrieve artifact
        cursor.execute(
            "SELECT * FROM artifacts WHERE evidence_id = ? AND analysis_type = 'ela' ORDER BY created_at DESC LIMIT 1;",
            (evidence_id,),
        )
        art_row = cursor.fetchone()
        ela_dict = {
            "status": "completed" if art_row else "unsupported",
            "quality": settings.DEFAULT_ELA_QUALITY,
            "scale": settings.DEFAULT_ELA_SCALE,
            "artifact_filename": art_row["artifact_name"] if art_row else None,
            "explanation": "ELA analysis completed on JPEG structure." if art_row else "ELA not performed or unsupported.",
        }

        # Retrieve findings
        cursor.execute("SELECT * FROM findings WHERE evidence_id = ? ORDER BY created_at ASC;", (evidence_id,))
        findings_rows = cursor.fetchall()
        findings_list = [dict(row) for row in findings_rows]

        # Retrieve comparison record if this evidence was examined in a comparison
        cursor.execute(
            """
            SELECT * FROM image_comparisons 
            WHERE reference_id = ? OR candidate_id = ? 
            ORDER BY created_at DESC LIMIT 1;
            """,
            (evidence_id, evidence_id),
        )
        comp_row = cursor.fetchone()
        comparison_dict = dict(comp_row) if comp_row else None

        # Verify hash
        stored_path = settings.EVIDENCE_DIR / evidence_row["stored_filename"]
        matches, current_hash = verify_file_integrity(stored_path, evidence_row["sha256_intake"])
        integrity_dict = {
            "current_hash": current_hash,
            "matches": matches,
        }

        # Generate report
        report_filename = f"report_{evidence_id}.pdf"
        report_path = settings.REPORTS_DIR / report_filename

        report_id = generate_pdf_report(
            evidence=dict(evidence_row),
            integrity=integrity_dict,
            metadata=metadata_dict,
            ela=ela_dict,
            cv_analysis={},
            findings=findings_list,
            output_path=report_path,
            comparison=comparison_dict,
        )

        cursor.execute(
            """
            INSERT INTO reports (id, evidence_id, file_path, generated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET file_path=excluded.file_path, generated_at=excluded.generated_at;
            """,
            (
                report_id,
                evidence_id,
                str(report_path),
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        record_audit_event(
            action="report.generate_pdf",
            resource_type="report",
            resource_id=report_id,
            details=f"Generated Section 65B forensic report PDF for evidence {evidence_id} ('{evidence_row['original_filename']}').",
        )

        return {
            "report_id": report_id,
            "evidence_id": evidence_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "download_url": f"/api/v1/reports/{evidence_id}/download",
            "filename": report_filename,
        }

@router.get("/{evidence_id}/download")
def download_report(evidence_id: str):
    """Download the generated forensic analysis PDF report."""
    report_filename = f"report_{evidence_id}.pdf"
    report_path = settings.REPORTS_DIR / report_filename

    # If report doesn't exist yet, generate it on demand
    if not report_path.exists():
        generate_report(evidence_id)

    if not report_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report file could not be generated for evidence '{evidence_id}'.",
        )

    return FileResponse(
        path=str(report_path),
        media_type="application/pdf",
        filename=f"EviSutra_Forensic_Report_{evidence_id}.pdf",
    )
