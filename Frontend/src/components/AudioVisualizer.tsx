import React, { useEffect, useRef } from "react";

interface AudioVisualizerProps {
  getFrequencyData: () => Uint8Array | null;
  isRecording: boolean;
  agentState: "connected" | "speaking" | "listening" | "processing" | "idle";
}

export const AudioVisualizer: React.FC<AudioVisualizerProps> = ({
  getFrequencyData,
  isRecording,
  agentState,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const draw = () => {
      animationFrameRef.current = requestAnimationFrame(draw);

      const width = canvas.width;
      const height = canvas.height;
      ctx.clearRect(0, 0, width, height);

      const frequencyData = getFrequencyData();

      if (!isRecording || !frequencyData) {
        ctx.beginPath();
        ctx.moveTo(0, height / 2);
        ctx.lineTo(width, height / 2);
        ctx.strokeStyle = "rgba(100, 116, 139, 0.3)"; // slate-500
        ctx.lineWidth = 2;
        ctx.stroke();
        return;
      }

      const barCount = 32;
      const step = Math.floor(frequencyData.length / barCount);
      const barWidth = width / barCount - 4;

      for (let i = 0; i < barCount; i++) {
        const dataIndex = i * step;
        const value = frequencyData[dataIndex] || 0;
        const normalizedValue = value / 255;
        const barHeight = Math.max(4, normalizedValue * (height - 16));

        const x = i * (barWidth + 4) + 2;
        const y = (height - barHeight) / 2;

        if (agentState === "speaking") {
          ctx.fillStyle = "rgba(99, 102, 241, 0.9)"; 
        } else if (agentState === "processing") {
          ctx.fillStyle = "rgba(245, 158, 11, 0.9)";
        } else {
          ctx.fillStyle = "rgba(16, 185, 129, 0.9)";
        }

        ctx.beginPath();
        ctx.roundRect(x, y, barWidth, barHeight, 4);
        ctx.fill();
      }
    };

    draw();

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [getFrequencyData, isRecording, agentState]);

  return (
    <div className="relative w-full h-24 bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden flex items-center justify-center p-2 shadow-inner">
      <canvas
        ref={canvasRef}
        width={400}
        height={80}
        className="w-full h-full"
        aria-label="Real-time audio frequency visualizer"
      />
    </div>
  );
};
