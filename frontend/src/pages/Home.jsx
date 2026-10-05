import React from 'react';
import {
  Camera,
  Cpu,
  MapPin,
  UserCheck,
  ShieldCheck,
  ArrowRight,
  Shield,
  CheckCircle2,
  FileText,
  Lock,
  Compass,
  Users
} from 'lucide-react';

export default function Home({
  currentUser,
  onNavigateReport,
  onNavigateHowItWorks,
  onNavigateAdmin
}) {
  const workflowPreview = [
    {
      num: "01",
      title: "Capture Issue",
      desc: "Upload photo & GPS",
      icon: Camera,
    },
    {
      num: "02",
      title: "Report Prepared",
      desc: "Structures report draft",
      icon: Cpu,
    },
    {
      num: "03",
      title: "Location Check",
      desc: "GIS cross-reference",
      icon: MapPin,
    },
    {
      num: "04",
      title: "Citizen Review",
      desc: "You confirm wording",
      icon: UserCheck,
    },
    {
      num: "05",
      title: "City Decides",
      desc: "Administrative decision",
      icon: ShieldCheck,
    },
  ];

  return (
    <div className="flex-1 flex flex-col">
      <main className="flex-1 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-10 w-full space-y-10 sm:space-y-12">
        {/* Hero Section */}
        <section aria-labelledby="hero-heading" className="text-center max-w-3xl mx-auto pt-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-800 border border-blue-200 mb-4 shadow-xs">
            <Shield className="w-3.5 h-3.5 text-blue-600" aria-hidden="true" />
            <span>Public Service Issue Reporting & Verification</span>
          </div>

          <h1 id="hero-heading" className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-slate-900 leading-tight">
            Report Civic issues. Make your community better..
          </h1>

          <p className="mt-4 text-sm sm:text-base text-slate-600 leading-relaxed max-w-2xl mx-auto">
            CivicFlow helps citizens report local issues quickly and accurately with guided drafting, location checks, and human review at every step.
          </p>

          <div className="mt-8 flex flex-col sm:flex-row items-stretch sm:items-center justify-center gap-3 max-w-md sm:max-w-none mx-auto">
            <button
              type="button"
              onClick={onNavigateReport}
              className="w-full sm:w-auto px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs sm:text-sm font-semibold transition shadow-sm inline-flex items-center justify-center gap-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            >
              <span>Report an Issue</span>
              <ArrowRight className="w-4 h-4" aria-hidden="true" />
            </button>
            <button
              type="button"
              onClick={onNavigateHowItWorks}
              className="w-full sm:w-auto px-5 py-3 bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 rounded-lg text-xs sm:text-sm font-semibold transition shadow-xs focus:outline-none focus:ring-2 focus:ring-slate-400 text-center"
            >
              How CivicFlow Works
            </button>
          </div>
        </section>

        {/* What CivicFlow Does - 3 Core Pillars */}
        <section aria-labelledby="pillars-heading" className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-4">
          <h2 id="pillars-heading" className="sr-only">Core Principles</h2>

          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs">
            <div className="w-10 h-10 rounded-lg bg-blue-50 border border-blue-200 text-blue-600 flex items-center justify-center mb-4">
              <Camera className="w-5 h-5" />
            </div>
            <h3 className="text-base font-bold text-slate-900 mb-2">
              Photo & Location Evidence
            </h3>
            <p className="text-xs sm:text-sm text-slate-600 leading-relaxed font-normal">
              Every report is grounded in a real photo and verified location from the community.
            </p>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs">
            <div className="w-10 h-10 rounded-lg bg-indigo-50 border border-indigo-200 text-indigo-600 flex items-center justify-center mb-4">
              <Cpu className="w-5 h-5" />
            </div>
            <h3 className="text-base font-bold text-slate-900 mb-2">
              Smart Report Drafting
            </h3>
            <p className="text-xs sm:text-sm text-slate-600 leading-relaxed font-normal">
              Organizes photos and descriptions into clear issue categories, summaries, and priority levels for municipal review.
            </p>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs">
            <div className="w-10 h-10 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-600 flex items-center justify-center mb-4">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <h3 className="text-base font-bold text-slate-900 mb-2">
              Citizen & Administrative Review
            </h3>
            <p className="text-xs sm:text-sm text-slate-600 leading-relaxed font-normal">
              You review and confirm your report before submission. Municipal staff review the details to take action.
            </p>
          </div>
        </section>

        {/* How CivicFlow Works - Compact Product Preview */}
        <section aria-labelledby="workflow-preview-heading" className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 sm:p-8">
          <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
            <div>
              <div className="flex items-center gap-2 text-blue-600 mb-1">
                <Compass className="w-4 h-4" />
                <span className="text-xs font-semibold uppercase tracking-wider">Five-Stage Process</span>
              </div>
              <h2 id="workflow-preview-heading" className="text-lg font-bold text-slate-900">
                How CivicFlow Works
              </h2>
            </div>
            <button
              type="button"
              onClick={onNavigateHowItWorks}
              className="text-xs sm:text-sm font-semibold text-blue-700 hover:text-blue-900 inline-flex items-center gap-1"
            >
              <span>Explore Detailed Workflow</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
            {workflowPreview.map((w) => {
              const Icon = w.icon;
              return (
                <div key={w.num} className="p-3.5 rounded-lg bg-slate-50 border border-slate-200">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono text-xs font-bold text-blue-600">{w.num}</span>
                    <Icon className="w-4 h-4 text-slate-500" />
                  </div>
                  <h3 className="text-sm font-bold text-slate-900">{w.title}</h3>
                  <p className="text-xs text-slate-600 mt-0.5 font-medium">{w.desc}</p>
                </div>
              );
            })}
          </div>
        </section>

        {/* Trust & Human Control Guarantee */}
        <section aria-labelledby="trust-heading" className="bg-slate-900 text-white rounded-xl p-6 sm:p-8 shadow-sm">
          <div className="max-w-3xl">
            <div className="flex items-center gap-2 text-blue-400 mb-2">
              <Lock className="w-4 h-4" />
              <span className="text-xs font-semibold uppercase tracking-wider">Trust & Accountability</span>
            </div>
            <h2 id="trust-heading" className="text-xl font-bold tracking-tight mb-3">
              Built on Transparency and Human Control
            </h2>
            <p className="text-sm text-slate-200 leading-relaxed mb-6">
              CivicFlow is built for transparency and public trust. You always have the final say on your report, location is cross-checked using OpenStreetMap, and municipal personnel make all final decisions.
            </p>
            <div className="flex flex-col sm:flex-row flex-wrap items-start sm:items-center gap-3 sm:gap-4 text-xs sm:text-sm font-medium text-slate-100">
              <span className="inline-flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                Verified Evidence
              </span>
              <span className="inline-flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                Human Review on Every Report
              </span>
              <span className="inline-flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                Secure Administrative Access
              </span>
            </div>
          </div>
        </section>
      </main>

      {/* Standard Civic Footer */}
      <footer className="border-t border-slate-200 bg-white py-6 mt-12">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-xs text-slate-600 space-y-1.5">
          <p className="font-bold text-slate-800 text-sm">
            CivicFlow — Municipal Issue Reporting & Review Platform
          </p>
          <p className="text-xs text-slate-500 font-medium">
            Community Reporting &bull; Verified Location &bull; Municipal Accountability
          </p>
          {onNavigateAdmin && (
            <p className="pt-2 text-xs">
              <button
                type="button"
                onClick={onNavigateAdmin}
                className="text-slate-500 hover:text-slate-800 hover:underline inline-flex items-center gap-1 font-medium"
              >
                <Lock className="w-3 h-3 text-slate-500" />
                <span>Administrator? Access the Admin Portal</span>
              </button>
            </p>
          )}
        </div>
      </footer>
    </div>
  );
}
