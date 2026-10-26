// EviSutra System Configuration & Environment Status
// Operational platform settings and cryptographic security enforcement.

import { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Tabs } from '@/components/ui/Tabs';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import { Info, Key } from 'lucide-react';

const activeSecurityStandards = [
  'SHA-256 Immediate Evidence Checksum Calculation',
  'Read-Only Immutable Evidence Vault Isolation',
  'Tamper-Resistant Chain of Custody Audit Logging',
  'Court-Admissible Section 65B / BSA 2023 Forensic Reporting',
];

export function Settings() {
  const [activeTab, setActiveTab] = useState('workspace');
  const [workspaceName, setWorkspaceName] = useState('Bihar State Cyber Crime Investigation Unit');
  const [workspaceDesc, setWorkspaceDesc] = useState('Garuda multi-modal digital evidence integrity, authenticity verification & analysis workbench.');

  const settingsTabs = [
    { id: 'workspace', label: 'Workspace' },
    { id: 'account', label: 'Account' },
    { id: 'security', label: 'Security' },
    { id: 'about', label: 'About' },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-xl sm:text-2xl font-semibold text-slate-900 tracking-tight">Settings</h1>
        <p className="text-sm text-slate-500 mt-1">
          Platform configuration and forensic environment settings
        </p>
      </div>

      {/* Tabs */}
      <Tabs tabs={settingsTabs} activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Tab Panels */}
      {activeTab === 'workspace' && (
        <Card title="Workspace Settings">
          <div className="space-y-4 max-w-lg">
            <Input
              label="Workspace Name"
              value={workspaceName}
              onChange={(e) => setWorkspaceName(e.target.value)}
              helperText="Authorized law enforcement or forensic laboratory identifier"
            />
            <div className="space-y-1.5">
              <label htmlFor="workspace-description" className="block text-sm font-medium text-slate-700">
                Description
              </label>
              <textarea
                id="workspace-description"
                rows={3}
                value={workspaceDesc}
                onChange={(e) => setWorkspaceDesc(e.target.value)}
                className="w-full px-3 py-2 bg-white border border-slate-200 rounded-md text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-cyan-500"
              />
              <p className="text-xs text-slate-400">Configured for law enforcement and judicial evidentiary review.</p>
            </div>
          </div>
        </Card>
      )}

      {activeTab === 'account' && (
        <Card title="Forensic Examiner Profile">
          <div className="flex items-start gap-4 p-4 rounded-lg bg-slate-50 border border-slate-100 max-w-lg">
            <div className="w-10 h-10 rounded-full bg-cyan-100 text-cyan-700 flex items-center justify-center font-bold flex-shrink-0">
              SV
            </div>
            <div>
              <h4 className="text-sm font-semibold text-slate-800">Inspector S. Verma</h4>
              <p className="text-xs text-slate-600 mt-0.5">
                Senior Cyber Forensics Examiner | State Forensic Science Laboratory
              </p>
              <div className="mt-2.5 inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 text-[11px] font-medium border border-emerald-200">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                <span>Active Forensic Session (Authorized)</span>
              </div>
            </div>
          </div>
        </Card>
      )}

      {activeTab === 'security' && (
        <Card title="Security & Access Control">
          <div className="space-y-4 max-w-xl">
            <div className="flex items-start gap-3 p-3.5 rounded-lg bg-slate-50 border border-slate-100">
              <Key className="w-5 h-5 text-cyan-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-slate-800">Cryptographic Security Active</p>
                <p className="text-xs text-slate-500 mt-1">
                  Enforcing cryptographic SHA-256 evidence sealing, non-repudiation audit trails, and strict Section 65B legal evidence compliance.
                </p>
              </div>
            </div>

            <div className="space-y-2">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Active Security Standards
              </h4>
              <div className="divide-y divide-slate-100 border border-slate-100 rounded-lg overflow-hidden bg-slate-50">
                {activeSecurityStandards.map((feature) => (
                  <div key={feature} className="px-4 py-3 flex items-center justify-between text-xs">
                    <span className="text-slate-700 font-medium">{feature}</span>
                    <Badge variant="success">Enforced</Badge>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Card>
      )}

      {activeTab === 'about' && (
        <Card title="About Garuda">
          <div className="space-y-4 max-w-xl">
            <div className="flex items-center gap-3.5 pb-3 border-b border-slate-100">
              <div className="w-12 h-12 rounded-xl bg-slate-950 border border-cyan-500/30 p-1.5 shadow-xs flex items-center justify-center">
                <img src="/garuda-logo.svg" alt="Garuda Forensics" className="w-9 h-9 object-contain" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900">Garuda</h3>
                <p className="text-xs text-slate-500">
                  Digital Evidence Authenticity &amp; Integrity Verification Platform
                </p>
              </div>
            </div>

            <dl className="divide-y divide-slate-100 text-xs">
              <div className="py-2.5 flex justify-between">
                <dt className="text-slate-500">Product</dt>
                <dd className="font-mono text-cyan-600 font-medium">Garuda Enterprise v2.4 (Bihar Cyber Hackathon Edition)</dd>
              </div>
              <div className="py-2.5 flex justify-between">
                <dt className="text-slate-500">Platform Stage</dt>
                <dd className="text-slate-700">Multi-Modal Forensics (Image, Video, Audio) — Operational</dd>
              </div>
              <div className="py-2.5 flex justify-between">
                <dt className="text-slate-500">Frontend Stack</dt>
                <dd className="text-slate-700">React 18 + TypeScript + Vite + Tailwind CSS</dd>
              </div>
              <div className="py-2.5 flex justify-between">
                <dt className="text-slate-500">Backend Forensics Core</dt>
                <dd className="text-emerald-700 font-medium">Python FastAPI + OpenCV + SciPy + Librosa + SQLite (Operational)</dd>
              </div>
              <div className="py-2.5 flex justify-between">
                <dt className="text-slate-500">Legal Admissibility</dt>
                <dd className="text-slate-700 font-medium">Section 65B Indian Evidence Act / Section 63 BSA 2023</dd>
              </div>
            </dl>

            <div className="p-3 rounded bg-slate-50 border border-slate-100 text-xs text-slate-500 flex items-center gap-2">
              <Info className="w-4 h-4 text-cyan-600 flex-shrink-0" />
              <span>Built for law enforcement officers, digital forensics analysts, and judicial court proceedings.</span>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
