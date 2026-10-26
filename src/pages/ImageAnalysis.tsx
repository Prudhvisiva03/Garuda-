import { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import {
  Image as ImageIcon,
  Play,
  ArrowLeft,
  Sliders,
  ShieldCheck,
  ShieldAlert,
  Info,
  CheckCircle2,
  RefreshCw,
  Download,
  AlertCircle,
  ExternalLink,
  GitCompare,
} from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Tabs } from '@/components/ui/Tabs';
import { StatusIndicator } from '@/components/ui/StatusIndicator';
import { EmptyState } from '@/components/ui/EmptyState';
import { ImageComparisonWorkbench } from '@/components/ImageComparisonWorkbench';
import { formatFileSize, formatDate } from '@/utils/formatters';
import { api, type ApiEvidence, type ApiFullAnalysis, type ApiIntegrityCheck } from '@/api/client';

export function ImageAnalysis() {
  const [searchParams, setSearchParams] = useSearchParams();
  const queryEvidenceId = searchParams.get('evidenceId');
  const queryMode = searchParams.get('mode');
  const queryRefId = searchParams.get('referenceId');
  const queryCandId = searchParams.get('candidateId');

  const [workbenchMode, setWorkbenchMode] = useState<'single' | 'compare'>(
    queryMode === 'compare' ? 'compare' : 'single'
  );

  const handleModeChange = (mode: 'single' | 'compare') => {
    setWorkbenchMode(mode);
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (mode === 'compare') {
        next.set('mode', 'compare');
      } else {
        next.delete('mode');
      }
      return next;
    });
  };

  const [activeTab, setActiveTab] = useState('ela');
  const [evidenceList, setEvidenceList] = useState<ApiEvidence[]>([]);
  const [selectedEvidence, setSelectedEvidence] = useState<ApiEvidence | null>(null);
  const [analysisData, setAnalysisData] = useState<ApiFullAnalysis | null>(null);

  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isVerifyingHash, setIsVerifyingHash] = useState(false);
  const [integrityStatus, setIntegrityStatus] = useState<ApiIntegrityCheck | null>(null);
  const [isDownloadingReport, setIsDownloadingReport] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // ELA parameters
  const [elaQuality, setElaQuality] = useState(95);
  const elaScale = 15;

  // Load available evidence list on mount
  useEffect(() => {
    async function loadEvidence() {
      try {
        const items = await api.listEvidence();
        // Filter strictly to image MIME types (excludes video/audio files)
        const imageItems = items.filter((it) => it.mime_type.startsWith('image/'));
        setEvidenceList(imageItems);

        if (imageItems.length > 0) {
          if (queryEvidenceId) {
            const found = imageItems.find((it) => it.id === queryEvidenceId);
            setSelectedEvidence(found || imageItems[0]);
          } else {
            setSelectedEvidence(imageItems[0]);
          }
        } else {
          setSelectedEvidence(null);
        }
      } catch (err) {
        console.warn('Backend not accessible:', err);
      }
    }
    loadEvidence();
  }, [queryEvidenceId]);

  // Load existing analysis if evidence changes (prevents stale results)
  useEffect(() => {
    if (!selectedEvidence) {
      setAnalysisData(null);
      setIntegrityStatus(null);
      return;
    }

    // Reset previous findings immediately to prevent stale state bleed
    setAnalysisData(null);
    setIntegrityStatus(null);
    setErrorMessage(null);

    async function fetchExistingAnalysis() {
      if (!selectedEvidence) return;
      try {
        const existing = await api.getAnalysis(selectedEvidence.id);
        setAnalysisData(existing);
        setIntegrityStatus(existing.integrity);
      } catch {
        // Analysis not yet run for this item; keep clean empty state
      }
    }

    fetchExistingAnalysis();
  }, [selectedEvidence]);

  // Handle manual evidence change
  const handleSelectEvidence = (evId: string) => {
    const item = evidenceList.find((e) => e.id === evId);
    if (item) {
      setSelectedEvidence(item);
      setSearchParams({ evidenceId: evId });
    }
  };

  // Run full analysis
  const handleRunAnalysis = async () => {
    if (!selectedEvidence) return;

    setIsAnalyzing(true);
    setErrorMessage(null);

    try {
      const result = await api.runAnalysis(selectedEvidence.id, elaQuality, elaScale);
      setAnalysisData(result);
      setIntegrityStatus(result.integrity);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Analysis failed to execute.';
      setErrorMessage(msg);
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Cryptographic hash re-check
  const handleVerifyHash = async () => {
    if (!selectedEvidence) return;

    setIsVerifyingHash(true);
    setErrorMessage(null);

    try {
      const result = await api.verifyHash(selectedEvidence.id);
      setIntegrityStatus(result);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Hash verification failed.';
      setErrorMessage(msg);
    } finally {
      setIsVerifyingHash(false);
    }
  };

  // Download PDF Report
  const handleDownloadReport = async () => {
    if (!selectedEvidence) return;

    setIsDownloadingReport(true);
    setErrorMessage(null);

    try {
      // Ensure report is generated
      await api.generateReport(selectedEvidence.id);
      const downloadUrl = api.getReportDownloadUrl(selectedEvidence.id);
      window.open(downloadUrl, '_blank');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to generate report.';
      setErrorMessage(msg);
    } finally {
      setIsDownloadingReport(false);
    }
  };

  // Real evidence state
  const isRealEvidence = Boolean(selectedEvidence);
  const currentFileName = selectedEvidence?.original_filename || 'No Evidence Loaded';
  const currentUploadDate = selectedEvidence?.created_at || '';
  const currentDimensions = selectedEvidence?.width && selectedEvidence?.height
    ? `${selectedEvidence.width} × ${selectedEvidence.height} px`
    : 'Unknown Dimensions';
  const currentFileSize = selectedEvidence?.file_size || 0;
  const currentMime = selectedEvidence?.mime_type || 'image/jpeg';
  const currentHash = selectedEvidence?.sha256_intake || null;

  const analysisTabs = [
    { id: 'ela', label: 'Error Level Analysis (ELA)' },
    {
      id: 'noise',
      label: 'Spatial Noise & Features',
    },
    {
      id: 'copy-move',
      label: 'Copy-Move Matching',
      disabled: true,
      disabledReason: 'Integrated directly into Spatial Noise & Feature analysis',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Workbench Header & Mode Navigation Bar */}
      <div className="bg-white border border-slate-200 rounded-lg p-4 sm:p-5 shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h1 className="text-xl sm:text-2xl font-semibold text-slate-900 tracking-tight">
              Image Analysis Workbench
            </h1>
            <p className="text-xs sm:text-sm text-slate-500 mt-1">
              Deterministic computer-vision examination, Error Level Analysis, and geometric feature correspondence
            </p>
          </div>

          <Link
            to="/evidence"
            className="text-xs text-cyan-600 hover:text-cyan-700 font-medium inline-flex items-center gap-1.5 self-start sm:self-auto bg-slate-50 hover:bg-slate-100 px-3 py-1.5 rounded-md border border-slate-200 transition-colors"
          >
            <span>+ Upload Evidence to Vault</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </Link>
        </div>

        {/* Mode Selector Tabs */}
        <div className="flex border-b border-slate-200 pt-2">
          <button
            type="button"
            onClick={() => handleModeChange('single')}
            className={`flex items-center gap-2 py-2.5 px-4 text-xs sm:text-sm font-semibold border-b-2 transition-colors ${
              workbenchMode === 'single'
                ? 'border-cyan-600 text-cyan-700 bg-cyan-50/30'
                : 'border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300'
            }`}
          >
            <ImageIcon className="w-4 h-4" />
            <span>Single Evidence Forensics</span>
            <span className="text-[11px] font-normal text-slate-400 hidden md:inline">
              (ELA, Noise, EXIF, Hash)
            </span>
          </button>

          <button
            type="button"
            onClick={() => handleModeChange('compare')}
            className={`flex items-center gap-2 py-2.5 px-4 text-xs sm:text-sm font-semibold border-b-2 transition-colors ${
              workbenchMode === 'compare'
                ? 'border-cyan-600 text-cyan-700 bg-cyan-50/30'
                : 'border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300'
            }`}
          >
            <GitCompare className="w-4 h-4" />
            <span>Original vs Cropped Comparison</span>
            <Badge variant="info" className="text-[10px] uppercase font-mono hidden sm:inline-flex">
              SIFT + RANSAC
            </Badge>
          </button>
        </div>
      </div>

      {workbenchMode === 'compare' ? (
        <ImageComparisonWorkbench
          evidenceList={evidenceList}
          initialReferenceId={queryRefId || selectedEvidence?.id}
          initialCandidateId={queryCandId}
        />
      ) : evidenceList.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-lg p-10 text-center shadow-xs">
          <div className="w-14 h-14 rounded-2xl bg-cyan-50 border border-cyan-200 flex items-center justify-center text-cyan-600 mx-auto mb-4">
            <ImageIcon className="w-7 h-7" />
          </div>
          <h3 className="text-base font-semibold text-slate-900">No Image Evidence in Vault</h3>
          <p className="text-xs sm:text-sm text-slate-500 mt-1.5 max-w-md mx-auto">
            Upload authentic photographic evidence (JPEG, PNG) at the Evidence Intake Desk to run deterministic Error Level Analysis (ELA), noise residual extraction, and court-admissible Section 65B forensic reports.
          </p>
          <div className="mt-5 flex items-center justify-center gap-3">
            <Link to="/evidence">
              <Button variant="primary" size="sm" leftIcon={<ExternalLink className="w-3.5 h-3.5" />}>
                Go to Evidence Intake Desk
              </Button>
            </Link>
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Evidence Selector Bar */}
      {evidenceList.length > 0 && (
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 bg-white border border-slate-200 rounded-lg shadow-xs text-xs">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-700">Select Ingested Evidence:</span>
            <select
              value={selectedEvidence?.id || ''}
              onChange={(e) => handleSelectEvidence(e.target.value)}
              className="px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded font-mono text-slate-800 text-xs focus:ring-1 focus:ring-cyan-500"
            >
              {evidenceList.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.original_filename} ({e.id}) &bull; {e.mime_type}
                </option>
              ))}
            </select>
          </div>

          <Link
            to="/evidence"
            className="text-cyan-600 hover:text-cyan-700 font-medium inline-flex items-center gap-1 self-start sm:self-auto"
          >
            <span>+ Upload New Evidence</span>
            <ExternalLink className="w-3 h-3" />
          </Link>
        </div>
      )}

      {/* Error alert */}
      {errorMessage && (
        <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-red-700 flex items-start gap-3 text-sm">
          <AlertCircle className="w-5 h-5 flex-shrink-0 text-red-600 mt-0.5" />
          <div>
            <p className="font-semibold text-red-800">Operation Error</p>
            <p>{errorMessage}</p>
          </div>
        </div>
      )}

      {/* Evidence Header Bar */}
      <div className="bg-white shadow-sm border border-slate-200 rounded-lg p-4 sm:p-5">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="space-y-1.5 min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-base font-semibold text-slate-900 truncate">
                {currentFileName}
              </span>
              <Badge variant={isRealEvidence ? 'success' : 'neutral'} dot className="text-[10px] px-1.5 py-0">
                {isRealEvidence ? 'INTAKE VERIFIED' : 'VAULT REPOSITORY'}
              </Badge>
              <Badge variant={analysisData ? 'success' : 'neutral'} dot>
                {analysisData ? 'Analysis Completed' : 'Not Analyzed'}
              </Badge>
            </div>

            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
              <div className="flex items-center gap-1.5">
                <span>Case:</span>
                <span className="font-medium text-slate-700">
                  {selectedEvidence?.case_id || 'General Forensic Intake'}
                </span>
              </div>
              <span className="text-slate-300 hidden sm:inline">•</span>
              <div>
                <span>Uploaded: </span>
                <span className="text-slate-700">{formatDate(currentUploadDate)}</span>
              </div>
              {selectedEvidence && (
                <>
                  <span className="text-slate-300 hidden sm:inline">•</span>
                  <div>
                    <span>Evidence ID: </span>
                    <span className="font-mono text-cyan-700 font-semibold">{selectedEvidence.id}</span>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Action Buttons Row */}
          <div className="flex flex-wrap items-center gap-2 sm:self-start lg:self-center">
            <Link to="/evidence">
              <Button
                variant="secondary"
                size="sm"
                leftIcon={<ArrowLeft className="w-3.5 h-3.5" />}
              >
                Intake Desk
              </Button>
            </Link>

            <Button
              variant="primary"
              size="sm"
              isLoading={isAnalyzing}
              disabled={!isRealEvidence || isAnalyzing}
              title={isRealEvidence ? 'Execute forensic analysis pipeline' : 'Upload real evidence through Intake first'}
              leftIcon={<Play className="w-3.5 h-3.5" />}
              onClick={handleRunAnalysis}
            >
              {isAnalyzing ? 'Analyzing Image...' : 'Run Analysis'}
            </Button>

            <Button
              variant="secondary"
              size="sm"
              isLoading={isDownloadingReport}
              disabled={!isRealEvidence || !analysisData}
              title={analysisData ? 'Download official examination PDF report' : 'Run analysis first to generate report'}
              leftIcon={<Download className="w-3.5 h-3.5" />}
              onClick={handleDownloadReport}
            >
              Download PDF Report
            </Button>
          </div>
        </div>
      </div>

      {/* 3-Panel Grid: Evidence Preview | Analysis Results | Metadata & Integrity */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        {/* LEFT PANEL - Evidence Preview */}
        <div>
          <Card
            title="Original Evidence"
            headerAction={
              <span className="text-[11px] font-mono text-slate-500 uppercase tracking-wider">
                {isRealEvidence ? 'Live Preview' : 'Placeholder'}
              </span>
            }
          >
            <div className="space-y-4">
              {/* Preview Box */}
              <div className="aspect-[4/3] bg-slate-50 border border-slate-200 rounded-lg flex flex-col items-center justify-center overflow-hidden">
                {selectedEvidence ? (
                  <img
                    src={api.getEvidenceFileUrl(selectedEvidence.id)}
                    alt={selectedEvidence.original_filename}
                    className="w-full h-full object-contain bg-slate-100"
                    loading="lazy"
                  />
                ) : (
                  <div className="p-6 text-center">
                    <div className="w-12 h-12 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-400 mb-3 mx-auto">
                      <ImageIcon className="w-6 h-6" />
                    </div>
                    <p className="text-sm font-medium text-slate-700">No evidence file loaded</p>
                    <p className="text-xs text-slate-400 mt-1 max-w-xs">
                      Upload genuine evidence through the Evidence Intake workflow to render visual preview.
                    </p>
                  </div>
                )}
              </div>

              {/* Evidence File Info Table */}
              <div className="border border-slate-100 rounded-md overflow-hidden bg-slate-50">
                <div className="px-3 py-2 bg-slate-100 border-b border-slate-100 text-xs font-medium text-slate-700 flex justify-between items-center">
                  <span>File Properties</span>
                  <span className="text-[10px] font-mono text-slate-500">
                    {isRealEvidence ? 'Intake Verified' : 'Vault Record'}
                  </span>
                </div>
                <dl className="divide-y divide-slate-100 text-xs">
                  <div className="px-3 py-2 flex justify-between">
                    <dt className="text-slate-500">File Name</dt>
                    <dd className="font-mono text-slate-800 truncate ml-2 max-w-[180px]">
                      {currentFileName}
                    </dd>
                  </div>
                  <div className="px-3 py-2 flex justify-between">
                    <dt className="text-slate-500">Validated Type</dt>
                    <dd className="font-mono text-slate-800">{currentMime}</dd>
                  </div>
                  <div className="px-3 py-2 flex justify-between">
                    <dt className="text-slate-500">Dimensions</dt>
                    <dd className="font-mono text-slate-800">{currentDimensions}</dd>
                  </div>
                  <div className="px-3 py-2 flex justify-between">
                    <dt className="text-slate-500">Size</dt>
                    <dd className="font-mono text-slate-800">{formatFileSize(currentFileSize)}</dd>
                  </div>
                </dl>
              </div>
            </div>
          </Card>
        </div>

        {/* CENTER PANEL - Analysis Results */}
        <div>
          <Card title="Analysis Visualizations">
            <div className="space-y-4">
              {/* Method Tabs */}
              <Tabs tabs={analysisTabs} activeTab={activeTab} onTabChange={setActiveTab} />

              {/* ELA TAB CONTENT */}
              {activeTab === 'ela' && (
                <div className="space-y-4">
                  {/* Result Visualization */}
                  <div className="aspect-[4/3] bg-slate-50 border border-slate-200 rounded-lg flex flex-col items-center justify-center overflow-hidden">
                    {analysisData?.ela.status === 'completed' && analysisData.ela.artifact_url ? (
                      <img
                        src={analysisData.ela.artifact_url}
                        alt="ELA Output Map"
                        className="w-full h-full object-contain bg-black"
                      />
                    ) : analysisData?.ela.status === 'unsupported' ? (
                      <div className="p-6 text-center space-y-2">
                        <Badge variant="neutral">Lossless Format (PNG)</Badge>
                        <p className="text-xs text-slate-600 max-w-xs mx-auto leading-relaxed">
                          {analysisData.ela.explanation}
                        </p>
                      </div>
                    ) : (
                      <div className="p-6 text-center">
                        <div className="w-12 h-12 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-400 mb-3 mx-auto">
                          <Sliders className="w-6 h-6" />
                        </div>
                        <p className="text-sm font-medium text-slate-700">Not analyzed</p>
                        <p className="text-xs text-slate-400 mt-1 max-w-xs">
                          {isRealEvidence
                            ? "Click 'Run Analysis' above to generate Error Level Analysis difference map."
                            : "Upload real evidence through Intake to run ELA analysis."}
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Analysis Parameters & Empirical Metrics */}
                  <div className="border border-slate-200 rounded-md p-3.5 bg-slate-50 space-y-2.5">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                        ELA Parameters
                      </h4>
                      {isRealEvidence && !isAnalyzing && (
                        <div className="flex items-center gap-2 text-xs">
                          <label className="text-slate-500">Quality:</label>
                          <select
                            value={elaQuality}
                            onChange={(e) => setElaQuality(Number(e.target.value))}
                            className="bg-white border border-slate-200 rounded px-1.5 py-0.5 text-xs text-slate-700"
                          >
                            <option value={90}>90</option>
                            <option value={95}>95 (Default)</option>
                            <option value={98}>98</option>
                          </select>
                        </div>
                      )}
                    </div>

                    <div className="space-y-1.5 text-xs">
                      <div className="flex items-center justify-between">
                        <span className="text-slate-500">JPEG Quality Factor</span>
                        <span className="font-mono text-slate-700">{elaQuality}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-slate-500">Visual Difference Scaling</span>
                        <span className="font-mono text-slate-700">{elaScale}x</span>
                      </div>
                      {analysisData?.ela.status === 'completed' && (
                        <>
                          <div className="flex items-center justify-between pt-1 border-t border-slate-100">
                            <span className="text-slate-500">Mean Compression Error</span>
                            <span className="font-mono font-bold text-cyan-700">
                              {analysisData.ela.mean_error}
                            </span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="text-slate-500">Peak Error Value</span>
                            <span className="font-mono text-slate-700">
                              {analysisData.ela.max_error}
                            </span>
                          </div>
                        </>
                      )}
                      <div className="flex items-center justify-between pt-1 border-t border-slate-100">
                        <span className="text-slate-500">Status</span>
                        <StatusIndicator
                          status={analysisData?.ela.status === 'completed' ? 'success' : 'neutral'}
                          label={
                            analysisData?.ela.status === 'completed'
                              ? 'Computed'
                              : analysisData?.ela.status === 'unsupported'
                              ? 'Unsupported Format'
                              : 'Not analyzed'
                          }
                          size="sm"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* NOISE & SPATIAL FEATURES TAB CONTENT */}
              {activeTab === 'noise' && (
                <div className="space-y-4">
                  <div className="border border-slate-200 rounded-md p-4 bg-slate-50 space-y-3">
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-600">
                      High-Frequency Noise Residual Variance
                    </h4>

                    {analysisData?.noise ? (
                      <div className="space-y-2 text-xs">
                        <div className="flex justify-between">
                          <span className="text-slate-500">Mean Residual Variance:</span>
                          <span className="font-mono font-bold text-slate-800">
                            {analysisData.noise.mean_residual_variance ?? 'N/A'}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-500">Regional Discrepancy Ratio:</span>
                          <span className="font-mono font-bold text-slate-800">
                            {analysisData.noise.variance_discrepancy_ratio ?? 'N/A'}
                          </span>
                        </div>
                        <div className="pt-2 border-t border-slate-200">
                          <p className="text-[11px] text-slate-600 leading-relaxed">
                            {analysisData.noise.explanation}
                          </p>
                        </div>
                      </div>
                    ) : (
                      <p className="text-xs text-slate-400 italic">
                        Run analysis to evaluate spatial noise decomposition and ORB descriptor matching.
                      </p>
                    )}
                  </div>
                </div>
              )}
            </div>
          </Card>
        </div>

        {/* RIGHT PANEL - Metadata & Integrity (scrollable) */}
        <div className="space-y-6">
          {/* File Integrity Card */}
          <Card
            title="Cryptographic Integrity"
            headerAction={
              integrityStatus?.matches ? (
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
              ) : (
                <ShieldAlert className="w-4 h-4 text-amber-600" />
              )
            }
          >
            <div className="space-y-3.5 text-xs">
              <div>
                <span className="text-slate-500 block mb-1">Authoritative Intake SHA-256</span>
                <div className="p-2 bg-slate-50 rounded border border-slate-200">
                  <code className="font-mono text-xs text-cyan-800 break-all select-all block">
                    {currentHash || 'Not calculated — backend not connected'}
                  </code>
                </div>
              </div>

              {integrityStatus && (
                <div className="p-2 rounded bg-emerald-50 border border-emerald-200 text-emerald-800 text-[11px] space-y-1">
                  <div className="flex items-center gap-1.5 font-semibold">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                    <span>{integrityStatus.status_label}</span>
                  </div>
                  <p className="text-emerald-700 leading-tight">{integrityStatus.message}</p>
                  <p className="text-[10px] text-emerald-600 font-mono">
                    Checked: {formatDate(integrityStatus.checked_at)}
                  </p>
                </div>
              )}

              <div className="flex items-center justify-between pt-1">
                <span className="text-slate-500">Hash Algorithm</span>
                <span className="font-mono text-slate-700">SHA-256 (FIPS 180-4)</span>
              </div>

              <div className="pt-2 border-t border-slate-100 flex justify-between items-center">
                <StatusIndicator
                  status={integrityStatus?.matches ? 'success' : isRealEvidence ? 'warning' : 'neutral'}
                  label={integrityStatus?.matches ? 'Verified' : 'Recheck pending'}
                  size="sm"
                />

                {isRealEvidence && (
                  <Button
                    variant="ghost"
                    size="sm"
                    isLoading={isVerifyingHash}
                    leftIcon={<RefreshCw className="w-3 h-3" />}
                    onClick={handleVerifyHash}
                  >
                    Re-verify Stored Hash
                  </Button>
                )}
              </div>
            </div>
          </Card>

          {/* Metadata Card */}
          <Card
            title="Metadata Inspector"
            headerAction={<Info className="w-4 h-4 text-slate-400" />}
          >
            <div className="space-y-3 text-xs">
              <dl className="divide-y divide-slate-100">
                <div className="py-2 first:pt-0 flex justify-between">
                  <dt className="text-slate-500">Camera Make</dt>
                  <dd className={analysisData?.metadata.make ? 'font-medium text-slate-800' : 'text-slate-400 italic'}>
                    {analysisData?.metadata.make || (isRealEvidence ? 'None recorded' : 'Not extracted yet')}
                  </dd>
                </div>
                <div className="py-2 flex justify-between">
                  <dt className="text-slate-500">Camera Model</dt>
                  <dd className={analysisData?.metadata.model ? 'font-medium text-slate-800' : 'text-slate-400 italic'}>
                    {analysisData?.metadata.model || (isRealEvidence ? 'None recorded' : 'Not extracted yet')}
                  </dd>
                </div>
                <div className="py-2 flex justify-between">
                  <dt className="text-slate-500">Date Taken</dt>
                  <dd className={analysisData?.metadata.datetime_original ? 'font-mono text-slate-800' : 'text-slate-400 italic'}>
                    {analysisData?.metadata.datetime_original || (isRealEvidence ? 'None recorded' : 'Not extracted yet')}
                  </dd>
                </div>
                <div className="py-2 flex justify-between">
                  <dt className="text-slate-500">GPS Location</dt>
                  <dd className={analysisData?.metadata.gps_lat ? 'font-mono text-cyan-700' : 'text-slate-400 italic'}>
                    {analysisData?.metadata.gps_lat
                      ? `${analysisData.metadata.gps_lat}, ${analysisData.metadata.gps_lon}`
                      : isRealEvidence
                      ? 'No GPS tags'
                      : 'Not extracted yet'}
                  </dd>
                </div>
                <div className="py-2 last:pb-0 flex justify-between">
                  <dt className="text-slate-500">Software Tag</dt>
                  <dd className={analysisData?.metadata.software ? 'font-medium text-amber-700' : 'text-slate-400 italic'}>
                    {analysisData?.metadata.software || (isRealEvidence ? 'None recorded' : 'Not extracted yet')}
                  </dd>
                </div>
              </dl>

              {analysisData?.metadata.raw_tags && Object.keys(analysisData.metadata.raw_tags).length > 0 && (
                <div className="pt-2 border-t border-slate-100">
                  <details className="text-[11px] text-slate-500">
                    <summary className="cursor-pointer font-medium hover:text-cyan-600">
                      View all {Object.keys(analysisData.metadata.raw_tags).length} raw EXIF tags
                    </summary>
                    <div className="mt-2 max-h-36 overflow-y-auto bg-slate-50 p-2 rounded border border-slate-200 font-mono text-[10px] space-y-1">
                      {Object.entries(analysisData.metadata.raw_tags).map(([k, v]) => (
                        <div key={k} className="truncate">
                          <span className="text-slate-600 font-bold">{k}:</span>{' '}
                          <span className="text-slate-800">{v}</span>
                        </div>
                      ))}
                    </div>
                  </details>
                </div>
              )}
            </div>
          </Card>
        </div>
      </div>

      {/* Findings Table Card */}
      <Card title="Analysis Findings & Empirical Observations">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500 uppercase font-medium border-b border-slate-200">
              <tr>
                <th className="px-4 py-3">Examination Test</th>
                <th className="px-4 py-3">Observed Result</th>
                <th className="px-4 py-3">Explanation</th>
                <th className="px-4 py-3">Method Limitations</th>
                <th className="px-4 py-3">Severity</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {analysisData && analysisData.findings.length > 0 ? (
                analysisData.findings.map((f) => (
                  <tr key={f.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-3 font-semibold text-slate-800 whitespace-nowrap">
                      {f.test_performed}
                    </td>
                    <td className="px-4 py-3 text-slate-700 font-medium">{f.observed_result}</td>
                    <td className="px-4 py-3 text-slate-600 leading-relaxed">{f.explanation}</td>
                    <td className="px-4 py-3 text-[11px] text-slate-500 italic leading-relaxed">
                      {f.limitations}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <Badge
                        variant={
                          f.severity === 'critical' || f.severity === 'high'
                            ? 'error'
                            : f.severity === 'medium'
                            ? 'warning'
                            : f.severity === 'low'
                            ? 'info'
                            : 'neutral'
                        }
                      >
                        {f.severity.toUpperCase()}
                      </Badge>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="p-0">
                    <EmptyState
                      title="No findings generated yet"
                      description={
                        isRealEvidence
                          ? "Run analysis on this image to evaluate SHA-256 integrity, EXIF provenance, and ELA."
                          : "Upload genuine evidence to generate empirical forensic findings."
                      }
                    />
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="mt-4 pt-3 border-t border-slate-100 flex flex-col sm:flex-row justify-between gap-2 text-xs text-slate-400">
          <p>
            Each finding identifies the test performed, observed result, interpretation, and scientific limitations.
          </p>
          <p className="font-medium text-slate-500">
            Automated heuristic observations &bull; Not standalone proof of scene authenticity.
          </p>
        </div>
      </Card>
        </div>
      )}
    </div>
  );
}
