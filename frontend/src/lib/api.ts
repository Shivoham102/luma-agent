const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface LumaEvent {
  id: string;
  name: string;
  description: string;
  start_time: string;
  end_time: string;
  location: string;
  category: string;
  host: string;
  url: string;
}

export interface ConversationMessage {
  role: "agent" | "user";
  content: string;
  timestamp: string;
}

export interface RegistrationResult {
  success: boolean;
  event_id: string;
  message: string;
}

export async function fetchEvents(email: string): Promise<LumaEvent[]> {
  const res = await fetch(`${API_BASE_URL}/api/events?email=${encodeURIComponent(email)}`);
  if (!res.ok) throw new Error("Failed to fetch events");
  return res.json();
}

export async function checkConflict(email: string, eventId: string): Promise<{ has_conflict: boolean; conflicting_event?: LumaEvent }> {
  const res = await fetch(`${API_BASE_URL}/api/conflict?email=${encodeURIComponent(email)}&event_id=${encodeURIComponent(eventId)}`);
  if (!res.ok) throw new Error("Failed to check conflict");
  return res.json();
}

export async function registerForEvent(email: string, eventId: string): Promise<RegistrationResult> {
  const res = await fetch(`${API_BASE_URL}/api/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, event_id: eventId }),
  });
  if (!res.ok) throw new Error("Failed to register");
  return res.json();
}

export async function getUserCalendar(email: string): Promise<LumaEvent[]> {
  const res = await fetch(`${API_BASE_URL}/api/calendar?email=${encodeURIComponent(email)}`);
  if (!res.ok) throw new Error("Failed to fetch calendar");
  return res.json();
}
