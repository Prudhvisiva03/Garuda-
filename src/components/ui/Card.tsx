import type { ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
  title?: string;
  headerAction?: ReactNode;
}

export function Card({ children, className = '', title, headerAction }: CardProps) {
  return (
    <div className={`bg-white border border-slate-200 shadow-sm rounded-lg ${className}`}>
      {title && (
        <div className="px-4 py-3 border-b border-slate-200 flex items-center justify-between">
          <h3 className="font-medium text-slate-900 text-sm">{title}</h3>
          {headerAction}
        </div>
      )}
      <div className="p-4">
        {children}
      </div>
    </div>
  );
}
