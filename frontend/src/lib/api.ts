const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface LumaEvent {
  id: string;
  name: string;
  description: string;
  start_time: string;
  end_time: string;
  location: string;
  url: string;
  cover_url?: string;
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

/**
 * Get the JWT token from localStorage (client-side only).
 */
export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

/**
 * Remove the JWT token and redirect to /login.
 */
export function logout(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem("token");
  window.location.href = "/login";
}

/**
 * Build headers including the Authorization bearer token when available.
 */
function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = { ...extra };
  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

export async function fetchEvents(email: string): Promise<LumaEvent[]> {
  const res = await fetch(
    `${API_BASE_URL}/api/events?email=${encodeURIComponent(email)}`,
    { headers: authHeaders() },
  );
  if (!res.ok) throw new Error("Failed to fetch events");
  return res.json();
}

export async function checkConflict(
  email: string,
  eventId: string,
): Promise<{ has_conflict: boolean; conflicting_event?: LumaEvent }> {
  const res = await fetch(
    `${API_BASE_URL}/api/conflict?email=${encodeURIComponent(email)}&event_id=${encodeURIComponent(eventId)}`,
    { headers: authHeaders() },
  );
  if (!res.ok) throw new Error("Failed to check conflict");
  return res.json();
}

export async function registerForEvent(
  email: string,
  eventId: string,
): Promise<RegistrationResult> {
  const res = await fetch(`${API_BASE_URL}/api/register`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ email, event_id: eventId }),
  });
  if (!res.ok) throw new Error("Failed to register");
  return res.json();
}

export async function getUserCalendar(email: string): Promise<LumaEvent[]> {
  const res = await fetch(
    `${API_BASE_URL}/api/calendar?email=${encodeURIComponent(email)}`,
    { headers: authHeaders() },
  );
  if (!res.ok) throw new Error("Failed to fetch calendar");
  return res.json();
}
