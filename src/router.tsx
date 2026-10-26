import { createBrowserRouter } from 'react-router-dom';
import { AppLayout } from '@/layouts/AppLayout';
import { Dashboard } from '@/pages/Dashboard';
import { Cases } from '@/pages/Cases';
import { EvidenceIntake } from '@/pages/EvidenceIntake';
import { ImageAnalysis } from '@/pages/ImageAnalysis';
import { VideoAnalysis } from '@/pages/VideoAnalysis';
import { AudioAnalysis } from '@/pages/AudioAnalysis';
import { Reports } from '@/pages/Reports';
import { AuditTrail } from '@/pages/AuditTrail';
import { Settings } from '@/pages/Settings';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: 'cases', element: <Cases /> },
      { path: 'evidence', element: <EvidenceIntake /> },
      { path: 'analysis', element: <ImageAnalysis /> },
      { path: 'video', element: <VideoAnalysis /> },
      { path: 'audio', element: <AudioAnalysis /> },
      { path: 'reports', element: <Reports /> },
      { path: 'audit', element: <AuditTrail /> },
      { path: 'settings', element: <Settings /> },
    ],
  },
]);
