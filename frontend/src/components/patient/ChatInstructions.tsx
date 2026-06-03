import { Icon } from "@/components/stitch/Icon";

const INSTRUCTIONS = [
  "Describe your symptoms in Urdu or English — Sehat replies in the same language.",
  "You do not pick a department. Sehat routes you automatically (general, pediatrics, or cardiology) from what you write.",
  "For routine visits it will ask: main symptom, how long, then a preferred appointment day — answer each message in order.",
  "Mention child/baby for pediatrics; chest or heart symptoms for cardiology. For emergencies (chest pain, breathing, bleeding) call 1122 immediately.",
  "This is a clinic intake demo; it does not replace emergency care or a doctor visit.",
] as const;

const DISMISS_KEY = "sehat-chat-instructions-dismissed";

export function ChatInstructions({
  open,
  onDismiss,
}: {
  open: boolean;
  onDismiss: () => void;
}) {
  if (!open) return null;

  return (
    <aside
      className="shrink-0 border-b border-outline-variant/20 bg-surface-container-low px-3 py-3 sm:px-4"
      aria-label="Chat instructions"
    >
      <div className="mx-auto flex max-w-2xl gap-3">
        <Icon name="info" className="mt-0.5 shrink-0 text-secondary" />
        <div className="min-w-0 flex-1">
          <p className="font-headline-sm text-headline-sm text-on-surface">Before you start</p>
          <ul className="mt-2 space-y-1.5 font-body-sm text-body-sm text-on-surface-variant">
            {INSTRUCTIONS.map((line) => (
              <li key={line} className="flex gap-2">
                <span className="text-secondary">•</span>
                <span>{line}</span>
              </li>
            ))}
          </ul>
          <p className="mt-2 font-label-caps text-label-caps text-on-surface-variant">
            Type <span className="text-on-surface">reset</span> anytime to start a new conversation.
          </p>
        </div>
        <button
          type="button"
          onClick={onDismiss}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-on-surface-variant transition-colors hover:bg-surface-container"
          aria-label="Dismiss instructions"
        >
          <Icon name="close" className="text-[20px]" />
        </button>
      </div>
    </aside>
  );
}

export function readInstructionsDismissed(): boolean {
  if (typeof window === "undefined") return false;
  return localStorage.getItem(DISMISS_KEY) === "1";
}

export function dismissInstructions(): void {
  localStorage.setItem(DISMISS_KEY, "1");
}
