"use client";

import type { LumaEvent } from "@/lib/api";

interface EventListProps {
  events: LumaEvent[];
  onSelect: (event: LumaEvent) => void;
  selectedEventId?: string;
}

export default function EventList({ events, onSelect, selectedEventId }: EventListProps) {
  if (events.length === 0) {
    return <p className="text-zinc-500 text-sm">No events to display.</p>;
  }

  return (
    <ul className="flex flex-col gap-3">
      {events.map((event, index) => (
        <li
          key={event.id}
          onClick={() => onSelect(event)}
          className={`cursor-pointer rounded-lg border p-4 transition-colors ${
            selectedEventId === event.id
              ? "border-blue-500 bg-blue-50 dark:bg-blue-950"
              : "border-zinc-200 hover:border-zinc-400 dark:border-zinc-700"
          }`}
        >
          <div className="flex items-baseline justify-between">
            <h3 className="font-medium text-zinc-900 dark:text-zinc-100">
              {index + 1}. {event.name}
            </h3>
            <span className="text-xs text-zinc-500">{event.location}</span>
          </div>
          <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">{event.description}</p>
          <div className="mt-2 flex gap-4 text-xs text-zinc-500">
            <span>{new Date(event.start_time).toLocaleString()}</span>
            <span>{event.location}</span>
          </div>
        </li>
      ))}
    </ul>
  );
}
