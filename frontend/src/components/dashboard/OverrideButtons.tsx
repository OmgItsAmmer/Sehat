import { useState } from "react";
import { Icon } from "@/components/stitch/Icon";
import { api } from "@/api/client";
import { friendlyApiError } from "@/lib/userMessages";
import type { OverrideAction, Priority } from "@/api/types";

type Props = {
  phone: string;
  priority: Priority;
  canOverride: boolean;
  onDone: () => void;
};

export function OverrideButtons({ phone, priority, canOverride, onDone }: Props) {
  const [busy, setBusy] = useState<OverrideAction | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function run(action: OverrideAction) {
    if (!canOverride || busy) return;
    setBusy(action);
    setError(null);
    setSuccess(null);
    try {
      const result = await api.overrideCase(phone, { action, receptionist_id: "sana" });
      const label =
        action === "agree"
          ? "Confirmed"
          : action === "upgrade"
            ? `Upgraded to ${result.priority ?? "higher priority"}`
            : `Downgraded to ${result.priority ?? "lower priority"}`;
      setSuccess(`${label}. The patient has been notified.`);
      onDone();
    } catch (e) {
      setError(friendlyApiError(e));
    } finally {
      setBusy(null);
    }
  }

  const priorityLabel = priority ?? "pending";

  return (
    <section className="rounded-lg border border-outline-variant bg-surface px-3 py-2 shadow-sm">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
        <h2 className="font-label-md text-label-md font-semibold text-on-surface">Triage decision</h2>
        <p className="font-body-md text-body-md text-on-surface-variant">
          {canOverride
            ? `AI: ${priorityLabel} — confirm or adjust.`
            : "Override available after escalation."}
        </p>
      </div>

      <div className="mb-2 grid grid-cols-3 gap-2">
        <OverrideBtn
          label="Agree"
          sublabel={priority ? `Keep ${priority}` : "Confirm"}
          icon="check_circle"
          variant="agree"
          disabled={!canOverride || !!busy}
          loading={busy === "agree"}
          onClick={() => void run("agree")}
        />
        <OverrideBtn
          label="Upgrade"
          sublabel="Raise priority"
          icon="arrow_upward"
          variant="upgrade"
          disabled={!canOverride || !!busy}
          loading={busy === "upgrade"}
          onClick={() => void run("upgrade")}
        />
        <OverrideBtn
          label="Downgrade"
          sublabel="Lower priority"
          icon="arrow_downward"
          variant="downgrade"
          disabled={!canOverride || !!busy}
          loading={busy === "downgrade"}
          onClick={() => void run("downgrade")}
        />
      </div>

      {success && (
        <p className="flex items-center gap-1.5 rounded-md bg-primary-container/30 px-2 py-1 font-body-md text-body-md text-primary">
          <Icon name="check_circle" className="text-[14px]" />
          {success}
        </p>
      )}
      {error && (
        <p className="flex items-start gap-1.5 rounded-md bg-error-container px-2 py-1 font-body-md text-body-md text-on-error-container">
          <Icon name="error" className="mt-0.5 shrink-0 text-[14px]" />
          {error}
        </p>
      )}
    </section>
  );
}

function OverrideBtn({
  label,
  sublabel,
  icon,
  onClick,
  disabled,
  loading,
  variant,
}: {
  label: string;
  sublabel: string;
  icon: string;
  onClick: () => void;
  disabled: boolean;
  loading: boolean;
  variant: "agree" | "upgrade" | "downgrade";
}) {
  const styles = {
    agree:
      "border border-primary/20 bg-primary-container text-on-primary-container hover:bg-primary hover:text-on-primary hover:shadow-md active:scale-[0.98]",
    upgrade:
      "border border-[#F59E0B]/30 bg-[#FEF3C7] text-[#92400E] hover:bg-[#FDE68A] hover:shadow-md active:scale-[0.98]",
    downgrade:
      "border border-outline-variant bg-surface-container-high text-on-surface-variant hover:bg-surface-variant hover:shadow-md active:scale-[0.98]",
  }[variant];

  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      title={sublabel}
      className={`flex min-h-9 flex-col items-center justify-center gap-0 rounded-lg px-2 py-1.5 transition-all duration-200 disabled:cursor-not-allowed disabled:opacity-45 disabled:hover:shadow-none disabled:active:scale-100 ${styles}`}
    >
      <span className="flex items-center gap-1 font-label-md text-label-md font-semibold">
        <Icon name={icon} className="text-[16px]" />
        {loading ? "…" : label}
      </span>
    </button>
  );
}
