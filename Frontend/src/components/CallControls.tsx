import React from "react";
import { PhoneCall, PhoneOff, Mic, MicOff, ShieldAlert } from "lucide-react";

interface CallControlsProps {
  isConnected: boolean;
  isRecording: boolean;
  agentState: "connected" | "speaking" | "listening" | "processing" | "idle";
  onStartCall: () => void;
  onEndCall: () => void;
  errorMessage: string | null;
}

export const CallControls: React.FC<CallControlsProps> = ({
  isConnected,
  isRecording,
  agentState,
  onStartCall,
  onEndCall,
  errorMessage,
}) => {
  const getStatusBadge = () => {
    switch (agentState) {
      case "speaking":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <span className="w-2 h-2 rounded-full bg-indigo-500 animate-ping" />
            AI Speaking
          </span>
        );
      case "processing":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
            Processing Speech...
          </span>
        );
      case "connected":
      case "listening":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            Listening to You
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700">
            Idle
          </span>
        );
    }
  };

  return (
    <div className="w-full bg-slate-900 border border-slate-800 rounded-2xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4 shadow-lg">
      <div className="flex items-center gap-3">
        {getStatusBadge()}
        {isRecording ? (
          <span className="flex items-center gap-1 text-xs text-slate-400">
            <Mic className="w-3.5 h-3.5 text-emerald-400" /> Mic Active
          </span>
        ) : (
          <span className="flex items-center gap-1 text-xs text-slate-500">
            <MicOff className="w-3.5 h-3.5" /> Mic Muted
          </span>
        )}
      </div>

      {errorMessage && (
        <div className="flex items-center gap-2 text-xs text-rose-400 bg-rose-500/10 px-3 py-1.5 rounded-lg border border-rose-500/20">
          <ShieldAlert className="w-4 h-4 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      <div className="flex items-center gap-3 w-full sm:w-auto justify-end">
        {!isConnected ? (
          <button
            onClick={onStartCall}
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-2.5 rounded-xl font-semibold text-sm bg-emerald-600 hover:bg-emerald-500 text-white shadow-md shadow-emerald-900/20 transition-all cursor-pointer"
          >
            <PhoneCall className="w-4 h-4" />
            Start AI Call
          </button>
        ) : (
          <button
            onClick={onEndCall}
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-2.5 rounded-xl font-semibold text-sm bg-rose-600 hover:bg-rose-500 text-white shadow-md shadow-rose-900/20 transition-all cursor-pointer"
          >
            <PhoneOff className="w-4 h-4" />
            End Call
          </button>
        )}
      </div>
    </div>
  );
};
