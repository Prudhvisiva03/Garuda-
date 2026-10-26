import { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Mic,
  Play,
  Pause,
  Upload,
  RefreshCw,
  Download,
  AlertTriangle,
  CheckCircle2,
  Activity,
  Layers,
  ShieldCheck,
  ShieldAlert,
  Info,
  Eye,
  FileText,
  Volume2,
} from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { formatFileSize } from '@/utils/formatters';
import {
  api,
  type ApiEvidence,
  type ApiAudioAnalysisResponse,
  type ApiIntegrityCheck,
} from '@/api/client';

export function AudioAnalysis() {
  const [searchParams, setSearchParams] = useSearchParams();
  const queryEvidenceId = searchParams.get('evidenceId');

  const [audioList, setAudioList] = useState<ApiEvidence[]>([]);
  const [selectedAudio, setSelectedAudio] = useState<ApiEvidence | null>(null);
  const [analysisData, setAnalysisData] = useState<ApiAudioAnalysisResponse | null>(null);

  const [activeTab, setActiveTab] = useState<'segments' | 'spectrogram' | 'synthetic' | 'findings'>('segments');
  const [isUploading, setIsUploading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [integrityStatus, setIntegrityStatus] = useState<ApiIntegrityCheck | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Audio player controls
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  // Load existing audio evidence on mount
  useEffect(() => {
    let isMounted = true;
    async function loadAudios() {
      try {
        const audios = await api.listAudios();
        if (!isMounted) return;
        setAudioList(audios);

        if (queryEvidenceId) {
          const found = audios.find((a) => a.id === queryEvidenceId);
          if (found) {
            setSelectedAudio(found);
          }
        } else if (audios.length > 0) {
          setSelectedAudio(audios[0]);
          setSearchParams({ evidenceId: audios[0].id });
        }
      } catch (err: unknown) {
        if (isMounted) {
          setErrorMsg(err instanceof Error ? err.message : 'Failed to load audio list');
        }
      }
    }
    loadAudios();
    return () => {
      isMounted = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // When selected audio changes, fetch or reset analysis
  useEffect(() => {
    if (!selectedAudio) {
      setAnalysisData(null);
      setIntegrityStatus(null);
      return;
    }

    let isMounted = true;
    async function fetchResults() {
      setErrorMsg(null);
      try {
        const results = await api.getAudioResults(selectedAudio!.id);
        if (isMounted) setAnalysisData(results);
      } catch {
        if (isMounted) setAnalysisData(null);
      }
    }
    fetchResults();
    return () => {
      isMounted = false;
    };
  }, [selectedAudio]);

  const handleTimeUpdate = () => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
    }
  };

  const handleLoadedMetadata = () => {
    if (audioRef.current) {
      setDuration(audioRef.current.duration);
    }
  };

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current.play();
      setIsPlaying(true);
    }
  };

  const seekTo = (seconds: number) => {
    if (audioRef.current) {
      audioRef.current.currentTime = seconds;
      setCurrentTime(seconds);
      if (!isPlaying) {
        audioRef.current.play();
        setIsPlaying(true);
      }
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setErrorMsg(null);
    try {
      const uploaded = await api.uploadAudio(file);
      setAudioList((prev) => [uploaded, ...prev]);
      setSelectedAudio(uploaded);
      setSearchParams({ evidenceId: uploaded.id });
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Audio intake failed');
    } finally {
      setIsUploading(false);
      event.target.value = '';
    }
  };

  const handleRunAnalysis = async () => {
    if (!selectedAudio) return;
    setIsAnalyzing(true);
    setErrorMsg(null);
    try {
      const results = await api.runAudioAnalysis(selectedAudio.id);
      setAnalysisData(results);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Forensic audio analysis failed');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleVerifyHash = async () => {
    if (!selectedAudio) return;
    setIsVerifying(true);
    try {
      const check = await api.verifyHash(selectedAudio.id);
      setIntegrityStatus(check);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Integrity verification failed');
    } finally {
      setIsVerifying(false);
    }
  };

  const tabs: Array<{
    id: 'segments' | 'spectrogram' | 'synthetic' | 'findings';
    label: string;
    icon: typeof Activity;
  }> = [
    { id: 'segments', label: 'Suspicious Segments & Edits', icon: Activity },
    { id: 'spectrogram', label: 'Waveform & Mel-Spectrogram', icon: Layers },
    { id: 'synthetic', label: 'Synthetic Voice Profiler', icon: Volume2 },
    { id: 'findings', label: 'Structured Findings', icon: FileText },
  ];

  return (
    <div className="space-y-6">
      {/* Top Banner / Title */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl sm:text-2xl font-semibold text-slate-900 tracking-tight">
              Audio &amp; Voice Forensics Workbench
            </h1>
            <Badge variant="info" dot className="font-mono text-[11px]">
              SWGDE COMPLIANT
            </Badge>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Short-time spectral flux acoustic splice detection, digital zero pause identification, ambient room noise floor estimation, and AI voice artifact analysis.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2 flex-wrap">
          <label className="cursor-pointer">
            <input
              type="file"
              accept=".mp3,.wav,.aac,.m4a"
              className="hidden"
              onChange={handleFileUpload}
              disabled={isUploading}
            />
            <Button
              type="button"
              variant="secondary"
              size="sm"
              isLoading={isUploading}
              leftIcon={<Upload className="w-4 h-4" />}
            >
              Upload Audio
            </Button>
          </label>

          {selectedAudio && (
            <>
              <Button
                type="button"
                variant="primary"
                size="sm"
                isLoading={isAnalyzing}
                onClick={handleRunAnalysis}
                leftIcon={<Play className="w-4 h-4" />}
              >
                Run Examination
              </Button>

              {analysisData && (
                <a
                  href={api.getAudioReportUrl(selectedAudio.id)}
                  download={`Garuda_Audio_Report_${selectedAudio.original_filename}.pdf`}
                  className="inline-flex"
                >
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    leftIcon={<Download className="w-4 h-4" />}
                  >
                    Export Report PDF
                  </Button>
                </a>
              )}
            </>
          )}
        </div>
      </div>

      {errorMsg && (
        <div className="bg-rose-50 border border-rose-200 text-rose-800 text-xs px-4 py-3 rounded-md flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-600 flex-shrink-0" />
            <span>{errorMsg}</span>
          </div>
          <button
            onClick={() => setErrorMsg(null)}
            className="text-rose-500 hover:text-rose-700 font-semibold"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Main Grid: Left Evidence & Audio Player / Right Forensics Workbench */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column (5 cols): Audio Evidence & Player */}
        <div className="lg:col-span-5 space-y-4">
          {/* Audio Selector Card */}
          <Card
            title="Audio Evidence Selection"
            headerAction={
              <span className="text-xs font-mono text-slate-500">
                {audioList.length} item{audioList.length === 1 ? '' : 's'}
              </span>
            }
          >
            {audioList.length === 0 ? (
              <EmptyState
                icon={<Mic className="w-8 h-8 text-slate-400" />}
                title="No audio evidence deposited"
                description="Upload an MP3, WAV, or AAC voice recording to begin forensic examination."
              />
            ) : (
              <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                {audioList.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => {
                      setSelectedAudio(item);
                      setSearchParams({ evidenceId: item.id });
                    }}
                    className={`w-full text-left p-2.5 rounded-md border text-xs transition-all flex items-center justify-between ${
                      selectedAudio?.id === item.id
                        ? 'border-cyan-500 bg-cyan-50/40 text-cyan-900 shadow-sm'
                        : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50/50 text-slate-700'
                    }`}
                  >
                    <div className="min-w-0 pr-2">
                      <div className="flex items-center gap-1.5 font-medium truncate">
                        <Mic className="w-3.5 h-3.5 text-cyan-600 flex-shrink-0" />
                        <span className="truncate">{item.original_filename}</span>
                      </div>
                      <div className="text-[11px] font-mono text-slate-500 mt-0.5">
                        {item.id} • {formatFileSize(item.file_size)}
                      </div>
                    </div>
                    <Badge
                      variant={item.status === 'analyzed' ? 'success' : 'neutral'}
                      className="capitalize flex-shrink-0 text-[10px]"
                    >
                      {item.status}
                    </Badge>
                  </button>
                ))}
              </div>
            )}
          </Card>

          {/* Audio Player Card */}
          {selectedAudio && (
            <Card title="Investigator Audio Playback">
              <div className="space-y-3">
                <audio
                  ref={audioRef}
                  src={api.getEvidenceFileUrl(selectedAudio.id)}
                  onTimeUpdate={handleTimeUpdate}
                  onLoadedMetadata={handleLoadedMetadata}
                  onEnded={() => setIsPlaying(false)}
                />

                <div className="p-4 bg-slate-900 rounded-lg text-white space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Volume2 className="w-4 h-4 text-cyan-400" />
                      <span className="text-xs font-mono font-medium truncate max-w-[200px]">
                        {selectedAudio.original_filename}
                      </span>
                    </div>
                    <span className="text-[11px] font-mono text-cyan-300">
                      {selectedAudio.mime_type}
                    </span>
                  </div>

                  <div className="space-y-1">
                    <div className="flex items-center justify-between text-xs font-mono text-slate-400">
                      <span>{currentTime.toFixed(2)}s</span>
                      <span>{duration.toFixed(2)}s</span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max={duration || 100}
                      step="0.01"
                      value={currentTime}
                      onChange={(e) => seekTo(parseFloat(e.target.value))}
                      className="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-cyan-400"
                    />
                  </div>

                  <div className="flex items-center justify-between pt-1">
                    <Button
                      type="button"
                      variant="primary"
                      size="sm"
                      onClick={togglePlay}
                      leftIcon={isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
                    >
                      {isPlaying ? 'Pause' : 'Play Audio'}
                    </Button>
                    <span className="text-[11px] font-mono text-slate-400">
                      {formatFileSize(selectedAudio.file_size)}
                    </span>
                  </div>
                </div>
              </div>
            </Card>
          )}

          {/* Cryptographic Chain of Custody Card */}
          {selectedAudio && (
            <Card
              title="Cryptographic Integrity"
              headerAction={
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  isLoading={isVerifying}
                  onClick={handleVerifyHash}
                  leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
                >
                  Verify Hash
                </Button>
              }
            >
              <div className="space-y-2.5 text-xs">
                <div>
                  <span className="text-slate-500 block text-[11px] uppercase tracking-wider font-semibold">
                    Intake SHA-256 Digest
                  </span>
                  <p className="font-mono text-slate-800 break-all bg-slate-50 p-2 rounded border border-slate-200 mt-1 select-all">
                    {selectedAudio.sha256_intake}
                  </p>
                </div>

                {integrityStatus && (
                  <div
                    className={`p-2.5 rounded border text-xs flex items-start gap-2 ${
                      integrityStatus.matches
                        ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                        : 'bg-rose-50 border-rose-200 text-rose-800'
                    }`}
                  >
                    {integrityStatus.matches ? (
                      <ShieldCheck className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
                    ) : (
                      <ShieldAlert className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
                    )}
                    <div>
                      <p className="font-semibold">{integrityStatus.status_label}</p>
                      <p className="text-[11px] mt-0.5">{integrityStatus.message}</p>
                    </div>
                  </div>
                )}
              </div>
            </Card>
          )}
        </div>

        {/* Right Column (7 cols): Forensics Workbench Results */}
        <div className="lg:col-span-7 space-y-4">
          {!selectedAudio ? (
            <Card>
              <EmptyState
                icon={<Mic className="w-8 h-8 text-slate-400" />}
                title="Select audio evidence"
                description="Select a deposited voice recording from the left or upload a new file to inspect acoustic metrics."
              />
            </Card>
          ) : !analysisData ? (
            <Card>
              <EmptyState
                icon={<Play className="w-8 h-8 text-slate-400" />}
                title="Analysis Pending"
                description="This audio evidence has not been examined yet. Click 'Run Examination' to execute spectral flux splice scanning, digital zero pause detection, and ambient noise floor profiling."
                action={
                  <Button
                    type="button"
                    variant="primary"
                    size="sm"
                    isLoading={isAnalyzing}
                    onClick={handleRunAnalysis}
                    leftIcon={<Play className="w-4 h-4" />}
                  >
                    Run Forensic Examination
                  </Button>
                }
              />
            </Card>
          ) : (
            <>
              {/* Executive Classification Banner */}
              <div
                className={`p-4 rounded-lg border flex items-start justify-between gap-3 ${
                  analysisData.classification === 'ai_synthesized_voice_detected'
                    ? 'bg-rose-50/70 border-rose-300'
                    : analysisData.classification === 'acoustic_splicing_detected'
                    ? 'bg-amber-50/70 border-amber-300'
                    : 'bg-emerald-50/70 border-emerald-300'
                }`}
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    {analysisData.classification === 'ai_synthesized_voice_detected' ? (
                      <AlertTriangle className="w-5 h-5 text-rose-600 flex-shrink-0" />
                    ) : analysisData.classification === 'acoustic_splicing_detected' ? (
                      <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0" />
                    ) : (
                      <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
                    )}
                    <h3 className="font-semibold text-slate-900 text-sm">
                      {analysisData.classification === 'ai_synthesized_voice_detected'
                        ? 'AI Synthesized / Generated Voice Detected'
                        : analysisData.classification === 'acoustic_splicing_detected'
                        ? 'Acoustic Splicing / Edit Boundaries Detected'
                        : 'Natural Speech Acoustic Consistency Verified'}
                    </h3>
                  </div>
                  <p className="text-xs text-slate-700 leading-relaxed">
                    {analysisData.summary_statement}
                  </p>
                </div>
                <Badge
                  variant={
                    analysisData.classification === 'ai_synthesized_voice_detected'
                      ? 'error'
                      : analysisData.classification === 'acoustic_splicing_detected'
                      ? 'warning'
                      : 'success'
                  }
                  className="uppercase font-mono text-[10px] tracking-wider flex-shrink-0"
                >
                  {analysisData.classification.replace(/_/g, ' ')}
                </Badge>
              </div>

              {/* Stream Telemetry Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="bg-white p-3 rounded-lg border border-slate-200">
                  <span className="text-[11px] text-slate-500 font-medium block">Sampling Rate</span>
                  <span className="text-sm font-semibold font-mono text-slate-900 mt-0.5 block">
                    {analysisData.audio_properties.sample_rate_hz} Hz
                  </span>
                  <span className="text-[10px] text-slate-400 font-mono">
                    {analysisData.audio_properties.channels} channel{analysisData.audio_properties.channels === 1 ? '' : 's'}
                  </span>
                </div>

                <div className="bg-white p-3 rounded-lg border border-slate-200">
                  <span className="text-[11px] text-slate-500 font-medium block">Duration</span>
                  <span className="text-sm font-semibold font-mono text-slate-900 mt-0.5 block">
                    {analysisData.audio_properties.duration_sec.toFixed(2)}s
                  </span>
                  <span className="text-[10px] text-slate-400 font-mono">
                    {analysisData.audio_properties.format}
                  </span>
                </div>

                <div className="bg-white p-3 rounded-lg border border-slate-200">
                  <span className="text-[11px] text-slate-500 font-medium block">Ambient Noise Floor</span>
                  <span
                    className={`text-sm font-semibold font-mono mt-0.5 block ${
                      analysisData.audio_properties.noise_floor_rms < 0.003
                        ? 'text-rose-600'
                        : 'text-slate-900'
                    }`}
                  >
                    {analysisData.audio_properties.noise_floor_rms.toFixed(5)}
                  </span>
                  <span className="text-[10px] text-slate-400 font-mono">
                    10th percentile RMS
                  </span>
                </div>

                <div className="bg-white p-3 rounded-lg border border-slate-200">
                  <span className="text-[11px] text-slate-500 font-medium block">Digital Silence Gaps</span>
                  <span
                    className={`text-sm font-semibold font-mono mt-0.5 block ${
                      analysisData.synthetic_indicators.digital_silence_ratio_pct > 4.0
                        ? 'text-rose-600'
                        : 'text-slate-900'
                    }`}
                  >
                    {analysisData.synthetic_indicators.digital_silence_ratio_pct.toFixed(1)}%
                  </span>
                  <span className="text-[10px] text-slate-400 font-mono">
                    {analysisData.synthetic_indicators.total_digital_silence_sec.toFixed(2)}s total
                  </span>
                </div>
              </div>

              {/* Forensic Details Tabs */}
              <Card>
                <div className="border-b border-slate-200 pb-3 mb-4">
                  <div className="flex gap-2 flex-wrap">
                    {tabs.map((tab) => {
                      const Icon = tab.icon;
                      return (
                        <button
                          key={tab.id}
                          onClick={() => setActiveTab(tab.id)}
                          className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                            activeTab === tab.id
                              ? 'bg-cyan-50 text-cyan-700 border border-cyan-200 shadow-sm'
                              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                          }`}
                        >
                          <Icon className="w-3.5 h-3.5" />
                          <span>{tab.label}</span>
                          {tab.id === 'segments' && (
                            <Badge
                              variant={
                                analysisData.suspicious_segments.length > 0
                                  ? 'warning'
                                  : 'neutral'
                              }
                              className="ml-1 text-[10px]"
                            >
                              {analysisData.suspicious_segments.length}
                            </Badge>
                          )}
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Tab 1: Suspicious Segments & Edits */}
                {activeTab === 'segments' && (
                  <div className="space-y-4">
                    <div className="bg-slate-50 p-3 rounded-md border border-slate-200 flex items-center justify-between text-xs">
                      <div>
                        <span className="font-semibold text-slate-800">
                          Acoustic Discontinuity &amp; Splice Scan
                        </span>
                        <p className="text-slate-500 mt-0.5">
                          Detects digital zero pause intervals (RMS &lt; 0.001) and Short-Time Spectral Flux spikes (Z &gt; 3.8&sigma;).
                        </p>
                      </div>
                      <Badge
                        variant={
                          analysisData.suspicious_segments.length > 0
                            ? 'warning'
                            : 'success'
                        }
                      >
                        {analysisData.suspicious_segments.length} anomal{analysisData.suspicious_segments.length === 1 ? 'y' : 'ies'} detected
                      </Badge>
                    </div>

                    {analysisData.suspicious_segments.length === 0 ? (
                      <EmptyState
                        icon={<CheckCircle2 className="w-8 h-8 text-emerald-500" />}
                        title="Continuous audio sequence"
                        description="No digital silence splices or abnormal spectral flux cut spikes were detected across the timeline."
                      />
                    ) : (
                      <div className="space-y-2.5 max-h-96 overflow-y-auto pr-1">
                        {analysisData.suspicious_segments.map((seg) => (
                          <div
                            key={seg.segment_index}
                            className={`p-3 bg-white border rounded-lg shadow-sm hover:border-cyan-400 transition-colors ${
                              seg.anomaly_type === 'digital_silence'
                                ? 'border-amber-200'
                                : 'border-rose-200'
                            }`}
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <span className="font-mono font-bold text-slate-800 text-xs">
                                  #{seg.segment_index}
                                </span>
                                <Badge
                                  variant={seg.severity === 'critical' ? 'error' : 'warning'}
                                  className="text-[10px]"
                                >
                                  {seg.anomaly_type.replace(/_/g, ' ').toUpperCase()}
                                </Badge>
                                <span className="text-xs text-slate-600 font-mono">
                                  {seg.start_sec.toFixed(2)}s &ndash; {seg.end_sec.toFixed(2)}s ({seg.duration_sec.toFixed(2)}s)
                                </span>
                              </div>
                              <Button
                                type="button"
                                variant="secondary"
                                size="sm"
                                onClick={() => seekTo(seg.start_sec)}
                                leftIcon={<Eye className="w-3.5 h-3.5" />}
                              >
                                Jump to Time
                              </Button>
                            </div>

                            <p className="text-xs text-slate-600 mt-2 leading-relaxed">
                              {seg.explanation}
                            </p>

                            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mt-2 pt-2 border-t border-slate-100 text-[11px] font-mono">
                              <div>
                                <span className="text-slate-400 block">Metric Value</span>
                                <span className="font-semibold text-slate-800">
                                  {seg.spectral_value.toFixed(4)}
                                </span>
                              </div>
                              <div>
                                <span className="text-slate-400 block">Z-Score</span>
                                <span className="font-semibold text-amber-600">
                                  {seg.z_score.toFixed(1)}&sigma;
                                </span>
                              </div>
                              <div>
                                <span className="text-slate-400 block">Severity Level</span>
                                <span className="font-semibold text-slate-700 capitalize">
                                  {seg.severity}
                                </span>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Tab 2: Waveform & Mel-Spectrogram */}
                {activeTab === 'spectrogram' && (
                  <div className="space-y-4">
                    <p className="text-xs text-slate-500">
                      Two-panel calibrated forensic visualization: time-domain amplitude waveform with color-shaded suspicious intervals (top) and Mel-Spectrogram frequency density from 0 to 11 kHz (bottom).
                    </p>

                    {analysisData.spectrogram_artifact ? (
                      <div className="border border-slate-200 rounded-lg overflow-hidden bg-black p-2 shadow-sm">
                        <img
                          src={api.getAudioArtifactUrl(analysisData.spectrogram_artifact)}
                          alt={`Spectrogram ${analysisData.evidence_id}`}
                          className="w-full h-auto object-contain"
                          loading="lazy"
                        />
                      </div>
                    ) : (
                      <EmptyState
                        icon={<Activity className="w-8 h-8 text-slate-400" />}
                        title="Spectrogram not generated"
                        description="Re-run forensic examination to produce calibrated spectral density visualization."
                      />
                    )}
                  </div>
                )}

                {/* Tab 3: Synthetic Voice Profiler */}
                {activeTab === 'synthetic' && (
                  <div className="space-y-4">
                    <div
                      className={`p-3.5 rounded-lg border flex items-center justify-between ${
                        analysisData.synthetic_indicators.synthetic_voice_detected
                          ? 'bg-rose-50/60 border-rose-300'
                          : 'bg-emerald-50/60 border-emerald-300'
                      }`}
                    >
                      <div className="flex items-center gap-2.5">
                        <Volume2 className="w-5 h-5 text-rose-600" />
                        <div>
                          <h4 className="font-semibold text-slate-900 text-xs">
                            {analysisData.synthetic_indicators.synthetic_voice_detected
                              ? 'Synthetic / AI Voice Artifacts Identified'
                              : 'Physical Acoustic Environment Verified'}
                          </h4>
                          <p className="text-[11px] text-slate-600 mt-0.5">
                            {analysisData.synthetic_indicators.synthetic_voice_detected
                              ? 'Suppressed ambient noise floor and digital zero pause intervals indicate neural vocoder text-to-speech synthesis.'
                              : 'Continuous background room acoustic reflections consistent with natural human vocalization recorded via physical microphone.'}
                          </p>
                        </div>
                      </div>
                      <Badge
                        variant={
                          analysisData.synthetic_indicators.synthetic_voice_detected
                            ? 'error'
                            : 'success'
                        }
                      >
                        {analysisData.synthetic_indicators.synthetic_voice_detected
                          ? 'AI SYNTHESIZED'
                          : 'NATURAL VOICE'}
                      </Badge>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      <div className="p-3 bg-white rounded-lg border border-slate-200">
                        <span className="text-xs text-slate-500 font-medium block">
                          Ambient Noise Floor RMS
                        </span>
                        <span className="text-lg font-bold font-mono text-slate-900 mt-1 block">
                          {analysisData.synthetic_indicators.noise_floor_rms.toFixed(5)}
                        </span>
                        <span className="text-[10px] text-slate-500 block mt-1">
                          Values &lt; 0.003 indicate artificial digital silence
                        </span>
                      </div>

                      <div className="p-3 bg-white rounded-lg border border-slate-200">
                        <span className="text-xs text-slate-500 font-medium block">
                          Digital Silence Ratio
                        </span>
                        <span className="text-lg font-bold font-mono text-slate-900 mt-1 block">
                          {analysisData.synthetic_indicators.digital_silence_ratio_pct.toFixed(1)}%
                        </span>
                        <span className="text-[10px] text-slate-500 block mt-1">
                          {analysisData.synthetic_indicators.total_digital_silence_sec.toFixed(2)}s non-acoustic pauses
                        </span>
                      </div>

                      <div className="p-3 bg-white rounded-lg border border-slate-200">
                        <span className="text-xs text-slate-500 font-medium block">
                          Spectral Rolloff (85% / 95%)
                        </span>
                        <span className="text-lg font-bold font-mono text-slate-900 mt-1 block">
                          {analysisData.synthetic_indicators.spectral_rolloff_85_hz.toFixed(0)} Hz
                        </span>
                        <span className="text-[10px] text-slate-500 block mt-1">
                          95% cutoff at {analysisData.synthetic_indicators.spectral_rolloff_95_hz.toFixed(0)} Hz
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Tab 4: Structured Findings */}
                {activeTab === 'findings' && (
                  <div className="space-y-3">
                    <p className="text-xs text-slate-500">
                      Scientific, verifiable findings recorded in compliance with SWGDE Digital Audio Forensic Examination Guidelines.
                    </p>

                    {analysisData.findings.map((f, i) => (
                      <div
                        key={i}
                        className="p-3.5 bg-white border border-slate-200 rounded-lg space-y-2 text-xs"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-slate-900 font-mono text-[11px]">
                              {f.test_performed}
                            </span>
                            <Badge
                              variant={
                                f.severity === 'high' || f.severity === 'critical'
                                  ? 'error'
                                  : f.severity === 'medium'
                                  ? 'warning'
                                  : 'info'
                              }
                              className="uppercase text-[9px]"
                            >
                              {f.severity}
                            </Badge>
                          </div>
                          <span className="text-[10px] font-mono text-slate-400">
                            {f.analysis_type}
                          </span>
                        </div>

                        <div>
                          <span className="text-[11px] text-slate-500 font-medium block">
                            Observed Result:
                          </span>
                          <p className="text-slate-800 mt-0.5">{f.observed_result}</p>
                        </div>

                        <div>
                          <span className="text-[11px] text-slate-500 font-medium block">
                            Forensic Interpretation:
                          </span>
                          <p className="text-slate-600 mt-0.5 leading-relaxed">
                            {f.explanation}
                          </p>
                        </div>

                        {f.limitations && (
                          <div className="pt-2 border-t border-slate-100 text-[11px] text-slate-500 flex items-start gap-1.5">
                            <Info className="w-3.5 h-3.5 text-slate-400 flex-shrink-0 mt-0.5" />
                            <span>
                              <strong>Scientific Limitation:</strong> {f.limitations}
                            </span>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
