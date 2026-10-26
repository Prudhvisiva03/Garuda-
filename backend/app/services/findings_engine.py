import uuid
from typing import Any
from backend.app.services.ela_service import ElaResult
from backend.app.services.cv_analysis import CvAnalysisResult

KNOWN_EDITING_SOFTWARE_KEYWORDS = [
    "photoshop", "gimp", "canva", "lightroom", "pixlr",
    "snapseed", "paint.net", "facetune", "picsart", "affinity"
]

def generate_findings_for_evidence(
    evidence_id: str,
    integrity_matches: bool,
    sha256_hash: str,
    metadata: dict[str, Any],
    ela_result: ElaResult,
    cv_result: CvAnalysisResult,
) -> list[dict[str, Any]]:
    findings = []

    # 1. Finding: SHA-256 Bitstream Integrity Check
    if integrity_matches:
        findings.append({
            "id": f"fnd_{uuid.uuid4().hex[:10]}",
            "evidence_id": evidence_id,
            "analysis_type": "hash-verify",
            "test_performed": "Cryptographic SHA-256 Digest Verification",
            "observed_result": f"Hash match confirmed: {sha256_hash[:16]}...",
            "explanation": (
                "The stored digital evidence bytes were recalculated and match the recorded intake digest exactly. "
                "This verifies that no bit-level alteration, corruption, or storage tampering has occurred since intake."
            ),
            "limitations": (
                "A matching cryptographic hash establishes byte-level preservation relative to the intake digest only. "
                "It does not establish that the evidence was authentic, unaltered, or genuine before intake."
            ),
            "severity": "info",
            "review_status": "confirmed",
        })
    else:
        findings.append({
            "id": f"fnd_{uuid.uuid4().hex[:10]}",
            "evidence_id": evidence_id,
            "analysis_type": "hash-verify",
            "test_performed": "Cryptographic SHA-256 Digest Verification",
            "observed_result": "CRITICAL INTEGRITY MISMATCH DETECTED",
            "explanation": (
                "The recalculated SHA-256 digest differs from the original recorded intake hash. "
                "The stored file has been modified, corrupted, or replaced post-intake."
            ),
            "limitations": "Immediate chain of custody investigation is required.",
            "severity": "critical",
            "review_status": "pending",
        })

    # 2. Finding: Metadata & Provenance Inspection
    if metadata.get("has_exif"):
        software = (metadata.get("software") or "").lower()
        editing_detected = any(k in software for k in KNOWN_EDITING_SOFTWARE_KEYWORDS)

        if editing_detected:
            findings.append({
                "id": f"fnd_{uuid.uuid4().hex[:10]}",
                "evidence_id": evidence_id,
                "analysis_type": "metadata",
                "test_performed": "EXIF Software Tag & Provenance Inspection",
                "observed_result": f"Editing software tag identified: '{metadata.get('software')}'",
                "explanation": (
                    f"The EXIF metadata header records a known image processing or authoring tool: {metadata.get('software')}. "
                    "This indicates that the image file was processed, exported, or saved using desktop image editing software."
                ),
                "limitations": (
                    "Editing software tags indicate processing history (e.g. format conversion, color grading, cropping, or saving) "
                    "but do not by themselves identify whether fraudulent content manipulation or splicing occurred. "
                    "Metadata can also be stripped, spoofed, or re-written."
                ),
                "severity": "medium",
                "review_status": "pending",
            })
        else:
            findings.append({
                "id": f"fnd_{uuid.uuid4().hex[:10]}",
                "evidence_id": evidence_id,
                "analysis_type": "metadata",
                "test_performed": "EXIF Metadata Header Verification",
                "observed_result": f"Metadata tags present (Camera: {metadata.get('make') or 'Unknown'} {metadata.get('model') or ''})",
                "explanation": (
                    f"Parsed {len(metadata.get('raw_tags', {}))} EXIF tags. Camera make/model and timestamps are recorded. "
                    "No explicit third-party editing suite signatures were detected in the Software tag."
                ),
                "limitations": (
                    "Absence of editing tags does not prove authenticity; sophisticated editing tools can strip or preserve "
                    "original camera metadata. Metadata alone cannot establish that the image scene has not been manipulated."
                ),
                "severity": "info",
                "review_status": "pending",
            })

        # Temporal Anomaly & Chronological Inversion Check
        dt_orig_str = metadata.get("datetime_original")
        dt_dig_str = metadata.get("datetime_digitized")
        if dt_orig_str:
            try:
                dt_orig = datetime.strptime(str(dt_orig_str)[:19], "%Y:%m:%d %H:%M:%S")
                if dt_orig.year > datetime.now().year + 1:
                    findings.append({
                        "id": f"fnd_ts_future_{uuid.uuid4().hex[:8]}",
                        "evidence_id": evidence_id,
                        "analysis_type": "metadata",
                        "test_performed": "EXIF Temporal Consistency & Chronology Check",
                        "observed_result": f"Post-dated timestamp detected: DateTimeOriginal is {dt_orig_str}",
                        "explanation": f"The embedded EXIF timestamp ({dt_orig_str}) is set in the future. This indicates system clock misconfiguration, intentional timestamp spoofing, or fabricated provenance.",
                        "limitations": "Camera internal clocks can be incorrectly set by users. Timestamp anomalies require corroboration with external network and file system timestamps.",
                        "severity": "high",
                        "review_status": "pending",
                    })
                elif dt_dig_str:
                    try:
                        dt_dig = datetime.strptime(str(dt_dig_str)[:19], "%Y:%m:%d %H:%M:%S")
                        if dt_dig < dt_orig:
                            findings.append({
                                "id": f"fnd_ts_inconsistent_{uuid.uuid4().hex[:8]}",
                                "evidence_id": evidence_id,
                                "analysis_type": "metadata",
                                "test_performed": "EXIF Temporal Consistency & Chronology Check",
                                "observed_result": f"Chronological contradiction: Digitized time ({dt_dig_str}) precedes Capture time ({dt_orig_str})",
                                "explanation": "In authentic camera acquisition, digitization cannot precede optical capture. This chronological inversion is a hallmark of metadata re-writing or post-hoc editing.",
                                "limitations": "Certain third-party scanner software or batch tools improperly populate digitization tags.",
                                "severity": "medium",
                                "review_status": "pending",
                            })
                    except Exception:
                        pass
            except Exception:
                pass
    else:
        findings.append({
            "id": f"fnd_{uuid.uuid4().hex[:10]}",
            "evidence_id": evidence_id,
            "analysis_type": "metadata",
            "test_performed": "EXIF Metadata Header Verification",
            "observed_result": "No EXIF metadata block found in image container",
            "explanation": (
                "The image file contains no EXIF container metadata. Common causes include stripping by web platforms, "
                "messaging applications (e.g. WhatsApp, Telegram), screenshot capture, or intentional anonymization."
            ),
            "limitations": (
                "Missing metadata is an inconclusive observation and must NOT be treated as proof of tampering. "
                "Many legitimate modern distribution pipelines routinely strip metadata."
            ),
            "severity": "info",
            "review_status": "pending",
        })

    # 3. Finding: Error Level Analysis (ELA)
    if ela_result.status == "completed":
        mean_err = ela_result.mean_error or 0.0
        max_err = ela_result.max_error or 0.0

        findings.append({
            "id": f"fnd_{uuid.uuid4().hex[:10]}",
            "evidence_id": evidence_id,
            "analysis_type": "ela",
            "test_performed": f"Error Level Analysis (JPEG Q={ela_result.quality})",
            "observed_result": f"Mean compression error: {mean_err:.2f}, peak error: {max_err:.2f}",
            "explanation": (
                f"Generated compression differential map at quality {ela_result.quality}. "
                "Uniform surfaces exhibit consistent error levels across the image canvas. "
                "Investigator should inspect the visual artifact for localized regions displaying divergent error brightness."
            ),
            "limitations": (
                "ELA is an indicative heuristic, not a definitive tampering test. "
                "High-frequency textures, sharp edges, and saturated colors naturally produce elevated ELA response. "
                "Uniform ELA does not prove authenticity (e.g. re-compressed uniform forgeries)."
            ),
            "severity": "low",
            "review_status": "pending",
        })
    elif ela_result.status == "unsupported":
        findings.append({
            "id": f"fnd_{uuid.uuid4().hex[:10]}",
            "evidence_id": evidence_id,
            "analysis_type": "ela",
            "test_performed": "Error Level Analysis (ELA)",
            "observed_result": "Inapplicable to lossless PNG format",
            "explanation": ela_result.explanation,
            "limitations": ela_result.limitations,
            "severity": "info",
            "review_status": "confirmed",
        })

    # 4. Finding: High-Frequency Noise & Keypoint Spatial Analysis
    if cv_result.status == "completed":
        if cv_result.anomaly_detected:
            findings.append({
                "id": f"fnd_{uuid.uuid4().hex[:10]}",
                "evidence_id": evidence_id,
                "analysis_type": "noise-analysis",
                "test_performed": "Noise Residual Variance & Feature Duplication Check",
                "observed_result": (
                    f"Elevated regional variance discrepancy (ratio: {cv_result.noise_discrepancy_ratio}) "
                    f"with {cv_result.copy_move_matches_count} candidate duplicate keypoints"
                ),
                "explanation": cv_result.explanation,
                "limitations": cv_result.limitations,
                "severity": "medium",
                "review_status": "pending",
            })
        else:
            findings.append({
                "id": f"fnd_{uuid.uuid4().hex[:10]}",
                "evidence_id": evidence_id,
                "analysis_type": "noise-analysis",
                "test_performed": "Noise Residual Variance & Feature Duplication Check",
                "observed_result": (
                    f"Baseline spatial noise variance (ratio: {cv_result.noise_discrepancy_ratio}) "
                    f"with {cv_result.copy_move_matches_count} candidate duplicate keypoints"
                ),
                "explanation": (
                    f"Empirical high-frequency noise analysis completed without detecting abnormal regional discrepancies. "
                    f"{cv_result.copy_move_matches_count} displaced descriptor matches detected."
                ),
                "limitations": cv_result.limitations,
                "severity": "info",
                "review_status": "confirmed",
            })

    return findings
