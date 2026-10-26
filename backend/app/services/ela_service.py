import io
import uuid
from pathlib import Path
from PIL import Image, ImageChops, ImageEnhance
import numpy as np
from backend.app.config import settings

class ElaResult:
    def __init__(
        self,
        status: str,
        quality: int,
        scale: int,
        mean_error: float | None = None,
        max_error: float | None = None,
        artifact_path: Path | None = None,
        artifact_filename: str | None = None,
        explanation: str = "",
        limitations: str = "",
    ):
        self.status = status
        self.quality = quality
        self.scale = scale
        self.mean_error = mean_error
        self.max_error = max_error
        self.artifact_path = artifact_path
        self.artifact_filename = artifact_filename
        self.explanation = explanation
        self.limitations = limitations

def generate_ela(
    file_path: Path,
    evidence_id: str,
    quality: int = settings.DEFAULT_ELA_QUALITY,
    scale: int = settings.DEFAULT_ELA_SCALE,
) -> ElaResult:
    """
    Performs genuine Error Level Analysis (ELA) on an image:
    1. Reads original without modification.
    2. Checks format compatibility (JPEG only; PNG is lossless).
    3. Recompresses copy in memory at specified JPEG quality.
    4. Calculates absolute difference between original and recompressed.
    5. Scales the difference for human visual inspection.
    6. Saves derived artifact separately.
    """
    if not file_path.exists():
        return ElaResult(
            status="failed",
            quality=quality,
            scale=scale,
            explanation="Original evidence file could not be located.",
            limitations="File I/O error prevented analysis.",
        )

    try:
        with Image.open(file_path) as orig_img:
            image_format = orig_img.format

            # Check format applicability
            if image_format != "JPEG":
                return ElaResult(
                    status="unsupported",
                    quality=quality,
                    scale=scale,
                    explanation=(
                        f"ELA is not applicable to the original {image_format} compression history. "
                        "Error Level Analysis measures differential quantization losses inherent to "
                        "lossy JPEG discrete cosine transform (DCT) compression. Lossless formats such "
                        "as PNG use Deflate compression and exhibit no DCT compression grids."
                    ),
                    limitations=(
                        "Inapplicable to lossless formats (PNG), uncompressed bitmaps (BMP), or synthetic vectors. "
                        "Converting a PNG to JPEG after the fact does not recover original camera compression history."
                    ),
                )

            # Ensure image is in RGB mode for consistent comparison
            orig_rgb = orig_img.convert("RGB")

            # Re-compress in memory as JPEG at designated quality
            buffer = io.BytesIO()
            orig_rgb.save(buffer, format="JPEG", quality=quality)
            buffer.seek(0)
            
            with Image.open(buffer) as recomp_img:
                recomp_rgb = recomp_img.convert("RGB")

                # Calculate absolute difference
                diff = ImageChops.difference(orig_rgb, recomp_rgb)

                # Convert to numpy array for exact statistical analysis
                diff_arr = np.array(diff, dtype=np.float32)
                mean_err = float(np.mean(diff_arr))
                max_err = float(np.max(diff_arr))

                # Scale difference for visual inspection
                # Multiply pixel values by scale factor, clamped to 255
                scaled_arr = np.clip(diff_arr * scale, 0, 255).astype(np.uint8)
                ela_visual = Image.fromarray(scaled_arr)

                # Save derived artifact separately
                artifact_filename = f"{evidence_id}_ela_q{quality}_s{scale}.png"
                artifact_path = settings.ARTIFACTS_DIR / artifact_filename
                ela_visual.save(artifact_path, format="PNG")

                explanation = (
                    f"ELA executed at JPEG quality factor {quality} with {scale}x visual scaling. "
                    f"Measured mean compression error: {mean_err:.2f}, peak difference: {max_err:.2f}. "
                    "In a pristine JPEG, surfaces of similar texture and brightness typically exhibit "
                    "a uniform level of compression error."
                )

                limitations = (
                    "ELA is an indicative heuristic, NOT conclusive proof of tampering. "
                    "High-contrast edges, saturated surfaces, and complex textures naturally produce "
                    "higher error levels than smooth flat regions. Multiple resaves, social media "
                    "recompression, and aggressive downscaling significantly diminish ELA reliability."
                )

                return ElaResult(
                    status="completed",
                    quality=quality,
                    scale=scale,
                    mean_error=round(mean_err, 2),
                    max_error=round(max_err, 2),
                    artifact_path=artifact_path,
                    artifact_filename=artifact_filename,
                    explanation=explanation,
                    limitations=limitations,
                )

    except Exception as e:
        return ElaResult(
            status="failed",
            quality=quality,
            scale=scale,
            explanation=f"Error executing ELA algorithm: {str(e)}",
            limitations="Analysis failed due to an unexpected decoding or processing exception.",
        )
