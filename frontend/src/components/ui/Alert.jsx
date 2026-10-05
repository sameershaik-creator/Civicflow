import React from 'react';
import { CheckCircle2, AlertCircle, AlertTriangle, Info, X } from 'lucide-react';

/**
 * Standard accessible Alert component.
 * Uses semantic ARIA roles: role="alert" for errors/warnings, role="status" for info/success.
 */
export default function Alert({
  variant = 'info',
  title,
  children,
  onClose,
  className = ''
}) {
  const configs = {
    info: {
      role: 'status',
      icon: Info,
      bg: 'bg-blue-50',
      text: 'text-blue-900',
      border: 'border-blue-200',
      iconColor: 'text-blue-600',
      titleColor: 'text-blue-950',
    },
    success: {
      role: 'status',
      icon: CheckCircle2,
      bg: 'bg-emerald-50',
      text: 'text-emerald-900',
      border: 'border-emerald-200',
      iconColor: 'text-emerald-600',
      titleColor: 'text-emerald-950',
    },
    warning: {
      role: 'alert',
      icon: AlertTriangle,
      bg: 'bg-amber-50',
      text: 'text-amber-900',
      border: 'border-amber-200',
      iconColor: 'text-amber-600',
      titleColor: 'text-amber-950',
    },
    error: {
      role: 'alert',
      icon: AlertCircle,
      bg: 'bg-rose-50',
      text: 'text-rose-900',
      border: 'border-rose-200',
      iconColor: 'text-rose-600',
      titleColor: 'text-rose-950',
    },
  };

  const current = configs[variant] || configs.info;
  const Icon = current.icon;

  return (
    <div
      role={current.role}
      className={`p-3.5 sm:p-4 rounded-xl border ${current.bg} ${current.border} ${current.text} text-xs sm:text-sm flex items-start gap-2.5 sm:gap-3 shadow-sm ${className}`}
    >
      <Icon className={`w-4 h-4 ${current.iconColor} shrink-0 mt-0.5`} aria-hidden="true" />
      <div className="flex-1 min-w-0 break-words">
        {title && (
          <h5 className={`font-bold text-xs sm:text-sm mb-1 ${current.titleColor}`}>
            {title}
          </h5>
        )}
        <div className="leading-relaxed font-medium">{children}</div>
      </div>
      {onClose && (
        <button
          type="button"
          onClick={onClose}
          aria-label="Dismiss alert"
          className="text-slate-400 hover:text-slate-700 p-0.5 rounded transition"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );
}
