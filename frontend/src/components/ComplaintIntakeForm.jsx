import React, { useState, useEffect } from 'react';
import { 
  Camera, 
  MapPin, 
  AlertCircle, 
  CheckCircle, 
  FileText, 
  Upload, 
  RefreshCw, 
  User, 
  Lock, 
  Edit3, 
  Eye, 
  X,
  HelpCircle,
  Cpu,
  Navigation,
  Shield,
  ArrowRight,
  Plus,
  ArrowLeft,
  Trash2
} from 'lucide-react';
import { getStoredToken, loginUser, registerUser, fetchCurrentUser, clearStoredToken } from '../services/auth';
import { 
  createComplaintDraft, 
  fetchMyComplaints, 
  fetchComplaintById, 
  analyzeComplaintWithAI, 
  verifyComplaintLocation, 
  deleteComplaintById 
} from '../services/complaints';
import InteractiveMap from './InteractiveMap';
import ComplaintReviewCard from './ComplaintReviewCard';
import StatusBadge from './ui/StatusBadge';
import Alert from './ui/Alert';
import EmptyState from './ui/EmptyState';
import LoadingState from './ui/LoadingState';
import { API_BASE_URL } from '../services/api';

export default function ComplaintIntakeForm({ onUserChange, selectedComplaintId, onNavigateAdmin }) {
  const [currentUser, setCurrentUser] = useState(null);
  const [loadingAuth, setLoadingAuth] = useState(true);
  const [authError, setAuthError] = useState(null);

  // Authentication mode for unauthenticated visitors
  const [authMode, setAuthMode] = useState('login'); // 'login' or 'register'
  const [authForm, setAuthForm] = useState({ name: '', email: '', password: '' });
  const [authSubmitting, setAuthSubmitting] = useState(false);

  // Complaint intake form state
  const [problem, setProblem] = useState('');
  const [address, setAddress] = useState('');
  const [latitude, setLatitude] = useState('');
  const [longitude, setLongitude] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [filePreview, setFilePreview] = useState(null);

  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  // Active Human Review Complaint (Phase 7)
  const [activeReviewComplaint, setActiveReviewComplaint] = useState(null);

  // List of citizen complaints
  const [complaintsList, setComplaintsList] = useState([]);
  const [loadingList, setLoadingList] = useState(false);

  // Delete confirmation state
  const [complaintToDelete, setComplaintToDelete] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [deleteError, setDeleteError] = useState(null);
  const [deleteSuccessMessage, setDeleteSuccessMessage] = useState(null);

  useEffect(() => {
    loadUser();
  }, []);

  useEffect(() => {
    if (selectedComplaintId) {
      fetchComplaintById(selectedComplaintId)
        .then(fresh => {
          if (fresh) {
            setActiveReviewComplaint(fresh);
            window.scrollTo({ top: 0, behavior: 'smooth' });
          }
        })
        .catch(() => {});
    } else {
      setActiveReviewComplaint(null);
    }
  }, [selectedComplaintId]);


  async function loadUser() {
    setLoadingAuth(true);
    setAuthError(null);
    try {
      const user = await fetchCurrentUser();
      setCurrentUser(user);
      if (onUserChange) {
        onUserChange(user);
      }
      if (user) {
        loadComplaints();
      }
    } catch (err) {
      setAuthError(err.message);
    } finally {
      setLoadingAuth(false);
    }
  }

  async function loadComplaints() {
    setLoadingList(true);
    try {
      const list = await fetchMyComplaints();
      setComplaintsList(list);
    } catch {
      // Ignored
    } finally {
      setLoadingList(false);
    }
  }

  async function handleAuthSubmit(e) {
    e.preventDefault();
    setAuthSubmitting(true);
    setAuthError(null);
    try {
      if (authMode === 'login') {
        await loginUser({ email: authForm.email, password: authForm.password });
      } else {
        await registerUser({ name: authForm.name, email: authForm.email, password: authForm.password });
      }
      await loadUser();
    } catch (err) {
      setAuthError(err.message || 'Authentication failed. Please verify your credentials.');
    } finally {
      setAuthSubmitting(false);
    }
  }

  function handleLogout() {
    clearStoredToken();
    setCurrentUser(null);
    if (onUserChange) {
      onUserChange(null);
    }
    setComplaintsList([]);
    setIntakeResult(null);
    setActiveReviewComplaint(null);
  }

  function handleDraftUpdated(updated) {
    setActiveReviewComplaint(updated);
    setComplaintsList(prev => prev.map(c => c.id === updated.id ? updated : c));
  }

  async function handleOpenReview(complaintItem) {
    try {
      const fresh = await fetchComplaintById(complaintItem.id);
      setActiveReviewComplaint(fresh);
    } catch {
      setActiveReviewComplaint(complaintItem);
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function handleComplaintDeleted(deletedId) {
    if (activeReviewComplaint && activeReviewComplaint.id === deletedId) {
      setActiveReviewComplaint(null);
    }
    setComplaintsList(prev => prev.filter(c => c.id !== deletedId));
    setDeleteSuccessMessage('Complaint deleted successfully.');
    setTimeout(() => setDeleteSuccessMessage(null), 5000);
  }

  async function handleConfirmDelete() {
    if (!complaintToDelete || deletingId) return;
    setDeletingId(complaintToDelete.id);
    setDeleteError(null);
    try {
      await deleteComplaintById(complaintToDelete.id);
      handleComplaintDeleted(complaintToDelete.id);
      setComplaintToDelete(null);
    } catch (err) {
      setDeleteError(err.message || 'Failed to delete complaint.');
    } finally {
      setDeletingId(null);
    }
  }

  function handleFileChange(e) {
    const file = e.target.files[0];
    if (file) {
      if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
        setErrorMessage('Unsupported file format. Please upload a JPEG, PNG, or WebP photo.');
        return;
      }
      if (file.size > 10 * 1024 * 1024) {
        setErrorMessage('File size exceeds the 10 MB limit. Please select a smaller photo.');
        return;
      }
      setSelectedFile(file);
      setFilePreview(URL.createObjectURL(file));
      setErrorMessage(null);
    }
  }

  function handleRemoveFile() {
    setSelectedFile(null);
    if (filePreview) {
      URL.revokeObjectURL(filePreview);
      setFilePreview(null);
    }
  }

  function handleGetLocation() {
    if ('geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setLatitude(pos.coords.latitude.toFixed(6));
          setLongitude(pos.coords.longitude.toFixed(6));
          setErrorMessage(null);
        },
        (err) => {
          setErrorMessage(`Device location could not be captured: ${err.message}. You can manually enter coordinates or proceed with an address.`);
        },
        { enableHighAccuracy: true, timeout: 10000 }
      );
    } else {
      setErrorMessage('Geolocation is not supported by your browser.');
    }
  }

  async function handleSubmit(e) {
    if (e && e.preventDefault) e.preventDefault();
    // Section 11: Strict duplicate request protection - ignore any click if already submitting
    if (submitting) return;

    if (!selectedFile) {
      setErrorMessage('Please select an evidence photo to upload.');
      return;
    }
    if (!problem.trim() || problem.trim().length < 5) {
      setErrorMessage('Please describe the observed civic issue (minimum 5 characters).');
      return;
    }

    setSubmitting(true);
    setErrorMessage(null);

    const t1_submit = performance.now();

    try {
      // Exactly ONE POST /api/v1/complaints/analyze per click
      const result = await createComplaintDraft({
        imageFile: selectedFile,
        problem: problem.trim(),
        address: address.trim(),
        latitude,
        longitude,
      });

      // Clear intake form fields
      setProblem('');
      setAddress('');
      setLatitude('');
      setLongitude('');
      handleRemoveFile();

      // Run AI Analysis and Location Verification concurrently for optimal latency
      await Promise.allSettled([
        analyzeComplaintWithAI(result.id),
        verifyComplaintLocation(result.id)
      ]);

      // Authoritative synchronization: fetch updated complaint from DB
      const freshComplaint = await fetchComplaintById(result.id);
      const t8_rendered = performance.now();
      console.log('[CivicFlow Latency Forensic]', {
        T1_submit_ms: t1_submit,
        T8_rendered_ms: t8_rendered,
        total_e2e_ms: Math.round(t8_rendered - t1_submit)
      });

      setActiveReviewComplaint(freshComplaint || result);
      window.scrollTo({ top: 0, behavior: 'smooth' });

      // Refresh citizen complaints list in the background
      fetchMyComplaints().then(list => setComplaintsList(list)).catch(() => {});
    } catch (err) {
      setErrorMessage(err.message || 'Failed to submit complaint intake.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden mb-10">
      {/* Intake Card Header */}
      <div className="px-6 py-4 bg-slate-50 border-b border-slate-200 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-slate-900 flex items-center gap-2">
            <Camera className="w-5 h-5 text-blue-600" aria-hidden="true" />
            <span>Citizen Complaint Intake</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Capture authentic photo evidence and record problem details. Saved strictly as a <strong>DRAFT</strong>.
          </p>
        </div>

        {currentUser && (
          <div className="flex items-center gap-3">
            <span className="text-xs bg-blue-50 text-blue-800 px-3 py-1 rounded-full font-medium border border-blue-200 flex items-center gap-1.5">
              <User className="w-3.5 h-3.5" aria-hidden="true" />
              <span>{currentUser.name}</span>
            </span>
            <button
              type="button"
              onClick={handleLogout}
              className="text-xs text-slate-500 hover:text-rose-600 font-medium transition"
            >
              Sign out
            </button>
          </div>
        )}
      </div>

      <div className="p-6">
        {loadingAuth ? (
          <LoadingState message="Verifying citizen session..." />
        ) : !currentUser ? (
          /* Unauthenticated Citizen Authentication Section */
          <div className="max-w-md mx-auto py-6">
            <div className="text-center mb-6">
              <div className="w-12 h-12 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center mx-auto mb-3 border border-blue-200 shadow-xs">
                <Lock className="w-6 h-6" aria-hidden="true" />
              </div>
              <h3 className="text-base font-bold text-slate-900">
                Citizen Sign In Required
              </h3>
              <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                Sign in with your citizen account to report municipal issues, inspect AI-assisted drafts, and track official decisions.
              </p>
            </div>

            {authError && (
              <Alert variant="error" className="mb-4">
                {authError}
              </Alert>
            )}

            <form onSubmit={handleAuthSubmit} className="space-y-4">
              {authMode === 'register' && (
                <div>
                  <label htmlFor="auth-name" className="block text-xs font-semibold text-slate-700 mb-1">
                    Full Name <span className="text-rose-500">*</span>
                  </label>
                  <input
                    id="auth-name"
                    type="text"
                    required
                    value={authForm.name}
                    onChange={(e) => setAuthForm({ ...authForm, name: e.target.value })}
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="e.g. Jane Doe"
                  />
                </div>
              )}

              <div>
                <label htmlFor="auth-email" className="block text-xs font-semibold text-slate-700 mb-1">
                  Email Address <span className="text-rose-500">*</span>
                </label>
                <input
                  id="auth-email"
                  type="email"
                  required
                  value={authForm.email}
                  onChange={(e) => setAuthForm({ ...authForm, email: e.target.value })}
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="citizen@example.com"
                />
              </div>

              <div>
                <label htmlFor="auth-password" className="block text-xs font-semibold text-slate-700 mb-1">
                  Password <span className="text-rose-500">*</span>
                </label>
                <input
                  id="auth-password"
                  type="password"
                  required
                  value={authForm.password}
                  onChange={(e) => setAuthForm({ ...authForm, password: e.target.value })}
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="••••••••"
                />
              </div>

              <button
                type="submit"
                disabled={authSubmitting}
                className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold transition flex items-center justify-center gap-2 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
              >
                {authSubmitting && <RefreshCw className="w-4 h-4 animate-spin" aria-hidden="true" />}
                <span>{authMode === 'login' ? 'Sign In to Report Issue' : 'Register Citizen Account'}</span>
              </button>
            </form>

            <div className="text-center mt-4">
              <button
                type="button"
                onClick={() => {
                  setAuthMode(authMode === 'login' ? 'register' : 'login');
                  setAuthError(null);
                }}
                className="text-xs text-blue-600 hover:text-blue-800 hover:underline font-medium"
              >
                {authMode === 'login'
                  ? "New citizen? Create an account to report issues"
                  : 'Already registered? Sign in'}
              </button>
            </div>

            {onNavigateAdmin && (
              <div className="text-center mt-4 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={onNavigateAdmin}
                  className="text-xs text-slate-500 hover:text-slate-800 hover:underline inline-flex items-center gap-1 font-medium"
                >
                  <Lock className="w-3 h-3 text-slate-400" aria-hidden="true" />
                  <span>Administrator? Go to Admin Portal</span>
                </button>
              </div>
            )}
          </div>
        ) : (
          /* Authenticated Citizen Experience */
          <div>
            {activeReviewComplaint ? (
              <div className="space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-100 p-3.5 rounded-xl border border-slate-200">
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-blue-600" />
                    <span className="text-xs font-semibold text-slate-800">
                      Currently Reviewing Case #{activeReviewComplaint.id.slice(0, 8)}…
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setActiveReviewComplaint(null);
                      setIntakeResult(null);
                      setProblem('');
                      setAddress('');
                      setLatitude('');
                      setLongitude('');
                      handleRemoveFile();
                    }}
                    className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold transition shadow-xs inline-flex items-center gap-1.5"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>+ Report Another Issue</span>
                  </button>
                </div>

                <ComplaintReviewCard
                  complaint={activeReviewComplaint}
                  onDraftUpdated={handleDraftUpdated}
                  onClose={() => setActiveReviewComplaint(null)}
                  onComplaintDeleted={handleComplaintDeleted}
                />
              </div>
            ) : (
              <div>
                {deleteSuccessMessage && (
                  <div className="mb-4">
                    <Alert variant="success" onClose={() => setDeleteSuccessMessage(null)}>
                      {deleteSuccessMessage}
                    </Alert>
                  </div>
                )}

                {errorMessage && (
                  <Alert variant="error" className="mb-6" onClose={() => setErrorMessage(null)}>
                    {errorMessage}
                  </Alert>
                )}

            {/* Primary Intake Form */}
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Step 1: Upload Evidence Photo */}
              <fieldset className="border border-slate-200 rounded-xl p-4 sm:p-5 bg-slate-50/50">
                <legend className="text-xs font-bold uppercase tracking-wider text-slate-700 px-2 flex items-center gap-1.5">
                  <span className="w-5 h-5 rounded-full bg-blue-600 text-white flex items-center justify-center text-[10px] font-bold">1</span>
                  <span>Evidence Photo</span>
                  <span className="text-rose-500 font-bold">*</span>
                </legend>
                <p className="text-xs text-slate-500 mb-3">
                  Upload authentic photo evidence showing the observed civic issue (JPEG, PNG, WebP up to 10 MB).
                </p>

                <div className="flex flex-wrap items-center gap-4">
                  <label
                    htmlFor="evidence-photo-input"
                    className="cursor-pointer inline-flex items-center gap-2 px-4 py-2.5 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-xs font-semibold text-slate-700 shadow-xs transition focus-within:ring-2 focus-within:ring-blue-500"
                  >
                    <Upload className="w-4 h-4 text-blue-600" aria-hidden="true" />
                    <span>Select Photo</span>
                    <input
                      id="evidence-photo-input"
                      type="file"
                      accept="image/jpeg,image/png,image/webp"
                      onChange={handleFileChange}
                      className="sr-only"
                    />
                  </label>

                  {selectedFile && (
                    <div className="flex items-center gap-2 bg-white px-3 py-1.5 rounded-lg border border-slate-200 text-xs text-slate-700 shadow-xs">
                      <span className="truncate max-w-xs font-medium">{selectedFile.name}</span>
                      <span className="text-slate-400">({(selectedFile.size / 1024).toFixed(0)} KB)</span>
                      <button
                        type="button"
                        onClick={handleRemoveFile}
                        aria-label="Remove selected photo"
                        className="p-1 text-slate-400 hover:text-rose-600 rounded transition"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  )}
                </div>

                {filePreview && (
                  <div className="mt-3 max-w-xs rounded-lg overflow-hidden border border-slate-200 shadow-xs relative">
                    <img
                      src={filePreview}
                      alt="Uploaded incident evidence preview"
                      className="w-full h-40 object-cover"
                    />
                    <div className="absolute bottom-1 right-1 bg-slate-900/80 text-white text-[10px] px-1.5 py-0.5 rounded font-mono">
                      Preview
                    </div>
                  </div>
                )}
              </fieldset>

              {/* Step 2: Problem Description */}
              <fieldset className="border border-slate-200 rounded-xl p-4 sm:p-5 bg-slate-50/50">
                <legend className="text-xs font-bold uppercase tracking-wider text-slate-700 px-2 flex items-center gap-1.5">
                  <span className="w-5 h-5 rounded-full bg-blue-600 text-white flex items-center justify-center text-[10px] font-bold">2</span>
                  <span>Problem Description</span>
                  <span className="text-rose-500 font-bold">*</span>
                </legend>
                <label htmlFor="problem-input" className="block text-xs font-medium text-slate-700 mb-1">
                  What is the problem?
                </label>
                <textarea
                  id="problem-input"
                  rows={3}
                  required
                  value={problem}
                  onChange={(e) => setProblem(e.target.value)}
                  placeholder="Example: Deep pothole near the main intersection causing vehicular hazard and water pooling..."
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                />
                <div className="flex justify-between text-[11px] text-slate-400 mt-1">
                  <span>Minimum 5 characters. Be descriptive and objective.</span>
                  <span>{problem.length} / 1000</span>
                </div>
              </fieldset>

              {/* Step 3: Location Information */}
              <fieldset className="border border-slate-200 rounded-xl p-4 sm:p-5 bg-slate-50/50 space-y-4">
                <legend className="text-xs font-bold uppercase tracking-wider text-slate-700 px-2 flex items-center gap-1.5">
                  <span className="w-5 h-5 rounded-full bg-blue-600 text-white flex items-center justify-center text-[10px] font-bold">3</span>
                  <span>Location Evidence</span>
                </legend>

                {/* Entered Address */}
                <div>
                  <label htmlFor="address-input" className="block text-xs font-semibold text-slate-700 mb-1">
                    Incident Address <span className="text-slate-400 font-normal">(Optional address hint)</span>
                  </label>
                  <input
                    id="address-input"
                    type="text"
                    value={address}
                    onChange={(e) => setAddress(e.target.value)}
                    placeholder="e.g. Near Community Health Center, 5th Main Road"
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                  />
                  <p className="text-[11px] text-slate-500 mt-1">
                    The street address or landmark where the incident occurred.
                  </p>
                </div>

                {/* Device Coordinates */}
                <div>
                  <div className="flex flex-wrap items-center justify-between gap-2 mb-1.5">
                    <label className="text-xs font-semibold text-slate-700">
                      Device Location <span className="text-slate-400 font-normal">(Supporting GPS coordinates)</span>
                    </label>
                    <button
                      type="button"
                      onClick={handleGetLocation}
                      className="text-xs text-blue-600 hover:text-blue-800 inline-flex items-center gap-1 font-medium transition"
                    >
                      <Navigation className="w-3.5 h-3.5" aria-hidden="true" />
                      <span>Attach Device GPS</span>
                    </button>
                  </div>

                  <p className="text-[11px] text-slate-500 mb-2 leading-relaxed">
                    Your device location is used as supporting location evidence. It is not treated as proof that the photo was taken there.
                  </p>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label htmlFor="latitude-input" className="sr-only">Latitude</label>
                      <input
                        id="latitude-input"
                        type="number"
                        step="any"
                        value={latitude}
                        onChange={(e) => setLatitude(e.target.value)}
                        placeholder="Latitude (e.g. 12.9716)"
                        className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white font-mono"
                      />
                    </div>
                    <div>
                      <label htmlFor="longitude-input" className="sr-only">Longitude</label>
                      <input
                        id="longitude-input"
                        type="number"
                        step="any"
                        value={longitude}
                        onChange={(e) => setLongitude(e.target.value)}
                        placeholder="Longitude (e.g. 77.5946)"
                        className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white font-mono"
                      />
                    </div>
                  </div>
                </div>
              </fieldset>

              {/* Submit Button */}
              <div className="pt-2">
                <button
                  type="submit"
                  disabled={submitting}
                  className="w-full sm:w-auto px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold transition shadow-sm flex items-center justify-center gap-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                >
                  {submitting ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" aria-hidden="true" />
                      <span>Creating Draft & Preparing AI Analysis...</span>
                    </>
                  ) : (
                    <>
                      <span>Create Complaint Draft & Review</span>
                      <ArrowRight className="w-4 h-4" aria-hidden="true" />
                    </>
                  )}
                </button>
              </div>
            </form>

            {/* Citizen's Existing Complaints Section */}
            <div className="mt-12 pt-8 border-t border-slate-200">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-600">
                  Your Submitted Complaints & Drafts ({complaintsList.length})
                </h3>
                <button
                  type="button"
                  onClick={loadComplaints}
                  disabled={loadingList}
                  className="text-xs text-blue-600 hover:text-blue-800 inline-flex items-center gap-1 font-medium"
                >
                  <RefreshCw className={`w-3 h-3 ${loadingList ? 'animate-spin' : ''}`} />
                  <span>Refresh</span>
                </button>
              </div>

              {loadingList && complaintsList.length === 0 ? (
                <LoadingState message="Loading your complaints..." />
              ) : complaintsList.length === 0 ? (
                <EmptyState
                  title="You haven't submitted any complaints yet."
                  description="When you create a complaint draft and submit it, your case history will appear here."
                />
              ) : (
                <div className="space-y-3">
                  {complaintsList.map((c) => (
                    <div
                      key={c.id}
                      className="p-4 bg-slate-50/70 hover:bg-slate-50 border border-slate-200 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-4 text-xs transition shadow-xs"
                    >
                      <div className="flex items-start gap-3 truncate">
                        {c.image_url && (
                          <img
                            src={`${API_BASE_URL}${c.image_url}`}
                            alt="Incident evidence thumbnail"
                            className="w-12 h-12 object-cover rounded-lg border border-slate-200 shrink-0"
                            onError={(e) => { e.target.style.display = 'none'; }}
                          />
                        )}
                        <div className="truncate">
                          <div className="font-semibold text-slate-900 truncate text-sm">
                            {c.final_problem || c.original_problem}
                          </div>
                          <div className="text-slate-500 text-xs truncate flex flex-wrap items-center gap-2 mt-1">
                            <span>{c.final_address || c.original_address || 'No address specified'}</span>
                            {c.location_status && (
                              <StatusBadge status={c.location_status} size="xs" />
                            )}
                            {c.map_url && (
                              <a
                                href={c.map_url}
                                target="_blank"
                                rel="noreferrer"
                                className="text-blue-600 hover:underline text-[11px]"
                              >
                                View Map &rarr;
                              </a>
                            )}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center justify-between sm:justify-end gap-3 shrink-0 pt-2 sm:pt-0 border-t sm:border-t-0 border-slate-200">
                        <StatusBadge status={c.status} />

                        <button
                          type="button"
                          onClick={() => handleOpenReview(c)}
                          className="px-3 py-1.5 text-xs text-blue-700 bg-white hover:bg-blue-50 border border-blue-300 rounded-lg font-semibold flex items-center gap-1.5 transition shadow-xs"
                        >
                          {['SUBMITTED', 'ACCEPTED', 'REJECTED'].includes(c.status) ? (
                            <>
                              <Eye className="w-3.5 h-3.5" aria-hidden="true" />
                              <span>View Case</span>
                            </>
                          ) : (
                            <>
                              <Edit3 className="w-3.5 h-3.5" aria-hidden="true" />
                              <span>Review & Edit</span>
                            </>
                          )}
                        </button>

                        <button
                          type="button"
                          onClick={() => {
                            setComplaintToDelete(c);
                            setDeleteError(null);
                          }}
                          className="px-2.5 py-1.5 text-xs text-rose-700 bg-white hover:bg-rose-50 border border-rose-300 rounded-lg font-semibold flex items-center gap-1 transition shadow-xs"
                          title="Delete this complaint"
                        >
                          <Trash2 className="w-3.5 h-3.5" aria-hidden="true" />
                          <span className="sr-only sm:not-sr-only">Delete</span>
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Delete Confirmation Modal for List Items */}
            {complaintToDelete && (
              <div 
                className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs"
                role="dialog"
                aria-modal="true"
                aria-labelledby="intake-delete-modal-title"
              >
                <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6 border border-slate-200">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 rounded-full bg-rose-100 flex items-center justify-center text-rose-600 shrink-0">
                      <Trash2 className="w-5 h-5" aria-hidden="true" />
                    </div>
                    <div>
                      <h4 id="intake-delete-modal-title" className="text-base font-bold text-slate-900">
                        Delete this complaint?
                      </h4>
                      <p className="text-xs text-slate-500">
                        Complaint ID: <span className="font-mono">{complaintToDelete.id.slice(0, 8)}…</span>
                      </p>
                    </div>
                  </div>

                  <p className="text-xs text-slate-600 mb-6 leading-relaxed">
                    This will permanently remove the complaint and its associated data. This action cannot be undone.
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
                      disabled={deletingId !== null}
                      onClick={() => {
                        setComplaintToDelete(null);
                        setDeleteError(null);
                      }}
                      className="px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100 rounded-lg transition"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      disabled={deletingId !== null}
                      onClick={handleConfirmDelete}
                      className="px-4 py-2 text-xs font-bold text-white bg-rose-600 hover:bg-rose-700 rounded-lg transition shadow-xs inline-flex items-center gap-1.5 focus:outline-none focus:ring-2 focus:ring-rose-500"
                    >
                      {deletingId !== null ? (
                        <>
                          <RefreshCw className="w-3.5 h-3.5 animate-spin" aria-hidden="true" />
                          <span>Deleting Complaint...</span>
                        </>
                      ) : (
                        <>
                          <Trash2 className="w-3.5 h-3.5" aria-hidden="true" />
                          <span>Delete Complaint</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
