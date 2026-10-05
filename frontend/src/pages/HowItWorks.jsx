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
  Lock
} from 'lucide-react';

export default function HowItWorks({ onNavigateReport }) {
  const steps = [
    {
      num: "01",
      title: "Capture the issue",
      desc: "Take or upload a photo, describe what you see, and add location details.",
      details: "CivicFlow begins with a clear photo of the issue (such as a pothole, broken streetlight, or waste overflow) along with your description and location details.",
      icon: Camera,
      pill: "Photos & Details"
    },
    {
      num: "02",
      title: "Report is prepared",
      desc: "Your photo and description are organized into a clear report draft.",
      details: "CivicFlow organizes the photo and description into standard issue categories, suggested priority levels, and concise summaries for municipal staff.",
      icon: Cpu,
      pill: "Smart Preparation"
    },
    {
      num: "03",
      title: "Location is checked",
      desc: "Address details and coordinates are cross-referenced to ensure accurate location.",
      details: "OpenStreetMap services verify that entered street addresses match the map location so municipal crews can locate the problem quickly.",
      icon: MapPin,
      pill: "Location Check"
    },
    {
      num: "04",
      title: "You review",
      desc: "You can edit and confirm all report details before submitting.",
      details: "You stay in complete control. Review the draft, adjust descriptions or addresses, and confirm when you are satisfied. Nothing is submitted without your approval.",
      icon: UserCheck,
      pill: "Your Review"
    },
    {
      num: "05",
      title: "Municipal review",
      desc: "Municipal staff review the report and take official action.",
      details: "Authorized municipal personnel inspect the complete report—including photo, location, and confirmed details—to accept or decline the report with clear reasons.",
      icon: ShieldCheck,
      pill: "Administrative Review"
    },
  ];

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-10">
      {/* Header */}
      <div className="text-center max-w-3xl mx-auto mb-8 sm:mb-12">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-800 border border-blue-200 mb-3">
          <Shield className="w-3.5 h-3.5 text-blue-600" aria-hidden="true" />
          <span>How It Works</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
          How CivicFlow Works
        </h1>
        <p className="mt-3 text-sm sm:text-base text-slate-600 leading-relaxed">
          A clear, straightforward public service workflow that pairs quick report preparation with thorough human review to resolve neighborhood issues.
        </p>
      </div>

      {/* 5 Stages List */}
      <div className="space-y-4 sm:space-y-6 mb-8 sm:mb-12">
        {steps.map((s) => {
          const Icon = s.icon;
          return (
            <div
              key={s.num}
              className="bg-white rounded-xl border border-slate-200 p-5 sm:p-6 lg:p-8 shadow-sm flex flex-col md:flex-row md:items-start gap-4 sm:gap-6 hover:border-slate-300 transition"
            >
              <div className="flex items-center gap-4 md:flex-col md:items-start shrink-0">
                <span className="font-mono text-3xl font-extrabold text-blue-600">
                  {s.num}
                </span>
                <div className="w-12 h-12 rounded-xl bg-blue-50 border border-blue-200 text-blue-600 flex items-center justify-center">
                  <Icon className="w-6 h-6" aria-hidden="true" />
                </div>
              </div>

              <div className="flex-1">
                <div className="flex flex-wrap items-center gap-2 mb-2">
                  <h2 className="text-lg font-bold text-slate-900">
                    {s.title}
                  </h2>
                  <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
                    {s.pill}
                  </span>
                </div>
                <p className="text-base font-semibold text-slate-900 mb-2">
                  {s.desc}
                </p>
                <p className="text-sm text-slate-600 leading-relaxed font-normal">
                  {s.details}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Human-in-the-Loop Governance Card */}
      <div className="bg-slate-900 text-white rounded-xl p-6 sm:p-8 mb-8 sm:mb-12 shadow-md">
        <div className="max-w-3xl">
          <div className="flex items-center gap-2 text-blue-400 mb-2">
            <Lock className="w-4 h-4" />
            <span className="text-xs font-semibold uppercase tracking-wider">Accountability & Review</span>
          </div>
          <h2 className="text-xl font-bold tracking-tight mb-3">
            Why Human Review Matters
          </h2>
          <p className="text-sm text-slate-200 leading-relaxed mb-4">
            Civic infrastructure matters to everyone. CivicFlow ensures that real people remain in charge at every stage. Technology only helps prepare and organize the information—citizens always confirm what is submitted, and municipal staff make every final decision.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 text-xs sm:text-sm text-slate-200 font-medium">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>No automated submissions</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>Complete report history preserved</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>Secure administrative access</span>
            </div>
          </div>
        </div>
      </div>

      {/* Action CTA */}
      <div className="text-center bg-blue-50 border border-blue-200 rounded-xl p-6 sm:p-8">
        <h3 className="text-lg font-bold text-slate-900 mb-2">
          Ready to report an issue in your community?
        </h3>
        <p className="text-sm text-slate-600 max-w-md mx-auto mb-5">
          Submit a report and help your local municipality respond quickly and effectively.
        </p>
        <button
          type="button"
          onClick={onNavigateReport}
          className="w-full sm:w-auto px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs sm:text-sm font-semibold transition shadow-sm inline-flex items-center justify-center gap-2"
        >
          <span>Report an Issue</span>
          <ArrowRight className="w-4 h-4" aria-hidden="true" />
        </button>
      </div>
    </div>
  );
}
