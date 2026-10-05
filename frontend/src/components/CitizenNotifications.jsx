import React, { useState, useEffect } from 'react';
import { 
  Bell, 
  CheckCircle2, 
  XCircle, 
  Check, 
  Clock, 
  RefreshCw, 
  AlertCircle, 
  FileText, 
  ChevronRight,
  Inbox
} from 'lucide-react';
import { fetchNotifications, markNotificationRead } from '../services/notifications';
import Alert from './ui/Alert';
import EmptyState from './ui/EmptyState';
import LoadingState from './ui/LoadingState';

export default function CitizenNotifications({ onSelectComplaint, onNotificationRead }) {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionInProgress, setActionInProgress] = useState(null);

  async function loadNotifications() {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchNotifications();
      setNotifications(data);
    } catch (err) {
      setError(err.message || 'Failed to load notifications.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadNotifications();
  }, []);

  async function handleMarkRead(id, e) {
    if (e) e.stopPropagation();
    setActionInProgress(id);
    try {
      const updated = await markNotificationRead(id);
      setNotifications(prev =>
        prev.map(n => (n.id === id ? { ...n, is_read: true } : n))
      );
      if (onNotificationRead) {
        onNotificationRead(updated);
      }
    } catch (err) {
      setError(err.message || 'Failed to mark notification as read.');
    } finally {
      setActionInProgress(null);
    }
  }

  function handleOpenComplaint(complaintId, notification) {
    if (!notification.is_read) {
      handleMarkRead(notification.id);
    }
    if (onSelectComplaint) {
      onSelectComplaint(complaintId);
    }
  }

  const unreadCount = notifications.filter(n => !n.is_read).length;

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden mb-8">
      {/* Header */}
      <div className="p-4 sm:p-6 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3 sm:gap-4">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600 shadow-xs">
            <Bell className="w-5 h-5" aria-hidden="true" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-slate-900">
                Notifications
              </h2>
              {unreadCount > 0 && (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800">
                  {unreadCount} unread
                </span>
              )}
            </div>
            <p className="text-xs sm:text-sm text-slate-600 mt-0.5 font-normal">
              Updates on your submitted reports.
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={loadNotifications}
          disabled={loading}
          className="p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition focus:outline-none focus:ring-2 focus:ring-blue-500"
          title="Refresh notifications"
          aria-label="Refresh notifications"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} aria-hidden="true" />
        </button>
      </div>

      {/* Error Banner */}
      {error && (
        <Alert variant="error" className="m-4 sm:m-6 mb-0" onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Content */}
      <div className="p-4 sm:p-6">
        {loading && notifications.length === 0 ? (
          <LoadingState message="Loading notifications..." />
        ) : notifications.length === 0 ? (
          <EmptyState
            icon={Inbox}
            title="You're all caught up."
            description="When your report is reviewed, status updates will appear here."
          />
        ) : (
          <div className="space-y-3">
            {notifications.map((n) => {
              const isAccepted = n.title?.toLowerCase().includes('accepted');
              const isRejected = n.title?.toLowerCase().includes('reject') || n.message?.toLowerCase().includes('rejected');

              return (
                <article
                  key={n.id}
                  className={`p-3.5 sm:p-4 rounded-xl border transition-all ${
                    n.is_read
                      ? 'bg-slate-50/70 border-slate-200 text-slate-700'
                      : 'bg-white border-blue-300 shadow-xs ring-1 ring-blue-100 text-slate-900'
                  }`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 sm:gap-4">
                    <div className="flex items-start gap-3 min-w-0 flex-1">
                      <div className="mt-0.5 shrink-0">
                        {isAccepted ? (
                          <div className="w-8 h-8 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center">
                            <CheckCircle2 className="w-5 h-5" aria-hidden="true" />
                          </div>
                        ) : isRejected ? (
                          <div className="w-8 h-8 rounded-full bg-rose-100 text-rose-700 flex items-center justify-center">
                            <XCircle className="w-5 h-5" aria-hidden="true" />
                          </div>
                        ) : (
                          <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center">
                            <FileText className="w-5 h-5" aria-hidden="true" />
                          </div>
                        )}
                      </div>

                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <h3 className="text-sm font-bold text-slate-900">
                            {n.title}
                          </h3>
                          {!n.is_read && (
                            <span className="inline-flex items-center px-1.5 py-0.2 rounded text-[10px] font-bold uppercase tracking-wider bg-blue-600 text-white shrink-0">
                              Unread
                            </span>
                          )}
                        </div>

                        <p className="text-xs sm:text-sm text-slate-800 mt-1 leading-relaxed">
                          {n.message}
                        </p>

                        <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 font-medium mt-2">
                          <span className="inline-flex items-center gap-1">
                            <Clock className="w-3.5 h-3.5 text-slate-500" aria-hidden="true" />
                            <time dateTime={n.created_at}>
                              {new Date(n.created_at).toLocaleString(undefined, {
                                year: 'numeric',
                                month: 'short',
                                day: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit',
                              })}
                            </time>
                          </span>
                          <span>&bull;</span>
                          <span className="font-mono text-xs text-slate-600">
                            Report: {n.complaint_id.slice(0, 8)}...
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-2 shrink-0 self-end sm:self-center w-full sm:w-auto justify-end pt-2 sm:pt-0 border-t sm:border-t-0 border-slate-200/60">
                      {!n.is_read && (
                        <button
                          type="button"
                          onClick={(e) => handleMarkRead(n.id, e)}
                          disabled={actionInProgress === n.id}
                          className="px-2.5 py-1.5 text-xs text-slate-700 hover:text-slate-900 hover:bg-slate-100 border border-slate-300 rounded-lg font-semibold transition inline-flex items-center gap-1.5 shadow-xs"
                          title="Mark as read"
                        >
                          <Check className="w-3.5 h-3.5" aria-hidden="true" />
                          <span>Mark Read</span>
                        </button>
                      )}

                      {n.complaint_id && onSelectComplaint && (
                        <button
                          type="button"
                          onClick={() => handleOpenComplaint(n.complaint_id, n)}
                          className="px-3 py-1.5 text-xs sm:text-sm text-blue-700 hover:text-blue-800 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded-lg font-semibold transition inline-flex items-center gap-1 shadow-xs"
                        >
                          <span>View Report</span>
                          <ChevronRight className="w-3.5 h-3.5" aria-hidden="true" />
                        </button>
                      )}
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
