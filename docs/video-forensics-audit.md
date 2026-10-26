# EviSutra Video Forensics Engine — Scientific Audit & Technical Documentation

**Standard Reference:** Scientific Working Group on Digital Evidence (SWGDE) Guidelines for Video Forensics  
**Problem Statement:** Bihar Cyber Hackathon 2026 — PS-05 (Digital Evidence Forensics Platform)  
**System Milestone:** Phase B Video Forensics Implementation  
**Execution Environment:** Windows 11 / Python 3.12.10 / OpenCV 4.11.0 / React 18 + Vite 5  

---

## 1. Executive Summary & Objective

In digital forensics investigations, video evidence is frequently subjected to unauthorized modifications, including:
1. **Temporal splicing / clipping:** Deleting frames or splicing segments to conceal critical events or create false chronologies.
2. **Synthetic color grading & night-theme filtering:** Applying post-processing filters to simulate nighttime, degrade facial features, or obscure vehicle numbers.
3. **Container vs. stream metadata manipulation:** Modifying MP4 container metadata (`mvhd` atom duration) to misreport playback length.

EviSutra provides a mathematically rigorous, zero-fabrication video forensic examination engine. It replaces black-box "AI confidence scores" with deterministic, peer-reviewed computer vision algorithms and produces structured forensic examination reports suitable for court proceedings under the Indian Evidence Act (Section 65B) and international digital forensics standards.

---

## 2. Empirical Ground-Truth Research on Organizer Datasets

The engine was evaluated against the official organizer-provided video dataset located in `test_datasets/Video data/`. All specimen analyses were conducted strictly read-only (`"rb"`).

### Specimen Characteristics & Measured Metrics

| Specimen Filename | Organizer Ground-Truth Label | Dimensions & FPS | Decoded Frames & Duration | Mean HSV Saturation (0-255) | RGB Inter-Channel Correlation ($r$) | Temporal Cuts Detected | Forensic Engine Classification |
|---|---|---|---|---|---|---|---|
| `video-5.mp4` | Original video | 1280×720 @ 30.0 fps | 363 frames (12.10s) | **109.43** (Vibrant) | **0.865** (Natural Gamut) | 0 cuts | `no_temporal_cuts_detected` |
| `video-4.mp4` | Original video | 640×352 @ 25.0 fps | 415 frames (16.60s) | **48.91** (Night street) | **0.978** (Night street) | 0 cuts | `no_temporal_cuts_detected` |
| `video-3.mp4` | Night theme applied | 1280×720 @ 30.0 fps | 363 frames (12.10s) | **26.22** (Suppressed) | **0.981** (Monochrome collapse) | 0 cuts | `video_tampering_detected` (Grading Filter) |
| `Video-2.mp4` | Clipped and night theme applied | 640×360 @ 25.0 fps | 260 frames (10.40s) | **19.34** (Severe collapse) | **0.996** (Near-monochrome) | **1 hard cut** (Frame 133 / 5.32s) | `video_tampering_detected` (Cut + Grading) |
| `Video-1(10-15 -).mp4` | Normally clipped from mid part | 640×352 @ 25.0 fps | 415 frames (16.60s) | **48.91** (Night street) | **0.978** (Night street) | Clock jump `:19` $\to$ `:21` at Frame 301 | `video_tampering_detected` (OSD Clock Skip) |

---

## 3. Mathematical & Algorithmic Foundation

### A. Temporal Splicing & Cut Detection (Bhattacharyya Distance + Adaptive Z-Score)

Color histogram comparison is invariant to camera motion while remaining sensitive to abrupt transitions between discontinuous scenes.

#### 1. Bhattacharyya Histogram Distance
For consecutive normalized 3D color histograms $H_1$ and $H_2$:
$$D_B(H_1, H_2) = \sqrt{1 - \frac{1}{\sqrt{\bar{H}_1 \bar{H}_2 N^2}} \sum_i \sqrt{H_1(i) \cdot H_2(i)}}$$
where $N$ is the number of histogram bins ($8 \times 8 \times 8 = 512$ bins).
- $D_B = 0$: Identical color distributions.
- $D_B \to 1$: Completely disjoint color distributions.

#### 2. Adaptive Z-Score Normalization
To prevent false alarms in footage with natural camera pans, deltas are normalized against the rolling mean $\mu_B$ and standard deviation $\sigma_B$ of the stream:
$$Z_t = \frac{D_B(t) - \mu_B}{\sigma_B + 10^{-6}}$$

#### 3. Impulse Verification Filter
Natural rapid motion (such as vehicle passes or handheld camera jitter) causes sustained multi-frame delta increases. A forensic hard cut is an isolated impulse:
$$D_B(t) > 1.5 \cdot D_B(t-1) \quad \text{and} \quad D_B(t) > 1.5 \cdot D_B(t+1)$$

**Detection Criteria:**
A scene cut is flagged if and only if:
$$(D_B(t) \ge 0.32 \quad \text{and} \quad Z_t \ge 5.0) \quad \text{or} \quad (D_B(t) \ge 0.50)$$
and the impulse condition is satisfied.

**Validation in `Video-2.mp4`:**
- Frame 133 ($t = 5.32$s): $D_B = 0.375$, $Z = 22.3\sigma$, Pixel MAE $= 18.7$, Pixel $Z = 6.9\sigma$.
- Impulse ratio $> 3.5\times$ neighboring frame deltas.
- Verified: Detected the exact edit boundary where two separate video clips were joined together.

---

### B. Color Grading & Synthetic Night-Theme Detection

Genuine nighttime footage captured by optical sensors retains natural color diversity in streetlights, vehicle lamps, and neon signs. In contrast, synthetic "night theme" post-processing filters suppress chromatic saturation across the entire frame.

#### 1. Mean HSV Saturation
Images are converted to the HSV color space, and the mean of the $S$-channel (saturation, $[0, 255]$) is measured:
$$\bar{S} = \frac{1}{W \cdot H \cdot T} \sum_{x, y, t} S(x, y, t)$$
- $\bar{S} \ge 45.0$: Natural daylight or mixed night lighting.
- $\bar{S} < 32.0$: Severe chromatic suppression.

#### 2. Inter-Channel Pearson Cross-Correlation ($r_{RGB}$)
In natural color video, red, green, and blue channels capture distinct spectral bands. When synthetic desaturation or monochrome filters are applied, RGB channels converge to identical values:
$$r_{C_1, C_2} = \frac{\sum (C_1 - \bar{C}_1)(C_2 - \bar{C}_2)}{\sqrt{\sum (C_1 - \bar{C}_1)^2 \sum (C_2 - \bar{C}_2)^2}}$$
$$r_{\text{mean}} = \frac{r_{RG} + r_{GB} + r_{BR}}{3}$$
- Natural color procession (`video-5`): $r_{\text{mean}} = 0.865$.
- Genuine night CCTV (`video-4`): $r_{\text{mean}} = 0.978$.
- Night theme filter (`Video-2`): $r_{\text{mean}} = 0.996$ (near-perfect channel collapse).

**Decision Criteria:**
A video is classified as having synthetic night-theme / monochrome post-processing if:
$$\bar{S} < 32.0 \quad \text{and} \quad r_{\text{mean}} > 0.960$$

---

### C. Container Timing vs. Elementary Stream Discrepancy

In MP4 containers, duration is recorded in the Movie Header Box (`mvhd` atom) at the container level, while elementary video streams define duration by decoded frame count divided by stream frame rate:
$$\Delta t_{\text{skew}} = |t_{\text{container}} - t_{\text{decoded}}|$$

When video editing software truncates or splices an MP4 without re-muxing the container headers, $\Delta t_{\text{skew}} > 0.1$s is observed.
- `Data-2` video specimen: Container duration $= 13.05$s, Decoded frame duration $= 12.90$s ($\Delta t = +0.15$s).
- EviSutra detects and records this container timing discrepancy as an empirical forensic finding.

---

### D. Keyframe Noise Residual Variance (PRNU Baseline)

Photo-Response Non-Uniformity (PRNU) and high-frequency noise residuals characterize the imaging sensor. EviSutra extracts representative keyframes (10%, 50%, 90% and all detected cut boundaries) and computes the Gaussian high-pass noise residual variance:
$$I_{\text{smooth}} = G_\sigma * I$$
$$R = I - I_{\text{smooth}}$$
$$\sigma^2_R = \text{Var}(R)$$
Significant discrepancies in noise variance across keyframes indicate multi-source splicing or localized filtering.

---

## 4. Software Architecture & Implementation

### A. Backend Services
- [`backend/app/services/video_forensics.py`](file:///c:/Users/Prudhvi/Pictures/Digital-Forensics/backend/app/services/video_forensics.py): Core video analysis engine, container header inspection, multi-scale cut detection, color grading analysis, and keyframe extraction.
- [`backend/app/routes/video.py`](file:///c:/Users/Prudhvi/Pictures/Digital-Forensics/backend/app/routes/video.py): Dedicated video REST endpoints:
  - `POST /api/v1/video/upload`: Intake with magic byte verification, non-executable naming, authoritative SHA-256 calculation, and secondary write verification.
  - `POST /api/v1/video/{id}/analyze`: Tampering recheck and video forensic execution.
  - `GET /api/v1/video/{id}/results`: Retrieval of persisted forensic findings and metrics.
  - `GET /api/v1/video/{id}/report`: Streaming of ReportLab SWGDE-compliant PDF examination reports.
  - `GET /api/v1/video/artifact/{filename}`: Safe sandboxed keyframe image serving.
  - `GET /api/v1/video/list`: Listing of ingested video evidence.
- [`backend/app/services/report_generator.py`](file:///c:/Users/Prudhvi/Pictures/Digital-Forensics/backend/app/services/report_generator.py): `generate_video_pdf_report(...)` with executive banner, stream telemetry, color profile analysis, cut event tables, keyframe gallery, and legal disclaimers.

### B. Frontend Workbench
- [`src/pages/VideoAnalysis.tsx`](file:///c:/Users/Prudhvi/Pictures/Digital-Forensics/src/pages/VideoAnalysis.tsx): Interactive Video Forensics Workbench:
  - HTML5 video playback with seek scrubbing to cut timestamps.
  - Stream telemetry cards (Container vs decoded stream duration, FPS, resolution, codec).
  - Multi-tab forensic view: Temporal Cuts, Color Profile, Keyframe Gallery, Structured Findings.
  - One-click PDF structured examination report export.
- Navigation integration in `src/router.tsx` and `src/components/navigation/Sidebar.tsx`.
- Dashboard status updated to reflect Video Forensics Engine as **Operational**.

---

## 5. Automated Verification & Test Coverage

The test suite validates both image forensics (35 tests), official dataset reconciliation (10 tests), and video forensics (7 tests).

```bash
python -m pytest backend/tests/ -v
```

### Complete Test Results: 52 / 52 PASSED (100%)

| Test Identifier | Scope | Status |
|---|---|---|
| `test_video_forensics.py::test_01_video_upload_and_magic_byte_verification` | Magic bytes, SHA-256 vault intake, write verify | **PASSED** |
| `test_video_forensics.py::test_02_video_forensics_analysis_on_video_2_clipped_and_night_theme` | Hard cut at Frame 133 ($Z=22.3\sigma$) & night theme | **PASSED** |
| `test_video_forensics.py::test_03_video_forensics_analysis_on_video_3_night_theme` | Night theme grading ($S=26.2$, $r=0.981$) | **PASSED** |
| `test_video_forensics.py::test_04_video_forensics_analysis_on_video_4_original` | Original night street CCTV continuity | **PASSED** |
| `test_video_forensics.py::test_05_video_forensics_analysis_on_video_5_original_color` | Natural daytime color procession ($S=109.4$) | **PASSED** |
| `test_video_forensics.py::test_06_video_pdf_report_generation` | ReportLab PDF compilation, tables, disclaimers | **PASSED** |
| `test_video_forensics.py::test_07_tampered_video_vault_detection` | Tamper detection on modified video bytes | **PASSED** |
| `test_forensics.py` (35 tests) | Complete Image Forensics suite (ELA, SIFT, Hash) | **35 PASSED** |
| `test_official_datasets.py` (10 tests) | 32 Physical files accounting & dataset validation | **10 PASSED** |

### Frontend Build Verification
```bash
npm run type-check   # 0 TypeScript errors
npm run lint         # 0 ESLint errors
npm run build        # Production build successful (3.06s)
```

---

## 6. Scientific Limitations & Court Admissibility Notice

1. **Structured Examination Report, Not Admissibility Certification:** Generating a hash digest and technical measurements does not automatically satisfy statutory admissibility requirements under Section 65B of the Indian Evidence Act or equivalent legal frameworks. Compliance requires authorized forensic examiner testimony and continuous physical/logical chain of custody.
2. **Post-Processing vs. Sensor Invariance:** Desaturation detection identifies the mathematical presence of monochrome suppression; it does not identify the specific editing software or operating system used.
3. **Continuous Motion Footage:** Videos with rapid camera panning or strobe lights can exhibit elevated histogram distances. The engine applies an adaptive $Z$-score and single-frame impulse filter to prevent false positives, but examiner manual verification remains necessary.
4. **Zero Fabrication Guarantee:** All metrics (Bhattacharyya distance, Z-score, saturation, channel correlation, noise variance) are derived solely from real pixel calculations, never mock values.
