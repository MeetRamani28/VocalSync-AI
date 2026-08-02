import { useState, useRef, useCallback, useEffect } from 'react';
import { WSMessage, TranscriptMessage, LeadProfile } from '../types';

export interface UseWebSocketVoiceReturn {
  isConnected: boolean;
  agentStatus: string;
  transcripts: TranscriptMessage[];
  liveLead: LeadProfile | null;
  connectWebSocket: (callId: string, businessId?: string) => void;
  disconnectWebSocket: () => void;
  sendAudioChunk: (blob: Blob) => Promise<void>;
  error: string | null;
}

export const useWebSocketVoice = (): UseWebSocketVoiceReturn => {
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [agentStatus, setAgentStatus] = useState<string>('idle');
  const [transcripts, setTranscripts] = useState<TranscriptMessage[]>([]);
  const [liveLead, setLiveLead] = useState<LeadProfile | null>(null);
  const [error, setError] = useState<string | null>(null);

  const socketRef = useRef<WebSocket | null>(null);
  const audioQueueRef = useRef<ArrayBuffer[]>([]);
  const isPlayingRef = useRef<boolean>(false);
  const audioContextRef = useRef<AudioContext | null>(null);

  const playNextAudioInQueue = useCallback(async () => {
    if (isPlayingRef.current || audioQueueRef.current.length === 0) {
      return;
    }

    isPlayingRef.current = true;
    const nextChunk = audioQueueRef.current.shift();

    if (!nextChunk) {
      isPlayingRef.current = false;
      return;
    }

    try {
      if (!audioContextRef.current || audioContextRef.current.state === 'closed') {
        const AudioCtx =
          window.AudioContext ||
          (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
        audioContextRef.current = new AudioCtx();
      }

      const audioContext = audioContextRef.current;
      const audioBuffer = await audioContext.decodeAudioData(nextChunk);
      const sourceNode = audioContext.createBufferSource();

      sourceNode.buffer = audioBuffer;
      sourceNode.connect(audioContext.destination);

      sourceNode.onended = () => {
        isPlayingRef.current = false;
        playNextAudioInQueue();
      };

      sourceNode.start(0);
    } catch (err) {
      console.error('Failed to decode or play incoming audio buffer:', err);
      isPlayingRef.current = false;
      playNextAudioInQueue();
    }
  }, []);

  const handleWebSocketMessage = useCallback(
    (event: MessageEvent) => {
      if (event.data instanceof Blob || event.data instanceof ArrayBuffer) {
        let bufferPromise: Promise<ArrayBuffer>;
        if (event.data instanceof Blob) {
          bufferPromise = event.data.arrayBuffer();
        } else {
          bufferPromise = Promise.resolve(event.data);
        }

        bufferPromise
          .then((buffer) => {
            audioQueueRef.current.push(buffer);
            playNextAudioInQueue();
          })
          .catch((err) => console.error('Error reading WebSocket audio blob:', err));
        return;
      }

      try {
        const parsed: WSMessage = JSON.parse(event.data);
        const { event: eventType, data } = parsed;

        switch (eventType) {
          case 'agent_state':
            setAgentStatus(data.status || 'connected');
            break;

          case 'transcript_update':
            setTranscripts((prev) => [
              ...prev,
              {
                role: data.role,
                content: data.content,
                sentiment: data.sentiment || 'Neutral',
                timestamp: new Date().toISOString(),
              },
            ]);
            setAgentStatus('listening');
            break;

          case 'lead_qualified':
            setLiveLead(data as LeadProfile);
            break;

          case 'error':
            setError(data.error || 'A voice processing error occurred.');
            break;

          default:
            break;
        }
      } catch (err) {
        console.error('Error parsing WebSocket JSON payload:', err);
      }
    },
    [playNextAudioInQueue]
  );

  const connectWebSocket = useCallback(
    (callId: string, businessId = 'default_business') => {
      setError(null);
      setTranscripts([]);
      setLiveLead(null);
      audioQueueRef.current = [];

      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsHost = import.meta.env.VITE_WS_BASE_URL || `${wsProtocol}//localhost:8000`;
      const wsUrl = `${wsHost}/ws/call/${callId}?business_id=${encodeURIComponent(businessId)}`;

      try {
        const ws = new WebSocket(wsUrl);
        ws.binaryType = 'arraybuffer';

        ws.onopen = () => {
          setIsConnected(true);
          setAgentStatus('connected');
        };

        ws.onmessage = handleWebSocketMessage;

        ws.onerror = () => {
          setError('WebSocket connection encountered an error.');
        };

        ws.onclose = () => {
          setIsConnected(false);
          setAgentStatus('idle');
          socketRef.current = null;
        };

        socketRef.current = ws;
      } catch (err) {
        console.error('Failed to establish WebSocket connection:', err);
        setError('Unable to connect to the voice server.');
      }
    },
    [handleWebSocketMessage]
  );

  const disconnectWebSocket = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.close();
      socketRef.current = null;
    }
    setIsConnected(false);
    setAgentStatus('idle');
    audioQueueRef.current = [];
    isPlayingRef.current = false;
  }, []);

  const sendAudioChunk = useCallback(async (blob: Blob) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      try {
        const arrayBuffer = await blob.arrayBuffer();
        socketRef.current.send(arrayBuffer);
      } catch (err) {
        console.error('Error transmitting binary audio chunk over WebSocket:', err);
      }
    }
  }, []);

  useEffect(() => {
    return () => {
      disconnectWebSocket();
    };
  }, [disconnectWebSocket]);

  return {
    isConnected,
    agentStatus,
    transcripts,
    liveLead,
    connectWebSocket,
    disconnectWebSocket,
    sendAudioChunk,
    error,
  };
};