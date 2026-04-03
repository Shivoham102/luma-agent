"use client";

import type { LumaEvent } from "@/lib/api";

interface RegistrationModalProps {
  event: LumaEvent | null;
  hasConflict: boolean;
  isOpen: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function RegistrationModal({
  event,
  hasConflict,
  isOpen,
  onConfirm,
  onCancel,
}: RegistrationModalProps) {
  if (!isOpen || !event) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl dark:bg-zinc-900">
        <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
          Confirm Registration
        </h2>
        <div className="mt-4 space-y-2 text-sm text-zinc-600 dark:text-zinc-400">
          <p><strong>Event:</strong> {event.name}</p>
          <p><strong>Date:</strong> {new Date(event.start_time).toLocaleString()}</p>
          <p><strong>Location:</strong> {event.location}</p>
        </div>
        {hasConflict && (
          <div className="mt-4 rounded-lg bg-amber-50 p-3 text-sm text-amber-800 dark:bg-amber-950 dark:text-amber-200">
            You have a scheduling conflict. You can still register if you want.
          </div>
        )}
        <div className="mt-6 flex gap-3 justify-end">
          <button
            onClick={onCancel}
            className="rounded-lg border border-zinc-300 px-4 py-2 text-sm text-zinc-700 hover:bg-zinc-50 dark:border-zinc-600 dark:text-zinc-300 dark:hover:bg-zinc-800"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700"
          >
            Register
          </button>
        </div>
      </div>
    </div>
  );
}
