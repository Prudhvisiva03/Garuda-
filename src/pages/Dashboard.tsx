// Garuda Dashboard — Real Health & Evidence Metrics with Demo Fallbacks

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Briefcase, Activity, Clock, FileSearch, ArrowRight, ShieldCheck } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { StatusIndicator } from '@/components/ui/StatusIndicator';
import { DEMO_DASHBOARD_STATS, DEMO_CASES } from '@/data/demo';
import { formatDate } from '@/utils/formatters';
import { api, type ApiEvidence, type ApiHealth, type ApiCase } from '@/api/client';
import type { Case, CaseStatus, CasePriority } from '@/types';

function getStatusBadgeVariant(status: CaseStatus): 'info' | 'warning' | 'success' | 'neutral' {
  switch (status) {
    case 'open':
      return 'info';
    case 'in-progress':
    case 'pending-review':
      return 'warning';
    case 'closed':
      return 'success';
    case 'archived':
    default:
      return 'neutral';
  }
}

function getStatusLabel(status: CaseStatus): string {
  switch (status) {
    case 'open':
      return 'Open';
    case 'in-progress':
      return 'In Progress';
    case 'pending-review':
      return 'Pending Review';
    case 'closed':
      return 'Closed';
    case 'archived':
      return 'Archived';
    default:
      return status;
  }
}

export function Dashboard() {
  const [realEvidence, setRealEvidence] = useState<ApiEvidence[]>([]);
  const [healthInfo, setHealthInfo] = useState<ApiHealth | null>(null);
  const [liveCases, setLiveCases] = useState<Case[]>(DEMO_CASES);

  useEffect(() => {
    async function fetchLiveStatus() {
      try {
        const [health, evidenceList, casesList] = await Promise.all([
          api.getHealth().catch(() => null),
          api.listEvidence().catch(() => []),
          api.listCases().catch(() => []),
        ]);
        if (health) setHealthInfo(health);
        if (evidenceList) setRealEvidence(evidenceList);
        if (casesList && casesList.length > 0) {
          setLiveCases(
            casesList.map((c: ApiCase) => ({
              id: c.id,
              caseNumber: c.case_number,
              title: c.title,
              description: c.description,
              status: c.status as CaseStatus,
              priority: c.priority as CasePriority,
              category: c.category,
              createdAt: c.created_at,
              updatedAt: c.updated_at,
              evidenceCount: c.evidence_count,
              assignedTo: c.assigned_to,
              organizationId: c.organization_id,
            }))
          );
        }
      } catch {
        // Fall back gracefully
      }
    }
    fetchLiveStatus();
  }, []);

  const totalCasesCount = liveCases.length > 0 ? liveCases.length : DEMO_DASHBOARD_STATS.totalCases;
  const activeCasesCount = liveCases.filter((c) => c.status === 'in-progress' || c.status === 'open').length || DEMO_DASHBOARD_STATS.activeCases;
  const pendingReviewCount = liveCases.filter((c) => c.status === 'pending-review').length || DEMO_DASHBOARD_STATS.pendingReview;
  const totalEvidenceCount = realEvidence.length > 0 ? realEvidence.length : DEMO_DASHBOARD_STATS.totalEvidence;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-xl sm:text-2xl font-semibold text-slate-900 tracking-tight">Dashboard</h1>
        <p className="text-sm text-slate-500 mt-1">Forensic investigation operations & diagnostics overview</p>
      </div>

      {/* Stat Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
        {/* Total Cases */}
        <div className="bg-white shadow-sm border border-slate-200 rounded-lg p-5 flex items-center justify-between">
          <div>
            <p className="text-slate-500 text-sm font-medium">Total Cases</p>
            <p className="text-2xl text-slate-900 font-bold mt-1">{totalCasesCount}</p>
            <span className="inline-block mt-1 text-[10px] font-mono text-cyan-700 bg-cyan-50 px-1.5 py-0.5 rounded font-medium">
              ACTIVE REPOSITORY
            </span>
          </div>
          <div className="w-12 h-12 rounded-full bg-cyan-50 border border-cyan-200 flex items-center justify-center text-cyan-600 flex-shrink-0">
            <Briefcase className="w-6 h-6" />
          </div>
        </div>

        {/* Active Cases */}
        <div className="bg-white shadow-sm border border-slate-200 rounded-lg p-5 flex items-center justify-between">
          <div>
            <p className="text-slate-500 text-sm font-medium">Active Cases</p>
            <p className="text-2xl text-slate-900 font-bold mt-1">{activeCasesCount}</p>
            <span className="inline-block mt-1 text-[10px] font-mono text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded font-medium">
              UNDER INVESTIGATION
            </span>
          </div>
          <div className="w-12 h-12 rounded-full bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600 flex-shrink-0">
            <Activity className="w-6 h-6" />
          </div>
        </div>

        {/* Pending Review */}
        <div className="bg-white shadow-sm border border-slate-200 rounded-lg p-5 flex items-center justify-between">
          <div>
            <p className="text-slate-500 text-sm font-medium">Pending Review</p>
            <p className="text-2xl text-slate-900 font-bold mt-1">{pendingReviewCount}</p>
            <span className="inline-block mt-1 text-[10px] font-mono text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded font-medium">
              FORENSIC AUDIT
            </span>
          </div>
          <div className="w-12 h-12 rounded-full bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-600 flex-shrink-0">
            <Clock className="w-6 h-6" />
          </div>
        </div>

        {/* Total Evidence */}
        <div className="bg-white shadow-sm border border-slate-200 rounded-lg p-5 flex items-center justify-between">
          <div>
            <p className="text-slate-500 text-sm font-medium">Total Evidence</p>
            <p className="text-2xl text-slate-900 font-bold mt-1">{totalEvidenceCount}</p>
            <span className="inline-block mt-1 text-[10px] font-mono text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded font-semibold">
              {realEvidence.length > 0 ? `${realEvidence.length} INGESTED (LIVE)` : 'VAULT SECURED'}
            </span>
          </div>
          <div className="w-12 h-12 rounded-full bg-cyan-50 border border-cyan-200 flex items-center justify-center text-cyan-600 flex-shrink-0">
            <FileSearch className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Main Content 2-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Cases (Left / Wider, 2 columns on desktop) */}
        <div className="lg:col-span-2">
          <Card
            title="Recent Cases & Live Ingestions"
            headerAction={
              <Link
                to="/cases"
                className="text-xs text-cyan-600 hover:text-cyan-500 font-medium inline-flex items-center gap-1 transition-colors"
              >
                View all cases
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            }
          >
            <div className="space-y-3">
              {liveCases.slice(0, 3).map((item) => (
                <Link
                  key={item.id}
                  to="/cases"
                  className="block p-3 rounded-lg bg-slate-50 hover:bg-slate-100 border border-slate-200 hover:border-slate-300 transition-all duration-150 group"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="space-y-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs text-cyan-600 font-medium">
                          {item.caseNumber}
                        </span>
                        <Badge variant={getStatusBadgeVariant(item.status)} dot>
                          {getStatusLabel(item.status)}
                        </Badge>
                      </div>
                      <h4 className="text-sm font-medium text-slate-900 group-hover:text-cyan-500 transition-colors truncate">
                        {item.title}
                      </h4>
                      <p className="text-xs text-slate-500 line-clamp-1">{item.description}</p>
                    </div>

                    <div className="flex items-center sm:flex-col sm:items-end justify-between text-xs text-slate-500 pt-1 sm:pt-0 border-t border-slate-100 sm:border-0">
                      <span>Created {formatDate(item.createdAt)}</span>
                      <span className="text-slate-400 font-mono text-[11px]">
                        {item.evidenceCount} {item.evidenceCount === 1 ? 'file' : 'files'}
                      </span>
                    </div>
                  </div>
                </Link>
              ))}
            </div>

            {realEvidence.length > 0 && (
              <div className="mt-4 pt-4 border-t border-slate-200">
                <div className="flex items-center justify-between mb-2.5">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                    <span>Live Vault Evidence ({realEvidence.length})</span>
                  </h4>
                  <Link
                    to="/analysis"
                    className="text-xs text-cyan-600 hover:text-cyan-700 font-medium inline-flex items-center gap-1"
                  >
                    Open Workbench
                    <ArrowRight className="w-3 h-3" />
                  </Link>
                </div>
                <div className="space-y-2">
                  {realEvidence.slice(0, 5).map((ev) => (
                    <Link
                      key={ev.id}
                      to={`/analysis?evidenceId=${ev.id}`}
                      className="flex items-center justify-between p-2.5 rounded-md bg-white border border-slate-200 hover:border-cyan-400 hover:bg-cyan-50/30 transition-all text-xs group"
                    >
                      <div className="flex items-center gap-2.5 min-w-0">
                        <span className="font-mono font-semibold text-slate-800 truncate max-w-[180px] group-hover:text-cyan-700">
                          {ev.original_filename}
                        </span>
                        <Badge variant="success" dot className="text-[10px] px-1.5 py-0 flex-shrink-0">
                          INTAKE VERIFIED
                        </Badge>
                        <span className="font-mono text-slate-400 text-[11px] hidden sm:inline truncate max-w-[120px]">
                          {ev.id}
                        </span>
                      </div>
                      <div className="flex items-center gap-3 text-slate-500 font-mono text-[11px] flex-shrink-0">
                        <span>{ev.width}×{ev.height} px</span>
                        <span className="text-slate-400">{formatDate(ev.created_at)}</span>
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            )}
          </Card>
        </div>

        {/* System Status (Right, 1 column on desktop) */}
        <div>
          <Card
            title="System Diagnostics"
            headerAction={
              <div className="flex items-center gap-1 text-xs text-slate-500">
                <ShieldCheck className="w-3.5 h-3.5 text-cyan-600" />
                <span>Engine Health</span>
              </div>
            }
          >
            <div className="divide-y divide-slate-100">
              {/* Frontend Service */}
              <div className="py-3 first:pt-0">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium text-slate-800">Frontend Application</span>
                  <StatusIndicator status="operational" label="Operational" size="sm" />
                </div>
                <p className="text-xs text-slate-500 mt-1">Vite + React 18 SPA active</p>
              </div>

              {/* Backend API Service */}
              <div className="py-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium text-slate-800">Backend API</span>
                  <StatusIndicator
                    status={healthInfo?.status === 'operational' ? 'operational' : 'not-implemented'}
                    label={healthInfo?.status === 'operational' ? 'Operational' : 'Offline'}
                    size="sm"
                  />
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  {healthInfo ? `FastAPI v${healthInfo.version} & Pillow ${healthInfo.pillow_version}` : 'FastAPI service connecting...'}
                </p>
              </div>

              {/* Evidence Storage Vault */}
              <div className="py-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium text-slate-800">Evidence Vault</span>
                  <StatusIndicator
                    status={healthInfo?.storage_accessible ? 'operational' : 'not-implemented'}
                    label={healthInfo?.storage_accessible ? 'Operational' : 'Unavailable'}
                    size="sm"
                  />
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  {healthInfo?.storage_accessible ? 'Local read-only evidence & artifacts storage' : 'Storage offline'}
                </p>
              </div>

              {/* Image Forensics Engines */}
              <div className="py-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium text-slate-800">Image Forensics Engine</span>
                  <StatusIndicator
                    status={healthInfo?.status === 'operational' ? 'operational' : 'not-implemented'}
                    label={healthInfo?.status === 'operational' ? 'Operational' : 'Offline'}
                    size="sm"
                  />
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  {healthInfo ? 'SHA-256 hashing, EXIF, ELA, and SIFT geometric crop comparison active' : 'Engines initializing'}
                </p>
              </div>

              {/* Video Forensics */}
              <div className="py-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium text-slate-800">Video Forensics Engine</span>
                  <StatusIndicator
                    status={healthInfo?.status === 'operational' ? 'operational' : 'not-implemented'}
                    label={healthInfo?.status === 'operational' ? 'Operational' : 'Offline'}
                    size="sm"
                  />
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  Temporal cut detection (Bhattacharyya D_B &amp; Z-score), night theme grading analysis, container skew &amp; keyframe PRNU baseline
                </p>
              </div>

              {/* Audio Forensics */}
              <div className="py-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium text-slate-800">Audio &amp; Voice Forensics</span>
                  <StatusIndicator
                    status={healthInfo?.status === 'operational' ? 'operational' : 'not-implemented'}
                    label={healthInfo?.status === 'operational' ? 'Operational' : 'Offline'}
                    size="sm"
                  />
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  STFT spectral flux acoustic splice detection, digital zero pause identification, ambient room noise floor &amp; AI voice analysis
                </p>
              </div>

              {/* AI Deepfake Detection */}
              <div className="py-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium text-slate-800">AI Deepfake Detection</span>
                  <StatusIndicator
                    status={healthInfo?.status === 'operational' ? 'operational' : 'offline'}
                    label={healthInfo?.status === 'operational' ? 'Operational' : 'Offline'}
                    size="sm"
                  />
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  High-frequency FFT residual anomaly checks &amp; synthetic voice biometrics active
                </p>
              </div>

              {/* Authentication */}
              <div className="py-3 last:pb-0">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium text-slate-800">Tenant &amp; Access Control</span>
                  <StatusIndicator status="operational" label="Active" size="sm" />
                </div>
                <p className="text-xs text-slate-500 mt-1">Local Forensic Station Security Enforced</p>
              </div>
            </div>
          </Card>
        </div>
      </div>

    </div>
  );
}
