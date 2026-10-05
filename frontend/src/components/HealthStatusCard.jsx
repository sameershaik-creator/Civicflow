import React, { useState, useEffect } from 'react';
import { checkBackendHealth, checkDatabaseHealth, API_BASE_URL } from '../services/api';
import { CheckCircle2, XCircle, RefreshCw, Server, Database, Activity } from 'lucide-react';

export default function HealthStatusCard() {
  const [backendHealth, setBackendHealth] = useState(null);
  const [dbHealth, setDbHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastChecked, setLastChecked] = useState(null);

  const runHealthChecks = async () => {
    setLoading(true);
    const [bHealth, dHealth] = await Promise.all([
      checkBackendHealth(),
      checkDatabaseHealth(),
    ]);
    setBackendHealth(bHealth);
    setDbHealth(dHealth);
    setLastChecked(new Date().toLocaleTimeString());
    setLoading(false);
  };

  useEffect(() => {
    runHealthChecks();
  }, []);

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 max-w-2xl mx-auto">
      <div className="flex items-center justify-between border-b border-slate-100 pb-4 mb-5">
        <div className="flex items-center space-x-2.5">
          <Activity className="w-5 h-5 text-blue-600" />
          <h2 className="text-lg font-semibold text-slate-800">
            System Connectivity Status
          </h2>
        </div>
        <button
          onClick={runHealthChecks}
          disabled={loading}
          className="inline-flex items-center px-3 py-1.5 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${loading ? 'animate-spin text-blue-600' : ''}`} />
          {loading ? 'Checking...' : 'Retest'}
        </button>
      </div>

      <div className="space-y-4">
        {/* Backend API Health */}
        <div className="flex items-start justify-between p-4 rounded-lg bg-slate-50 border border-slate-150">
          <div className="flex items-start space-x-3">
            <div className="mt-0.5 p-2 bg-white rounded-md border border-slate-200 text-slate-700">
              <Server className="w-4 h-4" />
            </div>
            <div>
              <div className="text-sm font-medium text-slate-900">
                Backend API Service
              </div>
              <div className="text-xs text-slate-500 font-mono mt-0.5">
                {API_BASE_URL}/health
              </div>
              {backendHealth && (
                <div className="mt-2 text-xs">
                  {backendHealth.ok ? (
                    <span className="text-emerald-700 font-medium">
                      Response: {JSON.stringify(backendHealth.data)} ({backendHealth.elapsedMs}ms)
                    </span>
                  ) : (
                    <span className="text-rose-600 font-medium">
                      Error: {backendHealth.error}
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>

          <div>
            {loading ? (
              <span className="text-xs text-slate-400">Pinging...</span>
            ) : backendHealth?.ok ? (
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> HTTP 200 OK
              </span>
            ) : (backendHealth?.status === 502 || backendHealth?.status === 503 || backendHealth?.error?.includes('waking up')) ? (
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">
                <RefreshCw className="w-3.5 h-3.5 mr-1 animate-spin" /> Waking up (~30-50s)
              </span>
            ) : (
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-rose-50 text-rose-700 border border-rose-200">
                <XCircle className="w-3.5 h-3.5 mr-1" /> Unreachable
              </span>
            )}
          </div>
        </div>

        {/* Database Health */}
        <div className="flex items-start justify-between p-4 rounded-lg bg-slate-50 border border-slate-150">
          <div className="flex items-start space-x-3">
            <div className="mt-0.5 p-2 bg-white rounded-md border border-slate-200 text-slate-700">
              <Database className="w-4 h-4" />
            </div>
            <div>
              <div className="text-sm font-medium text-slate-900">
                Database Engine Connection
              </div>
              <div className="text-xs text-slate-500 font-mono mt-0.5">
                {API_BASE_URL}/health/db
              </div>
              {dbHealth && (
                <div className="mt-2 text-xs">
                  {dbHealth.ok && dbHealth.data?.database?.connected ? (
                    <span className="text-emerald-700 font-medium">
                      Dialect: {dbHealth.data.database.dialect} | Connected: True
                    </span>
                  ) : (
                    <span className="text-rose-600 font-medium">
                      Status: {dbHealth.data?.database?.error || dbHealth.error || 'Connection Failed'}
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>

          <div>
            {loading ? (
              <span className="text-xs text-slate-400">Checking...</span>
            ) : dbHealth?.ok && dbHealth.data?.database?.connected ? (
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> Connected
              </span>
            ) : (
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-rose-50 text-rose-700 border border-rose-200">
                <XCircle className="w-3.5 h-3.5 mr-1" /> Disconnected
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="mt-5 pt-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400">
        <span>Environment Target: Local Development</span>
        <span>Last Checked: {lastChecked || 'Not checked yet'}</span>
      </div>
    </div>
  );
}
