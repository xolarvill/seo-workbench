import { useCallback, useEffect, useState } from "react";

import { fetchFiles, fetchProjects, fetchWorkspace } from "../api/client";
import type { FileSummary, ProjectSummary, WorkbenchEvent, Workspace } from "../api/types";


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

  const refresh = useCallback(() => {
    if (!projectId) return;
    setLoading(true);
    fetchWorkspace(projectId)
      .then((value) => {
        setWorkspace(value);
        setError(null);
      })
      .catch((reason: Error) => setError(reason.message))
      .finally(() => setLoading(false));
  }, [projectId]);

  useEffect(refresh, [refresh, refreshKey]);
  return { workspace, error, loading, refresh };
}

export function useFiles(projectId: string | null, refreshKey: number) {
  const [files, setFiles] = useState<FileSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    if (!projectId) return;
    fetchFiles(projectId).then(setFiles).catch((reason: Error) => setError(reason.message));
  }, [projectId]);

  useEffect(refresh, [refresh, refreshKey]);
  return { files, error, refresh };
}

const EVENT_TYPES = ["file.changed", "file.saved", "job.started", "job.updated", "job.finished"];

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
    EVENT_TYPES.forEach((type) => source.addEventListener(type, listener as EventListener));
    return () => {
      EVENT_TYPES.forEach((type) => source.removeEventListener(type, listener as EventListener));
      source.close();
    };
  }, [onEvent, onConnection]);
}
