import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  CheckCircle,
  XCircle,
  AlertCircle,
  RefreshCw,
  Eye,
  MapPin,
  FileText,
  Clock,
  ArrowLeft,
  User,
  Filter,
  Camera,
  CheckCircle2,
  Navigation
} from 'lucide-react';
import { fetchAdminComplaints, fetchAdminComplaintDetail, acceptComplaint, rejectComplaint } from '../services/admin';
import { fetchComplaintImageBlob } from '../services/complaints';
import InteractiveMap from './InteractiveMap';
import StatusBadge from './ui/StatusBadge';
import Alert from './ui/Alert';
import EmptyState from './ui/EmptyState';
import LoadingState from './ui/LoadingState';

function AuthenticatedImage({ complaintId, alt, className }) {
  const [imageSrc, setImageSrc] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    let url = null;

    async function loadImage() {
      try {
        setLoading(true);
        setError(false);
        const blob = await fetchComplaintImageBlob(complaintId);
        if (active) {
          url = URL.createObjectURL(blob);
          setImageSrc(url);
        }
      } catch {
        if (active) {
          setError(true);
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    if (complaintId) {
      loadImage();
    }

    return () => {
      active = false;
      if (url) {
        URL.revokeObjectURL(url);
      }
    };
  }, [complaintId]);

  if (loading) {
    return (
      <div className="h-56 bg-slate-100 animate-pulse rounded-lg flex items-center justify-center text-xs text-slate-500 font-medium">
        <RefreshCw className="w-4 h-4 animate-spin mr-2" aria-hidden="true" />
        <span>Loading photo...</span>
      </div>
    );
  }

  if (error || !imageSrc) {
    return (
      <div className="h-56 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-center text-xs text-slate-600 font-medium">
        <AlertCircle className="w-4 h-4 text-slate-500 mr-2" aria-hidden="true" />
        <span>Photo could not be loaded</span>
      </div>
    );
  }

  return (
    <img
      src={imageSrc}
      alt={alt || 'Report photo'}
      className={className || 'w-full h-56 object-cover rounded-lg border border-slate-200 shadow-sm'}
    />
  );
}

export default function AdminAdjudicationDashboard({ currentUser }) {
  const [complaints, setComplaints] = useState([]);
  const [loadingList, setLoadingList] = useState(true);
  const [listError, setListError] = useState(null);
  const [statusFilter, setStatusFilter] = useState('SUBMITTED');

  // Selected complaint detail
  const [selectedComplaint, setSelectedComplaint] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [detailError, setDetailError] = useState(null);

  // Adjudication actions
  const [adjudicating, setAdjudicating] = useState(false);
  const [actionError, setActionError] = useState(null);
  const [actionSuccess, setActionSuccess] = useState(null);

  // Rejection reason form
  const [showRejectBox, setShowRejectBox] = useState(false);
  const [rejectionReason, setRejectionReason] = useState('');
  const [reasonError, setReasonError] = useState(null);

  useEffect(() => {
    loadComplaints(statusFilter);
  }, [statusFilter]);

  async function loadComplaints(filter) {
    setLoadingList(true);
    setListError(null);
    try {
      const data = await fetchAdminComplaints(filter);
      setComplaints(data);
    } catch (err) {
      setListError(err.message || 'Failed to load reports.');
    } finally {
      setLoadingList(false);
    }
  }

  async function handleSelectComplaint(id) {
    setLoadingDetail(true);
    setDetailError(null);
    setActionError(null);
    setActionSuccess(null);
    setShowRejectBox(false);
    setRejectionReason('');
    setReasonError(null);

    try {
      const detail = await fetchAdminComplaintDetail(id);
      setSelectedComplaint(detail);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (err) {
      setDetailError(err.message || 'Failed to load report details.');
    } finally {
      setLoadingDetail(false);
    }
  }

  async function handleAccept() {
    if (!selectedComplaint) return;
    setAdjudicating(true);
    setActionError(null);
    setActionSuccess(null);

    try {
      const updated = await acceptComplaint(selectedComplaint.id);
      setSelectedComplaint(updated);
      setActionSuccess('Report accepted.');
      setComplaints(prev => prev.map(c => c.id === updated.id ? { ...c, status: 'ACCEPTED', decided_at: updated.decided_at } : c));
    } catch (err) {
      setActionError(err.message || 'Failed to accept report.');
    } finally {
      setAdjudicating(false);
    }
  }

  async function handleConfirmReject(e) {
    e.preventDefault();
    if (!selectedComplaint) return;

    if (!rejectionReason.trim()) {
      setReasonError('Please provide a reason for declining the report.');
      return;
    }

    setAdjudicating(true);
    setActionError(null);
    setActionSuccess(null);
    setReasonError(null);

    try {
      const updated = await rejectComplaint(selectedComplaint.id, {
        admin_reason: rejectionReason.trim(),
      });
      setSelectedComplaint(updated);
      setShowRejectBox(false);
      setActionSuccess('Report declined.');
      setComplaints(prev => prev.map(c => c.id === updated.id ? { ...c, status: 'REJECTED', decided_at: updated.decided_at, admin_reason: updated.admin_reason } : c));
    } catch (err) {
      setActionError(err.message || 'Failed to decline report.');
    } finally {
      setAdjudicating(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-slate-900 text-white rounded-xl p-4 sm:p-6 shadow-sm border border-slate-800">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-6 h-6 text-blue-400 shrink-0" aria-hidden="true" />
              <h2 className="text-xl font-bold tracking-tight">
                Administrative Review
              </h2>
            </div>
            <p className="text-xs sm:text-sm text-slate-300 mt-1.5 max-w-2xl leading-relaxed">
              Review submitted reports, verify details and location, and process administrative decisions.
            </p>
          </div>
          <div className="text-left sm:text-right">
            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-blue-950 text-blue-200 border border-blue-800">
              Admin: {currentUser?.name || currentUser?.email}
            </span>
          </div>
        </div>
      </div>

      {/* Detail Adjudication Card */}
      {selectedComplaint && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          {/* Header Bar */}
          <div className="px-4 sm:px-6 py-3.5 sm:py-4 bg-slate-50 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3 sm:gap-4">
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => setSelectedComplaint(null)}
                className="px-3 py-1.5 text-xs sm:text-sm text-slate-700 hover:text-slate-900 bg-white border border-slate-300 hover:bg-slate-50 rounded-lg font-semibold transition inline-flex items-center gap-1.5 shadow-xs shrink-0"
              >
                <ArrowLeft className="w-3.5 h-3.5" aria-hidden="true" />
                <span>Back to Reports</span>
              </button>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-bold text-slate-900">
                    Report Details
                  </h3>
                  <span className="font-mono text-xs text-slate-600 bg-slate-100 px-2 py-0.5 rounded border border-slate-200 truncate font-medium">
                    {selectedComplaint.id.slice(0, 8)}…
                  </span>
                </div>
                <p className="text-xs sm:text-sm text-slate-600 mt-0.5 truncate font-medium">
                  Citizen: {selectedComplaint.citizen_name || 'Anonymous'} ({selectedComplaint.citizen_email || 'No email'})
                </p>
              </div>
            </div>

            <StatusBadge status={selectedComplaint.status} size="lg" />
          </div>

          <div className="p-4 sm:p-6 space-y-5 sm:space-y-6">
            {/* Feedback Notifications */}
            {actionSuccess && (
              <Alert variant="success" title="Decision Recorded">
                {actionSuccess}
                {selectedComplaint.decided_at && (
                  <span className="block mt-1 font-mono text-xs text-emerald-900 font-medium">
                    Timestamp (UTC): {new Date(selectedComplaint.decided_at).toUTCString()}
                  </span>
                )}
              </Alert>
            )}

            {actionError && (
              <Alert variant="error" title="Action Error">
                {actionError}
              </Alert>
            )}

            {/* Terminal Banners */}
            {selectedComplaint.status === 'ACCEPTED' && (
              <Alert variant="success" title="Report Accepted">
                This report has been reviewed and accepted.
                {selectedComplaint.decided_at && (
                  <span className="block mt-1 font-mono text-xs text-emerald-900 font-medium">
                    Decided at (UTC): {new Date(selectedComplaint.decided_at).toUTCString()}
                  </span>
                )}
              </Alert>
            )}

            {selectedComplaint.status === 'REJECTED' && (
              <Alert variant="error" title="Report Declined">
                This report was reviewed and declined.
                <div className="mt-2 p-3 bg-white border border-rose-200 rounded-lg">
                  <span className="font-bold text-rose-950 block mb-1 text-xs sm:text-sm">Reason:</span>
                  <p className="text-rose-900 font-sans text-sm leading-relaxed">{selectedComplaint.admin_reason}</p>
                </div>
                {selectedComplaint.decided_at && (
                  <span className="block mt-2 font-mono text-xs text-rose-900 font-medium">
                    Decided at (UTC): {new Date(selectedComplaint.decided_at).toUTCString()}
                  </span>
                )}
              </Alert>
            )}

            {/* Section 1: Physical Incident Evidence */}
            <div className="border border-slate-200 rounded-xl p-5 bg-slate-50/50">
              <h4 className="text-sm font-bold uppercase tracking-wider text-slate-800 mb-3 flex items-center gap-2">
                <Camera className="w-4 h-4 text-slate-500" aria-hidden="true" />
                <span>1. Photos & Submitted Details</span>
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="md:col-span-1">
                  <AuthenticatedImage complaintId={selectedComplaint.id} alt="Incident photo" />
                </div>
                <div className="md:col-span-2 bg-white p-4 rounded-lg border border-slate-200 text-xs sm:text-sm space-y-3">
                  <div className="text-xs font-bold text-slate-600 uppercase tracking-wider">
                    Original Submission
                  </div>
                  <div>
                    <span className="font-semibold text-slate-800 block text-xs sm:text-sm">Problem Description:</span>
                    <p className="text-slate-900 mt-1 text-sm leading-relaxed">{selectedComplaint.original_problem}</p>
                  </div>
                  {selectedComplaint.original_address && (
                    <div>
                      <span className="font-semibold text-slate-800 block text-xs sm:text-sm">Reported Address:</span>
                      <p className="text-slate-900 mt-1 text-sm leading-relaxed">{selectedComplaint.original_address}</p>
                    </div>
                  )}
                  {selectedComplaint.original_latitude !== null && selectedComplaint.original_longitude !== null && (
                    <div>
                      <span className="font-semibold text-slate-800 block text-xs sm:text-sm">Device Coordinates:</span>
                      <p className="font-mono text-slate-700 mt-1 text-xs sm:text-sm font-medium">
                        Lat: {selectedComplaint.original_latitude.toFixed(6)}, Lon: {selectedComplaint.original_longitude.toFixed(6)}
                      </p>
                    </div>
                  )}
                  {selectedComplaint.submitted_at && (
                    <div>
                      <span className="font-semibold text-slate-800 block text-xs sm:text-sm">Submitted at (UTC):</span>
                      <p className="font-mono text-slate-700 mt-1 text-xs sm:text-sm font-medium">
                        {new Date(selectedComplaint.submitted_at).toUTCString()}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Section 2: AI-Assisted Interpretation */}
            <div className="border border-slate-200 rounded-xl p-5 bg-slate-50/50">
              <h4 className="text-sm font-bold uppercase tracking-wider text-slate-800 mb-3 flex items-center gap-2">
                <FileText className="w-4 h-4 text-blue-600" aria-hidden="true" />
                <span>2. Report Details</span>
              </h4>
              <div className="bg-white p-4 rounded-lg border border-slate-200 text-xs sm:text-sm space-y-3.5">
                <div className="flex flex-wrap items-center gap-3">
                  {selectedComplaint.category && (
                    <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-800">
                      Category: {selectedComplaint.category}
                    </span>
                  )}
                  {selectedComplaint.urgency_level && (
                    <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-800">
                      Urgency: {selectedComplaint.urgency_level}
                    </span>
                  )}
                </div>

                {selectedComplaint.observed_issue && (
                  <div>
                    <span className="font-semibold text-slate-800 block mb-1 text-xs sm:text-sm">Observed Issue:</span>
                    <p className="text-slate-900 bg-slate-50 p-3 rounded-lg border border-slate-200 text-sm leading-relaxed">
                      {selectedComplaint.observed_issue}
                    </p>
                  </div>
                )}

                {selectedComplaint.citizen_claim && (
                  <div>
                    <span className="font-semibold text-slate-800 block mb-1 text-xs sm:text-sm">Citizen Statement:</span>
                    <p className="text-slate-900 bg-slate-50 p-3 rounded-lg border border-slate-200 text-sm leading-relaxed">
                      {selectedComplaint.citizen_claim}
                    </p>
                  </div>
                )}

                {selectedComplaint.formal_summary && (
                  <div>
                    <span className="font-semibold text-slate-800 block mb-1 text-xs sm:text-sm">Summary:</span>
                    <p className="text-slate-900 bg-slate-50 p-3 rounded-lg border border-slate-200 font-medium text-sm leading-relaxed">
                      {selectedComplaint.formal_summary}
                    </p>
                  </div>
                )}

                {selectedComplaint.warnings && selectedComplaint.warnings.length > 0 && (
                  <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-950 font-medium">
                    <span className="font-bold block mb-1 text-xs sm:text-sm text-amber-950">Observations:</span>
                    <ul className="list-disc list-inside space-y-0.5 text-xs leading-relaxed text-amber-900">
                      {selectedComplaint.warnings.map((w, idx) => (
                        <li key={idx}>{w}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>

            {/* Section 3: Citizen-Reviewed Final Report */}
            <div className="border border-slate-200 rounded-xl p-5 bg-slate-50/50">
              <h4 className="text-sm font-bold uppercase tracking-wider text-slate-800 mb-3 flex items-center gap-2">
                <User className="w-4 h-4 text-emerald-600" aria-hidden="true" />
                <span>3. Citizen-Confirmed Report</span>
              </h4>
              <div className="bg-white p-4 rounded-lg border border-slate-200 text-xs sm:text-sm space-y-3.5">
                <div>
                  <span className="font-semibold text-slate-800 block mb-1 text-xs sm:text-sm">Problem Description:</span>
                  <p className="text-slate-900 bg-slate-50 p-3 rounded-lg border border-slate-200 font-medium text-sm leading-relaxed">
                    {selectedComplaint.final_problem || selectedComplaint.original_problem}
                  </p>
                </div>
                {selectedComplaint.final_address && (
                  <div>
                    <span className="font-semibold text-slate-800 block mb-1 text-xs sm:text-sm">Address / Location:</span>
                    <p className="text-slate-900 bg-slate-50 p-3 rounded-lg border border-slate-200 text-sm leading-relaxed">
                      {selectedComplaint.final_address}
                    </p>
                  </div>
                )}
                {selectedComplaint.final_summary && (
                  <div>
                    <span className="font-semibold text-slate-800 block mb-1 text-xs sm:text-sm">Summary:</span>
                    <p className="text-slate-900 bg-slate-50 p-3 rounded-lg border border-slate-200 text-sm leading-relaxed">
                      {selectedComplaint.final_summary}
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Section 4: Geographic Verification & Map */}
            <div>
              <h4 className="text-sm font-bold uppercase tracking-wider text-slate-800 mb-3 flex items-center gap-2">
                <Navigation className="w-4 h-4 text-blue-600" aria-hidden="true" />
                <span>4. Location & Map</span>
              </h4>
              {selectedComplaint.latitude ? (
                <InteractiveMap
                  latitude={selectedComplaint.latitude}
                  longitude={selectedComplaint.longitude}
                  mapUrl={selectedComplaint.map_url}
                  status={selectedComplaint.location_status}
                  geocodedAddress={selectedComplaint.final_address || selectedComplaint.original_address}
                />
              ) : (
                <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg text-xs sm:text-sm text-slate-600 font-medium">
                  No coordinates attached to this report.
                </div>
              )}
            </div>

            {/* Section 5: Authoritative Adjudication Decision */}
            <div className="pt-6 border-t border-slate-200">
              <h4 className="text-base font-bold text-slate-900 mb-1.5 flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-blue-600" aria-hidden="true" />
                <span>5. Administrative Decision</span>
              </h4>

              {String(selectedComplaint.status).toUpperCase() === 'ACCEPTED' && (
                <div className="mt-3 p-4 bg-emerald-50 border border-emerald-300 rounded-xl text-emerald-950">
                  <div className="flex items-center gap-2 font-bold text-sm">
                    <CheckCircle className="w-4 h-4 text-emerald-600" aria-hidden="true" />
                    <span>✓ Report Accepted</span>
                  </div>
                  <p className="text-xs sm:text-sm text-emerald-900 mt-1 leading-normal font-medium">
                    This report has been reviewed and accepted.
                  </p>
                  {selectedComplaint.decided_at && (
                    <span className="block mt-2 font-mono text-xs text-emerald-800 font-medium">
                      Decision Timestamp (UTC): {new Date(selectedComplaint.decided_at).toUTCString()}
                    </span>
                  )}
                </div>
              )}

              {String(selectedComplaint.status).toUpperCase() === 'REJECTED' && (
                <div className="mt-3 p-4 bg-rose-50 border border-rose-300 rounded-xl text-rose-950">
                  <div className="flex items-center gap-2 font-bold text-sm">
                    <XCircle className="w-4 h-4 text-rose-600" aria-hidden="true" />
                    <span>✕ Report Declined</span>
                  </div>
                  {selectedComplaint.admin_reason && (
                    <div className="mt-2 p-3 bg-white border border-rose-200 rounded-lg text-sm">
                      <span className="font-bold text-rose-950 block mb-1 text-xs sm:text-sm">Reason:</span>
                      <p className="text-rose-900 font-medium leading-relaxed text-sm">{selectedComplaint.admin_reason}</p>
                    </div>
                  )}
                  {selectedComplaint.decided_at && (
                    <span className="block mt-2 font-mono text-xs text-rose-800 font-medium">
                      Decision Timestamp (UTC): {new Date(selectedComplaint.decided_at).toUTCString()}
                    </span>
                  )}
                </div>
              )}

              {String(selectedComplaint.status).toUpperCase() === 'SUBMITTED' && (
                <div className="mt-3">
                  <p className="text-sm text-slate-600 mb-4 leading-normal">
                    Review the report details and location above before recording your decision.
                  </p>

                  {!showRejectBox ? (
                    <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 sm:gap-4">
                      <button
                        type="button"
                        onClick={handleAccept}
                        disabled={adjudicating}
                        className="w-full sm:w-auto px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-bold transition shadow-sm inline-flex items-center justify-center gap-2 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2"
                      >
                        {adjudicating ? (
                          <RefreshCw className="w-4 h-4 animate-spin" />
                        ) : (
                          <CheckCircle className="w-4 h-4" />
                        )}
                        <span>Accept Report</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => setShowRejectBox(true)}
                        disabled={adjudicating}
                        className="w-full sm:w-auto px-6 py-2.5 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-sm font-bold transition shadow-sm inline-flex items-center justify-center gap-2 focus:outline-none focus:ring-2 focus:ring-rose-500 focus:ring-offset-2"
                      >
                        <XCircle className="w-4 h-4" />
                        <span>Reject Report</span>
                      </button>
                    </div>
                  ) : (
                    <form onSubmit={handleConfirmReject} className="p-4 sm:p-5 bg-rose-50 border border-rose-200 rounded-xl space-y-4">
                      <div>
                        <label htmlFor="rejection-reason" className="block text-sm font-bold text-rose-950 mb-1.5">
                          Reason for Declining <span className="text-rose-600">*</span>
                        </label>
                        <p className="text-xs text-rose-900 mb-2 font-medium leading-normal">
                          Provide a clear reason for declining the report. This will be shared with the citizen.
                        </p>
                        <textarea
                          id="rejection-reason"
                          rows={3}
                          required
                          value={rejectionReason}
                          onChange={(e) => setRejectionReason(e.target.value)}
                          placeholder="Reason for declining the report..."
                          className="w-full px-3.5 py-2.5 text-sm border border-rose-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-rose-500 bg-white placeholder:text-slate-400 font-medium"
                        />
                        {reasonError && (
                          <p className="text-xs sm:text-sm text-rose-700 font-semibold mt-1.5">{reasonError}</p>
                        )}
                      </div>

                      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
                        <button
                          type="submit"
                          disabled={adjudicating}
                          className="w-full sm:w-auto px-5 py-2.5 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-sm font-bold transition shadow-sm inline-flex items-center justify-center gap-2"
                        >
                          {adjudicating && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                          <span>Confirm</span>
                        </button>

                        <button
                          type="button"
                          onClick={() => {
                            setShowRejectBox(false);
                            setRejectionReason('');
                            setReasonError(null);
                          }}
                          disabled={adjudicating}
                          className="w-full sm:w-auto px-4 py-2 border border-slate-300 hover:bg-slate-100 text-slate-700 rounded-lg text-sm font-semibold transition text-center"
                        >
                          Cancel
                        </button>
                      </div>
                    </form>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Complaints Queue Section */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-200">
          <div>
            <h3 className="text-base font-bold text-slate-900">
              Submitted Reports
            </h3>
            <p className="text-xs sm:text-sm text-slate-600 mt-0.5 font-normal">
              Review submitted reports and take administrative action.
            </p>
          </div>

          {/* Status Filter */}
          <div className="flex flex-wrap items-center gap-2">
            <Filter className="w-3.5 h-3.5 text-slate-500" aria-hidden="true" />
            <label htmlFor="status-filter-select" className="text-xs sm:text-sm font-semibold text-slate-700">Filter Reports:</label>
            <select
              id="status-filter-select"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="text-xs sm:text-sm border border-slate-300 rounded-lg px-3 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium text-slate-800"
            >
              <option value="SUBMITTED">SUBMITTED (Awaiting Review)</option>
              <option value="ACCEPTED">ACCEPTED (Approved)</option>
              <option value="REJECTED">REJECTED (Declined)</option>
              <option value="ALL">ALL Reports</option>
            </select>
          </div>
        </div>

        {/* Loading state */}
        {loadingList && (
          <LoadingState message="Loading reports..." />
        )}

        {/* Error state */}
        {listError && (
          <Alert variant="error" className="my-4">
            {listError}
          </Alert>
        )}

        {/* Empty state */}
        {!loadingList && !listError && complaints.length === 0 && (
          <EmptyState
            icon={Clock}
            title="No submitted reports are currently awaiting review."
            description="When citizens submit reports, they will appear here for review."
          />
        )}

        {/* Complaints Table (Desktop) / Cards (Mobile) */}
        {!loadingList && complaints.length > 0 && (
          <>
            {/* Desktop Table View */}
            <div className="hidden md:block mt-4 overflow-x-auto">
              <table className="w-full min-w-[640px] text-left text-xs sm:text-sm text-slate-800">
                <thead className="bg-slate-100/80 text-xs uppercase tracking-wider text-slate-600 font-bold border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3 font-bold">Report ID</th>
                    <th className="px-4 py-3 font-bold">Issue / Problem</th>
                    <th className="px-4 py-3 font-bold">Category / Urgency</th>
                    <th className="px-4 py-3 font-bold">Location</th>
                    <th className="px-4 py-3 font-bold">Submitted</th>
                    <th className="px-4 py-3 font-bold">Status</th>
                    <th className="px-4 py-3 font-bold text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {complaints.map((c) => (
                    <tr key={c.id} className="hover:bg-slate-50/70 transition">
                      <td className="px-4 py-3 font-mono text-xs text-slate-600 font-medium">
                        {c.id.slice(0, 8)}…
                      </td>
                      <td className="px-4 py-3 max-w-xs truncate font-semibold text-slate-900 text-sm">
                        {c.final_problem || c.original_problem}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-col gap-0.5">
                          <span className="font-semibold text-slate-900 text-xs sm:text-sm">{c.category || 'Civic Issue'}</span>
                          {c.urgency_level && (
                            <span className="text-xs text-slate-600 font-medium">
                              Urgency: {c.urgency_level}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 max-w-[180px] truncate text-slate-700 text-xs sm:text-sm font-medium">
                        {c.final_address || c.original_address || 'No address provided'}
                      </td>
                      <td className="px-4 py-3 text-slate-600 whitespace-nowrap text-xs font-medium">
                        {c.submitted_at ? new Date(c.submitted_at).toLocaleDateString() : 'Draft'}
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={c.status} size="xs" />
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          type="button"
                          onClick={() => handleSelectComplaint(c.id)}
                          className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded font-semibold text-xs sm:text-sm transition inline-flex items-center gap-1 shadow-xs"
                        >
                          <Eye className="w-3.5 h-3.5" aria-hidden="true" />
                          <span>Review</span>
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile Card List View */}
            <div className="md:hidden mt-4 space-y-3">
              {complaints.map((c) => (
                <div key={c.id} className="p-3.5 sm:p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs text-slate-600 font-medium">{c.id.slice(0, 8)}…</span>
                    <StatusBadge status={c.status} size="xs" />
                  </div>
                  <div className="font-bold text-slate-900 text-base">
                    {c.final_problem || c.original_problem}
                  </div>
                  <div className="text-slate-600 text-xs font-medium">
                    Location: {c.final_address || c.original_address || 'Not specified'}
                  </div>
                  <div className="pt-2 flex items-center justify-between border-t border-slate-200">
                    <span className="text-xs text-slate-500 font-medium">
                      {c.submitted_at ? new Date(c.submitted_at).toLocaleDateString() : 'Draft'}
                    </span>
                    <button
                      type="button"
                      onClick={() => handleSelectComplaint(c.id)}
                      className="px-3 py-1.5 bg-blue-600 text-white rounded-lg font-semibold text-xs sm:text-sm inline-flex items-center gap-1 shadow-xs"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      <span>Review Report</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
