"""
End-to-end validation of real camera photographs in EviSutra:
1. Reference: Real landscape photograph (1800x1200) with camera EXIF metadata.
2. Candidate: Separately cropped copy of that real photograph (1000x700).
3. Unrelated: Completely different real camera portrait photograph (1200x1800).
4. Verifies: Upload, Intake SHA-256, Analysis, Geometric Comparison, Visual Artifacts, and PDF Report.
"""

import hashlib
import io
import json
import sys
import urllib.request
from pathlib import Path

# Ensure Digital-Forensics project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.config import settings

def run_real_photo_validation():
    client = TestClient(app)
    fixtures_dir = Path("test_fixtures/real_photos")
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("STEP 1: Loading authentic real-world camera photographs...")
    ref_file = fixtures_dir / "real_landscape_reference.jpg"
    cand_file = fixtures_dir / "real_landscape_crop_candidate.jpg"
    unrelated_file = fixtures_dir / "real_portrait_unrelated.jpg"

    if ref_file.exists() and cand_file.exists() and unrelated_file.exists():
        landscape_bytes = ref_file.read_bytes()
        crop_bytes = cand_file.read_bytes()
        unrelated_bytes = unrelated_file.read_bytes()
        print(f"  [OK] Loaded existing Reference Photo from vault: {ref_file.name} ({len(landscape_bytes):,} bytes)")
        print(f"  [OK] Loaded existing Real Crop Candidate: {cand_file.name} ({len(crop_bytes):,} bytes)")
        print(f"  [OK] Loaded existing Unrelated Portrait: {unrelated_file.name} ({len(unrelated_bytes):,} bytes)")
    else:
        # Fetch authentic landscape reference image if missing
        req_ref = urllib.request.Request(
            "https://raw.githubusercontent.com/recurser/exif-orientation-examples/master/Landscape_1.jpg",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        landscape_bytes = urllib.request.urlopen(req_ref, timeout=15).read()
        ref_file.write_bytes(landscape_bytes)
        print(f"  [OK] Saved Reference Photo: {ref_file.name} ({len(landscape_bytes):,} bytes)")

        # Inspect image and create real crop
        ref_img = Image.open(io.BytesIO(landscape_bytes))
        cand_img = ref_img.crop((300, 200, 1300, 900))
        cand_buf = io.BytesIO()
        cand_img.save(cand_buf, format="JPEG", quality=90)
        crop_bytes = cand_buf.getvalue()
        cand_file.write_bytes(crop_bytes)
        print(f"  [OK] Created Real Crop: {cand_file.name} ({cand_img.size[0]}x{cand_img.size[1]} px, {len(crop_bytes):,} bytes)")

        # Fetch unrelated photo
        req_unrelated = urllib.request.Request(
            "https://raw.githubusercontent.com/recurser/exif-orientation-examples/master/Portrait_1.jpg",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        unrelated_bytes = urllib.request.urlopen(req_unrelated, timeout=15).read()
        unrelated_file.write_bytes(unrelated_bytes)
        print(f"  [OK] Saved Unrelated Photo: {unrelated_file.name} ({len(unrelated_bytes):,} bytes)")

    print("\n" + "=" * 70)
    print("STEP 2: Uploading genuine evidence specimens to EviSutra...")
    # Upload Reference
    res_up_ref = client.post(
        "/api/v1/evidence/upload",
        files={"file": (ref_file.name, landscape_bytes, "image/jpeg")},
        data={"case_id": "REAL-PHOTO-CASE-01"}
    )
    assert res_up_ref.status_code == 201, f"Failed reference upload: {res_up_ref.text}"
    ref_ev = res_up_ref.json()
    ref_id = ref_ev["id"]
    print(f"  [OK] Reference Ingested: ID={ref_id}")
    print(f"       Intake SHA-256: {ref_ev['sha256_intake']}")

    # Upload Crop Candidate
    res_up_cand = client.post(
        "/api/v1/evidence/upload",
        files={"file": (cand_file.name, crop_bytes, "image/jpeg")},
        data={"case_id": "REAL-PHOTO-CASE-01"}
    )
    assert res_up_cand.status_code == 201, f"Failed candidate upload: {res_up_cand.text}"
    cand_ev = res_up_cand.json()
    cand_id = cand_ev["id"]
    print(f"  [OK] Candidate Crop Ingested: ID={cand_id}")
    print(f"       Intake SHA-256: {cand_ev['sha256_intake']}")

    # Upload Unrelated Image
    res_up_unrelated = client.post(
        "/api/v1/evidence/upload",
        files={"file": (unrelated_file.name, unrelated_bytes, "image/jpeg")},
        data={"case_id": "REAL-PHOTO-CASE-01"}
    )
    assert res_up_unrelated.status_code == 201, f"Failed unrelated upload: {res_up_unrelated.text}"
    unrelated_ev = res_up_unrelated.json()
    unrelated_id = unrelated_ev["id"]
    print(f"  [OK] Unrelated Ingested: ID={unrelated_id}")
    print(f"       Intake SHA-256: {unrelated_ev['sha256_intake']}")

    print("\n" + "=" * 70)
    print("STEP 3: Running Single-Image Forensics (Intake Verification & ELA)...")
    res_analyze = client.post(f"/api/v1/analysis/{ref_id}/analyze")
    assert res_analyze.status_code == 200, f"Analysis failed: {res_analyze.text}"
    analysis_data = res_analyze.json()
    print(f"  [OK] Reference Analysis Completed.")
    print(f"       Integrity Verified: {analysis_data['integrity']['matches']} (SHA-256 matches disk)")
    print(f"       EXIF Tags Detected: {analysis_data['metadata']['has_exif']} ({len(analysis_data['metadata'].get('raw_tags', {}))} tags)")
    print(f"       ELA Status: {analysis_data['ela']['status']} (Mean Error: {analysis_data['ela']['mean_error']})")

    print("\n" + "=" * 70)
    print("STEP 4: Real-Image Geometric Comparison: Reference vs Cropped Photograph...")
    comp_res = client.post(
        "/api/v1/analysis/compare",
        json={"reference_id": ref_id, "candidate_id": cand_id, "algorithm": "SIFT", "ratio_threshold": 0.75}
    )
    assert comp_res.status_code == 200, f"Comparison failed: {comp_res.text}"
    comp_data = comp_res.json()
    print(f"  [OK] Comparison Status: {comp_data['status']}")
    print(f"       Raw Feature Matches: {comp_data['raw_matches']}")
    print(f"       RANSAC Inliers: {comp_data['inliers_count']}")
    print(f"       Inlier Ratio: {comp_data['inlier_ratio'] * 100:.1f}%")
    print(f"       Estimated Scale: {comp_data['estimated_scale']}x")
    print(f"       Overlap Bounding Box: {comp_data['overlap_box']}")
    print(f"       Artifact URL: {comp_data['artifact_url']}")
    assert comp_data["status"] == "possible_crop_match"
    assert comp_data["inliers_count"] >= 15
    assert comp_data["overlap_box"] is not None
    assert comp_data["artifact_url"] is not None

    # Check artifact file
    art_res = client.get(comp_data["artifact_url"])
    assert art_res.status_code == 200
    print(f"  [OK] Visual Match Artifact Generated: {len(art_res.content):,} bytes")

    print("\n" + "=" * 70)
    print("STEP 5: Real-Image Geometric Comparison: Reference vs Unrelated Photograph...")
    unrelated_comp = client.post(
        "/api/v1/analysis/compare",
        json={"reference_id": ref_id, "candidate_id": unrelated_id, "algorithm": "SIFT", "ratio_threshold": 0.75}
    ).json()
    print(f"  [OK] Unrelated Comparison Status: {unrelated_comp['status']}")
    print(f"       Raw Matches: {unrelated_comp['raw_matches']}, Inliers: {unrelated_comp['inliers_count']}, Inlier Ratio: {unrelated_comp['inlier_ratio']:.3f}")
    print(f"       Explanation: {unrelated_comp['explanation']}")
    assert unrelated_comp["status"] == "inconclusive"
    assert unrelated_comp["inliers_count"] == 15
    assert "inlier ratio 0.242 below threshold 0.25 (15/62 matches)" in unrelated_comp["explanation"]

    print("\n" + "=" * 70)
    print("STEP 6: Generating & Verifying Comprehensive Forensic PDF Report...")
    gen_res = client.post(f"/api/v1/reports/{ref_id}/generate")
    assert gen_res.status_code == 200
    gen_data = gen_res.json()
    print(f"  [OK] Report Generated: ID={gen_data['report_id']}")
    print(f"       Download URL: {gen_data['download_url']}")

    dl_res = client.get(f"/api/v1/reports/{ref_id}/download")
    assert dl_res.status_code == 200
    pdf_bytes = dl_res.content
    pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()
    print(f"  [OK] Report Downloaded: {len(pdf_bytes):,} bytes")
    print(f"       Report SHA-256: {pdf_hash}")
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 25000


    print("\n" + "=" * 70)
    print("SUCCESS: ALL REAL-PHOTOGRAPH FORENSIC VALIDATION CRITERIA SATISFIED!")
    print("=" * 70)

if __name__ == "__main__":
    run_real_photo_validation()
