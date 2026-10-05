import React, { useState, useEffect } from 'react';
import { 
  FileText, 
  Plus, 
  Clock, 
  MapPin, 
  ChevronRight, 
  RefreshCw, 
  AlertCircle, 
  CheckCircle2, 
  Eye, 
  Camera,
  User
} from 'lucide-react';
import { fetchMyComplaints } from '../services/complaints';
import StatusBadge from './ui/StatusBadge';
import EmptyState from './ui/EmptyState';
import LoadingState from './ui/LoadingState';
import Alert from './ui/Alert';

export default function CitizenDashboard({ 
  currentUser, 
  onNavigateReport, 
  onSelectComplaint 
}) {
  const [complaints, setComplaints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadComplaints();
  }, []);

  async function loadComplaints() {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchMyComplaints();
      setComplaints(data);
    } catch (err) {
      setError(err.message || 'Failed to load your complaints.');
    } finally {
      setLoading(false);
    }
  }

  const pendingCount = complaints.filter(c => c.status === 'UNDER_REVIEW' || c.status === 'AI_GENERATED' || c.status === 'DRAFT').length;
  const submittedCount = complaints.filter(c => c.status === 'SUBMITTED').length;
  const acceptedCount = complaints.filter(c => c.status === 'ACCEPTED').length;

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full">
      {/* Welcome & Context Header */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-semibold uppercase tracking-wider text-blue-600 bg-blue-50 px-2.5 py-0.5 rounded-full border border-blue-200">
              Citizen Portal
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900">
            Welcome, {currentUser?.name || 'Citizen'}
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Track and manage your submitted civic complaints, review AI-assisted drafts, and view official municipal decisions.
          </p>
        </div>

        <button
          type="button"
          onClick={onNavigateReport}
          className="px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold transition shadow-sm inline-flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          <span>Report an Issue</span>
        </button>
      </div>

      {/* Triage Summary Metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 block mb-1">
            Total Filed
          </span>
          <span className="text-2xl font-extrabold text-slate-900 font-mono">
            {complaints.length}
          </span>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-amber-600 block mb-1">
            Awaiting Review
          </span>
          <span className="text-2xl font-extrabold text-amber-600 font-mono">
            {pendingCount}
          </span>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-blue-600 block mb-1">
            Submitted to City
          </span>
          <span className="text-2xl font-extrabold text-blue-600 font-mono">
            {submittedCount}
          </span>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-emerald-600 block mb-1">
            Accepted / Resolved
          </span>
          <span className="text-2xl font-extrabold text-emerald-600 font-mono">
            {acceptedCount}
          </span>
        </div>
      </div>

      {/* Error alert */}
      {error && (
        <Alert variant="error" className="mb-6" onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Complaints List Section */}
      <section aria-labelledby="my-complaints-heading">
        <div className="flex items-center justify-between mb-4">
          <h2 id="my-complaints-heading" className="text-base font-bold text-slate-900 flex items-center gap-2">
            <FileText className="w-4 h-4 text-blue-600" />
            <span>My Complaints</span>
          </h2>
          <button
            type="button"
            onClick={loadComplaints}
            className="text-xs text-slate-500 hover:text-slate-800 inline-flex items-center gap-1"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </button>
        </div>

        {loading ? (
          <LoadingState message="Loading your submitted complaints..." />
        ) : complaints.length === 0 ? (
          <EmptyState
            icon={FileText}
            title="You haven't submitted any complaints yet"
            description="Report civic issues like road damage, streetlight outages, or sanitation issues in your neighborhood."
            actionLabel="Report Your First Issue"
            onAction={onNavigateReport}
          />
        ) : (
          <div className="space-y-3">
            {complaints.map((c) => {
              const displayTitle = c.final_problem || c.original_problem || 'Untitled Civic Issue';
              const displayAddress = c.final_address || c.original_address;
              const dateStr = c.created_at ? new Date(c.created_at).toLocaleDateString(undefined, {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
              }) : 'Recently';

              return (
                <div
                  key={c.id}
                  className="bg-white rounded-xl border border-slate-200 p-4 sm:p-5 shadow-xs hover:border-slate-300 transition flex flex-col sm:flex-row sm:items-center justify-between gap-4"
                >
                  <div className="space-y-1.5 flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <StatusBadge status={c.status} />
                      {c.location_status && (
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
                          {c.location_status}
                        </span>
                      )}
                      <span className="text-xs text-slate-400 font-mono">
                        #{c.id.slice(0, 8)}
                      </span>
                    </div>

                    <h3 className="text-sm font-semibold text-slate-900 truncate">
                      {displayTitle}
                    </h3>

                    <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500">
                      {displayAddress && (
                        <span className="flex items-center gap-1 truncate max-w-xs">
                          <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                          <span className="truncate">{displayAddress}</span>
                        </span>
                      )}
                      <span className="flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                        <span>{dateStr}</span>
                      </span>
                    </div>
                  </div>

                  <div className="shrink-0 flex items-center">
                    <button
                      type="button"
                      onClick={() => onSelectComplaint(c.id)}
                      className="w-full sm:w-auto px-4 py-2 bg-slate-100 hover:bg-blue-50 text-slate-700 hover:text-blue-700 border border-slate-200 hover:border-blue-300 rounded-lg text-xs font-semibold transition inline-flex items-center justify-center gap-1.5"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      <span>{c.status === 'SUBMITTED' || c.status === 'ACCEPTED' || c.status === 'REJECTED' ? 'View Case' : 'Review Case'}</span>
                      <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
