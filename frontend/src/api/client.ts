import { friendlyApiError, REQUEST_TIMEOUT } from "@/lib/userMessages";
import type {
  Analytics,
  CaseDetail,
  CaseSummary,
  WebChatSession,
  OverrideAction,
  OverrideResponse,
} from "./types";

/**
 * API base URL.
 * - Dev default: "" → same-origin + Vite proxy (no CORS).
 * - Set VITE_API_URL=http://127.0.0.1:8000 only if you open the app at 127.0.0.1:5173.
 */
function resolveApiBase(): string {
  const fromEnv = import.meta.env.VITE_API_URL;
  if (fromEnv !== undefined && fromEnv !== "") {
    return fromEnv.replace(/\/$/, "");
  }
  return "";
}

const API_BASE = resolveApiBase();
const REQUEST_TIMEOUT_MS = 15_000;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const res = await fetch(url, {
      ...init,
      signal: controller.signal,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(friendlyApiError(text || `${res.status} ${res.statusText}`));
    }
    return res.json() as Promise<T>;
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") {
      throw new Error(REQUEST_TIMEOUT);
    }
    throw e;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export const api = {
  baseUrl: API_BASE || "(vite proxy → :8000)",

  health: () => request<{ status: string }>("/health"),

  listCases: () => request<{ cases: CaseSummary[] }>("/api/cases"),

  getCase: (phone: string) =>
    request<CaseDetail>(`/api/cases/${encodeURIComponent(phone)}`),

  analytics: () => request<Analytics>("/api/analytics"),

  recentAlerts: () => request<{ alerts: CaseSummary[] }>("/api/alerts/recent"),

  overrideCase: (phone: string, body: { action: OverrideAction; receptionist_id?: string }) =>
    request<OverrideResponse>(`/api/cases/${encodeURIComponent(phone)}/override`, {
      method: "POST",
      body: JSON.stringify({
        receptionist_id: "sana",
        ...body,
      }),
    }),

  getWebSession: (sessionId: string) =>
    request<WebChatSession>(`/api/web-chat/sessions/${encodeURIComponent(sessionId)}`),

  sendWebChatMessage: (sessionId: string, body: string) =>
    request<WebChatSession>("/api/web-chat/message", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, body }),
    }),
};
