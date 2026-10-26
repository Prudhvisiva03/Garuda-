// EviSutra Reports Page — Downloadable Examination Reports

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { FileText, Download, Microscope, ArrowRight } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';
import { api, type ApiEvidence } from '@/api/client';
import { formatDate, formatFileSize } from '@/utils/formatters';

export function Reports() {
  const [evidenceList, setEvidenceList] = useState<ApiEvidence[]>([]);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  useEffect(() => {
    async function loadEvidence() {
      try {
        const items = await api.listEvidence();
        setEvidenceList(items);
      } catch {
        // Handled cleanly
      }
    }
    loadEvidence();
  }, []);

  const handleDownload = async (evId: string) => {
    setDownloadingId(evId);
    try {
      await api.generateReport(evId);
      const url = api.getReportDownloadUrl(evId);
      window.open(url, '_blank');
    } catch (err) {
      alert('Report generation failed: ' + (err instanceof Error ? err.message : String(err)));
    } finally {
      setDownloadingId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-semibold text-slate-900 tracking-tight">Forensic Reports</h1>
          <p className="text-sm text-slate-500 mt-1">
            Generate and export official digital evidence technical examination PDF reports
          </p>
        </div>
      </div>

      {/* Reports Table or Empty State */}
      <Card title="Available Examination Reports">
        {evidenceList.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-500 uppercase font-medium border-b border-slate-200">
                <tr>
                  <th className="px-4 py-3">Evidence ID</th>
                  <th className="px-4 py-3">File Name</th>
                  <th className="px-4 py-3">Format / Size</th>
                  <th className="px-4 py-3">Intake Timestamp</th>
                  <th className="px-4 py-3">Analysis State</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {evidenceList.map((e) => (
                  <tr key={e.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-3 font-mono font-medium text-cyan-600 whitespace-nowrap">
                      {e.id}
                    </td>
                    <td className="px-4 py-3 font-medium text-slate-800">{e.original_filename}</td>
                    <td className="px-4 py-3 text-slate-500 font-mono">
                      {e.mime_type} &bull; {formatFileSize(e.file_size)}
                    </td>
                    <td className="px-4 py-3 text-slate-500">{formatDate(e.created_at)}</td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      {e.status === 'analyzed' ? (
                        <Badge variant="success" dot>
                          Analyzed
                        </Badge>
                      ) : (
                        <Badge variant="neutral" dot>
                          Ingested
                        </Badge>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right whitespace-nowrap">
                      <div className="flex items-center justify-end gap-2">
                        <Link to={`/analysis?evidenceId=${e.id}`}>
                          <Button variant="ghost" size="sm" leftIcon={<Microscope className="w-3.5 h-3.5" />}>
                            Workbench
                          </Button>
                        </Link>
                        <Button
                          variant="primary"
                          size="sm"
                          isLoading={downloadingId === e.id}
                          leftIcon={<Download className="w-3.5 h-3.5" />}
                          onClick={() => handleDownload(e.id)}
                        >
                          Download PDF
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            icon={<FileText className="h-12 w-12 text-slate-400" />}
            title="No evidence items ingested yet"
            description="Upload digital evidence through the Evidence Intake desk to generate technical examination reports."
            action={
              <Link to="/evidence">
                <Button variant="primary" size="sm" leftIcon={<ArrowRight className="w-4 h-4" />}>
                  Go to Evidence Intake
                </Button>
              </Link>
            }
          />
        )}
      </Card>
    </div>
  );
}
