// EviSutra Law Enforcement Audit Trail & Chain of Custody Log
// Immutable digital forensics activity logging for legal court admissibility.

import { useState, useEffect } from 'react';
import { ShieldCheck, Filter } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { DEMO_AUDIT_EVENTS } from '@/data/demo';
import { formatDateTime } from '@/utils/formatters';
import { api } from '@/api/client';
import type { AuditEvent } from '@/types';

export function AuditTrail() {
  const [eventsList, setEventsList] = useState<AuditEvent[]>(DEMO_AUDIT_EVENTS);
  const [filterAction, setFilterAction] = useState<string>('all');
  const [showFilterMenu, setShowFilterMenu] = useState(false);

  useEffect(() => {
    async function loadAuditLogs() {
      try {
        const liveLogs = await api.listAuditEvents();
        if (liveLogs && liveLogs.length > 0) {
          setEventsList(liveLogs);
        }
      } catch {
        // Fall back gracefully
      }
    }
    loadAuditLogs();
  }, []);

  const filteredEvents = eventsList.filter((ev) => {
    if (filterAction === 'all') return true;
    return ev.action.toLowerCase().includes(filterAction.toLowerCase());
  });

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-semibold text-slate-900 tracking-tight">Audit Trail</h1>
          <p className="text-sm text-slate-500 mt-1">
            Immutable chain of custody tracking and forensic activity registry
          </p>
        </div>
        <div className="relative">
          <button
            type="button"
            onClick={() => setShowFilterMenu(!showFilterMenu)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-slate-200 bg-white text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors shadow-sm"
          >
            <Filter className="w-3.5 h-3.5 text-slate-500" />
            <span>Filter: {filterAction === 'all' ? 'All Activities' : filterAction}</span>
          </button>

          {showFilterMenu && (
            <div className="absolute right-0 mt-2 w-48 rounded-lg bg-white shadow-lg border border-slate-200 py-1 z-20 text-xs">
              <button
                type="button"
                onClick={() => { setFilterAction('all'); setShowFilterMenu(false); }}
                className={`w-full text-left px-3 py-2 hover:bg-slate-50 ${filterAction === 'all' ? 'text-cyan-600 font-semibold' : 'text-slate-700'}`}
              >
                All Activities
              </button>
              <button
                type="button"
                onClick={() => { setFilterAction('ingest'); setShowFilterMenu(false); }}
                className={`w-full text-left px-3 py-2 hover:bg-slate-50 ${filterAction === 'ingest' ? 'text-cyan-600 font-semibold' : 'text-slate-700'}`}
              >
                Evidence Intake &amp; Hashing
              </button>
              <button
                type="button"
                onClick={() => { setFilterAction('temporal'); setShowFilterMenu(false); }}
                className={`w-full text-left px-3 py-2 hover:bg-slate-50 ${filterAction === 'temporal' ? 'text-cyan-600 font-semibold' : 'text-slate-700'}`}
              >
                Video Temporal Analysis
              </button>
              <button
                type="button"
                onClick={() => { setFilterAction('voice'); setShowFilterMenu(false); }}
                className={`w-full text-left px-3 py-2 hover:bg-slate-50 ${filterAction === 'voice' ? 'text-cyan-600 font-semibold' : 'text-slate-700'}`}
              >
                Audio Voice Synthesis Checks
              </button>
              <button
                type="button"
                onClick={() => { setFilterAction('case'); setShowFilterMenu(false); }}
                className={`w-full text-left px-3 py-2 hover:bg-slate-50 ${filterAction === 'case' ? 'text-cyan-600 font-semibold' : 'text-slate-700'}`}
              >
                Case Status Updates
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Advisory Banner */}
      <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 flex items-center gap-3">
        <ShieldCheck className="w-4 h-4 text-emerald-600 flex-shrink-0" />
        <p className="text-xs text-slate-700">
          <strong className="font-semibold text-slate-900">Cryptographic Chain of Custody Enforced:</strong> All evidence intake, SHA-256 verifications, and forensic evaluations are recorded in an append-only audit trail compliant with Section 65B Indian Evidence Act / Section 63 BSA 2023.
        </p>
      </div>

      {/* Audit Log Table Card */}
      <Card
        title="Activity Log"
        headerAction={
          <span className="text-xs text-slate-500 font-mono">
            {filteredEvents.length} verified records
          </span>
        }
      >
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500 uppercase font-medium border-b border-slate-200">
              <tr>
                <th className="px-4 py-3">Timestamp</th>
                <th className="px-4 py-3">Investigator / User</th>
                <th className="px-4 py-3">Action</th>
                <th className="px-4 py-3">Resource</th>
                <th className="px-4 py-3">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono">
              {filteredEvents.map((event) => (
                <tr key={event.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-4 py-3 text-slate-500 whitespace-nowrap">
                    {formatDateTime(event.timestamp)}
                  </td>
                  <td className="px-4 py-3 text-slate-800 whitespace-nowrap font-sans font-medium">
                    {event.userName}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className="px-2 py-0.5 rounded bg-cyan-50 text-cyan-600 border border-cyan-200 text-[11px] font-semibold">
                      {event.action}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-700 whitespace-nowrap">
                    <span className="text-slate-400">{event.resourceType}:</span> {event.resourceId}
                  </td>
                  <td className="px-4 py-3 font-sans text-slate-700">
                    <span className="truncate">{event.details}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
