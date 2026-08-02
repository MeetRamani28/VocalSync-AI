import React, { useState } from "react";
import { apiService } from "../services/api";
import { OutboundCallResponse } from "../types";

interface OutboundDialerCardProps {
  businessId?: string;
  onCallInitiated?: (callId: string, twilioSid: string) => void;
}

export const OutboundDialerCard: React.FC<OutboundDialerCardProps> = ({
  businessId = "default_business",
  onCallInitiated,
}) => {
  const [phoneNumber, setPhoneNumber] = useState<string>("");
  const [callerName, setCallerName] = useState<string>("");
  const [isDialing, setIsDialing] = useState<boolean>(false);
  const [lastResponse, setLastResponse] = useState<OutboundCallResponse | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);

  const handleDial = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLastResponse(null);

    const trimmedPhone = phoneNumber.trim();
    if (!trimmedPhone || !trimmedPhone.startsWith("+")) {
      setError(
        "Please enter a valid E.164 phone number starting with + (e.g., +919876543210).",
      );
      return;
    }

    setIsDialing(true);
    try {
      const res = await apiService.dialOutboundCall({
        phone_number: trimmedPhone,
        caller_name: callerName.trim() || "Prospect",
        business_id: businessId,
      });

      setLastResponse(res);
      if (onCallInitiated) {
        onCallInitiated(res.call_id, res.twilio_sid);
      }
    } catch (err: any) {
      console.error("Outbound call failed:", err);
      setError(
        err?.response?.data?.detail ||
          "Failed to trigger Twilio PSTN call. Ensure Twilio credentials are in .env.",
      );
    } finally {
      setIsDialing(false);
    }
  };

  return (
    <div className="rounded-2xl bg-slate-900/80 border border-slate-800 p-5 shadow-lg">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="flex h-2.5 w-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
            PSTN Outbound AI Dialer
          </h3>
        </div>
        <span className="text-xs font-medium text-slate-500">
          Twilio Media Streams
        </span>
      </div>

      {error && (
        <div className="mb-3 rounded-lg bg-red-950/40 border border-red-800/80 p-2.5 text-xs text-red-300">
          {error}
        </div>
      )}

      {lastResponse && (
        <div className="mb-3 rounded-lg bg-emerald-950/40 border border-emerald-800/80 p-2.5 text-xs text-emerald-300">
          <p className="font-semibold">📞 Call Dispatched successfully!</p>
          <p className="text-slate-400 mt-1">
            Twilio SID: {lastResponse.twilio_sid}
          </p>
        </div>
      )}

      <form onSubmit={handleDial} className="space-y-3">
        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1">
            Prospect Name (for AI Greeting)
          </label>
          <input
            type="text"
            value={callerName}
            onChange={(e) => setCallerName(e.target.value)}
            placeholder="e.g., Meet Patel"
            className="w-full rounded-lg bg-slate-800/90 border border-slate-700 px-3 py-1.5 text-sm text-white focus:border-indigo-500 focus:outline-none"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1">
            Destination Phone Number (E.164 Format)
          </label>
          <input
            type="tel"
            required
            value={phoneNumber}
            onChange={(e) => setPhoneNumber(e.target.value)}
            placeholder="+919876543210 or +18005550199"
            className="w-full rounded-lg bg-slate-800/90 border border-slate-700 px-3 py-1.5 text-sm text-white focus:border-indigo-500 focus:outline-none"
          />
        </div>

        <button
          type="submit"
          disabled={isDialing}
          className="w-full rounded-lg bg-gradient-to-r from-indigo-600 to-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-md hover:from-indigo-500 hover:to-blue-500 disabled:opacity-50 transition-all flex items-center justify-center gap-2"
        >
          {isDialing ? (
            <>
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"></span>
              <span>Dialing Network...</span>
            </>
          ) : (
            <span>🚀 Dial Outbound PSTN Call</span>
          )}
        </button>
      </form>
    </div>
  );
};
