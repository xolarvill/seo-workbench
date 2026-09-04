import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchProjects } from "../api/client";
import { WORKBENCH_EVENT_TYPES } from "../hooks/useWorkbenchData";

afterEach(() => vi.unstubAllGlobals());

describe("workbench API client", () => {
  it("surfaces server validation details", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      text: async () => JSON.stringify({ detail: "Accepted issues require a decision note." }),
    }));

    await expect(fetchProjects()).rejects.toThrow("Accepted issues require a decision note.");
  });

  it("uses the local API without a browser session token", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      text: async () => JSON.stringify({ projects: [] }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await fetchProjects();

    expect(fetchMock).toHaveBeenCalledWith("/api/v1/projects", expect.objectContaining({
      headers: { "Content-Type": "application/json" },
    }));
  });

  it("subscribes to domain updates that change visible work", () => {
    expect(WORKBENCH_EVENT_TYPES).toEqual(expect.arrayContaining([
      "browser.capture.saved",
      "integration.updated",
      "seo-change.updated",
      "technical-issue.updated",
    ]));
  });
});
