import React, { useState, useEffect, useCallback } from "react";
import {
  Sparkles,
  PhoneCall,
  Activity,
  ShieldCheck,
  BarChart3,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
} from "lucide-react";
import { useAudioRecorder } from "./hooks/useAudioRecorder";
import { useWebSocketVoice } from "./hooks/useWebSocketVoice";
import { apiService } from "./services/api";
import type { AnalyticsSummary } from "./types";
import { AudioVisualizer } from "./components/AudioVisualizer";
import { CallControls } from "./components/CallControls";
import { TranscriptFeed } from "./components/TranscriptFeed";
import { LeadAnalyticsCard } from "./components/LeadAnalyticsCard";

export const App: React.FC = () => {
  const [callId, setCallId] = useState<string>("");
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);
  const [isBackendHealthy, setIsBackendHealthy] = useState<boolean | null>(
    null,
  );
  const [isRefreshingAnalytics, setIsRefreshingAnalytics] =
    useState<boolean>(false);

  const {
    isConnected,
    agentState,
    transcripts,
    latestToken,
    qualifiedLead,
    errorMessage: wsError,
    connect,
    disconnect,
    sendAudioChunk,
    clearError,
  } = useWebSocketVoice();

  const {
    isRecording,
    startRecording,
    stopRecording,
    getFrequencyData,
    error: audioError,
  } = useAudioRecorder({
    onAudioChunkAvailable: sendAudioChunk,
    timeSliceMs: 250,
  });

  const handleStartCall = useCallback(async () => {
    clearError();
    const newCallId = `call_${crypto.randomUUID()}`;
    setCallId(newCallId);

    try {
      connect(newCallId);
      await startRecording();
    } catch (err) {
      console.error("Failed to start voice call session:", err);
    }
  }, [clearError, connect, startRecording]);

  const fetchAnalytics = useCallback(async () => {
    setIsRefreshingAnalytics(true);
    try {
      const summary = await apiService.getAnalyticsSummary();
      setAnalytics(summary);
    } catch (err) {
      console.error("Failed to fetch analytics summary:", err);
    } finally {
      setIsRefreshingAnalytics(false);
    }
  }, []);

  const handleEndCall = useCallback(() => {
    stopRecording();
    disconnect();
    void fetchAnalytics();
  }, [stopRecording, disconnect, fetchAnalytics]);

  useEffect(() => {
    const checkSystemReady = async () => {
      try {
        const health = await apiService.checkHealth();
        setIsBackendHealthy(health.database_connected);
        await fetchAnalytics();
      } catch (err) {
        console.error("Backend unreachable:", err);
        setIsBackendHealthy(false);
      }
    };

    void checkSystemReady();
  }, [fetchAnalytics]);

  const activeError = wsError || audioError;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col selection:bg-indigo-500 selection:text-white">
      <header className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-linear-to-tr from-indigo-600 to-emerald-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <PhoneCall className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="text-base font-extrabold tracking-tight bg-linear-to-r from-white via-slate-200 to-indigo-400 bg-clip-text text-transparent">
                VocalSync-AI
              </span>
              <span className="block text-[10px] font-medium uppercase tracking-wider text-slate-400">
                Enterprise AI Voice Sales Console
              </span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="hidden md:flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-slate-800/80 border border-slate-700 text-slate-300">
              <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
              <span>OWASP LLM & API Guardrails Active</span>
            </div>

            <div className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-slate-900 border border-slate-800">
              {isBackendHealthy === true ? (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="text-emerald-400">System Online</span>
                </>
              ) : isBackendHealthy === false ? (
                <>
                  <AlertCircle className="w-3.5 h-3.5 text-rose-400" />
                  <span className="text-rose-400">Backend Offline</span>
                </>
              ) : (
                <>
                  <RefreshCw className="w-3.5 h-3.5 text-amber-400 animate-spin" />
                  <span className="text-amber-400">Connecting...</span>
                </>
              )}
            </div>
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          <div className="lg:col-span-7 xl:col-span-8 space-y-6">
            <section className="space-y-2">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                  <Activity className="w-4 h-4 text-emerald-400" />
                  Real-Time Voice Waveform
                </h2>
                {callId && (
                  <span className="text-xs font-mono text-slate-500">
                    Session: {callId}
                  </span>
                )}
              </div>
              <AudioVisualizer
                getFrequencyData={getFrequencyData}
                isRecording={isRecording}
                agentState={agentState}
              />
            </section>

            <section>
              <CallControls
                isConnected={isConnected}
                isRecording={isRecording}
                agentState={agentState}
                onStartCall={handleStartCall}
                onEndCall={handleEndCall}
                errorMessage={activeError}
              />
            </section>

            <section className="space-y-2">
              <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-indigo-400" />
                Live Conversation & Sentiment
              </h2>
              <TranscriptFeed
                transcripts={transcripts}
                latestToken={latestToken}
              />
            </section>
          </div>

          <div className="lg:col-span-5 xl:col-span-4 space-y-6">
            <section className="space-y-2">
              <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400">
                Live Lead Qualification
              </h2>
              <LeadAnalyticsCard lead={qualifiedLead} />
            </section>

            <section className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 space-y-4 shadow-lg">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <BarChart3 className="w-5 h-5 text-indigo-400" />
                  <h3 className="text-sm font-bold uppercase tracking-wider text-slate-200">
                    Executive Analytics
                  </h3>
                </div>
                <button
                  onClick={fetchAnalytics}
                  disabled={isRefreshingAnalytics}
                  className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 transition-colors disabled:opacity-50 cursor-pointer"
                  title="Refresh KPI metrics"
                >
                  <RefreshCw
                    className={`w-3.5 h-3.5 ${
                      isRefreshingAnalytics
                        ? "animate-spin text-indigo-400"
                        : ""
                    }`}
                  />
                </button>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
                    Total Calls
                  </span>
                  <span className="text-xl font-black text-slate-100 mt-1 block">
                    {analytics?.total_calls ?? 0}
                  </span>
                </div>

                <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
                    Qualified Leads
                  </span>
                  <span className="text-xl font-black text-emerald-400 mt-1 block">
                    {analytics?.qualified_leads ?? 0}
                  </span>
                </div>

                <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
                    Avg Call Time
                  </span>
                  <span className="text-xl font-black text-slate-100 mt-1 block">
                    {analytics?.avg_call_duration_seconds ?? 0}s
                  </span>
                </div>

                <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
                    Conversion Rate
                  </span>
                  <span className="text-xl font-black text-indigo-400 mt-1 block">
                    {analytics?.conversion_rate_percent ?? 0}%
                  </span>
                </div>
              </div>

              <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-500">
                <span>Warm CRM Pipeline:</span>
                <span className="font-semibold text-slate-300">
                  {analytics?.warm_leads ?? 0} Leads
                </span>
              </div>
            </section>
          </div>
        </div>
      </main>

      <footer className="border-t border-slate-800/80 bg-slate-900/30 py-4 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-slate-500">
          <p>
            Powered by Groq Whisper Turbo, Llama-3.3-70B, Edge-TTS, and MongoDB
            Atlas.
          </p>
          <p className="font-mono">100% Free Open-Source Infrastructure</p>
        </div>
      </footer>
    </div>
  );
};

export default App;
