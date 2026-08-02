import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useAudioRecorder } from './hooks/useAudioRecorder';
import { useWebSocketVoice } from './hooks/useWebSocketVoice';
import { apiService } from './services/api';
import { BusinessProfile, SystemHealth } from './types';

// UI Components
import { AudioVisualizer } from './components/AudioVisualizer';
import { CallControls } from './components/CallControls';
import { TranscriptFeed } from './components/TranscriptFeed';
import { LeadAnalyticsCard } from './components/LeadAnalyticsCard';
import { BusinessConfigModal } from './components/BusinessConfigModal';
import { OutboundDialerCard } from './components/OutboundDialerCard';

export const App: React.FC = () => {
  const [activeCallId, setActiveCallId] = useState<string | null>(null);
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null);
  const [businessProfile, setBusinessProfile] = useState<BusinessProfile | null>(null);
  const [isKbModalOpen, setIsKbModalOpen] = useState<boolean>(false);
  const [callMode, setCallMode] = useState<'browser' | 'pstn'>('browser');

  const animationFrameRef = useRef<number | null>(null);
  const [visualizerData, setVisualizerData] = useState<Uint8Array | null>(null);

  // Initialize Voice WebSocket Hook
  const {
    isConnected,
    agentStatus,
    transcripts,
    liveLead,
    connectWebSocket,
    disconnectWebSocket,
    sendAudioChunk,
    error: wsError,
  } = useWebSocketVoice();

  // Initialize Microphone Recording Hook (with RMS Noise Gate)
  const {
    isRecording,
    startRecording,
    stopRecording,
    getFrequencyData,
    error: micError,
  } = useAudioRecorder({
    onAudioChunkAvailable: async (blob: Blob) => {
      await sendAudioChunk(blob);
    },
    timeSliceMs: 1000,
    silenceThresholdDb: -50,
  });

  // Load System Health & Default Business KB on mount
  useEffect(() => {
    const initApp = async () => {
      try {
        const [health, profile] = await Promise.all([
          apiService.getHealth(),
          apiService.getBusinessProfile('default_business').catch(() => null),
        ]);
        setSystemHealth(health);
        if (profile) setBusinessProfile(profile);
      } catch (err) {
        console.error('Failed to initialize application data:', err);
      }
    };
    initApp();
  }, []);

  // 60fps Waveform Visualizer Loop
  const updateVisualizer = useCallback(() => {
    const data = getFrequencyData();
    if (data) {
      setVisualizerData(new Uint8Array(data));
    }
    animationFrameRef.current = requestAnimationFrame(updateVisualizer);
  }, [getFrequencyData]);

  useEffect(() => {
    if (isRecording) {
      animationFrameRef.current = requestAnimationFrame(updateVisualizer);
    } else if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      setVisualizerData(null);
    }
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [isRecording, updateVisualizer]);

  // Handle Browser AI Call Start
  const handleStartBrowserCall = async () => {
    const newCallId = `call_${crypto.randomUUID()}`;
    setActiveCallId(newCallId);
    connectWebSocket(
      newCallId,
      businessProfile?.business_id || 'default_business'
    );
    await startRecording();
  };

  // Handle Browser AI Call End
  const handleEndBrowserCall = () => {
    stopRecording();
    disconnectWebSocket();
    setActiveCallId(null);
  };

  // Callback when Outbound PSTN Call is dispatched
  const handlePstnCallInitiated = (callId: string, twilioSid: string) => {
    setActiveCallId(callId);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* TOP EXECUTIVE NAVIGATION BAR */}
      <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur-md sticky top-0 z-40 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600 font-bold text-white shadow-lg shadow-indigo-600/30">
            VS
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight text-white">
              VocalSync-AI Enterprise
            </h1>
            <p className="text-xs text-slate-400">
              Autonomous Sales Qualification & Telephony Calling Console
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* Active Knowledge Base Badge */}
          <button
            onClick={() => setIsKbModalOpen(true)}
            className="flex items-center gap-2 rounded-lg bg-slate-800 border border-slate-700 px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-750 hover:text-white transition-all"
          >
            <span>🏢 Active KB:</span>
            <span className="font-semibold text-indigo-400">
              {businessProfile?.company_name || 'VocalSync-AI Default'}
            </span>
            <span className="text-slate-500">⚙️</span>
          </button>

          {/* System Health Indicator */}
          <div className="flex items-center gap-2 rounded-full bg-slate-900 border border-slate-800 px-3 py-1 text-xs font-semibold">
            <span
              className={`h-2.5 w-2.5 rounded-full ${
                systemHealth?.status === 'online'
                  ? 'bg-emerald-500 shadow-sm shadow-emerald-500/50 animate-pulse'
                  : 'bg-amber-500'
              }`}
            />
            <span className="text-slate-300 uppercase">
              {systemHealth?.status || 'Connecting...'}
            </span>
          </div>
        </div>
      </header>

      {/* ERROR BANNER */}
      {(wsError || micError) && (
        <div className="bg-red-950/80 border-b border-red-800 px-6 py-2.5 text-xs font-medium text-red-200 flex items-center justify-between">
          <span>⚠️ {wsError || micError}</span>
          <button
            onClick={() => window.location.reload()}
            className="underline hover:text-white font-semibold"
          >
            Reload Page
          </button>
        </div>
      )}

      {/* MAIN CONSOLE DASHBOARD */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* LEFT COLUMN: LIVE VOICE CONTROLS & TRANSCRIPTS (7 Cols) */}
        <div className="lg:col-span-7 flex flex-col gap-6">
          {/* Mode Switching Tabs (Browser vs PSTN Phone) */}
          <div className="flex rounded-xl bg-slate-900 border border-slate-800 p-1">
            <button
              onClick={() => setCallMode('browser')}
              className={`flex-1 rounded-lg py-2 text-xs font-semibold uppercase tracking-wider transition-all ${
                callMode === 'browser'
                  ? 'bg-indigo-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              💻 Local Browser Mic Call
            </button>
            <button
              onClick={() => setCallMode('pstn')}
              className={`flex-1 rounded-lg py-2 text-xs font-semibold uppercase tracking-wider transition-all ${
                callMode === 'pstn'
                  ? 'bg-indigo-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              📞 Outbound PSTN Phone Call
            </button>
          </div>

          {/* CALL TRIGGER SECTION */}
          {callMode === 'browser' ? (
            <div className="rounded-2xl bg-slate-900 border border-slate-800 p-5 shadow-lg flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
                    Live Browser Voice Session
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Sub-second Llama-3.3-70B voice conversation over browser audio
                  </p>
                </div>
                <CallControls
                  isRecording={isRecording}
                  agentStatus={agentStatus}
                  onStartCall={handleStartBrowserCall}
                  onEndCall={handleEndBrowserCall}
                />
              </div>

              {/* Waveform Visualizer */}
              <div className="h-24 w-full rounded-xl bg-slate-950/80 border border-slate-800 overflow-hidden">
                <AudioVisualizer
                  data={visualizerData}
                  isRecording={isRecording}
                  agentStatus={agentStatus}
                />
              </div>
            </div>
          ) : (
            <OutboundDialerCard
              businessId={businessProfile?.business_id || 'default_business'}
              onCallInitiated={handlePstnCallInitiated}
            />
          )}

          {/* REAL-TIME DIALOGUE & SENTIMENT FEED */}
          <div className="flex-1 min-h-[380px] flex flex-col">
            <TranscriptFeed
              transcripts={transcripts}
              agentStatus={agentStatus}
              activeCallId={activeCallId}
            />
          </div>
        </div>

        {/* RIGHT COLUMN: AUTONOMOUS CRM BANT LEAD SCORECARD (5 Cols) */}
        <div className="lg:col-span-5 flex flex-col gap-6">
          <LeadAnalyticsCard liveLead={liveLead} />

          {/* QUICK HELP / TESTING TIPS */}
          <div className="rounded-2xl bg-slate-900/60 border border-slate-800/80 p-5 text-xs text-slate-400 space-y-2">
            <h4 className="font-semibold text-slate-200 text-sm">
              💡 Sales Test Scenarios
            </h4>
            <p>
              • <strong className="text-slate-300">Test Budget:</strong> Mention
              your budget (e.g., <em>"We have around $30,000 for this"</em>) to
              watch the CRM score increase.
            </p>
            <p>
              • <strong className="text-slate-300">Test Objections:</strong> Say{' '}
              <em>"Your price is too expensive"</em> to test Llama-3.3's
              objection handling and watch the objection badge trigger.
            </p>
            <p>
              • <strong className="text-slate-300">Test Silence:</strong> Notice
              how your RMS VAD noise gate prevents Whisper from hallucinating
              words when you stay quiet.
            </p>
          </div>
        </div>
      </main>

      {/* KNOWLEDGE BASE MODAL */}
      <BusinessConfigModal
        isOpen={isKbModalOpen}
        onClose={() => setIsKbModalOpen(false)}
        onSaveSuccess={(savedProfile) => setBusinessProfile(savedProfile)}
        currentProfile={businessProfile}
      />
    </div>
  );
};