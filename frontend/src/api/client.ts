import type {
  Analytics,
  CaseDetail,
  CaseSummary,
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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `${res.status} ${res.statusText} (${url})`);
  }
  return res.json() as Promise<T>;
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
};
