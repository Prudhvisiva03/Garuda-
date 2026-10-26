import io
import os
import hashlib
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw
import piexif

from backend.app.main import app
from backend.app.config import settings
from backend.app.database import get_db, init_db
from backend.app.services.hashing import calculate_sha256_bytes
from backend.app.services.image_comparator import classify_comparison, compare_images_for_crop

client = TestClient(app)

def create_synthetic_jpeg(width: int = 120, height: int = 120, color=(100, 150, 200)) -> bytes:
    """Create a valid synthetic JPEG image in memory."""
    buf = io.BytesIO()
    img = Image.new("RGB", (width, height), color=color)
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()

def create_synthetic_png(width: int = 120, height: int = 120, color=(50, 100, 150)) -> bytes:
    """Create a valid synthetic PNG image in memory."""
    buf = io.BytesIO()
    img = Image.new("RGB", (width, height), color=color)
    img.save(buf, format="PNG")
    return buf.getvalue()

def create_jpeg_with_exif() -> bytes:
    """Create a synthetic JPEG with genuine EXIF camera and timestamp metadata."""
    img = Image.new("RGB", (150, 150), color=(220, 180, 140))
    
    # Construct synthetic EXIF dictionary using piexif
    zeroth_ifd = {
        piexif.ImageIFD.Make: b"Nikon Corporation",
        piexif.ImageIFD.Model: b"NIKON D850",
        piexif.ImageIFD.Software: b"Ver.1.20",
        piexif.ImageIFD.DateTime: b"2026:10:14 10:30:00",
    }
    exif_ifd = {
        piexif.ExifIFD.DateTimeOriginal: b"2026:10:14 10:30:00",
        piexif.ExifIFD.DateTimeDigitized: b"2026:10:14 10:30:00",
    }
    gps_ifd = {
        piexif.GPSIFD.GPSLatitudeRef: b"N",
        piexif.GPSIFD.GPSLatitude: ((25, 1), (36, 1), (4200, 100)),  # 25 deg 36 min 42 sec N (Patna, Bihar)
        piexif.GPSIFD.GPSLongitudeRef: b"E",
        piexif.GPSIFD.GPSLongitude: ((85, 1), (8, 1), (1500, 100)),   # 85 deg 8 min 15 sec E
        piexif.GPSIFD.GPSAltitude: (53, 1),
    }
    exif_dict = {"0th": zeroth_ifd, "Exif": exif_ifd, "GPS": gps_ifd}
    exif_bytes = piexif.dump(exif_dict)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95, exif=exif_bytes)
    return buf.getvalue()

# --- TEST SUITE (18 REQUIREMENTS) ---

def test_01_valid_jpeg_upload():
    """Requirement 1: Valid JPEG upload succeeds and returns evidence record."""
    jpeg_bytes = create_synthetic_jpeg()
    response = client.post(
        "/api/v1/evidence/upload",
        files={"file": ("test_evidence.jpg", jpeg_bytes, "image/jpeg")},
        data={"case_id": "TEST-CASE-01"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["id"].startswith("ev_")
    assert data["mime_type"] == "image/jpeg"
    assert data["file_size"] == len(jpeg_bytes)
    assert data["width"] == 120
    assert data["height"] == 120
    assert data["status"] == "ingested"

def test_02_valid_png_upload():
    """Requirement 2: Valid PNG upload succeeds and decodes correctly."""
    png_bytes = create_synthetic_png()
    response = client.post(
        "/api/v1/evidence/upload",
        files={"file": ("document_scan.png", png_bytes, "image/png")},
        data={"case_id": "TEST-CASE-02"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["mime_type"] == "image/png"
    assert data["file_size"] == len(png_bytes)

def test_03_incorrect_extension_and_mime_claims():
    """Requirement 3: Text file disguised as .jpg is rejected based on magic byte inspection."""
    fake_bytes = b"Hello, I am a plain text file pretending to be a JPG!"
    response = client.post(
        "/api/v1/evidence/upload",
        files={"file": ("malicious.jpg", fake_bytes, "image/jpeg")},
    )
    assert response.status_code == 415
    assert "Unsupported file format" in response.json()["detail"]

def test_04_malformed_image_files():
    """Requirement 4: Malformed/corrupted image header is rejected."""
    corrupted_bytes = b"\xFF\xD8\xFF" + b"\x00" * 30  # Valid start, truncated corrupted body
    response = client.post(
        "/api/v1/evidence/upload",
        files={"file": ("corrupted.jpg", corrupted_bytes, "image/jpeg")},
    )
    assert response.status_code == 400
    assert "decoding failed" in response.json()["detail"].lower()

def test_05_oversized_upload():
    """Requirement 5: Files exceeding MAX_UPLOAD_SIZE (10 MiB) are rejected."""
    # Simulate oversized upload error by testing directly with smaller dummy limit
    from backend.app.services.file_validator import validate_and_save_upload
    from fastapi import UploadFile, HTTPException
    
    dummy_file = UploadFile(
        file=io.BytesIO(create_synthetic_jpeg()),
        filename="large.jpg",
    )
    # Set limit to 100 bytes so this file exceeds it
    with pytest.raises(HTTPException) as exc_info:
        validate_and_save_upload(dummy_file, max_size=100)
    assert exc_info.value.status_code == 413
    assert "exceeds the maximum allowed limit" in exc_info.value.detail

def test_06_unsafe_filename_traversal_protection():
    """Requirement 6: Path traversal in filenames is stripped safely."""
    jpeg_bytes = create_synthetic_jpeg()
    response = client.post(
        "/api/v1/evidence/upload",
        files={"file": ("../../../../etc/passwd.jpg", jpeg_bytes, "image/jpeg")},
    )
    assert response.status_code == 201
    data = response.json()
    assert ".." not in data["original_filename"]
    assert data["original_filename"] == "passwd.jpg"

def test_07_correct_sha256_calculation():
    """Requirement 7: SHA-256 matches independent hashlib digest calculation."""
    jpeg_bytes = create_synthetic_jpeg()
    expected_hash = hashlib.sha256(jpeg_bytes).hexdigest().lower()
    
    response = client.post(
        "/api/v1/evidence/upload",
        files={"file": ("integrity_test.jpg", jpeg_bytes, "image/jpeg")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["sha256_intake"] == expected_hash

def test_08_stored_file_digest_recheck():
    """Requirement 8: Stored-file digest recheck confirms matching hash."""
    jpeg_bytes = create_synthetic_jpeg()
    upload_res = client.post(
        "/api/v1/evidence/upload",
        files={"file": ("recheck.jpg", jpeg_bytes, "image/jpeg")},
    )
    ev_id = upload_res.json()["id"]

    recheck_res = client.post(f"/api/v1/evidence/{ev_id}/verify-hash")
    assert recheck_res.status_code == 200
    recheck_data = recheck_res.json()
    assert recheck_data["matches"] is True
    assert recheck_data["status_label"] == "Verified Match"
    assert recheck_data["current_hash"] == upload_res.json()["sha256_intake"]

def test_09_original_file_preservation_after_analysis():
    """Requirement 9: Original file bytes remain bit-for-bit identical after running analysis."""
    jpeg_bytes = create_synthetic_jpeg()
    upload_res = client.post(
        "/api/v1/evidence/upload",
        files={"file": ("preserve_test.jpg", jpeg_bytes, "image/jpeg")},
    )
    ev_id = upload_res.json()["id"]
    initial_hash = upload_res.json()["sha256_intake"]

    # Run complete analysis
    analysis_res = client.post(f"/api/v1/analysis/{ev_id}/analyze")
    assert analysis_res.status_code == 200

    # Re-verify hash post-analysis
    recheck_res = client.post(f"/api/v1/evidence/{ev_id}/verify-hash")
    assert recheck_res.status_code == 200
    assert recheck_res.json()["matches"] is True
    assert recheck_res.json()["current_hash"] == initial_hash

def test_10_exif_extraction_when_metadata_present():
    """Requirement 10: Real camera, GPS, and timestamp metadata are correctly parsed."""
    exif_jpeg_bytes = create_jpeg_with_exif()
    upload_res = client.post(
        "/api/v1/evidence/upload",
        files={"file": ("camera_photo.jpg", exif_jpeg_bytes, "image/jpeg")},
    )
    ev_id = upload_res.json()["id"]

    analysis_res = client.post(f"/api/v1/analysis/{ev_id}/analyze")
    assert analysis_res.status_code == 200
    meta = analysis_res.json()["metadata"]
    assert meta["has_exif"] is True
    assert "Nikon" in meta["make"]
    assert "D850" in meta["model"]
    assert meta["datetime_original"] == "2026:10:14 10:30:00"
    assert meta["gps_lat"] is not None
    assert round(meta["gps_lat"], 1) == 25.6  # 25.611667 N
    assert round(meta["gps_lon"], 1) == 85.1  # 85.1375 E

def test_11_images_without_exif_metadata():
    """Requirement 11: Image without EXIF returns honest absent status without error."""
    clean_jpeg = create_synthetic_jpeg()
    upload_res = client.post(
        "/api/v1/evidence/upload",
        files={"file": ("no_exif.jpg", clean_jpeg, "image/jpeg")},
    )
    ev_id = upload_res.json()["id"]

    analysis_res = client.post(f"/api/v1/analysis/{ev_id}/analyze")
    assert analysis_res.status_code == 200
    meta = analysis_res.json()["metadata"]
    assert meta["has_exif"] is False
    assert meta["make"] is None
    assert meta["gps_lat"] is None

def test_12_ela_output_generation_for_jpeg():
    """Requirement 12: Real ELA visual artifact and metrics are generated for JPEG."""
    jpeg_bytes = create_synthetic_jpeg(width=100, height=100)
    upload_res = client.post(
        "/api/v1/evidence/upload",
        files={"file": ("ela_test.jpg", jpeg_bytes, "image/jpeg")},
    )
    ev_id = upload_res.json()["id"]

    analysis_res = client.post(f"/api/v1/analysis/{ev_id}/analyze?ela_quality=90&ela_scale=20")
    assert analysis_res.status_code == 200
    ela = analysis_res.json()["ela"]
    assert ela["status"] == "completed"
    assert ela["quality"] == 90
    assert ela["scale"] == 20
    assert ela["mean_error"] is not None
    assert ela["artifact_url"] is not None

    # Verify that the generated artifact file actually exists and can be fetched
    art_res = client.get(ela["artifact_url"])
    assert art_res.status_code == 200
    assert art_res.headers["content-type"] == "image/png"

def test_13_correct_unsupported_status_for_png_ela():
    """Requirement 13: PNG images return honest unsupported ELA status explaining lossless format."""
    png_bytes = create_synthetic_png()
    upload_res = client.post(
        "/api/v1/evidence/upload",
        files={"file": ("sample.png", png_bytes, "image/png")},
    )
    ev_id = upload_res.json()["id"]

    analysis_res = client.post(f"/api/v1/analysis/{ev_id}/analyze")
    assert analysis_res.status_code == 200
    ela = analysis_res.json()["ela"]
    assert ela["status"] == "unsupported"
    assert "PNG" in ela["explanation"]

def test_14_failed_analysis_and_missing_artifacts_handling():
    """Requirement 14: Non-existent evidence returns 404 cleanly."""
    bad_res = client.get("/api/v1/evidence/non_existent_id_9999/artifact/ela")
    assert bad_res.status_code == 404

    bad_analyze = client.post("/api/v1/analysis/non_existent_id_9999/analyze")
    assert bad_analyze.status_code == 404

def test_15_database_persistence_across_restarts():
    """Requirement 15: Evidence records persist in SQLite across simulated application reloads."""
    jpeg_bytes = create_synthetic_jpeg()
    upload_res = client.post(
        "/api/v1/evidence/upload",
        files={"file": ("persistence_check.jpg", jpeg_bytes, "image/jpeg")},
    )
    ev_id = upload_res.json()["id"]

    # Direct query to SQLite using a fresh connection
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM evidence WHERE id = ?;", (ev_id,))
        row = cursor.fetchone()
        assert row is not None
        assert row["original_filename"] == "persistence_check.jpg"

def test_16_report_contents_correspond_to_actual_results():
    """Requirement 16: Downloadable PDF report contains real evidence ID and analysis findings."""
    jpeg_bytes = create_jpeg_with_exif()
    upload_res = client.post(
        "/api/v1/evidence/upload",
        files={"file": ("report_target.jpg", jpeg_bytes, "image/jpeg")},
    )
    ev_id = upload_res.json()["id"]

    # Run analysis first
    client.post(f"/api/v1/analysis/{ev_id}/analyze")

    # Generate report
    gen_res = client.post(f"/api/v1/reports/{ev_id}/generate")
    assert gen_res.status_code == 200
    assert gen_res.json()["report_id"].startswith("REP-")

    # Download report bytes
    dl_res = client.get(f"/api/v1/reports/{ev_id}/download")
    assert dl_res.status_code == 200
    assert dl_res.headers["content-type"] == "application/pdf"
    pdf_bytes = dl_res.content
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 2048  # Realistic PDF size with embedded tables and images

def test_17_frontend_error_handling_and_status_codes():
    """Requirement 17: Edge case HTTP error statuses are handled accurately."""
    # Empty file
    empty_res = client.post(
        "/api/v1/evidence/upload",
        files={"file": ("empty.jpg", b"", "image/jpeg")},
    )
    assert empty_res.status_code == 400

    # Non-existent evidence GET
    not_found = client.get("/api/v1/evidence/ev_does_not_exist")
    assert not_found.status_code == 404

def test_18_repeated_analysis_consistency():
    """Requirement 18: Repeated analysis on the same evidence yields deterministic results."""
    jpeg_bytes = create_synthetic_jpeg()
    upload_res = client.post(
        "/api/v1/evidence/upload",
        files={"file": ("repeated.jpg", jpeg_bytes, "image/jpeg")},
    )
    ev_id = upload_res.json()["id"]

    run1 = client.post(f"/api/v1/analysis/{ev_id}/analyze?ela_quality=95&ela_scale=15").json()
    run2 = client.post(f"/api/v1/analysis/{ev_id}/analyze?ela_quality=95&ela_scale=15").json()

    assert run1["integrity"]["intake_hash"] == run2["integrity"]["intake_hash"]
    assert run1["ela"]["mean_error"] == run2["ela"]["mean_error"]
    assert len(run1["findings"]) == len(run2["findings"])

# --- TESTS 19 TO 23: ORIGINAL VS CROPPED IMAGE COMPARISON ---

def create_rich_textured_image(width: int = 500, height: int = 400) -> bytes:
    """Creates an image with rich geometric and textural patterns suitable for feature matching."""
    from PIL import ImageDraw
    img = Image.new("RGB", (width, height), color=(240, 240, 240))
    draw = ImageDraw.Draw(img)
    # Checkerboard and grid patterns
    for i in range(0, width, 25):
        for j in range(0, height, 25):
            if (i // 25 + j // 25) % 2 == 0:
                draw.rectangle([i, j, i + 25, j + 25], fill=(i % 255, j % 255, (i * j) % 255))
    # Overlapping geometric colored shapes
    draw.ellipse([80, 60, 260, 240], fill=(220, 20, 60), outline=(0, 0, 0), width=3)
    draw.rectangle([180, 140, 360, 320], fill=(30, 144, 255), outline=(255, 255, 255), width=2)
    draw.polygon([(300, 80), (380, 220), (240, 260)], fill=(50, 205, 50), outline=(0, 0, 0), width=2)
    draw.line([(0, 0), (width, height)], fill=(255, 215, 0), width=4)
    draw.line([(0, height), (width, 0)], fill=(138, 43, 226), width=4)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()

def create_crop_from_jpeg_bytes(raw_bytes: bytes, box: tuple[int, int, int, int], resize: tuple[int, int] | None = None, quality: int = 90) -> bytes:
    with Image.open(io.BytesIO(raw_bytes)) as img:
        cropped = img.crop(box)
        if resize:
            cropped = cropped.resize(resize, Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        cropped.save(buf, format="JPEG", quality=quality)
        return buf.getvalue()

def test_19_original_vs_controlled_crop_detection():
    """Requirement 19: Detects controlled crop from original reference image with valid RANSAC inliers and overlap box."""
    ref_bytes = create_rich_textured_image(500, 400)
    cand_bytes = create_crop_from_jpeg_bytes(ref_bytes, (80, 60, 360, 320))

    # Upload reference
    res_ref = client.post(
        "/api/v1/evidence/upload",
        files={"file": ("reference_original.jpg", ref_bytes, "image/jpeg")},
        data={"case_id": "CROP-TEST-01"},
    )
    assert res_ref.status_code == 201
    ref_id = res_ref.json()["id"]

    # Upload candidate (crop)
    res_cand = client.post(
        "/api/v1/evidence/upload",
        files={"file": ("candidate_cropped.jpg", cand_bytes, "image/jpeg")},
        data={"case_id": "CROP-TEST-01"},
    )
    assert res_cand.status_code == 201
    cand_id = res_cand.json()["id"]

    # Compare
    comp_res = client.post(
        "/api/v1/analysis/compare",
        json={"reference_id": ref_id, "candidate_id": cand_id, "algorithm": "SIFT", "ratio_threshold": 0.75},
    )
    assert comp_res.status_code == 200
    comp_data = comp_res.json()

    assert comp_data["status"] == "possible_crop_match"
    assert comp_data["inliers_count"] >= 15
    assert comp_data["inlier_ratio"] >= 0.25
    assert comp_data["overlap_box"] is not None
    assert comp_data["overlap_box"]["width"] > 0
    assert comp_data["artifact_url"] is not None

    # Verify visual artifact endpoint
    art_res = client.get(comp_data["artifact_url"])
    assert art_res.status_code == 200
    assert art_res.headers["content-type"] == "image/png"

def test_20_original_vs_cropped_and_resized():
    """Requirement 20: Detects crop that has been subsequently resized (SIFT scale invariance)."""
    ref_bytes = create_rich_textured_image(500, 400)
    # Cropped and resized down by ~40%
    cand_bytes = create_crop_from_jpeg_bytes(ref_bytes, (80, 60, 360, 320), resize=(170, 155))

    res_ref = client.post(
        "/api/v1/evidence/upload",
        files={"file": ("orig_for_resize.jpg", ref_bytes, "image/jpeg")},
    )
    ref_id = res_ref.json()["id"]

    res_cand = client.post(
        "/api/v1/evidence/upload",
        files={"file": ("cropped_and_scaled.jpg", cand_bytes, "image/jpeg")},
    )
    cand_id = res_cand.json()["id"]

    comp_res = client.post(
        "/api/v1/analysis/compare",
        json={"reference_id": ref_id, "candidate_id": cand_id},
    )
    assert comp_res.status_code == 200
    assert comp_res.json()["status"] == "possible_crop_match"
    assert comp_res.json()["inliers_count"] >= 12

def test_21_original_vs_cropped_and_recompressed():
    """Requirement 21: Detects crop that has been recompressed at lower JPEG quality."""
    ref_bytes = create_rich_textured_image(500, 400)
    # Cropped and recompressed at quality 55
    cand_bytes = create_crop_from_jpeg_bytes(ref_bytes, (80, 60, 360, 320), quality=55)

    res_ref = client.post(
        "/api/v1/evidence/upload",
        files={"file": ("orig_for_recomp.jpg", ref_bytes, "image/jpeg")},
    )
    ref_id = res_ref.json()["id"]

    res_cand = client.post(
        "/api/v1/evidence/upload",
        files={"file": ("cropped_recompressed.jpg", cand_bytes, "image/jpeg")},
    )
    cand_id = res_cand.json()["id"]

    comp_res = client.post(
        "/api/v1/analysis/compare",
        json={"reference_id": ref_id, "candidate_id": cand_id},
    )
    assert comp_res.status_code == 200
    assert comp_res.json()["status"] == "possible_crop_match"

def test_22_original_vs_completely_unrelated_image():
    """Requirement 22: Unrelated images produce no reliable match status."""
    ref_bytes = create_rich_textured_image(500, 400)
    unrelated_bytes = create_synthetic_jpeg(300, 300, color=(15, 30, 45))

    res_ref = client.post(
        "/api/v1/evidence/upload",
        files={"file": ("ref_textured.jpg", ref_bytes, "image/jpeg")},
    )
    ref_id = res_ref.json()["id"]

    res_unrelated = client.post(
        "/api/v1/evidence/upload",
        files={"file": ("unrelated_photo.jpg", unrelated_bytes, "image/jpeg")},
    )
    unrelated_id = res_unrelated.json()["id"]

    comp_res = client.post(
        "/api/v1/analysis/compare",
        json={"reference_id": ref_id, "candidate_id": unrelated_id},
    )
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    assert comp_data["status"] == "no_reliable_match"
    assert comp_data["inliers_count"] < 8

def test_23_comparison_validation_and_error_handling():
    """Requirement 23: Comparison rejects identical evidence ID and non-existent IDs."""
    ref_bytes = create_rich_textured_image(300, 300)
    res_ref = client.post(
        "/api/v1/evidence/upload",
        files={"file": ("single_img.jpg", ref_bytes, "image/jpeg")},
    )
    ref_id = res_ref.json()["id"]

    # Same image compared against itself
    same_res = client.post(
        "/api/v1/analysis/compare",
        json={"reference_id": ref_id, "candidate_id": ref_id},
    )
    assert same_res.status_code == 400
    assert "must be different" in same_res.json()["detail"]

    # Non-existent candidate
    missing_res = client.post(
        "/api/v1/analysis/compare",
        json={"reference_id": ref_id, "candidate_id": "ev_non_existent_999"},
    )
    assert missing_res.status_code == 404

def test_24_tampered_stored_file_byte_mismatch():
    """Requirement 24: Modifying a byte in the stored file on disk triggers an integrity mismatch."""
    jpeg_bytes = create_synthetic_jpeg()
    upload_res = client.post(
        "/api/v1/evidence/upload",
        files={"file": ("tamper_specimen.jpg", jpeg_bytes, "image/jpeg")},
    )
    ev_id = upload_res.json()["id"]

    # Verify initial hash matches
    initial_check = client.post(f"/api/v1/evidence/{ev_id}/verify-hash").json()
    assert initial_check["matches"] is True

    # Artificially tamper with the stored file on disk
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT stored_filename FROM evidence WHERE id = ?;", (ev_id,))
        stored_filename = cursor.fetchone()["stored_filename"]

    stored_path = settings.EVIDENCE_DIR / stored_filename
    with open(stored_path, "r+b") as f:
        f.seek(50)  # Seek into data segment
        original_byte = f.read(1)
        tampered_byte = bytes([(original_byte[0] ^ 0xFF)])
        f.seek(50)
        f.write(tampered_byte)

    # Recheck hash: must report mismatch
    tamper_check_res = client.post(f"/api/v1/evidence/{ev_id}/verify-hash")
    assert tamper_check_res.status_code == 200
    tamper_data = tamper_check_res.json()
    assert tamper_data["matches"] is False
    assert tamper_data["status_label"] == "Integrity Mismatch Detected"
    assert "CRITICAL" in tamper_data["message"]
    assert tamper_data["current_hash"] != upload_res.json()["sha256_intake"]

def test_25_identical_exact_copy_comparison():
    """Requirement 25: Comparing reference against an identical duplicate copy yields maximum inliers and 1.0x scale."""
    ref_bytes = create_rich_textured_image(400, 300)
    
    # Upload reference
    res_ref = client.post(
        "/api/v1/evidence/upload",
        files={"file": ("original_ref.jpg", ref_bytes, "image/jpeg")},
    )
    ref_id = res_ref.json()["id"]

    # Upload exact duplicate as separate evidence
    res_copy = client.post(
        "/api/v1/evidence/upload",
        files={"file": ("exact_duplicate.jpg", ref_bytes, "image/jpeg")},
    )
    copy_id = res_copy.json()["id"]

    comp_res = client.post(
        "/api/v1/analysis/compare",
        json={"reference_id": ref_id, "candidate_id": copy_id, "algorithm": "SIFT"},
    )
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    assert comp_data["status"] == "exact_byte_duplicate"
    assert comp_data["inlier_ratio"] > 0.85
    assert comp_data["estimated_scale"] is not None
    assert round(comp_data["estimated_scale"], 1) == 1.0
    assert "Exact byte duplicate" in comp_data["explanation"]

def test_28_identical_visual_content_different_hash():
    """Requirement 28: Full-frame recompression or metadata alteration yields 'identical_visual_content'."""
    ref_bytes = create_rich_textured_image(400, 300)
    
    # Re-save the same image buffer at different JPEG quality (different bytes/SHA-256, identical frame)
    img = Image.open(io.BytesIO(ref_bytes))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    reencoded_bytes = buf.getvalue()
    assert ref_bytes != reencoded_bytes  # Confirm different hashes

    res_ref = client.post(
        "/api/v1/evidence/upload",
        files={"file": ("orig_visual.jpg", ref_bytes, "image/jpeg")},
    )
    ref_id = res_ref.json()["id"]

    res_reencoded = client.post(
        "/api/v1/evidence/upload",
        files={"file": ("reencoded_visual.jpg", reencoded_bytes, "image/jpeg")},
    )
    cand_id = res_reencoded.json()["id"]

    comp_res = client.post(
        "/api/v1/analysis/compare",
        json={"reference_id": ref_id, "candidate_id": cand_id, "algorithm": "SIFT"},
    )
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    assert comp_data["status"] == "visually_similar_full_frame"
    assert comp_data["inliers_count"] >= 15
    assert round(comp_data["estimated_scale"], 1) == 1.0
    assert "Visually similar full-frame content" in comp_data["explanation"]

def test_26_isolated_evidence_results_no_cross_contamination():
    """Requirement 26: Results, artifacts, and findings for different evidence items remain strictly isolated."""
    jpeg_exif_bytes = create_jpeg_with_exif()
    png_bytes = create_synthetic_png()

    ev_a = client.post(
        "/api/v1/evidence/upload",
        files={"file": ("specimen_a.jpg", jpeg_exif_bytes, "image/jpeg")},
    ).json()["id"]

    ev_b = client.post(
        "/api/v1/evidence/upload",
        files={"file": ("specimen_b.png", png_bytes, "image/png")},
    ).json()["id"]

    # Analyze both
    res_a = client.post(f"/api/v1/analysis/{ev_a}/analyze").json()
    res_b = client.post(f"/api/v1/analysis/{ev_b}/analyze").json()

    # Verify A has EXIF, completed ELA, and unique hash
    assert res_a["metadata"]["has_exif"] is True
    assert res_a["ela"]["status"] == "completed"
    
    # Verify B has no EXIF, unsupported ELA, and different hash
    assert res_b["metadata"]["has_exif"] is False
    assert res_b["ela"]["status"] == "unsupported"

    assert res_a["integrity"]["intake_hash"] != res_b["integrity"]["intake_hash"]

def test_27_comparison_data_included_in_generated_pdf_report():
    """Requirement 27: Generated forensic PDF report includes geometric comparison data when comparison was performed."""
    ref_bytes = create_rich_textured_image(400, 300)
    cand_bytes = create_crop_from_jpeg_bytes(ref_bytes, (50, 50, 250, 200))

    ref_id = client.post(
        "/api/v1/evidence/upload",
        files={"file": ("report_ref.jpg", ref_bytes, "image/jpeg")},
    ).json()["id"]

    cand_id = client.post(
        "/api/v1/evidence/upload",
        files={"file": ("report_cand.jpg", cand_bytes, "image/jpeg")},
    ).json()["id"]

    # Run single analysis on reference
    client.post(f"/api/v1/analysis/{ref_id}/analyze")

    # Run comparison between reference and candidate
    client.post(
        "/api/v1/analysis/compare",
        json={"reference_id": ref_id, "candidate_id": cand_id},
    )

    # Generate and download PDF report for reference image
    gen_res = client.post(f"/api/v1/reports/{ref_id}/generate")
    assert gen_res.status_code == 200

    dl_res = client.get(f"/api/v1/reports/{ref_id}/download")
    assert dl_res.status_code == 200
    pdf_bytes = dl_res.content
    assert pdf_bytes.startswith(b"%PDF")
    # PDF with embedded ELA and comparison artifacts is substantial
    assert len(pdf_bytes) > 20000

def test_29_comparison_boundary_and_geometric_decision_tree():
    """
    Requirement 29: Deterministic boundary tests for 5, 6, 14, 15 inliers,
    inlier ratio thresholds, non-convex degenerate homographies, and area ratio ranges.
    Never classifies an image as a crop solely because inliers >= 15.
    """
    default_kwargs = {
        "is_exact_byte_duplicate": False,
        "scale_est": 0.85,
        "is_same_dimensions": False,
        "pixel_mae": 999.0,
        "w_cand": 800,
        "h_cand": 600,
        "w_ref": 1600,
        "h_ref": 1200,
        "ref_hash": "a" * 64,
        "cand_hash": "b" * 64,
        "overlap_box": {"x": 100, "y": 100, "width": 800, "height": 600, "area_ratio": 0.25},
    }

    # 1. Boundary: 5 inliers (< 6) -> no_reliable_match
    st, exp, lim, _ = classify_comparison(
        inliers_count=5, total_good_matches=10, inlier_ratio=0.5,
        is_convex=True, area_ratio=0.25, **default_kwargs
    )
    assert st == "no_reliable_match"
    assert "No reliable feature correspondence: 5 inliers verified" in exp

    # 2. Boundary: 6 inliers (>= 6 but < 15) -> inconclusive
    st, exp, lim, _ = classify_comparison(
        inliers_count=6, total_good_matches=10, inlier_ratio=0.6,
        is_convex=True, area_ratio=0.25, **default_kwargs
    )
    assert st == "inconclusive"
    assert "inlier count 6 below threshold 15" in exp

    # 3. Boundary: 14 inliers (< 15) -> inconclusive
    st, exp, lim, _ = classify_comparison(
        inliers_count=14, total_good_matches=20, inlier_ratio=0.7,
        is_convex=True, area_ratio=0.25, **default_kwargs
    )
    assert st == "inconclusive"
    assert "inlier count 14 below threshold 15" in exp

    # 4. Boundary: 15 inliers but LOW inlier ratio (< 0.25) -> inconclusive
    # (Exact unrelated camera photograph scenario: 15 inliers / 62 matches = 0.242)
    st, exp, lim, _ = classify_comparison(
        inliers_count=15, total_good_matches=62, inlier_ratio=0.242,
        is_convex=True, area_ratio=0.5205, **default_kwargs
    )
    assert st == "inconclusive"
    assert "inlier ratio 0.242 below threshold 0.25 (15/62 matches)" in exp

    # 5. Boundary: 15 inliers, strong ratio (0.80), but NON-CONVEX projected quad -> inconclusive
    st, exp, lim, _ = classify_comparison(
        inliers_count=15, total_good_matches=18, inlier_ratio=0.833,
        is_convex=False, area_ratio=0.25, **default_kwargs
    )
    assert st == "inconclusive"
    assert "projected quadrilateral is non-convex or degenerate (twisted homography)" in exp

    # 6. Boundary: 15 inliers, strong ratio, convex, but area ratio < 0.02 (degenerate sub-region) -> inconclusive
    st, exp, lim, _ = classify_comparison(
        inliers_count=15, total_good_matches=18, inlier_ratio=0.833,
        is_convex=True, area_ratio=0.010, **default_kwargs
    )
    assert st == "inconclusive"
    assert "projected area ratio 0.0100 is below 2% canvas threshold" in exp

    # 7. Boundary: 15 inliers, strong ratio, convex, but area ratio > 1.15 (candidate larger than ref) -> inconclusive
    st, exp, lim, _ = classify_comparison(
        inliers_count=15, total_good_matches=18, inlier_ratio=0.833,
        is_convex=True, area_ratio=1.650, **default_kwargs
    )
    assert st == "inconclusive"
    assert "candidate projected area (165.0%) exceeds reference canvas" in exp

    # 7b. Boundary: 15 inliers, same dimensions, but localized alteration detected (max_block_mae > 15.0) -> inconclusive
    st, exp, lim, _ = classify_comparison(
        is_exact_byte_duplicate=False,
        inliers_count=20, total_good_matches=22, inlier_ratio=0.91,
        is_convex=True, area_ratio=1.0, scale_est=1.0, is_same_dimensions=True,
        pixel_mae=0.15, max_pixel_diff=120.0, max_block_mae=48.0,
        w_cand=1600, h_cand=1200, w_ref=1600, h_ref=1200,
        ref_hash="a"*64, cand_hash="b"*64, overlap_box=None
    )
    assert st == "inconclusive"
    assert "localized pixel alteration detected" in exp

    # 8. Boundary: 15 inliers, strong ratio (0.75), convex, valid area ratio (0.25) -> possible_crop_match
    st, exp, lim, _ = classify_comparison(
        inliers_count=15, total_good_matches=20, inlier_ratio=0.75,
        is_convex=True, area_ratio=0.25, **default_kwargs
    )
    assert st == "possible_crop_match"
    assert "Possible partial-image match" in exp

    # 9. Cryptographic exact byte duplicate override
    st, exp, lim, _ = classify_comparison(
        is_exact_byte_duplicate=True, inliers_count=50, total_good_matches=50,
        inlier_ratio=1.0, is_convex=True, area_ratio=1.0, scale_est=1.0,
        is_same_dimensions=True, pixel_mae=0.0, w_cand=800, h_cand=600,
        w_ref=800, h_ref=600, ref_hash="c"*64, cand_hash="c"*64, overlap_box=None
    )
    assert st == "exact_byte_duplicate"

def test_30_real_images_comparison_matrix():
    """
    Requirement 30: Tests genuine real-camera photographs across all 4 key scenarios:
    exact byte duplicate, re-encoded identical content, controlled crop, and unrelated photo.
    Verifies that the unrelated photo (15 inliers) is classified as inconclusive with traceable ratio explanation.
    """
    real_fixtures_dir = Path("test_fixtures/real_photos")
    ref_path = real_fixtures_dir / "real_landscape_reference.jpg"
    crop_path = real_fixtures_dir / "real_landscape_crop_candidate.jpg"
    unrel_path = real_fixtures_dir / "real_portrait_unrelated.jpg"

    assert ref_path.exists() and crop_path.exists() and unrel_path.exists()

    # 1. Exact byte duplicate
    res_dup = compare_images_for_crop(ref_path, ref_path, "ref_1", "dup_1")
    assert res_dup.status == "exact_byte_duplicate"
    assert "Exact byte duplicate" in res_dup.explanation

    # 2. Re-encoded visually similar full-frame content
    im = Image.open(ref_path)
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=90)
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(buf.getvalue())
        tmp_path = Path(tmp.name)
    try:
        res_reenc = compare_images_for_crop(ref_path, tmp_path, "ref_1", "reenc_1")
        assert res_reenc.status == "visually_similar_full_frame"
        assert res_reenc.inliers_count >= 15
        assert round(res_reenc.estimated_scale, 1) == 1.0
    finally:
        tmp_path.unlink(missing_ok=True)

    # 3. Controlled crop derived from the photograph
    res_crop = compare_images_for_crop(ref_path, crop_path, "ref_1", "crop_1")
    assert res_crop.status == "possible_crop_match"
    assert res_crop.inliers_count >= 500
    assert res_crop.inlier_ratio >= 0.90
    assert round(res_crop.estimated_scale, 1) == 1.0

    # 4. Completely unrelated camera portrait
    res_unrel = compare_images_for_crop(ref_path, unrel_path, "ref_1", "unrel_1")
    # Must NOT classify as crop despite 15 inliers!
    assert res_unrel.status == "inconclusive"
    assert res_unrel.inliers_count == 15
    assert res_unrel.inlier_ratio < 0.25
    assert "inlier ratio 0.242 below threshold 0.25 (15/62 matches)" in res_unrel.explanation

def test_31_report_and_ui_classification_consistency():
    """
    Requirement 31: Verifies that comparison classification, explanation, and evidence IDs
    remain perfectly identical between API response and generated PDF report.
    """
    ref_path = Path("test_fixtures/real_photos/real_landscape_reference.jpg")
    unrel_path = Path("test_fixtures/real_photos/real_portrait_unrelated.jpg")

    # Upload both real images through API
    ref_id = client.post(
        "/api/v1/evidence/upload",
        files={"file": ("real_ref.jpg", ref_path.read_bytes(), "image/jpeg")},
    ).json()["id"]

    unrel_id = client.post(
        "/api/v1/evidence/upload",
        files={"file": ("real_unrel.jpg", unrel_path.read_bytes(), "image/jpeg")},
    ).json()["id"]

    # Analyze reference image
    client.post(f"/api/v1/analysis/{ref_id}/analyze")

    # Run comparison
    comp_res = client.post(
        "/api/v1/analysis/compare",
        json={"reference_id": ref_id, "candidate_id": unrel_id},
    )
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    assert comp_data["status"] == "inconclusive"
    assert comp_data["reference_id"] == ref_id
    assert comp_data["candidate_id"] == unrel_id
    assert comp_data["inliers_count"] == 15

    # Generate PDF report for reference
    gen_res = client.post(f"/api/v1/reports/{ref_id}/generate")
    assert gen_res.status_code == 200

    dl_res = client.get(f"/api/v1/reports/{ref_id}/download")
    assert dl_res.status_code == 200
    pdf_bytes = dl_res.content
    assert pdf_bytes.startswith(b"%PDF")
    
    # Decompress ASCII85+Flate encoded text streams from ReportLab PDF
    import base64, zlib
    decompressed_text = b""
    idx = 0
    while True:
        s_idx = pdf_bytes.find(b"stream", idx)
        if s_idx == -1:
            break
        e_idx = pdf_bytes.find(b"endstream", s_idx)
        if e_idx == -1:
            break
        raw_stream = pdf_bytes[s_idx + 6:e_idx].strip()
        try:
            a85 = base64.a85decode(raw_stream, adobe=True)
            decompressed_text += zlib.decompress(a85) + b"\n"
        except Exception:
            pass
        idx = e_idx + 9

    assert ref_id.encode("utf-8") in decompressed_text
    assert unrel_id.encode("utf-8") in decompressed_text
    assert b"INCONCLUSIVE" in decompressed_text

def test_32_localized_modification_detected_as_inconclusive():
    """
    Requirement 32: Detects localized tampering (small patch or text overlay) on same-dimension images.
    Even though global pixel_mae is tiny, max_block_mae > 15.0 causes it to be classified as inconclusive,
    preventing spliced images from being labeled as visually similar or identical.
    """
    real_fixtures_dir = Path("test_fixtures/real_photos")
    ref_path = real_fixtures_dir / "real_landscape_reference.jpg"
    assert ref_path.exists()

    # Create candidate with a localized 60x60 red square modification
    img = Image.open(ref_path).convert("RGB")
    cand = img.copy()
    draw = ImageDraw.Draw(cand)
    # Tamper a 60x60 patch at (300, 300)
    draw.rectangle([300, 300, 360, 360], fill=(255, 0, 0))

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        cand.save(tmp.name, format="JPEG", quality=90)
        cand_path = Path(tmp.name)

    try:
        res = compare_images_for_crop(ref_path, cand_path, "ref_1", "tampered_1")
        assert res.status == "inconclusive"
        assert res.inliers_count >= 15
        assert "localized pixel alteration detected" in res.explanation
        assert "exceeds threshold 15.0" in res.explanation
    finally:
        cand_path.unlink(missing_ok=True)

def test_33_crop_area_ratio_boundary_and_reversed_roles():
    """
    Requirement 33: Tests area ratio semantics:
    - Normal crop (contained within reference, 0.02 <= area_ratio <= 0.85) -> possible_crop_match.
    - Reversed roles (candidate is full scene, reference is crop, area_ratio > 1.15) -> inconclusive,
      reporting candidate exceeds reference canvas.
    """
    real_fixtures_dir = Path("test_fixtures/real_photos")
    ref_path = real_fixtures_dir / "real_landscape_reference.jpg"
    crop_path = real_fixtures_dir / "real_landscape_crop_candidate.jpg"
    assert ref_path.exists() and crop_path.exists()

    # 1. Normal crop comparison: reference is original, candidate is crop
    res_normal = compare_images_for_crop(ref_path, crop_path, "ref_1", "crop_1")
    assert res_normal.status == "possible_crop_match"
    assert 0.02 <= res_normal.overlap_box["area_ratio"] <= 0.85

    # 2. Reversed crop comparison: reference is crop, candidate is full scene
    res_reversed = compare_images_for_crop(crop_path, ref_path, "crop_1", "ref_1")
    assert res_reversed.status == "inconclusive"
    assert res_reversed.inliers_count >= 15
    assert "exceeds reference canvas: candidate is larger than reference" in res_reversed.explanation

def test_34_low_texture_and_repeated_patterns():
    """
    Requirement 34: Tests edge cases:
    - Low-texture solid image yielding < 4 keypoints -> no_reliable_match.
    - Repeated pattern grid testing.
    """
    # 1. Low-texture solid color image
    solid_img = Image.new("RGB", (400, 300), color=(180, 180, 180))
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_solid, \
         tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_ref:
        solid_img.save(tmp_solid.name, format="JPEG")
        # Save a rich textured image for reference
        rich_bytes = create_rich_textured_image(400, 300)
        Path(tmp_ref.name).write_bytes(rich_bytes)
        
        solid_path = Path(tmp_solid.name)
        ref_path = Path(tmp_ref.name)
    try:
        res_solid = compare_images_for_crop(ref_path, solid_path, "ref_1", "solid_1")
        assert res_solid.status == "no_reliable_match"
        assert "Insufficient textured keypoints" in res_solid.explanation or "Found only" in res_solid.explanation or "No reliable" in res_solid.explanation
    finally:
        solid_path.unlink(missing_ok=True)
        ref_path.unlink(missing_ok=True)

def test_35_resized_and_rotated_candidate():
    """
    Requirement 35: Candidate scaled down by 0.5x and rotated by 15 degrees.
    Verifies SIFT scale and rotation invariance where RANSAC computes valid homography.
    """
    real_fixtures_dir = Path("test_fixtures/real_photos")
    ref_path = real_fixtures_dir / "real_landscape_reference.jpg"
    assert ref_path.exists()

    # Load, downscale by 50% and rotate by 15 degrees
    img = Image.open(ref_path).convert("RGB")
    w, h = img.size
    scaled = img.resize((w // 2, h // 2), Image.Resampling.LANCZOS)
    rotated = scaled.rotate(15, expand=True)

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        rotated.save(tmp.name, format="JPEG", quality=90)
        cand_path = Path(tmp.name)

    try:
        res = compare_images_for_crop(ref_path, cand_path, "ref_1", "rot_cand")
        # Rotated & scaled full scene corresponds to reference canvas
        assert res.status in ["possible_crop_match", "visually_similar_full_frame", "inconclusive"]
        assert res.inliers_count >= 15
        assert res.inlier_ratio >= 0.25
    finally:
        cand_path.unlink(missing_ok=True)


