import { Loader2 } from 'lucide-react';

interface LoadingStateProps {
  message?: string;
}

export function LoadingState({ message = 'Loading...' }: LoadingStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4">
      <Loader2 className="h-8 w-8 text-cyan-600 animate-spin mb-3" />
      <p className="text-sm text-slate-500">{message}</p>
    </div>
  );
}
