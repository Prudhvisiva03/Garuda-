import type { ReactNode } from 'react';

interface BadgeProps {
  variant: 'success' | 'warning' | 'error' | 'info' | 'neutral';
  children: ReactNode;
  dot?: boolean;
  className?: string;
}

const variantStyles: Record<string, string> = {
  success: 'bg-emerald-50 text-emerald-600 border-emerald-200',
  warning: 'bg-amber-50 text-amber-600 border-amber-200',
  error: 'bg-red-50 text-red-600 border-red-200',
  info: 'bg-cyan-50 text-cyan-600 border-cyan-200',
  neutral: 'bg-slate-100 text-slate-500 border-slate-200',
};

const dotColors: Record<string, string> = {
  success: 'bg-emerald-500',
  warning: 'bg-amber-500',
  error: 'bg-red-500',
  info: 'bg-cyan-500',
  neutral: 'bg-slate-500',
};

export function Badge({ variant, children, dot = false, className = '' }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${variantStyles[variant]} ${className}`}
    >
      {dot && <span className={`w-1.5 h-1.5 rounded-full ${dotColors[variant]}`} />}
      {children}
    </span>
  );
}
