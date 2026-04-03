"use client";

import { useState } from "react";
import VoiceAgent, { type VoiceStatus } from "@/components/VoiceAgent";
import EventList from "@/components/EventList";
import ConversationPanel from "@/components/ConversationPanel";
import RegistrationModal from "@/components/RegistrationModal";
import CalendarView from "@/components/CalendarView";
import type { LumaEvent, ConversationMessage } from "@/lib/api";

export default function Home() {
  const [voiceStatus, setVoiceStatus] = useState<VoiceStatus>("idle");
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [events, setEvents] = useState<LumaEvent[]>([]);
  const [registrations, setRegistrations] = useState<LumaEvent[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<LumaEvent | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [hasConflict, setHasConflict] = useState(false);

  function handleEventSelect(event: LumaEvent) {
    setSelectedEvent(event);
    setShowModal(true);
    // TODO: call checkConflict API and set hasConflict
  }

  function handleConfirmRegistration() {
    // TODO: call registerForEvent API
    setShowModal(false);
    setSelectedEvent(null);
  }

  function handleCancelRegistration() {
    setShowModal(false);
    setSelectedEvent(null);
  }

  return (
    <div className="flex flex-col min-h-screen bg-zinc-50 dark:bg-zinc-950">
      <header className="border-b border-zinc-200 dark:border-zinc-800 px-6 py-4">
        <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
          Luma Voice Agent
        </h1>
        <p className="text-sm text-zinc-500">
          Discover and register for events hands-free
        </p>
      </header>

      <main className="flex flex-1 flex-col lg:flex-row gap-6 p-6 max-w-7xl mx-auto w-full">
        {/* Left column: Voice + Conversation */}
        <section className="flex flex-col gap-6 lg:w-1/2">
          <div className="rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900">
            <h2 className="mb-4 text-sm font-medium text-zinc-700 dark:text-zinc-300">
              Voice Control
            </h2>
            <VoiceAgent
              onTranscript={(text) =>
                setMessages((prev) => [
                  ...prev,
                  { role: "user", content: text, timestamp: new Date().toISOString() },
                ])
              }
              onStatusChange={setVoiceStatus}
            />
          </div>

          <div className="rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900 flex-1">
            <h2 className="mb-4 text-sm font-medium text-zinc-700 dark:text-zinc-300">
              Conversation
            </h2>
            <ConversationPanel messages={messages} />
          </div>
        </section>

        {/* Right column: Events + Calendar */}
        <section className="flex flex-col gap-6 lg:w-1/2">
          <div className="rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900">
            <h2 className="mb-4 text-sm font-medium text-zinc-700 dark:text-zinc-300">
              Upcoming Events
            </h2>
            <EventList
              events={events}
              onSelect={handleEventSelect}
              selectedEventId={selectedEvent?.id}
            />
          </div>

          <div className="rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900">
            <h2 className="mb-4 text-sm font-medium text-zinc-700 dark:text-zinc-300">
              My Calendar
            </h2>
            <CalendarView registrations={registrations} />
          </div>
        </section>
      </main>

      <RegistrationModal
        event={selectedEvent}
        hasConflict={hasConflict}
        isOpen={showModal}
        onConfirm={handleConfirmRegistration}
        onCancel={handleCancelRegistration}
      />
    </div>
  );
}
