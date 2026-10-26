import { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Film,
  Play,
  Pause,
  Upload,
  RefreshCw,
  Download,
  AlertTriangle,
  CheckCircle2,
  Layers,
  Palette,
  ShieldCheck,
  ShieldAlert,
  Info,
  Scissors,
  Eye,
  FileText,
} from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { formatFileSize } from '@/utils/formatters';
import {
  api,
  type ApiEvidence,
  type ApiVideoAnalysisResponse,
  type ApiIntegrityCheck,
} from '@/api/client';

export function VideoAnalysis() {
  const [searchParams, setSearchParams] = useSearchParams();
  const queryEvidenceId = searchParams.get('evidenceId');

  const [videoList, setVideoList] = useState<ApiEvidence[]>([]);
  const [selectedVideo, setSelectedVideo] = useState<ApiEvidence | null>(null);
  const [analysisData, setAnalysisData] = useState<ApiVideoAnalysisResponse | null>(null);

  const [activeTab, setActiveTab] = useState<'cuts' | 'color' | 'keyframes' | 'findings'>('cuts');
  const [isUploading, setIsUploading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [integrityStatus, setIntegrityStatus] = useState<ApiIntegrityCheck | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Video player controls
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  // Load existing videos on mount
  useEffect(() => {
    let isMounted = true;
    async function loadVideos() {
      try {
        const videos = await api.listVideos();
        if (!isMounted) return;
        setVideoList(videos);

        // Select from query param or first available
        if (queryEvidenceId) {
          const found = videos.find((v) => v.id === queryEvidenceId);
          if (found) {
            setSelectedVideo(found);
          }
        } else if (videos.length > 0) {
          setSelectedVideo(videos[0]);
          setSearchParams({ evidenceId: videos[0].id });
        }
      } catch (err: unknown) {
        if (isMounted) {
          setErrorMsg(err instanceof Error ? err.message : 'Failed to load video list');
        }
      }
    }
    loadVideos();
    return () => {
      isMounted = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // When selected video changes, fetch or run analysis
  useEffect(() => {
    if (!selectedVideo) {
      setAnalysisData(null);
      setIntegrityStatus(null);
      return;
    }

    let isMounted = true;
    async function fetchResults() {
      setErrorMsg(null);
      try {
        const results = await api.getVideoResults(selectedVideo!.id);
        if (isMounted) setAnalysisData(results);
      } catch {
        // Not analyzed yet, will show "Run Analysis" prompt
        if (isMounted) setAnalysisData(null);
      }
    }
    fetchResults();
    return () => {
      isMounted = false;
    };
  }, [selectedVideo]);

  // Video playback time updates
  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
    }
  };

  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration);
    }
  };

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
      setIsPlaying(false);
    } else {
      videoRef.current.play();
      setIsPlaying(true);
    }
  };

  const seekTo = (seconds: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = seconds;
      setCurrentTime(seconds);
      if (!isPlaying) {
        videoRef.current.play();
        setIsPlaying(true);
      }
    }
  };

  // Upload handler
  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setErrorMsg(null);
    try {
      const uploaded = await api.uploadVideo(file);
      setVideoList((prev) => [uploaded, ...prev]);
      setSelectedVideo(uploaded);
      setSearchParams({ evidenceId: uploaded.id });
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Video intake failed');
    } finally {
      setIsUploading(false);
      event.target.value = '';
    }
  };

  // Run analysis handler
  const handleRunAnalysis = async () => {
    if (!selectedVideo) return;
    setIsAnalyzing(true);
    setErrorMsg(null);
    try {
      const results = await api.runVideoAnalysis(selectedVideo.id);
      setAnalysisData(results);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Forensic analysis failed');
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Verify hash handler
  const handleVerifyHash = async () => {
    if (!selectedVideo) return;
    setIsVerifying(true);
    try {
      const check = await api.verifyHash(selectedVideo.id);
      setIntegrityStatus(check);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Integrity check failed');
    } finally {
      setIsVerifying(false);
    }
  };

  const tabs: Array<{ id: 'cuts' | 'color' | 'keyframes' | 'findings'; label: string; icon: typeof Scissors }> = [
    { id: 'cuts', label: 'Temporal Cuts & Splicing', icon: Scissors },
    { id: 'color', label: 'Color & Theme Grading', icon: Palette },
    { id: 'keyframes', label: 'Keyframes & PRNU Noise', icon: Layers },
    { id: 'findings', label: 'Structured Findings', icon: FileText },
  ];

  return (
    <div className="space-y-6">
      {/* Top Banner / Title */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl sm:text-2xl font-semibold text-slate-900 tracking-tight">
              Video Forensics Workbench
            </h1>
            <Badge variant="info" dot className="font-mono text-[11px]">
              SWGDE COMPLIANT
            </Badge>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Frame-accurate cut detection, synthetic monochrome grading analysis, container vs elementary stream timing, and keyframe sensor noise baseline.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2 flex-wrap">
          <label className="cursor-pointer">
            <input
              type="file"
              accept=".mp4,.mov,.avi,.xls,.xlsx,video/*,*"
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
              Upload Video
            </Button>
          </label>

          {selectedVideo && (
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
                  href={api.getVideoReportUrl(selectedVideo.id)}
                  download={`Garuda_Video_Report_${selectedVideo.original_filename}.pdf`}
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

      {/* Main Grid: Left Evidence & Video Preview / Right Forensics Workbench */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column (5 cols): Evidence Selection & Video Player */}
        <div className="lg:col-span-5 space-y-4">
          {/* Evidence Selector Card */}
          <Card
            title="Video Evidence Selection"
            headerAction={
              <span className="text-xs font-mono text-slate-500">
                {videoList.length} item{videoList.length === 1 ? '' : 's'}
              </span>
            }
          >
            {videoList.length === 0 ? (
              <EmptyState
                icon={<Film className="w-8 h-8 text-slate-400" />}
                title="No video evidence deposited"
                description="Upload an MP4, MOV, or AVI video to begin forensic examination."
              />
            ) : (
              <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                {videoList.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => {
                      setSelectedVideo(item);
                      setSearchParams({ evidenceId: item.id });
                    }}
                    className={`w-full text-left p-2.5 rounded-md border text-xs transition-all flex items-center justify-between ${
                      selectedVideo?.id === item.id
                        ? 'border-cyan-500 bg-cyan-50/40 text-cyan-900 shadow-sm'
                        : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50/50 text-slate-700'
                    }`}
                  >
                    <div className="min-w-0 pr-2">
                      <div className="flex items-center gap-1.5 font-medium truncate">
                        <Film className="w-3.5 h-3.5 text-cyan-600 flex-shrink-0" />
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

          {/* Video Player Card */}
          {selectedVideo && (
            <Card title="Investigator Video Playback">
              <div className="space-y-3">
                <div className="relative bg-black rounded-lg overflow-hidden border border-slate-900 aspect-video flex items-center justify-center">
                  <video
                    ref={videoRef}
                    src={api.getEvidenceFileUrl(selectedVideo.id)}
                    className="w-full h-full object-contain"
                    onTimeUpdate={handleTimeUpdate}
                    onLoadedMetadata={handleLoadedMetadata}
                    onEnded={() => setIsPlaying(false)}
                    controls={false}
                  />
                  {!isPlaying && (
                    <button
                      onClick={togglePlay}
                      className="absolute inset-0 m-auto w-12 h-12 bg-black/60 hover:bg-black/80 text-white rounded-full flex items-center justify-center backdrop-blur-sm transition-transform hover:scale-105"
                      aria-label="Play video"
                    >
                      <Play className="w-5 h-5 ml-0.5" />
                    </button>
                  )}
                </div>

                {/* Player Scrubber & Controls */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs font-mono text-slate-600">
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
                    className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-cyan-600"
                  />
                  <div className="flex items-center justify-between pt-1">
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={togglePlay}
                      leftIcon={isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
                    >
                      {isPlaying ? 'Pause' : 'Play'}
                    </Button>
                    <span className="text-[11px] font-mono text-slate-500">
                      {selectedVideo.width}×{selectedVideo.height} px
                    </span>
                  </div>
                </div>
              </div>
            </Card>
          )}

          {/* Cryptographic Chain of Custody Card */}
          {selectedVideo && (
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
                    {selectedVideo.sha256_intake}
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
          {!selectedVideo ? (
            <Card>
              <EmptyState
                icon={<Film className="w-8 h-8 text-slate-400" />}
                title="Select video evidence"
                description="Select a deposited video from the left or upload a new file to inspect forensic metrics."
              />
            </Card>
          ) : !analysisData ? (
            <Card>
              <EmptyState
                icon={<Play className="w-8 h-8 text-slate-400" />}
                title="Analysis Pending"
                description="This video evidence has not been examined yet. Click 'Run Examination' to execute temporal cut analysis, color grading detection, and keyframe extraction."
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
                  analysisData.classification === 'video_tampering_detected'
                    ? 'bg-amber-50/70 border-amber-300'
                    : 'bg-emerald-50/70 border-emerald-300'
                }`}
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    {analysisData.classification === 'video_tampering_detected' ? (
                      <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0" />
                    ) : (
                      <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
                    )}
                    <h3 className="font-semibold text-slate-900 text-sm">
                      {analysisData.classification === 'video_tampering_detected'
                        ? 'Video Tampering / Editing Detected'
                        : 'No Discontinuities Detected (Consistent Stream)'}
                    </h3>
                  </div>
                  <p className="text-xs text-slate-700 leading-relaxed">
                    {analysisData.summary_statement}
                  </p>
                </div>
                <Badge
                  variant={analysisData.classification === 'video_tampering_detected' ? 'warning' : 'success'}
                  className="uppercase font-mono text-[10px] tracking-wider flex-shrink-0"
                >
                  {analysisData.classification.replace(/_/g, ' ')}
                </Badge>
              </div>

              {/* Stream Telemetry Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="bg-white p-3 rounded-lg border border-slate-200">
                  <span className="text-[11px] text-slate-500 font-medium block">Resolution</span>
                  <span className="text-sm font-semibold font-mono text-slate-900 mt-0.5 block">
                    {analysisData.video_properties.resolution}
                  </span>
                  <span className="text-[10px] text-slate-400 font-mono">
                    {analysisData.video_properties.codec}
                  </span>
                </div>

                <div className="bg-white p-3 rounded-lg border border-slate-200">
                  <span className="text-[11px] text-slate-500 font-medium block">Decoded Duration</span>
                  <span className="text-sm font-semibold font-mono text-slate-900 mt-0.5 block">
                    {analysisData.video_properties.decoded_duration_sec.toFixed(2)}s
                  </span>
                  <span className="text-[10px] text-slate-400 font-mono">
                    {analysisData.video_properties.total_frames} frames @ {analysisData.video_properties.fps.toFixed(1)} fps
                  </span>
                </div>

                <div className="bg-white p-3 rounded-lg border border-slate-200">
                  <span className="text-[11px] text-slate-500 font-medium block">Container Duration</span>
                  <span className="text-sm font-semibold font-mono text-slate-900 mt-0.5 block">
                    {analysisData.video_properties.container_duration_sec
                      ? `${analysisData.video_properties.container_duration_sec.toFixed(2)}s`
                      : 'N/A'}
                  </span>
                  <span className="text-[10px] text-slate-400 font-mono">
                    mvhd atom header
                  </span>
                </div>

                <div className="bg-white p-3 rounded-lg border border-slate-200">
                  <span className="text-[11px] text-slate-500 font-medium block">Audio/Video Skew</span>
                  <span
                    className={`text-sm font-semibold font-mono mt-0.5 block ${
                      Math.abs(analysisData.video_properties.audio_video_skew_sec) > 0.1
                        ? 'text-amber-600'
                        : 'text-slate-900'
                    }`}
                  >
                    {analysisData.video_properties.audio_video_skew_sec >= 0 ? '+' : ''}
                    {analysisData.video_properties.audio_video_skew_sec.toFixed(2)}s
                  </span>
                  <span className="text-[10px] text-slate-400 font-mono">
                    container mismatch
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
                          {tab.id === 'cuts' && (
                            <Badge
                              variant={
                                analysisData.temporal_cuts.total_cuts_detected > 0
                                  ? 'warning'
                                  : 'neutral'
                              }
                              className="ml-1 text-[10px]"
                            >
                              {analysisData.temporal_cuts.total_cuts_detected}
                            </Badge>
                          )}
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Tab 1: Temporal Cuts & Splicing */}
                {activeTab === 'cuts' && (
                  <div className="space-y-4">
                    <div className="bg-slate-50 p-3.5 rounded-lg border border-slate-200 space-y-2 text-xs">
                      <div className="flex items-center justify-between">
                        <div>
                          <span className="font-semibold text-slate-800 text-sm">
                            Multi-Scale Adaptive Temporal Cut Detector
                          </span>
                          <p className="text-slate-500 text-[11px] mt-0.5">
                            Detects inter-frame splices using Bhattacharyya distance on normalized 3D color histograms.
                          </p>
                        </div>
                        <Badge
                          variant={
                            analysisData.temporal_cuts.total_cuts_detected > 0
                              ? 'warning'
                              : 'success'
                          }
                          className="font-mono text-xs"
                        >
                          {analysisData.temporal_cuts.total_cuts_detected} cut{analysisData.temporal_cuts.total_cuts_detected === 1 ? '' : 's'} detected
                        </Badge>
                      </div>

                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-slate-200/80 font-mono text-[11px]">
                        <div className="bg-white p-2 rounded border border-slate-200">
                          <span className="text-slate-400 block text-[10px]">D_B Cut Threshold</span>
                          <span className="font-bold text-slate-800">
                            &gt; {analysisData.temporal_cuts.thresholds.bhatt_abs_threshold || 0.32}
                          </span>
                        </div>
                        <div className="bg-white p-2 rounded border border-slate-200">
                          <span className="text-slate-400 block text-[10px]">Z-Score Threshold</span>
                          <span className="font-bold text-slate-800">
                            &gt; {analysisData.temporal_cuts.thresholds.bhatt_z_threshold || 5.0}σ
                          </span>
                        </div>
                        <div className="bg-white p-2 rounded border border-slate-200">
                          <span className="text-slate-400 block text-[10px]">Sampling Stride</span>
                          <span className="font-bold text-slate-800">
                            {analysisData.temporal_cuts.sampling_stride || 2} frames
                          </span>
                        </div>
                        <div className="bg-white p-2 rounded border border-slate-200">
                          <span className="text-slate-400 block text-[10px]">Verification Model</span>
                          <span className="font-bold text-cyan-700">
                            Impulse 1-Frame
                          </span>
                        </div>
                      </div>
                    </div>

                    {analysisData.temporal_cuts.cuts.length === 0 ? (
                      <EmptyState
                        icon={<CheckCircle2 className="w-8 h-8 text-emerald-500" />}
                        title="Continuous video sequence"
                        description="No abrupt scene cuts or frame splices were detected in the sampled frame stream. Histograms exhibit natural temporal continuity."
                      />
                    ) : (
                      <div className="space-y-2.5">
                        {analysisData.temporal_cuts.cuts.map((cut) => (
                          <div
                            key={cut.cut_index}
                            className="p-3 bg-white border border-amber-200 rounded-lg shadow-sm hover:border-cyan-400 transition-colors"
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <span className="font-mono font-bold text-amber-700 text-xs">
                                  Cut #{cut.cut_index}
                                </span>
                                <Badge variant="warning" className="text-[10px]">
                                  {cut.cut_type.replace(/_/g, ' ')}
                                </Badge>
                                <span className="text-xs text-slate-500 font-mono">
                                  Frame #{cut.frame_index} ({cut.timestamp_sec.toFixed(2)}s)
                                </span>
                              </div>
                              <Button
                                type="button"
                                variant="secondary"
                                size="sm"
                                onClick={() => seekTo(cut.timestamp_sec)}
                                leftIcon={<Eye className="w-3.5 h-3.5" />}
                              >
                                Jump to Frame
                              </Button>
                            </div>

                            <p className="text-xs text-slate-600 mt-2 leading-relaxed">
                              {cut.explanation}
                            </p>

                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-3 pt-2.5 border-t border-slate-100 text-[11px] font-mono">
                              <div>
                                <span className="text-slate-400 block">Bhattacharyya D_B</span>
                                <span className="font-semibold text-slate-800">
                                  {cut.bhattacharyya_distance.toFixed(3)}
                                </span>
                              </div>
                              <div>
                                <span className="text-slate-400 block">Z-Score</span>
                                <span className="font-semibold text-amber-600">
                                  {cut.bhatt_z_score.toFixed(1)}σ
                                </span>
                              </div>
                              <div>
                                <span className="text-slate-400 block">Pixel Delta (MAE)</span>
                                <span className="font-semibold text-slate-800">
                                  {cut.pixel_delta.toFixed(1)}
                                </span>
                              </div>
                              <div>
                                <span className="text-slate-400 block">Pixel Z-Score</span>
                                <span className="font-semibold text-slate-800">
                                  {cut.pixel_z_score.toFixed(1)}σ
                                </span>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Tab 2: Color & Theme Grading */}
                {activeTab === 'color' && (
                  <div className="space-y-4">
                    <div
                      className={`p-3.5 rounded-lg border flex items-center justify-between ${
                        analysisData.color_profile.night_theme_detected
                          ? 'bg-purple-50/60 border-purple-300'
                          : 'bg-emerald-50/60 border-emerald-300'
                      }`}
                    >
                      <div className="flex items-center gap-2.5">
                        <Palette className="w-5 h-5 text-purple-600" />
                        <div>
                          <h4 className="font-semibold text-slate-900 text-xs">
                            {analysisData.color_profile.night_theme_detected
                              ? 'Synthetic Monochrome / Night Theme Detected'
                              : 'Natural Full-Gamut Color Profile'}
                          </h4>
                          <p className="text-[11px] text-slate-600 mt-0.5">
                            {analysisData.color_profile.night_theme_detected
                              ? 'Severe HSV saturation suppression and inter-channel correlation indicate post-processing desaturation filter.'
                              : 'Normal chroma distribution consistent with unmodified sensor color recording.'}
                          </p>
                        </div>
                      </div>
                      <Badge
                        variant={analysisData.color_profile.night_theme_detected ? 'warning' : 'success'}
                      >
                        {analysisData.color_profile.night_theme_detected ? 'FILTERED' : 'NATURAL'}
                      </Badge>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      <div className="p-3 bg-white rounded-lg border border-slate-200">
                        <span className="text-xs text-slate-500 font-medium block">
                          Mean Saturation (HSV S-channel)
                        </span>
                        <span className="text-lg font-bold font-mono text-slate-900 mt-1 block">
                          {analysisData.color_profile.mean_saturation.toFixed(1)}
                          <span className="text-xs text-slate-400 font-normal"> / 255</span>
                        </span>
                        <span className="text-[10px] text-slate-500 block mt-1">
                          Threshold: &lt; 32.0 indicates severe desaturation
                        </span>
                      </div>

                      <div className="p-3 bg-white rounded-lg border border-slate-200">
                        <span className="text-xs text-slate-500 font-medium block">
                          RGB Cross-Channel Correlation
                        </span>
                        <span className="text-lg font-bold font-mono text-slate-900 mt-1 block">
                          {analysisData.color_profile.channel_correlation.toFixed(4)}
                        </span>
                        <span className="text-[10px] text-slate-500 block mt-1">
                          Values &gt; 0.98 indicate color channels collapsed to monochrome
                        </span>
                      </div>

                      <div className="p-3 bg-white rounded-lg border border-slate-200">
                        <span className="text-xs text-slate-500 font-medium block">
                          Mean Luminance (HSV V-channel)
                        </span>
                        <span className="text-lg font-bold font-mono text-slate-900 mt-1 block">
                          {analysisData.color_profile.mean_luminance.toFixed(1)}
                          <span className="text-xs text-slate-400 font-normal"> / 255</span>
                        </span>
                        <span className="text-[10px] text-slate-500 block mt-1">
                          Average brightness across sampled frames
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Tab 3: Keyframes & PRNU Noise */}
                {activeTab === 'keyframes' && (
                  <div className="space-y-4">
                    <p className="text-xs text-slate-500">
                      Extracted keyframes representative of opening, midpoint, and concluding scenes, plus transition boundaries detected during temporal cut scanning. Noise residual variance reflects sensor PRNU and compression consistency.
                    </p>

                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                      {analysisData.keyframes.map((kf, idx) => (
                        <div
                          key={idx}
                          className="bg-white border border-slate-200 rounded-lg overflow-hidden shadow-sm hover:border-cyan-400 transition-all flex flex-col"
                        >
                          <div className="relative aspect-video bg-black flex items-center justify-center overflow-hidden">
                            <img
                              src={api.getVideoArtifactUrl(kf.artifact_name)}
                              alt={`Keyframe ${kf.frame_index}`}
                              className="w-full h-full object-cover"
                              loading="lazy"
                            />
                            <div className="absolute top-2 left-2 flex gap-1">
                              <span className="px-1.5 py-0.5 rounded bg-black/70 text-white font-mono text-[10px] backdrop-blur-sm">
                                {kf.timestamp_sec.toFixed(2)}s
                              </span>
                              {kf.is_cut_frame && (
                                <span className="px-1.5 py-0.5 rounded bg-amber-600 text-white font-mono text-[10px] font-semibold">
                                  CUT FRAME
                                </span>
                              )}
                            </div>
                          </div>

                          <div className="p-2.5 flex-1 flex flex-col justify-between text-xs font-mono">
                            <div className="flex items-center justify-between text-slate-600">
                              <span>Frame #{kf.frame_index}</span>
                              <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                onClick={() => seekTo(kf.timestamp_sec)}
                                className="h-6 px-1.5 text-[11px]"
                              >
                                Seek
                              </Button>
                            </div>
                            <div className="mt-1 pt-1 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
                              <span>Noise Res Var:</span>
                              <span className="font-semibold text-slate-700">
                                {kf.noise_variance.toFixed(2)}
                              </span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Tab 4: Structured Findings */}
                {activeTab === 'findings' && (
                  <div className="space-y-3">
                    <p className="text-xs text-slate-500">
                      Scientific, verifiable findings recorded in compliance with SWGDE Digital Video Forensic Examination Guidelines.
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
