import React, { useState } from 'react';
import { ShieldCheck, Lock, RefreshCw, ArrowLeft, AlertCircle } from 'lucide-react';
import { loginUser, fetchCurrentUser, clearStoredToken } from '../services/auth';
import Alert from './ui/Alert';

export default function AdminLogin({ onAdminLoginSuccess, onCancel }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      await loginUser({ email: email.trim(), password });
      const user = await fetchCurrentUser();

      if (!user || user.role !== 'admin') {
        clearStoredToken();
        throw new Error('Access denied: this account does not have administrator privileges.');
      }

      if (onAdminLoginSuccess) {
        onAdminLoginSuccess(user);
      }
    } catch (err) {
      setError(err.message || 'Authentication failed. Please verify your credentials.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-md mx-auto py-8 sm:py-12 px-4">
      <div className="bg-white rounded-2xl border border-slate-200 shadow-md p-5 sm:p-8">
        <div className="text-center mb-6">
          <div className="w-12 h-12 rounded-xl bg-slate-900 text-blue-400 flex items-center justify-center mx-auto mb-3 border border-slate-800 shadow-sm">
            <ShieldCheck className="w-6 h-6" aria-hidden="true" />
          </div>
          <h2 className="text-xl font-bold text-slate-900">
            CivicFlow Admin Portal
          </h2>
          <p className="text-sm text-slate-600 mt-1.5 max-w-xs mx-auto leading-normal">
            Authorized personnel only. Sign in with administrative credentials to access the review dashboard.
          </p>
        </div>

        {error && (
          <Alert variant="error" className="mb-5" onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="admin-email" className="block text-sm font-semibold text-slate-800 mb-1.5">
              Administrator Email <span className="text-rose-500">*</span>
            </label>
            <input
              id="admin-email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="admin@municipality.gov"
              className="w-full px-3.5 py-2.5 text-sm text-slate-900 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white placeholder:text-slate-400"
            />
          </div>

          <div>
            <label htmlFor="admin-password" className="block text-sm font-semibold text-slate-800 mb-1.5">
              Password <span className="text-rose-500">*</span>
            </label>
            <input
              id="admin-password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full px-3.5 py-2.5 text-sm text-slate-900 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white placeholder:text-slate-400"
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full py-2.5 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-sm font-semibold transition flex items-center justify-center gap-2 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          >
            {submitting && <RefreshCw className="w-4 h-4 animate-spin" aria-hidden="true" />}
            <span>Admin Sign In</span>
          </button>
        </form>

        <div className="pt-6 mt-6 border-t border-slate-100 text-center">
          <button
            type="button"
            onClick={onCancel}
            className="text-sm text-slate-600 hover:text-slate-900 inline-flex items-center gap-1 font-medium transition"
          >
            <ArrowLeft className="w-3.5 h-3.5" aria-hidden="true" />
            <span>Return to Citizen Portal</span>
          </button>
        </div>
      </div>
    </div>
  );
}
