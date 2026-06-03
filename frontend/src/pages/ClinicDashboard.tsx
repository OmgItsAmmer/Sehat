import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { OverrideButtons } from "@/components/dashboard/OverrideButtons";
import { Icon } from "@/components/stitch/Icon";
import { useBackendHealth, useCaseDetail, useCases } from "@/hooks/useCases";
import {
  complaintLine,
  displayName,
  initials,
  patientLabel,
  priorityBadgeClasses,
  priorityBorder,
} from "@/lib/caseDisplay";
import type { CaseDetail, CaseSummary, Priority } from "@/api/types";

export function ClinicDashboard() {
  const { cases, loading, error, lastUpdated, refresh: refreshCases } = useCases();
  const { ok: backendOk } = useBackendHealth();

  useEffect(() => {
    if (import.meta.env.DEV) {
      console.info("[Sehat] API base:", import.meta.env.VITE_API_URL || "http://127.0.0.1:8000 (default)");
    }
  }, []);
  const [params, setParams] = useSearchParams();
  const [filter, setFilter] = useState<Priority | "all">("all");
  const [bannerOpen, setBannerOpen] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const caseParam = params.get("case");
  const selectedPhone = useMemo(() => {
    if (caseParam && cases.some((c) => c.phone === caseParam)) return caseParam;
    return cases[0]?.phone ?? "";
  }, [caseParam, cases]);

  const { detail, loading: detailLoading, error: detailError, refresh: refreshDetail } =
    useCaseDetail(selectedPhone || undefined);

  const filtered = useMemo(() => {
    if (filter === "all") return cases;
    return cases.filter((c) => c.priority === filter);
  }, [cases, filter]);

  const selected = cases.find((c) => c.phone === selectedPhone);
  const p1 = cases.filter((c) => c.priority === "P1");

  useEffect(() => {
    if (caseParam && caseParam !== selectedPhone && selectedPhone) {
      setParams({ case: selectedPhone }, { replace: true });
    }
  }, [caseParam, selectedPhone, setParams]);

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await refreshCases();
      if (selectedPhone) await refreshDetail();
    } finally {
      setRefreshing(false);
    }
  }, [refreshCases, refreshDetail, selectedPhone]);

  function selectCase(phone: string) {
    setParams({ case: phone });
  }

  return (
    <div className="flex min-h-dvh flex-col overflow-hidden bg-background font-body-md text-on-background">
      {backendOk === false && (
        <div className="relative z-50 bg-error-container px-container-padding py-2 text-on-error-container">
          <p className="font-body-md text-body-md">
            Backend offline — run <code className="font-mono-clinical">make dev</code> on port 8000,
            then restart <code className="font-mono-clinical">make frontend-dev</code>.
          </p>
        </div>
      )}

      {error && (
        <div className="relative z-50 bg-error-container px-container-padding py-2 text-on-error-container">
          <p className="font-body-md text-body-md">API error: {error}</p>
        </div>
      )}

      {bannerOpen && p1[0] && (
        <div className="stat-banner-enter relative z-50 flex h-touch-target-min items-center justify-between bg-error px-container-padding text-on-error">
          <button
            type="button"
            className="flex flex-1 items-center gap-2 text-left hover:opacity-90"
            onClick={() => selectCase(p1[0].phone)}
          >
            <Icon name="volume_up" filled className="text-[20px]" />
            <span className="font-headline-md text-headline-md uppercase tracking-tight">
              NEW P1 ARRIVAL: {patientLabel(p1[0].phone)}
            </span>
          </button>
          <button
            type="button"
            className="flex h-touch-target-min min-w-touch-target-min items-center justify-center p-2 hover:opacity-80"
            onClick={() => setBannerOpen(false)}
            aria-label="Dismiss banner"
          >
            <Icon name="close" />
          </button>
        </div>
      )}

      <header className="fixed top-0 z-40 flex h-touch-target-min w-full items-center justify-between border-b border-outline-variant bg-surface px-container-padding">
        <div className="flex items-center gap-3">
          <span className="font-headline-lg text-title-lg tracking-tight text-primary">
            Sehat | صحت
          </span>
          <span
            className={`h-2 w-2 rounded-full ${backendOk === false ? "bg-error" : backendOk ? "bg-primary-container" : "bg-outline"}`}
            title={backendOk === false ? "Backend offline" : backendOk ? "Backend connected" : "Checking…"}
          />
        </div>
        <div className="flex flex-1 justify-center">
          <div className="flex items-center gap-2 rounded-full border border-outline-variant bg-surface-container-low px-4 py-1.5">
            <span className={`h-2 w-2 rounded-full ${p1.length ? "bg-error pulse-red" : "bg-primary-container"}`} />
            <span className="font-label-md text-label-md text-on-surface">
              {loading ? "…" : `${cases.length} Active Cases`}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled={refreshing}
            onClick={() => void handleRefresh()}
            className="flex h-touch-target-min items-center gap-1 rounded-full px-3 py-2 text-on-surface-variant transition-colors hover:bg-surface-container-low disabled:opacity-50"
            title="Refresh from API"
          >
            <Icon name="refresh" className={refreshing ? "animate-spin" : ""} />
            <span className="hidden font-label-md text-label-md sm:inline">Refresh</span>
          </button>
          {p1[0] && (
            <Link
              to="/alerts/slack"
              className="flex h-touch-target-min w-[48px] items-center justify-center rounded-full p-2 text-on-surface-variant transition-colors hover:bg-surface-container-low"
              title="P1 Slack alert preview"
            >
              <Icon name="notifications" />
            </Link>
          )}
          <Link
            to="/analytics"
            className="flex h-touch-target-min w-[48px] items-center justify-center rounded-full p-2 text-on-surface-variant transition-colors hover:bg-surface-container-low"
            title="Analytics"
          >
            <Icon name="monitoring" />
          </Link>
        </div>
      </header>

      <div className="flex h-screen w-full flex-1 pt-[48px]">
        <nav className="flex h-full w-80 shrink-0 flex-col border-r border-outline-variant bg-surface-container-low p-unit">
          <div className="mb-2 border-b border-outline-variant px-4 py-4">
            <h2 className="font-headline-md text-headline-md text-primary">Case Queue</h2>
            <p className="font-mono-clinical text-mono-clinical text-on-surface-variant">
              {lastUpdated ? `Updated ${lastUpdated.toLocaleTimeString()}` : "Live Traffic"}
            </p>
          </div>
          <div className="flex flex-col gap-1 px-2">
            <QueueTab active={filter === "all"} label="All Cases" onClick={() => setFilter("all")} />
            <QueueTab
              active={filter === "P1"}
              label="P1 Critical"
              onClick={() => setFilter("P1")}
              highlight
            />
            <QueueTab active={filter === "P2"} label="P2 Urgent" onClick={() => setFilter("P2")} />
            <QueueTab active={filter === "P3"} label="P3 Routine" onClick={() => setFilter("P3")} />
          </div>

          <div className="flex flex-1 flex-col gap-unit overflow-y-auto px-2 pt-4">
            {loading && !cases.length && (
              <p className="px-3 text-body-md text-on-surface-variant">Loading queue…</p>
            )}
            {!loading && filtered.length === 0 && (
              <p className="px-3 text-body-md text-on-surface-variant">
                No cases in queue. Intake arrives via WhatsApp webhook.
              </p>
            )}
            {filtered.map((c) => (
              <QueueCard
                key={c.phone}
                c={c}
                active={c.phone === selectedPhone}
                onSelect={() => selectCase(c.phone)}
              />
            ))}
          </div>
        </nav>

        <main className="flex flex-1 justify-center overflow-y-auto bg-background p-container-padding">
          {!selected ? (
            <EmptyMain onRefresh={() => void handleRefresh()} />
          ) : (
            <div className="flex w-full max-w-4xl flex-col gap-6">
              {detailError && (
                <p className="rounded-lg bg-error-container px-4 py-2 font-body-md text-on-error-container">
                  {detailError}
                </p>
              )}
              <PatientHeader
                c={detail ?? selected}
                onOverrideDone={() => void handleRefresh()}
              />
              {detail?.reasoning && (
                <section className="rounded-xl border border-outline-variant bg-surface-container-low p-4">
                  <p className="mb-1 font-label-md text-label-md uppercase text-on-surface-variant">
                    AI reasoning
                  </p>
                  <p className="font-body-md text-body-md text-on-surface">{detail.reasoning}</p>
                </section>
              )}
              <ConversationThread
                loading={detailLoading}
                messages={detail?.messages ?? []}
                phone={selected.phone}
                reply={detail?.reply ?? selected.reply}
                dbMessages={detail?.db_messages}
              />
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

function QueueTab({
  active,
  label,
  onClick,
  highlight,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
  highlight?: boolean;
}) {
  const base = "mx-2 flex cursor-pointer items-center gap-2 rounded-lg px-3 py-2";
  const cls = active
    ? highlight
      ? `${base} rounded-xl bg-primary-container font-bold text-on-primary-container`
      : `${base} bg-surface-container-high font-bold text-on-surface`
    : `${base} text-on-surface-variant hover:bg-surface-container-high`;
  return (
    <button type="button" className={cls} onClick={onClick}>
      <span className="flex-1 font-label-md text-label-md text-left">{label}</span>
      <span className="font-mono-clinical text-mono-clinical text-[10px] opacity-70">
        {active ? "●" : ""}
      </span>
    </button>
  );
}

function QueueCard({
  c,
  active,
  onSelect,
}: {
  c: CaseSummary;
  active: boolean;
  onSelect: () => void;
}) {
  const p = c.priority;
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`group relative cursor-pointer overflow-hidden rounded-r-lg border-y border-r border-outline-variant bg-surface p-3 text-left shadow-[0_4px_12px_rgba(0,0,0,0.05)] ${priorityBorder(p)} border-l-[4px] ${
        active ? "ring-2 ring-primary-container" : ""
      } ${p === "P1" ? "hover:bg-error/5" : "hover:bg-surface-container-low"} transition-colors`}
    >
      <div className="relative z-10 mb-1 flex items-start justify-between">
        <div className="flex items-center gap-2">
          {p === "P1" && <span className="h-2 w-2 rounded-full bg-error pulse-red" />}
          {p === "P2" && <span className="h-2 w-2 rounded-full bg-[#F59E0B]" />}
          {p !== "P1" && p !== "P2" && <span className="h-2 w-2 rounded-full bg-outline" />}
          <span className={`font-label-md text-label-md font-bold uppercase ${priorityBadgeClasses(p)}`}>
            {p ?? "PENDING"}
          </span>
        </div>
        <span className={`font-mono-clinical text-mono-clinical ${p === "P1" ? "text-error" : "text-on-surface-variant"}`}>
          {c.message_count} msgs
        </span>
      </div>
      <h3 className="relative z-10 font-title-lg text-title-lg text-on-surface">
        {patientLabel(c.phone)}
      </h3>
      <p className="relative z-10 font-body-md text-body-md text-on-surface-variant">
        {complaintLine(c)}
      </p>
    </button>
  );
}

function PatientHeader({
  c,
  onOverrideDone,
}: {
  c: CaseSummary;
  onOverrideDone: () => void;
}) {
  const isP1 = c.priority === "P1";
  return (
    <div
      className={`relative overflow-hidden rounded-xl border-[2px] bg-surface p-6 shadow-[0_4px_12px_rgba(220,38,38,0.1)] ${
        isP1 ? "border-error" : "border-outline-variant"
      }`}
    >
      {isP1 && (
        <div className="pointer-events-none absolute right-0 top-0 h-32 w-32 rounded-bl-full bg-error/5" />
      )}
      <div className="flex items-start justify-between">
        <div>
          {isP1 && (
            <div className="mb-3 inline-flex items-center gap-2 rounded-full bg-error px-3 py-1 text-on-error">
              <span className="h-2 w-2 animate-pulse rounded-full bg-white" />
              <span className="font-label-md text-label-md font-bold uppercase tracking-wider">
                P1 EMERGENCY
              </span>
            </div>
          )}
          <h1 className="mb-1 font-headline-lg text-headline-lg text-on-surface">
            {patientLabel(c.phone)}
          </h1>
          <p className="font-title-lg text-title-lg text-on-surface-variant">
            {displayName(c)} • {Math.round((c.confidence || 0) * 100)}% confidence
          </p>
        </div>
        <div className="text-right">
          <div className={`mb-1 font-mono-clinical text-mono-clinical ${isP1 ? "text-error" : "text-on-surface-variant"}`}>
            {c.escalated ? "ESCALATED" : "ACTIVE"}
          </div>
          <div className="font-label-md text-label-md text-on-surface-variant">
            {c.slots_complete ? "Intake complete" : c.pending_slot ? `Awaiting: ${c.pending_slot}` : "In triage"}
          </div>
        </div>
      </div>
      {Object.keys(c.slots ?? {}).length > 0 && (
        <dl className="mt-4 grid gap-2 border-t border-outline-variant/30 pt-4 sm:grid-cols-3">
          {Object.entries(c.slots).map(([k, v]) => (
            <div key={k}>
              <dt className="font-label-md text-label-md text-on-surface-variant">{k}</dt>
              <dd className="font-body-md text-body-md text-on-surface">{v}</dd>
            </div>
          ))}
        </dl>
      )}
      {c.awaiting_human_review && (
        <div className="mt-4 border-t border-outline-variant/30 pt-4">
          <OverrideButtons
            phone={c.phone}
            priority={c.priority}
            awaitingReview={!!c.awaiting_human_review}
            onDone={onOverrideDone}
          />
        </div>
      )}
    </div>
  );
}

function ConversationThread({
  loading,
  messages,
  phone,
  reply,
  dbMessages,
}: {
  loading: boolean;
  messages: string[];
  phone: string;
  reply: string;
  dbMessages?: CaseDetail["db_messages"];
}) {
  const ini = initials(phone);
  const hasSession = messages.length > 0 || reply;
  const hasDb = dbMessages && dbMessages.length > 0;

  return (
    <div className="flex min-h-[300px] flex-1 flex-col rounded-xl border border-outline-variant bg-surface">
      <div className="rounded-t-xl border-b border-outline-variant bg-surface-container-lowest px-6 py-4">
        <h3 className="font-title-lg text-title-lg text-on-surface">Intake Conversation</h3>
        <p className="font-label-md text-label-md text-on-surface-variant">From session memory + database</p>
      </div>
      <div className="flex flex-1 flex-col gap-6 overflow-y-auto p-6">
        {loading && <p className="text-body-md text-on-surface-variant">Loading case…</p>}
        {!loading && !hasSession && !hasDb && (
          <p className="text-body-md text-on-surface-variant">No messages in session yet.</p>
        )}
        {messages.map((text, i) => (
          <PatientBubble key={`s-${i}`} ini={ini} text={text} />
        ))}
        {reply && <BotBubble text={reply} />}
        {dbMessages?.map((m) =>
          m.direction === "inbound" ? (
            <PatientBubble key={m.id} ini={ini} text={m.body} time={m.created_at} />
          ) : (
            <BotBubble key={m.id} text={m.body} time={m.created_at} />
          ),
        )}
      </div>
    </div>
  );
}

function PatientBubble({ ini, text, time }: { ini: string; text: string; time?: string | null }) {
  const critical =
    text.toLowerCase().includes("seene") ||
    text.toLowerCase().includes("chest") ||
    text.toLowerCase().includes("saans");
  return (
    <div className="flex flex-row-reverse gap-4">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-primary/20 bg-primary-container">
        <span className="font-label-md text-label-md text-on-primary-container">{ini}</span>
      </div>
      <div
        className={`max-w-[80%] rounded-2xl rounded-tr-sm border p-4 ${
          critical
            ? "relative overflow-hidden border-error/20 bg-error/10"
            : "border-primary/10 bg-primary/5"
        }`}
      >
        {critical && <div className="absolute bottom-0 left-0 top-0 w-1 bg-error" />}
        <p className={`font-body-md text-body-md text-on-surface ${critical ? "font-bold" : "font-medium"}`}>
          {text}
        </p>
        {time && (
          <span className="mt-1 block text-right font-mono-clinical text-[10px] text-on-surface-variant">
            {new Date(time).toLocaleTimeString()}
          </span>
        )}
      </div>
    </div>
  );
}

function BotBubble({ text, time }: { text: string; time?: string | null }) {
  return (
    <div className="flex gap-4">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-outline-variant bg-surface-container-high">
        <Icon name="smart_toy" className="text-[16px] text-on-surface-variant" />
      </div>
      <div className="max-w-[80%] rounded-2xl rounded-tl-sm border border-outline-variant bg-surface-container-low p-4">
        <p className="font-body-md text-body-md text-on-surface">{text}</p>
        {time && (
          <span className="mt-1 block font-mono-clinical text-[10px] text-on-surface-variant">
            {new Date(time).toLocaleTimeString()}
          </span>
        )}
      </div>
    </div>
  );
}

function EmptyMain({ onRefresh }: { onRefresh: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <Icon name="clinical_notes" className="mb-4 text-5xl text-primary-container" />
      <h2 className="font-headline-md text-headline-md text-on-surface">No active cases</h2>
      <p className="mt-2 max-w-sm font-body-md text-body-md text-on-surface-variant">
        Cases appear when patients message via WhatsApp webhook.
      </p>
      <button
        type="button"
        onClick={onRefresh}
        className="mt-6 flex items-center gap-2 rounded-xl bg-primary-container px-6 py-3 font-label-md text-on-primary-container"
      >
        <Icon name="refresh" />
        Refresh from API
      </button>
    </div>
  );
}
