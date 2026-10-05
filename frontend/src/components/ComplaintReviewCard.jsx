import React, { useState, useEffect } from 'react';
import { 
  FileText, 
  MapPin, 
  AlertCircle, 
  CheckCircle, 
  XCircle, 
  Save, 
  RotateCcw, 
  RefreshCw, 
  Eye, 
  ShieldCheck, 
  Send, 
  Lock,
  X,
  UserCheck,
  Cpu,
  Camera,
  Navigation,
  Trash2
} from 'lucide-react';
import { 
  updateComplaintDraft, 
  submitComplaint, 
  getComplaintAIDraft, 
  getComplaintLocation, 
  fetchComplaintImageBlob,
  analyzeComplaintWithAI,
  fetchComplaintById,
  deleteComplaintById
} from '../services/complaints';
import InteractiveMap from './InteractiveMap';
import StatusBadge from './ui/StatusBadge';
import Alert from './ui/Alert';

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
      <div className="h-48 bg-slate-100 animate-pulse rounded-lg flex items-center justify-center text-xs text-slate-400">
        <RefreshCw className="w-4 h-4 animate-spin mr-2" aria-hidden="true" />
        <span>Loading photo...</span>
      </div>
    );
  }

  if (error || !imageSrc) {
    return (
      <div className="h-48 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-center text-xs text-slate-500">
        <AlertCircle className="w-4 h-4 text-slate-400 mr-2" aria-hidden="true" />
        <span>Photo could not be loaded</span>
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

export default function ComplaintReviewCard({ complaint: initialComplaint, onDraftUpdated, onClose, onComplaintDeleted }) {
  // Authoritative complaint state initialized from prop and synchronized with database
  const [complaint, setComplaint] = useState(initialComplaint);

  useEffect(() => {
    setComplaint(initialComplaint);
  }, [initialComplaint]);

  // AI Draft state
  const [aiDraft, setAiDraft] = useState(null);
  const [loadingAI, setLoadingAI] = useState(false);
  const [aiError, setAiError] = useState(null);

  // Geographic data
  const [locationData, setLocationData] = useState(null);
  const [loadingLocation, setLoadingLocation] = useState(false);

  // Citizen editable fields
  const [finalProblem, setFinalProblem] = useState('');
  const [finalAddress, setFinalAddress] = useState('');
  const [finalSummary, setFinalSummary] = useState('');

  // Draft save states
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saveError, setSaveError] = useState(null);

  // Final submission states
  const [submittingFinal, setSubmittingFinal] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState(false);
  const [submitError, setSubmitError] = useState(null);

  // Delete complaint states
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState(null);

  const currentStatus = complaint?.status || 'AI_GENERATED';
  const isAccepted = currentStatus === 'ACCEPTED';
  const isRejected = currentStatus === 'REJECTED';
  const isTerminal = isAccepted || isRejected;
  const isSubmitted = currentStatus === 'SUBMITTED';
  const isLocked = isSubmitted || isTerminal;
  const [retryingAI, setRetryingAI] = useState(false);

  useEffect(() => {
    if (!complaint?.id) return;

    let isMounted = true;

    async function syncComplaintAndDrafts() {
      // 1. Immediately fetch the fresh, authoritative complaint from the server
      try {
        const fresh = await fetchComplaintById(complaint.id);
        if (isMounted && fresh) {
          setComplaint(fresh);
          setFinalProblem(fresh.final_problem || fresh.ai_problem || '');
          setFinalAddress(fresh.final_address || fresh.original_address || '');
          setFinalSummary(fresh.final_summary || fresh.ai_summary || '');
          setSubmitSuccess(fresh.status === 'SUBMITTED');
        }
      } catch {
        if (isMounted) {
          setFinalProblem(complaint.final_problem || complaint.ai_problem || '');
          setFinalAddress(complaint.final_address || complaint.original_address || '');
          setFinalSummary(complaint.final_summary || complaint.ai_summary || '');
          setSubmitSuccess(complaint.status === 'SUBMITTED');
        }
      }

      setSaveSuccess(false);
      setSaveError(null);
      setSubmitError(null);

      // 2. Fetch full structured AI draft and geographic details
      loadAIDraft(complaint.id);
      loadLocationDetails(complaint.id);
    }

    syncComplaintAndDrafts();

    return () => {
      isMounted = false;
    };
  }, [complaint?.id]);

  async function loadAIDraft(id) {
    setLoadingAI(true);
    setAiError(null);
    try {
      const draft = await getComplaintAIDraft(id);
      setAiDraft(draft);
      // Ensure backend status and AI fields are fully synchronized
      const fresh = await fetchComplaintById(id);
      if (fresh) {
        setComplaint(fresh);
        if (!fresh.final_problem && draft.observed_issue) {
          setFinalProblem(draft.observed_issue);
        }
        if (!fresh.final_summary && draft.formal_summary) {
          setFinalSummary(draft.formal_summary);
        }
      }
    } catch {
      // Fallback cleanly to persisted complaint fields if sidecar draft is not on disk
      setAiDraft(null);
    } finally {
      setLoadingAI(false);
    }
  }

  async function loadLocationDetails(id) {
    setLoadingLocation(true);
    try {
      const loc = await getComplaintLocation(id);
      setLocationData(loc);
    } catch {
      // Ignored
    } finally {
      setLoadingLocation(false);
    }
  }

  async function handleRetryAI() {
    if (isLocked || retryingAI) return;
    setRetryingAI(true);
    setAiError(null);
    try {
      const draft = await analyzeComplaintWithAI(complaint.id);
      setAiDraft(draft);
      const refreshed = await fetchComplaintById(complaint.id);
      if (refreshed) {
        setComplaint(refreshed);
        if (draft.observed_issue) {
          setFinalProblem(draft.observed_issue);
        }
        if (draft.formal_summary) {
          setFinalSummary(draft.formal_summary);
        }
        if (onDraftUpdated) {
          onDraftUpdated(refreshed);
        }
      }
    } catch (err) {
      setAiError(err.message || 'Report details could not be prepared.');
    } finally {
      setRetryingAI(false);
    }
  }

  async function handleDeleteComplaint() {
    if (deleting) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await deleteComplaintById(complaint.id);
      setShowDeleteModal(false);
      if (onComplaintDeleted) {
        onComplaintDeleted(complaint.id);
      } else if (onClose) {
        onClose();
      }
    } catch (err) {
      setDeleteError(err.message || 'Failed to delete report.');
    } finally {
      setDeleting(false);
    }
  }

  function handleReset() {
    if (isLocked) return;
    setFinalProblem(aiDraft?.observed_issue || complaint.ai_problem || '');
    setFinalAddress(complaint.original_address || '');
    setFinalSummary(aiDraft?.formal_summary || complaint.ai_summary || '');
    setSaveError(null);
    setSaveSuccess(false);
  }

  async function handleSaveDraft(e) {
    if (e && e.preventDefault) e.preventDefault();
    if (isLocked) return;
    if (!finalProblem.trim()) {
      setSaveError('Problem description cannot be empty.');
      return;
    }

    setSaving(true);
    setSaveError(null);
    setSaveSuccess(false);

    try {
      const updated = await updateComplaintDraft(complaint.id, {
        final_problem: finalProblem,
        final_address: finalAddress,
        final_summary: finalSummary,
      });

      setComplaint(updated);
      setSaveSuccess(true);
      if (onDraftUpdated) {
        onDraftUpdated(updated);
      }
      return updated;
    } catch (err) {
      setSaveError(err.message || 'Failed to save changes.');
      throw err;
    } finally {
      setSaving(false);
    }
  }

  async function handleSubmitComplaint() {
    if (isSubmitted || isTerminal) return;
    if (currentStatus === 'DRAFT') {
      setSubmitError('This report is still being prepared and must be reviewed before submission.');
      return;
    }
    if (!finalProblem.trim()) {
      setSubmitError('Please save a confirmed problem description before submission.');
      return;
    }

    setSubmittingFinal(true);
    setSubmitError(null);

    try {
      // Step 1: If currently in AI_GENERATED, save the human review edits first
      // This strictly transitions the complaint from AI_GENERATED to UNDER_REVIEW in the DB
      if (currentStatus === 'AI_GENERATED') {
        const updated = await updateComplaintDraft(complaint.id, {
          final_problem: finalProblem,
          final_address: finalAddress,
          final_summary: finalSummary,
        });
        setComplaint(updated);
      } else if (currentStatus === 'UNDER_REVIEW') {
        // Also persist any updated unsaved edits before submitting
        const updated = await updateComplaintDraft(complaint.id, {
          final_problem: finalProblem,
          final_address: finalAddress,
          final_summary: finalSummary,
        });
        setComplaint(updated);
      }

      // Step 2: Final authoritative submission to municipal triage queue (SUBMITTED)
      const submitted = await submitComplaint(complaint.id);
      setComplaint(submitted);
      setSubmitSuccess(true);
      if (onDraftUpdated) {
        onDraftUpdated(submitted);
      }
    } catch (err) {
      setSubmitError(err.message || 'Submission failed.');
    } finally {
      setSubmittingFinal(false);
    }
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden mb-10">
      {/* Header Bar */}
      <div className="px-4 sm:px-6 py-3.5 sm:py-4 bg-slate-50 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3 sm:gap-4">
        <div>
          <div className="flex items-center gap-2">
            <UserCheck className="w-5 h-5 text-blue-600" aria-hidden="true" />
            <h3 className="text-base sm:text-lg font-bold text-slate-900">
              {isSubmitted ? 'Report Details (Submitted)' : 'Review & Confirm Report'}
            </h3>
            <span className="font-mono text-xs text-slate-600 bg-white px-2 py-0.5 rounded border border-slate-200 font-medium">
              {complaint.id.slice(0, 8)}…
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-600 mt-1 leading-normal">
            {isAccepted
              ? 'This report has been accepted by municipal administration.'
              : isRejected
              ? 'This report was reviewed and declined by municipal administration.'
              : isSubmitted
              ? 'This report has been submitted and is locked for editing.'
              : 'Review the details below and make any necessary adjustments before submitting your report.'}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <StatusBadge status={currentStatus} />
          <button
            type="button"
            onClick={() => setShowDeleteModal(true)}
            className="px-2.5 py-1 text-xs sm:text-sm text-rose-700 bg-white hover:bg-rose-50 border border-rose-300 rounded-lg font-semibold inline-flex items-center gap-1.5 transition shadow-xs"
            title="Delete this report"
          >
            <Trash2 className="w-3.5 h-3.5" aria-hidden="true" />
            <span className="hidden sm:inline">Delete</span>
          </button>
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              aria-label="Close review panel"
              className="text-slate-400 hover:text-slate-600 p-1.5 hover:bg-slate-200 rounded-md transition"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      <div className="p-4 sm:p-6 space-y-5 sm:space-y-6">
        {/* Terminal or Submission Feedback Banners */}
        {isAccepted && (
          <Alert variant="success" title="Report Accepted">
            This report has been reviewed and accepted by municipal administration.
            {complaint.decided_at && (
              <span className="block mt-1 font-mono text-[11px] text-emerald-800">
                Decision recorded (UTC): {new Date(complaint.decided_at).toUTCString()}
              </span>
            )}
          </Alert>
        )}

        {isRejected && (
          <Alert variant="error" title="Report Declined">
            This report was reviewed and declined by municipal administration.
            {complaint.admin_reason && (
              <div className="mt-2 p-3 bg-white border border-rose-200 rounded-lg">
                <span className="font-semibold text-rose-900 block mb-0.5">Reason:</span>
                <p className="text-rose-800 font-sans">{complaint.admin_reason}</p>
              </div>
            )}
            {complaint.decided_at && (
              <span className="block mt-2 font-mono text-[11px] text-rose-800">
                Decision recorded (UTC): {new Date(complaint.decided_at).toUTCString()}
              </span>
            )}
          </Alert>
        )}

        {isSubmitted && !isTerminal && (
          <div className="p-4 bg-emerald-50 border border-emerald-300 rounded-xl text-emerald-900 shadow-xs">
            <div className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-emerald-600" aria-hidden="true" />
              <h4 className="text-sm font-bold text-emerald-950">✓ Report Submitted</h4>
            </div>
            <div className="mt-1.5 text-xs sm:text-sm">
              <p className="font-semibold text-emerald-900">
                Status: SUBMITTED — Awaiting Review
              </p>
              <p className="text-emerald-800 mt-1 leading-normal">
                Your report has been submitted. It is now queued for municipal review.
              </p>
              {complaint.submitted_at && (
                <span className="block mt-1 font-mono text-xs text-emerald-700">
                  Submitted at (UTC): {new Date(complaint.submitted_at).toUTCString()}
                </span>
              )}
            </div>
          </div>
        )}

        {saveSuccess && (
          <Alert variant="success" onClose={() => setSaveSuccess(false)}>
            Draft changes saved successfully.
          </Alert>
        )}

        {saveError && (
          <Alert variant="error" onClose={() => setSaveError(null)}>
            {saveError}
          </Alert>
        )}

        {submitError && (
          <Alert variant="error" onClose={() => setSubmitError(null)}>
            {submitError}
          </Alert>
        )}

        {/* Layer 1: Original Citizen Evidence */}
        <section aria-labelledby="layer1-heading" className="border border-slate-200 rounded-xl p-4 sm:p-5 bg-slate-50/50">
          <div className="flex items-center gap-2 mb-3">
            <Camera className="w-4 h-4 text-slate-500" aria-hidden="true" />
            <h4 id="layer1-heading" className="text-sm font-bold uppercase tracking-wider text-slate-700">
              1. Photos & Submitted Details
            </h4>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-1">
              <AuthenticatedImage complaintId={complaint.id} alt="Original incident evidence" />
            </div>
            <div className="md:col-span-2 space-y-2 text-xs sm:text-sm">
              <div>
                <span className="font-semibold text-slate-800 block text-xs sm:text-sm">Problem Description:</span>
                <p className="text-slate-900 mt-1 bg-white p-3 rounded-lg border border-slate-200 text-sm leading-relaxed">
                  {complaint.original_problem}
                </p>
              </div>

              {complaint.original_address && (
                <div>
                  <span className="font-semibold text-slate-800 block text-xs sm:text-sm">Incident Address:</span>
                  <p className="text-slate-900 mt-1 bg-white p-2.5 rounded-lg border border-slate-200 text-sm">
                    {complaint.original_address}
                  </p>
                </div>
              )}

              {complaint.original_latitude !== null && complaint.original_longitude !== null && (
                <div>
                  <span className="font-semibold text-slate-800 block text-xs sm:text-sm">GPS Coordinates:</span>
                  <p className="font-mono text-slate-700 mt-1 bg-white p-2.5 rounded-lg border border-slate-200 text-xs sm:text-sm font-medium">
                    {complaint.original_latitude.toFixed(6)}, {complaint.original_longitude.toFixed(6)}
                  </p>
                </div>
              )}
            </div>
          </div>
        </section>

        {/* Layer 2: AI-Assisted Interpretation */}
        {(() => {
          const displayAi = aiDraft;

          return (
            <section aria-labelledby="layer2-heading" className="border border-slate-200 rounded-xl p-4 sm:p-5 bg-slate-50/50">
              <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                <div className="flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-blue-600 shrink-0" aria-hidden="true" />
                  <div>
                    <h4 id="layer2-heading" className="text-sm font-bold uppercase tracking-wider text-slate-800">
                      2. Report Details
                    </h4>
                    <span className="text-xs text-slate-600 font-normal">
                      Structured details — review before submission
                    </span>
                  </div>
                </div>
                {displayAi && (
                  <div className="flex flex-wrap items-center gap-2">
                    {displayAi.category && (
                      <span className="px-2.5 py-0.5 bg-blue-100 text-blue-800 rounded-full text-xs font-semibold">
                        {displayAi.category}
                      </span>
                    )}
                    {displayAi.urgency_level && (
                      <span className="px-2.5 py-0.5 bg-slate-200 text-slate-800 rounded-full text-xs font-semibold">
                        Urgency: {displayAi.urgency_level}
                      </span>
                    )}
                  </div>
                )}
              </div>

              {loadingAI ? (
                <div className="py-6 text-center text-xs sm:text-sm text-slate-600 font-medium flex items-center justify-center gap-2">
                  <RefreshCw className="w-4 h-4 animate-spin text-blue-600" aria-hidden="true" />
                  <span>Preparing report details...</span>
                </div>
              ) : displayAi ? (
                <div className="space-y-3.5">
                  {displayAi.observed_issue && (
                    <div>
                      <span className="font-semibold text-slate-800 block mb-1 text-xs sm:text-sm">Observed Issue:</span>
                      <p className="text-slate-900 bg-white p-3 rounded-lg border border-slate-200 text-sm leading-relaxed">
                        {displayAi.observed_issue}
                      </p>
                    </div>
                  )}

                  {displayAi.citizen_claim && (
                    <div>
                      <span className="font-semibold text-slate-800 block mb-1 text-xs sm:text-sm">Reported Description:</span>
                      <p className="text-slate-900 bg-white p-3 rounded-lg border border-slate-200 text-sm leading-relaxed">
                        {displayAi.citizen_claim}
                      </p>
                    </div>
                  )}

                  {displayAi.formal_summary && (
                    <div>
                      <span className="font-semibold text-slate-800 block mb-1 text-xs sm:text-sm">Summary:</span>
                      <p className="text-slate-900 bg-white p-3 rounded-lg border border-slate-200 font-medium text-sm leading-relaxed">
                        {displayAi.formal_summary}
                      </p>
                    </div>
                  )}

                  {displayAi.warnings && displayAi.warnings.length > 0 && (
                    <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-950 font-medium">
                      <span className="font-bold block mb-1 text-xs sm:text-sm text-amber-950">Observations:</span>
                      <ul className="list-disc list-inside space-y-0.5 text-xs leading-relaxed text-amber-900">
                        {displayAi.warnings.map((w, idx) => (
                          <li key={idx}>{w}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <p className="text-xs text-slate-500 italic font-medium">
                    This summary helps organize your report for municipal review.
                  </p>
                </div>
              ) : (
                <div className="py-3 px-4 bg-amber-50 border border-amber-200 rounded-lg text-amber-950 text-xs sm:text-sm">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="font-bold text-amber-950 text-sm">Could not prepare report details.</p>
                      <p className="text-amber-900 mt-0.5 text-xs sm:text-sm leading-normal">
                        {aiError || 'Please try preparing the report details again before submission.'}
                      </p>
                    </div>
                    {!isLocked && (
                      <button
                        type="button"
                        onClick={handleRetryAI}
                        disabled={retryingAI}
                        className="px-3.5 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded-md font-semibold text-xs sm:text-sm transition inline-flex items-center gap-1.5 shadow-xs whitespace-nowrap"
                      >
                        <RefreshCw className={`w-3.5 h-3.5 ${retryingAI ? 'animate-spin' : ''}`} aria-hidden="true" />
                        <span>{retryingAI ? 'Preparing...' : 'Retry Details'}</span>
                      </button>
                    )}
                  </div>
                </div>
              )}
            </section>
          );
        })()}

        {/* Layer 3: Location Verification & Map */}
        {(locationData || complaint.latitude) && (
          <section aria-labelledby="location-heading">
            <h4 id="location-heading" className="sr-only">Location & Map</h4>
            <InteractiveMap
              latitude={locationData?.latitude ?? complaint.latitude}
              longitude={locationData?.longitude ?? complaint.longitude}
              mapUrl={locationData?.map_url ?? complaint.map_url}
              status={locationData?.location_status ?? complaint.location_status}
              distanceMeters={locationData?.distance_meters}
              message={locationData?.message}
              geocodedAddress={locationData?.geocoded_address ?? complaint.final_address ?? complaint.original_address}
              reverseAddress={locationData?.reverse_geocoded_address}
            />
          </section>
        )}

        {/* Layer 4: Final Citizen Report (Editable by Citizen) */}
        <section aria-labelledby="layer4-heading" className="border-2 border-blue-200 rounded-xl p-4 sm:p-5 bg-white shadow-xs">
          <div className="flex flex-wrap items-center justify-between gap-2 mb-4 pb-3 border-b border-slate-100">
            <div>
              <div className="flex items-center gap-2">
                <UserCheck className="w-4 h-4 text-blue-600" aria-hidden="true" />
                <h4 id="layer4-heading" className="text-base font-bold text-slate-900">
                  {isLocked 
                    ? '3. Your Report (Submitted)' 
                    : '3. Review & Edit Your Report'}
                </h4>
              </div>
              <p className="text-xs sm:text-sm text-slate-600 mt-1 leading-normal">
                {isLocked
                  ? 'Your report has been submitted and is locked for review.'
                  : 'Review and make any edits needed so your report accurately reflects the issue.'}
              </p>
            </div>

            {!isLocked && (
              <button
                type="button"
                onClick={handleReset}
                className="text-xs sm:text-sm text-slate-600 hover:text-slate-900 flex items-center gap-1.5 font-medium transition"
              >
                <RotateCcw className="w-3.5 h-3.5" aria-hidden="true" />
                <span>Reset to Prepared Draft</span>
              </button>
            )}
          </div>

          <form onSubmit={handleSaveDraft} className="space-y-4">
            <div>
              <label htmlFor="final-problem-input" className="block text-sm font-semibold text-slate-800 mb-1.5">
                Problem Description <span className="text-rose-500">*</span>
              </label>
              <textarea
                id="final-problem-input"
                rows={3}
                required
                disabled={isLocked}
                value={finalProblem}
                onChange={(e) => setFinalProblem(e.target.value)}
                placeholder="Review and confirm the exact problem description..."
                className="w-full px-3.5 py-2.5 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white disabled:bg-slate-100 disabled:text-slate-700 font-medium placeholder:text-slate-400"
              />
            </div>

            <div>
              <label htmlFor="final-address-input" className="block text-sm font-semibold text-slate-800 mb-1.5">
                Incident Address
              </label>
              <input
                id="final-address-input"
                type="text"
                disabled={isLocked}
                value={finalAddress}
                onChange={(e) => setFinalAddress(e.target.value)}
                placeholder="e.g. 5th Main Road near Community Center"
                className="w-full px-3.5 py-2.5 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white disabled:bg-slate-100 disabled:text-slate-700 placeholder:text-slate-400"
              />
            </div>

            <div>
              <label htmlFor="final-summary-input" className="block text-sm font-semibold text-slate-800 mb-1.5">
                Summary
              </label>
              <textarea
                id="final-summary-input"
                rows={2}
                disabled={isLocked}
                value={finalSummary}
                onChange={(e) => setFinalSummary(e.target.value)}
                placeholder="Summary of the issue..."
                className="w-full px-3.5 py-2.5 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white disabled:bg-slate-100 disabled:text-slate-700 placeholder:text-slate-400"
              />
            </div>

            {isLocked ? (
              <div className="pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2 text-xs sm:text-sm text-slate-600">
                <div className="flex items-center gap-1.5 font-medium text-slate-700">
                  <Lock className="w-4 h-4 text-slate-400" aria-hidden="true" />
                  <span>
                    {isTerminal
                      ? 'Case file is finalized and archived.'
                      : 'Submitted — Locked during review.'}
                  </span>
                </div>
                <span className="font-bold text-slate-800 bg-slate-100 px-2.5 py-1 rounded text-xs border border-slate-200">
                  Status: {currentStatus}
                </span>
              </div>
            ) : (
              <div className="pt-3 flex flex-col-reverse sm:flex-row items-stretch sm:items-center justify-between gap-3 border-t border-slate-100">
                <button
                  type="submit"
                  disabled={saving}
                  className="w-full sm:w-auto px-4 py-2.5 sm:py-2 bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 rounded-lg text-sm font-semibold transition inline-flex items-center justify-center gap-1.5 shadow-xs"
                >
                  {saving ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                  <span>Save Changes</span>
                </button>

                <button
                  type="button"
                  onClick={handleSubmitComplaint}
                  disabled={submittingFinal}
                  className="w-full sm:w-auto px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-bold transition shadow-sm inline-flex items-center justify-center gap-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                >
                  {submittingFinal ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" aria-hidden="true" />
                      <span>Submitting Report...</span>
                    </>
                  ) : (
                    <>
                      <Send className="w-4 h-4" aria-hidden="true" />
                      <span>Submit Report</span>
                    </>
                  )}
                </button>
              </div>
            )}
          </form>
        </section>
      </div>
      {/* Delete Confirmation Modal */}
      {showDeleteModal && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs"
          role="dialog"
          aria-modal="true"
          aria-labelledby="delete-modal-title"
        >
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6 border border-slate-200">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-rose-100 flex items-center justify-center text-rose-600 shrink-0">
                <Trash2 className="w-5 h-5" aria-hidden="true" />
              </div>
              <div>
                <h4 id="delete-modal-title" className="text-lg font-bold text-slate-900">
                  Delete this report?
                </h4>
                <p className="text-xs sm:text-sm text-slate-600">
                  Report ID: <span className="font-mono font-medium">{complaint.id.slice(0, 8)}…</span>
                </p>
              </div>
            </div>

            <p className="text-sm text-slate-600 mb-6 leading-relaxed">
              This will permanently remove the report. This action cannot be undone.
            </p>

            {deleteError && (
              <div className="mb-4">
                <Alert variant="error" onClose={() => setDeleteError(null)}>
                  {deleteError}
                </Alert>
              </div>
            )}

            <div className="flex items-center justify-end gap-3">
              <button
                type="button"
                disabled={deleting}
                onClick={() => {
                  setShowDeleteModal(false);
                  setDeleteError(null);
                }}
                className="px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100 rounded-lg transition"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={deleting}
                onClick={handleDeleteComplaint}
                className="px-4 py-2 text-sm font-bold text-white bg-rose-600 hover:bg-rose-700 rounded-lg transition shadow-xs inline-flex items-center gap-1.5 focus:outline-none focus:ring-2 focus:ring-rose-500"
              >
                {deleting ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" aria-hidden="true" />
                    <span>Deleting Report...</span>
                  </>
                ) : (
                  <>
                    <Trash2 className="w-3.5 h-3.5" aria-hidden="true" />
                    <span>Delete Report</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
