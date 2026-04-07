"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import {
  Room,
  RoomEvent,
  Track,
  RemoteTrack,
  RemoteParticipant,
  ConnectionState,
} from "livekit-client";
import type { LumaEvent } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Phase = "idle" | "connecting" | "connected";

export default function Home() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [events, setEvents] = useState<LumaEvent[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [showEmailModal, setShowEmailModal] = useState(false);
  const [email, setEmail] = useState("");
  const [agentSpeaking, setAgentSpeaking] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [requestedEvents, setRequestedEvents] = useState<Set<string>>(
    new Set()
  );

  const roomRef = useRef<Room | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    return () => {
      roomRef.current?.disconnect();
    };
  }, []);

  const connectToRoom = useCallback(async () => {
    if (phase !== "idle") return;
    setPhase("connecting");
    try {
      const res = await fetch(`${API_BASE}/token`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const { serverUrl, participantToken } = await res.json();

      const room = new Room();
      roomRef.current = room;

      room.on(RoomEvent.ConnectionStateChanged, (state: ConnectionState) => {
        if (state === ConnectionState.Connected) {
          setPhase("connected");
        } else if (state === ConnectionState.Disconnected) {
          setAgentSpeaking(false);
          setIsMuted(false);
          setPhase("idle");
        }
      });

      room.on(
        RoomEvent.TrackSubscribed,
        (track: RemoteTrack, _pub, _participant: RemoteParticipant) => {
          if (track.kind === Track.Kind.Audio) {
            const el = track.attach();
            audioRef.current = el as HTMLAudioElement;
            el.play().catch(() => {});
          }
        }
      );

      room.on(RoomEvent.TrackUnsubscribed, (track: RemoteTrack) => {
        track.detach();
      });

      room.on(RoomEvent.ActiveSpeakersChanged, (speakers) => {
        setAgentSpeaking(speakers.some((s) => !s.isLocal));
      });

      room.on(RoomEvent.DataReceived, (payload, participant) => {
        if (participant?.isLocal) return;
        try {
          const msg = JSON.parse(new TextDecoder().decode(payload));
          if (msg.type === "request_email") {
            setShowEmailModal(true);
          } else if (msg.type === "events") {
            setEvents(msg.data);
            setSidebarOpen(true);
          } else if (msg.type === "registration" && msg.data?.success) {
            setRequestedEvents(
              (prev) => new Set(prev).add(msg.data.event_id || "")
            );
          }
        } catch {
          /* ignore non-JSON */
        }
      });

      await room.connect(serverUrl, participantToken);
      await room.localParticipant.setMicrophoneEnabled(true);
    } catch (error) {
      console.error("Failed to connect:", error);
      setPhase("idle");
    }
  }, [phase]);

  const handleOrbTap = useCallback(async () => {
    if (phase === "idle") {
      connectToRoom();
    } else if (phase === "connected") {
      const room = roomRef.current;
      if (!room) return;

      // If the agent is currently speaking, immediately silence its audio
      if (agentSpeaking) {
        audioRef.current?.pause();
      }

      // Toggle mic mute
      const currentMicEnabled =
        room.localParticipant.isMicrophoneEnabled;
      await room.localParticipant.setMicrophoneEnabled(!currentMicEnabled);
      setIsMuted(currentMicEnabled);
    }
  }, [phase, agentSpeaking, connectToRoom]);

  const endSession = useCallback(() => {
    roomRef.current?.disconnect();
    roomRef.current = null;
    setSidebarOpen(false);
    setAgentSpeaking(false);
    setIsMuted(false);
    setPhase("idle");
    setEvents([]);
    setRequestedEvents(new Set());
    setShowEmailModal(false);
  }, []);

  const handleEmailSubmit = useCallback(() => {
    if (!email || !roomRef.current) return;
    roomRef.current.localParticipant.publishData(
      new TextEncoder().encode(JSON.stringify({ type: "email", email })),
      { topic: "user_input" }
    );
    setShowEmailModal(false);
  }, [email]);

  return (
    <div className="relative flex h-screen w-screen overflow-hidden bg-[#0a0a0a]">
      {/* Main agent area */}
      <div
        className={`flex flex-1 flex-col items-center justify-center transition-all duration-300 ${
          sidebarOpen ? "mr-80" : ""
        }`}
      >
        {/* Orb */}
        <button
          onClick={handleOrbTap}
          disabled={phase === "connecting"}
          className="group relative flex items-center justify-center focus:outline-none disabled:cursor-default"
        >
          <div
            className={`absolute h-44 w-44 rounded-full transition-all duration-700 ${
              agentSpeaking
                ? "orb-ping bg-blue-500/20"
                : phase === "connected"
                  ? "orb-pulse bg-blue-500/10"
                  : "bg-transparent"
            }`}
          />
          <div
            className={`absolute h-32 w-32 rounded-full transition-all duration-500 ${
              agentSpeaking
                ? "scale-110 bg-blue-500/15"
                : phase === "connected"
                  ? "scale-100 bg-blue-500/10"
                  : "scale-90 bg-transparent"
            }`}
          />
          <div
            className={`relative h-24 w-24 rounded-full transition-all duration-300 ${
              agentSpeaking
                ? "bg-blue-500 shadow-[0_0_60px_rgba(59,130,246,0.6)]"
                : phase === "connected"
                  ? "bg-blue-600 shadow-[0_0_30px_rgba(59,130,246,0.3)]"
                  : phase === "connecting"
                    ? "animate-pulse bg-blue-700 shadow-[0_0_20px_rgba(59,130,246,0.2)]"
                    : "bg-zinc-700 shadow-lg group-hover:bg-zinc-600"
            }`}
          />
        </button>

        <p className="mt-8 text-sm font-medium text-zinc-400">
          {agentSpeaking
            ? "Speaking..."
            : phase === "connected"
              ? isMuted
                ? "Muted"
                : "Listening..."
              : phase === "connecting"
                ? "Connecting..."
                : "Tap to start"}
        </p>
        <p className="mt-2 text-xs text-zinc-600">
          {phase === "connected"
            ? "Tap orb to mute/unmute"
            : "Lumi — Your Luma Event Assistant"}
        </p>
        {phase === "connected" && (
          <button
            onClick={endSession}
            className="mt-4 rounded-lg border border-zinc-700 px-4 py-1.5 text-xs font-medium text-zinc-400 transition-colors hover:border-zinc-500 hover:text-zinc-200"
          >
            End Session
          </button>
        )}
      </div>

      {/* Email modal overlay */}
      {showEmailModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-sm rounded-2xl border border-zinc-700 bg-zinc-900 p-6 shadow-2xl">
            <h2 className="text-lg font-semibold text-zinc-100">
              Enter your email
            </h2>
            <p className="mt-1 text-sm text-zinc-400">
              We&apos;ll use this to help you register for events on Luma.
            </p>
            <input
              type="email"
              autoFocus
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleEmailSubmit()}
              className="mt-4 w-full rounded-lg border border-zinc-600 bg-zinc-800 px-4 py-2.5 text-sm text-zinc-100 placeholder:text-zinc-500 focus:border-blue-500 focus:outline-none"
            />
            <div className="mt-4 flex gap-3">
              <button
                onClick={handleEmailSubmit}
                disabled={!email}
                className="w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-40"
              >
                Continue
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Event sidebar */}
      <div
        className={`fixed right-0 top-0 h-full w-80 border-l border-zinc-800 bg-zinc-900/95 backdrop-blur transition-transform duration-300 ease-in-out ${
          sidebarOpen ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between border-b border-zinc-800 px-4 py-4">
          <h2 className="text-sm font-semibold text-zinc-200">
            Upcoming Events
          </h2>
          <button
            onClick={() => setSidebarOpen(false)}
            className="text-zinc-500 hover:text-zinc-300"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M18 6L6 18" />
              <path d="M6 6l12 12" />
            </svg>
          </button>
        </div>
        <ul className="h-[calc(100%-57px)] space-y-3 overflow-y-auto p-4">
          {events.length === 0 ? (
            <li className="text-sm text-zinc-500">No events found.</li>
          ) : (
            events.map((event, i) => (
              <li
                key={event.id}
                className="rounded-lg border border-zinc-800 p-3 transition-colors hover:border-zinc-600"
              >
                <h3 className="text-sm font-medium text-zinc-100">
                  {i + 1}. {event.name}
                </h3>
                <p className="mt-1 line-clamp-2 text-xs text-zinc-400">
                  {event.description}
                </p>
                <div className="mt-2 flex gap-3 text-xs text-zinc-500">
                  <span>
                    {new Date(event.start_time).toLocaleDateString()}
                  </span>
                  <span>{event.location}</span>
                </div>
                {event.url && (
                  <a
                    href={event.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-2 inline-block rounded-md bg-blue-600 px-3 py-1 text-xs font-medium text-white hover:bg-blue-500"
                  >
                    Register on Luma
                  </a>
                )}
                {requestedEvents.has(event.id) && (
                  <div className="mt-1">
                    <span className="rounded-full bg-green-500/20 px-2 py-0.5 text-xs text-green-400">
                      Link opened
                    </span>
                  </div>
                )}
              </li>
            ))
          )}
        </ul>
      </div>

      {/* Sidebar reopen toggle */}
      {!sidebarOpen && events.length > 0 && phase === "connected" && (
        <button
          onClick={() => setSidebarOpen(true)}
          className="fixed right-4 top-1/2 -translate-y-1/2 rounded-full border border-zinc-700 bg-zinc-800 p-3 text-zinc-400 shadow-lg hover:text-zinc-200"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M15 18l-6-6 6-6" />
          </svg>
        </button>
      )}
    </div>
  );
}
