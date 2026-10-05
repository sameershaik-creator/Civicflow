import React from 'react';
import { 
  CheckCircle2, 
  XCircle, 
  Clock, 
  FileEdit, 
  ShieldCheck, 
  MapPin, 
  AlertTriangle,
  HelpCircle,
  Cpu
} from 'lucide-react';

/**
 * Accessible StatusBadge component.
 * Ensures status is never conveyed by color alone (always pairs icon + textual label).
 */
export default function StatusBadge({ status, size = 'sm', className = '' }) {
  if (!status) return null;

  const normalized = String(status).toUpperCase().trim();

  let config = {
    label: normalized,
    icon: HelpCircle,
    bg: 'bg-slate-100',
    text: 'text-slate-800',
    border: 'border-slate-300',
  };

  switch (normalized) {
    case 'DRAFT':
      config = {
        label: 'Draft in Preparation',
        icon: FileEdit,
        bg: 'bg-amber-50',
        text: 'text-amber-800',
        border: 'border-amber-300',
      };
      break;
    case 'AI_GENERATED':
      config = {
        label: 'Report Draft Ready',
        icon: Cpu,
        bg: 'bg-blue-50',
        text: 'text-blue-800',
        border: 'border-blue-300',
      };
      break;
    case 'UNDER_REVIEW':
      config = {
        label: 'In Review',
        icon: Clock,
        bg: 'bg-purple-50',
        text: 'text-purple-800',
        border: 'border-purple-300',
      };
      break;
    case 'SUBMITTED':
      config = {
        label: 'Submitted',
        icon: ShieldCheck,
        bg: 'bg-blue-50',
        text: 'text-blue-800',
        border: 'border-blue-300',
      };
      break;
    case 'ACCEPTED':
      config = {
        label: 'Report Accepted',
        icon: CheckCircle2,
        bg: 'bg-emerald-50',
        text: 'text-emerald-800',
        border: 'border-emerald-300',
      };
      break;
    case 'REJECTED':
      config = {
        label: 'Report Declined',
        icon: XCircle,
        bg: 'bg-rose-50',
        text: 'text-rose-800',
        border: 'border-rose-300',
      };
      break;
    case 'VERIFIED':
      config = {
        label: 'Location Verified',
        icon: CheckCircle2,
        bg: 'bg-emerald-50',
        text: 'text-emerald-800',
        border: 'border-emerald-300',
      };
      break;
    case 'MISMATCH':
    case 'MISMATCH_SUSPECTED':
      config = {
        label: 'Location Differs',
        icon: AlertTriangle,
        bg: 'bg-amber-50',
        text: 'text-amber-800',
        border: 'border-amber-300',
      };
      break;
    case 'NOT_VERIFIED':
      config = {
        label: 'Unverified Location',
        icon: MapPin,
        bg: 'bg-slate-100',
        text: 'text-slate-700',
        border: 'border-slate-300',
      };
      break;
    default:
      config.label = normalized;
      break;
  }

  const Icon = config.icon;
  const sizeClasses = size === 'xs' 
    ? 'px-2 py-0.5 text-xs font-semibold gap-1' 
    : size === 'lg'
    ? 'px-3 py-1.5 text-sm font-semibold gap-2'
    : 'px-2.5 py-1 text-xs font-semibold gap-1.5';

  const iconSizes = size === 'xs' ? 'w-3 h-3' : size === 'lg' ? 'w-4 h-4' : 'w-3.5 h-3.5';

  return (
    <span
      role="status"
      aria-label={`Status: ${config.label}`}
      className={`inline-flex items-center rounded-full border whitespace-nowrap shrink-0 ${config.bg} ${config.text} ${config.border} ${sizeClasses} ${className}`}
    >
      <Icon className={`${iconSizes} shrink-0`} aria-hidden="true" />
      <span>{config.label}</span>
    </span>
  );
}
