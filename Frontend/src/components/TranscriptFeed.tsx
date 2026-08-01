import React, { useEffect, useRef } from "react";
import type { TranscriptMessage, Sentiment } from "../types";
import { User, Bot, Sparkles } from "lucide-react";

interface TranscriptFeedProps {
  transcripts: TranscriptMessage[];
  latestToken: string;
}

export const TranscriptFeed: React.FC<TranscriptFeedProps> = ({
  transcripts,
  latestToken,
}) => {
  const feedEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    feedEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcripts, latestToken]);

  const getSentimentBadge = (sentiment: Sentiment) => {
    switch (sentiment) {
      case "Positive":
        return (
          <span className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            Positive
          </span>
        );
      case "Hesitant":
        return (
          <span className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
            Hesitant
          </span>
        );
      case "Negative":
        return (
          <span className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded bg-rose-500/10 text-rose-400 border border-rose-500/20">
            Negative
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded bg-slate-800 text-slate-400">
            Neutral
          </span>
        );
    }
  };

  return (
    <div className="flex flex-col h-[400px] bg-slate-900/60 border border-slate-800 rounded-2xl p-4 overflow-y-auto space-y-4">
      {transcripts.length === 0 && !latestToken && (
        <div className="flex flex-col items-center justify-center h-full text-center text-slate-500 space-y-2">
          <Sparkles className="w-8 h-8 text-indigo-400/50" />
          <p className="text-sm">No active conversation yet.</p>
          <p className="text-xs text-slate-600">
            Click "Start AI Call" and speak into your microphone to begin sales
            qualification.
          </p>
        </div>
      )}

      {transcripts.map((msg, idx) => (
        <div
          key={idx}
          className={`flex gap-3 ${
            msg.role === "user" ? "justify-end" : "justify-start"
          }`}
        >
          {msg.role === "assistant" && (
            <div className="w-8 h-8 rounded-full bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center shrink-0">
              <Bot className="w-4 h-4 text-indigo-400" />
            </div>
          )}

          <div
            className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm space-y-1.5 ${
              msg.role === "user"
                ? "bg-emerald-950/40 border border-emerald-800/40 text-slate-100 rounded-br-none"
                : "bg-slate-800/70 border border-slate-700/50 text-slate-200 rounded-bl-none"
            }`}
          >
            <div className="flex items-center justify-between gap-4">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                {msg.role === "user" ? "Customer" : "VocalSync AI"}
              </span>
              {msg.role === "user" && getSentimentBadge(msg.sentiment)}
            </div>
            <p className="leading-relaxed whitespace-pre-wrap">{msg.content}</p>
          </div>

          {msg.role === "user" && (
            <div className="w-8 h-8 rounded-full bg-emerald-600/20 border border-emerald-500/30 flex items-center justify-center shrink-0">
              <User className="w-4 h-4 text-emerald-400" />
            </div>
          )}
        </div>
      ))}

      {/* Real-time LLM Token Streaming Indicator */}
      {latestToken && (
        <div className="flex gap-3 justify-start">
          <div className="w-8 h-8 rounded-full bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center shrink-0">
            <Bot className="w-4 h-4 text-indigo-400 animate-spin" />
          </div>
          <div className="max-w-[80%] rounded-2xl rounded-bl-none px-4 py-3 text-sm bg-slate-800/70 border border-indigo-500/30 text-slate-200">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-indigo-400 block mb-1">
              VocalSync AI (Speaking...)
            </span>
            <p className="leading-relaxed inline">{latestToken}</p>
            <span className="inline-block w-1.5 h-4 ml-1 bg-indigo-400 animate-pulse align-middle" />
          </div>
        </div>
      )}

      <div ref={feedEndRef} />
    </div>
  );
};
