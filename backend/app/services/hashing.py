import hashlib
from pathlib import Path

def calculate_sha256_bytes(data: bytes) -> str:
    """Calculate SHA-256 hash from in-memory byte buffer."""
    hasher = hashlib.sha256()
    hasher.update(data)
    return hasher.hexdigest().lower()

def calculate_sha256_file(file_path: Path) -> str:
    """Calculate SHA-256 hash by streaming file chunks (64 KiB buffer)."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest().lower()

def verify_file_integrity(file_path: Path, expected_hash: str) -> tuple[bool, str]:
    """
    Independently re-reads the stored file, computes the current SHA-256 digest,
    and returns (matches: bool, current_hash: str).
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Evidence file not found at path: {file_path}")
        
    current_hash = calculate_sha256_file(file_path)
    matches = (current_hash == expected_hash.lower())
    return matches, current_hash
