import React from 'react';
import { RefreshCw } from 'lucide-react';

/**
 * Accessible truthful LoadingState component.
 */
export default function LoadingState({
  message = 'Loading...',
  subtext,
  size = 'md',
  className = ''
}) {
  const iconSizes = size === 'sm' ? 'w-4 h-4' : size === 'lg' ? 'w-7 h-7' : 'w-5 h-5';
  const padClasses = size === 'sm' ? 'py-4' : size === 'lg' ? 'py-16' : 'py-8';

  return (
    <div
      role="status"
      aria-live="polite"
      className={`text-center flex flex-col items-center justify-center ${padClasses} ${className}`}
    >
      <RefreshCw className={`${iconSizes} animate-spin text-blue-600 mb-2`} aria-hidden="true" />
      <p className="text-sm font-semibold text-slate-800">{message}</p>
      {subtext && <p className="text-xs text-slate-600 mt-1 max-w-sm">{subtext}</p>}
      <span className="sr-only">{message}</span>
    </div>
  );
}
