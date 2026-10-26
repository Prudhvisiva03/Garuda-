// EviSutra — Type Definitions
// Client-side data model. Backend model may differ.

export type CaseStatus = 'open' | 'in-progress' | 'pending-review' | 'closed' | 'archived';
export type CasePriority = 'critical' | 'high' | 'medium' | 'low';
export type EvidenceType = 'image' | 'video' | 'audio' | 'document' | 'other';
export type EvidenceStatus = 'uploaded' | 'validating' | 'validated' | 'analyzing' | 'analyzed' | 'error' | 'unsupported';
export type AnalysisStatus = 'not-analyzed' | 'queued' | 'processing' | 'completed' | 'error' | 'unsupported' | 'planned';
export type FindingSeverity = 'critical' | 'high' | 'medium' | 'low' | 'info' | 'inconclusive';
export type ReviewStatus = 'pending' | 'reviewed' | 'disputed' | 'confirmed';

export type AnalysisType =
  | 'ela'
  | 'metadata'
  | 'hash-verify'
  | 'ai-detection'
  | 'copy-move'
  | 'noise-analysis';

export interface Case {
  id: string;
  caseNumber: string;
  title: string;
  description: string;
  status: CaseStatus;
  priority: CasePriority;
  category: string;
  createdAt: string;
  updatedAt: string;
  evidenceCount: number;
  assignedTo: string[];
  organizationId: string;
}

export interface EvidenceItem {
  id: string;
  caseId: string;
  fileName: string;
  originalFileName: string;
  fileType: EvidenceType;
  mimeType: string;
  fileSize: number;
  dimensions?: { width: number; height: number };
  sha256: string | null;
  status: EvidenceStatus;
  uploadedAt: string;
  uploadedBy: string;
  description: string;
  chainOfCustody: string;
  analysisResults: AnalysisResult[];
}

export interface AnalysisResult {
  id: string;
  evidenceId: string;
  analysisType: AnalysisType;
  status: AnalysisStatus;
  startedAt: string | null;
  completedAt: string | null;
  findings: Finding[];
  engineVersion: string | null;
  settings: Record<string, unknown>;
}

export interface Finding {
  id: string;
  analysisId: string;
  testPerformed: string;
  observedResult: string;
  explanation: string;
  limitations: string;
  severity: FindingSeverity;
  reviewStatus: ReviewStatus;
  reviewedBy: string | null;
  reviewNotes: string | null;
}

export interface AuditEvent {
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

export interface Report {
  id: string;
  caseId: string;
  title: string;
  generatedAt: string | null;
  status: 'pending' | 'generating' | 'completed' | 'error';
  generatedBy: string;
  format: 'pdf' | 'html' | 'json';
}

export interface SystemStatus {
  service: string;
  status: 'operational' | 'degraded' | 'offline' | 'not-implemented';
  lastChecked: string;
  message: string;
}

export interface DashboardStats {
  totalCases: number;
  activeCases: number;
  pendingReview: number;
  totalEvidence: number;
}
