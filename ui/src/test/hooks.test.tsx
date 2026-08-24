import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { fetchWorkspace } from "../api/client";
import type { Workspace } from "../api/types";
import { useWorkspace } from "../hooks/useWorkbenchData";

vi.mock("../api/client", () => ({
  fetchFiles: vi.fn(),
  fetchProjects: vi.fn(),
  fetchTechAudit: vi.fn(),
  fetchWorkspace: vi.fn(),
}));

function workspace(projectId: string): Workspace {
  return { project_id: projectId, project: { name: projectId, url: `https://${projectId}.example`, type: "existing" }, phase: "INIT", step: null, next: null, phase_order: [], phases: {}, evidence: { items: [], performance: { score: null, high_variance: null, metrics: { lcp: null, tbt: null, cls: null } }, technology: {}, channels: [], business: { status: "not_collected", windows: {} }, diff: {} }, changes: { count: 0, due: 0, counts: {}, items: [] }, content: { items: [], counts: {}, due_for_indexing: { count: 0, urls: [], items: [] }, ops: { schema_version: "1.0", generated_at: "", actions: [] }, portfolio: { collection_status: "not_collected", count: 0, counts: {}, items: [] } }, recent_files: [] };
}

describe("project-scoped data hooks", () => {
  it("ignores a stale workspace response after switching projects", async () => {
    let finishOld: (value: Workspace) => void = () => undefined;
    vi.mocked(fetchWorkspace).mockImplementation((projectId) => projectId === "old"
      ? new Promise((resolve) => { finishOld = resolve; })
      : Promise.resolve(workspace("new")));

    const { result, rerender } = renderHook(({ projectId }) => useWorkspace(projectId, 0), { initialProps: { projectId: "old" } });
    rerender({ projectId: "new" });
    await waitFor(() => expect(result.current.workspace?.project_id).toBe("new"));
    await act(async () => finishOld(workspace("old")));
    expect(result.current.workspace?.project_id).toBe("new");
  });
});
