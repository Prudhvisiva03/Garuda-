# EviSutra — Digital Evidence Authenticity & Integrity Verification Platform

> **Bihar Cyber Hackathon 2026** — Problem Statement PS-05  
> Operational Multi-Modal Digital Forensics & Court Admissibility Suite (Section 65B Indian Evidence Act / Section 63 BSA 2023)

---

## 🌟 Platform Capabilities

EviSutra is a zero-demo, fully operational digital forensics platform designed for Indian law enforcement, cyber crime cells, and forensic examiners. It features deterministic, mathematically explainable signal processing pipelines without black-box AI claims.

| Forensic Modality / Engine | Status | Implementation Details |
|---|---|---|
| **Multi-Modal Intake Desk** | ✅ **Operational** | Universal ingestion for Images (JPEG/PNG), Videos (MP4/MOV/AVI), and Audios (WAV/MP3). Enforces magic byte validation, decompression safety, and isolated vault storage. |
| **Cryptographic Sealing (SHA-256)** | ✅ **Operational** | Immediate intake digest computation, secondary disk write integrity verification, and on-demand tamper recheck. |
| **Image Forensics & SIFT Homography** | ✅ **Operational** | Scale-invariant feature transform (SIFT), Lowe's ratio test, and RANSAC planar homography for crop matching; Error Level Analysis (ELA); Laplacian noise residual analysis. |
| **Video Forensics & Temporal Splicing** | ✅ **Operational** | Bhattacharyya distance on normalized 3D color histograms with adaptive Z-score outlier detection; night theme / monochrome HSV analysis; CCTV duplicate/frozen frame detection. |
| **Audio Forensics & AI Voice Detection** | ✅ **Operational** | Short-Time Spectral Flux acoustic splice detection; noise floor RMS and digital silence ratio scanning for synthetic/deepfake speech biometrics; Mel-Spectrogram artifact generation. |
| **Law Enforcement Case Registry** | ✅ **Operational** | Full CRUD for FIR cases backed by SQLite; target case assignment at intake; interactive case drill-down modal showing all linked evidence items. |
| **Immutable Audit Trail (Section 65B)** | ✅ **Operational** | Automatic persistent logging for every intake, hash check, analysis run, case update, and report generation with timestamp, IP, and cryptographic digest. |
| **Court-Admissible PDF Reports** | ✅ **Operational** | SWGDE-compliant PDF reports generated via ReportLab embedding visual spectrograms, keyframes, and Section 65B legal certificates. |

---

## 🛠️ Technology Stack

- **Frontend:** React 18, TypeScript (Strict), Vite 5, Tailwind CSS, Lucide React
- **Backend:** Python 3.12, FastAPI, Pydantic v2, Uvicorn
- **Signal Processing & CV:** OpenCV (Headless), Pillow (PIL), NumPy, SciPy (Waveform/FFT)
- **Reporting:** ReportLab PDF Engine
- **Database:** SQLite3 with strict foreign key enforcement and persistent relational tables
- **Testing:** Pytest (60/60 tests passing), ESLint 9 (0 errors)

---

## 🚀 Quick Start Guide

### Prerequisites
- Node.js v18+ and npm v9+
- Python 3.10+ (Tested on Python 3.12)

### 1. Start the Backend Forensic Server
```bash
# Navigate to project root
cd Digital-Forensics

# Start FastAPI backend (runs on port 8000)
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```
Interactive Swagger API documentation: `http://localhost:8000/docs`.

### 2. Start the Frontend Application
```bash
# In another terminal:
cd Digital-Forensics

# Start Vite dev server (runs on port 5173, with proxy to backend)
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 🧪 Automated Test Suites (60 / 60 Tests Passing)

Run the full automated test suite:
```bash
# Run all backend forensic tests
python -m pytest backend/tests/ -v

# Run frontend quality checks
npm run lint         # ESLint 9 validation (0 errors, 0 warnings)
npm run build        # Production Vite bundle build (0 errors)
```

### Test Breakdown:
1. `backend/tests/test_forensics.py` (35 tests): Image upload, magic bytes, ELA, noise variance, SIFT homography, tamper detection.
2. `backend/tests/test_official_datasets.py` (10 tests): Official hackathon dataset pairs (Image Pairs 1–5, Mismatched extensions, Video metrics, Voice metrics, Data-2).
3. `backend/tests/test_video_forensics.py` (7 tests): Container atoms, temporal cut detection, night theme grading, video PDF report, tamper alert.
4. `backend/tests/test_audio_forensics.py` (7 tests): Audio magic bytes, natural voice vs AI voice detection, spectrogram generation, audio PDF report, tamper alert.
5. `backend/tests/test_audit_and_cases.py` (1 test): Case CRUD, evidence linking, and automatic Section 65B audit event generation.

---

## ⚖️ Forensic Admissibility Standards

1. **Deterministic & Explainable**: No opaque black-box AI scores; all metrics cite mathematical formulas (Bhattacharyya distance, Lowe ratio, spectral flux).
2. **Cryptographic Proof Scope**: SHA-256 verifies vault byte preservation against intake digest.
3. **Transparent Limitations**: Every finding report includes mandatory scientific caveats and method limitations.
4. **Legal Admissibility**: Outputs structured in compliance with Indian Evidence Act Section 65B / Bharatiya Sakshya Adhiniyam 2023 Section 63.
