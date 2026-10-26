export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

export function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-IN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

export function formatDateTime(dateString: string): string {
  return new Date(dateString).toLocaleString('en-IN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + '\u2026';
}

export function getAnalysisStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    'not-analyzed': 'Not analyzed',
    'queued': 'Queued',
    'processing': 'Processing\u2026',
    'completed': 'Completed',
    'error': 'Error',
    'unsupported': 'Unsupported',
    'planned': 'Planned \u2014 not yet implemented',
  };
  return labels[status] || status;
}
