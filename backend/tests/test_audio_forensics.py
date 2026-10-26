import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.config import settings

client = TestClient(app)

VOICE_DIR = Path("test_datasets/Voice data")


@pytest.fixture(scope="module")
def voice_dataset_available() -> bool:
    if not VOICE_DIR.exists():
        pytest.skip("Organizer Voice data dataset not available.")
    return True


def test_01_audio_upload_and_magic_byte_verification(voice_dataset_available):
    """Verifies audio intake, magic byte validation, and vault SHA-256 calculation."""
    # 1. Valid MP3 intake
    p_mp3 = VOICE_DIR / "AMIT voice 1.mp3"
    with open(p_mp3, "rb") as f:
        mp3_bytes = f.read()

    res_mp3 = client.post(
        "/api/v1/audio/upload",
        files={"file": (p_mp3.name, mp3_bytes, "audio/mpeg")},
    )
    assert res_mp3.status_code == 201
    mp3_data = res_mp3.json()
    assert mp3_data["id"].startswith("ev_aud_")
    assert mp3_data["mime_type"] == "audio/mpeg"
    assert len(mp3_data["sha256_intake"]) == 64

    # 2. Valid WAV intake
    p_wav = VOICE_DIR / "Cyber voice 6 .wav"
    with open(p_wav, "rb") as f:
        wav_bytes = f.read()

    res_wav = client.post(
        "/api/v1/audio/upload",
        files={"file": (p_wav.name, wav_bytes, "audio/wav")},
    )
    assert res_wav.status_code == 201
    wav_data = res_wav.json()
    assert wav_data["id"].startswith("ev_aud_")
    assert wav_data["mime_type"] == "audio/wav"

    # 3. Reject invalid text/fake audio
    res_fake = client.post(
        "/api/v1/audio/upload",
        files={"file": ("fake_audio.mp3", b"Not an audio file header at all", "audio/mpeg")},
    )
    assert res_fake.status_code == 415

    # 4. Reject empty 0-byte file
    res_empty = client.post(
        "/api/v1/audio/upload",
        files={"file": ("empty.mp3", b"", "audio/mpeg")},
    )
    assert res_empty.status_code == 400


def test_02_audio_forensics_analysis_on_cyber_voice_6_real(voice_dataset_available):
    """
    Organizer Clip 6 (Cyber voice 6 .wav): Ground-Truth Real Voice.
    Engine must verify:
    - Ambient room noise floor is continuous (RMS > 0.015).
    - Digital zero pauses are virtually 0% (0.0%).
    - Classification: natural_speech_consistent.
    """
    p_wav = VOICE_DIR / "Cyber voice 6 .wav"
    with open(p_wav, "rb") as f:
        wav_bytes = f.read()

    up_res = client.post(
        "/api/v1/audio/upload",
        files={"file": (p_wav.name, wav_bytes, "audio/wav")},
    ).json()
    ev_id = up_res["id"]

    an_res = client.post(f"/api/v1/audio/{ev_id}/analyze")
    assert an_res.status_code == 200
    data = an_res.json()

    assert data["classification"] == "natural_speech_consistent"
    props = data["audio_properties"]
    assert props["format"] == "PCM_S16LE" or props["format"] == "WAV"
    assert props["sample_rate_hz"] == 44100
    assert props["noise_floor_rms"] > 0.015

    synth = data["synthetic_indicators"]
    assert synth["synthetic_voice_detected"] is False
    assert synth["digital_silence_ratio_pct"] < 2.0


def test_03_audio_forensics_analysis_on_amit_voice_1_ai(voice_dataset_available):
    """
    Organizer Clip 1 (AMIT voice 1.mp3): Ground-Truth AI Generated Voice.
    Engine must detect:
    - Suppressed ambient noise floor (RMS < 0.001).
    - High digital silence ratio (> 10%).
    - Classification: ai_synthesized_voice_detected.
    """
    p_mp3 = VOICE_DIR / "AMIT voice 1.mp3"
    with open(p_mp3, "rb") as f:
        mp3_bytes = f.read()

    up_res = client.post(
        "/api/v1/audio/upload",
        files={"file": (p_mp3.name, mp3_bytes, "audio/mpeg")},
    ).json()
    ev_id = up_res["id"]

    an_res = client.post(f"/api/v1/audio/{ev_id}/analyze")
    assert an_res.status_code == 200
    data = an_res.json()

    assert data["classification"] == "ai_synthesized_voice_detected"
    synth = data["synthetic_indicators"]
    assert synth["synthetic_voice_detected"] is True
    assert synth["noise_floor_rms"] < 0.001
    assert synth["digital_silence_ratio_pct"] > 10.0
    assert len(data["suspicious_segments"]) > 0


def test_04_audio_forensics_analysis_on_other_ai_clips(voice_dataset_available):
    """Tests remaining organizer AI voice clips (Female Voice 2, Murder voice 4, etc.)."""
    for fname in ["Female Voice 2.mp3", "Murder voice 4.mp3"]:
        p = VOICE_DIR / fname
        with open(p, "rb") as f:
            b = f.read()

        up = client.post("/api/v1/audio/upload", files={"file": (p.name, b, "audio/mpeg")}).json()
        an = client.post(f"/api/v1/audio/{up['id']}/analyze").json()

        assert an["synthetic_indicators"]["synthetic_voice_detected"] is True
        assert an["audio_properties"]["noise_floor_rms"] < 0.005


def test_05_audio_spectrogram_artifact_generation(voice_dataset_available):
    """Verifies that waveform & spectrogram PNG artifact is generated and served correctly."""
    p_mp3 = VOICE_DIR / "Customercare voice 5.mp3"
    with open(p_mp3, "rb") as f:
        b = f.read()

    up = client.post("/api/v1/audio/upload", files={"file": (p_mp3.name, b, "audio/mpeg")}).json()
    an = client.post(f"/api/v1/audio/{up['id']}/analyze").json()

    art_name = an["spectrogram_artifact"]
    assert art_name is not None
    assert art_name.startswith("spec_")

    art_res = client.get(f"/api/v1/audio/artifact/{art_name}")
    assert art_res.status_code == 200
    assert art_res.headers["content-type"] == "image/png"
    assert len(art_res.content) > 10000


def test_06_audio_pdf_report_generation(voice_dataset_available):
    """Verifies generation of SWGDE-compliant PDF Forensic Audio Examination Report."""
    p_wav = VOICE_DIR / "Cyber voice 6 .wav"
    with open(p_wav, "rb") as f:
        b = f.read()

    up = client.post("/api/v1/audio/upload", files={"file": (p_wav.name, b, "audio/wav")}).json()
    client.post(f"/api/v1/audio/{up['id']}/analyze")

    rep_res = client.get(f"/api/v1/audio/{up['id']}/report")
    assert rep_res.status_code == 200
    assert rep_res.headers["content-type"] == "application/pdf"
    assert rep_res.content.startswith(b"%PDF-")


def test_07_tampered_audio_vault_detection(voice_dataset_available):
    """Verifies that unauthorized byte modification in the vault triggers a tamper alert."""
    p_mp3 = VOICE_DIR / "Apk voice 3.mp3"
    with open(p_mp3, "rb") as f:
        b = f.read()

    up = client.post("/api/v1/audio/upload", files={"file": (p_mp3.name, b, "audio/mpeg")}).json()
    ev_id = up["id"]

    # Tamper with 1 byte in the vault file
    stored_path = settings.EVIDENCE_DIR / f"{ev_id}.mp3"
    assert stored_path.exists()

    with open(stored_path, "r+b") as f:
        f.seek(500)
        curr = f.read(1)
        f.seek(500)
        f.write(bytes([curr[0] ^ 0xFF]))

    # Analyze must catch tampering
    an_res = client.post(f"/api/v1/audio/{ev_id}/analyze")
    assert an_res.status_code == 400
    assert "Evidence tampering detected" in an_res.json()["detail"]
