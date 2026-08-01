import { useState, useRef, useCallback, useEffect } from 'react';
import type {
    WSMessage,
    TranscriptMessage,
    LeadProfile,
    AgentStatePayload,
} from '../types';

export interface UseWebSocketVoiceReturn {
  isConnected: boolean;
  agentState: AgentStatePayload['status'];
  transcripts: TranscriptMessage[];
  latestToken: string;
  qualifiedLead: LeadProfile | null;
  errorMessage: string | null;
  connect: (callId: string) => void;
  disconnect: () => void;
  sendAudioChunk: (blob: Blob) => Promise<void>;
  clearError: () => void;
}

/**
 * Real-time WebSocket voice pipeline hook.
 * Manages bidirectional audio/text streaming and gapless Edge-TTS playback.
 */
export const useWebSocketVoice = (): UseWebSocketVoiceReturn => {
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [agentState, setAgentState] = useState<AgentStatePayload['status']>('idle');
  const [transcripts, setTranscripts] = useState<TranscriptMessage[]>([]);
  const [latestToken, setLatestToken] = useState<string>('');
  const [qualifiedLead, setQualifiedLead] = useState<LeadProfile | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const playbackContextRef = useRef<AudioContext | null>(null);
  const nextPlayTimeRef = useRef<number>(0);

  /**
   * Initializes or retrieves the playback Web Audio Context.
   */
  const getPlaybackContext = useCallback((): AudioContext => {
    if (!playbackContextRef.current || playbackContextRef.current.state === 'closed') {
      const AudioCtx =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      playbackContextRef.current = new AudioCtx();
      nextPlayTimeRef.current = playbackContextRef.current.currentTime;
    }
    return playbackContextRef.current;
  }, []);

  /**
   * Decodes incoming binary Edge-TTS chunks and schedules them for gapless
   * playback in the browser audio thread.
   */
  const handleBinaryAudioPlayback = useCallback(
    async (audioBufferData: ArrayBuffer) => {
      try {
        const audioCtx = getPlaybackContext();
        if (audioCtx.state === 'suspended') {
          await audioCtx.resume();
        }

        // Copy buffer to prevent detachment bugs during decodeAudioData
        const bufferCopy = audioBufferData.slice(0);
        const decodedBuffer = await audioCtx.decodeAudioData(bufferCopy);

        const sourceNode = audioCtx.createBufferSource();
        sourceNode.buffer = decodedBuffer;
        sourceNode.connect(audioCtx.destination);

        // Calculate schedule time to prevent stuttering between TTS sentence chunks
        const currentTime = audioCtx.currentTime;
        const scheduleTime = Math.max(currentTime, nextPlayTimeRef.current);
        
        sourceNode.start(scheduleTime);
        nextPlayTimeRef.current = scheduleTime + decodedBuffer.duration;
      } catch (err) {
        console.error('Error decoding/playing TTS binary audio chunk:', err);
      }
    },
    [getPlaybackContext]
  );

  /**
   * Parses and handles structured JSON events received from FastAPI.
   */
  const handleTextMessage = useCallback((rawText: string) => {
    try {
      const message = JSON.parse(rawText) as WSMessage;

      switch (message.event) {
        case 'agent_state':
          setAgentState(message.data.status);
          break;

        case 'transcript_update':
          setTranscripts((prev) => [
            ...prev,
            {
              role: message.data.role,
              content: message.data.content,
              sentiment: message.data.sentiment,
              timestamp: new Date().toISOString(),
            },
          ]);
          setLatestToken(''); // Reset streaming token buffer after turn completion
          break;

        case 'text_token':
          setLatestToken((prev) => prev + message.data.token);
          break;

        case 'lead_qualified':
          setQualifiedLead(message.data);
          break;

        case 'error':
          setErrorMessage(message.data.error);
          setAgentState('idle');
          break;

        default:
          break;
      }
    } catch (err) {
      console.error('Failed to parse incoming WebSocket JSON payload:', err);
    }
  }, []);

  /**
   * Opens the WebSocket connection to the voice agent server.
   */
  const connect = useCallback(
    (callId: string) => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        return;
      }

      // Determine ws protocol based on location (wss: for https:, ws: for http:)
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      const wsUrl = `${protocol}//${host}/ws/call/${callId}`;

      const ws = new WebSocket(wsUrl);
      ws.binaryType = 'arraybuffer'; // Enforce ArrayBuffer for incoming binary Edge-TTS audio

      ws.onopen = () => {
        setIsConnected(true);
        setErrorMessage(null);
        setAgentState('connected');
      };

      ws.onmessage = (event: MessageEvent) => {
        if (event.data instanceof ArrayBuffer) {
          void handleBinaryAudioPlayback(event.data);
        } else if (typeof event.data === 'string') {
          handleTextMessage(event.data);
        }
      };

      ws.onerror = () => {
        setErrorMessage('WebSocket connection error occurred.');
        setIsConnected(false);
        setAgentState('idle');
      };

      ws.onclose = () => {
        setIsConnected(false);
        setAgentState('idle');
        wsRef.current = null;
      };

      wsRef.current = ws;
    },
    [handleBinaryAudioPlayback, handleTextMessage]
  );

  /**
   * Closes the active WebSocket connection and audio playback contexts.
   */
  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    if (playbackContextRef.current) {
      playbackContextRef.current.close().catch(console.error);
      playbackContextRef.current = null;
    }
    setIsConnected(false);
    setAgentState('idle');
  }, []);

  /**
   * Transmits a recorded WebM audio chunk as binary data to FastAPI.
   */
  const sendAudioChunk = useCallback(async (blob: Blob) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      const arrayBuffer = await blob.arrayBuffer();
      wsRef.current.send(arrayBuffer);
    }
  }, []);

  const clearError = useCallback(() => setErrorMessage(null), []);

  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    isConnected,
    agentState,
    transcripts,
    latestToken,
    qualifiedLead,
    errorMessage,
    connect,
    disconnect,
    sendAudioChunk,
    clearError,
  };
};