from pydantic import BaseModel, Field
from typing import Any

class EvidenceResponse(BaseModel):
    id: str
    case_id: str
    original_filename: str
    mime_type: str
    file_size: int
    width: int | None = None
    height: int | None = None
    sha256_intake: str
    created_at: str
    status: str

class IntegrityCheckResponse(BaseModel):
    evidence_id: str
    intake_hash: str
    current_hash: str
    matches: bool
    algorithm: str = "SHA-256"
    checked_at: str
    status_label: str
    message: str

class MetadataResponse(BaseModel):
    evidence_id: str
    has_exif: bool
    make: str | None = None
    model: str | None = None
    datetime_original: str | None = None
    datetime_digitized: str | None = None
    software: str | None = None
    gps_lat: float | None = None
    gps_lon: float | None = None
    gps_altitude: float | None = None
    quantization_tables: dict[str, Any] | None = None
    raw_tags: dict[str, Any] = Field(default_factory=dict)
    notes: str

class FindingResponse(BaseModel):
    id: str
    evidence_id: str
    analysis_type: str
    test_performed: str
    observed_result: str
    explanation: str
    limitations: str
    severity: str  # "info" | "low" | "medium" | "high" | "critical" | "inconclusive"
    review_status: str  # "pending" | "reviewed" | "confirmed"

class ElaAnalysisResponse(BaseModel):
    status: str  # "completed" | "unsupported" | "failed"
    quality: int
    scale: int
    mean_error: float | None = None
    max_error: float | None = None
    artifact_url: str | None = None
    explanation: str
    limitations: str

class NoiseAnalysisResponse(BaseModel):
    status: str  # "completed" | "unsupported" | "failed"
    mean_residual_variance: float | None = None
    variance_discrepancy_ratio: float | None = None
    anomaly_detected: bool = False
    explanation: str
    limitations: str

class FullAnalysisResponse(BaseModel):
    evidence_id: str
    status: str
    integrity: IntegrityCheckResponse
    metadata: MetadataResponse
    ela: ElaAnalysisResponse
    noise: NoiseAnalysisResponse
    findings: list[FindingResponse]
    analyzed_at: str

class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str
    pillow_version: str
    database_status: str
    storage_accessible: bool
    upload_limit_bytes: int

class ComparisonRequest(BaseModel):
    reference_id: str
    candidate_id: str
    algorithm: str = "SIFT"
    ratio_threshold: float = 0.75

class ComparisonResponse(BaseModel):
    id: str
    reference_id: str
    candidate_id: str
    algorithm: str
    status: str  # "exact_byte_duplicate" | "visually_similar_full_frame" | "identical_visual_content" | "possible_crop_match" | "no_reliable_match" | "inconclusive" | "failed"
    inliers_count: int
    raw_matches: int
    inlier_ratio: float
    overlap_box: dict[str, Any] | None = None
    estimated_scale: float | None = None
    artifact_url: str | None = None
    explanation: str
    limitations: str
    created_at: str

class VideoProperties(BaseModel):
    resolution: str
    width: int
    height: int
    fps: float
    total_frames: int
    codec: str
    decoded_duration_sec: float
    container_duration_sec: float | None = None
    audio_video_skew_sec: float = 0.0

class VideoCut(BaseModel):
    cut_index: int
    frame_index: int
    timestamp_sec: float
    cut_type: str
    bhattacharyya_distance: float
    bhatt_z_score: float
    pixel_delta: float
    pixel_z_score: float
    explanation: str

class VideoColorProfile(BaseModel):
    mean_saturation: float
    mean_luminance: float
    channel_correlation: float
    night_theme_detected: bool

class VideoKeyframe(BaseModel):
    frame_index: int
    timestamp_sec: float
    artifact_name: str
    artifact_path: str
    noise_variance: float
    is_cut_frame: bool

class VideoAnalysisResponse(BaseModel):
    evidence_id: str
    classification: str
    summary_statement: str
    video_properties: VideoProperties
    color_profile: VideoColorProfile
    temporal_cuts: dict[str, Any]
    keyframes: list[VideoKeyframe]
    findings: list[FindingResponse]

class AudioProperties(BaseModel):
    format: str
    sample_rate_hz: int
    channels: int
    duration_sec: float
    bitrate_kbps: int | None = None
    rms_amplitude: float
    noise_floor_rms: float

class AudioSuspiciousSegment(BaseModel):
    segment_index: int
    start_sec: float
    end_sec: float
    duration_sec: float
    anomaly_type: str  # "digital_silence" | "spectral_flux_spike" | "noise_floor_shift"
    severity: str      # "medium" | "high" | "critical"
    spectral_value: float
    z_score: float
    explanation: str

class AudioSyntheticIndicators(BaseModel):
    noise_floor_rms: float
    digital_silence_ratio_pct: float
    total_digital_silence_sec: float
    spectral_rolloff_85_hz: float
    spectral_rolloff_95_hz: float
    hf_energy_ratio_pct: float
    mean_spectral_flux: float
    max_spectral_flux: float
    synthetic_voice_detected: bool
    confidence_indicators: dict[str, Any]

class AudioAnalysisResponse(BaseModel):
    evidence_id: str
    classification: str  # "ai_synthesized_voice_detected" | "acoustic_splicing_detected" | "natural_speech_consistent"
    summary_statement: str
    audio_properties: AudioProperties
    synthetic_indicators: AudioSyntheticIndicators
    suspicious_segments: list[AudioSuspiciousSegment]
    spectrogram_artifact: str | None = None
    findings: list[FindingResponse]
