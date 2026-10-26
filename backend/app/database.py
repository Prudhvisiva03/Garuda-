import sqlite3
import json
from pathlib import Path
from contextlib import contextmanager
from typing import Generator, Any
from backend.app.config import settings

def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or settings.DB_PATH
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

@contextmanager
def get_db(db_path: Path | None = None) -> Generator[sqlite3.Connection, None, None]:
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db(db_path: Path | None = None) -> None:
    """Initialize database tables with constraints and indexes."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        
        # Evidence table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evidence (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                stored_filename TEXT NOT NULL UNIQUE,
                mime_type TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                width INTEGER,
                height INTEGER,
                sha256_intake TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL
            );
        """)
        
        # Integrity checks log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS integrity_checks (
                id TEXT PRIMARY KEY,
                evidence_id TEXT NOT NULL,
                calculated_hash TEXT NOT NULL,
                matches_intake INTEGER NOT NULL,
                checked_at TEXT NOT NULL,
                FOREIGN KEY (evidence_id) REFERENCES evidence (id) ON DELETE CASCADE
            );
        """)
        
        # Extracted Metadata
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadata_records (
                id TEXT PRIMARY KEY,
                evidence_id TEXT NOT NULL UNIQUE,
                make TEXT,
                model TEXT,
                datetime_original TEXT,
                datetime_digitized TEXT,
                software TEXT,
                gps_lat REAL,
                gps_lon REAL,
                gps_altitude REAL,
                raw_json TEXT,
                FOREIGN KEY (evidence_id) REFERENCES evidence (id) ON DELETE CASCADE
            );
        """)
        
        # Analysis Runs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analysis_runs (
                id TEXT PRIMARY KEY,
                evidence_id TEXT NOT NULL,
                analysis_type TEXT NOT NULL,
                status TEXT NOT NULL,
                parameters_json TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                FOREIGN KEY (evidence_id) REFERENCES evidence (id) ON DELETE CASCADE
            );
        """)
        
        # Generated Artifacts (ELA maps, thumbnails, etc.)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS artifacts (
                id TEXT PRIMARY KEY,
                evidence_id TEXT NOT NULL,
                analysis_type TEXT NOT NULL,
                artifact_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                mime_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (evidence_id) REFERENCES evidence (id) ON DELETE CASCADE
            );
        """)
        
        # Forensic Findings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS findings (
                id TEXT PRIMARY KEY,
                evidence_id TEXT NOT NULL,
                analysis_type TEXT NOT NULL,
                test_performed TEXT NOT NULL,
                observed_result TEXT NOT NULL,
                explanation TEXT NOT NULL,
                limitations TEXT NOT NULL,
                severity TEXT NOT NULL,
                review_status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (evidence_id) REFERENCES evidence (id) ON DELETE CASCADE
            );
        """)
        
        # Reports
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id TEXT PRIMARY KEY,
                evidence_id TEXT NOT NULL,
                file_path TEXT NOT NULL,
                generated_at TEXT NOT NULL,
                FOREIGN KEY (evidence_id) REFERENCES evidence (id) ON DELETE CASCADE
            );
        """)
        
        # Image Comparisons (Original vs Crop, etc.)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS image_comparisons (
                id TEXT PRIMARY KEY,
                reference_id TEXT NOT NULL,
                candidate_id TEXT NOT NULL,
                algorithm TEXT NOT NULL,
                status TEXT NOT NULL,
                inliers_count INTEGER NOT NULL,
                raw_matches INTEGER NOT NULL,
                inlier_ratio REAL NOT NULL,
                overlap_box_json TEXT,
                estimated_scale REAL,
                artifact_name TEXT,
                explanation TEXT NOT NULL,
                limitations TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (reference_id) REFERENCES evidence (id) ON DELETE CASCADE,
                FOREIGN KEY (candidate_id) REFERENCES evidence (id) ON DELETE CASCADE
            );
        """)

        # Cases Table (Law Enforcement Case Registry)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cases (
                id TEXT PRIMARY KEY,
                case_number TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL,
                priority TEXT NOT NULL,
                category TEXT NOT NULL,
                assigned_to TEXT NOT NULL,
                organization_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)

        # Audit Logs Table (Section 65B Immutable Audit Trail)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                user_id TEXT NOT NULL,
                user_name TEXT NOT NULL,
                action TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                details TEXT NOT NULL,
                ip_address TEXT NOT NULL
            );
        """)

        # Pre-populate default official cases if table is empty
        cursor.execute("SELECT COUNT(*) FROM cases;")
        if cursor.fetchone()[0] == 0:
            default_cases = [
                (
                    "case-bih-2026-041",
                    "FIR-2026-041/CYBER",
                    "Digital Media Tampering & Identity Forgery Investigation",
                    "Forensic examination of altered photographic evidence, forged identity credentials, and cloned texture regions.",
                    "in-progress",
                    "high",
                    "Image Forensics",
                    json.dumps(["Inspector S. Verma (Cyber FSL)"]),
                    "State Cyber Crime Investigation Division",
                    "2026-10-10T09:00:00+05:30",
                    "2026-10-18T14:30:00+05:30",
                ),
                (
                    "case-bih-2026-088",
                    "FIR-2026-088/CCTV",
                    "Surveillance Video Frame-Splice & Temporal Integrity Audit",
                    "Verification of CCTV camera feeds for dropped frames, inter-frame splicing, and lighting discontinuity.",
                    "open",
                    "medium",
                    "Video Forensics",
                    json.dumps(["Analyst R. K. Singh (Video Forensics Lab)"]),
                    "State Cyber Crime Investigation Division",
                    "2026-10-12T11:00:00+05:30",
                    "2026-10-18T16:15:00+05:30",
                ),
                (
                    "case-bih-2026-104",
                    "FIR-2026-104/VOICE",
                    "Cyber Extortion Audio & Deepfake Voice Biometric Analysis",
                    "Spectral analysis, high-frequency harmonic verification, and splice detection on extortion voice notes.",
                    "pending-review",
                    "high",
                    "Audio Forensics",
                    json.dumps(["Dr. P. Mukherjee (Senior Audio Forensics Examiner)"]),
                    "Central Forensic Science Laboratory",
                    "2026-10-14T16:00:00+05:30",
                    "2026-10-18T18:45:00+05:30",
                ),
            ]
            cursor.executemany("""
                INSERT INTO cases (
                    id, case_number, title, description, status, priority,
                    category, assigned_to, organization_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, default_cases)

        # Pre-populate default audit logs if table is empty
        cursor.execute("SELECT COUNT(*) FROM audit_logs;")
        if cursor.fetchone()[0] == 0:
            default_audits = [
                ("aud-2026-101", "2026-10-18T17:30:00+05:30", "inv-usr-041", "Inspector S. Verma", "evidence.ingest", "evidence", "ev_86acb2bdabaf", "Ingested and SHA-256 verified Red_Teaming_Original_Fixed.png into FIR-2026-041/CYBER", "10.20.4.15"),
                ("aud-2026-102", "2026-10-18T16:45:00+05:30", "inv-usr-088", "Analyst R. K. Singh", "analysis.video_temporal", "evidence", "ev_vid_80b6689c2269", "Executed temporal histogram discontinuity & splice check on static_cctv.mp4", "10.20.4.22"),
                ("aud-2026-103", "2026-10-18T15:20:00+05:30", "inv-usr-104", "Dr. P. Mukherjee", "analysis.voice_synthesis", "evidence", "ev_aud_1d03ea1f21bf", "Extracted spectral centroid and pitch variance for Cyber voice 6 .wav", "10.20.4.30"),
                ("aud-2026-104", "2026-10-18T14:10:00+05:30", "inv-usr-041", "Inspector S. Verma", "case.status_update", "case", "case-bih-2026-041", "Updated case status to in-progress following multi-modal evidence review", "10.20.4.15"),
            ]
            cursor.executemany("""
                INSERT INTO audit_logs (
                    id, timestamp, user_id, user_name, action, resource_type, resource_id, details, ip_address
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, default_audits)

        # Migration helper for existing databases
        try:
            cursor.execute("ALTER TABLE image_comparisons ADD COLUMN estimated_scale REAL;")
        except Exception:
            pass

# Initialize database on module import
init_db()

def record_audit_event(
    action: str,
    resource_type: str,
    resource_id: str,
    details: str,
    user_name: str = "Inspector S. Verma",
    user_id: str = "inv-usr-041",
    ip_address: str = "127.0.0.1",
    db_path: Path | None = None,
) -> None:
    """Appends an immutable audit log entry compliant with Section 65B."""
    import uuid
    from datetime import datetime, timezone
    try:
        with get_db(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO audit_logs (
                    id, timestamp, user_id, user_name, action, resource_type, resource_id, details, ip_address
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                f"aud-{uuid.uuid4().hex[:8]}",
                datetime.now(timezone.utc).isoformat(),
                user_id,
                user_name,
                action,
                resource_type,
                resource_id,
                details,
                ip_address,
            ))
    except Exception:
        pass

