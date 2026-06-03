import { useCallback, useEffect, useState } from "react";
import { api } from "@/api/client";
import type { CaseDetail, CaseSummary } from "@/api/types";

export function useCases() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const r = await api.listCases();
      setCases(r.cases);
      setError(null);
      setLastUpdated(new Date());
      return r.cases;
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      throw e;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh().catch(() => {});
    const id = window.setInterval(() => {
      refresh().catch(() => {});
    }, 8000);
    return () => window.clearInterval(id);
  }, [refresh]);

  return { cases, loading, error, lastUpdated, refresh };
}

export function useCaseDetail(phone: string | undefined) {
  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!phone) {
      setDetail(null);
      return null;
    }
    setLoading(true);
    try {
      const d = await api.getCase(phone);
      setDetail(d);
      setError(null);
      return d;
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      if (!msg.includes("404") && !msg.includes("Case not found")) {
        setError(msg);
      } else {
        setError(null);
      }
      setDetail(null);
      throw e;
    } finally {
      setLoading(false);
    }
  }, [phone]);

  useEffect(() => {
    refresh().catch(() => {});
  }, [refresh]);

  return { detail, loading, error, refresh };
}

export function useBackendHealth() {
  const [ok, setOk] = useState<boolean | null>(null);

  const check = useCallback(async () => {
    try {
      const r = await api.health();
      setOk(r.status === "ok");
    } catch {
      setOk(false);
    }
  }, []);

  useEffect(() => {
    check();
    const id = window.setInterval(check, 30000);
    return () => window.clearInterval(id);
  }, [check]);

  return { ok, check };
}
