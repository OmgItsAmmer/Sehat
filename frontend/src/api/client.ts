import type { Analytics, CaseDetail, CaseSummary } from "./types";

const API_BASE = import.meta.env.VITE_API_URL ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string }>("/health"),

  listCases: () => request<{ cases: CaseSummary[] }>("/api/cases"),

  getCase: (phone: string) =>
    request<CaseDetail>(`/api/cases/${encodeURIComponent(phone)}`),

  analytics: () => request<Analytics>("/api/analytics"),

  recentAlerts: () => request<{ alerts: CaseSummary[] }>("/api/alerts/recent"),
};
