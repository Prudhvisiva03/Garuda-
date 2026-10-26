from pathlib import Path
from typing import Any
import cv2
import numpy as np
from PIL import Image

class CvAnalysisResult:
    def __init__(
        self,
        status: str,
        noise_mean_variance: float | None = None,
        noise_discrepancy_ratio: float | None = None,
        copy_move_matches_count: int = 0,
        anomaly_detected: bool = False,
        explanation: str = "",
        limitations: str = "",
    ):
        self.status = status
        self.noise_mean_variance = noise_mean_variance
        self.noise_discrepancy_ratio = noise_discrepancy_ratio
        self.copy_move_matches_count = copy_move_matches_count
        self.anomaly_detected = anomaly_detected
        self.explanation = explanation
        self.limitations = limitations

def analyze_noise_and_features(file_path: Path) -> CvAnalysisResult:
    """
    Executes experimental computer vision heuristics on the image:
    1. High-frequency noise residual variance analysis (median filter residual).
    2. Keypoint-based candidate duplication / copy-move check (ORB feature matching).
    
    Returns genuine, empirical measurements from the image pixels.
    Does NOT simulate detections.
    """
    if not file_path.exists():
        return CvAnalysisResult(
            status="failed",
            explanation="Image file not found for CV analysis.",
            limitations="File access failure.",
        )

    try:
        # Load image via OpenCV in grayscale
        img_gray = cv2.imread(str(file_path), cv2.IMREAD_GRAYSCALE)
        if img_gray is None:
            return CvAnalysisResult(
                status="failed",
                explanation="Failed to decode image into OpenCV matrix.",
                limitations="Unsupported internal pixel format.",
            )

        h, w = img_gray.shape
        if h < 64 or w < 64:
            return CvAnalysisResult(
                status="inconclusive",
                explanation=f"Image dimensions ({w}x{h}) are too small for reliable spatial noise decomposition.",
                limitations="Requires minimum 64x64 pixel grid.",
            )

        # 1. Noise Residual Analysis
        # Estimate high-frequency noise by subtracting a 3x3 median filter from original
        blurred = cv2.medianBlur(img_gray, 3)
        noise_residual = cv2.absdiff(img_gray, blurred).astype(np.float32)

        # Block-based variance calculation (32x32 pixel blocks)
        block_size = 32
        h_blocks = h // block_size
        w_blocks = w // block_size

        if h_blocks > 0 and w_blocks > 0:
            block_variances = []
            for i in range(h_blocks):
                for j in range(w_blocks):
                    block = noise_residual[
                        i * block_size : (i + 1) * block_size,
                        j * block_size : (j + 1) * block_size,
                    ]
                    block_variances.append(np.var(block))

            block_variances = np.array(block_variances)
            mean_var = float(np.mean(block_variances))
            median_var = float(np.median(block_variances))
            p95_var = float(np.percentile(block_variances, 95))
            
            # Ratio of high regional variance to median regional variance
            # Use minimum baseline noise of 1.0 (quantization noise floor) to avoid division artifacts on smooth/bokeh backgrounds
            baseline_noise = max(median_var, 1.0)
            discrepancy_ratio = float(p95_var / baseline_noise)
            if mean_var < 5.0:
                # Overall image noise is negligible (e.g. smooth gradient, flat surface, or lens bokeh blur)
                discrepancy_ratio = min(discrepancy_ratio, 2.0)
        else:
            mean_var = float(np.var(noise_residual))
            discrepancy_ratio = 1.0

        # 2. Keypoint Copy-Move Candidate Analysis using ORB
        copy_move_matches = 0
        try:
            orb = cv2.ORB_create(nfeatures=1500)
            keypoints, descriptors = orb.detectAndCompute(img_gray, None)

            if descriptors is not None and len(descriptors) > 30:
                bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
                # k=3 nearest neighbors to compare self-descriptors
                matches = bf.knnMatch(descriptors, descriptors, k=3)

                min_spatial_distance = 40.0  # Pixels apart to avoid trivial self-matching
                for m_group in matches:
                    if len(m_group) >= 2:
                        best = m_group[1]  # Exclude self-match (distance 0 at index 0)
                        if best.distance < 35:  # Low Hamming distance indicates strong descriptor similarity
                            pt1 = keypoints[best.queryIdx].pt
                            pt2 = keypoints[best.trainIdx].pt
                            spatial_dist = np.hypot(pt1[0] - pt2[0], pt1[1] - pt2[1])
                            if spatial_dist >= min_spatial_distance:
                                copy_move_matches += 1
        except Exception:
            copy_move_matches = 0

        # Check if the image represents a high-contrast document/UI layout (light or dark mode)
        white_ratio = float(np.mean(img_gray > 225))
        dark_ratio = float(np.mean(img_gray < 35))
        is_light_doc = (white_ratio > 0.60) and (float(np.mean(img_gray < 75)) > 0.005)
        is_dark_doc = (dark_ratio > 0.60) and (float(np.mean(img_gray > 180)) > 0.005)
        is_document_like = is_light_doc or is_dark_doc

        # Check for dense periodic architectural textures (e.g. windows, building facades, brickwork)
        is_periodic_texture = (copy_move_matches > 400) and not is_document_like

        if is_document_like:
            # In text documents, contrast between blank paper and ink naturally produces localized variance.
            # Typographical glyphs repeat across words; this is normal document composition.
            anomaly_detected = False
            explanation = (
                f"Measured noise residual variance: {mean_var:.2f} (regional discrepancy ratio: {discrepancy_ratio:.2f}). "
                f"Identified {copy_move_matches} candidate keypoint matches consistent with typographical character repetition "
                f"in a high-contrast text/UI document ({'light mode' if is_light_doc else 'dark mode'}). "
                f"Status: Typographical character repetition (normal document layout)."
            )
            limitations = (
                "DOCUMENT HEURISTIC. In textual documents, books, and UI screenshots, repetitive font glyphs and words "
                "legitimately trigger duplicate keypoint matches. This reflects standard typographic composition, not photographic copy-move splicing."
            )
        elif is_periodic_texture:
            anomaly_detected = (discrepancy_ratio > 15.0 and mean_var > 20.0)
            explanation = (
                f"Measured noise residual variance: {mean_var:.2f} (regional discrepancy ratio: {discrepancy_ratio:.2f}). "
                f"Identified {copy_move_matches} candidate keypoint matches distributed across a dense periodic architectural or structural pattern (e.g. window grid, tiles, facade). "
                f"Status: {'Elevated spatial noise variance observed' if anomaly_detected else 'Periodic architectural surface regularity (benign natural pattern)'}."
            )
            limitations = (
                "PERIODIC PATTERN HEURISTIC. Dense uniform keypoint repetitions across geometric facades reflect "
                "natural building architecture (windows, masonry, tiles) rather than localized object duplication."
            )
        else:
            # Standard photographic scene evaluation:
            # Avoid false positives on smooth bokeh blur or natural facial symmetry
            anomaly_detected = (discrepancy_ratio > 8.0 and mean_var > 15.0) or (copy_move_matches > 200)
            explanation = (
                f"Measured noise residual variance: {mean_var:.2f} (regional discrepancy ratio: {discrepancy_ratio:.2f}). "
                f"Identified {copy_move_matches} candidate displaced keypoint descriptor matches (threshold: 40px spatial separation). "
                f"Status: {'Elevated spatial noise variance observed' if anomaly_detected else 'Within standard variance baseline'}."
            )
            limitations = (
                "EXPERIMENTAL HEURISTIC. Local noise variance discrepancies can naturally arise from "
                "lens vignetting, depth-of-field blur (bokeh), lighting shadows, or high-frequency textures (foliage, fabrics). "
                "Keypoint matches can be triggered by legitimate repetitive patterns (windows, tiles, text). "
                "This test must not be treated as standalone proof of splicing."
            )

        return CvAnalysisResult(
            status="completed",
            noise_mean_variance=round(mean_var, 2),
            noise_discrepancy_ratio=round(discrepancy_ratio, 2),
            copy_move_matches_count=copy_move_matches,
            anomaly_detected=anomaly_detected,
            explanation=explanation,
            limitations=limitations,
        )

    except Exception as e:
        return CvAnalysisResult(
            status="failed",
            explanation=f"Computer vision analysis error: {str(e)}",
            limitations="Processing failed due to matrix computational error.",
        )
