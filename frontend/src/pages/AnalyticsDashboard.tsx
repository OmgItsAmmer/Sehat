import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/api/client";
import type { Analytics } from "@/api/types";
import { Icon } from "@/components/stitch/Icon";

export function AnalyticsDashboard() {
  const [data, setData] = useState<Analytics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      const r = await api.analytics();
      setData(r);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    setLoading(true);
    load().finally(() => setLoading(false));
  }, [load]);

  async function handleRefresh() {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  }

  const bp = data?.by_priority ?? {};

  return (
    <div className="min-h-dvh font-body-md text-on-background">
      <header className="sticky top-0 z-50 flex h-16 w-full items-center justify-between border-b border-outline-variant bg-surface px-container-padding">
        <div className="flex items-center gap-8">
          <span className="font-headline-md text-headline-md font-bold text-primary">Sehat | صحت</span>
          <nav className="hidden items-center gap-6 md:flex">
            <Link className="font-body-md text-on-surface-variant hover:text-primary" to="/">
              Dashboard
            </Link>
            <Link className="border-b-2 border-primary pb-1 font-body-md font-bold text-primary" to="/analytics">
              Analytics
            </Link>
          </nav>
        </div>
        <button
          type="button"
          disabled={refreshing}
          onClick={() => void handleRefresh()}
          className="flex items-center gap-2 rounded-full px-4 py-2 text-on-surface-variant hover:bg-surface-container-low disabled:opacity-50"
        >
          <Icon name="refresh" className={refreshing ? "animate-spin" : ""} />
          <span className="font-label-md text-label-md">Refresh</span>
        </button>
      </header>

      <main className="mx-auto max-w-6xl space-y-gutter p-container-padding">
        <div>
          <h1 className="font-headline-lg text-headline-lg text-on-background">System Performance Overview</h1>
          <p className="font-body-md text-on-surface-variant">
            Data from <code className="text-primary">GET /api/analytics</code>
            {data?.as_of && ` · ${new Date(data.as_of).toLocaleString()}`}
          </p>
        </div>

        {error && (
          <p className="rounded-lg bg-error-container px-4 py-3 font-body-md text-on-error-container">{error}</p>
        )}
        {loading && <p className="text-on-surface-variant">Loading analytics…</p>}

        <div className="grid grid-cols-12 gap-gutter">
          <div className="col-span-12 rounded-xl border border-outline-variant bg-surface p-6 lg:col-span-4">
            <p className="font-label-md text-label-md uppercase tracking-wider text-on-surface-variant">
              Active cases
            </p>
            <h2 className="mt-2 font-display-lg text-display-lg text-primary">{data?.total_cases ?? "—"}</h2>
          </div>

          <div className="col-span-12 rounded-xl border border-outline-variant bg-surface p-6 lg:col-span-8">
            <p className="mb-4 font-label-md text-label-md uppercase tracking-wider text-on-surface-variant">
              Priority distribution
            </p>
            <div className="grid grid-cols-4 gap-4">
              <MetricBox label="P1" value={bp.P1 ?? 0} color="text-error" />
              <MetricBox label="P2" value={bp.P2 ?? 0} color="text-[#B45309]" />
              <MetricBox label="P3" value={bp.P3 ?? 0} color="text-on-surface-variant" />
              <MetricBox label="Unset" value={bp.unset ?? 0} color="text-outline" />
            </div>
          </div>

          <div className="col-span-12 grid gap-gutter md:grid-cols-2">
            <StatPanel title="Escalated" value={data?.escalated ?? 0} icon="e911_emergency" />
            <StatPanel title="Intake complete" value={data?.intake_complete ?? 0} icon="task_alt" />
            {data?.database && (
              <>
                <StatPanel title="DB patients" value={data.database.patients} icon="groups" />
                <StatPanel title="DB messages" value={data.database.messages} icon="forum" />
              </>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

function MetricBox({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="rounded-lg border border-outline-variant bg-surface-container-low p-4 text-center">
      <p className={`font-display-lg text-display-lg ${color}`}>{value}</p>
      <p className="font-label-md text-label-md text-on-surface-variant">{label}</p>
    </div>
  );
}

function StatPanel({ title, value, icon }: { title: string; value: number; icon: string }) {
  return (
    <div className="flex items-center gap-4 rounded-xl border border-outline-variant bg-surface p-5">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-surface-container-high">
        <Icon name={icon} className="text-primary" />
      </div>
      <div>
        <p className="font-label-md text-label-md text-on-surface-variant">{title}</p>
        <p className="font-headline-md text-headline-md text-on-surface">{value}</p>
      </div>
    </div>
  );
}
