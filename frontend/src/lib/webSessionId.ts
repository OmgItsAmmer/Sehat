import { WEB_SESSION_ID_PREFIX } from "@/lib/webSessionConstants";

const STORAGE_KEY = "sehat-web-session-id";

function newSessionId(): string {
  return `${WEB_SESSION_ID_PREFIX}${crypto.randomUUID()}`;
}

/** Stable web chat session id (separate from WhatsApp chat ids). */
export function getOrCreateWebSessionId(): string {
  if (typeof window === "undefined") {
    return `${WEB_SESSION_ID_PREFIX}demo`;
  }
  const existing = localStorage.getItem(STORAGE_KEY);
  if (existing && existing.startsWith(WEB_SESSION_ID_PREFIX)) return existing;
  const id = newSessionId();
  localStorage.setItem(STORAGE_KEY, id);
  return id;
}

export function resetWebSessionId(): string {
  const id = newSessionId();
  localStorage.setItem(STORAGE_KEY, id);
  return id;
}
