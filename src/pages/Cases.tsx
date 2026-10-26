// Garuda Law Enforcement Case Management
// Operational evidence case tracking, drill-down vault inspection, and multi-modal digital forensics registry.

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Plus,
  X,
  FolderPlus,
  FolderOpen,
  Eye,
  FileImage,
  Video,
  Mic,
  ArrowRight,
  ShieldAlert,
} from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { DEMO_CASES } from '@/data/demo';
import { formatDate, formatFileSize } from '@/utils/formatters';
import { api, type ApiCase, type ApiEvidence } from '@/api/client';
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

function getPriorityBadgeVariant(priority: CasePriority): 'error' | 'warning' | 'info' | 'neutral' {
  switch (priority) {
    case 'critical':
      return 'error';
    case 'high':
      return 'warning';
    case 'medium':
      return 'info';
    case 'low':
    default:
      return 'neutral';
  }
}

function mapApiCase(c: ApiCase): Case {
  return {
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
  };
}

export function Cases() {
  const navigate = useNavigate();
  const [casesList, setCasesList] = useState<Case[]>(DEMO_CASES);
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedCase, setSelectedCase] = useState<Case | null>(null);
  const [caseEvidence, setCaseEvidence] = useState<ApiEvidence[]>([]);
  const [isLoadingEvidence, setIsLoadingEvidence] = useState(false);

  const [newCaseNumber, setNewCaseNumber] = useState('');
  const [newTitle, setNewTitle] = useState('');
  const [newCategory, setNewCategory] = useState<'Image Forensics' | 'Video Forensics' | 'Audio Forensics'>('Image Forensics');
  const [newPriority, setNewPriority] = useState<'low' | 'medium' | 'high'>('high');
  const [newDescription, setNewDescription] = useState('');
  const [newInvestigator, setNewInvestigator] = useState('Inspector S. Verma');
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    async function loadCases() {
      try {
        const liveCases = await api.listCases();
        if (liveCases && liveCases.length > 0) {
          setCasesList(liveCases.map(mapApiCase));
        }
      } catch {
        // Fall back gracefully to initialized list
      }
    }
    loadCases();
  }, []);

  const handleSelectCase = async (c: Case) => {
    setSelectedCase(c);
    setIsLoadingEvidence(true);
    setCaseEvidence([]);
    try {
      const items = await api.listCaseEvidence(c.id);
      setCaseEvidence(items);
    } catch {
      // If error or empty, keep empty array
    } finally {
      setIsLoadingEvidence(false);
    }
  };

  const handleCreateCase = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCaseNumber.trim() || !newTitle.trim()) return;

    setIsSubmitting(true);
    try {
      const created = await api.createCase({
        case_number: newCaseNumber.trim(),
        title: newTitle.trim(),
        description: newDescription.trim() || 'Digital forensics case intake for chain of custody and artifact analysis.',
        priority: newPriority,
        category: newCategory,
        assigned_to: [newInvestigator.trim() || 'Forensic Examiner'],
        organization_id: 'State Cyber Crime Investigation Division',
      });

      setCasesList((prev) => [mapApiCase(created), ...prev]);

      // Reset and close
      setNewCaseNumber('');
      setNewTitle('');
      setNewDescription('');
      setIsModalOpen(false);
    } catch {
      // Local fallback in case network fails
      const fallbackCase: Case = {
        id: `case-bih-${Date.now()}`,
        caseNumber: newCaseNumber.trim(),
        title: newTitle.trim(),
        description: newDescription.trim() || 'Digital forensics case intake for chain of custody and artifact analysis.',
        status: 'open',
        priority: newPriority,
        category: newCategory,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        evidenceCount: 0,
        assignedTo: [newInvestigator.trim() || 'Forensic Examiner'],
        organizationId: 'State Cyber Crime Investigation Division',
      };
      setCasesList((prev) => [fallbackCase, ...prev]);
      setNewCaseNumber('');
      setNewTitle('');
      setNewDescription('');
      setIsModalOpen(false);
    } finally {
      setIsSubmitting(false);
    }
  };

  const filteredCases = casesList.filter((c) => {
    if (filterStatus === 'all') return true;
    return c.status === filterStatus;
  });

  const getEvidenceIcon = (mime: string) => {
    if (mime.startsWith('video/')) return <Video className="w-4 h-4 text-indigo-600" />;
    if (mime.startsWith('audio/')) return <Mic className="w-4 h-4 text-purple-600" />;
    return <FileImage className="w-4 h-4 text-cyan-600" />;
  };

  const openEvidenceWorkbench = (ev: ApiEvidence) => {
    if (ev.mime_type.startsWith('video/')) {
      navigate(`/video?evidenceId=${ev.id}`);
    } else if (ev.mime_type.startsWith('audio/')) {
      navigate(`/audio?evidenceId=${ev.id}`);
    } else {
      navigate(`/analysis?evidenceId=${ev.id}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-semibold text-slate-900 tracking-tight">Cases</h1>
          <p className="text-sm text-slate-500 mt-1">
            Manage forensic investigation cases, FIR registries, and linked evidence items
          </p>
        </div>
        <Button
          variant="primary"
          size="sm"
          onClick={() => setIsModalOpen(true)}
          leftIcon={<Plus className="w-4 h-4" />}
        >
          New Case
        </Button>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
        {[
          { key: 'all', label: 'All Cases', count: casesList.length },
          { key: 'open', label: 'Open', count: casesList.filter((c) => c.status === 'open').length },
          { key: 'in-progress', label: 'In Progress', count: casesList.filter((c) => c.status === 'in-progress').length },
          { key: 'pending-review', label: 'Pending Review', count: casesList.filter((c) => c.status === 'pending-review').length },
          { key: 'closed', label: 'Closed', count: casesList.filter((c) => c.status === 'closed').length },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setFilterStatus(tab.key)}
            className={`px-3 py-1.5 rounded-md font-medium transition-all whitespace-nowrap flex items-center gap-1.5 ${
              filterStatus === tab.key
                ? 'bg-slate-900 text-white shadow-xs'
                : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
            }`}
          >
            <span>{tab.label}</span>
            <span
              className={`text-[10px] px-1.5 py-0.2 rounded-full ${
                filterStatus === tab.key ? 'bg-slate-800 text-slate-300' : 'bg-slate-100 text-slate-600'
              }`}
            >
              {tab.count}
            </span>
          </button>
        ))}
      </div>

      {/* Case Creation Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 max-w-lg w-full p-6 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <FolderPlus className="w-5 h-5 text-cyan-600" />
                <h3 className="text-base font-semibold text-slate-900">Initiate Forensic Case</h3>
              </div>
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 transition-colors p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateCase} className="space-y-4 mt-4">
              <Input
                label="Case / FIR Identifier"
                placeholder="e.g. FIR-2026-112/CYBER"
                value={newCaseNumber}
                onChange={(e) => setNewCaseNumber(e.target.value)}
                required
              />

              <Input
                label="Case Subject / Title"
                placeholder="e.g. Altered Financial Record & Signature Examination"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                required
              />

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    Forensic Modality
                  </label>
                  <select
                    value={newCategory}
                    onChange={(e) => setNewCategory(e.target.value as 'Image Forensics' | 'Video Forensics' | 'Audio Forensics')}
                    className="w-full text-xs rounded-md border border-slate-200 px-3 py-2 bg-white text-slate-800 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                  >
                    <option value="Image Forensics">Image Forensics</option>
                    <option value="Video Forensics">Video Forensics</option>
                    <option value="Audio Forensics">Audio Forensics</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    Priority Level
                  </label>
                  <select
                    value={newPriority}
                    onChange={(e) => setNewPriority(e.target.value as 'low' | 'medium' | 'high')}
                    className="w-full text-xs rounded-md border border-slate-200 px-3 py-2 bg-white text-slate-800 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                  >
                    <option value="high">High Priority</option>
                    <option value="medium">Medium Priority</option>
                    <option value="low">Standard</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Investigation Summary
                </label>
                <textarea
                  rows={3}
                  placeholder="Summary of allegations, seized media source, or court order details..."
                  value={newDescription}
                  onChange={(e) => setNewDescription(e.target.value)}
                  className="w-full text-xs rounded-md border border-slate-200 p-2.5 bg-white text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-cyan-500"
                />
              </div>

              <Input
                label="Assigned Forensic Examiner"
                placeholder="e.g. Inspector S. Verma"
                value={newInvestigator}
                onChange={(e) => setNewInvestigator(e.target.value)}
              />

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => setIsModalOpen(false)}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  size="sm"
                  disabled={!newCaseNumber.trim() || !newTitle.trim() || isSubmitting}
                >
                  {isSubmitting ? 'Creating Case...' : 'Create Case Record'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Case Details & Evidence Drawer Modal */}
      {selectedCase && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 max-w-3xl w-full p-6 max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <FolderOpen className="w-5 h-5 text-cyan-600" />
                <div>
                  <h3 className="text-base font-semibold text-slate-900 flex items-center gap-2">
                    <span>{selectedCase.caseNumber}</span>
                    <Badge variant={getStatusBadgeVariant(selectedCase.status)} dot>
                      {getStatusLabel(selectedCase.status)}
                    </Badge>
                  </h3>
                  <p className="text-xs text-slate-500">{selectedCase.title}</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setSelectedCase(null)}
                className="text-slate-400 hover:text-slate-600 transition-colors p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="py-4 space-y-4 overflow-y-auto flex-1 text-xs">
              {/* Summary attributes */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-50 p-3 rounded-lg border border-slate-200">
                <div>
                  <span className="text-slate-500 block">Modality</span>
                  <span className="font-semibold text-slate-800">{selectedCase.category}</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Priority</span>
                  <Badge variant={getPriorityBadgeVariant(selectedCase.priority)}>
                    {selectedCase.priority.toUpperCase()}
                  </Badge>
                </div>
                <div>
                  <span className="text-slate-500 block">Assigned Examiner</span>
                  <span className="font-medium text-slate-800 truncate block">
                    {selectedCase.assignedTo?.join(', ') || 'Unassigned'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 block">Registered</span>
                  <span className="text-slate-700">{formatDate(selectedCase.createdAt)}</span>
                </div>
              </div>

              {selectedCase.description && (
                <div className="p-3 bg-white border border-slate-200 rounded-lg">
                  <span className="text-slate-500 block font-semibold mb-1">Investigation Scope</span>
                  <p className="text-slate-700 leading-relaxed">{selectedCase.description}</p>
                </div>
              )}

              {/* Linked Evidence Section */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <h4 className="font-semibold text-slate-900 flex items-center gap-1.5">
                    <ShieldAlert className="w-4 h-4 text-cyan-600" />
                    <span>Evidence Items Deposited in this Case ({caseEvidence.length})</span>
                  </h4>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => navigate('/intake')}
                    leftIcon={<Plus className="w-3.5 h-3.5" />}
                  >
                    Deposit New Evidence
                  </Button>
                </div>

                {isLoadingEvidence ? (
                  <div className="p-8 text-center text-slate-400">Loading case evidence items...</div>
                ) : caseEvidence.length === 0 ? (
                  <div className="p-6 text-center bg-slate-50 border border-dashed border-slate-300 rounded-lg text-slate-500">
                    <p>No evidence files currently linked to this case identifier.</p>
                    <p className="text-[11px] text-slate-400 mt-1">
                      Go to Evidence Intake to deposit and SHA-256 seal media under {selectedCase.caseNumber}.
                    </p>
                  </div>
                ) : (
                  <div className="border border-slate-200 rounded-lg overflow-hidden">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-50 text-slate-500 uppercase font-medium border-b border-slate-200">
                        <tr>
                          <th className="px-3 py-2">Evidence</th>
                          <th className="px-3 py-2">Intake SHA-256</th>
                          <th className="px-3 py-2">Size</th>
                          <th className="px-3 py-2 text-right">Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {caseEvidence.map((ev) => (
                          <tr key={ev.id} className="hover:bg-slate-50 transition-colors">
                            <td className="px-3 py-2.5">
                              <div className="flex items-center gap-2">
                                {getEvidenceIcon(ev.mime_type)}
                                <div className="min-w-0">
                                  <p className="font-semibold text-slate-800 truncate">{ev.original_filename}</p>
                                  <p className="text-[10px] font-mono text-slate-400">{ev.id}</p>
                                </div>
                              </div>
                            </td>
                            <td className="px-3 py-2.5 font-mono text-slate-500">
                              <span title={ev.sha256_intake}>
                                {ev.sha256_intake.slice(0, 14)}...{ev.sha256_intake.slice(-8)}
                              </span>
                            </td>
                            <td className="px-3 py-2.5 text-slate-600 font-mono">
                              {formatFileSize(ev.file_size)}
                            </td>
                            <td className="px-3 py-2.5 text-right">
                              <Button
                                variant="primary"
                                size="sm"
                                leftIcon={<ArrowRight className="w-3.5 h-3.5" />}
                                onClick={() => openEvidenceWorkbench(ev)}
                              >
                                Examine
                              </Button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>

            <div className="pt-3 border-t border-slate-100 flex justify-end">
              <Button variant="secondary" size="sm" onClick={() => setSelectedCase(null)}>
                Close Details
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Cases Table Card */}
      <Card
        title="All Cases"
        headerAction={
          <span className="text-xs text-slate-500 font-mono">
            {filteredCases.length} of {casesList.length} cases shown
          </span>
        }
      >
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500 uppercase font-medium border-b border-slate-200">
              <tr>
                <th className="px-4 py-3">Case ID</th>
                <th className="px-4 py-3">Title</th>
                <th className="px-4 py-3">Modality</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Priority</th>
                <th className="px-4 py-3">Evidence</th>
                <th className="px-4 py-3">Created</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredCases.map((c) => (
                <tr
                  key={c.id}
                  onClick={() => handleSelectCase(c)}
                  className="hover:bg-cyan-50/40 cursor-pointer transition-colors"
                >
                  <td className="px-4 py-3 font-mono font-medium text-cyan-700 whitespace-nowrap">
                    {c.caseNumber}
                  </td>
                  <td className="px-4 py-3">
                    <div className="font-medium text-slate-900">{c.title}</div>
                    <div className="text-[11px] text-slate-500 line-clamp-1 mt-0.5">{c.description}</div>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 text-[11px] font-medium">
                      {c.category}
                    </span>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <Badge variant={getStatusBadgeVariant(c.status)} dot>
                      {getStatusLabel(c.status)}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <Badge variant={getPriorityBadgeVariant(c.priority)}>
                      {c.priority.toUpperCase()}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-slate-700 font-mono whitespace-nowrap">
                    {c.evidenceCount} {c.evidenceCount === 1 ? 'item' : 'items'}
                  </td>
                  <td className="px-4 py-3 text-slate-500 whitespace-nowrap">
                    {formatDate(c.createdAt)}
                  </td>
                  <td className="px-4 py-3 text-right whitespace-nowrap">
                    <Button
                      variant="ghost"
                      size="sm"
                      leftIcon={<Eye className="w-3.5 h-3.5" />}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleSelectCase(c);
                      }}
                    >
                      View
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-4 pt-3 border-t border-slate-100">
          <p className="text-xs text-slate-500">
            Click on any case record to inspect linked evidence items, or navigate to Image, Video, or Audio Analysis to examine ingested evidence under Section 65B Indian Evidence Act / BSA 2023.
          </p>
        </div>
      </Card>
    </div>
  );
}
