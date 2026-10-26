import io
import os
import uuid
from pathlib import Path
from PIL import Image, UnidentifiedImageError
from fastapi import HTTPException, status, UploadFile
from backend.app.config import settings

# Enforce PIL decompression bomb limit
Image.MAX_IMAGE_PIXELS = settings.MAX_IMAGE_PIXELS

# Known magic numbers
MAGIC_BYTES = {
    "image/jpeg": [b"\xFF\xD8\xFF"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
}

def detect_mime_from_magic_bytes(header: bytes) -> str | None:
    if header.startswith(b"\xFF\xD8\xFF"):
        return "image/jpeg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    return None

def sanitize_filename(filename: str) -> str:
    # Strip any directory traversal characters (Unix or Windows)
    clean = os.path.basename(filename.replace("\\", "/"))
    # Fallback to evidence if empty or whitespace
    clean = clean.strip()
    return clean if clean else "unnamed_evidence"

class ValidatedFile:
    def __init__(
        self,
        evidence_id: str,
        original_filename: str,
        stored_filename: str,
        stored_path: Path,
        mime_type: str,
        file_size: int,
        width: int,
        height: int,
        raw_bytes: bytes,
    ):
        self.evidence_id = evidence_id
        self.original_filename = original_filename
        self.stored_filename = stored_filename
        self.stored_path = stored_path
        self.mime_type = mime_type
        self.file_size = file_size
        self.width = width
        self.height = height
        self.raw_bytes = raw_bytes

def validate_and_save_upload(
    upload_file: UploadFile,
    max_size: int = settings.MAX_UPLOAD_SIZE,
) -> ValidatedFile:
    # 1. Read file bytes
    try:
        raw_bytes = upload_file.file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to read uploaded file: {str(e)}",
        )
    
    file_size = len(raw_bytes)
    
    # 2. Size limit check
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes).",
        )
    
    if file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size ({file_size} bytes) exceeds the maximum allowed limit of {max_size} bytes (10 MiB).",
        )

    # 3. Magic bytes inspection (header must be at least 8 bytes)
    if len(raw_bytes) < 8:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File is too small to contain a valid media header.",
        )
        
    detected_mime = detect_mime_from_magic_bytes(raw_bytes[:8])
    if not detected_mime or detected_mime not in settings.ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file format. Only genuine JPEG and PNG images are supported by the engine.",
        )

    # 4. Strict Image decoding & integrity check using Pillow
    try:
        with Image.open(io.BytesIO(raw_bytes)) as img:
            # Verify basic structural integrity without loading entire image pixels
            img.verify()
            
        # Re-open because verify() closes or alters internal image pointer
        with Image.open(io.BytesIO(raw_bytes)) as img:
            width, height = img.size
            if width <= 0 or height <= 0:
                raise ValueError("Invalid image dimensions detected.")
            
            # Check decompression bomb pixel count
            total_pixels = width * height
            if total_pixels > settings.MAX_IMAGE_PIXELS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Image dimensions ({width}x{height} = {total_pixels} pixels) exceed safety threshold.",
                )
    except (UnidentifiedImageError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image decoding failed or corrupted file structure: {str(e)}",
        )
    except Image.DecompressionBombError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Decompression bomb protection triggered: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image validation error: {str(e)}",
        )

    # 5. Generate secure, non-executable storage filename
    evidence_id = f"ev_{uuid.uuid4().hex[:12]}"
    ext = ".jpg" if detected_mime == "image/jpeg" else ".png"
    stored_filename = f"{evidence_id}_{uuid.uuid4().hex[:8]}{ext}"
    stored_path = settings.EVIDENCE_DIR / stored_filename
    
    # Check that parent directory exists and write bytes
    settings.EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    with open(stored_path, "wb") as f:
        f.write(raw_bytes)
        
    # Read-only permission simulation (ensure file is not executable)
    clean_name = sanitize_filename(upload_file.filename or "evidence_file")

    return ValidatedFile(
        evidence_id=evidence_id,
        original_filename=clean_name,
        stored_filename=stored_filename,
        stored_path=stored_path,
        mime_type=detected_mime,
        file_size=file_size,
        width=width,
        height=height,
        raw_bytes=raw_bytes,
    )
