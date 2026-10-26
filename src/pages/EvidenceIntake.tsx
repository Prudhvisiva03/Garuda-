import { useState, useEffect, useRef, type DragEvent, type ChangeEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Upload,
  CheckCircle2,
  AlertCircle,
  FileImage,
  Video,
  Mic,
  ArrowRight,
  ShieldCheck,
  RefreshCw,
  FolderOpen,
} from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { api, type ApiEvidence, type ApiCase } from '@/api/client';
import { formatFileSize } from '@/utils/formatters';

const custodyWorkflowSteps = [
  { step: 1, title: 'Accept file', description: 'Ingest raw multi-modal media artifact (Image, Video, Audio)' },
  { step: 2, title: 'Validate format', description: 'Verify magic bytes, container headers, and integrity constraints' },
  { step: 3, title: 'Calculate SHA-256', description: 'Compute cryptographic checksum immediately upon intake' },
  { step: 4, title: 'Store securely', description: 'Persist read-only original file to isolated evidence vault' },
  { step: 5, title: 'Create evidence record', description: 'Generate audit trail log and chain of custody documentation' },
];

export function EvidenceIntake() {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadedEvidence, setUploadedEvidence] = useState<ApiEvidence | null>(null);
  const [cases, setCases] = useState<ApiCase[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string>('FIR-2026-041/CYBER');

  useEffect(() => {
    async function loadCases() {
      try {
        const list = await api.listCases();
        if (list && list.length > 0) {
          setCases(list);
          setSelectedCaseId(list[0].case_number || list[0].id);
        }
      } catch {
        // Fallback to default
      }
    }
    loadCases();
  }, []);

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  };

  const handleFileInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileSelected(e.target.files[0]);
    }
  };

  const getFileModality = (file: File): 'image' | 'video' | 'audio' | 'unknown' => {
    const ext = file.name.toLowerCase().split('.').pop() || '';
    if (['jpg', 'jpeg', 'png'].includes(ext) || file.type.startsWith('image/')) return 'image';
    if (['mp4', 'mov', 'avi'].includes(ext) || file.type.startsWith('video/')) return 'video';
    if (['wav', 'mp3', 'ogg', 'flac'].includes(ext) || file.type.startsWith('audio/')) return 'audio';
    return 'unknown';
  };

  const handleFileSelected = (file: File) => {
    setUploadError(null);
    setUploadedEvidence(null);

    const modality = getFileModality(file);
    if (modality === 'unknown') {
      setUploadError('Invalid format: Supported media includes Images (JPEG/PNG), Videos (MP4/MOV/AVI), and Audios (WAV/MP3).');
      return;
    }

    // Size limit check (25 MiB)
    if (file.size > 25 * 1024 * 1024) {
      setUploadError('File size exceeds the 25 MiB ingestion limit.');
      return;
    }

    setSelectedFile(file);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setIsUploading(true);
    setUploadError(null);

    try {
      const modality = getFileModality(selectedFile);
      let result: ApiEvidence;

      if (modality === 'video') {
        result = await api.uploadVideo(selectedFile, selectedCaseId);
      } else if (modality === 'audio') {
        result = await api.uploadAudio(selectedFile, selectedCaseId);
      } else {
        result = await api.uploadEvidence(selectedFile, selectedCaseId);
      }

      setUploadedEvidence(result);
      setSelectedFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Upload failed due to connection error.';
      setUploadError(msg);
    } finally {
      setIsUploading(false);
    }
  };

  const isVideoEvidence = uploadedEvidence?.mime_type.startsWith('video/');
  const isAudioEvidence = uploadedEvidence?.mime_type.startsWith('audio/');

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-semibold text-slate-900 tracking-tight">Evidence Intake</h1>
          <p className="text-sm text-slate-500 mt-1">
            Universal ingestion desk for Images, CCTV Videos, and Audio Evidence with instant SHA-256 sealing
          </p>
        </div>
      </div>

      {/* Upload Error Banner */}
      {uploadError && (
        <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-red-700 flex items-start gap-3 text-sm">
          <AlertCircle className="w-5 h-5 flex-shrink-0 text-red-600 mt-0.5" />
          <div className="space-y-1">
            <p className="font-semibold text-red-800">Evidence Ingestion Error</p>
            <p>{uploadError}</p>
          </div>
        </div>
      )}

      {/* Success Intake Confirmation Card */}
      {uploadedEvidence && (
        <div className="p-5 rounded-lg bg-emerald-50 border border-emerald-200 text-slate-800 space-y-4 shadow-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-emerald-700 font-semibold text-base">
              <CheckCircle2 className="w-5 h-5 text-emerald-600" />
              <span>Evidence Ingested Successfully</span>
            </div>
            <Badge variant="success" dot>
              Cryptographically Verified
            </Badge>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 text-xs bg-white p-4 rounded-md border border-emerald-100 shadow-xs">
            <div>
              <span className="text-slate-500 block">Evidence ID</span>
              <span className="font-mono font-bold text-slate-900">{uploadedEvidence.id}</span>
            </div>
            <div>
              <span className="text-slate-500 block">Case / FIR</span>
              <span className="font-mono font-bold text-cyan-700">{uploadedEvidence.case_id}</span>
            </div>
            <div>
              <span className="text-slate-500 block">Original Name</span>
              <span className="font-medium text-slate-800 truncate block">{uploadedEvidence.original_filename}</span>
            </div>
            <div>
              <span className="text-slate-500 block">Format & Dimensions</span>
              <span className="font-mono text-slate-800">
                {uploadedEvidence.mime_type} {uploadedEvidence.width ? `(${uploadedEvidence.width} × ${uploadedEvidence.height} px)` : ''}
              </span>
            </div>
            <div>
              <span className="text-slate-500 block">File Size</span>
              <span className="font-mono text-slate-800">{formatFileSize(uploadedEvidence.file_size)}</span>
            </div>
          </div>

          <div className="bg-white p-3 rounded-md border border-emerald-100">
            <span className="text-xs text-slate-500 block mb-1">Authoritative Intake SHA-256 Digest</span>
            <code className="text-xs font-mono text-cyan-700 break-all select-all block bg-slate-50 p-2 rounded border border-slate-100">
              {uploadedEvidence.sha256_intake}
            </code>
          </div>

          <div className="flex flex-wrap items-center gap-3 pt-1">
            {isVideoEvidence ? (
              <Button
                variant="primary"
                size="sm"
                leftIcon={<ArrowRight className="w-4 h-4" />}
                onClick={() => navigate(`/video?evidenceId=${uploadedEvidence.id}`)}
              >
                Open in Video Forensics Workbench
              </Button>
            ) : isAudioEvidence ? (
              <Button
                variant="primary"
                size="sm"
                leftIcon={<ArrowRight className="w-4 h-4" />}
                onClick={() => navigate(`/audio?evidenceId=${uploadedEvidence.id}`)}
              >
                Open in Audio Forensics Workbench
              </Button>
            ) : (
              <Button
                variant="primary"
                size="sm"
                leftIcon={<ArrowRight className="w-4 h-4" />}
                onClick={() => navigate(`/analysis?evidenceId=${uploadedEvidence.id}`)}
              >
                Open in Image Analysis Workbench
              </Button>
            )}
            <Button
              variant="secondary"
              size="sm"
              leftIcon={<RefreshCw className="w-4 h-4" />}
              onClick={() => {
                setUploadedEvidence(null);
                setSelectedFile(null);
              }}
            >
              Upload Another Evidence Item
            </Button>
          </div>
        </div>
      )}

      {/* Main Upload Drop Area */}
      {!uploadedEvidence && (
        <Card title="Upload Digital Evidence">
          {/* Target Case Selector */}
          <div className="mb-4 p-3 bg-slate-50 border border-slate-200 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-xs font-medium text-slate-700">
              <FolderOpen className="w-4 h-4 text-cyan-600 flex-shrink-0" />
              <span>Target Investigation Case (FIR):</span>
            </div>
            <div className="flex-1 sm:max-w-md">
              <select
                value={selectedCaseId}
                onChange={(e) => setSelectedCaseId(e.target.value)}
                className="w-full text-xs rounded-md border border-slate-300 bg-white py-1.5 px-2.5 text-slate-800 font-medium focus:outline-none focus:ring-1 focus:ring-cyan-500 shadow-xs"
              >
                {cases.length > 0 ? (
                  cases.map((c) => (
                    <option key={c.id} value={c.case_number}>
                      {c.case_number} &bull; {c.title} ({c.category})
                    </option>
                  ))
                ) : (
                  <>
                    <option value="FIR-2026-041/CYBER">FIR-2026-041/CYBER &bull; Digital Media Tampering</option>
                    <option value="FIR-2026-088/CCTV">FIR-2026-088/CCTV &bull; Surveillance CCTV Video Splicing</option>
                    <option value="FIR-2026-104/VOICE">FIR-2026-104/VOICE &bull; Cyber Extortion Audio</option>
                  </>
                )}
              </select>
            </div>
          </div>

          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,video/mp4,video/quicktime,video/x-msvideo,audio/wav,audio/mpeg,audio/mp3"
            className="hidden"
            onChange={handleFileInputChange}
          />

          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-lg p-8 sm:p-12 text-center transition-all cursor-pointer ${
              isDragging
                ? 'border-cyan-500 bg-cyan-50/60'
                : 'border-slate-300 hover:border-slate-400 bg-slate-50/60'
            }`}
            onClick={() => fileInputRef.current?.click()}
          >
            <div className="flex flex-col items-center justify-center space-y-3">
              <div className="w-14 h-14 rounded-full bg-cyan-50 border border-cyan-200 flex items-center justify-center text-cyan-600 shadow-xs">
                <Upload className="w-7 h-7" />
              </div>

              <div>
                <p className="text-base font-medium text-slate-800">
                  Click to select evidence file or drag and drop here
                </p>
                <p className="text-xs text-slate-500 mt-1">
                  Supported formats: Images (JPEG, PNG) &bull; Videos (MP4, MOV, AVI) &bull; Voice/Audio (WAV, MP3) &bull; Max 25 MiB
                </p>
              </div>

              <div className="flex items-center gap-2 pt-2 text-xs text-slate-500">
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
                <span>Cryptographic SHA-256 digest computed immediately upon intake</span>
              </div>
            </div>
          </div>

          {/* Selected File Details & Upload Action */}
          {selectedFile && (
            <div className="mt-4 p-4 rounded-lg bg-slate-50 border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-3 min-w-0">
                {getFileModality(selectedFile) === 'video' ? (
                  <Video className="w-6 h-6 text-indigo-600 flex-shrink-0" />
                ) : getFileModality(selectedFile) === 'audio' ? (
                  <Mic className="w-6 h-6 text-purple-600 flex-shrink-0" />
                ) : (
                  <FileImage className="w-6 h-6 text-cyan-600 flex-shrink-0" />
                )}
                <div className="min-w-0 text-xs">
                  <p className="font-semibold text-slate-800 truncate">{selectedFile.name}</p>
                  <p className="text-slate-500 font-mono mt-0.5">
                    {formatFileSize(selectedFile.size)} &bull; {selectedFile.type || 'unknown format'}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 flex-shrink-0">
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={isUploading}
                  onClick={() => {
                    setSelectedFile(null);
                    if (fileInputRef.current) fileInputRef.current.value = '';
                  }}
                >
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  isLoading={isUploading}
                  leftIcon={<Upload className="w-4 h-4" />}
                  onClick={handleUpload}
                >
                  {isUploading ? 'Ingesting Evidence...' : 'Ingest & Hash Evidence'}
                </Button>
              </div>
            </div>
          )}
        </Card>
      )}

      {/* Standard Ingestion Workflow Card */}
      <Card title="Evidence Custody Protocol">
        <div className="space-y-3">
          <p className="text-xs text-slate-500">
            The evidence intake pipeline enforces strict digital forensics custody standards:
          </p>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-3 pt-1">
            {custodyWorkflowSteps.map((item) => (
              <div
                key={item.step}
                className="p-3 rounded-lg bg-slate-50 border border-slate-200"
              >
                <div className="flex items-center gap-2 mb-1.5 text-cyan-600 font-semibold">
                  <span className="w-5 h-5 rounded-full bg-cyan-100 text-cyan-700 text-[11px] font-mono flex items-center justify-center">
                    {item.step}
                  </span>
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                </div>
                <h4 className="text-xs font-semibold text-slate-800">{item.title}</h4>
                <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">
                  {item.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </Card>
    </div>
  );
}
