import { useState } from "react";
import { Icon } from "@/components/stitch/Icon";
import { api } from "@/api/client";
import type { OverrideAction } from "@/api/types";

type Props = {
  phone: string;
  priority: string | null;
  awaitingReview: boolean;
  onDone: () => void;
};

export function OverrideButtons({ phone, priority, awaitingReview, onDone }: Props) {
  const [busy, setBusy] = useState<OverrideAction | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!awaitingReview && !priority) return null;

  async function run(action: OverrideAction) {
    setBusy(action);
    setError(null);
    try {
      await api.overrideCase(phone, { action, receptionist_id: "sana" });
      onDone();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="rounded-xl border border-outline-variant bg-surface-container-low p-4">
      <p className="mb-3 font-label-md text-label-md uppercase text-on-surface-variant">
        Human review {priority ? `· ${priority}` : ""}
      </p>
      {awaitingReview ? (
        <p className="mb-4 font-body-md text-body-md text-on-surface">
          Low-confidence classification — confirm or correct priority. The patient receives an
          updated reply when you choose.
        </p>
      ) : (
        <p className="mb-4 font-body-md text-body-md text-on-surface-variant">
          Override is available for escalated cases.
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <OverrideBtn
          label="Agree"
          icon="check_circle"
          disabled={!!busy}
          loading={busy === "agree"}
          onClick={() => void run("agree")}
        />
        <OverrideBtn
          label="Upgrade"
          icon="arrow_upward"
          highlight
          disabled={!!busy}
          loading={busy === "upgrade"}
          onClick={() => void run("upgrade")}
        />
        <OverrideBtn
          label="Downgrade"
          icon="arrow_downward"
          disabled={!!busy}
          loading={busy === "downgrade"}
          onClick={() => void run("downgrade")}
        />
      </div>
      {error && (
        <p className="mt-3 font-body-md text-body-md text-error">{error}</p>
      )}
    </section>
  );
}

function OverrideBtn({
  label,
  icon,
  onClick,
  disabled,
  loading,
  highlight,
}: {
  label: string;
  icon: string;
  onClick: () => void;
  disabled: boolean;
  loading: boolean;
  highlight?: boolean;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={`flex min-h-touch-target-min items-center gap-2 rounded-xl px-4 py-2 font-label-md text-label-md transition-colors disabled:opacity-50 ${
        highlight
          ? "bg-error text-on-error hover:opacity-90"
          : "border border-outline-variant bg-surface text-on-surface hover:bg-surface-container-high"
      }`}
    >
      <Icon name={icon} className="text-[18px]" />
      {loading ? "…" : label}
    </button>
  );
}
