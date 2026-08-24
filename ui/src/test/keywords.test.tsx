import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { KeywordViewResponse } from "../api/types";
import { KeywordsWorkbenchPage } from "../features/keywords/KeywordsWorkbenchPage";

const view: KeywordViewResponse = {
  ok: true,
  dataset: "keywords",
  scope: "queue",
  rows: [
    { row_key: "desk shelf", keyword: "desk shelf", managed: true, source: "semrush_manual", intent: "commercial", priority_score: 76, volume_hint: 3200, cpc_hint: .65, decision: "unreviewed", stage: "researched", mapping: "unmapped", research_path: "strategy/keyword-dives/product-desk-shelf.md", owner_urls: ["https://example.com/products/desk-shelf"], market: { provider: "dataforseo", location_code: 2840, language_code: "en", collected_at: "2026-08-19T00:00:00Z", search_volume: 3600, cpc: .7, competition: .62, intent: "commercial", monthly_searches: [{ year: 2026, month: 7, search_volume: 3600 }, { year: 2026, month: 8, search_volume: 4200 }], serp: { se_results_count: 1200000, item_types: ["organic", "people_also_ask"], results: [{ rank: 1, title: "Desk Shelf", url: "https://example.com/desk-shelf", domain: "example.com", description: "A desktop shelf result." }] }, cost_usd: .004 }, gsc: { query: "Desk Shelf", clicks: 3, impressions: 120, ctr: .025, position: 8 }, cluster_gsc: { clicks: 5, impressions: 170, ctr: .0294, position: 8.6 }, observed_queries: [{ query: "Desk Shelf", clicks: 3, impressions: 120, ctr: .025, position: 8, owner_urls: ["https://example.com/products/desk-shelf"] }, { query: "Desk Shelf Ideas", clicks: 2, impressions: 50, ctr: .04, position: 10, owner_urls: ["https://example.com/blogs/desk-shelf-ideas"] }] },
    { row_key: "monitor riser", keyword: "monitor riser", managed: false, source: "gsc", priority_score: 52, decision: "unreviewed", stage: "needs_decision", mapping: "unmapped", gsc: { query: "Monitor Riser", clicks: 1, impressions: 80, ctr: .0125, position: 12 }, cluster_gsc: { clicks: 1, impressions: 80, ctr: .0125, position: 12 }, observed_queries: [{ query: "Monitor Riser", clicks: 1, impressions: 80, ctr: .0125, position: 12, owner_urls: [] }] },
  ],
  pagination: { offset: 0, limit: 50, total: 2 },
  summary: { total: 12664, queue: 169, queue_stages: { needs_decision: 162, researched: 1, demand_check: 3, mapped: 3 }, unmanaged: 12658, unmapped: 2, decisions: { unreviewed: 2 }, stages: { needs_decision: 12661, researched: 1, demand_check: 2, handed_off: 1 } },
  facets: { decision: ["unreviewed"], stage: ["needs_decision", "researched", "demand_check"], intent: ["commercial"], source: ["gsc", "semrush_manual"], mapping: ["unmapped"] },
  sources: { gsc: { path: "audits/gsc/search-analytics/latest.json", count: 2, collection_status: "ok", generated_at: "2026-08-18T00:00:00Z" }, dataforseo: { path: "audits/keywords/dataforseo/latest.json", count: 1, collection_status: "complete", generated_at: "2026-08-19T00:00:00Z" } },
  options: { clusters: [{ id: "desk", label: "Desk" }], content_items: [{ id: "post-1", label: "Desk guide", status: "planned" }] },
  revision: "a".repeat(64),
};

function response(payload: unknown, ok = true, status = 200) {
  return { ok, status, text: async () => JSON.stringify(payload) };
}

afterEach(() => vi.unstubAllGlobals());

describe("keyword workbench", () => {
  it("shows the progressive status and skeleton rows before evidence arrives", async () => {
    let resolve: (value: unknown) => void = () => undefined;
    const pending = new Promise<unknown>((done) => { resolve = done; });
    vi.stubGlobal("fetch", vi.fn().mockReturnValue(pending));
    const { container } = render(<KeywordsWorkbenchPage projectId="shop" refreshKey={0} refreshing={false} onRefresh={vi.fn()} onOpenFile={vi.fn()} />);

    await waitFor(() => expect(screen.getByRole("status").textContent).toContain("Loading keywords"));
    expect(container.querySelectorAll("tbody tr")).toHaveLength(7);
    resolve(response(view));
    await waitFor(() => expect(screen.getByText("desk shelf")).toBeTruthy());
    const firstRow = screen.getByText("desk shelf").closest("tr");
    expect(firstRow?.querySelector(".statusPill")?.getAttribute("data-tone")).toBe("warning");
    expect(firstRow?.querySelectorAll(".statusPill")[1]?.getAttribute("data-tone")).toBe("success");
  });

  it("renders the pipeline funnel, scope toggle, filters and cross-page selection", async () => {
    const fetchMock = vi.fn().mockResolvedValue(response(view));
    vi.stubGlobal("fetch", fetchMock);
    render(<KeywordsWorkbenchPage projectId="shop" refreshKey={0} refreshing={false} onRefresh={vi.fn()} onOpenFile={vi.fn()} />);

    await waitFor(() => expect(screen.getByRole("heading", { name: "Keywords" })).toBeTruthy());
    expect(screen.getByRole("tab", { name: /Opportunity Pool/ }).getAttribute("aria-selected")).toBe("true");
    expect(screen.getByLabelText("Help: Opportunity Pool")).toBeTruthy();
    expect(screen.getByLabelText("Help: Topic Map")).toBeTruthy();
    expect(screen.getByLabelText("Help: Research")).toBeTruthy();
    expect(within(screen.getByLabelText("Keyword pipeline summary")).getAllByRole("button").map((button) => button.querySelector("span")?.textContent)).toEqual(["Decide", "Map", "Demand", "Research"]);
    expect(within(screen.getByLabelText("Keyword pipeline summary")).getByText("In content").closest("a")?.getAttribute("href")).toBe("#/content");
    expect(screen.getByRole("button", { name: /Decision queue/ }).getAttribute("aria-pressed")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: /All/ }));
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes("scope=map"))).toBe(true));
    expect(screen.queryByLabelText("Select current page")).toBeNull();
    expect(screen.getByRole("button", { name: /Decision queue/ })).toBeTruthy();
    expect(screen.getByText(/Evidence view/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /Decision queue/ }));
    expect(screen.getByText(/Only rows needing your judgment/)).toBeTruthy();
    expect(screen.getByRole("columnheader", { name: /^Volume/ })).toBeTruthy();
    expect(screen.getByRole("columnheader", { name: /^CPC/ })).toBeTruthy();
    expect(screen.getByRole("columnheader", { name: /^Comp/ })).toBeTruthy();
    fireEvent.click(screen.getByLabelText("Select current page"));
    expect(screen.getByText("2 selected")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Select all 2 filtered" }));
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes("limit=1000"))).toBe(true));
  });

  it("shows owner column and per-state next-step actions", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(view)));
    render(<KeywordsWorkbenchPage projectId="shop" refreshKey={0} refreshing={false} onRefresh={vi.fn()} onOpenFile={vi.fn()} />);
    await waitFor(() => expect(screen.getByText("desk shelf")).toBeTruthy());

    const deskRow = screen.getByText("desk shelf").closest("tr")!;
    expect(within(deskRow).getByText(/products\/desk-shelf/)).toBeTruthy();
    expect(within(deskRow).getByText("Brief →")).toBeTruthy();
    const monitorRow = screen.getByText("monitor riser").closest("tr")!;
    expect(within(monitorRow).getByText("gap — no owner")).toBeTruthy();
    expect(within(monitorRow).getByText("Decide")).toBeTruthy();
  });

  it("renders em-dash counts instead of NaN when the summary lacks queue fields", async () => {
    const stale = { ...view, summary: { total: 12664, unmanaged: 12658, unmapped: 2, decisions: { unreviewed: 2 }, stages: { needs_decision: 1 } } } as unknown as KeywordViewResponse;
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(stale)));
    render(<KeywordsWorkbenchPage projectId="shop" refreshKey={0} refreshing={false} onRefresh={vi.fn()} onOpenFile={vi.fn()} />);
    await waitFor(() => expect(screen.getByText("desk shelf")).toBeTruthy());

    const buttons = within(screen.getByLabelText("Keyword workspace scope")).getAllByRole("button");
    expect(buttons[0].querySelector("strong")?.textContent).toBe("—");
    expect(buttons[1].querySelector("strong")?.textContent).toBe("—");
    expect(screen.queryByText("NaN")).toBeNull();
  });

  it("separates strategy fields from exact and cluster query evidence", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(view)));
    render(<KeywordsWorkbenchPage projectId="shop" refreshKey={0} refreshing={false} onRefresh={vi.fn()} onOpenFile={vi.fn()} />);
    await waitFor(() => expect(screen.getByText("desk shelf")).toBeTruthy());

    fireEvent.click(screen.getByText("desk shelf"));
    expect(screen.getByRole("heading", { name: /^Pipeline/ })).toBeTruthy();
    expect(screen.getByText(/Step 5 · handoff/)).toBeTruthy();
    expect(screen.getByText(/Steps 5-8 · content side/)).toBeTruthy();
    expect(screen.getByRole("heading", { name: /^Strategy and ownership/ })).toBeTruthy();
    expect(screen.getByRole("heading", { name: /^Query evidence/ })).toBeTruthy();
    expect(screen.getByRole("heading", { name: /^Market and SERP evidence/ })).toBeTruthy();
    expect(screen.getByText("SERP analysis")).toBeTruthy();
    expect(screen.getByText("A desktop shelf result.")).toBeTruthy();
    expect(screen.getByText("Desk Shelf Ideas")).toBeTruthy();
    expect(screen.getByText("170")).toBeTruthy();
  });

  it("shows one topic row with target and ownership conflicts", async () => {
    const topicView: KeywordViewResponse = {
      ...view,
      dataset: "topics",
      rows: [{ row_key: "desk", cluster_ref: "desk", representative_keyword: "desk shelf", keyword_count: 2, query_count: 2, keywords: ["desk shelf", "desk shelf ideas"], target_urls: ["/products/desk-shelf", "/blogs/desk-shelf-ideas"], target_content_ids: ["post-1"], impressions: 170, target_conflict: true, ownership_conflict: true }],
      pagination: { offset: 0, limit: 50, total: 1 },
    };
    const fetchMock = vi.fn().mockImplementation((url: string) => Promise.resolve(response(String(url).includes("dataset=topics") ? topicView : view)));
    vi.stubGlobal("fetch", fetchMock);
    render(<KeywordsWorkbenchPage projectId="shop" refreshKey={0} refreshing={false} onRefresh={vi.fn()} onOpenFile={vi.fn()} />);
    await waitFor(() => expect(screen.getByText("desk shelf")).toBeTruthy());

    fireEvent.click(screen.getByRole("tab", { name: /Topic Map/ }));
    await waitFor(() => expect(screen.getByText("target conflict")).toBeTruthy());
    expect(screen.getByText("ownership conflict")).toBeTruthy();
    expect(screen.getByText("2 keywords · 2 observed queries")).toBeTruthy();
  });

  it("applies a batch decision and reloads after a revision conflict", async () => {
    let patchCount = 0;
    const fetchMock = vi.fn().mockImplementation((url: string, options?: RequestInit) => {
      if (options?.method === "PATCH") {
        patchCount += 1;
        return patchCount === 1
          ? Promise.resolve(response({ updated: 2, revision: "b".repeat(64) }))
          : Promise.resolve(response({ detail: { code: "revision_conflict", current_revision: "c".repeat(64) } }, false, 409));
      }
      return Promise.resolve(response(view));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<KeywordsWorkbenchPage projectId="shop" refreshKey={0} refreshing={false} onRefresh={vi.fn()} onOpenFile={vi.fn()} />);
    await waitFor(() => expect(screen.getByText("desk shelf")).toBeTruthy());

    fireEvent.click(screen.getByLabelText("Select current page"));
    fireEvent.click(screen.getByRole("button", { name: "Apply" }));
    await waitFor(() => expect(screen.getByText("2 keywords updated.")).toBeTruthy());
    const firstPatch = fetchMock.mock.calls.find(([, options]) => options?.method === "PATCH");
    expect(JSON.parse(String(firstPatch?.[1]?.body))).toEqual(expect.objectContaining({ keywords: ["desk shelf", "monitor riser"], patch: { decision: "prioritize" } }));

    fireEvent.click(screen.getByLabelText("Select current page"));
    fireEvent.click(screen.getByRole("button", { name: "Apply" }));
    await waitFor(() => expect(screen.getByRole("alert").textContent).toMatch(/changed in another session/i));
    expect(fetchMock.mock.calls.filter(([url]) => String(url).includes("/keywords/view")).length).toBeGreaterThan(1);
  });

  it("opens existing research and hands missing research to Codex", async () => {
    const openFile = vi.fn();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
    const fetchMock = vi.fn().mockImplementation((url: string, options?: RequestInit) => {
      if (String(url).includes("/handoff") && String(url).includes("desk+shelf")) return Promise.resolve(response({ ok: true, keyword: "desk shelf", existing_path: "strategy/keyword-dives/product-desk-shelf.md", skill: "skills/keyword-deep-dive/SKILL.md" }));
      if (String(url).includes("/handoff")) return Promise.resolve(response({ ok: true, keyword: "monitor riser", existing_path: null, skill: "skills/keyword-deep-dive/SKILL.md", output_path: "strategy/keyword-dives/info-monitor-riser.md", prompt: "Research monitor riser" }));
      if (String(url).includes("/codex/open") && options?.method === "POST") return Promise.resolve(response({ ok: true }, true, 202));
      return Promise.resolve(response(view));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<KeywordsWorkbenchPage projectId="shop" refreshKey={0} refreshing={false} onRefresh={vi.fn()} onOpenFile={openFile} />);
    await waitFor(() => expect(screen.getByText("desk shelf")).toBeTruthy());

    fireEvent.click(screen.getByText("desk shelf"));
    await waitFor(() => expect(screen.getByRole("button", { name: "Open research" })).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: "Open research" }));
    await waitFor(() => expect(openFile).toHaveBeenCalledWith("strategy/keyword-dives/product-desk-shelf.md"));
    fireEvent.click(screen.getAllByRole("button", { name: "Close keyword details" })[1]);

    fireEvent.click(screen.getByText("monitor riser"));
    await waitFor(() => expect(screen.getByRole("button", { name: "Agent deep dive" })).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: "Agent deep dive" }));
    await waitFor(() => expect(writeText).toHaveBeenCalledWith("Research monitor riser"));
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes("/codex/open"))).toBe(true);
    expect(await screen.findByText(/Expected output: strategy\/keyword-dives\/info-monitor-riser.md/)).toBeTruthy();
  });
});
