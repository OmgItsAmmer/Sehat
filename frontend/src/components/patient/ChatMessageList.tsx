import { useEffect, useRef } from "react";
import { Icon } from "@/components/stitch/Icon";
import type { ChatTurn } from "@/hooks/usePatientChat";
import type { Priority } from "@/api/types";

function isEmergency(priority?: Priority, text?: string) {
  if (priority === "P1") return true;
  const t = (text ?? "").toLowerCase();
  return (
    t.includes("1122") ||
    t.includes("emergency") ||
    t.includes("fori") ||
    t.includes("warning")
  );
}

function PatientBubble({ body }: { body: string }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[min(85%,20rem)] rounded-2xl rounded-tr-sm bg-secondary-container px-3 py-2.5 font-body-sm text-body-sm text-on-secondary-container shadow-sm sm:px-4 sm:py-3">
        {body}
      </div>
    </div>
  );
}

function BotBubble({ body, priority }: { body: string; priority?: Priority }) {
  const emergency = isEmergency(priority, body);
  return (
    <div className="flex justify-start gap-2 sm:gap-3">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-secondary text-on-secondary sm:h-10 sm:w-10">
        <Icon name="smart_toy" className="text-[18px]" />
      </div>
      <div
        className={`max-w-[min(85%,20rem)] rounded-2xl rounded-tl-sm px-3 py-2.5 font-body-sm text-body-sm shadow-sm sm:px-4 sm:py-3 ${
          emergency
            ? "border border-error bg-error-container text-on-error-container"
            : "border border-outline-variant/25 bg-surface-container-lowest text-on-surface"
        }`}
      >
        {emergency && (
          <div className="mb-1 flex items-center gap-1 font-label-caps text-label-caps text-error">
            <Icon name="warning" className="text-[16px]" />
            Urgent
          </div>
        )}
        {body}
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex justify-start gap-2 sm:gap-3" aria-live="polite" aria-label="Sehat is typing">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-secondary text-on-secondary">
        <Icon name="smart_toy" className="text-[18px]" />
      </div>
      <div className="flex items-center gap-1 rounded-2xl rounded-tl-sm border border-outline-variant/25 bg-surface-container-lowest px-4 py-3">
        <span className="h-2 w-2 animate-bounce rounded-full bg-on-surface-variant [animation-delay:0ms]" />
        <span className="h-2 w-2 animate-bounce rounded-full bg-on-surface-variant [animation-delay:150ms]" />
        <span className="h-2 w-2 animate-bounce rounded-full bg-on-surface-variant [animation-delay:300ms]" />
      </div>
    </div>
  );
}

export function ChatMessageList({
  turns,
  sending,
  hydrating,
}: {
  turns: ChatTurn[];
  sending: boolean;
  hydrating: boolean;
}) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns, sending, hydrating]);

  return (
    <div
      className="custom-scrollbar min-h-0 flex-1 overflow-y-auto overscroll-contain px-3 py-4 sm:px-4"
      role="log"
      aria-live="polite"
      aria-relevant="additions"
    >
      <div className="mx-auto flex max-w-2xl flex-col gap-3 sm:gap-4">
        {hydrating && (
          <p className="text-center font-body-sm text-body-sm text-on-surface-variant">
            Loading your conversation…
          </p>
        )}
        {!hydrating &&
          turns.map((t) =>
            t.role === "patient" ? (
              <PatientBubble key={t.id} body={t.body} />
            ) : (
              <BotBubble key={t.id} body={t.body} priority={t.priority} />
            ),
          )}
        {sending && <TypingIndicator />}
        <div ref={endRef} className="h-1 shrink-0" />
      </div>
    </div>
  );
}
