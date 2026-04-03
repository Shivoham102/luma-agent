"use client";

import { useState } from "react";

export type VoiceStatus = "idle" | "listening" | "processing" | "speaking";

interface VoiceAgentProps {
  onTranscript: (text: string) => void;
  onStatusChange: (status: VoiceStatus) => void;
}

export default function VoiceAgent({ onTranscript, onStatusChange }: VoiceAgentProps) {
  const [status, setStatus] = useState<VoiceStatus>("idle");

  function handleToggle() {
    const next = status === "idle" ? "listening" : "idle";
    setStatus(next);
    onStatusChange(next);
    // TODO: connect to ElevenLabs Conversational AI SDK
  }

  return (
    <div className="flex flex-col items-center gap-4">
      <button
        onClick={handleToggle}
        className={`h-20 w-20 rounded-full text-white font-semibold transition-colors ${
          status === "idle"
            ? "bg-blue-600 hover:bg-blue-700"
            : "bg-red-500 hover:bg-red-600"
        }`}
      >
        {status === "idle" ? "Start" : "Stop"}
      </button>
      <span className="text-sm text-zinc-500 capitalize">{status}</span>
    </div>
  );
}
