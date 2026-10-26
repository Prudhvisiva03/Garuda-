"""
Scientific validation script for 9 controlled photographic scenarios.
Measures and records empirical metrics without fabrication.
"""
import io
import json
import tempfile
from pathlib import Path
import numpy as np
import cv2
from PIL import Image, ImageDraw

from backend.app.services.image_comparator import compare_images_for_crop, compute_pixel_differences

def run_evaluation_matrix():
    real_fixtures_dir = Path("test_fixtures/real_photos")
    ref_path = real_fixtures_dir / "real_landscape_reference.jpg"
    crop_path = real_fixtures_dir / "real_landscape_crop_candidate.jpg"
    unrel_path = real_fixtures_dir / "real_portrait_unrelated.jpg"

    assert ref_path.exists(), "Reference photo missing"
    assert crop_path.exists(), "Crop candidate missing"
    assert unrel_path.exists(), "Unrelated photo missing"

    ref_img = Image.open(ref_path)
    ref_w, ref_h = ref_img.size

    results = {}

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_dir = Path(tmpdir)

        # 1. Exact byte duplicate
        res1 = compare_images_for_crop(ref_path, ref_path, "ref", "cand_1")
        results["1_exact_byte_duplicate"] = {
            "scenario": "Exact Byte Duplicate (Identical SHA-256)",
            "status": res1.status,
            "inliers": res1.inliers_count,
            "raw_matches": res1.raw_matches,
            "inlier_ratio": res1.inlier_ratio,
            "scale": res1.estimated_scale,
            "area_ratio": res1.overlap_box.get("area_ratio") if res1.overlap_box else None,
            "explanation": res1.explanation,
        }

        # 2. Re-encoded / metadata-altered full-frame
        reenc_path = tmp_dir / "reencoded_q90.jpg"
        ref_img.save(reenc_path, format="JPEG", quality=90)
        res2 = compare_images_for_crop(ref_path, reenc_path, "ref", "cand_2")
        results["2_reencoded_identical"] = {
            "scenario": "Re-encoded / Format Transcoded (Full Frame Q=90)",
            "status": res2.status,
            "inliers": res2.inliers_count,
            "raw_matches": res2.raw_matches,
            "inlier_ratio": res2.inlier_ratio,
            "scale": res2.estimated_scale,
            "area_ratio": res2.overlap_box.get("area_ratio") if res2.overlap_box else None,
            "explanation": res2.explanation,
        }

        # 3. Controlled crop (derived directly from reference)
        res3 = compare_images_for_crop(ref_path, crop_path, "ref", "cand_3")
        results["3_controlled_crop"] = {
            "scenario": "Controlled Crop from Reference Landscape",
            "status": res3.status,
            "inliers": res3.inliers_count,
            "raw_matches": res3.raw_matches,
            "inlier_ratio": res3.inlier_ratio,
            "scale": res3.estimated_scale,
            "area_ratio": res3.overlap_box.get("area_ratio") if res3.overlap_box else None,
            "explanation": res3.explanation,
        }

        # 4. Recompressed crop
        crop_reenc_path = tmp_dir / "crop_recompressed_q65.jpg"
        crop_img = Image.open(crop_path)
        crop_img.save(crop_reenc_path, format="JPEG", quality=65)
        res4 = compare_images_for_crop(ref_path, crop_reenc_path, "ref", "cand_4")
        results["4_recompressed_crop"] = {
            "scenario": "Recompressed Crop (Aggressive JPEG Q=65)",
            "status": res4.status,
            "inliers": res4.inliers_count,
            "raw_matches": res4.raw_matches,
            "inlier_ratio": res4.inlier_ratio,
            "scale": res4.estimated_scale,
            "area_ratio": res4.overlap_box.get("area_ratio") if res4.overlap_box else None,
            "explanation": res4.explanation,
        }

        # 5. Localized modification (spliced patch on 1800x1200 scene)
        spliced_path = tmp_dir / "spliced_patch.jpg"
        spliced_img = ref_img.copy()
        draw = ImageDraw.Draw(spliced_img)
        # 80x80 solid red patch at (400, 300)
        draw.rectangle([400, 300, 480, 380], fill=(220, 20, 20))
        spliced_img.save(spliced_path, format="JPEG", quality=90)
        res5 = compare_images_for_crop(ref_path, spliced_path, "ref", "cand_5")
        results["5_localized_modification"] = {
            "scenario": "Localized Modification (80x80 Spliced Patch)",
            "status": res5.status,
            "inliers": res5.inliers_count,
            "raw_matches": res5.raw_matches,
            "inlier_ratio": res5.inlier_ratio,
            "scale": res5.estimated_scale,
            "area_ratio": res5.overlap_box.get("area_ratio") if res5.overlap_box else None,
            "explanation": res5.explanation,
        }

        # 6. Completely unrelated photograph (portrait)
        res6 = compare_images_for_crop(ref_path, unrel_path, "ref", "cand_6")
        results["6_unrelated_photograph"] = {
            "scenario": "Completely Unrelated Real Photo (Portrait)",
            "status": res6.status,
            "inliers": res6.inliers_count,
            "raw_matches": res6.raw_matches,
            "inlier_ratio": res6.inlier_ratio,
            "scale": res6.estimated_scale,
            "area_ratio": res6.overlap_box.get("area_ratio") if res6.overlap_box else None,
            "explanation": res6.explanation,
        }

        # 7. Resized & Rotated candidate (0.6x scale, 12 degree rotation)
        rot_path = tmp_dir / "resized_rotated.jpg"
        scaled_w, scaled_h = int(ref_w * 0.6), int(ref_h * 0.6)
        scaled_img = ref_img.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)
        rot_img = scaled_img.rotate(12, expand=True)
        rot_img.save(rot_path, format="JPEG", quality=90)
        res7 = compare_images_for_crop(ref_path, rot_path, "ref", "cand_7")
        results["7_resized_rotated"] = {
            "scenario": "Resized (0.6x) and Rotated (12 deg) Scene",
            "status": res7.status,
            "inliers": res7.inliers_count,
            "raw_matches": res7.raw_matches,
            "inlier_ratio": res7.inlier_ratio,
            "scale": res7.estimated_scale,
            "area_ratio": res7.overlap_box.get("area_ratio") if res7.overlap_box else None,
            "explanation": res7.explanation,
        }

        # 8. Low-texture image (smooth gradient)
        low_tex_path = tmp_dir / "low_texture.jpg"
        grad_arr = np.zeros((600, 800, 3), dtype=np.uint8)
        for i in range(600):
            grad_arr[i, :, :] = int(100 + 100 * (i / 600))
        cv2.imwrite(str(low_tex_path), grad_arr)
        res8 = compare_images_for_crop(ref_path, low_tex_path, "ref", "cand_8")
        results["8_low_texture"] = {
            "scenario": "Low Texture Surface (Smooth Gradient)",
            "status": res8.status,
            "inliers": res8.inliers_count,
            "raw_matches": res8.raw_matches,
            "inlier_ratio": res8.inlier_ratio,
            "scale": res8.estimated_scale,
            "area_ratio": res8.overlap_box.get("area_ratio") if res8.overlap_box else None,
            "explanation": res8.explanation,
        }

        # 9. Repeated pattern (checkerboard grid)
        grid_path = tmp_dir / "repeated_pattern.jpg"
        grid_arr = np.zeros((600, 800, 3), dtype=np.uint8)
        for y in range(0, 600, 20):
            for x in range(0, 800, 20):
                if (x // 20 + y // 20) % 2 == 0:
                    grid_arr[y:y+20, x:x+20] = 255
        cv2.imwrite(str(grid_path), grid_arr)
        res9 = compare_images_for_crop(ref_path, grid_path, "ref", "cand_9")
        results["9_repeated_patterns"] = {
            "scenario": "Repeated Pattern (Checkerboard Grid)",
            "status": res9.status,
            "inliers": res9.inliers_count,
            "raw_matches": res9.raw_matches,
            "inlier_ratio": res9.inlier_ratio,
            "scale": res9.estimated_scale,
            "area_ratio": res9.overlap_box.get("area_ratio") if res9.overlap_box else None,
            "explanation": res9.explanation,
        }

    print(json.dumps(results, indent=2))
    return results

if __name__ == "__main__":
    run_evaluation_matrix()
