"""Diagnostic: trace the classification decision tree for the unrelated portrait comparison."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import urllib.request
import io
import cv2
import numpy as np
from PIL import Image
from backend.app.services.image_comparator import _calculate_file_hash

fixtures_dir = Path("test_fixtures/real_photos")
fixtures_dir.mkdir(parents=True, exist_ok=True)

# Download if needed
ref_path = fixtures_dir / "real_landscape_reference.jpg"
unrelated_path = fixtures_dir / "real_portrait_unrelated.jpg"

if not ref_path.exists():
    req = urllib.request.Request(
        "https://raw.githubusercontent.com/recurser/exif-orientation-examples/master/Landscape_1.jpg",
        headers={"User-Agent": "Mozilla/5.0"})
    ref_path.write_bytes(urllib.request.urlopen(req, timeout=15).read())

if not unrelated_path.exists():
    req = urllib.request.Request(
        "https://raw.githubusercontent.com/recurser/exif-orientation-examples/master/Portrait_1.jpg",
        headers={"User-Agent": "Mozilla/5.0"})
    unrelated_path.write_bytes(urllib.request.urlopen(req, timeout=15).read())

# Run the exact same logic as image_comparator.py
ref_gray = cv2.imread(str(ref_path), cv2.IMREAD_GRAYSCALE)
cand_gray = cv2.imread(str(unrelated_path), cv2.IMREAD_GRAYSCALE)

h_ref, w_ref = ref_gray.shape
h_cand, w_cand = cand_gray.shape
print(f"Reference: {w_ref}x{h_ref} px")
print(f"Unrelated: {w_cand}x{h_cand} px")

ref_hash = _calculate_file_hash(ref_path)
cand_hash = _calculate_file_hash(unrelated_path)
print(f"SHA-256 match: {ref_hash == cand_hash}")

sift = cv2.SIFT_create(nfeatures=3000)
kp_ref, desc_ref = sift.detectAndCompute(ref_gray, None)
kp_cand, desc_cand = sift.detectAndCompute(cand_gray, None)
print(f"Keypoints: ref={len(kp_ref)}, cand={len(kp_cand)}")

bf = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)
raw_knn = bf.knnMatch(desc_cand, desc_ref, k=2)
good_matches = []
for m_group in raw_knn:
    if len(m_group) == 2:
        m, n = m_group
        if m.distance < 0.75 * n.distance:
            good_matches.append(m)
total_good = len(good_matches)
print(f"Lowe ratio matches: {total_good}")

src_pts = np.float32([kp_cand[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
dst_pts = np.float32([kp_ref[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)

matches_mask = mask.ravel().tolist()
inliers_count = int(np.sum(matches_mask))
inlier_ratio = round(float(inliers_count / (total_good + 1e-6)), 3)
print(f"RANSAC inliers: {inliers_count}")
print(f"Inlier ratio: {inlier_ratio}")

cand_corners = np.float32([[0, 0], [w_cand, 0], [w_cand, h_cand], [0, h_cand]]).reshape(-1, 1, 2)
proj_corners = cv2.perspectiveTransform(cand_corners, H)
proj_pts = proj_corners.reshape(-1, 2)

is_convex = cv2.isContourConvex(np.int32(proj_corners))
poly_area = float(cv2.contourArea(np.int32(proj_corners)))
ref_area = float(w_ref * h_ref)
area_ratio = poly_area / (ref_area + 1e-5)
cand_area = float(w_cand * h_cand)
scale_est = round(float(np.sqrt(poly_area / (cand_area + 1e-5))), 2)

is_same_dims = (w_ref == w_cand and h_ref == h_cand)

print(f"\n--- GEOMETRIC VALIDATION ---")
print(f"is_convex: {is_convex}")
print(f"poly_area: {poly_area:.1f}")
print(f"ref_area: {ref_area:.1f}")
print(f"area_ratio: {area_ratio:.4f}")
print(f"scale_est: {scale_est}")
print(f"is_same_dimensions: {is_same_dims}")
print(f"Projected polygon corners: {[[int(p[0]),int(p[1])] for p in proj_pts]}")

print(f"\n--- DECISION TREE TRACE ---")
print(f"1. exact_byte_duplicate? SHA-256 match = {ref_hash == cand_hash} -> NO")

cond_iv = (inliers_count >= 15 and inlier_ratio >= 0.25 and is_convex and (
    (is_same_dims and False) or
    (0.88 <= area_ratio <= 1.15 and scale_est is not None and 0.92 <= scale_est <= 1.08)
))
print(f"2. identical_visual_content?")
print(f"   inliers >= 15: {inliers_count >= 15}")
print(f"   inlier_ratio >= 0.25: {inlier_ratio >= 0.25}")
print(f"   is_convex: {is_convex}")
print(f"   area_ratio in [0.88, 1.15]: {0.88 <= area_ratio <= 1.15}")
print(f"   scale_est in [0.92, 1.08]: {scale_est is not None and 0.92 <= scale_est <= 1.08}")
print(f"   -> Result: {cond_iv}")

cond_crop = (inliers_count >= 15 and inlier_ratio >= 0.25 and is_convex and 0.02 <= area_ratio < 0.88)
print(f"3. possible_crop_match?")
print(f"   inliers >= 15: {inliers_count >= 15}")
print(f"   inlier_ratio >= 0.25: {inlier_ratio >= 0.25}")
print(f"   is_convex: {is_convex}")
print(f"   area_ratio in [0.02, 0.88): {0.02 <= area_ratio < 0.88}")
print(f"   -> Result: {cond_crop}")

print(f"4. inconclusive? inliers >= 6: {inliers_count >= 6}")

if not cond_iv and not cond_crop and inliers_count >= 6:
    # What specifically failed?
    print(f"\n--- ROOT CAUSE ---")
    if not (inliers_count >= 15):
        print(f"  Failed: inlier count {inliers_count} < 15")
    if not (inlier_ratio >= 0.25):
        print(f"  Failed: inlier ratio {inlier_ratio} < 0.25")
    if not is_convex:
        print(f"  Failed: projected polygon is NOT CONVEX")
    if not (0.02 <= area_ratio < 0.88):
        print(f"  Failed: area_ratio {area_ratio:.4f} not in [0.02, 0.88)")
    if not (0.88 <= area_ratio <= 1.15):
        print(f"  Also not in [0.88, 1.15] for identical_visual_content")
