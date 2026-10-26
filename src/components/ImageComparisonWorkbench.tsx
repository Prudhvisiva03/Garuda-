// Garuda — Original vs Cropped Image Comparison Workbench
// Real OpenCV SIFT feature detection, Lowe's ratio test, and RANSAC homography

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowLeftRight,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  ExternalLink,
  Sliders,
  Play,
  Info,
  FileImage,
  Layers,
  ShieldAlert,
} from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { api, type ApiEvidence, type ApiComparisonResponse } from '@/api/client';
import { formatFileSize, formatDateTime } from '@/utils/formatters';

interface ImageComparisonWorkbenchProps {
  evidenceList: ApiEvidence[];
  initialReferenceId?: string | null;
  initialCandidateId?: string | null;
}

export function ImageComparisonWorkbench({
  evidenceList,
  initialReferenceId,
  initialCandidateId,
}: ImageComparisonWorkbenchProps) {
  const [referenceId, setReferenceId] = useState<string>('');
  const [candidateId, setCandidateId] = useState<string>('');
  const [algorithm, setAlgorithm] = useState<string>('SIFT');
  const [ratioThreshold, setRatioThreshold] = useState<number>(0.75);

  const [isComparing, setIsComparing] = useState<boolean>(false);
  const [comparisonResult, setComparisonResult] = useState<ApiComparisonResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Initialize selection when evidence list is loaded
  useEffect(() => {
    if (evidenceList.length > 0) {
      if (initialReferenceId && evidenceList.some((e) => e.id === initialReferenceId)) {
        setReferenceId(initialReferenceId);
      } else if (!referenceId) {
        setReferenceId(evidenceList[0].id);
      }

      if (initialCandidateId && evidenceList.some((e) => e.id === initialCandidateId)) {
        setCandidateId(initialCandidateId);
      } else if (!candidateId) {
        // Default candidate to the second image if available, else first
        const secondItem = evidenceList.length > 1 ? evidenceList[1].id : evidenceList[0].id;
        setCandidateId(secondItem);
      }
    }
  }, [evidenceList, initialReferenceId, initialCandidateId, referenceId, candidateId]);

  // Clear comparison result when items change to prevent stale display
  useEffect(() => {
    setComparisonResult(null);
    setErrorMessage(null);
  }, [referenceId, candidateId, algorithm, ratioThreshold]);

  const referenceItem = evidenceList.find((e) => e.id === referenceId) || null;
  const candidateItem = evidenceList.find((e) => e.id === candidateId) || null;

  const handleSwap = () => {
    const temp = referenceId;
    setReferenceId(candidateId);
    setCandidateId(temp);
  };

  const handleRunComparison = async () => {
    if (!referenceId || !candidateId) {
      setErrorMessage('Please select both a Reference Image and a Candidate Image.');
      return;
    }

    if (referenceId === candidateId) {
      setErrorMessage('Reference and Candidate images must be distinct evidence files.');
      return;
    }

    setIsComparing(true);
    setErrorMessage(null);

    try {
      const result = await api.compareImages(referenceId, candidateId, algorithm, ratioThreshold);
      setComparisonResult(result);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Comparison execution failed.';
      setErrorMessage(msg);
    } finally {
      setIsComparing(false);
    }
  };

  if (evidenceList.length < 2) {
    return (
      <Card title="Original vs Cropped Image Comparison">
        <div className="py-8 text-center space-y-4">
          <div className="w-12 h-12 rounded-full bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-600 mx-auto">
            <Layers className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-slate-800">
              Multiple Evidence Items Required
            </h3>
            <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
              Image comparison requires at least two genuine evidence records in the vault (a reference original and a candidate crop). You currently have {evidenceList.length} evidence record.
            </p>
          </div>
          <Link to="/evidence">
            <Button variant="primary" size="sm" leftIcon={<FileImage className="w-4 h-4" />}>
              Go to Evidence Intake to Upload Candidate Image
            </Button>
          </Link>
        </div>
      </Card>
    );
  }

  const isSameEvidence = referenceId === candidateId;

  return (
    <div className="space-y-6">
      {/* Configuration & Image Selectors */}
      <Card
        title="Comparison Setup & Evidence Pairing"
        headerAction={
          <Badge variant="info" className="text-[10px] uppercase font-mono">
            {algorithm} Feature Matching
          </Badge>
        }
      >
        <div className="space-y-5">
          {/* Dual Evidence Selection Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-stretch">
            {/* Reference Image (Original) */}
            <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 flex flex-col justify-between space-y-4">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wider text-cyan-800 flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-cyan-600 inline-block" />
                    Reference Image (Original)
                  </span>
                  <Badge variant="neutral" className="text-[10px]">
                    FULL SCENE
                  </Badge>
                </div>

                <select
                  value={referenceId}
                  onChange={(e) => setReferenceId(e.target.value)}
                  className="w-full px-3 py-2 bg-white border border-slate-200 rounded text-xs font-mono text-slate-800 focus:ring-1 focus:ring-cyan-500"
                >
                  {evidenceList.map((e) => (
                    <option key={e.id} value={e.id}>
                      {e.original_filename} ({e.id}) &bull; {e.width}×{e.height}
                    </option>
                  ))}
                </select>
              </div>

              {/* Preview & Metadata */}
              {referenceItem && (
                <div className="space-y-2">
                  <div className="relative aspect-[4/3] bg-white border border-slate-200 rounded-md overflow-hidden flex items-center justify-center">
                    <img
                      src={api.getEvidenceFileUrl(referenceItem.id)}
                      alt={referenceItem.original_filename}
                      className="w-full h-full object-contain"
                      loading="lazy"
                    />
                    {comparisonResult?.overlap_box && referenceItem.width && referenceItem.height && (
                      <svg
                        viewBox={`0 0 ${referenceItem.width} ${referenceItem.height}`}
                        className="absolute inset-0 w-full h-full pointer-events-none"
                      >
                        {comparisonResult.overlap_box.polygon ? (
                          <polygon
                            points={comparisonResult.overlap_box.polygon.map((p) => p.join(',')).join(' ')}
                            fill="rgba(6, 182, 212, 0.3)"
                            stroke="#06b6d4"
                            strokeWidth={Math.max(3, referenceItem.width / 150)}
                          />
                        ) : (
                          <rect
                            x={comparisonResult.overlap_box.x}
                            y={comparisonResult.overlap_box.y}
                            width={comparisonResult.overlap_box.width}
                            height={comparisonResult.overlap_box.height}
                            fill="rgba(6, 182, 212, 0.3)"
                            stroke="#06b6d4"
                            strokeWidth={Math.max(3, referenceItem.width / 150)}
                          />
                        )}
                      </svg>
                    )}
                  </div>
                  <dl className="text-[11px] divide-y divide-slate-100 font-mono">
                    <div className="py-1 flex justify-between">
                      <dt className="text-slate-500 font-sans">Resolution:</dt>
                      <dd className="text-slate-800 font-semibold">{referenceItem.width} × {referenceItem.height} px</dd>
                    </div>
                    <div className="py-1 flex justify-between">
                      <dt className="text-slate-500 font-sans">Size:</dt>
                      <dd className="text-slate-700">{formatFileSize(referenceItem.file_size)}</dd>
                    </div>
                    <div className="py-1 flex justify-between">
                      <dt className="text-slate-500 font-sans">Format:</dt>
                      <dd className="text-slate-700">{referenceItem.mime_type}</dd>
                    </div>
                  </dl>
                </div>
              )}
            </div>

            {/* Candidate Image (Potentially Cropped) */}
            <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 flex flex-col justify-between space-y-4">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wider text-amber-800 flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-amber-500 inline-block" />
                    Candidate Image (Modified / Cropped)
                  </span>
                  <Badge variant="neutral" className="text-[10px]">
                    TARGET SAMPLE
                  </Badge>
                </div>

                <select
                  value={candidateId}
                  onChange={(e) => setCandidateId(e.target.value)}
                  className="w-full px-3 py-2 bg-white border border-slate-200 rounded text-xs font-mono text-slate-800 focus:ring-1 focus:ring-amber-500"
                >
                  {evidenceList.map((e) => (
                    <option key={e.id} value={e.id}>
                      {e.original_filename} ({e.id}) &bull; {e.width}×{e.height}
                    </option>
                  ))}
                </select>
              </div>

              {/* Preview & Metadata */}
              {candidateItem && (
                <div className="space-y-2">
                  <div className="aspect-[4/3] bg-white border border-slate-200 rounded-md overflow-hidden flex items-center justify-center">
                    <img
                      src={api.getEvidenceFileUrl(candidateItem.id)}
                      alt={candidateItem.original_filename}
                      className="w-full h-full object-contain"
                      loading="lazy"
                    />
                  </div>
                  <dl className="text-[11px] divide-y divide-slate-100 font-mono">
                    <div className="py-1 flex justify-between">
                      <dt className="text-slate-500 font-sans">Resolution:</dt>
                      <dd className="text-slate-800 font-semibold">{candidateItem.width} × {candidateItem.height} px</dd>
                    </div>
                    <div className="py-1 flex justify-between">
                      <dt className="text-slate-500 font-sans">Size:</dt>
                      <dd className="text-slate-700">{formatFileSize(candidateItem.file_size)}</dd>
                    </div>
                    <div className="py-1 flex justify-between">
                      <dt className="text-slate-500 font-sans">Format:</dt>
                      <dd className="text-slate-700">{candidateItem.mime_type}</dd>
                    </div>
                  </dl>
                </div>
              )}
            </div>
          </div>

          {/* Controls Bar & Parameters */}
          <div className="p-3 bg-white border border-slate-200 rounded-lg flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-4 text-xs">
              <Button
                variant="secondary"
                size="sm"
                leftIcon={<ArrowLeftRight className="w-3.5 h-3.5" />}
                onClick={handleSwap}
                title="Swap Reference and Candidate roles"
              >
                Swap Images
              </Button>

              <div className="flex items-center gap-2">
                <Sliders className="w-3.5 h-3.5 text-slate-400" />
                <span className="text-slate-500 font-medium">Detector:</span>
                <select
                  value={algorithm}
                  onChange={(e) => setAlgorithm(e.target.value)}
                  className="px-2 py-1 bg-slate-50 border border-slate-200 rounded font-mono text-slate-700"
                >
                  <option value="SIFT">SIFT (Scale-Invariant, Recommended)</option>
                  <option value="ORB">ORB (Oriented FAST)</option>
                </select>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-slate-500 font-medium">Lowe's Ratio:</span>
                <select
                  value={ratioThreshold}
                  onChange={(e) => setRatioThreshold(parseFloat(e.target.value))}
                  className="px-2 py-1 bg-slate-50 border border-slate-200 rounded font-mono text-slate-700"
                >
                  <option value={0.70}>0.70 (Strict)</option>
                  <option value={0.75}>0.75 (Standard Recommended)</option>
                  <option value={0.80}>0.80 (Permissive)</option>
                </select>
              </div>
            </div>

            <Button
              variant="primary"
              size="sm"
              isLoading={isComparing}
              disabled={isSameEvidence || isComparing}
              leftIcon={<Play className="w-3.5 h-3.5" />}
              onClick={handleRunComparison}
            >
              {isComparing ? 'Computing Correspondences...' : 'Run Geometric Comparison'}
            </Button>
          </div>

          {isSameEvidence && (
            <p className="text-xs text-amber-600 font-medium flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5" />
              Reference and Candidate are set to the same evidence file. Please select two different images to evaluate overlap.
            </p>
          )}

          {errorMessage && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}
        </div>
      </Card>

      {/* Comparison Results Section */}
      {comparisonResult && (
        <div className="space-y-6">
          {/* Classification Status Banner */}
          <div
            className={`p-4 rounded-lg border flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-xs ${
              comparisonResult.status === 'exact_byte_duplicate'
                ? 'bg-cyan-50 border-cyan-200 text-cyan-950'
                : comparisonResult.status === 'visually_similar_full_frame' || comparisonResult.status === 'identical_visual_content'
                ? 'bg-sky-50 border-sky-200 text-sky-950'
                : comparisonResult.status === 'possible_crop_match'
                ? 'bg-emerald-50 border-emerald-200 text-emerald-950'
                : comparisonResult.status === 'inconclusive'
                ? 'bg-amber-50 border-amber-200 text-amber-900'
                : comparisonResult.status === 'no_reliable_match'
                ? 'bg-slate-100 border-slate-200 text-slate-800'
                : 'bg-red-50 border-red-200 text-red-900'
            }`}
          >
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                {comparisonResult.status === 'exact_byte_duplicate' || comparisonResult.status === 'visually_similar_full_frame' || comparisonResult.status === 'identical_visual_content' ? (
                  <CheckCircle2 className="w-5 h-5 text-cyan-600 flex-shrink-0" />
                ) : comparisonResult.status === 'possible_crop_match' ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
                ) : comparisonResult.status === 'inconclusive' ? (
                  <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0" />
                ) : (
                  <AlertCircle className="w-5 h-5 text-slate-600 flex-shrink-0" />
                )}
                <h3 className="font-semibold text-sm">
                  {comparisonResult.status === 'exact_byte_duplicate'
                    ? 'Exact Byte Duplicate (Identical SHA-256)'
                    : comparisonResult.status === 'visually_similar_full_frame'
                    ? 'Visually Similar Full Frame (Re-encoded / Transcoded)'
                    : comparisonResult.status === 'identical_visual_content'
                    ? 'Identical Visual Content (Different Cryptographic Hash)'
                    : comparisonResult.status === 'possible_crop_match'
                    ? 'Possible Partial-Image / Crop Match Confirmed'
                    : comparisonResult.status === 'inconclusive'
                    ? 'Inconclusive Geometric Relationship'
                    : comparisonResult.status === 'no_reliable_match'
                    ? 'No Reliable Feature Correspondence'
                    : 'Comparison Failed'}
                </h3>
              </div>
              <p className="text-xs opacity-90 leading-relaxed max-w-2xl">
                {comparisonResult.explanation}
              </p>
            </div>

            <Badge
              variant={
                comparisonResult.status === 'exact_byte_duplicate' || comparisonResult.status === 'visually_similar_full_frame' || comparisonResult.status === 'identical_visual_content'
                  ? 'info'
                  : comparisonResult.status === 'possible_crop_match'
                  ? 'success'
                  : comparisonResult.status === 'inconclusive'
                  ? 'warning'
                  : comparisonResult.status === 'no_reliable_match'
                  ? 'neutral'
                  : 'error'
              }
              className="text-xs px-2.5 py-1 whitespace-nowrap self-start sm:self-auto font-mono"
            >
              {comparisonResult.status.toUpperCase().replace(/_/g, ' ')}
            </Badge>
          </div>

          {/* Visual Correspondence & Artifact Display */}
          <Card
            title="Feature Correspondence & Overlap Visualization"
            headerAction={
              comparisonResult.artifact_url && (
                <a
                  href={comparisonResult.artifact_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-cyan-600 hover:text-cyan-700 font-medium inline-flex items-center gap-1"
                >
                  <span>Open Full-Res Artifact</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              )
            }
          >
            <div className="space-y-4">
              <div className="aspect-[16/9] bg-slate-900 border border-slate-200 rounded-lg overflow-hidden flex items-center justify-center">
                {comparisonResult.artifact_url ? (
                  <img
                    src={comparisonResult.artifact_url}
                    alt="Feature Matching and Bounding Box Artifact"
                    className="w-full h-full object-contain"
                  />
                ) : (
                  <div className="p-8 text-center text-slate-400 text-xs">
                    No visual correspondence artifact generated for this comparison.
                  </div>
                )}
              </div>

              {comparisonResult.overlap_box && (
                <div className="p-3 bg-cyan-50 border border-cyan-200 rounded-md text-cyan-900 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="w-3 h-3 border-2 border-cyan-500 bg-cyan-200/50 rounded-xs inline-block" />
                    <span className="font-semibold">Estimated Overlap Region on Reference:</span>
                    <span className="font-mono">
                      X={comparisonResult.overlap_box.x}, Y={comparisonResult.overlap_box.y}, Width={comparisonResult.overlap_box.width} px, Height={comparisonResult.overlap_box.height} px
                    </span>
                  </div>
                  {comparisonResult.overlap_box.area_ratio !== undefined && (
                    <span className="font-mono font-semibold bg-white px-2 py-0.5 rounded border border-cyan-200 text-cyan-800">
                      {(comparisonResult.overlap_box.area_ratio * 100).toFixed(1)}% of reference area
                    </span>
                  )}
                </div>
              )}
            </div>
          </Card>

          {/* Empirical Measurements & Mathematical Verification Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-4 bg-white border border-slate-200 rounded-lg shadow-xs space-y-1">
              <span className="text-slate-500 text-xs font-medium">Lowe Ratio Matches</span>
              <p className="text-xl font-bold font-mono text-slate-900">
                {comparisonResult.raw_matches}
              </p>
              <span className="text-[10px] text-slate-400 block">Candidate keypoint pairs</span>
            </div>

            <div className="p-4 bg-white border border-slate-200 rounded-lg shadow-xs space-y-1">
              <span className="text-slate-500 text-xs font-medium">RANSAC Inliers</span>
              <p className="text-xl font-bold font-mono text-emerald-600">
                {comparisonResult.inliers_count}
              </p>
              <span className="text-[10px] text-slate-400 block">Geometrically verified points</span>
            </div>

            <div className="p-4 bg-white border border-slate-200 rounded-lg shadow-xs space-y-1">
              <span className="text-slate-500 text-xs font-medium">Inlier Ratio</span>
              <p className="text-xl font-bold font-mono text-cyan-700">
                {(comparisonResult.inlier_ratio * 100).toFixed(1)}%
              </p>
              <span className="text-[10px] text-slate-400 block">Verified / Raw match ratio</span>
            </div>

            <div className="p-4 bg-white border border-slate-200 rounded-lg shadow-xs space-y-1">
              <span className="text-slate-500 text-xs font-medium">Estimated Scale Ratio</span>
              <p className="text-xl font-bold font-mono text-slate-800">
                {comparisonResult.estimated_scale !== null
                  ? `${comparisonResult.estimated_scale.toFixed(3)}×`
                  : 'N/A'}
              </p>
              <span className="text-[10px] text-slate-400 block">Candidate relative to crop</span>
            </div>
          </div>

          {/* Explainability & Scientific Limitations (Requirement 6) */}
          <Card
            title="Scientific Forensic Methodology & Method Limitations"
            headerAction={<Info className="w-4 h-4 text-slate-400" />}
          >
            <div className="space-y-4 text-xs text-slate-600">
              <div className="space-y-2">
                <h4 className="font-semibold text-slate-800 text-xs uppercase tracking-wider">
                  Test Methodology
                </h4>
                <p className="leading-relaxed">
                  Local photometric scale-space extrema are identified via OpenCV {comparisonResult.algorithm} and matched across images using L2 norm distance with Lowe’s nearest-neighbor ratio test (threshold: {ratioThreshold}). The geometric spatial transformation is solved using RANSAC planar homography (5.0 px maximum reprojection error). If verified inliers form a valid convex quadrilateral within normal scale bounds, the region is projected onto the reference image.
                </p>
              </div>

              <div className="p-3 bg-amber-50 border border-amber-200 rounded-md text-amber-900 space-y-2">
                <div className="flex items-center gap-1.5 font-semibold text-amber-800">
                  <ShieldAlert className="w-4 h-4 text-amber-600 flex-shrink-0" />
                  <span>Mandatory Forensic Caveats & Method Limitations</span>
                </div>
                <ul className="list-disc list-inside space-y-1 text-[11px] leading-relaxed text-amber-900/90">
                  <li>
                    <strong>Not Legal Provenance Proof:</strong> Feature correspondence measures shared visual texture patterns, not custodial provenance, camera ownership, or legal authenticity.
                  </li>
                  <li>
                    <strong>Symmetry & Repetitive Structures:</strong> Identical stock objects, symmetrical architecture, or repetitive brick/textile textures may yield matching clusters across unrelated scenes.
                  </li>
                  <li>
                    <strong>Transformation Boundaries:</strong> Severe perspective distortion (&gt;60°), non-rigid warping (e.g. stretching/liquify), extreme downsampling (&lt;40px), or heavy JPEG recompression can suppress feature inliers, resulting in false negatives (inconclusive).
                  </li>
                  <li>
                    <strong>Required Corroboration:</strong> Findings must always be cross-referenced with cryptographic hash verification, EXIF metadata inspection, and investigator visual analysis.
                  </li>
                </ul>
              </div>

              <div className="pt-2 border-t border-slate-100 flex flex-wrap items-center justify-between text-[11px] text-slate-500 font-mono">
                <span>Comparison ID: {comparisonResult.id}</span>
                <span>Evaluated: {formatDateTime(comparisonResult.created_at)}</span>
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
