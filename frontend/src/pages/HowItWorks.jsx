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
      desc: "Upload a real photo, describe the problem and provide location evidence.",
      details: "CivicFlow begins with authentic visual evidence. Citizens provide an unaltered photo of the civic defect (such as a pothole, broken streetlight, or garbage overflow) along with their description and location hints.",
      icon: Camera,
      pill: "Citizen Evidence"
    },
    {
      num: "02",
      title: "AI assists",
      desc: "Gemini analyzes the supplied evidence and prepares a structured complaint draft.",
      details: "Our multimodal AI analyzes the physical photo and citizen description to infer the correct municipal category, urgency level, and standard civic terminology—without ever fabricating facts or replacing human judgment.",
      icon: Cpu,
      pill: "Multimodal AI"
    },
    {
      num: "03",
      title: "Location is checked",
      desc: "Address information and device coordinates are cross-referenced using geographic services.",
      details: "OpenStreetMap and Nominatim services perform forward and reverse geocoding to detect discrepancies between reported street addresses and GPS device coordinates, ensuring work crews are dispatched accurately.",
      icon: MapPin,
      pill: "Deterministic GIS"
    },
    {
      num: "04",
      title: "You review",
      desc: "The citizen remains in control and can edit the AI-assisted report.",
      details: "Human agency is strictly preserved. Citizens review the AI proposal, edit any wording, refine summaries, and explicitly confirm their submission. Nothing is submitted without citizen authorization.",
      icon: UserCheck,
      pill: "Human-in-the-Loop"
    },
    {
      num: "05",
      title: "A human administrator decides",
      desc: "Municipal administrators review the evidence and make the final decision.",
      details: "Authorized municipal officers inspect the complete immutable case package—including the original photo, AI interpretation, citizen-reviewed report, and GIS map—to officially accept or reject the complaint with stated reasons.",
      icon: ShieldCheck,
      pill: "Municipal Authority"
    },
  ];

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      {/* Header */}
      <div className="text-center max-w-3xl mx-auto mb-12">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-800 border border-blue-200 mb-3">
          <Shield className="w-3.5 h-3.5 text-blue-600" aria-hidden="true" />
          <span>Product Workflow</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
          How CivicFlow Works
        </h1>
        <p className="mt-3 text-sm sm:text-base text-slate-600 leading-relaxed">
          A transparent, five-stage public service workflow that combines authentic evidence, AI assistance, 
          and human authority to resolve civic problems fairly and reliably.
        </p>
      </div>

      {/* 5 Stages List */}
      <div className="space-y-6 mb-12">
        {steps.map((s) => {
          const Icon = s.icon;
          return (
            <div
              key={s.num}
              className="bg-white rounded-xl border border-slate-200 p-6 sm:p-8 shadow-sm flex flex-col md:flex-row md:items-start gap-6 hover:border-slate-300 transition"
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
                  <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
                    {s.pill}
                  </span>
                </div>
                <p className="text-sm font-medium text-slate-700 mb-2">
                  {s.desc}
                </p>
                <p className="text-xs text-slate-500 leading-relaxed">
                  {s.details}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Human-in-the-Loop Governance Card */}
      <div className="bg-slate-900 text-white rounded-xl p-8 mb-12 shadow-md">
        <div className="max-w-3xl">
          <div className="flex items-center gap-2 text-blue-400 mb-2">
            <Lock className="w-4 h-4" />
            <span className="text-xs font-semibold uppercase tracking-wider">Security & Governance</span>
          </div>
          <h2 className="text-xl font-bold tracking-tight mb-3">
            Why Human Authorization Matters
          </h2>
          <p className="text-xs sm:text-sm text-slate-300 leading-relaxed mb-4">
            Civic infrastructure impacts everyday lives. CivicFlow guarantees that AI never replaces human decision-makers. 
            AI only assists in drafting and categorizing; the citizen must review and authorize the report, and a verified municipal 
            official must decide on municipal action.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 text-xs text-slate-300">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>Zero autonomous submissions</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>Full audit provenance preserved</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>Server-enforced role security</span>
            </div>
          </div>
        </div>
      </div>

      {/* Action CTA */}
      <div className="text-center bg-blue-50 border border-blue-200 rounded-xl p-8">
        <h3 className="text-lg font-bold text-slate-900 mb-2">
          Ready to report an issue in your community?
        </h3>
        <p className="text-xs text-slate-600 max-w-md mx-auto mb-5">
          Submit authentic evidence and help your local municipality respond quickly and effectively.
        </p>
        <button
          type="button"
          onClick={onNavigateReport}
          className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs sm:text-sm font-semibold transition shadow-sm inline-flex items-center gap-2"
        >
          <span>Report an Issue</span>
          <ArrowRight className="w-4 h-4" aria-hidden="true" />
        </button>
      </div>
    </div>
  );
}
