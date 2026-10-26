"""
Automated Pytest Suite for Garuda Video Forensics Engine
Complies with SWGDE & ISO/IEC 27037 standards:
- MP4 container intake & cryptographic hashing
- Secondary write verification & vault tamper detection
- Temporal cut / splicing detection via Bhattacharyya distance & Z-score
- Color profile & Night theme / infrared filter detection
- Keyframe extraction & noise analysis
- Structured PDF Video Forensic Report compilation
"""
import io
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.config import settings

client = TestClient(app)

VID_DATA_DIR = Path("test_datasets/Video data")


@pytest.fixture(scope="module")
def video_files() -> dict[str, Path]:
    if not VID_DATA_DIR.exists():
        pytest.skip("Test video dataset not found. Skipping video forensics tests.")
    files = {p.name: p for p in VID_DATA_DIR.glob("*.mp4")}
    return files


def test_01_video_upload_and_magic_byte_verification(video_files: dict[str, Path]):
    """Tests genuine MP4 upload, hash recording, and rejection of invalid media."""
    p_v4 = video_files.get("video-4.mp4")
    assert p_v4 and p_v4.exists()

    # 1. Genuine video upload
    res = client.post(
        "/api/v1/video/upload",
        files={"file": (p_v4.name, p_v4.read_bytes(), "video/mp4")},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["id"].startswith("ev_vid_")
    assert len(data["sha256_intake"]) == 64
    assert data["mime_type"] == "video/mp4"
    assert data["width"] == 1920
    assert data["height"] == 1080

    # 2. Rejection of empty file
    res_empty = client.post("/api/v1/video/upload", files={"file": ("empty.mp4", b"", "video/mp4")})
    assert res_empty.status_code == 400

    # 3. Rejection of fake header (e.g. text file named .mp4)
    res_fake = client.post("/api/v1/video/upload", files={"file": ("fake.mp4", b"NOT A VIDEO HEADER DUMMY", "video/mp4")})
    assert res_fake.status_code == 415


def test_02_video_forensics_analysis_on_video_2_clipped_and_night_theme(video_files: dict[str, Path]):
    """
    Video-2: 'Clipped and night theme applied' (Organizer ground truth).
    Verifies that EviSutra detects both the night theme (monochrome saturation collapse)
    and the temporal cut at frame 133 (5.32s).
    """
    p_v2 = video_files.get("Video-2.mp4")
    assert p_v2 and p_v2.exists()

    res_upload = client.post("/api/v1/video/upload", files={"file": (p_v2.name, p_v2.read_bytes(), "video/mp4")})
    assert res_upload.status_code == 201
    ev_id = res_upload.json()["id"]

    res_an = client.post(f"/api/v1/video/{ev_id}/analyze")
    assert res_an.status_code == 200
    an = res_an.json()

    assert an["classification"] == "cut_and_color_grading_detected"
    assert an["color_profile"]["night_theme_detected"] is True
    assert an["color_profile"]["mean_saturation"] < 25.0
    assert an["temporal_cuts"]["cuts_detected_count"] >= 1

    # Verify cut near 5.3s
    cut_timestamps = [c["timestamp_sec"] for c in an["temporal_cuts"]["cuts"]]
    assert any(abs(t - 5.32) < 0.5 for t in cut_timestamps)

    # Verify keyframes
    assert len(an["keyframes"]) >= 3
    for kf in an["keyframes"]:
        art_path = Path(kf["artifact_path"])
        assert art_path.exists() and art_path.stat().st_size > 0


def test_03_video_forensics_analysis_on_video_3_night_theme(video_files: dict[str, Path]):
    """
    video-3: 'Night theme applied' (Organizer ground truth).
    Verifies detection of synthetic night-theme color grading.
    """
    p_v3 = video_files.get("video-3.mp4")
    assert p_v3 and p_v3.exists()

    res_upload = client.post("/api/v1/video/upload", files={"file": (p_v3.name, p_v3.read_bytes(), "video/mp4")})
    assert res_upload.status_code == 201
    ev_id = res_upload.json()["id"]

    res_an = client.post(f"/api/v1/video/{ev_id}/analyze")
    assert res_an.status_code == 200
    an = res_an.json()

    assert an["color_profile"]["night_theme_detected"] is True
    assert an["color_profile"]["mean_saturation"] < 32.0


def test_04_video_forensics_analysis_on_video_4_original(video_files: dict[str, Path]):
    """
    video-4: 'Original video' (Organizer ground truth).
    Verifies that genuine, continuous night CCTV footage is NOT misclassified as a cut.
    """
    p_v4 = video_files.get("video-4.mp4")
    assert p_v4 and p_v4.exists()

    res_upload = client.post("/api/v1/video/upload", files={"file": (p_v4.name, p_v4.read_bytes(), "video/mp4")})
    assert res_upload.status_code == 201
    ev_id = res_upload.json()["id"]

    res_an = client.post(f"/api/v1/video/{ev_id}/analyze")
    assert res_an.status_code == 200
    an = res_an.json()

    assert an["classification"] == "natural_continuous_stream"
    assert an["temporal_cuts"]["cuts_detected_count"] == 0
    assert an["color_profile"]["night_theme_detected"] is False


def test_05_video_forensics_analysis_on_video_5_original_color(video_files: dict[str, Path]):
    """
    video-5: 'Original video' (Organizer ground truth, daytime color procession).
    Verifies high saturation, continuous timeline, and zero false cut alarms despite moving crowd.
    """
    p_v5 = video_files.get("video-5.mp4")
    assert p_v5 and p_v5.exists()

    res_upload = client.post("/api/v1/video/upload", files={"file": (p_v5.name, p_v5.read_bytes(), "video/mp4")})
    assert res_upload.status_code == 201
    ev_id = res_upload.json()["id"]

    res_an = client.post(f"/api/v1/video/{ev_id}/analyze")
    assert res_an.status_code == 200
    an = res_an.json()

    assert an["classification"] == "natural_continuous_stream"
    assert an["color_profile"]["mean_saturation"] > 90.0
    assert an["temporal_cuts"]["cuts_detected_count"] == 0


def test_06_video_pdf_report_generation(video_files: dict[str, Path]):
    """
    Verifies generation of SWGDE/ISO 27037 compliant Video Examination PDF report.
    """
    p_v2 = video_files.get("Video-2.mp4")
    assert p_v2 and p_v2.exists()

    res_upload = client.post("/api/v1/video/upload", files={"file": (p_v2.name, p_v2.read_bytes(), "video/mp4")})
    ev_id = res_upload.json()["id"]

    # Download report
    res_rep = client.get(f"/api/v1/video/{ev_id}/report")
    assert res_rep.status_code == 200
    assert res_rep.headers["content-type"] == "application/pdf"
    assert res_rep.content.startswith(b"%PDF")
    assert len(res_rep.content) > 50000  # Multi-page PDF with embedded keyframes


def test_07_tampered_video_vault_detection(video_files: dict[str, Path]):
    """
    Tamper Detection:
    If bytes of deposited video evidence in vault are altered, analyze endpoint
    must catch the mismatch and reject execution.
    """
    p_v4 = video_files.get("video-4.mp4")
    assert p_v4 and p_v4.exists()

    res_upload = client.post("/api/v1/video/upload", files={"file": (p_v4.name, p_v4.read_bytes(), "video/mp4")})
    ev_id = res_upload.json()["id"]

    # Tamper with stored file
    stored_file = settings.EVIDENCE_DIR / f"{ev_id}.mp4"
    assert stored_file.exists()
    with open(stored_file, "r+b") as f:
        f.seek(50)
        f.write(b"CORRUPTED_BYTES_INJECTED")

    res_an = client.post(f"/api/v1/video/{ev_id}/analyze")
    assert res_an.status_code == 400
    assert "tampering detected" in res_an.json()["detail"].lower()
