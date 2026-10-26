import { useState, useEffect } from 'react';
import { ShieldCheck, Info, AlertTriangle } from 'lucide-react';
import { api } from '@/api/client';

export function DemoBanner() {
  const [status, setStatus] = useState<'live' | 'ready' | 'offline'>('ready');
  const [evidenceCount, setEvidenceCount] = useState<number>(0);

  useEffect(() => {
    let isMounted = true;
    async function checkStatus() {
      try {
        const [health, evidenceList] = await Promise.all([
          api.getHealth().catch(() => null),
          api.listEvidence().catch(() => []),
        ]);
        if (!isMounted) return;
        if (!health) {
          setStatus('offline');
        } else if (evidenceList && evidenceList.length > 0) {
          setEvidenceCount(evidenceList.length);
          setStatus('live');
        } else {
          setStatus('ready');
        }
      } catch {
        if (isMounted) setStatus('offline');
      }
    }
    checkStatus();
    const interval = setInterval(checkStatus, 15000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  if (status === 'live') {
    return (
      <div className="bg-emerald-50 border-b border-emerald-200 px-4 py-2 flex items-center justify-center gap-2">
        <ShieldCheck className="h-4 w-4 text-emerald-600 flex-shrink-0" />
        <p className="text-xs text-emerald-800 font-medium">
          <strong className="font-semibold tracking-wide">GARUDA FORENSIC VAULT ACTIVE:</strong> {evidenceCount} custody-verified evidence item{evidenceCount === 1 ? '' : 's'} secured with SHA-256 integrity | Image ELA/SIFT, Video Temporal Continuity &amp; Audio Synthesis Engines Operational.
        </p>
      </div>
    );
  }

  if (status === 'ready') {
    return (
      <div className="bg-sky-50 border-b border-sky-200 px-4 py-2 flex items-center justify-center gap-2">
        <Info className="h-4 w-4 text-sky-600 flex-shrink-0" />
        <p className="text-xs text-sky-800 font-medium">
          <strong className="font-semibold tracking-wide">GARUDA FORENSIC ENGINES ONLINE:</strong> Multi-modal evidence intake ready for Image, Video, and Voice authenticity verification.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-amber-50 border-b border-amber-200 px-4 py-2 flex items-center justify-center gap-2">
      <AlertTriangle className="h-4 w-4 text-amber-600 flex-shrink-0" />
      <p className="text-xs text-amber-800 font-medium">
        <strong className="font-semibold">FORENSIC BACKEND OFFLINE:</strong> FastAPI engine at 127.0.0.1:8000 not responding. Please verify Python service status.
      </p>
    </div>
  );
}

export const SystemStatusBar = DemoBanner;
