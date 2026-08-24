import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { fetchStatistics } from "../api/client";
import type { StatisticsResponse } from "../api/types";
import { StatisticsPage } from "../features/statistics/StatisticsPage";

vi.mock("../api/client", () => ({
  fetchStatistics: vi.fn(),
}));

const statistics: StatisticsResponse = {
  ok: true,
  portfolio: {
    collection_status: "ok",
    schema_version: "content-portfolio-v4",
    generated_at: "2026-08-17T05:36:43Z",
    count: 1473,
    comparability: { comparable: true, issues: [] },
    source_status: { gsc: { status: "ok" }, business: { status: "ok" } },
    statistics: {
      click_change_decomposition: {
        observed_click_change: -114,
        exposure_effect: -12.4,
        ctr_effect: -101.6,
        top_drivers: [],
      },
      query_portfolio: {
        current: { observed_query_count: 12663, effective_queries: 4.94, hhi: 0.2, top_5_impression_share: 0.59 },
        previous: { hhi: 0.16, top_5_impression_share: 0.52 },
        new_queries: 5891,
        stable_queries: 6772,
        lost_queries: 5381,
      },
      ranking_opportunity: {
        positions_4_20_impressions: 343776,
        transitions: {
          "positions_11_20->positions_4_10": { cell_count: 482, current_impressions: 26183 },
          "positions_4_10->positions_11_20": { cell_count: 120, current_impressions: 3400 },
        },
      },
      ctr_benchmark: {
        global_ctr: 0.0078,
        recoverable_clicks: 1280,
        recoverable_clicks_unadjusted: 1430,
        multiple_testing: { method: "Benjamini–Hochberg FDR 0.05" },
      },
      search_change_confidence: {
        status: "ok",
        evidence_grade: "strong",
        click_change: { ci95: [-418.5, -49.5], probability_increase: 0.006, direction: "decrease" },
      },
      search_trend: {
        status: "ok",
        direction: "decreasing",
        click_slope_per_week: -12.3,
        latest_anomaly: true,
        weekly_clicks: [300, 290, 285, 270, 260, 250, 240, 230],
      },
      commercial_value: { currency: "USD", total_revenue: 120000, revenue_hhi: 0.42, attribution: "all_channel_context" },
      technical_issue_effects: {
        status: "insufficient_data",
        tested_rules: 0,
        significant_rules: 0,
        rules: ["BROKEN_INTERNAL_LINK", "DUPLICATE_TITLE"],
        causal_claim: false,
        interpretation: "Association after verified fixes only.",
      },
    },
  },
  coverage: {
    status: "ok",
    sources: { gsc: { count: 56, first: "2026-06-19", last: "2026-08-13" }, business: { count: 56, first: "2026-06-19", last: "2026-08-13" } },
  },
  regimes: { collection_status: "ok", count: 0, regimes: [] },
  business: {
    status: "ok",
    currency: "USD",
    windows: {
      current: {
        start_date: "2026-07-17",
        end_date: "2026-08-13",
        organic_product_views: 120,
        organic_add_to_carts: 18,
        organic_checkouts: 9,
        organic_purchases: 4,
        organic_revenue: 799.96,
        commerce_tracking: { status: "complete", missing_events: [] },
      },
    },
  },
};

describe("statistics workbench", () => {
  beforeEach(() => {
    vi.mocked(fetchStatistics).mockResolvedValue(statistics);
  });

  it("renders collection status, coverage and measurement regimes", async () => {
    render(<StatisticsPage projectId="shop" refreshKey={0} refreshing={false} onRefresh={vi.fn()} onNavigatePages={vi.fn()} />);
    await waitFor(() => expect(screen.getByRole("heading", { name: "Statistics" })).toBeTruthy());
    expect(screen.getByText("Collection status")).toBeTruthy();
    expect(screen.getByText("Daily history coverage")).toBeTruthy();
    expect(screen.getByText("Measurement regimes")).toBeTruthy();
    expect(screen.getByText("Organic commerce funnel")).toBeTruthy();
    expect(screen.getAllByText("120").length).toBeGreaterThan(0);
    expect(screen.getByText(/799.96 organic purchase revenue/)).toBeTruthy();
    expect(screen.getByText("1,473")).toBeTruthy();
    expect(screen.getByLabelText("Help: Daily history coverage")).toBeTruthy();
    expect(screen.getByLabelText("Help: Measurement regimes")).toBeTruthy();
    expect(screen.getByLabelText("Help: CTR benchmark")).toBeTruthy();
    expect(screen.getByText(/Comparability guard/)).toBeTruthy();
    expect(screen.getByText(/Internal, within-property benchmark/)).toBeTruthy();
    expect(screen.getAllByText("gsc").length).toBeGreaterThan(0);
    expect(screen.getAllByText("56 days").length).toBeGreaterThan(0);
    expect(screen.getAllByText("ok", { selector: '[class*="statusPill"]' }).every((pill) => pill.getAttribute("data-tone") === "success")).toBe(true);
    expect(screen.getByText("decrease", { selector: '[class*="statusPill"]' }).getAttribute("data-tone")).toBe("warning");
    expect(screen.getByText("Yes", { selector: '[class*="statusPill"]' }).getAttribute("data-tone")).toBe("warning");
    expect(screen.getByText("insufficient data", { selector: '[class*="statusPill"]' }).getAttribute("data-tone")).toBe("danger");
  });

  it("renders statistical blocks with crude trend bars and transitions", async () => {
    render(<StatisticsPage projectId="shop" refreshKey={0} refreshing={false} onRefresh={vi.fn()} onNavigatePages={vi.fn()} />);
    await waitFor(() => expect(screen.getByRole("heading", { name: "Statistics" })).toBeTruthy());
    expect(screen.getByText("Click change decomposition")).toBeTruthy();
    expect(screen.getByText("8-week click trend")).toBeTruthy();
    expect(screen.getByLabelText("8-week click trend")).toBeTruthy();
    expect(screen.getByText("Query portfolio")).toBeTruthy();
    expect(screen.getByText("Ranking transitions")).toBeTruthy();
    expect(screen.getByText("11–20 → 4–10")).toBeTruthy();
    expect(screen.getByText("CTR benchmark")).toBeTruthy();
    expect(screen.getByText("Commercial value")).toBeTruthy();
    expect(screen.getByText("Verified technical effects")).toBeTruthy();
  });

  it("queues statistics collection from the toolbar", async () => {
    const onRefresh = vi.fn();
    render(<StatisticsPage projectId="shop" refreshKey={0} refreshing={false} onRefresh={onRefresh} onNavigatePages={vi.fn()} />);
    await waitFor(() => expect(screen.getByRole("button", { name: /Run statistics collection/i })).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: /Run statistics collection/i }));
    expect(onRefresh).toHaveBeenCalled();
  });

  it("shows an empty state when no statistical projection exists", async () => {
    vi.mocked(fetchStatistics).mockResolvedValue({ ...statistics, portfolio: { ...statistics.portfolio, statistics: undefined } });
    render(<StatisticsPage projectId="shop" refreshKey={0} refreshing={false} onRefresh={vi.fn()} onNavigatePages={vi.fn()} />);
    await waitFor(() => expect(screen.getByText(/No statistical projection yet/i)).toBeTruthy());
  });
});
