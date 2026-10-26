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
  ShieldAlert,
  RefreshCw,
  FolderOpen,
} from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { api, type ApiEvidence, type ApiCase } from '@/api/client';
import { formatFileSize } from '@/utils/formatters';

interface MagicByteInspection {
  detectedModality: 'image' | 'video' | 'audio' | 'document' | 'empty' | 'unknown';
  isMismatch: boolean;
  detectedMime: string;
  magicHex: string;
  description: string;
}

async function inspectMagicBytes(file: File): Promise<MagicByteInspection> {
  if (file.size === 0) {
    return {
      detectedModality: 'empty',
      isMismatch: false,
      detectedMime: 'application/x-empty',
      magicHex: '',
      description: 'Zero-byte empty file. Cannot be ingested into forensic vault.',
    };
  }

  const slice = file.slice(0, 32);
  const buffer = await slice.arrayBuffer();
  const bytes = new Uint8Array(buffer);
  const ext = file.name.toLowerCase().split('.').pop() || '';

  // 1. JPEG: FF D8 FF
  if (bytes[0] === 0xFF && bytes[1] === 0xD8 && bytes[2] === 0xFF) {
    const isMismatch = !['jpg', 'jpeg'].includes(ext);
    return {
      detectedModality: 'image',
      isMismatch,
      detectedMime: 'image/jpeg',
      magicHex: 'FF D8 FF',
      description: isMismatch
        ? `Mismatched Extension Trap: File '${file.name}' has a .${ext} extension, but binary magic bytes confirm a genuine JPEG Image (FF D8 FF E0). Disguised media container identified!`
        : 'JPEG Image Matrix',
    };
  }

  // 2. PNG: 89 50 4E 47
  if (bytes[0] === 0x89 && bytes[1] === 0x50 && bytes[2] === 0x4E && bytes[3] === 0x47) {
    const isMismatch = ext !== 'png';
    return {
      detectedModality: 'image',
      isMismatch,
      detectedMime: 'image/png',
      magicHex: '89 50 4E 47',
      description: isMismatch
        ? `Mismatched Extension: File '${file.name}' has a .${ext} extension, but binary magic bytes confirm a PNG Image.`
        : 'PNG Image Matrix',
    };
  }

  // 3. MP4 / ISO Base Media: byte 4..8 is 'ftyp' or 'moov'
  const isFtyp = bytes.length >= 8 && (
    (bytes[4] === 0x66 && bytes[5] === 0x74 && bytes[6] === 0x79 && bytes[7] === 0x70) ||
    (bytes[4] === 0x6D && bytes[5] === 0x6F && bytes[6] === 0x6F && bytes[7] === 0x76)
  );
  if (isFtyp) {
    const isMismatch = !['mp4', 'mov', 'm4v', 'avi'].includes(ext);
    return {
      detectedModality: 'video',
      isMismatch,
      detectedMime: 'video/mp4',
      magicHex: '66 74 79 70 (ftyp)',
      description: isMismatch
        ? `Mismatched Extension Trap Detected: File '${file.name}' has an .${ext} extension, but binary magic bytes confirm an MP4 Video container (ftyp / isom). Disguised media container identified!`
        : 'MP4 ISO Base Media Container',
    };
  }

  // 4. RIFF container (WAV or AVI)
  if (bytes[0] === 0x52 && bytes[1] === 0x49 && bytes[2] === 0x46 && bytes[3] === 0x46) {
    const fourCC = String.fromCharCode(...bytes.slice(8, 12));
    if (fourCC === 'WAVE') {
      const isMismatch = ext !== 'wav';
      return {
        detectedModality: 'audio',
        isMismatch,
        detectedMime: 'audio/wav',
        magicHex: '52 49 46 46 (WAVE)',
        description: isMismatch
          ? `Mismatched Extension: File '${file.name}' has a .${ext} extension, but contains a WAV audio stream.`
          : 'PCM WAV Audio Stream',
      };
    }
    if (fourCC === 'AVI ') {
      const isMismatch = ext !== 'avi';
      return {
        detectedModality: 'video',
        isMismatch,
        detectedMime: 'video/x-msvideo',
        magicHex: '52 49 46 46 (AVI )',
        description: isMismatch
          ? `Mismatched Extension: File '${file.name}' has a .${ext} extension, but contains an AVI video container.`
          : 'AVI Video Container',
      };
    }
  }

  // 5. MP3: ID3 or FF FB/FA
  if ((bytes[0] === 0x49 && bytes[1] === 0x44 && bytes[2] === 0x33) || (bytes[0] === 0xFF && (bytes[1] & 0xE0) === 0xE0)) {
    const isMismatch = ext !== 'mp3';
    return {
      detectedModality: 'audio',
      isMismatch,
      detectedMime: 'audio/mpeg',
      magicHex: '49 44 33 (ID3/MPEG)',
      description: isMismatch
        ? `Mismatched Extension: File '${file.name}' has a .${ext} extension, but contains an MP3 audio stream.`
        : 'MPEG Layer-3 Audio',
    };
  }

  // 6. ZIP / Office Open XML (DOCX / XLSX): 50 4B 03 04
  if (bytes[0] === 0x50 && bytes[1] === 0x4B && bytes[2] === 0x03 && bytes[3] === 0x04) {
    return {
      detectedModality: 'document',
      isMismatch: ['jpg', 'jpeg', 'png', 'mp4', 'wav', 'mp3'].includes(ext),
      detectedMime: 'application/vnd.openxmlformats-officedocument',
      magicHex: '50 4B 03 04 (PK..)',
      description: `Office Open XML Document (${ext.toUpperCase()}). Non-media binary safely rejected from image/video decoding pipelines to prevent polyglot execution.`,
    };
  }

  // 7. Legacy Office (XLS / DOC): D0 CF 11 E0
  if (bytes[0] === 0xD0 && bytes[1] === 0xCF && bytes[2] === 0x11 && bytes[3] === 0xE0) {
    return {
      detectedModality: 'document',
      isMismatch: ['jpg', 'jpeg', 'png', 'mp4', 'wav', 'mp3'].includes(ext),
      detectedMime: 'application/vnd.ms-excel',
      magicHex: 'D0 CF 11 E0',
      description: `Legacy Microsoft Office Binary Document. Non-media container.`,
    };
  }

  // Standard extension fallback if magic bytes are not matched above
  if (['jpg', 'jpeg', 'png'].includes(ext)) {
    return { detectedModality: 'image', isMismatch: false, detectedMime: file.type || 'image/jpeg', magicHex: '', description: 'Image Matrix' };
  }
  if (['mp4', 'mov', 'avi'].includes(ext)) {
    return { detectedModality: 'video', isMismatch: false, detectedMime: file.type || 'video/mp4', magicHex: '', description: 'Video Container' };
  }
  if (['wav', 'mp3', 'ogg', 'flac'].includes(ext)) {
    return { detectedModality: 'audio', isMismatch: false, detectedMime: file.type || 'audio/wav', magicHex: '', description: 'Audio Stream' };
  }

  return {
    detectedModality: 'unknown',
    isMismatch: false,
    detectedMime: file.type || 'application/octet-stream',
    magicHex: Array.from(bytes.slice(0, 4)).map((b) => b.toString(16).padStart(2, '0')).join(' '),
    description: `Binary header signature not recognized as a supported media container.`,
  };
}

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
  const [inspection, setInspection] = useState<MagicByteInspection | null>(null);
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

  const handleDrop = async (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      await handleFileSelected(e.dataTransfer.files[0]);
    }
  };

  const handleFileInputChange = async (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      await handleFileSelected(e.target.files[0]);
    }
  };

  const getFileModality = (file: File): 'image' | 'video' | 'audio' | 'unknown' => {
    const ext = file.name.toLowerCase().split('.').pop() || '';
    if (['jpg', 'jpeg', 'png'].includes(ext) || file.type.startsWith('image/')) return 'image';
    if (['mp4', 'mov', 'avi'].includes(ext) || file.type.startsWith('video/')) return 'video';
    if (['wav', 'mp3', 'ogg', 'flac'].includes(ext) || file.type.startsWith('audio/')) return 'audio';
    return 'unknown';
  };

  const handleFileSelected = async (file: File) => {
    setUploadError(null);
    setUploadedEvidence(null);
    setInspection(null);

    // Size limit check (25 MiB)
    if (file.size > 25 * 1024 * 1024) {
      setUploadError('File size exceeds the 25 MiB ingestion limit.');
      return;
    }

    const ins = await inspectMagicBytes(file);
    setInspection(ins);

    if (ins.detectedModality === 'empty') {
      setUploadError('Empty file (0 bytes) rejected. Electronic evidence must contain an authenticated, non-empty bitstream.');
      return;
    }

    if (ins.detectedModality === 'unknown') {
      setUploadError('Unsupported format: Media header not recognized. Supported formats are Images (JPEG/PNG), Videos (MP4/MOV/AVI), and Audios (WAV/MP3).');
      return;
    }

    setSelectedFile(file);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setIsUploading(true);
    setUploadError(null);

    try {
      const modality = inspection?.detectedModality || getFileModality(selectedFile);
      let result: ApiEvidence;

      if (modality === 'video') {
        const uploadFile = inspection?.isMismatch
          ? new File([selectedFile], selectedFile.name.replace(/\.[^/.]+$/, "") + ".mp4", { type: "video/mp4" })
          : selectedFile;
        result = await api.uploadVideo(uploadFile, selectedCaseId);
      } else if (modality === 'audio') {
        const uploadFile = inspection?.isMismatch
          ? new File([selectedFile], selectedFile.name.replace(/\.[^/.]+$/, "") + ".wav", { type: "audio/wav" })
          : selectedFile;
        result = await api.uploadAudio(uploadFile, selectedCaseId);
      } else if (modality === 'image') {
        const uploadFile = inspection?.isMismatch
          ? new File([selectedFile], selectedFile.name.replace(/\.[^/.]+$/, "") + ".jpg", { type: "image/jpeg" })
          : selectedFile;
        result = await api.uploadEvidence(uploadFile, selectedCaseId);
      } else {
        throw new Error(`Non-media binary (${inspection?.description || 'Document'}) cannot be parsed as forensic media. Rejection enforced for Section 65B court admissibility.`);
      }

      setUploadedEvidence(result);
      setSelectedFile(null);
      setInspection(null);
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
            accept="image/jpeg,image/png,video/mp4,video/quicktime,video/x-msvideo,audio/wav,audio/mpeg,audio/mp3,.xls,.xlsx,.pdf,.doc,.docx,*"
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

          {/* Mismatched Extension Trap Alert */}
          {selectedFile && inspection?.isMismatch && (
            <div className="mt-3 p-3.5 rounded-lg bg-amber-50 border border-amber-300 text-amber-900 text-xs flex items-start gap-3">
              <ShieldAlert className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-amber-900">
                    Disguised Media Container Detected (Magic Bytes: {inspection.magicHex})
                  </span>
                  <Badge variant="warning" className="text-[10px] font-mono uppercase">
                    Anti-Spoofing Active
                  </Badge>
                </div>
                <p className="text-amber-800 leading-relaxed">{inspection.description}</p>
                <p className="text-[11px] text-amber-700 font-medium">
                  Garuda automatically routes this specimen to the{' '}
                  <strong className="underline font-semibold">{inspection.detectedModality.toUpperCase()} Forensics Pipeline</strong>{' '}
                  to prevent container spoofing.
                </p>
              </div>
            </div>
          )}

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
