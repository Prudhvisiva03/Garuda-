"""
Automated Pytest Suite for Official Organizer-Provided Hackathon Datasets.
Tests:
- Image data Pairs 1-5
- Mismatched extension handling
- Video data container metrics
- Voice data stream metrics
- Data-2 image analysis & PDF generation
"""
import os
import hashlib
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from PIL import Image
import numpy as np

from backend.app.main import app
from scripts.validate_official_datasets import (
    get_dataset_dir,
    calculate_sha256,
    detect_file_signature,
    parse_video_properties,
    parse_audio_properties,
)

client = TestClient(app)


@pytest.fixture(scope="module")
def dataset_root() -> Path:
    try:
        return get_dataset_dir()
    except FileNotFoundError:
        pytest.skip("Official hackathon datasets not found. Set GARUDA_TEST_DATA_DIR to run.")


def test_official_image_pair_1_metadata_and_near_identical_pixels(dataset_root: Path):
    """
    Image 1: Metadata differences and nearly unchanged pixels.
    Orig (309x250) vs Copy (309x250). Pixel MAE ~ 0.35, Peak diff = 9.0.
    Classified as visually_similar_full_frame with differing hashes.
    """
    p_orig = dataset_root / "Image data" / "Original file" / "Image-1.jpg"
    p_copy = dataset_root / "Image data" / "Image-1 copy.jpg"
    assert p_orig.exists() and p_copy.exists()

    res_orig = client.post("/api/v1/evidence/upload", files={"file": (p_orig.name, p_orig.read_bytes(), "image/jpeg")}).json()
    res_copy = client.post("/api/v1/evidence/upload", files={"file": (p_copy.name, p_copy.read_bytes(), "image/jpeg")}).json()

    assert res_orig["sha256_intake"] != res_copy["sha256_intake"]

    an_orig = client.post(f"/api/v1/analysis/{res_orig['id']}/analyze").json()
    an_copy = client.post(f"/api/v1/analysis/{res_copy['id']}/analyze").json()
    assert an_orig["metadata"]["has_exif"] is True
    assert an_copy["metadata"]["has_exif"] is True

    comp = client.post("/api/v1/analysis/compare", json={"reference_id": res_orig["id"], "candidate_id": res_copy["id"]}).json()
    assert comp["status"] == "visually_similar_full_frame"
    assert comp["inliers_count"] >= 500
    assert round(comp["estimated_scale"], 1) == 1.0


def test_official_image_pair_2_resizing_and_appearance_differences(dataset_root: Path):
    """
    Image 2: Resizing (963x882 vs 1311x1200) and appearance differences.
    Classified conservatively as inconclusive due to scale mismatch (0.73x).
    """
    p_orig = dataset_root / "Image data" / "Original file" / "Image-2.png"
    p_copy = dataset_root / "Image data" / "Image-2 copy.png"
    assert p_orig.exists() and p_copy.exists()

    res_orig = client.post("/api/v1/evidence/upload", files={"file": (p_orig.name, p_orig.read_bytes(), "image/png")}).json()
    res_copy = client.post("/api/v1/evidence/upload", files={"file": (p_copy.name, p_copy.read_bytes(), "image/png")}).json()

    assert (res_orig["width"], res_orig["height"]) != (res_copy["width"], res_copy["height"])

    comp = client.post("/api/v1/analysis/compare", json={"reference_id": res_orig["id"], "candidate_id": res_copy["id"]}).json()
    assert comp["status"] == "inconclusive"
    assert "lacks required identity scale" in comp["explanation"]


def test_official_image_pair_3_substantial_visual_differences(dataset_root: Path):
    """
    Image 3: Substantial visual differences (global MAE > 50, peak diff 255).
    Classified as inconclusive with localized alteration detected and low inlier ratio.
    """
    p_orig = dataset_root / "Image data" / "Original file" / "Image-3.png"
    p_copy = dataset_root / "Image data" / "Image-3 copy.png"
    assert p_orig.exists() and p_copy.exists()

    res_orig = client.post("/api/v1/evidence/upload", files={"file": (p_orig.name, p_orig.read_bytes(), "image/png")}).json()
    res_copy = client.post("/api/v1/evidence/upload", files={"file": (p_copy.name, p_copy.read_bytes(), "image/png")}).json()

    comp = client.post("/api/v1/analysis/compare", json={"reference_id": res_orig["id"], "candidate_id": res_copy["id"]}).json()
    assert comp["status"] == "inconclusive"
    assert "inlier ratio" in comp["explanation"] or "localized pixel alteration" in comp["explanation"]


def test_official_image_pair_4_cctv_timestamp_overlay(dataset_root: Path):
    """
    Image 4: Changed visible CCTV timestamp/camera overlays (1672x941 vs 1671x941).
    Full scene correspondence maintained.
    """
    p_orig = dataset_root / "Image data" / "Original file" / "Image-4.png"
    p_copy = dataset_root / "Image data" / "Image-4 copy.png"
    assert p_orig.exists() and p_copy.exists()

    res_orig = client.post("/api/v1/evidence/upload", files={"file": (p_orig.name, p_orig.read_bytes(), "image/png")}).json()
    res_copy = client.post("/api/v1/evidence/upload", files={"file": (p_copy.name, p_copy.read_bytes(), "image/png")}).json()

    comp = client.post("/api/v1/analysis/compare", json={"reference_id": res_orig["id"], "candidate_id": res_copy["id"]}).json()
    assert comp["status"] in ["visually_similar_full_frame", "possible_crop_match"]
    assert comp["inliers_count"] >= 100


def test_official_image_pair_5_identical_decoded_rgb_pixels_different_hashes(dataset_root: Path):
    """
    Image 5: Exactly identical decoded RGB pixels (MAE = 0.000) despite different file hashes.
    Classified as visually_similar_full_frame with 3000 inliers and 1.0x scale.
    """
    p_orig = dataset_root / "Image data" / "Original file" / "Image-5.png"
    p_copy = dataset_root / "Image data" / "Image-5 copy.png"
    assert p_orig.exists() and p_copy.exists()

    res_orig = client.post("/api/v1/evidence/upload", files={"file": (p_orig.name, p_orig.read_bytes(), "image/png")}).json()
    res_copy = client.post("/api/v1/evidence/upload", files={"file": (p_copy.name, p_copy.read_bytes(), "image/png")}).json()

    # Confirm different file hashes
    assert res_orig["sha256_intake"] != res_copy["sha256_intake"]

    # Confirm identical decoded pixels
    im_orig = Image.open(p_orig)
    im_copy = Image.open(p_copy)
    arr1 = np.array(im_orig.convert("RGB"), dtype=np.float32)
    arr2 = np.array(im_copy.convert("RGB"), dtype=np.float32)
    assert np.max(np.abs(arr1 - arr2)) == 0.0

    comp = client.post("/api/v1/analysis/compare", json={"reference_id": res_orig["id"], "candidate_id": res_copy["id"]}).json()
    assert comp["status"] == "visually_similar_full_frame"
    assert comp["inliers_count"] == 3000
    assert round(comp["estimated_scale"], 1) == 1.0


def test_official_mismatched_extensions(dataset_root: Path):
    """
    Mismatched extension files:
    - Audio.mp3: empty (0 bytes) -> HTTP 400
    - Doc.pdf: JPEG named PDF -> HTTP 201 (safe ingestion as JPEG)
    - Image.jpg: Word docx named JPG -> HTTP 415
    - Video.mp4: Excel xlsx named MP4 -> HTTP 415
    - data.xls: MP4 named XLS -> HTTP 415
    """
    mismatch_dir = dataset_root / "Mismatched extension"
    assert mismatch_dir.exists()

    # 1. Audio.mp3 (0 bytes)
    p_audio = mismatch_dir / "Audio.mp3"
    r_audio = client.post("/api/v1/evidence/upload", files={"file": (p_audio.name, p_audio.read_bytes(), "audio/mpeg")})
    assert r_audio.status_code == 400

    # 2. Doc.pdf (JPEG disguised as PDF)
    p_pdf = mismatch_dir / "Doc.pdf"
    r_pdf = client.post("/api/v1/evidence/upload", files={"file": (p_pdf.name, p_pdf.read_bytes(), "application/pdf")})
    assert r_pdf.status_code == 201
    assert r_pdf.json()["mime_type"] == "image/jpeg"

    # 3. Image.jpg (DOCX disguised as JPG)
    p_jpg = mismatch_dir / "Image.jpg"
    r_jpg = client.post("/api/v1/evidence/upload", files={"file": (p_jpg.name, p_jpg.read_bytes(), "image/jpeg")})
    assert r_jpg.status_code == 415

    # 4. Video.mp4 (XLSX disguised as MP4)
    p_mp4 = mismatch_dir / "Video.mp4"
    r_mp4 = client.post("/api/v1/evidence/upload", files={"file": (p_mp4.name, p_mp4.read_bytes(), "video/mp4")})
    assert r_mp4.status_code == 415

    # 5. data.xls (MP4 disguised as XLS)
    p_xls = mismatch_dir / "data.xls"
    r_xls = client.post("/api/v1/evidence/upload", files={"file": (p_xls.name, p_xls.read_bytes(), "application/vnd.ms-excel")})
    assert r_xls.status_code == 415


def test_official_video_data_container_metrics(dataset_root: Path):
    """
    Video data files:
    Extracts actual container metrics (codec, fps, duration, dimensions).
    Upload attempts must return HTTP 415 (unsupported media type).
    """
    vid_dir = dataset_root / "Video data"
    assert vid_dir.exists()

    for p in vid_dir.glob("*.mp4"):
        props = parse_video_properties(p)
        assert props["accessible"] is True
        assert props["width"] > 0 and props["height"] > 0
        assert props["fps"] > 0
        assert props["duration_sec"] > 0

        # Upload attempt
        res = client.post("/api/v1/evidence/upload", files={"file": (p.name, p.read_bytes(), "video/mp4")})
        assert res.status_code == 415


def test_official_voice_data_stream_metrics(dataset_root: Path):
    """
    Voice data files:
    Extracts format, sample rate, channels, and duration.
    Upload attempts return HTTP 415.
    """
    voice_dir = dataset_root / "Voice data"
    assert voice_dir.exists()

    for p in voice_dir.iterdir():
        if p.suffix.lower() not in [".mp3", ".wav"]:
            continue
        props = parse_audio_properties(p)
        assert "sample_rate_hz" in props
        assert props["sample_rate_hz"] in [44100, 48000, 32000, 16000]

        mime = "audio/mpeg" if p.suffix.lower() == ".mp3" else "audio/wav"
        res = client.post("/api/v1/evidence/upload", files={"file": (p.name, p.read_bytes(), mime)})
        assert res.status_code == 415


def test_official_data_2_images_and_pdf(dataset_root: Path):
    """
    Data-2 images:
    Ingests 5 PNG images, verifies hash, runs analysis, and compiles PDF report.
    """
    data2_dir = dataset_root / "Data-2"
    assert data2_dir.exists()

    for p in (data2_dir / "Image").glob("*.png"):
        res = client.post("/api/v1/evidence/upload", files={"file": (p.name, p.read_bytes(), "image/png")})
        assert res.status_code == 201
        ev_id = res.json()["id"]

        chk = client.post(f"/api/v1/evidence/{ev_id}/verify-hash").json()
        assert chk["matches"] is True

        an = client.post(f"/api/v1/analysis/{ev_id}/analyze").json()
        assert "findings" in an
        assert len(an["findings"]) >= 3

        rep = client.post(f"/api/v1/reports/{ev_id}/generate")
        assert rep.status_code == 200

        dl = client.get(f"/api/v1/reports/{ev_id}/download")
        assert dl.status_code == 200 and dl.content.startswith(b"%PDF")


def test_official_dataset_accounting_reconciliation(dataset_root: Path):
    """
    Test 45: Official Hackathon Dataset Accounting Reconciliation.
    Verifies:
    1. Physical disk inventory: exactly 32 physical evidence specimens + 3 documentation files = 35 files.
    2. Dataset breakdown: 10 Image, 5 Mismatch, 5 Video, 6 Voice, 6 Data-2.
    3. Programmatic reconciliation: 16 Ingested + 16 Rejected + 0 Skipped + 0 Failed == 32 Physical Files.
    4. 27 distinct validation cases (5 comparison pairs [10 files] + 22 single-file cases).
    5. JSON and CSV validation reports exist, match accounting, and clearly distinguish
       successful execution from validated detections.
    """
    import json
    import csv

    # 1. Inspect physical files on disk
    all_files = [f for f in sorted(dataset_root.rglob("*")) if f.is_file()]
    doc_files = [f for f in all_files if f.suffix.lower() in [".docx", ".txt", ".md"]]
    evidence_files = [f for f in all_files if f.suffix.lower() not in [".docx", ".txt", ".md"]]

    assert len(all_files) == 35, f"Expected 35 total files on disk, found {len(all_files)}"
    assert len(doc_files) == 3, f"Expected 3 documentation files, found {len(doc_files)}"
    assert len(evidence_files) == 32, f"Expected 32 physical evidence files, found {len(evidence_files)}"

    # Check dataset breakdown
    breakdown = {}
    for ef in evidence_files:
        top_dir = ef.relative_to(dataset_root).parts[0]
        breakdown[top_dir] = breakdown.get(top_dir, 0) + 1

    assert breakdown == {
        "Image data": 10,
        "Mismatched extension": 5,
        "Video data": 5,
        "Voice data": 6,
        "Data-2": 6,
    }

    # 2. Verify JSON report accounting
    json_path = Path("reports/official_dataset_validation.json")
    assert json_path.exists(), "reports/official_dataset_validation.json must exist"

    with open(json_path, "r", encoding="utf-8") as f:
        rep_json = json.load(f)

    summary = rep_json["accounting_summary"]
    assert summary["total_files_on_disk"] == 35
    assert summary["documentation_files_count"] == 3
    assert summary["physical_evidence_files_count"] == 32
    assert summary["validation_cases_count"] == 27
    assert summary["files_ingested"] == 16
    assert summary["files_rejected"] == 16
    assert summary["files_skipped"] == 0
    assert summary["files_failed"] == 0
    assert summary["reconciliation_balanced"] is True
    assert summary["files_ingested"] + summary["files_rejected"] == 32

    assert len(rep_json["physical_files"]) == 32
    assert len(rep_json["validation_cases"]) == 27
    assert len(rep_json["documentation_files"]) == 3

    # 3. Verify CSV report
    csv_path = Path("reports/official_dataset_validation.csv")
    assert csv_path.exists(), "reports/official_dataset_validation.csv must exist"

    with open(csv_path, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 32, f"CSV should contain exactly 32 physical files, found {len(rows)}"
    csv_ingested = sum(1 for r in rows if r["intake_status"] == "INGESTED")
    csv_rejected = sum(1 for r in rows if r["intake_status"] == "REJECTED")
    assert csv_ingested == 16
    assert csv_rejected == 16

    for r in rows:
        assert len(r["sha256"]) == 64, f"Invalid SHA-256 in CSV for {r['filename']}"
        assert r["validation_case_id"].startswith("CASE-")
        assert r["intake_status"] in ["INGESTED", "REJECTED"]

    # 4. Verify distinction between execution and detection
    for vc in rep_json["validation_cases"]:
        assert vc["execution_status"] == "SUCCESS", "All test pipelines must execute without unhandled errors"
        assert "validated_detection_statement" in vc and len(vc["validated_detection_statement"]) > 10

        # Video and voice cases must honestly report UNSUPPORTED detection status
        if vc["case_type"] in ["VIDEO_CONTAINER_INSPECTION", "VOICE_STREAM_INSPECTION"]:
            assert "UNSUPPORTED" in vc["forensic_result"]
            assert "UNSUPPORTED" in vc["validated_detection_statement"]
