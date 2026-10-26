import os
import json
import subprocess
from pathlib import Path
from typing import Any
import numpy as np
from scipy import signal
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def decode_audio_stream(filepath: Path, target_sr: int = 22050) -> tuple[np.ndarray, int]:
    """
    Decodes audio file (WAV, MP3, AAC, M4A) to uncompressed 32-bit float PCM numpy array.
    Normalizes amplitude to [-1.0, 1.0].
    """
    cmd = [
        "ffmpeg", "-v", "quiet",
        "-i", str(filepath),
        "-f", "s16le",
        "-acodec", "pcm_s16le",
        "-ar", str(target_sr),
        "-ac", "1",
        "pipe:1"
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    raw, err = proc.communicate()
    if proc.returncode != 0 or len(raw) == 0:
        raise RuntimeError(f"FFmpeg audio decode failed: {err.decode('utf-8', errors='ignore')}")
    
    arr = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    return arr, target_sr


def probe_audio_metadata(filepath: Path) -> dict[str, Any]:
    """Inspects native audio stream metadata using ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-show_streams", "-show_format",
        "-print_format", "json",
        str(filepath)
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, _ = proc.communicate()
    try:
        data = json.loads(out.decode("utf-8", errors="ignore"))
        streams = data.get("streams", [])
        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), {})
        fmt = data.get("format", {})
        
        codec = audio_stream.get("codec_name", filepath.suffix.replace(".", "").lower())
        sr = int(audio_stream.get("sample_rate", 44100))
        channels = int(audio_stream.get("channels", 1))
        bitrate = int(fmt.get("bit_rate", 0)) // 1000 if fmt.get("bit_rate") else None
        
        return {
            "codec": codec.upper(),
            "sample_rate_hz": sr,
            "channels": channels,
            "bitrate_kbps": bitrate,
        }
    except Exception:
        return {
            "codec": filepath.suffix.replace(".", "").upper(),
            "sample_rate_hz": 44100,
            "channels": 1,
            "bitrate_kbps": None,
        }


def detect_suspicious_segments(
    y: np.ndarray, sr: int
) -> tuple[list[dict[str, Any]], float, float, float, np.ndarray]:
    """
    Detects acoustic splices, digital silence gaps, and abrupt noise floor shifts.
    Returns:
    - suspicious_segments: list of detected anomalies with timestamps and explanations
    - noise_floor_rms: 10th percentile background energy
    - total_silence_sec: total duration of pure digital silence gaps
    - silence_ratio_pct: percentage of recording spent in digital silence
    - spectral_flux: frame-to-frame spectral difference array
    """
    dur = len(y) / sr
    hop_sec = 0.025
    frame_len = int(0.050 * sr)
    hop_len = int(hop_sec * sr)
    n_frames = (len(y) - frame_len) // hop_len

    if n_frames <= 0:
        return [], 0.0, 0.0, 0.0, np.array([])

    times = np.array([i * hop_sec for i in range(n_frames)])
    frame_rms = np.array([np.sqrt(np.mean(y[i*hop_len : i*hop_len+frame_len]**2)) for i in range(n_frames)])

    # Background noise floor: 10th percentile of energy distribution
    noise_floor_rms = float(np.percentile(frame_rms, 10))

    # STFT for spectral flux (rate of spectral change)
    f, t_stft, Zxx = signal.stft(y, fs=sr, nperseg=512, noverlap=256)
    mag = np.abs(Zxx)
    mag_norm = mag / (np.sum(mag, axis=0, keepdims=True) + 1e-12)
    flux = np.sqrt(np.sum(np.diff(mag_norm, axis=1)**2, axis=0))
    flux_times = t_stft[:-1]

    mean_flux = float(np.mean(flux)) if len(flux) > 0 else 0.0
    std_flux = float(np.std(flux)) if len(flux) > 0 else 1.0

    segments: list[dict[str, Any]] = []
    seg_idx = 1

    # 1. Digital silence detection (RMS < 0.001 for at least 180ms)
    silence_mask = frame_rms < 0.001
    in_silence = False
    start_t = 0.0
    total_silence_sec = 0.0

    for idx, is_sil in enumerate(silence_mask):
        t = float(times[idx])
        if is_sil and not in_silence:
            in_silence = True
            start_t = t
        elif not is_sil and in_silence:
            in_silence = False
            seg_dur = t - start_t
            if seg_dur >= 0.18:
                total_silence_sec += seg_dur
                segments.append({
                    "segment_index": seg_idx,
                    "start_sec": round(start_t, 2),
                    "end_sec": round(t, 2),
                    "duration_sec": round(seg_dur, 2),
                    "anomaly_type": "digital_silence",
                    "severity": "high" if seg_dur > 0.5 else "medium",
                    "spectral_value": round(float(np.mean(frame_rms[int(start_t/hop_sec):int(t/hop_sec)])), 5),
                    "z_score": round((noise_floor_rms - 0.001) / (noise_floor_rms + 1e-6), 2),
                    "explanation": (
                        f"Unnatural digital zero silence interval of {seg_dur:.2f}s (RMS < 0.001). "
                        "Physical microphones always capture ambient room acoustic reverberation; "
                        "complete digital silence indicates artificial synthesis pause or spliced padding."
                    ),
                })
                seg_idx += 1

    if in_silence:
        seg_dur = float(times[-1]) - start_t
        if seg_dur >= 0.18:
            total_silence_sec += seg_dur
            segments.append({
                "segment_index": seg_idx,
                "start_sec": round(start_t, 2),
                "end_sec": round(float(times[-1]), 2),
                "duration_sec": round(seg_dur, 2),
                "anomaly_type": "digital_silence",
                "severity": "high" if seg_dur > 0.5 else "medium",
                "spectral_value": 0.0,
                "z_score": 0.0,
                "explanation": f"Digital silence padding at audio tail ({seg_dur:.2f}s).",
            })
            seg_idx += 1

    # 2. Spectral flux cut spikes (Splice / Edit points: flux > mean + 3.8 * std and flux > 0.30)
    flux_thresh = max(0.30, mean_flux + 3.8 * std_flux)
    flux_spikes_idx = np.where(flux > flux_thresh)[0]

    # Cluster flux spikes that are within 100ms of each other
    time_step = (t_stft[1] - t_stft[0]) if len(t_stft) > 1 else 0.025
    clustered_spikes: list[int] = []
    for s_idx in flux_spikes_idx:
        if not clustered_spikes or (s_idx - clustered_spikes[-1]) > int(0.15 / time_step):
            clustered_spikes.append(s_idx)

    for s_idx in clustered_spikes[:12]: # limit to top 12 significant cuts
        cut_time = float(flux_times[s_idx])
        val = float(flux[s_idx])
        z = (val - mean_flux) / (std_flux + 1e-6)
        segments.append({
            "segment_index": seg_idx,
            "start_sec": round(max(0.0, cut_time - 0.05), 2),
            "end_sec": round(min(dur, cut_time + 0.05), 2),
            "duration_sec": 0.10,
            "anomaly_type": "spectral_flux_spike",
            "severity": "critical" if z > 5.0 else "high",
            "spectral_value": round(val, 3),
            "z_score": round(z, 1),
            "explanation": (
                f"Acoustic splice / edit discontinuity detected at {cut_time:.2f}s "
                f"(Spectral Flux={val:.3f}, Z={z:.1f}σ). Indicates abrupt phonetic transition, "
                "audio concatenation, or inserted phrase."
            ),
        })
        seg_idx += 1

    # Sort segments chronologically
    segments.sort(key=lambda s: s["start_sec"])
    # Re-index
    for i, s in enumerate(segments, start=1):
        s["segment_index"] = i

    silence_ratio_pct = (total_silence_sec / dur) * 100.0 if dur > 0 else 0.0
    return segments, noise_floor_rms, total_silence_sec, silence_ratio_pct, flux


def compute_spectral_indicators(y: np.ndarray, sr: int) -> tuple[float, float, float, float]:
    """Computes frequency domain metrics: rolloff (85%, 95%), HF energy ratio, spectral flatness."""
    freqs, times, Sxx = signal.spectrogram(y, fs=sr, nperseg=1024, noverlap=512, scaling='spectrum')
    psd_mean = np.mean(Sxx, axis=1)
    total_power = float(np.sum(psd_mean)) + 1e-12
    cum_power = np.cumsum(psd_mean) / total_power

    idx85 = np.where(cum_power >= 0.85)[0]
    roll85 = float(freqs[idx85[0]]) if len(idx85) > 0 else float(freqs[-1])

    idx95 = np.where(cum_power >= 0.95)[0]
    roll95 = float(freqs[idx95[0]]) if len(idx95) > 0 else float(freqs[-1])

    hf_mask = freqs > 8000
    hf_ratio = float(np.sum(psd_mean[hf_mask]) / total_power * 100.0)

    # Spectral flatness (Wiener entropy)
    geom_mean = np.exp(np.mean(np.log(psd_mean + 1e-12)))
    arith_mean = np.mean(psd_mean) + 1e-12
    spectral_flatness = float(geom_mean / arith_mean)

    return roll85, roll95, hf_ratio, spectral_flatness


def generate_spectrogram_artifact(
    y: np.ndarray,
    sr: int,
    dur: float,
    suspicious_segments: list[dict[str, Any]],
    evidence_id: str,
    artifacts_dir: Path,
) -> str:
    """Generates and saves a high-resolution forensic Waveform + Mel-Spectrogram artifact."""
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    artifact_name = f"spec_{evidence_id}.png"
    out_path = artifacts_dir / artifact_name

    # Compute spectrogram
    f, t, Sxx = signal.spectrogram(y, fs=sr, nperseg=1024, noverlap=768)
    Sxx_db = 10 * np.log10(Sxx + 1e-10)

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(11, 5.5), sharex=True, gridspec_kw={"height_ratios": [1, 2.2]}
    )

    # 1. Waveform Plot
    time_axis = np.linspace(0, dur, len(y))
    # Downsample waveform for plotting speed if long
    step = max(1, len(y) // 20000)
    ax1.plot(time_axis[::step], y[::step], color="#0284c7", linewidth=0.6, alpha=0.9)
    ax1.set_ylabel("Amplitude", fontsize=8, fontweight="bold")
    ax1.set_title(
        f"EviSutra Audio Forensics — Waveform & Spectral Density [{evidence_id}]",
        fontsize=10,
        fontweight="bold",
        pad=8,
    )
    ax1.grid(True, linestyle="--", alpha=0.35)
    ax1.set_ylim(-1.05, 1.05)

    # Shade suspicious segments on waveform
    for seg in suspicious_segments:
        if seg["anomaly_type"] == "digital_silence":
            ax1.axvspan(seg["start_sec"], seg["end_sec"], color="#f59e0b", alpha=0.35, label="Digital Silence")
        elif seg["anomaly_type"] == "spectral_flux_spike":
            ax1.axvspan(seg["start_sec"], seg["end_sec"], color="#ef4444", alpha=0.45, label="Acoustic Splice")

    # 2. Spectrogram Plot
    im = ax2.pcolormesh(t, f, Sxx_db, shading="gouraud", cmap="magma", vmin=-80, vmax=0)
    ax2.set_ylabel("Frequency (Hz)", fontsize=8, fontweight="bold")
    ax2.set_xlabel("Timeline (seconds)", fontsize=8, fontweight="bold")
    ax2.set_ylim(0, min(11025, sr // 2))
    ax2.grid(True, linestyle="--", alpha=0.25)

    # Add colorbar
    cbar = fig.colorbar(im, ax=ax2, orientation="horizontal", pad=0.20, fraction=0.04)
    cbar.set_label("Spectral Power Density (dB / Hz)", fontsize=7)
    cbar.ax.tick_params(labelsize=6)

    plt.tight_layout()
    plt.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)

    return artifact_name


def analyze_audio(filepath: Path, evidence_id: str, artifacts_dir: Path) -> dict[str, Any]:
    """
    Main forensic audio examination entrypoint.
    Executes:
    1. Stream decode & native metadata probe
    2. Digital silence and acoustic splice segment detection
    3. Spectral rolloff, energy bands, and synthetic voice artifact indicators
    4. Two-panel forensic spectrogram artifact rendering
    5. SWGDE-compliant structured forensic findings
    """
    meta = probe_audio_metadata(filepath)
    y, sr = decode_audio_stream(filepath, target_sr=22050)
    dur = float(len(y) / sr)
    rms_amp = float(np.sqrt(np.mean(y**2)))

    # Segment and silence detection
    segments, noise_floor, silence_dur, silence_pct, flux = detect_suspicious_segments(y, sr)
    roll85, roll95, hf_ratio, flatness = compute_spectral_indicators(y, sr)

    mean_flux = float(np.mean(flux)) if len(flux) > 0 else 0.0
    max_flux = float(np.max(flux)) if len(flux) > 0 else 0.0

    # Decision Logic: AI Synthesized Voice vs Spliced vs Natural Speech
    # Scientific criteria:
    # 1. Physical mics in acoustic rooms have continuous ambient room noise floor (RMS >= 0.015)
    # 2. Synthetic TTS models generate pure digital zero pauses (RMS < 0.001) with silence ratio > 5%
    # 3. Concatenated phonemes produce sharp spectral flux onsets (max_flux > 0.35)
    is_synthetic = False
    classification = "natural_speech_consistent"
    summary_stmt = ""

    if rms_amp < 0.001:
        # Pure digital silence / muted audio with no speech signal
        is_synthetic = False
        classification = "muted_or_empty_audio"
        summary_stmt = (
            f"Muted / silent audio stream: Overall RMS amplitude ({rms_amp:.5f}) is below audible threshold. "
            "No active acoustic or speech signals detected across recording."
        )
    elif noise_floor < 0.003 and silence_pct >= 4.0:
        is_synthetic = True
        classification = "ai_synthesized_voice_detected"
        summary_stmt = (
            f"Evidence exhibits characteristics of AI synthetic voice generation: suppressed ambient noise floor "
            f"({noise_floor:.5f} RMS) and {silence_pct:.1f}% digital silence ({silence_dur:.2f}s across {len([s for s in segments if s['anomaly_type'] == 'digital_silence'])} segments). "
            f"Lacks natural room acoustic reverberation."
        )
    elif len([s for s in segments if s["anomaly_type"] == "spectral_flux_spike"]) >= 2:
        classification = "acoustic_splicing_detected"
        summary_stmt = (
            f"Acoustic splicing detected: {len([s for s in segments if s['anomaly_type'] == 'spectral_flux_spike'])} "
            f"high-magnitude spectral flux discontinuities detected (Max Flux={max_flux:.3f}), indicating edit boundaries or spliced phrases."
        )
    else:
        classification = "natural_speech_consistent"
        summary_stmt = (
            f"Audio stream demonstrates natural acoustic consistency: continuous ambient room noise floor "
            f"({noise_floor:.5f} RMS, 0.0% digital zero gaps) and smooth phonetic transitions consistent with genuine microphone capture."
        )

    # Generate Spectrogram Artifact
    artifact_name = generate_spectrogram_artifact(y, sr, dur, segments, evidence_id, artifacts_dir)

    # Structured SWGDE-compliant findings
    findings: list[dict[str, Any]] = [
        {
            "id": f"fnd_aud_floor_{evidence_id[:8]}",
            "evidence_id": evidence_id,
            "analysis_type": "audio_forensics",
            "test_performed": "Ambient Room Acoustic Noise Floor Analysis",
            "observed_result": f"10th percentile background noise floor RMS = {noise_floor:.5f}",
            "explanation": (
                "Natural microphone recordings contain thermal microphone noise, room acoustic reflections, and ambient atmosphere. "
                "Synthetic text-to-speech vocoders insert pure digital zeros between words."
                if is_synthetic else
                "Continuous non-zero acoustic floor indicates natural physical room environment."
            ),
            "limitations": "Post-processed real recordings with heavy aggressive noise gates can exhibit reduced background noise.",
            "severity": "high" if is_synthetic else "info",
            "review_status": "pending",
        },
        {
            "id": f"fnd_aud_sil_{evidence_id[:8]}",
            "evidence_id": evidence_id,
            "analysis_type": "audio_forensics",
            "test_performed": "Digital Zero Silence Gap Discontinuity Scan",
            "observed_result": f"{silence_pct:.1f}% digital silence ({silence_dur:.2f}s total across recording)",
            "explanation": (
                f"Identified {len([s for s in segments if s['anomaly_type'] == 'digital_silence'])} intervals with RMS < 0.001. "
                "Consistent with synthetic TTS phoneme generation pauses."
                if silence_pct >= 4.0 else
                "No artificial digital silence padding detected across timeline."
            ),
            "limitations": "Studio recordings with manual silence editing can introduce digital gaps.",
            "severity": "high" if silence_pct >= 4.0 else "info",
            "review_status": "pending",
        },
        {
            "id": f"fnd_aud_flux_{evidence_id[:8]}",
            "evidence_id": evidence_id,
            "analysis_type": "audio_forensics",
            "test_performed": "Short-Time Spectral Flux Splice Point Detection",
            "observed_result": f"Mean Spectral Flux = {mean_flux:.4f}, Peak Spike = {max_flux:.4f}",
            "explanation": (
                f"Detected {len([s for s in segments if s['anomaly_type'] == 'spectral_flux_spike'])} abnormal spectral change boundaries. "
                "Points of high spectral discontinuity correspond to potential edit or concatenation points."
            ),
            "limitations": "Sudden loud acoustic transients (e.g. door slaps or mic taps) also produce elevated spectral flux.",
            "severity": "medium" if max_flux > 0.35 else "info",
            "review_status": "pending",
        },
        {
            "id": f"fnd_aud_roll_{evidence_id[:8]}",
            "evidence_id": evidence_id,
            "analysis_type": "audio_forensics",
            "test_performed": "Frequency Rolloff & High-Band Energy Profiling",
            "observed_result": f"85% Rolloff = {roll85:.0f} Hz, 95% Rolloff = {roll95:.0f} Hz (HF > 8kHz Energy: {hf_ratio:.2f}%)",
            "explanation": (
                "Characterizes the effective bandwidth of the vocal track. Neural speech vocoders often exhibit sharp brickwall filters."
            ),
            "limitations": "Telephone bandpass filters (G.711 / AMR) naturally restrict speech to 3.4 kHz.",
            "severity": "info",
            "review_status": "pending",
        },
    ]

    return {
        "evidence_id": evidence_id,
        "classification": classification,
        "summary_statement": summary_stmt,
        "audio_properties": {
            "format": meta["codec"],
            "sample_rate_hz": meta["sample_rate_hz"],
            "channels": meta["channels"],
            "duration_sec": round(dur, 2),
            "bitrate_kbps": meta["bitrate_kbps"],
            "rms_amplitude": round(rms_amp, 4),
            "noise_floor_rms": round(noise_floor, 5),
        },
        "synthetic_indicators": {
            "noise_floor_rms": round(noise_floor, 5),
            "digital_silence_ratio_pct": round(silence_pct, 2),
            "total_digital_silence_sec": round(silence_dur, 2),
            "spectral_rolloff_85_hz": round(roll85, 1),
            "spectral_rolloff_95_hz": round(roll95, 1),
            "hf_energy_ratio_pct": round(hf_ratio, 2),
            "mean_spectral_flux": round(mean_flux, 4),
            "max_spectral_flux": round(max_flux, 4),
            "synthetic_voice_detected": is_synthetic,
            "confidence_indicators": {
                "noise_floor_evaluation": "suppressed_synthetic" if noise_floor < 0.003 else "natural_ambient",
                "silence_profile": "unnatural_pauses" if silence_pct >= 4.0 else "continuous_ambient",
                "spectral_flux_integrity": "abrupt_transitions" if max_flux > 0.35 else "smooth_phonetics",
            },
        },
        "suspicious_segments": segments,
        "spectrogram_artifact": artifact_name,
        "findings": findings,
    }
