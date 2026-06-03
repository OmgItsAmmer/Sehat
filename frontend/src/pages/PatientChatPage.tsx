import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import {
  ChatInstructions,
  dismissInstructions,
  readInstructionsDismissed,
} from "@/components/patient/ChatInstructions";
import { ChatMessageList } from "@/components/patient/ChatMessageList";
import { Icon } from "@/components/stitch/Icon";
import { usePatientChat } from "@/hooks/usePatientChat";
import "@/theme/landing-theme.css";

export function PatientChatPage() {
  const { turns, sending, hydrating, error, send, startNewSession, clearError } = usePatientChat();
  const [instructionsOpen, setInstructionsOpen] = useState(() => !readInstructionsDismissed());
  const [draft, setDraft] = useState("");
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const submitMessage = useCallback(async () => {
    const text = draft.trim();
    if (!text || sending || hydrating) return;
    setDraft("");
    await send(text);
    inputRef.current?.focus();
  }, [draft, send, sending, hydrating]);

  useEffect(() => {
    if (!hydrating) inputRef.current?.focus();
  }, [hydrating]);

  useEffect(() => {
    const onWindowKeyDown = (e: globalThis.KeyboardEvent) => {
      if (sending || hydrating) return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === "Tab" || e.key === "Escape") return;

      const target = e.target as HTMLElement | null;
      const inChatInput = target === inputRef.current;

      if (inChatInput) {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          void submitMessage();
        }
        return;
      }

      if (
        target &&
        (target.tagName === "TEXTAREA" ||
          target.tagName === "INPUT" ||
          target.tagName === "SELECT" ||
          target.isContentEditable)
      ) {
        return;
      }

      if (e.key === "Enter") {
        e.preventDefault();
        inputRef.current?.focus();
        if (draft.trim()) void submitMessage();
        return;
      }

      if (e.key.length === 1) {
        e.preventDefault();
        inputRef.current?.focus();
        setDraft((prev) => prev + e.key);
      } else if (e.key === "Backspace") {
        e.preventDefault();
        inputRef.current?.focus();
        setDraft((prev) => prev.slice(0, -1));
      }
    };

    window.addEventListener("keydown", onWindowKeyDown);
    return () => window.removeEventListener("keydown", onWindowKeyDown);
  }, [draft, sending, hydrating, submitMessage]);

  function handleDismissInstructions() {
    dismissInstructions();
    setInstructionsOpen(false);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    await submitMessage();
  }

  return (
    <div className="landing-page flex h-dvh max-h-dvh flex-col overflow-hidden bg-background font-body-md text-on-background">
      <header className="z-20 flex shrink-0 items-center gap-2 border-b border-outline-variant/15 bg-primary-container px-3 py-2 shadow-sm sm:gap-3 sm:px-4 sm:py-3">
        <Link
          to="/"
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-on-primary transition-colors hover:bg-on-primary/10"
          aria-label="Back to home"
        >
          <Icon name="arrow_back" />
        </Link>
        <div className="min-w-0 flex-1">
          <p className="truncate font-headline-sm text-headline-sm font-bold text-on-primary">
            Sehat | صحت
          </p>
          <p className="truncate font-body-sm text-body-sm text-on-primary-container">
            Dr. Muhid Clinics · Patient intake
          </p>
        </div>
        <button
          type="button"
          onClick={() => setInstructionsOpen((o) => !o)}
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-on-primary transition-colors hover:bg-on-primary/10 sm:hidden"
          aria-label="Toggle instructions"
        >
          <Icon name="help" />
        </button>
        <button
          type="button"
          onClick={() => startNewSession()}
          disabled={sending}
          className="flex h-11 shrink-0 items-center justify-center rounded-full text-on-primary transition-colors hover:bg-on-primary/10 disabled:opacity-50 sm:gap-1 sm:rounded-lg sm:border sm:border-outline-variant/30 sm:px-3"
          aria-label="Start new chat"
        >
          <Icon name="restart_alt" className="text-[20px] sm:text-[18px]" />
          <span className="hidden font-label-caps text-label-caps sm:inline">New chat</span>
        </button>
      </header>

      <ChatInstructions open={instructionsOpen} onDismiss={handleDismissInstructions} />

      {error && (
        <div
          className="shrink-0 border-b border-error/30 bg-error-container px-3 py-2 sm:px-4"
          role="alert"
        >
          <div className="mx-auto flex max-w-2xl items-start justify-between gap-2">
            <p className="font-body-sm text-body-sm text-on-error-container">{error}</p>
            <button
              type="button"
              onClick={clearError}
              className="shrink-0 font-label-caps text-label-caps text-error underline"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      <ChatMessageList turns={turns} sending={sending} hydrating={hydrating} />

      <form
        onSubmit={handleSubmit}
        className="shrink-0 border-t border-outline-variant/20 bg-surface-container-lowest px-3 py-3 pb-safe sm:px-4"
      >
        <div className="mx-auto flex max-w-2xl items-end gap-2">
          <label className="sr-only" htmlFor="patient-chat-input">
            Your message
          </label>
          <textarea
            id="patient-chat-input"
            ref={inputRef}
            rows={1}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            disabled={sending || hydrating}
            placeholder="Apni takleef likhein…"
            className="max-h-32 min-h-[48px] flex-1 resize-none rounded-xl border border-outline-variant/40 bg-surface px-3 py-3 font-body-md text-body-md text-on-surface placeholder:text-on-surface-variant focus:border-secondary focus:outline-none focus:ring-2 focus:ring-secondary/30 disabled:opacity-60"
          />
          <button
            type="submit"
            disabled={sending || hydrating || !draft.trim()}
            className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-secondary text-on-secondary shadow-md transition-all hover:opacity-90 active:scale-95 disabled:cursor-not-allowed disabled:opacity-40"
            aria-label="Send message"
          >
            <Icon name="send" filled className="text-[22px]" />
          </button>
        </div>
        <p className="mx-auto mt-2 hidden max-w-2xl text-center font-label-caps text-label-caps text-on-surface-variant sm:block">
          Enter to send · Shift+Enter for new line
        </p>
      </form>
    </div>
  );
}
