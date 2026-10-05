import React from 'react';
import { Inbox } from 'lucide-react';

/**
 * Standard accessible EmptyState component.
 */
export default function EmptyState({
  icon: Icon = Inbox,
  title = 'No items found',
  description,
  action,
  className = ''
}) {
  return (
    <div className={`py-12 px-4 text-center max-w-sm mx-auto ${className}`}>
      <div className="w-12 h-12 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center mx-auto mb-3 text-slate-500 shadow-sm">
        <Icon className="w-6 h-6" aria-hidden="true" />
      </div>
      <h4 className="text-base font-bold text-slate-900">{title}</h4>
      {description && (
        <p className="text-xs sm:text-sm text-slate-600 mt-1.5 leading-relaxed">{description}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
