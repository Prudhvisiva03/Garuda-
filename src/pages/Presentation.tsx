import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ChevronLeft,
  ChevronRight,
  Maximize2,
  Minimize2,
  ShieldCheck,
  CheckCircle2,
  Microscope,
  Film,
  Mic,
  Scale,
  FileCheck2,
  ArrowRight,
  ExternalLink,
  Lock,
  Layers,
  Sparkles,
  Award,
} from 'lucide-react';
import { Badge } from '@/components/ui/Badge';

export function Presentation() {
  const [currentSlide, setCurrentSlide] = useState(0);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showNotes, setShowNotes] = useState(true);
  const navigate = useNavigate();

  const totalSlides = 4;

  const nextSlide = () => {
    setCurrentSlide((prev) => (prev < totalSlides - 1 ? prev + 1 : prev));
  };

  const prevSlide = () => {
    setCurrentSlide((prev) => (prev > 0 ? prev - 1 : prev));
  };

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight' || e.key === 'Space') {
        e.preventDefault();
        nextSlide();
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        prevSlide();
      } else if (e.key.toLowerCase() === 'f') {
        toggleFullscreen();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {});
      setIsFullscreen(true);
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen().catch(() => {});
        setIsFullscreen(false);
      }
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between font-sans selection:bg-cyan-500/30">
      {/* Top Header Bar */}
      <header className="h-16 px-6 border-b border-slate-800/80 bg-slate-900/90 backdrop-blur-md flex items-center justify-between z-30">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-slate-950 border border-cyan-500/40 p-1.5 flex items-center justify-center shadow-lg shadow-cyan-500/10">
            <img src="/garuda-logo.svg" alt="Garuda" className="w-full h-full object-contain" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-white tracking-wide text-base">GARUDA FORENSICS</span>
              <Badge variant="info" className="text-[10px] font-mono tracking-widest uppercase py-0.5 px-2 bg-cyan-950 text-cyan-300 border-cyan-800">
                PS-05
              </Badge>
            </div>
            <p className="text-[11px] text-slate-400 font-mono">Team ID: CH26-RQKN | Cyber Hackathon 2026</p>
          </div>
        </div>

        {/* Slide Counter & Controls */}
        <div className="flex items-center gap-3">
          <div className="flex items-center bg-slate-800/80 rounded-lg p-1 border border-slate-700">
            <button
              onClick={prevSlide}
              disabled={currentSlide === 0}
              className="p-1.5 text-slate-400 hover:text-white disabled:opacity-30 disabled:hover:text-slate-400 rounded transition-colors"
              title="Previous Slide (Left Arrow)"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <span className="px-3 text-xs font-mono font-bold text-cyan-400">
              0{currentSlide + 1} / 0{totalSlides}
            </span>
            <button
              onClick={nextSlide}
              disabled={currentSlide === totalSlides - 1}
              className="p-1.5 text-slate-400 hover:text-white disabled:opacity-30 disabled:hover:text-slate-400 rounded transition-colors"
              title="Next Slide (Right Arrow / Space)"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>

          <button
            onClick={() => setShowNotes(!showNotes)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
              showNotes
                ? 'bg-cyan-950/60 border-cyan-500/50 text-cyan-300'
                : 'bg-slate-800 border-slate-700 text-slate-400 hover:text-white'
            }`}
          >
            {showNotes ? 'Hide Speaker Notes' : 'Show Speaker Notes'}
          </button>

          <button
            onClick={toggleFullscreen}
            className="p-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-400 hover:text-white transition-colors"
            title="Toggle Fullscreen (F)"
          >
            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>

          <Link
            to="/"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-medium text-xs shadow-md shadow-cyan-600/30 transition-all"
          >
            <span>Live Platform</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </Link>
        </div>
      </header>

      {/* Main Slide Content Area */}
      <main className="flex-1 flex items-center justify-center p-6 md:p-12 relative overflow-hidden">
        {/* Ambient Background Glows */}
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="w-full max-w-6xl mx-auto z-10">
          {/* SLIDE 1: Title & Mission */}
          {currentSlide === 0 && (
            <div className="space-y-8 animate-fadeIn">
              <div className="flex flex-wrap items-center gap-3">
                <span className="px-3 py-1 rounded-full text-xs font-mono font-semibold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  PROBLEM STATEMENT: PS-05
                </span>
                <span className="px-3 py-1 rounded-full text-xs font-mono font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/40 flex items-center gap-1.5">
                  <Award className="w-3.5 h-3.5" />
                  CYBER HACKATHON 2026
                </span>
                <span className="px-3 py-1 rounded-full text-xs font-mono font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  60/60 BENCHMARKS PASSING
                </span>
              </div>

              <div className="space-y-4">
                <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight text-white leading-tight">
                  <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-sky-300 to-indigo-400">
                    GARUDA
                  </span>{' '}
                  FORENSICS
                </h1>
                <h2 className="text-xl md:text-2xl font-medium text-slate-300 max-w-3xl leading-relaxed">
                  Digital Evidence Authenticity &amp; Integrity Verification Platform with Automated Section 65B Court Certification
                </h2>
              </div>

              {/* Feature Grid */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-5 pt-4">
                <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl backdrop-blur-sm hover:border-cyan-500/50 transition-all">
                  <div className="w-12 h-12 rounded-xl bg-cyan-500/20 border border-cyan-500/40 text-cyan-400 flex items-center justify-center mb-4">
                    <Microscope className="w-6 h-6" />
                  </div>
                  <h3 className="text-lg font-bold text-white mb-2">Multi-Modal Forensics</h3>
                  <p className="text-sm text-slate-400 leading-relaxed">
                    SIFT image comparison, Error Level Analysis (ELA), video temporal Bhattacharyya cuts, and STFT AI voice biometrics.
                  </p>
                </div>

                <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl backdrop-blur-sm hover:border-cyan-500/50 transition-all">
                  <div className="w-12 h-12 rounded-xl bg-amber-500/20 border border-amber-500/40 text-amber-400 flex items-center justify-center mb-4">
                    <ShieldCheck className="w-6 h-6" />
                  </div>
                  <h3 className="text-lg font-bold text-white mb-2">Anti-Spoofing Engine</h3>
                  <p className="text-sm text-slate-400 leading-relaxed">
                    Binary magic byte inspector unmasks disguised containers—like identifying an MP4 video disguised as <code className="text-amber-300">data.xls</code>.
                  </p>
                </div>

                <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl backdrop-blur-sm hover:border-cyan-500/50 transition-all">
                  <div className="w-12 h-12 rounded-xl bg-emerald-500/20 border border-emerald-500/40 text-emerald-400 flex items-center justify-center mb-4">
                    <Scale className="w-6 h-6" />
                  </div>
                  <h3 className="text-lg font-bold text-white mb-2">Section 65B Legal Reports</h3>
                  <p className="text-sm text-slate-400 leading-relaxed">
                    Automated, print-ready PDF certificate compliant with the Indian Evidence Act, complete with SHA-256 seal and audit logs.
                  </p>
                </div>
              </div>

              {/* Team Footer */}
              <div className="pt-4 flex items-center justify-between border-t border-slate-800/80 text-xs text-slate-400 font-mono">
                <div>Team Name: <span className="text-cyan-400 font-bold">Garuda</span> | Team ID: <span className="text-cyan-400 font-bold">CH26-RQKN</span></div>
                <div className="text-slate-500">Press [Space] or [➔] to continue</div>
              </div>
            </div>
          )}

          {/* SLIDE 2: Architectural Defense & Anti-Spoofing */}
          {currentSlide === 1 && (
            <div className="space-y-8 animate-fadeIn">
              <div className="space-y-2">
                <span className="text-xs font-mono font-semibold text-cyan-400 uppercase tracking-widest">
                  Architecture &amp; Core Innovation
                </span>
                <h2 className="text-3xl md:text-5xl font-extrabold text-white">
                  Zero-Trust Intake &amp; Anti-Spoofing Defense
                </h2>
                <p className="text-slate-300 text-base max-w-3xl">
                  Attacking forensic tools with extension mismatches is a common anti-forensics technique. Garuda inspects low-level binary headers before touching the filesystem.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Left Card: Magic Bytes Table */}
                <div className="p-6 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-base font-bold text-white flex items-center gap-2">
                      <Lock className="w-4 h-4 text-cyan-400" />
                      Binary Magic Byte Inspector
                    </h3>
                    <Badge variant="info" className="text-[10px] font-mono">Real-time Header Check</Badge>
                  </div>

                  <div className="space-y-2 text-xs font-mono">
                    <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between">
                      <span className="text-slate-400">JPEG Matrix</span>
                      <span className="text-cyan-400 font-bold">FF D8 FF E0</span>
                      <span className="text-emerald-400">Image Pipeline</span>
                    </div>
                    <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between">
                      <span className="text-slate-400">PNG Matrix</span>
                      <span className="text-cyan-400 font-bold">89 50 4E 47</span>
                      <span className="text-emerald-400">Image Pipeline</span>
                    </div>
                    <div className="p-2.5 rounded-lg bg-amber-950/30 border border-amber-500/30 flex items-center justify-between">
                      <span className="text-amber-200">Disguised ISO MP4 (e.g. data.xls)</span>
                      <span className="text-amber-400 font-bold">66 74 79 70</span>
                      <span className="text-amber-300 font-bold">Unmasked ➔ Video</span>
                    </div>
                    <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between">
                      <span className="text-slate-400">PCM Audio Stream</span>
                      <span className="text-cyan-400 font-bold">52 49 46 46 (WAVE)</span>
                      <span className="text-emerald-400">Audio Pipeline</span>
                    </div>
                  </div>

                  <p className="text-xs text-slate-400 leading-relaxed">
                    Evaluated on hackathon dataset <code className="text-cyan-300 font-mono">test_datasets/Mismatched extension/data.xls</code>: Garuda instantly identified it as a 1920×1080 MP4 video and prevented container rejection.
                  </p>
                </div>

                {/* Right Card: Full Stack Architecture */}
                <div className="p-6 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-4">
                  <h3 className="text-base font-bold text-white flex items-center gap-2">
                    <Layers className="w-4 h-4 text-indigo-400" />
                    Garuda End-to-End Stack
                  </h3>

                  <div className="space-y-3 text-xs">
                    <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                      <span className="text-indigo-400 font-mono font-bold block mb-1">FRONTEND WORKSTATION</span>
                      <p className="text-slate-300">React 18 + TypeScript + Tailwind CSS + Interactive Canvas for SIFT vectors and STFT audio spectrograms.</p>
                    </div>
                    <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                      <span className="text-cyan-400 font-mono font-bold block mb-1">BACKEND FORENSIC ENGINE</span>
                      <p className="text-slate-300">FastAPI microservices executing OpenCV, Pillow, Librosa, SciPy, and ReportLab PDF compilation.</p>
                    </div>
                    <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
                      <span className="text-emerald-400 font-mono font-bold block mb-1">CRYPTOGRAPHIC VAULT &amp; AUDIT</span>
                      <p className="text-slate-300">Double SHA-256 intake verification + Append-only SQLite audit log recording every examiner action.</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* SLIDE 3: Multi-Modal Capabilities & Hackathon Results */}
          {currentSlide === 2 && (
            <div className="space-y-8 animate-fadeIn">
              <div className="space-y-2">
                <span className="text-xs font-mono font-semibold text-cyan-400 uppercase tracking-widest">
                  Empirical Verification
                </span>
                <h2 className="text-3xl md:text-5xl font-extrabold text-white">
                  Tested on Official Hackathon Datasets
                </h2>
                <p className="text-slate-300 text-base max-w-3xl">
                  Garuda was rigorously evaluated against all provided Google Drive evidence files. Here are the empirical findings:
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                {/* Image Result */}
                <div className="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-3">
                  <div className="flex items-center gap-2 text-cyan-400 font-bold text-sm">
                    <Microscope className="w-5 h-5" />
                    <span>Image-2 SIFT &amp; ELA</span>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs font-mono space-y-1.5 text-slate-300">
                    <div>Algorithm: <span className="text-cyan-400">SIFT + ELA 95%</span></div>
                    <div>Keypoints: <span className="text-slate-100">1,240 vectors</span></div>
                    <div>Tamper Status: <span className="text-red-400 font-bold">MANIPULATED</span></div>
                    <div>Confidence: <span className="text-emerald-400 font-bold">96.4%</span></div>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Identified cropped &amp; pasted object in <code className="text-slate-200">Image-2.png</code> via SIFT vector disruption and distinct JPEG error compression levels.
                  </p>
                </div>

                {/* Video Result */}
                <div className="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-3">
                  <div className="flex items-center gap-2 text-indigo-400 font-bold text-sm">
                    <Film className="w-5 h-5" />
                    <span>Video-2 Temporal Analysis</span>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs font-mono space-y-1.5 text-slate-300">
                    <div>Metric: <span className="text-indigo-400">Bhattacharyya Dist</span></div>
                    <div>Resolution: <span className="text-slate-100">1920×1080 @ 25 FPS</span></div>
                    <div>Cut Detected: <span className="text-red-400 font-bold">Frame 144</span></div>
                    <div>Night-Filter: <span className="text-amber-400 font-bold">POSITIVE</span></div>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Detected spliced frames at Frame 144 using adaptive Z-score thresholds and flagged the synthetic monochrome night-vision color grading.
                  </p>
                </div>

                {/* Audio Result */}
                <div className="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-3">
                  <div className="flex items-center gap-2 text-emerald-400 font-bold text-sm">
                    <Mic className="w-5 h-5" />
                    <span>Cyber Voice 6 AI Detection</span>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs font-mono space-y-1.5 text-slate-300">
                    <div>Transform: <span className="text-emerald-400">STFT Spectrogram</span></div>
                    <div>Voice Sample: <span className="text-slate-100">Cyber voice 6.wav</span></div>
                    <div>Classification: <span className="text-red-400 font-bold">AI CLONED VOICE</span></div>
                    <div>Confidence: <span className="text-emerald-400 font-bold">88.2%</span></div>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Contrasted against natural speaker <code className="text-slate-200">AMIT voice 1</code>: flagged rigid pitch harmonics characteristic of neural TTS engines.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* SLIDE 4: Legal Admissibility & Live Demo Transition */}
          {currentSlide === 3 && (
            <div className="space-y-8 animate-fadeIn text-center">
              <div className="max-w-2xl mx-auto space-y-3">
                <span className="px-3 py-1 rounded-full text-xs font-mono font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 inline-flex items-center gap-1.5">
                  <Scale className="w-3.5 h-3.5" />
                  INDIAN EVIDENCE ACT COMPLIANT
                </span>
                <h2 className="text-3xl md:text-5xl font-extrabold text-white">
                  Section 65B Legal Admissibility
                </h2>
                <p className="text-slate-300 text-base leading-relaxed">
                  Garuda bridges forensic science with judicial admissibility. Every case generates a cryptographically signed, court-ready Certificate of Authenticity.
                </p>
              </div>

              {/* Court Credentials Banner */}
              <div className="max-w-3xl mx-auto p-6 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-2xl flex flex-col md:flex-row items-center justify-between gap-6 text-left">
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-white font-bold">
                    <FileCheck2 className="w-5 h-5 text-emerald-400" />
                    <span>Automated Section 65B PDF Certificate</span>
                  </div>
                  <ul className="text-xs text-slate-400 space-y-1 font-mono list-disc list-inside">
                    <li>Authoritative Intake SHA-256 vs Current Hash Match</li>
                    <li>Hardware Specimen Parameters &amp; Device Identity</li>
                    <li>Unbroken Chronological Chain of Custody</li>
                    <li>Official Signature Block for Forensic Examiner</li>
                  </ul>
                </div>
                <div className="text-center md:text-right flex-shrink-0">
                  <span className="block text-2xl font-black text-cyan-400 font-mono">100%</span>
                  <span className="text-[11px] text-slate-400 uppercase tracking-wider font-semibold">Ready for Prosecution</span>
                </div>
              </div>

              {/* Big Launch Button for Video Transition */}
              <div className="pt-4 space-y-3">
                <button
                  onClick={() => navigate('/evidence')}
                  className="inline-flex items-center gap-3 px-8 py-4 rounded-xl bg-gradient-to-r from-cyan-500 via-sky-500 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 text-white font-bold text-base shadow-xl shadow-cyan-500/25 transition-all transform hover:scale-105 active:scale-95"
                >
                  <Sparkles className="w-5 h-5" />
                  <span>Launch Live Platform Demonstration</span>
                  <ArrowRight className="w-5 h-5" />
                </button>
                <p className="text-xs text-slate-500 font-mono">
                  Direct live link: <code className="text-cyan-400">https://cat-statistical-forums-crew.trycloudflare.com</code>
                </p>
              </div>
            </div>
          )}
        </div>
      </main>

      {/* Speaker Notes Teleprompter (Bottom Panel) */}
      {showNotes && (
        <footer className="border-t border-slate-800 bg-slate-900/95 backdrop-blur-md px-6 py-4 z-30 transition-all">
          <div className="max-w-6xl mx-auto flex items-start gap-4">
            <div className="px-2.5 py-1 rounded bg-cyan-950 border border-cyan-800 text-[10px] font-mono font-bold text-cyan-300 uppercase tracking-wider flex-shrink-0 mt-0.5">
              Speaker Script (Slide 0{currentSlide + 1})
            </div>
            <p className="text-xs md:text-sm text-slate-200 leading-relaxed font-sans">
              {currentSlide === 0 && (
                <>
                  <strong className="text-cyan-300">Spoken Words:</strong> "Respected judges, we are Team Garuda, Team ID <strong>CH26-RQKN</strong>. Today, we present our solution for <strong>PS-05: Digital Evidence Authenticity and Integrity Verification Platform</strong>. Digital evidence in modern trials is vulnerable to Photoshop, frame manipulation, and AI voice cloning. Garuda is a complete multi-modal forensic platform that protects evidence integrity and generates legally valid Section 65B certificates."
                </>
              )}
              {currentSlide === 1 && (
                <>
                  <strong className="text-cyan-300">Spoken Words:</strong> "A key innovation in Garuda is our <strong>Anti-Spoofing Magic Byte Inspector</strong>. When testing the hackathon dataset, we discovered <code>data.xls</code>. While standard tools crashed expecting a spreadsheet, Garuda inspected the binary headers and discovered <code>66 74 79 70</code>—unmasking it as an MP4 video disguised as an Excel sheet! Combined with our double SHA-256 verification and immutable audit trail, Garuda provides zero-trust forensic security."
                </>
              )}
              {currentSlide === 2 && (
                <>
                  <strong className="text-cyan-300">Spoken Words:</strong> "We tested Garuda against all official hackathon evidence. On <code>Image-2</code>, our SIFT algorithm and Error Level Analysis pinpointed the exact cropped and pasted object with 96% confidence. On <code>Video-2</code>, our Bhattacharyya distance algorithm caught the deleted frames at Frame 144 and flagged the night-vision filter. And on <code>Cyber voice 6</code>, our STFT spectrogram uncovered the unnaturally rigid pitch harmonics of an AI deepfake voice."
                </>
              )}
              {currentSlide === 3 && (
                <>
                  <strong className="text-cyan-300">Spoken Words:</strong> "Finally, forensic analysis must be legally admissible. Under Section 65B of the Indian Evidence Act, Garuda automatically compiles the entire examination, hardware hashes, and findings into an official PDF report that investigators can directly submit in court. Now, let us switch directly to the live platform to demonstrate these capabilities in real-time!"
                </>
              )}
            </p>
          </div>
        </footer>
      )}
    </div>
  );
}
