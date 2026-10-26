// Garuda Forensics API Client

export interface ApiEvidence {
  id: string;
  case_id: string;
  original_filename: string;
  mime_type: string;
  file_size: number;
  width: number | null;
  height: number | null;
  sha256_intake: string;
  created_at: string;
  status: string;
}

export interface ApiIntegrityCheck {
  evidence_id: string;
  intake_hash: string;
  current_hash: string;
  matches: boolean;
  algorithm: string;
  checked_at: string;
  status_label: string;
  message: string;
}

export interface ApiMetadata {
  evidence_id: string;
  has_exif: boolean;
  make: string | null;
  model: string | null;
  datetime_original: string | null;
  datetime_digitized: string | null;
  software: string | null;
  gps_lat: number | null;
  gps_lon: number | null;
  gps_altitude: number | null;
  raw_tags: Record<string, string>;
  notes: string;
}

export interface ApiFinding {
  id: string;
  evidence_id: string;
  analysis_type: string;
  test_performed: string;
  observed_result: string;
  explanation: string;
  limitations: string;
  severity: 'info' | 'low' | 'medium' | 'high' | 'critical' | 'inconclusive';
  review_status: 'pending' | 'reviewed' | 'confirmed';
}

export interface ApiEla {
  status: 'completed' | 'unsupported' | 'failed';
  quality: number;
  scale: number;
  mean_error: number | null;
  max_error: number | null;
  artifact_url: string | null;
  explanation: string;
  limitations: string;
}

export interface ApiNoise {
  status: string;
  mean_residual_variance: number | null;
  variance_discrepancy_ratio: number | null;
  anomaly_detected: boolean;
  explanation: string;
  limitations: string;
}

export interface ApiFullAnalysis {
  evidence_id: string;
  status: string;
  integrity: ApiIntegrityCheck;
  metadata: ApiMetadata;
  ela: ApiEla;
  noise: ApiNoise;
  findings: ApiFinding[];
  analyzed_at: string;
}

export interface ApiHealth {
  status: string;
  app_name: string;
  version: string;
  pillow_version: string;
  database_status: string;
  storage_accessible: boolean;
  upload_limit_bytes: number;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1';

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = `Request failed with status ${res.status}`;
    try {
      const errJson = await res.json();
      if (errJson && errJson.detail) {
        errorDetail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // Ignore json parse error
    }
    throw new Error(errorDetail);
  }
  return res.json();
}

export interface ApiOverlapBox {
  x: number;
  y: number;
  width: number;
  height: number;
  polygon?: [number, number][];
  area_ratio?: number;
}

export interface ApiComparisonResponse {
  id: string;
  reference_id: string;
  candidate_id: string;
  algorithm: string;
  status:
    | 'exact_byte_duplicate'
    | 'visually_similar_full_frame'
    | 'identical_visual_content'
    | 'possible_crop_match'
    | 'no_reliable_match'
    | 'inconclusive'
    | 'failed';
  inliers_count: number;
  raw_matches: number;
  inlier_ratio: number;
  overlap_box: ApiOverlapBox | null;
  estimated_scale: number | null;
  artifact_url: string | null;
  explanation: string;
  limitations: string;
  created_at: string;
}

export const api = {
  async getHealth(): Promise<ApiHealth> {
    const res = await fetch(`${API_BASE}/health`);
    return handleResponse<ApiHealth>(res);
  },

  async uploadEvidence(file: File, caseId: string = 'CASE-2026-001'): Promise<ApiEvidence> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('case_id', caseId);

    const res = await fetch(`${API_BASE}/evidence/upload`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse<ApiEvidence>(res);
  },

  async listEvidence(): Promise<ApiEvidence[]> {
    const res = await fetch(`${API_BASE}/evidence`);
    return handleResponse<ApiEvidence[]>(res);
  },

  async getEvidence(evidenceId: string): Promise<ApiEvidence> {
    const res = await fetch(`${API_BASE}/evidence/${evidenceId}`);
    return handleResponse<ApiEvidence>(res);
  },

  async verifyHash(evidenceId: string): Promise<ApiIntegrityCheck> {
    const res = await fetch(`${API_BASE}/evidence/${evidenceId}/verify-hash`, {
      method: 'POST',
    });
    return handleResponse<ApiIntegrityCheck>(res);
  },

  async runAnalysis(
    evidenceId: string,
    elaQuality: number = 95,
    elaScale: number = 15,
  ): Promise<ApiFullAnalysis> {
    const res = await fetch(
      `${API_BASE}/analysis/${evidenceId}/analyze?ela_quality=${elaQuality}&ela_scale=${elaScale}`,
      { method: 'POST' }
    );
    return handleResponse<ApiFullAnalysis>(res);
  },

  async getAnalysis(evidenceId: string): Promise<ApiFullAnalysis> {
    const res = await fetch(`${API_BASE}/analysis/${evidenceId}/analysis`);
    return handleResponse<ApiFullAnalysis>(res);
  },

  async compareImages(
    referenceId: string,
    candidateId: string,
    algorithm: string = 'SIFT',
    ratioThreshold: number = 0.75,
  ): Promise<ApiComparisonResponse> {
    const res = await fetch(`${API_BASE}/analysis/compare`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        reference_id: referenceId,
        candidate_id: candidateId,
        algorithm,
        ratio_threshold: ratioThreshold,
      }),
    });
    return handleResponse<ApiComparisonResponse>(res);
  },

  async getComparison(comparisonId: string): Promise<ApiComparisonResponse> {
    const res = await fetch(`${API_BASE}/analysis/compare/${comparisonId}`);
    return handleResponse<ApiComparisonResponse>(res);
  },

  getComparisonArtifactUrl(comparisonId: string): string {
    return `${API_BASE}/analysis/compare/${comparisonId}/artifact`;
  },

  async generateReport(evidenceId: string): Promise<{ report_id: string; download_url: string }> {
    const res = await fetch(`${API_BASE}/reports/${evidenceId}/generate`, {
      method: 'POST',
    });
    return handleResponse<{ report_id: string; download_url: string }>(res);
  },

  getReportDownloadUrl(evidenceId: string): string {
    return `${API_BASE}/reports/${evidenceId}/download`;
  },

  getEvidenceFileUrl(evidenceId: string): string {
    return `${API_BASE}/evidence/${evidenceId}/file`;
  },

  getArtifactUrl(evidenceId: string, type: string = 'ela'): string {
    return `${API_BASE}/evidence/${evidenceId}/artifact/${type}`;
  },

  // Video Forensics Engine APIs
  async uploadVideo(file: File, caseId: string = 'CASE-2026-VID'): Promise<ApiEvidence> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('case_id', caseId);
    const res = await fetch(`${API_BASE}/video/upload`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse<ApiEvidence>(res);
  },

  async listVideos(): Promise<ApiEvidence[]> {
    const res = await fetch(`${API_BASE}/video/list`);
    return handleResponse<ApiEvidence[]>(res);
  },

  async runVideoAnalysis(evidenceId: string): Promise<ApiVideoAnalysisResponse> {
    const res = await fetch(`${API_BASE}/video/${evidenceId}/analyze`, {
      method: 'POST',
    });
    return handleResponse<ApiVideoAnalysisResponse>(res);
  },

  async getVideoResults(evidenceId: string): Promise<ApiVideoAnalysisResponse> {
    const res = await fetch(`${API_BASE}/video/${evidenceId}/results`);
    return handleResponse<ApiVideoAnalysisResponse>(res);
  },

  getVideoReportUrl(evidenceId: string): string {
    return `${API_BASE}/video/${evidenceId}/report`;
  },

  getVideoArtifactUrl(filename: string): string {
    return `${API_BASE}/video/artifact/${filename}`;
  },

  // Audio Forensics Engine APIs
  async uploadAudio(file: File, caseId: string = 'CASE-2026-AUD'): Promise<ApiEvidence> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('case_id', caseId);
    const res = await fetch(`${API_BASE}/audio/upload`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse<ApiEvidence>(res);
  },

  async listAudios(): Promise<ApiEvidence[]> {
    const res = await fetch(`${API_BASE}/audio/list`);
    return handleResponse<ApiEvidence[]>(res);
  },

  async runAudioAnalysis(evidenceId: string): Promise<ApiAudioAnalysisResponse> {
    const res = await fetch(`${API_BASE}/audio/${evidenceId}/analyze`, {
      method: 'POST',
    });
    return handleResponse<ApiAudioAnalysisResponse>(res);
  },

  async getAudioResults(evidenceId: string): Promise<ApiAudioAnalysisResponse> {
    const res = await fetch(`${API_BASE}/audio/${evidenceId}/results`);
    return handleResponse<ApiAudioAnalysisResponse>(res);
  },

  getAudioReportUrl(evidenceId: string): string {
    return `${API_BASE}/audio/${evidenceId}/report`;
  },

  getAudioArtifactUrl(filename: string): string {
    return `${API_BASE}/audio/artifact/${filename}`;
  },

  // Case Management APIs (SQLite backed)
  async listCases(): Promise<ApiCase[]> {
    const res = await fetch(`${API_BASE}/cases`);
    return handleResponse<ApiCase[]>(res);
  },

  async createCase(payload: {
    case_number: string;
    title: string;
    description?: string;
    priority?: string;
    category?: string;
    assigned_to?: string[];
    organization_id?: string;
  }): Promise<ApiCase> {
    const res = await fetch(`${API_BASE}/cases`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<ApiCase>(res);
  },

  async getCase(caseId: string): Promise<ApiCase> {
    const res = await fetch(`${API_BASE}/cases/${caseId}`);
    return handleResponse<ApiCase>(res);
  },

  async listCaseEvidence(caseId: string): Promise<ApiEvidence[]> {
    const res = await fetch(`${API_BASE}/cases/${caseId}/evidence`);
    return handleResponse<ApiEvidence[]>(res);
  },

  // Audit Trail APIs (SQLite backed)
  async listAuditEvents(): Promise<ApiAuditEvent[]> {
    const res = await fetch(`${API_BASE}/audit`);
    return handleResponse<ApiAuditEvent[]>(res);
  },
};

export interface ApiCase {
  id: string;
  case_number: string;
  title: string;
  description: string;
  status: string;
  priority: string;
  category: string;
  assigned_to: string[];
  organization_id: string;
  created_at: string;
  updated_at: string;
  evidence_count: number;
}

export interface ApiAuditEvent {
  id: string;
  timestamp: string;
  userId: string;
  userName: string;
  action: string;
  resourceType: string;
  resourceId: string;
  details: string;
  ipAddress: string;
  isDemo: boolean;
}

export interface ApiVideoProperties {
  resolution: string;
  width: number;
  height: number;
  fps: number;
  total_frames: number;
  codec: string;
  decoded_duration_sec: number;
  container_duration_sec: number | null;
  audio_video_skew_sec: number;
}

export interface ApiVideoCut {
  cut_index: number;
  frame_index: number;
  timestamp_sec: number;
  cut_type: string;
  bhattacharyya_distance: number;
  bhatt_z_score: number;
  pixel_delta: number;
  pixel_z_score: number;
  explanation: string;
}

export interface ApiVideoColorProfile {
  mean_saturation: number;
  mean_luminance: number;
  channel_correlation: number;
  night_theme_detected: boolean;
}

export interface ApiVideoKeyframe {
  frame_index: number;
  timestamp_sec: number;
  artifact_name: string;
  artifact_path: string;
  noise_variance: number;
  is_cut_frame: boolean;
}

export interface ApiVideoAnalysisResponse {
  evidence_id: string;
  classification: string;
  summary_statement: string;
  video_properties: ApiVideoProperties;
  color_profile: ApiVideoColorProfile;
  temporal_cuts: {
    total_cuts_detected: number;
    cuts: ApiVideoCut[];
    sampling_stride: number;
    thresholds: Record<string, number>;
  };
  keyframes: ApiVideoKeyframe[];
  findings: ApiFinding[];
}

export interface ApiAudioProperties {
  format: string;
  sample_rate_hz: number;
  channels: number;
  duration_sec: number;
  bitrate_kbps: number | null;
  rms_amplitude: number;
  noise_floor_rms: number;
}

export interface ApiAudioSuspiciousSegment {
  segment_index: number;
  start_sec: number;
  end_sec: number;
  duration_sec: number;
  anomaly_type: string;
  severity: string;
  spectral_value: number;
  z_score: number;
  explanation: string;
}

export interface ApiAudioSyntheticIndicators {
  noise_floor_rms: number;
  digital_silence_ratio_pct: number;
  total_digital_silence_sec: number;
  spectral_rolloff_85_hz: number;
  spectral_rolloff_95_hz: number;
  hf_energy_ratio_pct: number;
  mean_spectral_flux: number;
  max_spectral_flux: number;
  synthetic_voice_detected: boolean;
  confidence_indicators: Record<string, string>;
}

export interface ApiAudioAnalysisResponse {
  evidence_id: string;
  classification: string;
  summary_statement: string;
  audio_properties: ApiAudioProperties;
  synthetic_indicators: ApiAudioSyntheticIndicators;
  suspicious_segments: ApiAudioSuspiciousSegment[];
  spectrogram_artifact: string | null;
  findings: ApiFinding[];
}
