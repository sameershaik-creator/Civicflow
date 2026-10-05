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
      <div className="h-56 bg-slate-100 animate-pulse rounded-lg flex items-center justify-center text-xs text-slate-400">
        <RefreshCw className="w-4 h-4 animate-spin mr-2" aria-hidden="true" />
        <span>Loading evidence photo...</span>
      </div>
    );
  }

  if (error || !imageSrc) {
    return (
      <div className="h-56 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-center text-xs text-slate-500">
        <AlertCircle className="w-4 h-4 text-slate-400 mr-2" aria-hidden="true" />
        <span>Evidence photo could not be loaded</span>
      </div>
    );
  }

  return (
    <img
      src={imageSrc}
      alt={alt || 'Complaint evidence'}
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
      setListError(err.message || 'Failed to load complaints.');
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
      setDetailError(err.message || 'Failed to load complaint detail.');
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
      setActionSuccess('Complaint accepted for municipal action.');
      setComplaints(prev => prev.map(c => c.id === updated.id ? { ...c, status: 'ACCEPTED', decided_at: updated.decided_at } : c));
    } catch (err) {
      setActionError(err.message || 'Failed to accept complaint.');
    } finally {
      setAdjudicating(false);
    }
  }

  async function handleConfirmReject(e) {
    e.preventDefault();
    if (!selectedComplaint) return;

    if (!rejectionReason.trim()) {
      setReasonError('Please provide a specific, objective municipal reason for rejection.');
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
      setActionSuccess('Complaint rejected for administrative record.');
      setComplaints(prev => prev.map(c => c.id === updated.id ? { ...c, status: 'REJECTED', decided_at: updated.decided_at, admin_reason: updated.admin_reason } : c));
    } catch (err) {
      setActionError(err.message || 'Failed to reject complaint.');
    } finally {
      setAdjudicating(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-slate-900 text-white rounded-xl p-6 shadow-sm border border-slate-800">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-6 h-6 text-blue-400" aria-hidden="true" />
              <h2 className="text-xl font-bold tracking-tight">
                Municipal Adjudication Console
              </h2>
            </div>
            <p className="text-xs text-slate-400 mt-1 max-w-2xl">
              Inspect submitted citizen reports, evaluate multi-layer provenance and GIS verification, and make authoritative municipal adjudication decisions.
            </p>
          </div>
          <div className="text-right">
            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-950 text-blue-300 border border-blue-800">
              Admin: {currentUser?.name || currentUser?.email}
            </span>
          </div>
        </div>
      </div>

      {/* Detail Adjudication Card */}
      {selectedComplaint && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          {/* Header Bar */}
          <div className="px-6 py-4 bg-slate-50 border-b border-slate-200 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => setSelectedComplaint(null)}
                className="px-3 py-1.5 text-xs text-slate-700 hover:text-slate-900 bg-white border border-slate-300 hover:bg-slate-50 rounded-lg font-medium transition inline-flex items-center gap-1.5 shadow-xs"
              >
                <ArrowLeft className="w-3.5 h-3.5" aria-hidden="true" />
                <span>Back to Queue</span>
              </button>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold text-slate-900">
                    Complaint Case File
                  </h3>
                  <span className="font-mono text-xs text-slate-500 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                    {selectedComplaint.id}
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  Citizen: {selectedComplaint.citizen_name || 'Anonymous'} ({selectedComplaint.citizen_email || 'No email'})
                </p>
              </div>
            </div>

            <StatusBadge status={selectedComplaint.status} size="lg" />
          </div>

          <div className="p-6 space-y-6">
            {/* Feedback Notifications */}
            {actionSuccess && (
              <Alert variant="success" title="Adjudication Recorded">
                {actionSuccess}
                {selectedComplaint.decided_at && (
                  <span className="block mt-1 font-mono text-[11px] text-emerald-800">
                    Timestamp (UTC): {new Date(selectedComplaint.decided_at).toUTCString()}
                  </span>
                )}
              </Alert>
            )}

            {actionError && (
              <Alert variant="error" title="Adjudication Error">
                {actionError}
              </Alert>
            )}

            {/* Terminal Banners */}
            {selectedComplaint.status === 'ACCEPTED' && (
              <Alert variant="success" title="Complaint Accepted for Municipal Action">
                This complaint has been reviewed and formally accepted. The case file is now terminal and permanently locked against further modification.
                {selectedComplaint.decided_at && (
                  <span className="block mt-1 font-mono text-[11px] text-emerald-800">
                    Decided at (UTC): {new Date(selectedComplaint.decided_at).toUTCString()}
                  </span>
                )}
              </Alert>
            )}

            {selectedComplaint.status === 'REJECTED' && (
              <Alert variant="error" title="Complaint Formally Rejected">
                This complaint has been formally declined by the municipality.
                <div className="mt-2 p-3 bg-white border border-rose-200 rounded-lg">
                  <span className="font-semibold text-rose-900 block mb-0.5">Official Rejection Reason:</span>
                  <p className="text-rose-800 font-sans">{selectedComplaint.admin_reason}</p>
                </div>
                {selectedComplaint.decided_at && (
                  <span className="block mt-2 font-mono text-[11px] text-rose-800">
                    Decided at (UTC): {new Date(selectedComplaint.decided_at).toUTCString()}
                  </span>
                )}
              </Alert>
            )}

            {/* Section 1: Physical Incident Evidence */}
            <div className="border border-slate-200 rounded-xl p-5 bg-slate-50/50">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-600 mb-3 flex items-center gap-2">
                <Camera className="w-4 h-4 text-slate-500" aria-hidden="true" />
                <span>1. Physical Incident Evidence & Raw Citizen Input</span>
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="md:col-span-1">
                  <AuthenticatedImage complaintId={selectedComplaint.id} alt="Physical incident evidence" />
                </div>
                <div className="md:col-span-2 bg-white p-4 rounded-lg border border-slate-200 text-xs space-y-2.5">
                  <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wide">
                    Layer 1 Provenance (Citizen Original)
                  </div>
                  <div>
                    <span className="font-semibold text-slate-700">Problem Description:</span>
                    <p className="text-slate-800 mt-0.5">{selectedComplaint.original_problem}</p>
                  </div>
                  {selectedComplaint.original_address && (
                    <div>
                      <span className="font-semibold text-slate-700">Reported Address Hint:</span>
                      <p className="text-slate-800 mt-0.5">{selectedComplaint.original_address}</p>
                    </div>
                  )}
                  {selectedComplaint.original_latitude !== null && selectedComplaint.original_longitude !== null && (
                    <div>
                      <span className="font-semibold text-slate-700">Device Coordinates (Telemetry):</span>
                      <p className="font-mono text-slate-600 mt-0.5">
                        Lat: {selectedComplaint.original_latitude.toFixed(6)}, Lon: {selectedComplaint.original_longitude.toFixed(6)}
                      </p>
                    </div>
                  )}
                  {selectedComplaint.submitted_at && (
                    <div>
                      <span className="font-semibold text-slate-700">Submitted at (UTC):</span>
                      <p className="font-mono text-slate-600 mt-0.5">
                        {new Date(selectedComplaint.submitted_at).toUTCString()}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Section 2: AI-Assisted Interpretation */}
            <div className="border border-slate-200 rounded-xl p-5 bg-slate-50/50">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-600 mb-3 flex items-center gap-2">
                <FileText className="w-4 h-4 text-blue-600" aria-hidden="true" />
                <span>2. AI-Assisted Interpretation (Layer 2 Provenance)</span>
              </h4>
              <div className="bg-white p-4 rounded-lg border border-slate-200 text-xs space-y-3">
                <div className="flex flex-wrap items-center gap-3">
                  {selectedComplaint.category && (
                    <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-blue-100 text-blue-800">
                      Category: {selectedComplaint.category}
                    </span>
                  )}
                  {selectedComplaint.urgency_level && (
                    <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-slate-100 text-slate-800">
                      Urgency: {selectedComplaint.urgency_level}
                    </span>
                  )}
                </div>

                {selectedComplaint.observed_issue && (
                  <div>
                    <span className="font-semibold text-slate-700 block mb-0.5">Observed Physical Issue (Visual Evidence):</span>
                    <p className="text-slate-800 bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                      {selectedComplaint.observed_issue}
                    </p>
                  </div>
                )}

                {selectedComplaint.citizen_claim && (
                  <div>
                    <span className="font-semibold text-slate-700 block mb-0.5">Citizen Claim (Reported Statement):</span>
                    <p className="text-slate-800 bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                      {selectedComplaint.citizen_claim}
                    </p>
                  </div>
                )}

                {selectedComplaint.formal_summary && (
                  <div>
                    <span className="font-semibold text-slate-700 block mb-0.5">Formal Municipal Summary:</span>
                    <p className="text-slate-800 bg-slate-50 p-2.5 rounded-lg border border-slate-200 font-medium">
                      {selectedComplaint.formal_summary}
                    </p>
                  </div>
                )}

                {selectedComplaint.warnings && selectedComplaint.warnings.length > 0 && (
                  <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-900">
                    <span className="font-semibold block mb-1">Observations & Warnings:</span>
                    <ul className="list-disc list-inside space-y-0.5 text-[11px]">
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
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-600 mb-3 flex items-center gap-2">
                <User className="w-4 h-4 text-emerald-600" aria-hidden="true" />
                <span>3. Citizen-Reviewed Final Report (Layer 3 Provenance)</span>
              </h4>
              <div className="bg-white p-4 rounded-lg border border-slate-200 text-xs space-y-3">
                <div>
                  <span className="font-semibold text-slate-700 block mb-0.5">Final Confirmed Problem Description:</span>
                  <p className="text-slate-900 bg-slate-50 p-2.5 rounded-lg border border-slate-200 font-medium">
                    {selectedComplaint.final_problem || selectedComplaint.original_problem}
                  </p>
                </div>
                {selectedComplaint.final_address && (
                  <div>
                    <span className="font-semibold text-slate-700 block mb-0.5">Confirmed Address / Location:</span>
                    <p className="text-slate-800 bg-slate-50 p-2 rounded-lg border border-slate-200">
                      {selectedComplaint.final_address}
                    </p>
                  </div>
                )}
                {selectedComplaint.final_summary && (
                  <div>
                    <span className="font-semibold text-slate-700 block mb-0.5">Confirmed Official Summary:</span>
                    <p className="text-slate-800 bg-slate-50 p-2 rounded-lg border border-slate-200">
                      {selectedComplaint.final_summary}
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Section 4: Geographic Verification & Map */}
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-600 mb-3 flex items-center gap-2">
                <Navigation className="w-4 h-4 text-blue-600" aria-hidden="true" />
                <span>4. Geographic Verification & Location Map</span>
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
                <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-500">
                  No verified coordinates attached to this complaint.
                </div>
              )}
            </div>

            {/* Section 5: Authoritative Adjudication Decision */}
            <div className="pt-6 border-t border-slate-200">
              <h4 className="text-sm font-bold text-slate-900 mb-1 flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-blue-600" aria-hidden="true" />
                <span>5. Authoritative Adjudication Decision</span>
              </h4>

              {String(selectedComplaint.status).toUpperCase() === 'ACCEPTED' && (
                <div className="mt-3 p-4 bg-emerald-50 border border-emerald-300 rounded-xl text-emerald-950">
                  <div className="flex items-center gap-2 font-bold text-sm">
                    <CheckCircle className="w-4 h-4 text-emerald-600" aria-hidden="true" />
                    <span>✓ Complaint Officially Accepted</span>
                  </div>
                  <p className="text-xs text-emerald-800 mt-1">
                    This complaint has been reviewed and accepted by municipal administration for field dispatch and resolution. The case file is officially closed for further adjudication.
                  </p>
                  {selectedComplaint.decided_at && (
                    <span className="block mt-2 font-mono text-[11px] text-emerald-700">
                      Adjudication Timestamp (UTC): {new Date(selectedComplaint.decided_at).toUTCString()}
                    </span>
                  )}
                </div>
              )}

              {String(selectedComplaint.status).toUpperCase() === 'REJECTED' && (
                <div className="mt-3 p-4 bg-rose-50 border border-rose-300 rounded-xl text-rose-950">
                  <div className="flex items-center gap-2 font-bold text-sm">
                    <XCircle className="w-4 h-4 text-rose-600" aria-hidden="true" />
                    <span>✕ Complaint Formally Rejected</span>
                  </div>
                  {selectedComplaint.admin_reason && (
                    <div className="mt-2 p-3 bg-white border border-rose-200 rounded-lg text-xs">
                      <span className="font-semibold text-rose-900 block mb-0.5">Municipal Rejection Reason:</span>
                      <p className="text-rose-800">{selectedComplaint.admin_reason}</p>
                    </div>
                  )}
                  {selectedComplaint.decided_at && (
                    <span className="block mt-2 font-mono text-[11px] text-rose-700">
                      Adjudication Timestamp (UTC): {new Date(selectedComplaint.decided_at).toUTCString()}
                    </span>
                  )}
                </div>
              )}

              {String(selectedComplaint.status).toUpperCase() === 'SUBMITTED' && (
                <div className="mt-3">
                  <p className="text-xs text-slate-600 mb-4">
                    Review the complete case file and provenance above. Accepting confirms the report for municipal dispatch; rejecting records an objective public reason delivered directly to the citizen.
                  </p>

                  {!showRejectBox ? (
                    <div className="flex flex-wrap items-center gap-4">
                      <button
                        type="button"
                        onClick={handleAccept}
                        disabled={adjudicating}
                        className="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold transition shadow-sm inline-flex items-center gap-2 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2"
                      >
                        {adjudicating ? (
                          <RefreshCw className="w-4 h-4 animate-spin" />
                        ) : (
                          <CheckCircle className="w-4 h-4" />
                        )}
                        <span>Accept Complaint</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => setShowRejectBox(true)}
                        disabled={adjudicating}
                        className="px-6 py-2.5 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-bold transition shadow-sm inline-flex items-center gap-2 focus:outline-none focus:ring-2 focus:ring-rose-500 focus:ring-offset-2"
                      >
                        <XCircle className="w-4 h-4" />
                        <span>Reject Complaint</span>
                      </button>
                    </div>
                  ) : (
                    <form onSubmit={handleConfirmReject} className="p-5 bg-rose-50 border border-rose-200 rounded-xl space-y-4">
                      <div>
                        <label htmlFor="rejection-reason" className="block text-xs font-bold text-rose-950 mb-1">
                          Administrative Rejection Reason <span className="text-rose-600">*</span>
                        </label>
                        <p className="text-[11px] text-rose-800 mb-2">
                          State a clear, objective reason for rejection (e.g. Issue falls outside municipal jurisdiction, duplicate of active work order). This will be delivered directly to the citizen.
                        </p>
                        <textarea
                          id="rejection-reason"
                          rows={3}
                          required
                          value={rejectionReason}
                          onChange={(e) => setRejectionReason(e.target.value)}
                          placeholder="State clear, objective municipal reason for rejection..."
                          className="w-full px-3 py-2 text-xs border border-rose-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-rose-500 bg-white"
                        />
                        {reasonError && (
                          <p className="text-xs text-rose-700 font-medium mt-1">{reasonError}</p>
                        )}
                      </div>

                      <div className="flex items-center gap-3">
                        <button
                          type="submit"
                          disabled={adjudicating}
                          className="px-5 py-2.5 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-bold transition shadow-sm inline-flex items-center gap-2"
                        >
                          {adjudicating && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                          <span>Confirm Rejection</span>
                        </button>

                        <button
                          type="button"
                          onClick={() => {
                            setShowRejectBox(false);
                            setRejectionReason('');
                            setReasonError(null);
                          }}
                          disabled={adjudicating}
                          className="px-4 py-2 border border-slate-300 hover:bg-slate-100 text-slate-700 rounded-lg text-xs font-medium transition"
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
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-200">
          <div>
            <h3 className="text-sm font-bold text-slate-900">
              Municipal Triage Queue
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Review submitted citizen complaints and inspect full evidence before adjudication.
            </p>
          </div>

          {/* Status Filter */}
          <div className="flex items-center gap-2">
            <Filter className="w-3.5 h-3.5 text-slate-400" aria-hidden="true" />
            <label htmlFor="status-filter-select" className="text-xs font-medium text-slate-600">Filter Queue:</label>
            <select
              id="status-filter-select"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium"
            >
              <option value="SUBMITTED">SUBMITTED (Awaiting Adjudication)</option>
              <option value="ACCEPTED">ACCEPTED (Approved)</option>
              <option value="REJECTED">REJECTED (Declined)</option>
              <option value="ALL">ALL Adjudicable (Submitted, Accepted, Rejected)</option>
            </select>
          </div>
        </div>

        {/* Loading state */}
        {loadingList && (
          <LoadingState message="Loading complaints from database..." />
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
            title="No submitted complaints are currently awaiting review."
            description="When citizens complete the human review process and submit complaints, they will appear in this triage queue."
          />
        )}

        {/* Complaints Table (Desktop) / Cards (Mobile) */}
        {!loadingList && complaints.length > 0 && (
          <>
            {/* Desktop Table View */}
            <div className="hidden md:block mt-4 overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-700">
                <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500 border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3 font-semibold">Complaint ID</th>
                    <th className="px-4 py-3 font-semibold">Issue / Problem</th>
                    <th className="px-4 py-3 font-semibold">Category / Urgency</th>
                    <th className="px-4 py-3 font-semibold">Location</th>
                    <th className="px-4 py-3 font-semibold">Submitted</th>
                    <th className="px-4 py-3 font-semibold">Status</th>
                    <th className="px-4 py-3 font-semibold text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {complaints.map((c) => (
                    <tr key={c.id} className="hover:bg-slate-50/70 transition">
                      <td className="px-4 py-3 font-mono text-[11px] text-slate-500">
                        {c.id.slice(0, 8)}…
                      </td>
                      <td className="px-4 py-3 max-w-xs truncate font-medium text-slate-900">
                        {c.final_problem || c.original_problem}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-col gap-0.5">
                          <span className="font-medium text-slate-800">{c.category || 'Civic Issue'}</span>
                          {c.urgency_level && (
                            <span className="text-[10px] text-slate-500 font-semibold">
                              Urgency: {c.urgency_level}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 max-w-[180px] truncate text-slate-600">
                        {c.final_address || c.original_address || 'No address provided'}
                      </td>
                      <td className="px-4 py-3 text-slate-500 whitespace-nowrap text-[11px]">
                        {c.submitted_at ? new Date(c.submitted_at).toLocaleDateString() : 'Draft'}
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={c.status} size="xs" />
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          type="button"
                          onClick={() => handleSelectComplaint(c.id)}
                          className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded font-medium text-xs transition inline-flex items-center gap-1 shadow-xs"
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
                <div key={c.id} className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[11px] text-slate-500">{c.id.slice(0, 8)}…</span>
                    <StatusBadge status={c.status} size="xs" />
                  </div>
                  <div className="font-semibold text-slate-900 text-sm">
                    {c.final_problem || c.original_problem}
                  </div>
                  <div className="text-slate-500 text-[11px]">
                    Location: {c.final_address || c.original_address || 'Not specified'}
                  </div>
                  <div className="pt-2 flex items-center justify-between border-t border-slate-200">
                    <span className="text-[11px] text-slate-400">
                      {c.submitted_at ? new Date(c.submitted_at).toLocaleDateString() : 'Draft'}
                    </span>
                    <button
                      type="button"
                      onClick={() => handleSelectComplaint(c.id)}
                      className="px-3 py-1.5 bg-blue-600 text-white rounded-lg font-semibold text-xs inline-flex items-center gap-1 shadow-xs"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      <span>Review Case</span>
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
