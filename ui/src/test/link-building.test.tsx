import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { fetchBacklinkView } from "../api/client";
import type { BacklinkViewResponse } from "../api/types";
import { LinkBuildingPage } from "../features/link-building/LinkBuildingPage";

vi.mock("../api/client", () => ({
  fetchBacklinkView: vi.fn(),
}));

const response: BacklinkViewResponse = {
  ok: true,
  collection_status: "ok",
  generated_at: "2026-08-21T00:00:00Z",
  captured_at: "2026-08-21T00:00:00Z",
  source: { name: "provider" },
  complete_snapshot: true,
  summary: { links: 2, active_links: 2, referring_domains: 2, target_pages: 2, target_reclaim_candidates: 1 },
  comparison: { status: "no_baseline", new_observed: [], lost: [], missing_unconfirmed: [] },
  top_anchors: [{ anchor: "desk setup", count: 1 }],
  claims: { authority_score: "not_calculated" },
  columns: [
    { id: "source_domain", label: "Referring domain", default: true },
    { id: "source_url", label: "Source URL", default: true },
    { id: "target_url", label: "Target URL", default: true },
    { id: "anchor", label: "Anchor", default: true },
    { id: "provider_status", label: "Status", default: true },
    { id: "follow", label: "Follow", default: true },
    { id: "target_status_code", label: "Target HTTP", default: true },
    { id: "target_reclaim_candidate", label: "Reclaim", default: true },
  ],
  rows: [
    {
      id: "link-1",
      source_domain: "publisher.example",
      source_url: "https://publisher.example/guide",
      target_url: "https://example.com/guide",
      anchor: "desk setup",
      follow: true,
      provider_status: "active",
      target_status_code: null,
      target_reclaim_candidate: false,
    },
  ],
  pagination: { offset: 0, limit: 50, total: 1 },
};

describe("link building workbench", () => {
  let resolveRequest: ((value: BacklinkViewResponse) => void) | undefined;

  beforeEach(() => {
    vi.mocked(fetchBacklinkView).mockResolvedValue(response);
  });

  it("shows progressive loading, backlink evidence and filter controls", async () => {
    vi.mocked(fetchBacklinkView).mockImplementation(() => new Promise((resolve) => { resolveRequest = resolve; }));
    render(<LinkBuildingPage projectId="shop" refreshKey={0} />);
    expect(screen.getByRole("status").textContent).toContain("Loading backlink records");
    expect(document.querySelectorAll('[class*="skeletonLine"]').length).toBeGreaterThan(0);

    resolveRequest?.(response);
    await waitFor(() => expect(screen.getByRole("heading", { name: "Link building" })).toBeTruthy());
    expect(screen.getByText("publisher.example")).toBeTruthy();
    expect(screen.getByText("Top anchors")).toBeTruthy();
    expect(screen.getByText(/Complete snapshot/)).toBeTruthy();

    fireEvent.change(screen.getByLabelText("Status"), { target: { value: "active" } });
    await waitFor(() => expect(fetchBacklinkView).toHaveBeenLastCalledWith("shop", expect.objectContaining({ status: "active" })));
  });
});
