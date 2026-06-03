import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { OverrideButtons } from "@/components/dashboard/OverrideButtons";
import { LoadingSkeleton, LoadingState } from "@/components/dashboard/LoadingState";
import { Icon } from "@/components/stitch/Icon";
import { useBackendHealth, useCaseDetail, useCases } from "@/hooks/useCases";
import {
  complaintLine,
  displayName,
  formatSlotLabel,
  initials,
  isWebSession,
  patientLabel,
  priorityBadgeClasses,
  priorityBorder,
} from "@/lib/caseDisplay";
import type { CaseDetail, CaseSummary, Priority } from "@/api/types";
import {
  BACKEND_OFFLINE,
  EMPTY_DETAIL,
  EMPTY_INTAKE_SLOTS,
  EMPTY_QUEUE,
  EMPTY_QUEUE_FILTER,
  LOADING_CASE,
  LOADING_DASHBOARD,
  NO_MESSAGES,
} from "@/lib/userMessages";

export function ClinicDashboard() {
  const { cases, error, lastUpdated, refresh: refreshCases, initialLoading: queueInitialLoading } =
    useCases();
  const { ok: backendOk, checking: backendChecking } = useBackendHealth();

  useEffect(() => {
    if (import.meta.env.DEV) {
      console.info(
        "[Sehat] API:",
        import.meta.env.VITE_API_URL?.trim() || "Vite proxy → http://127.0.0.1:8000",
      );
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

  const { detail, error: detailError, refresh: refreshDetail, initialLoading: detailInitialLoading } =
    useCaseDetail(selectedPhone || undefined);

  const filtered = useMemo(() => {
    const list = filter === "all" ? cases : cases.filter((c) => c.priority === filter);
    return [...list].sort((a, b) => {
      const at = a.last_activity_at ?? "";
      const bt = b.last_activity_at ?? "";
      return bt.localeCompare(at);
    });
  }, [cases, filter]);

  const selected = cases.find((c) => c.phone === selectedPhone);
  const p1 = cases.filter((c) => c.priority === "P1");

  const headerCase = useMemo((): CaseSummary | null => {
    if (!selected) return null;
    if (!detail) return selected;
    return { ...selected, ...detail, slots: detail.slots ?? selected.slots ?? {} };
  }, [selected, detail]);

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

  const showQueueLoader = queueInitialLoading;
  const showMainLoader = queueInitialLoading;

  return (
    <div className="flex h-dvh flex-col overflow-hidden bg-background font-body-md text-on-background">
      {backendOk === false && (
        <div className="relative z-50 flex items-center gap-2 bg-error-container px-container-padding py-3 text-on-error-container">
          <Icon name="cloud_off" className="shrink-0 text-[20px]" />
          <p className="font-body-md text-body-md">{BACKEND_OFFLINE}</p>
        </div>
      )}

      {error && (
        <div className="relative z-50 flex items-center justify-between gap-3 bg-error-container px-container-padding py-3 text-on-error-container">
          <p className="flex items-center gap-2 font-body-md text-body-md">
            <Icon name="error" className="shrink-0 text-[20px]" />
            {error}
          </p>
          <button
            type="button"
            onClick={() => void handleRefresh()}
            className="shrink-0 rounded-lg border border-on-error-container/30 px-3 py-1.5 font-label-md text-label-md transition-colors hover:bg-error/10 active:scale-[0.98]"
          >
            Retry
          </button>
        </div>
      )}

      {bannerOpen && p1[0] && (
        <div className="stat-banner-enter relative z-50 flex h-touch-target-min items-center justify-between bg-error px-container-padding text-on-error">
          <button
            type="button"
            className="flex flex-1 items-center gap-2 text-left transition-opacity hover:opacity-90 active:scale-[0.99]"
            onClick={() => selectCase(p1[0].phone)}
          >
            <Icon name="volume_up" filled className="text-[20px]" />
            <span className="font-headline-md text-headline-md uppercase tracking-tight">
              NEW P1 ARRIVAL: {patientLabel(p1[0].phone)}
            </span>
          </button>
          <button
            type="button"
            className="flex h-touch-target-min min-w-touch-target-min items-center justify-center rounded-full p-2 transition-colors hover:bg-error/20 active:scale-95"
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
            className={`h-2 w-2 rounded-full ${
              backendChecking
                ? "bg-outline animate-pulse"
                : backendOk === false
                  ? "bg-error"
                  : backendOk
                    ? "bg-primary-container"
                    : "bg-outline"
            }`}
            title={
              backendChecking
                ? "Checking server…"
                : backendOk === false
                  ? "Backend offline"
                  : backendOk
                    ? "Backend connected"
                    : "Checking…"
            }
          />
        </div>
        <div className="flex flex-1 justify-center">
          <div className="flex items-center gap-2 rounded-full border border-outline-variant bg-surface-container-low px-4 py-1.5">
            <span className={`h-2 w-2 rounded-full ${p1.length ? "bg-error pulse-red" : "bg-primary-container"}`} />
            <span className="font-label-md text-label-md text-on-surface">
              {showQueueLoader ? "Loading…" : `${cases.length} Active Cases`}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled={refreshing}
            onClick={() => void handleRefresh()}
            className="flex h-touch-target-min items-center gap-1 rounded-full px-3 py-2 text-on-surface-variant transition-all duration-200 hover:bg-surface-container-high hover:text-on-surface hover:shadow-sm active:scale-95 disabled:opacity-50 disabled:hover:bg-transparent disabled:hover:shadow-none"
            title="Reload cases from API"
          >
            <Icon name="refresh" className={refreshing ? "animate-spin" : ""} />
            <span className="hidden font-label-md text-label-md sm:inline">Refresh</span>
          </button>
          {p1[0] && (
            <Link
              to="/alerts/slack"
              className="flex h-touch-target-min w-[48px] items-center justify-center rounded-full p-2 text-on-surface-variant transition-all duration-200 hover:bg-surface-container-high hover:text-on-surface hover:shadow-sm active:scale-95"
              title="P1 Slack alert preview"
            >
              <Icon name="notifications" />
            </Link>
          )}
          <Link
            to="/analytics"
            className="flex h-touch-target-min w-[48px] items-center justify-center rounded-full p-2 text-on-surface-variant transition-all duration-200 hover:bg-surface-container-high hover:text-on-surface hover:shadow-sm active:scale-95"
            title="Analytics"
          >
            <Icon name="monitoring" />
          </Link>
        </div>
      </header>

      <div className="flex min-h-0 w-full flex-1 pt-[48px]">
        <aside className="flex h-[calc(100dvh-48px)] w-80 shrink-0 flex-col overflow-hidden border-r border-outline-variant bg-surface-container-low p-unit">
          <div className="shrink-0 border-b border-outline-variant px-4 py-4">
            <h2 className="font-headline-md text-headline-md text-primary">Case Queue</h2>
            <p className="font-mono-clinical text-mono-clinical text-on-surface-variant">
              {showQueueLoader
                ? "Syncing queue…"
                : lastUpdated
                  ? `Updated ${lastUpdated.toLocaleTimeString()}`
                  : "Live Traffic"}
            </p>
          </div>
          <div className="flex shrink-0 flex-col gap-1 px-2 py-2">
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

          <div className="custom-scrollbar flex min-h-0 flex-1 flex-col gap-unit overflow-y-auto overscroll-contain px-2 pt-2 pb-4">
            {showQueueLoader && <LoadingSkeleton lines={4} />}
            {!showQueueLoader && filtered.length === 0 && (
              <div className="mx-2 rounded-xl border border-dashed border-outline-variant bg-surface px-4 py-6 text-center">
                <Icon name="inbox" className="mb-2 text-3xl text-outline" />
                <p className="font-body-md text-body-md text-on-surface-variant">
                  {cases.length === 0 ? EMPTY_QUEUE : EMPTY_QUEUE_FILTER}
                </p>
              </div>
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
        </aside>

        <main className="flex h-[calc(100dvh-48px)] min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-background">
          {showMainLoader ? (
            <LoadingState label={queueInitialLoading ? LOADING_DASHBOARD : LOADING_CASE} />
          ) : !selected ? (
            <EmptyMain onRefresh={() => void handleRefresh()} />
          ) : (
            <>
              <div className="flex shrink-0 flex-col gap-2 px-4 pt-3 pb-2">
                {detailError && (
                  <p className="flex shrink-0 items-center gap-1.5 rounded-md bg-error-container px-2 py-1.5 font-body-md text-on-error-container">
                    <Icon name="error" className="shrink-0 text-[14px]" />
                    {detailError}
                  </p>
                )}
                <PatientHeader c={headerCase ?? selected} loading={detailInitialLoading} />
                {showOverridePanel(detail ?? selected) && (
                  <OverrideButtons
                    phone={selected.phone}
                    priority={(detail ?? selected).priority}
                    canOverride={canOverrideCase(detail ?? selected)}
                    onDone={() => void handleRefresh()}
                  />
                )}
                {detail?.reasoning && <AiReasoningPanel reasoning={detail.reasoning} />}
              </div>

              <div className="flex min-h-0 flex-1 flex-col px-4 pb-3">
                <ConversationThread
                  loading={detailInitialLoading}
                  messages={detail?.messages ?? []}
                  phone={selected.phone}
                  reply={detail?.reply ?? selected.reply}
                  dbMessages={detail?.db_messages}
                />
              </div>
            </>
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
  const base =
    "mx-2 flex cursor-pointer items-center gap-2 rounded-lg px-3 py-2 transition-all duration-200 active:scale-[0.98]";
  const cls = active
    ? highlight
      ? `${base} rounded-xl bg-primary-container font-bold text-on-primary-container shadow-sm`
      : `${base} bg-surface-container-high font-bold text-on-surface shadow-sm`
    : `${base} text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface hover:shadow-sm`;
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
      className={`group relative cursor-pointer overflow-hidden rounded-r-lg border-y border-r border-outline-variant bg-surface p-3 text-left shadow-[0_4px_12px_rgba(0,0,0,0.05)] ${priorityBorder(p)} border-l-[4px] transition-all duration-200 ${
        active ? "ring-2 ring-primary-container shadow-md" : ""
      } ${p === "P1" ? "hover:bg-error/5 hover:shadow-md" : "hover:bg-surface-container-low hover:shadow-md"} active:scale-[0.99]`}
    >
      <div className="relative z-10 mb-1 flex items-start justify-between">
        <div className="flex items-center gap-2">
          {p === "P1" && <span className="h-2 w-2 rounded-full bg-error pulse-red" />}
          {p === "P2" && <span className="h-2 w-2 rounded-full bg-[#F59E0B]" />}
          {p !== "P1" && p !== "P2" && <span className="h-2 w-2 rounded-full bg-outline" />}
          <span className={`font-label-md text-label-md font-bold uppercase ${priorityBadgeClasses(p)}`}>
            {p ?? (c.source === "database" ? "DB" : "PENDING")}
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

function showOverridePanel(c: CaseSummary): boolean {
  return c.source !== "database";
}

function canOverrideCase(c: CaseSummary): boolean {
  return !!(c.awaiting_human_review || c.escalated);
}

function AiReasoningPanel({ reasoning }: { reasoning: string }) {
  return (
    <section className="dashboard-ai-reasoning relative shrink-0 overflow-hidden rounded-lg border px-3 py-2">
      <p className="relative mb-1 flex items-center gap-1.5 font-label-md text-label-md font-semibold uppercase tracking-wide text-primary">
        <Icon name="psychology" className="text-[16px]" />
        AI reasoning
      </p>
      <p className="relative line-clamp-3 font-body-md text-body-md text-on-surface">{reasoning}</p>
    </section>
  );
}

function PatientHeader({ c, loading }: { c: CaseSummary; loading?: boolean }) {
  const isP1 = c.priority === "P1";
  const status = c.slots_complete
    ? "Intake complete"
    : c.pending_slot
      ? `Awaiting: ${formatSlotLabel(c.pending_slot)}`
      : "In triage";
  const slotEntries = Object.entries(c.slots ?? {});

  return (
    <div
      className={`relative overflow-hidden rounded-lg border bg-surface px-3 py-2 shadow-sm ${
        isP1 ? "border-error" : "border-outline-variant"
      }`}
    >
      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
        <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
          {isP1 && (
            <span className="inline-flex shrink-0 items-center gap-1 rounded-full bg-error px-2 py-0.5 text-on-error">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-white" />
              <span className="font-label-md text-[10px] font-bold uppercase tracking-wide">P1</span>
            </span>
          )}
          <h1 className="font-headline-md text-headline-md text-on-surface">{patientLabel(c.phone)}</h1>
          <span className="font-body-md text-body-md text-on-surface-variant">
            {displayName(c)} · {Math.round((c.confidence || 0) * 100)}%
          </span>
        </div>
        <div className="flex shrink-0 items-center gap-3 text-right font-mono-clinical text-[11px]">
          <span className={isP1 ? "font-semibold text-error" : "text-on-surface-variant"}>
            {c.escalated ? "ESCALATED" : "ACTIVE"}
          </span>
          <span className="text-on-surface-variant">{status}</span>
        </div>
      </div>
      <section className="mt-2 border-t border-outline-variant/25 pt-2">
        <p className="mb-1.5 flex items-center gap-1 font-label-md text-[10px] font-semibold uppercase tracking-wide text-on-surface-variant">
          <Icon name="clinical_notes" className="text-[14px]" />
          Intake details
          {loading && (
            <Icon name="progress_activity" className="ml-1 animate-spin text-[12px] text-primary" />
          )}
          {c.pending_slot && !c.slots_complete && (
            <span className="ml-1 normal-case font-normal text-primary">
              · asking for {formatSlotLabel(c.pending_slot)}
            </span>
          )}
        </p>
        {loading && slotEntries.length === 0 ? (
          <div className="animate-pulse space-y-1.5" aria-hidden="true">
            <div className="h-10 rounded-md bg-surface-container-high" />
            <div className="h-10 w-4/5 rounded-md bg-surface-container-high" />
          </div>
        ) : slotEntries.length === 0 ? (
          <p className="font-body-md text-[12px] text-on-surface-variant">{EMPTY_INTAKE_SLOTS}</p>
        ) : (
          <dl className="flex flex-wrap gap-x-4 gap-y-1.5">
            {slotEntries.map(([key, value]) => (
              <div
                key={key}
                className="min-w-[140px] rounded-md border border-outline-variant/40 bg-surface-container-lowest px-2 py-1"
              >
                <dt className="font-label-md text-[10px] uppercase tracking-wide text-on-surface-variant">
                  {formatSlotLabel(key)}
                </dt>
                <dd className="font-body-md text-[12px] font-medium text-on-surface">{value}</dd>
              </div>
            ))}
          </dl>
        )}
      </section>
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
  const hasDb = dbMessages && dbMessages.length > 0;
  const hasSession = messages.length > 0 || reply;
  const showRedisOnly = !hasDb && hasSession;

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden rounded-lg border border-outline-variant bg-surface">
      <div className="shrink-0 border-b border-outline-variant/60 bg-surface-container-lowest px-3 py-1.5">
        <h3 className="font-label-md text-label-md font-semibold text-on-surface">Intake conversation</h3>
        <p className="font-body-md text-[11px] text-on-surface-variant">
          {isWebSession(phone) ? "Web patient chat" : "WhatsApp intake thread"}
        </p>
      </div>
      <div className="custom-scrollbar flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto overscroll-contain p-3">
        {loading && !hasSession && !hasDb && (
          <LoadingState label={LOADING_CASE} compact />
        )}
        {!loading && !hasSession && !hasDb && (
          <p className="text-body-md text-on-surface-variant">{NO_MESSAGES}</p>
        )}
        {showRedisOnly &&
          messages.map((text, i) => <PatientBubble key={`s-${i}`} ini={ini} text={text} />)}
        {showRedisOnly && reply && <BotBubble text={reply} />}
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
    <div className="flex flex-row-reverse gap-2">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-primary/20 bg-primary-container">
        <span className="text-[11px] font-semibold text-on-primary-container">{ini}</span>
      </div>
      <div
        className={`max-w-[80%] rounded-xl rounded-tr-sm border p-2.5 ${
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
    <div className="flex gap-2">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-outline-variant bg-surface-container-high">
        <Icon name="smart_toy" className="text-[14px] text-on-surface-variant" />
      </div>
      <div className="max-w-[80%] rounded-xl rounded-tl-sm border border-outline-variant bg-surface-container-low p-2.5">
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
    <div className="flex h-full flex-col items-center justify-center p-container-padding text-center">
      <Icon name="clinical_notes" className="mb-4 text-5xl text-primary-container" />
      <h2 className="font-headline-md text-headline-md text-on-surface">Waiting for patients</h2>
      <p className="mt-2 max-w-sm font-body-md text-body-md text-on-surface-variant">
        {EMPTY_DETAIL}
      </p>
      <button
        type="button"
        onClick={onRefresh}
        className="mt-6 flex items-center gap-2 rounded-xl bg-primary-container px-6 py-3 font-label-md text-on-primary-container shadow-md transition-all duration-200 hover:bg-primary hover:text-on-primary hover:shadow-lg active:scale-[0.98]"
      >
        <Icon name="refresh" />
        Refresh queue
      </button>
    </div>
  );
}
