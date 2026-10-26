import { type ButtonHTMLAttributes, type ReactNode } from 'react';
import { Loader2 } from 'lucide-react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: ReactNode;
}

const variantStyles: Record<string, string> = {
  primary: 'bg-cyan-600 hover:bg-cyan-700 text-white',
  secondary: 'bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300',
  ghost: 'bg-transparent hover:bg-slate-100 text-slate-700',
  danger: 'bg-red-50 hover:bg-red-100 text-red-600 border border-red-200',
};

const sizeStyles: Record<string, string> = {
  sm: 'px-3 py-1.5 text-xs',
  md: 'px-4 py-2 text-sm',
  lg: 'px-6 py-2.5 text-sm',
};

export function Button({
  variant = 'primary',
  size = 'md',
  isLoading = false,
  leftIcon,
  children,
  className = '',
  disabled,
  ...props
}: ButtonProps) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-md font-medium
        transition-colors duration-150
        focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500 focus-visible:ring-offset-2 focus-visible:ring-offset-white
        disabled:opacity-50 disabled:cursor-not-allowed
        ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : leftIcon}
      {children}
    </button>
  );
}
