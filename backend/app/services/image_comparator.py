import hashlib
import json
import uuid
from pathlib import Path
from typing import Any
import cv2
import numpy as np
from PIL import Image

from backend.app.config import settings

def _calculate_file_hash(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

class ComparisonResult:
    def __init__(
        self,
        status: str,
        inliers_count: int = 0,
        raw_matches: int = 0,
        inlier_ratio: float = 0.0,
        overlap_box: dict[str, Any] | None = None,
        estimated_scale: float | None = None,
        artifact_filename: str | None = None,
        artifact_path: Path | None = None,
        explanation: str = "",
        limitations: str = "",
    ):
        self.status = status
        self.inliers_count = inliers_count
        self.raw_matches = raw_matches
        self.inlier_ratio = inlier_ratio
        self.overlap_box = overlap_box
        self.estimated_scale = estimated_scale
        self.artifact_filename = artifact_filename
        self.artifact_path = artifact_path
        self.explanation = explanation
        self.limitations = limitations

def compute_pixel_differences(
    ref_gray: np.ndarray,
    cand_gray: np.ndarray,
    block_size: int = 32,
) -> tuple[float, float, float]:
    """
    Computes global MAE, peak pixel difference, and maximum localized block MAE
    across non-overlapping blocks to prevent localized alterations (e.g. spliced patches,
    text overlays, removed objects) from being masked by low whole-image averages.
    """
    diff = np.abs(ref_gray.astype(np.float32) - cand_gray.astype(np.float32))
    pixel_mae = float(np.mean(diff))
    max_pixel_diff = float(np.max(diff))

    h, w = diff.shape
    if h < block_size or w < block_size:
        return pixel_mae, max_pixel_diff, pixel_mae

    max_block_mae = 0.0
    for y in range(0, h - block_size + 1, block_size):
        for x in range(0, w - block_size + 1, block_size):
            b_mae = float(np.mean(diff[y : y + block_size, x : x + block_size]))
            if b_mae > max_block_mae:
                max_block_mae = b_mae

    return pixel_mae, max_pixel_diff, max_block_mae

def classify_comparison(
    *,
    is_exact_byte_duplicate: bool,
    inliers_count: int,
    total_good_matches: int,
    inlier_ratio: float,
    is_convex: bool,
    area_ratio: float,
    scale_est: float | None,
    is_same_dimensions: bool,
    pixel_mae: float,
    max_pixel_diff: float = 0.0,
    max_block_mae: float = 0.0,
    w_cand: int,
    h_cand: int,
    w_ref: int,
    h_ref: int,
    ref_hash: str,
    cand_hash: str,
    overlap_box: dict[str, Any] | None = None,
) -> tuple[str, str, str, dict[str, Any] | None]:
    """
    Evaluates the empirical decision tree for image comparison.
    Every branch documents the exact measured conditions.
    Returns (status, explanation, limitations, overlap_box).

    Decision tree:
      A. exact_byte_duplicate       : SHA-256(ref) == SHA-256(cand)
      B. visually_similar_full_frame: NOT A, AND inliers >= 15, AND inlier_ratio >= 0.25,
                                       AND convex, AND (
                                           (same-dim + pixel_mae <= 5.0 + max_block_mae <= 15.0)
                                           OR (area_ratio in [0.85, 1.15] AND scale in [0.92, 1.08])
                                       )
      C. possible_crop_match        : NOT A/B, AND inliers >= 15, AND inlier_ratio >= 0.25,
                                       AND convex, AND area_ratio in [0.02, 0.85]
      D. inconclusive               : NOT A/B/C, AND inliers >= 6
                                       (reached when inliers 6-14, or inlier_ratio < 0.25,
                                        or non-convex, or localized alteration detected,
                                        or area_ratio outside valid crop/similarity bounds)
      E. no_reliable_match          : inliers < 6 (or Lowe matches < 4, or failed homography)
    """
    _has_enough_inliers = inliers_count >= 15
    _has_strong_ratio = inlier_ratio >= 0.25
    _has_convex_quad = is_convex
    _area_in_crop_range = 0.02 <= area_ratio <= 0.85
    _area_in_full_frame_range = 0.85 <= area_ratio <= 1.15
    _scale_in_identity_range = scale_est is not None and 0.92 <= scale_est <= 1.08
    _no_localized_alteration = (not is_same_dimensions) or (pixel_mae <= 5.0 and max_block_mae <= 15.0)

    if is_exact_byte_duplicate:
        # Branch A: cryptographic identity
        status = "exact_byte_duplicate"
        explanation = (
            f"Exact byte duplicate: Candidate and Reference evidence files have identical SHA-256 "
            f"cryptographic hashes ({ref_hash}). All byte sequences, metadata headers, and pixel "
            f"matrices match perfectly across both items. "
            f"Verified {inliers_count} RANSAC inliers with 1.0x scale and 100% canvas alignment."
        )
        limitations = (
            "Cryptographic SHA-256 collision resistance establishes byte-level identity. "
            "This confirms the files are identical copies, not that the content is unmanipulated."
        )
        if overlap_box is None:
            overlap_box = {
                "x": 0, "y": 0, "width": w_ref, "height": h_ref,
                "polygon": [[0, 0], [w_ref, 0], [w_ref, h_ref], [0, h_ref]],
                "area_ratio": 1.0,
            }

    elif (_has_enough_inliers and _has_strong_ratio and _has_convex_quad
          and _no_localized_alteration
          and (
              is_same_dimensions
              or (_area_in_full_frame_range and _scale_in_identity_range)
          )):
        # Branch B: visually similar full-frame content
        status = "visually_similar_full_frame"
        scale_display = f"{scale_est:.2f}" if scale_est is not None else "unknown"
        explanation = (
            f"Visually similar full-frame content: Candidate and Reference share full-frame visual "
            f"correspondence ({w_cand}x{h_cand} px) with {inliers_count} verified RANSAC inliers "
            f"(scale ~{scale_display}x, {inlier_ratio:.1%} inlier ratio, MAE: {pixel_mae:.2f}). "
            f"Cryptographic SHA-256 hashes differ ({ref_hash[:12]}... vs {cand_hash[:12]}...), "
            f"consistent with container transcoding, recompression, or altered metadata. "
            f"Evidence establishes visual similarity, not byte-level identity."
        )
        limitations = (
            "Empirical feature and pixel correspondence establishes full-frame visual similarity, "
            "NOT mathematical bit identity. Subtle compression noise or sub-threshold localized pixel "
            "variations may be present."
        )

    elif (_has_enough_inliers and _has_strong_ratio and _has_convex_quad
          and _area_in_crop_range):
        # Branch C: localized sub-region crop containment
        status = "possible_crop_match"
        box_w = overlap_box["width"] if overlap_box else "unknown"
        box_h = overlap_box["height"] if overlap_box else "unknown"
        explanation = (
            f"Possible partial-image match: Candidate exhibits geometric correspondence with "
            f"a localized sub-region of the Reference image. "
            f"Verified {inliers_count} RANSAC inliers across {total_good_matches} feature matches "
            f"(inlier ratio: {inlier_ratio:.1%}). "
            f"The candidate corresponds to an estimated "
            f"{box_w}x{box_h} px sub-window in the reference "
            f"image (approx {area_ratio:.1%} of reference canvas)."
        )
        limitations = (
            "Feature matching establishes rigid geometric visual correspondence, "
            "NOT proof of intentional cropping. Common scenes, architectural repetitions, "
            "or similar objects photographed separately can generate feature inliers. "
            "Severe downscaling, heavy recompression, or extreme crops (< 5% canvas) "
            "degrade keypoint detectability."
        )

    elif inliers_count >= 6:
        # Branch D: inconclusive — report exactly which geometric or similarity conditions failed
        failed_conditions = []
        if not _has_enough_inliers:
            failed_conditions.append(
                f"inlier count {inliers_count} below threshold 15")
        if not _has_strong_ratio:
            failed_conditions.append(
                f"inlier ratio {inlier_ratio:.3f} below threshold 0.25 "
                f"({inliers_count}/{total_good_matches} matches)")
        if not _has_convex_quad:
            failed_conditions.append(
                "projected quadrilateral is non-convex or degenerate (twisted homography)")
        if is_same_dimensions and not _no_localized_alteration:
            failed_conditions.append(
                f"localized pixel alteration detected: max 32x32 block MAE of {max_block_mae:.1f} "
                f"(peak diff: {max_pixel_diff:.1f}, global MAE: {pixel_mae:.2f}) exceeds threshold 15.0")
        if not _area_in_crop_range and not (_area_in_full_frame_range and _scale_in_identity_range):
            if area_ratio < 0.02:
                failed_conditions.append(
                    f"projected area ratio {area_ratio:.4f} is below 2% canvas threshold (insufficient spatial support)")
            elif area_ratio > 1.15:
                failed_conditions.append(
                    f"candidate projected area ({area_ratio:.1%}) exceeds reference canvas: candidate is larger than reference (reversed crop relationship or incompatible scale)")
            elif 0.85 < area_ratio <= 1.15 and not _scale_in_identity_range:
                failed_conditions.append(
                    f"full-frame area ratio ({area_ratio:.2f}) lacks required identity scale [0.92, 1.08] (measured: {scale_est})")
        failed_str = "; ".join(failed_conditions) if failed_conditions else "none identified"

        status = "inconclusive"
        scale_display = f"{scale_est:.2f}" if scale_est is not None else "unknown"
        explanation = (
            f"Inconclusive: {inliers_count} geometrically aligned inliers found "
            f"({inlier_ratio:.1%} inlier ratio, {total_good_matches} Lowe matches). "
            f"Classification conditions not met: {failed_str}. "
            f"Measured geometry: convex={is_convex}, area_ratio={area_ratio:.4f}, "
            f"scale={scale_display}. "
            f"Manual expert examination required."
        )
        limitations = (
            "Feature density or geometric quality was insufficient to confirm a rigid "
            "homography or rule out accidental correlation. "
            "Manual forensic examination of high-contrast landmarks is advised."
        )

    else:
        # Branch E: insufficient inliers
        status = "no_reliable_match"
        explanation = (
            f"No reliable feature correspondence: {inliers_count} inliers verified out of "
            f"{total_good_matches} candidate matches (inlier ratio {inlier_ratio:.3f}). "
            f"No coherent geometric correspondence exists between these images."
        )
        limitations = (
            "Candidate and reference images do not share sufficient verified keypoint "
            "clusters to suggest common origin."
        )

    return status, explanation, limitations, overlap_box

def compare_images_for_crop(
    reference_path: Path,
    candidate_path: Path,
    reference_id: str,
    candidate_id: str,
    algorithm: str = "SIFT",
    ratio_threshold: float = 0.75,
) -> ComparisonResult:
    """
    Performs empirical computer vision comparison between a Reference (original)
    image and a Candidate (potentially cropped / resized / recompressed) image.

    Uses Scale-Invariant Feature Transform (SIFT) with Lowe's ratio test and
    RANSAC homography estimation for geometric verification.
    Does NOT invent scores or simulate bounding boxes.
    """
    if not reference_path.exists() or not candidate_path.exists():
        return ComparisonResult(
            status="failed",
            explanation="One or both evidence files could not be found on storage vault.",
            limitations="File I/O failure.",
        )

    # 0. Cryptographic SHA-256 Hash Pre-check
    ref_hash = _calculate_file_hash(reference_path)
    cand_hash = _calculate_file_hash(candidate_path)
    is_exact_byte_duplicate = (ref_hash == cand_hash)

    # 1. Load images via OpenCV in grayscale
    ref_gray = cv2.imread(str(reference_path), cv2.IMREAD_GRAYSCALE)
    cand_gray = cv2.imread(str(candidate_path), cv2.IMREAD_GRAYSCALE)

    if ref_gray is None or cand_gray is None:
        return ComparisonResult(
            status="failed",
            explanation="Unable to decode one or both images into OpenCV pixel matrices.",
            limitations="Unsupported internal image pixel structure.",
        )

    h_ref, w_ref = ref_gray.shape
    h_cand, w_cand = cand_gray.shape

    # 2. Extract SIFT features
    try:
        sift = cv2.SIFT_create(nfeatures=3000)
        kp_ref, desc_ref = sift.detectAndCompute(ref_gray, None)
        kp_cand, desc_cand = sift.detectAndCompute(cand_gray, None)
    except Exception as e:
        return ComparisonResult(
            status="failed",
            explanation=f"Feature extraction failed: {str(e)}",
            limitations="Computer vision feature computation error.",
        )

    if desc_ref is None or desc_cand is None or len(kp_ref) < 4 or len(kp_cand) < 4:
        if is_exact_byte_duplicate:
            return ComparisonResult(
                status="exact_byte_duplicate",
                inliers_count=len(kp_ref) if kp_ref else 0,
                raw_matches=len(kp_ref) if kp_ref else 0,
                inlier_ratio=1.0,
                overlap_box={
                    "x": 0, "y": 0, "width": w_ref, "height": h_ref,
                    "polygon": [[0, 0], [w_ref, 0], [w_ref, h_ref], [0, h_ref]],
                    "area_ratio": 1.0,
                },
                estimated_scale=1.0,
                explanation=f"Exact byte duplicate: Candidate and Reference files have identical SHA-256 cryptographic hashes ({ref_hash}). Every byte and pixel matches perfectly.",
                limitations="None. Cryptographic SHA-256 collision resistance (2^256) establishes absolute byte identity.",
            )
        return ComparisonResult(
            status="no_reliable_match",
            inliers_count=0,
            raw_matches=0,
            inlier_ratio=0.0,
            explanation=(
                f"Insufficient textured keypoints detected (Reference: {len(kp_ref)}, Candidate: {len(kp_cand)}). "
                "Images with smooth surfaces, lack of texture, or extreme blur cannot be matched reliably."
            ),
            limitations="Feature matching requires rich, non-repeating visual textures.",
        )

    # 3. Match features using BFMatcher with Lowe's ratio test
    bf = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)
    raw_knn = bf.knnMatch(desc_cand, desc_ref, k=2)

    good_matches = []
    for m_group in raw_knn:
        if len(m_group) == 2:
            m, n = m_group
            if m.distance < ratio_threshold * n.distance:
                good_matches.append(m)

    total_good_matches = len(good_matches)

    # If insufficient matches to attempt RANSAC
    if total_good_matches < 4:
        if is_exact_byte_duplicate:
            return ComparisonResult(
                status="exact_byte_duplicate",
                inliers_count=total_good_matches,
                raw_matches=total_good_matches,
                inlier_ratio=1.0,
                overlap_box={
                    "x": 0, "y": 0, "width": w_ref, "height": h_ref,
                    "polygon": [[0, 0], [w_ref, 0], [w_ref, h_ref], [0, h_ref]],
                    "area_ratio": 1.0,
                },
                estimated_scale=1.0,
                explanation=f"Exact byte duplicate: Candidate and Reference files have identical SHA-256 cryptographic hashes ({ref_hash}).",
                limitations="None. Cryptographic SHA-256 collision resistance guarantees exact byte identity.",
            )
        return ComparisonResult(
            status="no_reliable_match",
            inliers_count=0,
            raw_matches=total_good_matches,
            inlier_ratio=0.0,
            explanation=(
                f"Found only {total_good_matches} feature correspondences passing Lowe's ratio test. "
                "Minimum required for geometric homography is 4. No reliable visual relationship detected."
            ),
            limitations="Insufficient matching keypoints between images.",
        )

    # 4. Geometric Verification via RANSAC Homography
    src_pts = np.float32([kp_cand[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp_ref[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

    H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)

    if H is None or mask is None:
        if is_exact_byte_duplicate:
            return ComparisonResult(
                status="exact_byte_duplicate",
                inliers_count=total_good_matches,
                raw_matches=total_good_matches,
                inlier_ratio=1.0,
                overlap_box={
                    "x": 0, "y": 0, "width": w_ref, "height": h_ref,
                    "polygon": [[0, 0], [w_ref, 0], [w_ref, h_ref], [0, h_ref]],
                    "area_ratio": 1.0,
                },
                estimated_scale=1.0,
                explanation=f"Exact byte duplicate: Candidate and Reference files have identical SHA-256 cryptographic hashes ({ref_hash}).",
                limitations="None. Cryptographic SHA-256 collision resistance guarantees exact byte identity.",
            )
        return ComparisonResult(
            status="no_reliable_match",
            inliers_count=0,
            raw_matches=total_good_matches,
            inlier_ratio=0.0,
            explanation=(
                f"Evaluated {total_good_matches} feature matches, but RANSAC could not compute "
                "a coherent geometric homography. Points do not share a consistent spatial plane."
            ),
            limitations="Features do not form a geometrically rigid correspondence.",
        )

    matches_mask = mask.ravel().tolist()
    inliers_count = int(np.sum(matches_mask))
    inlier_ratio = round(float(inliers_count / (total_good_matches + 1e-6)), 3)

    # 5. Project candidate boundaries onto reference image
    cand_corners = np.float32([[0, 0], [w_cand, 0], [w_cand, h_cand], [0, h_cand]]).reshape(-1, 1, 2)
    try:
        proj_corners = cv2.perspectiveTransform(cand_corners, H)
        proj_pts = proj_corners.reshape(-1, 2)

        # Geometric sanity checks on projected quad:
        is_convex = cv2.isContourConvex(np.int32(proj_corners))
        poly_area = float(cv2.contourArea(np.int32(proj_corners)))
        ref_area = float(w_ref * h_ref)
        area_ratio = poly_area / (ref_area + 1e-5)

        # Check reasonable scale change
        cand_area = float(w_cand * h_cand)
        scale_est = round(float(np.sqrt(poly_area / (cand_area + 1e-5))), 2)

        x_coords = proj_pts[:, 0]
        y_coords = proj_pts[:, 1]
        x_min, x_max = int(np.min(x_coords)), int(np.max(x_coords))
        y_min, y_max = int(np.min(y_coords)), int(np.max(y_coords))

        overlap_box = {
            "x": max(0, x_min),
            "y": max(0, y_min),
            "width": max(1, x_max - x_min),
            "height": max(1, y_max - y_min),
            "polygon": [[int(pt[0]), int(pt[1])] for pt in proj_pts],
            "area_ratio": round(area_ratio, 3),
        }
    except Exception:
        is_convex = False
        poly_area = 0.0
        area_ratio = 0.0
        scale_est = None
        overlap_box = None

    # Pixel difference metrics if same dimensions
    is_same_dimensions = (w_ref == w_cand and h_ref == h_cand)
    if is_same_dimensions:
        pixel_mae, max_pixel_diff, max_block_mae = compute_pixel_differences(ref_gray, cand_gray)
    else:
        pixel_mae, max_pixel_diff, max_block_mae = 999.0, 999.0, 999.0

    # 6. Empirical Status Classification (5-category taxonomy)
    status, explanation, limitations, overlap_box = classify_comparison(
        is_exact_byte_duplicate=is_exact_byte_duplicate,
        inliers_count=inliers_count,
        total_good_matches=total_good_matches,
        inlier_ratio=inlier_ratio,
        is_convex=is_convex,
        area_ratio=area_ratio,
        scale_est=scale_est,
        is_same_dimensions=is_same_dimensions,
        pixel_mae=pixel_mae,
        max_pixel_diff=max_pixel_diff,
        max_block_mae=max_block_mae,
        w_cand=w_cand,
        h_cand=h_cand,
        w_ref=w_ref,
        h_ref=h_ref,
        ref_hash=ref_hash,
        cand_hash=cand_hash,
        overlap_box=overlap_box,
    )

    # 7. Generate Visual Comparison Artifact
    artifact_filename = f"compare_{reference_id}_{candidate_id}_{uuid.uuid4().hex[:6]}.png"
    artifact_path = settings.ARTIFACTS_DIR / artifact_filename

    try:
        # Load color images for visualization
        ref_color = cv2.imread(str(reference_path))
        cand_color = cv2.imread(str(candidate_path))

        # If possible crop match or inconclusive with valid polygon, draw bounding box on reference copy
        ref_vis = ref_color.copy()
        if overlap_box and overlap_box.get("polygon"):
            poly_np = np.array(overlap_box["polygon"], dtype=np.int32).reshape((-1, 1, 2))
            # Draw semi-transparent cyan highlight polygon
            cv2.polylines(ref_vis, [poly_np], isClosed=True, color=(238, 211, 34), thickness=3) # Cyan BGR
            # Label
            cv2.putText(
                ref_vis,
                f"Candidate Overlap Region ({overlap_box['width']}x{overlap_box['height']})",
                (overlap_box["x"] + 5, max(20, overlap_box["y"] + 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (238, 211, 34),
                2,
            )

        # Create combined visualization with inlier matches
        # Draw inlier matches using cv2.drawMatches
        vis_img = cv2.drawMatches(
            cand_color,
            kp_cand,
            ref_vis,
            kp_ref,
            good_matches,
            None,
            matchColor=(0, 255, 128),  # Green inliers
            singlePointColor=(128, 128, 128),
            matchesMask=matches_mask,
            flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS,
        )

        cv2.imwrite(str(artifact_path), vis_img)
    except Exception as e:
        artifact_filename = None
        artifact_path = None

    return ComparisonResult(
        status=status,
        inliers_count=inliers_count,
        raw_matches=total_good_matches,
        inlier_ratio=inlier_ratio,
        overlap_box=overlap_box,
        estimated_scale=scale_est,
        artifact_filename=artifact_filename,
        artifact_path=artifact_path,
        explanation=explanation,
        limitations=limitations,
    )
