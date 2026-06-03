import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/api/client";
import type { CaseDetail, CaseSummary } from "@/api/types";
import { friendlyApiError } from "@/lib/userMessages";

const QUEUE_POLL_MS = 8000;
const DETAIL_POLL_MS = 2000;

export function useCases() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const hasLoaded = useRef(false);

  const refresh = useCallback(async (opts?: { silent?: boolean }) => {
    const silent = opts?.silent && hasLoaded.current;
    if (!silent) setLoading(true);
    try {
      const r = await api.listCases();
      setCases(r.cases);
      setError(null);
      setLastUpdated(new Date());
      hasLoaded.current = true;
      return r.cases;
    } catch (e) {
      if (!silent) setError(friendlyApiError(e));
      throw e;
    } finally {
      if (!silent) setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh().catch(() => {});
    const id = window.setInterval(() => {
      refresh({ silent: true }).catch(() => {});
    }, QUEUE_POLL_MS);
    return () => window.clearInterval(id);
  }, [refresh]);

  return { cases, loading, error, lastUpdated, refresh, initialLoading: loading && !hasLoaded.current };
}

export function useCaseDetail(phone: string | undefined) {
  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [loading, setLoading] = useState(() => Boolean(phone));
  const [error, setError] = useState<string | null>(null);
  const hasLoaded = useRef(false);
  const phoneRef = useRef(phone);

  const refresh = useCallback(
    async (opts?: { silent?: boolean }) => {
      if (!phone) {
        setDetail(null);
        setLoading(false);
        hasLoaded.current = false;
        return null;
      }
      const silent = opts?.silent && hasLoaded.current;
      if (!silent) setLoading(true);
      try {
        const d = await api.getCase(phone);
        setDetail(d);
        setError(null);
        hasLoaded.current = true;
        return d;
      } catch (e) {
        const msg = friendlyApiError(e);
        if (!msg.includes("no longer active") && !msg.includes("could not be found")) {
          if (!silent) setError(msg);
        } else if (!silent) {
          setError(null);
        }
        if (!silent) setDetail(null);
        throw e;
      } finally {
        if (!silent) setLoading(false);
      }
    },
    [phone],
  );

  useEffect(() => {
    if (phoneRef.current !== phone) {
      phoneRef.current = phone;
      hasLoaded.current = false;
      setDetail(null);
      setLoading(Boolean(phone));
    }
    refresh().catch(() => {});
  }, [refresh, phone]);

  useEffect(() => {
    if (!phone) return;
    const id = window.setInterval(() => {
      refresh({ silent: true }).catch(() => {});
    }, DETAIL_POLL_MS);
    return () => window.clearInterval(id);
  }, [phone, refresh]);

  return {
    detail,
    loading,
    error,
    refresh,
    initialLoading: loading && !hasLoaded.current,
  };
}

export function useBackendHealth() {
  const [ok, setOk] = useState<boolean | null>(null);
  const [checking, setChecking] = useState(true);

  const check = useCallback(async () => {
    setChecking(true);
    try {
      const r = await api.health();
      setOk(r.status === "ok");
    } catch {
      setOk(false);
    } finally {
      setChecking(false);
    }
  }, []);

  useEffect(() => {
    check();
    const id = window.setInterval(check, 30000);
    return () => window.clearInterval(id);
  }, [check]);

  return { ok, checking, check };
}
