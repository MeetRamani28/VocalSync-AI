import { useState, useRef, useCallback, useEffect } from 'react';

export interface UseAudioRecorderReturn {
  isRecording: boolean;
  startRecording: () => Promise<void>;
  stopRecording: () => void;
  getFrequencyData: () => Uint8Array | null;
  error: string | null;
}

interface UseAudioRecorderProps {
  onAudioChunkAvailable: (chunk: Blob) => void;
  timeSliceMs?: number;
}

export const useAudioRecorder = ({
  onAudioChunkAvailable,
  timeSliceMs = 250,
}: UseAudioRecorderProps): UseAudioRecorderReturn => {
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const mediaStreamRef = useRef<MediaStream | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const frequencyDataRef = useRef<Uint8Array | null>(null);

  const cleanupResources = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }
    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      audioContextRef.current.close().catch(console.error);
      audioContextRef.current = null;
    }
    analyserRef.current = null;
    frequencyDataRef.current = null;
    setIsRecording(false);
  }, []);

  const startRecording = useCallback(async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 16000, 
        },
        video: false,
      });

      mediaStreamRef.current = stream;

      const audioContext = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
      const sourceNode = audioContext.createMediaStreamSource(stream);
      const analyserNode = audioContext.createAnalyser();

      analyserNode.fftSize = 256;
      analyserNode.smoothingTimeConstant = 0.8;
      sourceNode.connect(analyserNode);

      audioContextRef.current = audioContext;
      analyserRef.current = analyserNode;
      frequencyDataRef.current = new Uint8Array(analyserNode.frequencyBinCount);

      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm';

      const recorder = new MediaRecorder(stream, { mimeType });

      recorder.ondataavailable = (event: BlobEvent) => {
        if (event.data && event.data.size > 0) {
          onAudioChunkAvailable(event.data);
        }
      };

      recorder.onerror = (event: Event) => {
        console.error('MediaRecorder error:', event);
        setError('An error occurred during audio capture.');
        cleanupResources();
      };

      recorder.start(timeSliceMs);
      mediaRecorderRef.current = recorder;
      setIsRecording(true);
    } catch (err) {
      console.error('Failed to access microphone:', err);
      setError('Microphone permission denied or device unavailable.');
      cleanupResources();
    }
  }, [cleanupResources, onAudioChunkAvailable, timeSliceMs]);

  const stopRecording = useCallback(() => {
    cleanupResources();
  }, [cleanupResources]);

  const getFrequencyData = useCallback((): Uint8Array | null => {
    if (analyserRef.current && frequencyDataRef.current) {
      analyserRef.current.getByteFrequencyData(frequencyDataRef.current);
      return frequencyDataRef.current;
    }
    return null;
  }, []);

  useEffect(() => {
    return () => {
      cleanupResources();
    };
  }, [cleanupResources]);

  return {
    isRecording,
    startRecording,
    stopRecording,
    getFrequencyData,
    error,
  };
};