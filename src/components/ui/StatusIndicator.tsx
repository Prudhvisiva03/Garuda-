interface StatusIndicatorProps {
  status: 'operational' | 'degraded' | 'offline' | 'not-implemented' | 'success' | 'warning' | 'error' | 'neutral';
  label: string;
  size?: 'sm' | 'md';
}

const dotColors: Record<string, string> = {
  operational: 'bg-emerald-500',
  success: 'bg-emerald-500',
  degraded: 'bg-amber-500',
  warning: 'bg-amber-500',
  offline: 'bg-red-500',
  error: 'bg-red-500',
  'not-implemented': 'bg-slate-400',
  neutral: 'bg-slate-400',
};

export function StatusIndicator({ status, label, size = 'md' }: StatusIndicatorProps) {
  const dotSize = size === 'sm' ? 'w-1.5 h-1.5' : 'w-2 h-2';
  const textSize = size === 'sm' ? 'text-xs' : 'text-sm';

  return (
    <div className="flex items-center gap-2">
      <span className={`${dotSize} rounded-full ${dotColors[status]}`} />
      <span className={`${textSize} text-slate-500`}>{label}</span>
    </div>
  );
}
