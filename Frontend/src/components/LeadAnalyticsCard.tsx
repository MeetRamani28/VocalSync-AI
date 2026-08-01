import React from "react";
import type { LeadProfile } from "../types";
import {
  Award,
  DollarSign,
  Building2,
  User,
  AlertCircle,
  ShieldCheck,
} from "lucide-react";

interface LeadAnalyticsCardProps {
  lead: LeadProfile | null;
}

export const LeadAnalyticsCard: React.FC<LeadAnalyticsCardProps> = ({
  lead,
}) => {
  if (!lead) {
    return (
      <div className="w-full bg-slate-900/60 border border-slate-800 rounded-2xl p-6 flex flex-col items-center justify-center text-center text-slate-500 space-y-3 min-h-[220px]">
        <Award className="w-10 h-10 text-slate-700" />
        <p className="text-sm font-medium text-slate-400">
          No Lead Profile Qualified Yet
        </p>
        <p className="text-xs text-slate-600 max-w-xs">
          As the conversation progresses, VocalSync AI autonomously extracts
          intent, budget tier, and contact information.
        </p>
      </div>
    );
  }

  const getScoreColor = (score: number) => {
    if (score >= 75)
      return "text-emerald-400 border-emerald-500/30 bg-emerald-500/10";
    if (score >= 50)
      return "text-amber-400 border-amber-500/30 bg-amber-500/10";
    return "text-rose-400 border-rose-500/30 bg-rose-500/10";
  };

  return (
    <div className="w-full bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4 shadow-lg">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-indigo-400" />
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-200">
            Qualified CRM Lead
          </h3>
        </div>
        <span
          className={`px-3 py-1 rounded-full text-xs font-bold border ${getScoreColor(
            lead.qualification_score,
          )}`}
        >
          Score: {lead.qualification_score} / 100
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
        <div className="flex items-center gap-2 p-2.5 rounded-xl bg-slate-950/60 border border-slate-800">
          <User className="w-4 h-4 text-slate-400 shrink-0" />
          <div className="truncate">
            <span className="text-slate-500 block text-[10px] uppercase">
              Caller
            </span>
            <span className="font-semibold text-slate-200">
              {lead.caller_name || "Anonymous Prospect"}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2 p-2.5 rounded-xl bg-slate-950/60 border border-slate-800">
          <Building2 className="w-4 h-4 text-slate-400 shrink-0" />
          <div className="truncate">
            <span className="text-slate-500 block text-[10px] uppercase">
              Company
            </span>
            <span className="font-semibold text-slate-200">
              {lead.company_name || "Not Specified"}
            </span>
          </div>
        </div>
      </div>

      <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 space-y-1">
        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
          Primary Intent & Needs
        </span>
        <p className="text-xs text-slate-300 leading-relaxed">
          {lead.intent_summary}
        </p>
      </div>

      <div className="flex items-center justify-between p-3 rounded-xl bg-slate-950/60 border border-slate-800 text-xs">
        <span className="flex items-center gap-1.5 text-slate-400">
          <DollarSign className="w-4 h-4 text-emerald-400" /> Estimated Budget
        </span>
        <span className="font-bold uppercase tracking-wider text-emerald-400">
          {lead.budget_tier.replace("_", " ")}
        </span>
      </div>

      {lead.objections_raised.length > 0 && (
        <div className="space-y-1.5">
          <span className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider text-amber-400">
            <AlertCircle className="w-3.5 h-3.5" /> Logged Objections
          </span>
          <div className="flex flex-wrap gap-1.5">
            {lead.objections_raised.map((objection, index) => (
              <span
                key={index}
                className="px-2.5 py-1 text-[11px] rounded-lg bg-amber-500/10 text-amber-300 border border-amber-500/20"
              >
                {objection}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
