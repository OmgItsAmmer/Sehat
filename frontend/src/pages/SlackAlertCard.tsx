import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/api/client";
import type { CaseSummary } from "@/api/types";
import { Icon } from "@/components/stitch/Icon";
import { patientLabel } from "@/lib/caseDisplay";

export function SlackAlertCard() {
  const [alerts, setAlerts] = useState<CaseSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    const r = await api.recentAlerts();
    setAlerts(r.alerts);
    setError(null);
  }, []);

  useEffect(() => {
    load()
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, [load]);

  async function handleRefresh() {
    setRefreshing(true);
    try {
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRefreshing(false);
    }
  }

  const alert = alerts.find((a) => a.priority === "P1") ?? alerts[0];

  return (
    <div className="min-h-dvh bg-[#F8F8F8] p-8 font-body-md">
      <header className="mb-8 flex items-start justify-between">
        <div>
          <Link to="/dashboard" className="font-label-md text-primary hover:underline">
            ← Clinic dashboard
          </Link>
          <h1 className="mt-2 font-headline-lg text-headline-lg text-on-surface">
            Slack P1 Alert Card
          </h1>
          <p className="font-body-md text-on-surface-variant">
            Live data from <code className="text-primary">GET /api/alerts/recent</code>
          </p>
        </div>
        <button
          type="button"
          disabled={refreshing}
          onClick={() => void handleRefresh()}
          className="flex items-center gap-2 rounded-lg border border-outline-variant bg-white px-4 py-2 font-label-md shadow-sm disabled:opacity-50"
        >
          <Icon name="refresh" className={refreshing ? "animate-spin" : ""} />
          Refresh
        </button>
      </header>

      {error && (
        <p className="mb-4 rounded-lg bg-error-container px-4 py-3 text-on-error-container">{error}</p>
      )}
      {loading && <p className="text-on-surface-variant">Loading alerts…</p>}

      <div className="mx-auto max-w-[700px] rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        {alert ? (
          <div className="pulse-red max-w-[600px] overflow-hidden rounded-[4px] border border-slate-200 bg-white shadow-sm">
            <div className="flex items-center gap-2 bg-secondary-container px-4 py-2">
              <span className="text-[15px] font-bold text-white">
                🚨 {alert.priority ?? "ALERT"} — Immediate action required
              </span>
            </div>
            <div className="space-y-4 p-4">
              <p className="text-[16px] font-bold text-on-surface">{patientLabel(alert.phone)}</p>
              <div className="rounded border-l-4 border-secondary bg-surface-container-low p-3">
                <span className="text-[14px] leading-relaxed text-on-surface">
                  &quot;{alert.last_message || alert.slots?.chief_complaint || "—"}&quot;
                </span>
              </div>
              {alert.reasoning && (
                <p className="text-[13px] text-on-surface-variant">{alert.reasoning}</p>
              )}
              <p className="text-[14px] font-bold text-secondary">
                Confidence {Math.round((alert.confidence || 0) * 100)}% · {alert.message_count} messages
              </p>
              <Link
                to={`/?case=${encodeURIComponent(alert.phone)}`}
                className="inline-flex h-9 items-center gap-1 rounded-[4px] border border-slate-300 bg-white px-4 text-[13px] font-bold text-on-surface shadow-sm hover:bg-slate-50"
              >
                Open in dashboard
              </Link>
            </div>
            <div className="border-t border-slate-100 bg-slate-50 px-4 py-2">
              <span className="text-[12px] text-slate-500">Sehat AI Triage · Do not ignore P1 alerts</span>
            </div>
          </div>
        ) : (
          !loading && <p className="text-on-surface-variant">No P1/P2 alerts in queue.</p>
        )}
      </div>
    </div>
  );
}
