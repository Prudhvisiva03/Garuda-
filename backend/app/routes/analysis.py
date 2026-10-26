import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import FileResponse

from backend.app.config import settings
from backend.app.database import get_db, record_audit_event
from backend.app.models import (
    FullAnalysisResponse,
    IntegrityCheckResponse,
    MetadataResponse,
    ElaAnalysisResponse,
    NoiseAnalysisResponse,
    FindingResponse,
    ComparisonRequest,
    ComparisonResponse,
)
from backend.app.services.hashing import verify_file_integrity
from backend.app.services.exif_service import extract_metadata
from backend.app.services.ela_service import generate_ela
from backend.app.services.cv_analysis import analyze_noise_and_features
from backend.app.services.findings_engine import generate_findings_for_evidence
from backend.app.services.image_comparator import compare_images_for_crop

router = APIRouter(prefix="/analysis", tags=["Forensic Analysis"])

@router.post("/{evidence_id}/analyze", response_model=FullAnalysisResponse)
def run_analysis(
    evidence_id: str,
    ela_quality: int = Query(default=settings.DEFAULT_ELA_QUALITY, ge=50, le=100),
    ela_scale: int = Query(default=settings.DEFAULT_ELA_SCALE, ge=1, le=50),
):
    """
    Executes the comprehensive forensic examination pipeline on uploaded evidence:
    1. Independent SHA-256 byte integrity verification.
    2. Real EXIF container and GPS metadata extraction.
    3. Error Level Analysis (ELA) on lossy JPEG structures.
    4. Empirical spatial noise variance & feature duplication analysis.
    5. Explainable findings generation with transparent limitations.
    6. Persistent storage of all outputs in SQLite.
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

        stored_path = settings.EVIDENCE_DIR / evidence_row["stored_filename"]
        if not stored_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Underlying evidence file missing from storage vault.",
            )

        analyzed_at = datetime.now(timezone.utc).isoformat()

        # Step 1: Re-verify integrity
        matches, current_hash = verify_file_integrity(stored_path, evidence_row["sha256_intake"])

        # Step 2: Extract real EXIF metadata
        raw_meta = extract_metadata(stored_path)
        cursor.execute(
            """
            INSERT INTO metadata_records (
                id, evidence_id, make, model, datetime_original, datetime_digitized,
                software, gps_lat, gps_lon, gps_altitude, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(evidence_id) DO UPDATE SET
                make=excluded.make, model=excluded.model,
                datetime_original=excluded.datetime_original,
                datetime_digitized=excluded.datetime_digitized,
                software=excluded.software, gps_lat=excluded.gps_lat,
                gps_lon=excluded.gps_lon, gps_altitude=excluded.gps_altitude,
                raw_json=excluded.raw_json;
            """,
            (
                f"meta_{uuid.uuid4().hex[:10]}",
                evidence_id,
                raw_meta.get("make"),
                raw_meta.get("model"),
                raw_meta.get("datetime_original"),
                raw_meta.get("datetime_digitized"),
                raw_meta.get("software"),
                raw_meta.get("gps_lat"),
                raw_meta.get("gps_lon"),
                raw_meta.get("gps_altitude"),
                json.dumps(raw_meta.get("raw_tags", {})),
            ),
        )

        # Step 3: Run Error Level Analysis
        ela_res = generate_ela(stored_path, evidence_id, quality=ela_quality, scale=ela_scale)
        if ela_res.status == "completed" and ela_res.artifact_path:
            cursor.execute(
                """
                INSERT INTO artifacts (id, evidence_id, analysis_type, artifact_name, file_path, mime_type, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    f"art_{uuid.uuid4().hex[:10]}",
                    evidence_id,
                    "ela",
                    ela_res.artifact_filename,
                    str(ela_res.artifact_path),
                    "image/png",
                    analyzed_at,
                ),
            )

        # Step 4: Run CV Noise & Feature Analysis
        cv_res = analyze_noise_and_features(stored_path)

        # Step 5: Synthesize explainable findings
        findings_list = generate_findings_for_evidence(
            evidence_id=evidence_id,
            integrity_matches=matches,
            sha256_hash=current_hash,
            metadata=raw_meta,
            ela_result=ela_res,
            cv_result=cv_res,
        )

        # Clear previous findings for this evidence to maintain fresh state
        cursor.execute("DELETE FROM findings WHERE evidence_id = ?;", (evidence_id,))
        for f in findings_list:
            cursor.execute(
                """
                INSERT INTO findings (
                    id, evidence_id, analysis_type, test_performed, observed_result,
                    explanation, limitations, severity, review_status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    f["id"],
                    evidence_id,
                    f["analysis_type"],
                    f["test_performed"],
                    f["observed_result"],
                    f["explanation"],
                    f["limitations"],
                    f["severity"],
                    f["review_status"],
                    analyzed_at,
                ),
            )

        # Update evidence status
        cursor.execute("UPDATE evidence SET status = ? WHERE id = ?;", ("analyzed", evidence_id))

        # Log analysis run
        cursor.execute(
            """
            INSERT INTO analysis_runs (id, evidence_id, analysis_type, status, parameters_json, created_at, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (
                f"run_{uuid.uuid4().hex[:10]}",
                evidence_id,
                "full_suite",
                "completed",
                json.dumps({"ela_quality": ela_quality, "ela_scale": ela_scale}),
                analyzed_at,
                analyzed_at,
            ),
        )

        artifact_url = f"/api/v1/evidence/{evidence_id}/artifact/ela" if ela_res.status == "completed" else None

        record_audit_event(
            action="analysis.image_full",
            resource_type="evidence",
            resource_id=evidence_id,
            details=f"Executed full forensic analysis pipeline (ELA quality={ela_quality}, scale={ela_scale}, Noise variance={cv_res.noise_mean_variance}, Findings={len(findings_list)}).",
        )

        return FullAnalysisResponse(
            evidence_id=evidence_id,
            status="completed",
            integrity=IntegrityCheckResponse(
                evidence_id=evidence_id,
                intake_hash=evidence_row["sha256_intake"],
                current_hash=current_hash,
                matches=matches,
                algorithm="SHA-256",
                checked_at=analyzed_at,
                status_label="Verified Match" if matches else "Mismatch Detected",
                message="Hash verified against intake record." if matches else "Hash mismatch detected!",
            ),
            metadata=MetadataResponse(
                evidence_id=evidence_id,
                has_exif=raw_meta.get("has_exif", False),
                make=raw_meta.get("make"),
                model=raw_meta.get("model"),
                datetime_original=raw_meta.get("datetime_original"),
                datetime_digitized=raw_meta.get("datetime_digitized"),
                software=raw_meta.get("software"),
                gps_lat=raw_meta.get("gps_lat"),
                gps_lon=raw_meta.get("gps_lon"),
                gps_altitude=raw_meta.get("gps_altitude"),
                raw_tags=raw_meta.get("raw_tags", {}),
                notes=raw_meta.get("notes", ""),
            ),
            ela=ElaAnalysisResponse(
                status=ela_res.status,
                quality=ela_res.quality,
                scale=ela_res.scale,
                mean_error=ela_res.mean_error,
                max_error=ela_res.max_error,
                artifact_url=artifact_url,
                explanation=ela_res.explanation,
                limitations=ela_res.limitations,
            ),
            noise=NoiseAnalysisResponse(
                status=cv_res.status,
                mean_residual_variance=cv_res.noise_mean_variance,
                variance_discrepancy_ratio=cv_res.noise_discrepancy_ratio,
                anomaly_detected=cv_res.anomaly_detected,
                explanation=cv_res.explanation,
                limitations=cv_res.limitations,
            ),
            findings=[FindingResponse(**f) for f in findings_list],
            analyzed_at=analyzed_at,
        )

@router.get("/{evidence_id}/analysis", response_model=FullAnalysisResponse)
def get_existing_analysis(evidence_id: str):
    """Retrieves persisted analysis results and findings for an evidence record."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM evidence WHERE id = ?;", (evidence_id,))
        evidence_row = cursor.fetchone()
        if not evidence_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Evidence with ID '{evidence_id}' not found.",
            )

        if evidence_row["status"] != "analyzed":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Analysis has not yet been executed for evidence '{evidence_id}'.",
            )

        # Retrieve metadata
        cursor.execute("SELECT * FROM metadata_records WHERE evidence_id = ?;", (evidence_id,))
        meta_row = cursor.fetchone()
        raw_tags = json.loads(meta_row["raw_json"]) if meta_row and meta_row["raw_json"] else {}

        # Retrieve artifact
        cursor.execute(
            "SELECT * FROM artifacts WHERE evidence_id = ? AND analysis_type = 'ela' ORDER BY created_at DESC LIMIT 1;",
            (evidence_id,),
        )
        art_row = cursor.fetchone()

        # Retrieve findings
        cursor.execute("SELECT * FROM findings WHERE evidence_id = ? ORDER BY created_at ASC;", (evidence_id,))
        findings_rows = cursor.fetchall()

        # Re-check hash
        stored_path = settings.EVIDENCE_DIR / evidence_row["stored_filename"]
        matches, current_hash = verify_file_integrity(stored_path, evidence_row["sha256_intake"])

        artifact_url = f"/api/v1/evidence/{evidence_id}/artifact/ela" if art_row else None

        return FullAnalysisResponse(
            evidence_id=evidence_id,
            status="completed",
            integrity=IntegrityCheckResponse(
                evidence_id=evidence_id,
                intake_hash=evidence_row["sha256_intake"],
                current_hash=current_hash,
                matches=matches,
                algorithm="SHA-256",
                checked_at=datetime.now(timezone.utc).isoformat(),
                status_label="Verified Match" if matches else "Mismatch Detected",
                message="Hash verified against intake record." if matches else "Hash mismatch detected!",
            ),
            metadata=MetadataResponse(
                evidence_id=evidence_id,
                has_exif=bool(meta_row and (meta_row["make"] or raw_tags)),
                make=meta_row["make"] if meta_row else None,
                model=meta_row["model"] if meta_row else None,
                datetime_original=meta_row["datetime_original"] if meta_row else None,
                datetime_digitized=meta_row["datetime_digitized"] if meta_row else None,
                software=meta_row["software"] if meta_row else None,
                gps_lat=meta_row["gps_lat"] if meta_row else None,
                gps_lon=meta_row["gps_lon"] if meta_row else None,
                gps_altitude=meta_row["gps_altitude"] if meta_row else None,
                raw_tags=raw_tags,
                notes="Retrieved from persisted database records.",
            ),
            ela=ElaAnalysisResponse(
                status="completed" if art_row else "unsupported",
                quality=settings.DEFAULT_ELA_QUALITY,
                scale=settings.DEFAULT_ELA_SCALE,
                artifact_url=artifact_url,
                explanation="Retrieved persisted ELA analysis.",
                limitations="ELA is an indicative heuristic, not definitive proof of tampering.",
            ),
            noise=NoiseAnalysisResponse(
                status="completed",
                explanation="Retrieved persisted noise analysis.",
                limitations="Experimental heuristic only.",
            ),
            findings=[
                FindingResponse(
                    id=row["id"],
                    evidence_id=row["evidence_id"],
                    analysis_type=row["analysis_type"],
                    test_performed=row["test_performed"],
                    observed_result=row["observed_result"],
                    explanation=row["explanation"],
                    limitations=row["limitations"],
                    severity=row["severity"],
                    review_status=row["review_status"],
                )
                for row in findings_rows
            ],
            analyzed_at=evidence_row["created_at"],
        )

@router.post("/compare", response_model=ComparisonResponse)
def compare_evidence_images(req: ComparisonRequest):
    """
    Performs empirical SIFT feature matching and RANSAC homography comparison
    between a Reference evidence image and a Candidate evidence image to detect
    potential cropping, resizing, or sub-region modifications.
    """
    if req.reference_id == req.candidate_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reference and candidate evidence IDs must be different images.",
        )

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM evidence WHERE id = ?;", (req.reference_id,))
        ref_row = cursor.fetchone()
        if not ref_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Reference evidence '{req.reference_id}' not found.",
            )

        cursor.execute("SELECT * FROM evidence WHERE id = ?;", (req.candidate_id,))
        cand_row = cursor.fetchone()
        if not cand_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate evidence '{req.candidate_id}' not found.",
            )

        ref_path = settings.EVIDENCE_DIR / ref_row["stored_filename"]
        cand_path = settings.EVIDENCE_DIR / cand_row["stored_filename"]

        comp_res = compare_images_for_crop(
            reference_path=ref_path,
            candidate_path=cand_path,
            reference_id=req.reference_id,
            candidate_id=req.candidate_id,
            algorithm=req.algorithm,
            ratio_threshold=req.ratio_threshold,
        )

        comp_id = f"cmp_{uuid.uuid4().hex[:10]}"
        created_at = datetime.now(timezone.utc).isoformat()
        overlap_box_json = json.dumps(comp_res.overlap_box) if comp_res.overlap_box else None

        cursor.execute(
            """
            INSERT INTO image_comparisons (
                id, reference_id, candidate_id, algorithm, status,
                inliers_count, raw_matches, inlier_ratio, overlap_box_json,
                estimated_scale, artifact_name, explanation, limitations, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                comp_id,
                req.reference_id,
                req.candidate_id,
                req.algorithm,
                comp_res.status,
                comp_res.inliers_count,
                comp_res.raw_matches,
                comp_res.inlier_ratio,
                overlap_box_json,
                comp_res.estimated_scale,
                comp_res.artifact_filename,
                comp_res.explanation,
                comp_res.limitations,
                created_at,
            ),
        )

        artifact_url = f"/api/v1/analysis/compare/{comp_id}/artifact" if comp_res.artifact_filename else None

        record_audit_event(
            action="analysis.image_compare",
            resource_type="comparison",
            resource_id=comp_id,
            details=f"Compared reference {req.reference_id} with candidate {req.candidate_id} ({req.algorithm}). Status: {comp_res.status}, Inliers: {comp_res.inliers_count}/{comp_res.raw_matches} ({comp_res.inlier_ratio*100:.1f}%).",
        )

        return ComparisonResponse(
            id=comp_id,
            reference_id=req.reference_id,
            candidate_id=req.candidate_id,
            algorithm=req.algorithm,
            status=comp_res.status,
            inliers_count=comp_res.inliers_count,
            raw_matches=comp_res.raw_matches,
            inlier_ratio=comp_res.inlier_ratio,
            overlap_box=comp_res.overlap_box,
            estimated_scale=comp_res.estimated_scale,
            artifact_url=artifact_url,
            explanation=comp_res.explanation,
            limitations=comp_res.limitations,
            created_at=created_at,
        )

@router.get("/compare/{comparison_id}", response_model=ComparisonResponse)
def get_comparison(comparison_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM image_comparisons WHERE id = ?;", (comparison_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Comparison record '{comparison_id}' not found.",
            )

        overlap_box = json.loads(row["overlap_box_json"]) if row["overlap_box_json"] else None
        artifact_url = f"/api/v1/analysis/compare/{comparison_id}/artifact" if row["artifact_name"] else None
        estimated_scale = row["estimated_scale"] if "estimated_scale" in row.keys() else None

        return ComparisonResponse(
            id=row["id"],
            reference_id=row["reference_id"],
            candidate_id=row["candidate_id"],
            algorithm=row["algorithm"],
            status=row["status"],
            inliers_count=row["inliers_count"],
            raw_matches=row["raw_matches"],
            inlier_ratio=row["inlier_ratio"],
            overlap_box=overlap_box,
            estimated_scale=estimated_scale,
            artifact_url=artifact_url,
            explanation=row["explanation"],
            limitations=row["limitations"],
            created_at=row["created_at"],
        )

@router.get("/compare/{comparison_id}/artifact")
def get_comparison_artifact(comparison_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM image_comparisons WHERE id = ?;", (comparison_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Comparison record '{comparison_id}' not found.",
            )

        if not row["artifact_name"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No visual artifact generated for this comparison.",
            )

        artifact_path = settings.ARTIFACTS_DIR / row["artifact_name"]
        if not artifact_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Artifact file missing from storage vault.",
            )

        return FileResponse(
            path=str(artifact_path),
            media_type="image/png",
            filename=row["artifact_name"],
        )

