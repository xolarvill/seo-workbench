import { useCallback, useEffect, useRef, useState, type Dispatch, type SetStateAction } from "react";

import { fetchFiles, fetchPresentationStatus, fetchProjects, fetchReportArchive, fetchSeoChanges, fetchTechAudit, fetchWorkspace } from "../api/client";
import type { FileSummary, PresentationStatus, ProjectSummary, ReportArchive, ReportArchiveParams, SeoChangesResponse, TechAuditData, WorkbenchEvent, Workspace } from "../api/types";

export function useDebouncedValue<T>(value: T, delay = 250): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delay);
    return () => window.clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

export function useViewData<T, P extends object>(projectId: string, params: P, refreshKey: unknown, fetcher: (projectId: string, params: P) => Promise<T>): { data: T | null; error: string | null; loading: boolean; setData: Dispatch<SetStateAction<T | null>>; setError: Dispatch<SetStateAction<string | null>> } {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const requestId = useRef(0);

  useEffect(() => {
    const request = ++requestId.current;
    setLoading(true);
    setError(null);
    fetcher(projectId, params)
      .then((value) => { if (request === requestId.current) setData(value); })
      .catch((reason: Error) => { if (request === requestId.current) setError(reason.message); })
      .finally(() => { if (request === requestId.current) setLoading(false); });
    return () => { requestId.current += 1; };
  }, [fetcher, params, projectId, refreshKey]);

  return { data, error, loading, setData, setError };
}


export function useProjects() {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchProjects().then(setProjects).catch((reason: Error) => setError(reason.message));
  }, []);

  return { projects, error };
}

export function useWorkspace(projectId: string | null, refreshKey: number) {
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const requestId = useRef(0);

  const refresh = useCallback(() => {
    if (!projectId) return;
    const request = ++requestId.current;
    setLoading(true);
    fetchWorkspace(projectId)
      .then((value) => {
        if (request !== requestId.current) return;
        setWorkspace(value);
        setError(null);
      })
      .catch((reason: Error) => { if (request === requestId.current) setError(reason.message); })
      .finally(() => { if (request === requestId.current) setLoading(false); });
  }, [projectId]);

  useEffect(() => { requestId.current += 1; setWorkspace(null); setError(null); }, [projectId]);
  useEffect(refresh, [refresh, refreshKey]);
  return { workspace, error, loading, refresh };
}

export function useFiles(projectId: string | null, refreshKey: number) {
  const [files, setFiles] = useState<FileSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const requestId = useRef(0);

  const refresh = useCallback(() => {
    if (!projectId) return;
    const request = ++requestId.current;
    fetchFiles(projectId)
      .then((value) => { if (request === requestId.current) { setFiles(value); setError(null); } })
      .catch((reason: Error) => { if (request === requestId.current) setError(reason.message); });
  }, [projectId]);

  useEffect(() => { requestId.current += 1; setFiles([]); setError(null); }, [projectId]);
  useEffect(refresh, [refresh, refreshKey]);
  return { files, error, refresh };
}

export function useReportArchive(projectId: string | null, refreshKey: number, params: ReportArchiveParams = {}) {
  const [archive, setArchive] = useState<ReportArchive | null>(null);
  const [error, setError] = useState<string | null>(null);
  const requestId = useRef(0);

  const refresh = useCallback(() => {
    if (!projectId) return;
    const request = ++requestId.current;
    fetchReportArchive(projectId, params)
      .then((value) => { if (request === requestId.current) { setArchive(value); setError(null); } })
      .catch((reason: Error) => { if (request === requestId.current) setError(reason.message); });
  }, [projectId, params]);

  useEffect(() => { requestId.current += 1; setArchive(null); setError(null); }, [projectId]);
  useEffect(refresh, [refresh, refreshKey]);
  return { archive, error, refresh };
}

export function usePresentationStatus(projectId: string | null, refreshKey: number) {
  const [status, setStatus] = useState<PresentationStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const requestId = useRef(0);

  const refresh = useCallback(() => {
    if (!projectId) return;
    const request = ++requestId.current;
    fetchPresentationStatus(projectId)
      .then((value) => { if (request === requestId.current) { setStatus(value); setError(null); } })
      .catch((reason: Error) => { if (request === requestId.current) setError(reason.message); });
  }, [projectId]);

  useEffect(() => { requestId.current += 1; setStatus(null); setError(null); }, [projectId]);
  useEffect(refresh, [refresh, refreshKey]);
  return { status, error, refresh };
}

export function useSeoChanges(projectId: string | null, refreshKey: number) {
  const [data, setData] = useState<SeoChangesResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const requestId = useRef(0);

  const refresh = useCallback(() => {
    if (!projectId) return;
    const request = ++requestId.current;
    fetchSeoChanges(projectId)
      .then((value) => { if (request === requestId.current) { setData(value); setError(null); } })
      .catch((reason: Error) => { if (request === requestId.current) setError(reason.message); });
  }, [projectId]);

  useEffect(() => { requestId.current += 1; setData(null); setError(null); }, [projectId]);
  useEffect(refresh, [refresh, refreshKey]);
  return { data, error, refresh };
}

export function useTechAudit(projectId: string | null, refreshKey: number) {
  const [data, setData] = useState<TechAuditData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const requestId = useRef(0);

  const refresh = useCallback(() => {
    if (!projectId) return;
    const request = ++requestId.current;
    setLoading(true);
    fetchTechAudit(projectId)
      .then((value) => { if (request === requestId.current) { setData(value); setError(null); } })
      .catch((reason: Error) => { if (request === requestId.current) setError(reason.message); })
      .finally(() => { if (request === requestId.current) setLoading(false); });
  }, [projectId]);

  useEffect(() => { requestId.current += 1; setData(null); setError(null); }, [projectId]);
  useEffect(refresh, [refresh, refreshKey]);
  useEffect(() => {
    if (data?.run?.status !== "running") return;
    const timer = window.setInterval(refresh, 2000);
    return () => window.clearInterval(timer);
  }, [data?.run?.status, refresh]);
  return { data, error, loading, refresh };
}

export const WORKBENCH_EVENT_TYPES = [
  "browser.capture.saved",
  "content.updated",
  "file.changed",
  "file.saved",
  "integration.updated",
  "job.finished",
  "job.started",
  "job.updated",
  "report.star.updated",
  "seo-change.created",
  "seo-change.evaluated",
  "seo-change.updated",
  "tech-audit.schedule.updated",
  "technical-issue.updated",
  "workflow.updated",
];

export function useWorkbenchEvents(onEvent: (event: WorkbenchEvent) => void, onConnection?: (connected: boolean) => void) {
  useEffect(() => {
    const source = new EventSource("/api/v1/events");
    const listener = (message: MessageEvent<string>) => {
      try {
        onEvent(JSON.parse(message.data) as WorkbenchEvent);
      } catch {
        // Ignore malformed local events and wait for the next valid message.
      }
    };
    source.onopen = () => onConnection?.(true);
    source.onerror = () => onConnection?.(false);
    WORKBENCH_EVENT_TYPES.forEach((type) => source.addEventListener(type, listener as EventListener));
    return () => {
      WORKBENCH_EVENT_TYPES.forEach((type) => source.removeEventListener(type, listener as EventListener));
      source.close();
    };
  }, [onEvent, onConnection]);
}
