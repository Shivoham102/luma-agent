"use client";

import type { LumaEvent } from "@/lib/api";

interface CalendarViewProps {
  registrations: LumaEvent[];
}

export default function CalendarView({ registrations }: CalendarViewProps) {
  if (registrations.length === 0) {
    return (
      <p className="text-sm text-zinc-500">No upcoming registrations.</p>
    );
  }

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
        Your Registered Events
      </h3>
      <ul className="space-y-2">
        {registrations.map((event) => (
          <li
            key={event.id}
            className="flex items-center justify-between rounded-lg border border-zinc-200 p-3 dark:border-zinc-700"
          >
            <div>
              <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">{event.name}</p>
              <p className="text-xs text-zinc-500">{new Date(event.start_time).toLocaleString()}</p>
            </div>
            <span className="text-xs rounded-full bg-green-100 px-2 py-1 text-green-700 dark:bg-green-900 dark:text-green-300">
              Registered
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
