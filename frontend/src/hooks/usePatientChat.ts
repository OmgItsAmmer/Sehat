import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/api/client";
import type { Priority, WebChatSession } from "@/api/types";
import { getOrCreateWebSessionId, resetWebSessionId } from "@/lib/webSessionId";
import { friendlyApiError } from "@/lib/userMessages";

export type ChatTurn = {
  id: string;
  role: "patient" | "bot";
  body: string;
  priority?: Priority;
  at: number;
};

const WELCOME: ChatTurn = {
  id: "welcome",
  role: "bot",
  body: "Assalam o Alaikum! Dr. Muhid Clinics mein khush aamdeed. Apni takleef batayein — Urdu ya English mein.",
  at: 0,
};

function turnsFromSession(detail: WebChatSession): ChatTurn[] {
  const turns: ChatTurn[] = [];
  for (const text of detail.messages ?? []) {
    turns.push({
      id: `p-${turns.length}`,
      role: "patient",
      body: text,
      at: Date.now(),
    });
  }
  if (detail.reply?.trim()) {
    turns.push({
      id: "reply-latest",
      role: "bot",
      body: detail.reply.trim(),
      priority: detail.priority ?? undefined,
      at: Date.now(),
    });
  }
  return turns.length > 0 ? turns : [WELCOME];
}

export function usePatientChat() {
  const [sessionId, setSessionId] = useState(() => getOrCreateWebSessionId());
  const [turns, setTurns] = useState<ChatTurn[]>([WELCOME]);
  const [sending, setSending] = useState(false);
  const [hydrating, setHydrating] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const sessionRef = useRef(sessionId);

  useEffect(() => {
    sessionRef.current = sessionId;
  }, [sessionId]);

  const hydrate = useCallback(async (id: string) => {
    setHydrating(true);
    setError(null);
    try {
      const detail = await api.getWebSession(id);
      if (detail.message_count > 0 || detail.reply?.trim()) {
        setTurns(turnsFromSession(detail));
      } else {
        setTurns([WELCOME]);
      }
    } catch {
      setTurns([WELCOME]);
    } finally {
      setHydrating(false);
    }
  }, []);

  useEffect(() => {
    hydrate(sessionId);
  }, [sessionId, hydrate]);

  const send = useCallback(
    async (body: string) => {
      const text = body.trim();
      if (!text || sending) return;

      setError(null);
      setSending(true);
      setTurns((prev) => [
        ...prev,
        { id: `p-pending-${Date.now()}`, role: "patient", body: text, at: Date.now() },
      ]);

      try {
        const res = await api.sendWebChatMessage(sessionRef.current, text);
        const isReset = /reset|restart|start over|new chat|clear/i.test(text);
        if (isReset) {
          setTurns([
            WELCOME,
            {
              id: `b-reset-${Date.now()}`,
              role: "bot",
              body: res.reply?.trim() || WELCOME.body,
              at: Date.now(),
            },
          ]);
        } else {
          setTurns((prev) => {
            const withoutPending = prev.filter((t) => !t.id.startsWith("p-pending-"));
            const base = [...withoutPending];
            const last = base[base.length - 1];
            if (last?.role !== "patient" || last.body !== text) {
              base.push({ id: `p-${Date.now()}`, role: "patient", body: text, at: Date.now() });
            }
            if (res.reply?.trim()) {
              base.push({
                id: `b-${Date.now()}`,
                role: "bot",
                body: res.reply.trim(),
                priority: res.priority ?? undefined,
                at: Date.now(),
              });
            }
            return base;
          });
        }
      } catch (e) {
        setTurns((prev) => prev.filter((t) => !t.id.startsWith("p-pending-")));
        setError(friendlyApiError(e));
      } finally {
        setSending(false);
      }
    },
    [sending],
  );

  const startNewSession = useCallback(async () => {
    const id = resetWebSessionId();
    setSessionId(id);
    setTurns([WELCOME]);
    setError(null);
    await hydrate(id);
  }, [hydrate]);

  return {
    sessionId,
    turns,
    sending,
    hydrating,
    error,
    send,
    startNewSession,
    clearError: () => setError(null),
  };
}
