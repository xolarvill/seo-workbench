import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { createSeoChange, evaluateSeoChange, fetchFiles, fetchMarkdown, fetchPageDetail, fetchPageView, fetchPresentationStatus, fetchReportArchive, fetchSeoChanges, fetchTechAudit, fetchTechAuditDetail, fetchTechAuditView, fetchTutorial, fetchTutorials, updateContentStatus, updateSeoChangeStatus, updateTechAuditSchedule, updateTechnicalIssueStatus } from "../api/client";
import type { FileSummary, Job, PageDetailResponse, PageViewResponse, PresentationStatus, ReportArchive, SeoChangesResponse, TechAuditData, TechAuditDetailResponse, TechAuditViewResponse, TutorialDocument, TutorialSummary, Workspace } from "../api/types";
import { AppShell } from "../components/AppShell";
import { Drawer } from "../components/Drawer";
import { Pagination, SearchField, pageLabel } from "../components/WorkbenchControls";
import { ContentWorkbenchPage } from "../features/content/ContentWorkbenchPage";
import { MarkdownPreview } from "../features/editor/MarkdownPreview";
import MarkdownOverlay from "../features/editor/MarkdownOverlay";
import { EvidenceStatusCard } from "../features/overview/EvidenceRail";
import { OverviewPage } from "../features/overview/OverviewPage";
import { OwnersPage } from "../features/owners/OwnersPage";
import { FilesPage } from "../features/files/FilesPage";
import { PagesWorkbenchPage } from "../features/pages/PagesWorkbenchPage";
import { ReportsPage } from "../features/reports/ReportsPage";
import { TutorialsPage } from "../features/tutorials/TutorialsPage";
import { TechnicalAuditPage } from "../features/technical-audit/TechnicalAuditPage";
import { WorkflowPage } from "../features/workflow/WorkflowPage";

vi.mock("../api/client", () => ({
  createSeoChange: vi.fn(),
  evaluateSeoChange: vi.fn(),
  fetchFiles: vi.fn(),
  fetchMarkdown: vi.fn(),
  fetchPageDetail: vi.fn(),
  fetchPageView: vi.fn(),
  fetchPresentationStatus: vi.fn(),
  fetchReportArchive: vi.fn(),
  fetchSeoChanges: vi.fn(),
  fetchTechAudit: vi.fn(),
  fetchTechAuditDetail: vi.fn(),
  fetchTechAuditView: vi.fn(),
  fetchTutorial: vi.fn(),
  fetchTutorials: vi.fn(),
  updateContentStatus: vi.fn(),
  updateSeoChangeStatus: vi.fn(),
  updateTechAuditSchedule: vi.fn(),
  updateTechnicalIssueStatus: vi.fn(),
}));

const project = {
  id: "shop",
  path: "/tmp/shop",
  name: "Example Shop",
  url: "https://www.example.com",
  type: "shopify",
  phase: "TECHNICAL_AUDIT",
  selectable: true,
  valid_state: true,
};

describe("shared workbench controls", () => {
  it("keeps search clearing and pagination boundaries consistent", () => {
    const changeSearch = vi.fn();
    const changeOffset = vi.fn();
    render(<><SearchField label="Search records" value="desk" onChange={changeSearch} /><Pagination offset={50} limit={50} total={120} onOffsetChange={changeOffset} onLimitChange={vi.fn()} /></>);
    fireEvent.click(screen.getByRole("button", { name: "Clear search records" }));
    fireEvent.click(screen.getByRole("button", { name: "Next page" }));
    expect(changeSearch).toHaveBeenCalledWith("");
    expect(changeOffset).toHaveBeenCalledWith(100);
    expect(pageLabel(100, 50, 120)).toBe("101–120 of 120");
  });

  it("closes drawers with Escape and restores focus", () => {
    function Harness() {
      const [open, setOpen] = useState(false);
      return <><button type="button" onClick={() => setOpen(true)}>Open drawer</button>{open ? <Drawer label="Test drawer" eyebrow="Test" title="Details" onClose={() => setOpen(false)}><button type="button">Action</button></Drawer> : null}</>;
    }
    render(<Harness />);
    const opener = screen.getByRole("button", { name: "Open drawer" });
    opener.focus();
    fireEvent.click(opener);
    expect(screen.getAllByRole("button", { name: "Close details" })[1]).toBe(document.activeElement);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("dialog", { name: "Test drawer" })).toBeNull();
    expect(opener).toBe(document.activeElement);
  });
});

const workspace: Workspace = {
  project_id: "shop",
  project: { name: "Example Shop", url: "https://example.com", type: "shopify" },
  phase: "TECHNICAL_AUDIT",
  step: { id: "collect", label: "Collect evidence", status: "pending" },
  next: { phase: "TECHNICAL_AUDIT", step: "collect", label: "Collect evidence", skill: "technical-audit", context: [], output: "audits/technical.md" },
  phase_order: ["DISCOVERY", "TECHNICAL_AUDIT"],
  phases: {
    DISCOVERY: { status: "done", steps: [{ id: "brief", label: "Brief", status: "done" }] },
    TECHNICAL_AUDIT: { status: "in_progress", steps: [{ id: "collect", label: "Collect evidence", status: "pending" }] },
  },
  evidence: {
    items: [],
    performance: { score: 71, high_variance: false, metrics: { lcp: 2200, tbt: 170, cls: 0.08 } },
    technology: {},
    channels: [],
    business: { status: "not_collected", windows: {} },
    diff: {},
  },
  changes: {
    count: 1,
    due: 1,
    counts: { shipped: 1 },
    items: [{ id: "chg-1", status: "shipped", change_type: "content", changed_at: "2026-07-01", review_date: "2026-07-29", hypothesis: "Improve qualified clicks", urls: ["https://example.com/page"], classification: "winning" }],
  },
  content: {
    items: [],
    counts: {},
    due_for_indexing: { count: 0, urls: [], items: [] },
    ops: { schema_version: "content-ops-v1", generated_at: "2026-07-29T00:00:00Z", actions: [] },
    portfolio: {
      collection_status: "ok",
      count: 1,
      counts: { refresh: 1 },
      statistics: {
        click_change_decomposition: { observed_click_change: -12, exposure_effect: 8, ctr_effect: -20 },
        query_portfolio: { current: { effective_queries: 18.4, hhi: .31, top_5_impression_share: .52 }, previous: { effective_queries: 17.1, hhi: .34, top_5_impression_share: .55 }, new_queries: 12, stable_queries: 44, lost_queries: 7 },
        ranking_opportunity: { positions_4_20_impressions: 3400 },
        commercial_value: { revenue_hhi: .42 },
      },
      items: [{ id: "rec1", title: "Refresh this guide", url: "https://example.com/guide", decision: "refresh", recommendation: "Refresh intent coverage" }],
    },
  },
  recent_files: [],
};

const tutorialSummaries: TutorialSummary[] = [
  { slug: "seo-foundations", title: "SEO 基础知识与证据模型", description: "Evidence", category: "Foundations", source: "SEO基础知识与证据模型.md" },
  { slug: "growth-diagnosis", title: "SEO 增长诊断与拆解", description: "Growth", category: "Foundations", source: "SEO增长诊断与拆解.md" },
];

const tutorialDocuments: Record<string, TutorialDocument> = {
  "seo-foundations": { ...tutorialSummaries[0], content: "# Foundations\n\n[Growth](SEO增长诊断与拆解.md)", revision: "one", modified_at: "2026-07-18T00:00:00Z" },
  "growth-diagnosis": { ...tutorialSummaries[1], content: "# Growth diagnosis", revision: "two", modified_at: "2026-07-18T00:00:00Z" },
};

const contentFiles: FileSummary[] = [
  { path: "content/briefs/rec1.md", name: "rec1.md", size: 1200, modified_at: "2026-07-29T00:00:00Z" },
  { path: "content/reports/daily.md", name: "daily.md", size: 900, modified_at: "2026-07-29T00:00:00Z" },
];

const reportArchive: ReportArchive = {
  reports_dir: "reports",
  weekly: [
    {
      path: "reports/2026_week_34_work_done.md",
      year: 2026,
      week: 34,
      name: "2026_week_34_work_done.md",
      start: "08-17",
      end: "08-23",
      modified_at: "2026-08-18T00:00:00Z",
      size: 900,
      checked: 2,
      total: 3,
      carry_over: 1,
      inherited_from: [33],
      follow_ups: [{ date: "2026-09-11", text: "Cable Hub 变更效果评估" }],
    },
  ],
  sub_reports: [
    { path: "reports/20260817_tech_theme-fix-handoff.md", date: "20260817", category: "tech", topic: "theme-fix-handoff", modified_at: "2026-08-17T00:00:00Z", size: 800 },
  ],
  categories: {
    tech: [{ path: "reports/20260817_tech_theme-fix-handoff.md", date: "20260817", category: "tech", topic: "theme-fix-handoff", modified_at: "2026-08-17T00:00:00Z", size: 800 }],
  },
  latest_week: { year: 2026, week: 34 },
  filters: { query: "", category: "", year: null, month: null },
  progress: {
    follow_ups: [
      { date: "2026-08-01", text: "旧遗留项", year: 2026, week: 33, path: "reports/2026_week_33_work_done.md", state: "overdue" },
      { date: "2026-09-11", text: "Cable Hub 变更效果评估", year: 2026, week: 34, path: "reports/2026_week_34_work_done.md", state: "future" },
    ],
    overdue: 1,
    upcoming: 0,
    carried_over_tracks: [
      { task: "Cable Hub 变更效果评估", entries: [{ year: 2026, week: 33, path: "reports/2026_week_33_work_done.md" }, { year: 2026, week: 34, path: "reports/2026_week_34_work_done.md" }], spans: 2 },
    ],
  },
};

const presentationStatus: PresentationStatus = {
  schema_version: "seo-presentation-v1",
  status: "ready_with_warnings",
  ready: true,
  report_date: "2026-08-28",
  target_week: { year: 2026, week: 35 },
  max_statistics_age_hours: 72,
  statistics: { status: "partial", completed_at: "2026-08-28T06:00:00Z", age_hours: 2, common_finalized_end_date: "2026-08-26" },
  checks: [{ code: "statistics_fresh", label: "Statistics freshness", passed: true, required: true, detail: "completed 2h ago" }],
  warnings: ["business measurement regime changed inside the comparison range"],
  artifact: { path: "reports/presentations/2026_week_35.pdf", size: 48000, generated_at: "2026-08-28T08:00:00Z", week: { year: 2026, week: 35 } },
};

const seoChanges: SeoChangesResponse = {
  schema_version: "seo-change-list-v1",
  collection_status: "ok",
  count: 2,
  changes: [
    { id: "chg-2", changed_at: "2026-08-19", review_date: "2026-09-16", status: "shipped", change_type: "metadata", urls: ["https://example.com/products/desk"], hypothesis: "Improve the product title", expected_metrics: ["ctr", "clicks"], note: "Updated title and description", updates: [] },
    { id: "chg-1", changed_at: "2026-08-01", review_date: "2026-08-29", status: "reviewed", change_type: "content", urls: ["https://example.com/guide"], hypothesis: "Expand the guide", expected_metrics: ["clicks"], note: "Evidence checked", updates: [{ updated_at: "2026-08-20T00:00:00Z", status: "reviewed", note: "Reviewed evidence" }] },
  ],
};

const contentWorkspace: Workspace = {
  ...workspace,
  content: {
    ...workspace.content,
    items: [
      { id: "rec1", status: "approved", title: "Ready Post", slug: "ready-post", target_keyword: "desk shelf", word_count: 860, scheduled_at: "2026-08-01T00:00:00Z", live_url: "https://example.com/blogs/articles/ready-post", warnings: [{ code: "images", message: "Resolve image refs" }] },
      { id: "rec2", status: "review", title: "Review Post", slug: "review-post", review_thread_id: "om_1" },
    ],
    counts: { approved: 1, review: 1 },
    due_for_indexing: { count: 1, urls: ["https://example.com/blogs/articles/ready-post"], items: [] },
    ops: {
      schema_version: "content-ops-v1",
      generated_at: "2026-07-29T00:00:00Z",
      actions: [
        { id: "review_digest", cadence: "every_30m", due: true, count: 1, command: "content review-digest", items: [] },
        { id: "gsc_inspect", cadence: "daily", due: true, count: 1, command: "gsc inspect --limit <n>", items: [] },
        { id: "content_report", cadence: "daily", due: true, count: 2, command: "content report --period daily", items: [] },
      ],
    },
  },
  recent_files: contentFiles,
};

const techAudit: TechAuditData = {
  status: "ready",
  snapshot: { generated_at: "2026-08-03T00:00:00Z", collection_status: "ok" },
  history: [
    { run_id: "run-2", kind: "tech-audit", status: "ok", collection_status: "ok", generated_at: "2026-08-03T00:00:00Z", active: false, snapshot_available: true },
    { run_id: "run-1", kind: "tech-audit", status: "ok", collection_status: "ok", generated_at: "2026-08-02T00:00:00Z", active: false, snapshot_available: true },
  ],
  run: null,
  summary: { pages: 18, issues: 4, four_oh_four: 2, successful_pages: 16, crawled_pages: 18, discovered_unique: 21, queued_remaining: 3, continuation_available: true },
  schedule: { enabled: true, every_minutes: 60, notify_role: "seo", profile: "hexcal-seo", next_run_at: "2026-08-03T01:00:00Z" },
  last_recrawl: null,
  pages: [
    { page_id: "page-1", url: "https://example.com/missing", final_url: "https://example.com/missing", status_code: 404, indexability: { status: "unknown", indexable: null }, title: "", meta_description: "", meta_keywords: "", h1: [], h2: [], inlink_count: 3, crawl_depth: 1, response_time_ms: 20, response_size: 100, issue_ids: ["HTTP_4XX"], priority: 65, last_recrawl_at: null, last_recrawl_status: null },
    { page_id: "page-2", url: "https://example.com/old", final_url: "https://example.com/old", status_code: 404, indexability: { status: "unknown", indexable: null }, title: "Old", meta_description: "", meta_keywords: "", h1: [], h2: [], inlink_count: 0, crawl_depth: 2, response_time_ms: 20, response_size: 100, issue_ids: ["HTTP_4XX"], priority: 20, last_recrawl_at: null, last_recrawl_status: null },
  ],
  pagination: { offset: 0, limit: 500, total: 2 },
};

const viewerPages: TechAuditViewResponse = {
  ok: true,
  dataset: "pages",
  snapshot: techAudit.snapshot,
  columns: [
    { id: "url", label: "URL", default: true },
    { id: "status_code", label: "Status", default: true },
    { id: "title", label: "Title", default: true },
  ],
  rows: [
    { row_key: "https://example.com/missing", url: "https://example.com/missing", status_code: 404, title: "", indexability: { status: "unknown" } },
    { row_key: "https://example.com/old", url: "https://example.com/old", status_code: 404, title: "Old", indexability: { status: "unknown" } },
  ],
  pagination: { offset: 0, limit: 50, total: 2 },
};

const viewerLinks: TechAuditViewResponse = { ...viewerPages, dataset: "links", columns: [{ id: "url", label: "URL", default: true }, { id: "crawled", label: "Crawled", default: true }], rows: [{ row_key: "https://help.example.com/", url: "https://help.example.com/", crawled: true }], pagination: { offset: 0, limit: 50, total: 1 } };
const viewerIssues: TechAuditViewResponse = { ...viewerPages, dataset: "issues", columns: [{ id: "rule_id", label: "Rule", default: true }, { id: "severity", label: "Severity", default: true }, { id: "url", label: "URL", default: true }], rows: [{ row_key: "fingerprint-1", url: "https://example.com/missing", rule_id: "HTTP_4XX", severity: "high" }], pagination: { offset: 0, limit: 50, total: 1 } };
const viewerDetail: TechAuditDetailResponse = { ok: true, dataset: "pages", row: { row_key: "https://example.com/missing", url: "https://example.com/missing", title: "Missing", status_code: 404, h1: ["Primary heading"], h2: ["Supporting heading"] }, issues: [{ rule_id: "HTTP_4XX", severity: "high", url: "https://example.com/missing", evidence: { status_code: 404 }, remediation_guidance: "Restore URL" }, { rule_id: "HTTP_4XX", severity: "high", url: "https://example.com/old", evidence: { status_code: 404 }, remediation_guidance: "Restore URL" }, { rule_id: "META_TITLE_MISSING", severity: "medium", url: "https://example.com/untitled", evidence: { title: "" }, remediation_guidance: "Add a title" }], recrawl: null, diff: { comparable: true, changes: [], warnings: [] } };

const pageView: PageViewResponse = {
  ok: true,
  dataset: "actions",
  columns: [{ id: "urgency", label: "Urgency", default: true }, { id: "title", label: "Action", default: true }, { id: "url", label: "URL", default: true }],
  rows: [{ row_key: "portfolio:https://example.com/page", source: "portfolio", source_id: "https://example.com/page", group: "now", urgency: "high", title: "Refresh guide", url: "https://example.com/page", status: "refresh", reason: "Refresh intent coverage.", target_view: "#/pages" }],
  pagination: { offset: 0, limit: 50, total: 1 },
  summary: { groups: { now: 1, review: 2, watch: 3 }, pages: 10, query_conflicts: 2 },
  sources: { portfolio: { status: "ok", generated_at: "2026-08-09T00:00:00Z" }, gsc: { status: "ok", generated_at: "2026-08-09T00:00:00Z" }, technical: { status: "not_collected" } },
};
const pageDetail: PageDetailResponse = { ok: true, dataset: "actions", row: pageView.rows[0], page: { row_key: "https://example.com/page", url: "https://example.com/page", title: "Refresh guide", page_type: "article", sources: { gsc_current: true, gsc_previous: true, technical: true, content: false }, metrics: { previous: { clicks: 4, impressions: 100, ctr: .04, position: 8.5 }, current: { clicks: 5, impressions: 120, ctr: .041667, position: 7.9 }, delta: { clicks: { absolute: 1, relative: .25 }, impressions: { absolute: 20, relative: .2 }, ctr: { absolute: .001667, relative: .041675 }, position: { absolute: -.6, relative: -.070588 } } }, statistics: { click_change_decomposition: { observed_click_change: 1, exposure_effect: 2.2, ctr_effect: -1.2, top_drivers: [{ query: "desk cable management", url: "https://example.com/page", click_change: 1, exposure_effect: 2.2, ctr_effect: -1.2 }] }, query_portfolio: { current: { observed_query_count: 8, effective_queries: 4.5 }, new_queries: 3, stable_queries: 5, lost_queries: 2 }, ranking_opportunity: { positions_4_20_impressions: 96, current_impression_share: { top_3: .2 } }, commercial_value: { quadrant: "grow", revenue_share: .35 } }, top_queries: [{ query: "desk cable management", clicks: 3, impressions: 80, ctr: .0375, position: 6.2 }], multiple_page_queries: [{ query: "cable tray", owner_count: 2, total_impressions: 140, ownership: { hhi: .54, primary_owner_share: .642857 }, owners: [{ url: "https://example.com/page", impressions: 90 }, { url: "https://example.com/other", impressions: 50 }] }], technical: { status_code: 200, indexability: { status: "indexable", indexable: true }, canonical: "https://example.com/page", h1: ["Cable management guide"], issue_count: 2, crawl_depth: 2, inlink_count: 14, outlink_count: 8, response_time_ms: 240 } }, sources: pageView.sources };
pageDetail.internal_link_candidates = { status: "ok", reason: "Manual implementation and verification required.", rows: [{ source_url: "https://example.com/page", target_url: "https://example.com/products/desk", anchor_candidates: ["standing desk", "desk"], already_linked: false, cluster_ref: "desk-cluster", reason: "Same mapped keyword cluster." }] };

beforeEach(() => {
  vi.mocked(fetchFiles).mockResolvedValue(contentFiles);
  vi.mocked(fetchReportArchive).mockResolvedValue(reportArchive);
  vi.mocked(fetchPresentationStatus).mockResolvedValue(presentationStatus);
  vi.mocked(fetchSeoChanges).mockResolvedValue(seoChanges);
  vi.mocked(fetchMarkdown).mockResolvedValue({ path: "reports/2026_week_34_work_done.md", content: "# Week 34\n\n## 速览\n\n- [x] 完成", revision: "r1", modified_at: "2026-08-18T00:00:00Z" });
  vi.mocked(fetchPageView).mockImplementation(async (_projectId, params) => ({ ...pageView, dataset: params.dataset, columns: params.dataset === "actions" ? pageView.columns : [{ id: params.dataset === "pages" ? "title" : "query", label: params.dataset === "pages" ? "Page" : "Query", default: true }], rows: params.dataset === "actions" ? pageView.rows : [] }));
  vi.mocked(fetchPageDetail).mockResolvedValue(pageDetail);
  vi.mocked(createSeoChange).mockResolvedValue({ ok: true });
  vi.mocked(evaluateSeoChange).mockResolvedValue({ report: { classification: "winning" } });
  vi.mocked(updateContentStatus).mockResolvedValue({ item: { id: "content-1", status: "indexed" }, queue: contentWorkspace.content });
  vi.mocked(updateSeoChangeStatus).mockResolvedValue({ ok: true });
  vi.mocked(updateTechnicalIssueStatus).mockResolvedValue({ ok: true });
  vi.mocked(fetchTutorials).mockResolvedValue(tutorialSummaries);
  vi.mocked(fetchTutorial).mockImplementation(async (slug) => tutorialDocuments[slug]);
  vi.mocked(fetchTechAudit).mockResolvedValue(techAudit);
  vi.mocked(fetchTechAuditView).mockImplementation(async (_projectId, params) => params.dataset === "pages" ? viewerPages : params.dataset === "links" ? viewerLinks : viewerIssues);
  vi.mocked(fetchTechAuditDetail).mockResolvedValue(viewerDetail);
  vi.mocked(updateTechAuditSchedule).mockResolvedValue(techAudit.schedule);
});

describe("workbench frontend", () => {
  it("renders project navigation and routes button clicks", () => {
    const navigate = vi.fn();
    render(<AppShell projects={[project]} selectedProject="shop" activeView="overview" onProjectChange={vi.fn()} onNavigate={navigate}><p>Workspace</p></AppShell>);
    expect(screen.getAllByText("Example Shop").length).toBeGreaterThan(0);
    expect(screen.getAllByText("example.com").length).toBeGreaterThan(0);
    fireEvent.click(screen.getAllByRole("button", { name: /Plan/i })[0]);
    expect(navigate).toHaveBeenCalledWith("workflow");
    fireEvent.click(screen.getAllByRole("button", { name: /Keywords/i })[0]);
    expect(navigate).toHaveBeenCalledWith("keywords");
    fireEvent.click(screen.getAllByRole("button", { name: /Owners/i })[0]);
    expect(navigate).toHaveBeenCalledWith("owners");
    fireEvent.click(screen.getAllByRole("button", { name: /Pages/i })[0]);
    expect(navigate).toHaveBeenCalledWith("pages");
    fireEvent.click(screen.getAllByRole("button", { name: /Link building/i })[0]);
    expect(navigate).toHaveBeenCalledWith("link-building");
    fireEvent.click(screen.getAllByRole("button", { name: /Connections/i })[0]);
    expect(navigate).toHaveBeenCalledWith("integrations");
    fireEvent.click(screen.getAllByRole("button", { name: /Guides/i })[0]);
    expect(navigate).toHaveBeenCalledWith("tutorials");
    expect(screen.queryByRole("button", { name: "Run audit" })).toBeNull();
  });

  it("closes mobile navigation after choosing a destination", () => {
    const navigate = vi.fn();
    const { container } = render(<AppShell projects={[project]} selectedProject="shop" activeView="overview" onProjectChange={vi.fn()} onNavigate={navigate}><p>Workspace</p></AppShell>);
    const menu = container.querySelector("details");
    expect(menu).not.toBeNull();
    menu!.open = true;
    fireEvent.click(within(menu!).getByRole("button", { name: "Connections" }));
    expect(menu!.open).toBe(false);
    expect(navigate).toHaveBeenCalledWith("integrations");
  });

  it("renders expandable technical audit subnavigation", () => {
    const navigate = vi.fn();
    const section = vi.fn();
    render(<AppShell projects={[project]} selectedProject="shop" activeView="audits" activeAuditSection="url-inventory" onAuditSectionChange={section} onProjectChange={vi.fn()} onNavigate={navigate}><p>Workspace</p></AppShell>);
    expect(screen.getByRole("button", { name: "URL inventory" }).className).toContain("activeTechnicalSubitem");
    fireEvent.click(screen.getByRole("button", { name: "Schedule" }));
    expect(navigate).toHaveBeenCalledWith("audits");
    expect(section).toHaveBeenCalledWith("automation");
  });

  it("renders Connections sections with the shared expandable subnavigation", () => {
    const navigate = vi.fn();
    const section = vi.fn();
    render(<AppShell projects={[project]} selectedProject="shop" activeView="integrations" activeConnectionSection="optional" onConnectionSectionChange={section} onProjectChange={vi.fn()} onNavigate={navigate}><p>Workspace</p></AppShell>);
    expect(screen.getByRole("button", { name: "Optional providers" }).className).toContain("activeTechnicalSubitem");
    fireEvent.click(screen.getByRole("button", { name: "Core sources" }));
    expect(navigate).toHaveBeenCalledWith("integrations");
    expect(section).toHaveBeenCalledWith("core");
  });

  it("renders Content sections with the shared expandable subnavigation", () => {
    const navigate = vi.fn();
    const section = vi.fn();
    render(<AppShell projects={[project]} selectedProject="shop" activeView="content" activeContentSection="brief" onContentSectionChange={section} onProjectChange={vi.fn()} onNavigate={navigate}><p>Workspace</p></AppShell>);
    expect(screen.getByRole("button", { name: "Brief" }).className).toContain("activeTechnicalSubitem");
    fireEvent.click(screen.getByRole("button", { name: "Produce" }));
    expect(navigate).toHaveBeenCalledWith("content");
    expect(section).toHaveBeenCalledWith("produce");
  });

  it("keeps an expanded audit menu open when navigating away", () => {
    const { rerender } = render(<AppShell projects={[project]} selectedProject="shop" activeView="audits" activeAuditSection="overview" onProjectChange={vi.fn()} onNavigate={vi.fn()}><p>Workspace</p></AppShell>);
    rerender(<AppShell projects={[project]} selectedProject="shop" activeView="pages" activeAuditSection="overview" onProjectChange={vi.fn()} onNavigate={vi.fn()}><p>Workspace</p></AppShell>);
    expect(screen.getByRole("button", { name: "Summary" })).toBeTruthy();
    expect(screen.getAllByRole("button", { name: "Audit" })[0].getAttribute("aria-expanded")).toBe("true");
  });

  it("shows the current workflow instruction and phase states", () => {
    const onOpenActions = vi.fn();
    const onOpenKeywords = vi.fn();
    render(<WorkflowPage workspace={{ ...workspace, phase_order: ["DISCOVERY", "STRATEGY", "TECHNICAL_AUDIT"], phases: { ...workspace.phases, STRATEGY: { status: "pending", steps: [] } } }} onStepAction={vi.fn()} onOpenActions={onOpenActions} onOpenKeywords={onOpenKeywords} />);
    fireEvent.click(screen.getByRole("button", { name: "Run audit evidence" }));
    expect(onOpenActions).toHaveBeenCalledOnce();
    expect(screen.getAllByText("Collect evidence").length).toBeGreaterThan(0);
    expect(screen.getByText("technical-audit")).toBeTruthy();
    expect(screen.getByText("DISCOVERY")).toBeTruthy();
    expect(screen.queryByText("Workflow complete")).toBeNull();
    expect(screen.getByText("Map demand and ownership")).toBeTruthy();
    fireEvent.click(screen.getAllByRole("link", { name: "Open Keywords" })[0]);
    expect(onOpenKeywords).toHaveBeenCalledOnce();
  });

  it("explains content production without turning Plan into a queue", () => {
    const onOpenContent = vi.fn();
    render(<WorkflowPage workspace={{ ...workspace, phase: "CONTENT_PRODUCTION", phase_order: ["DISCOVERY", "CONTENT_PRODUCTION", "TECHNICAL_AUDIT"], step: null, next: null, phases: { ...workspace.phases, CONTENT_PRODUCTION: { status: "pending", steps: [] } } }} onStepAction={vi.fn()} onOpenContent={onOpenContent} />);
    expect(screen.getAllByText("Create or improve the page").length).toBeGreaterThan(0);
    expect(screen.getByText("Write or improve the content")).toBeTruthy();
    expect(screen.queryByText("Review content queue")).toBeNull();
    fireEvent.click(screen.getAllByRole("link", { name: "Open Content" })[0]);
    expect(onOpenContent).toHaveBeenCalledOnce();
  });

  it("keeps workflow action failures visible", async () => {
    const initWorkspace: Workspace = {
      ...workspace,
      phase: "INIT",
      phase_order: ["INIT", "STRATEGY"],
      step: { id: "config-brand-voice", label: "Define brand voice", status: "pending" },
      next: { phase: "INIT", step: "config-brand-voice", label: "Define brand voice", skill: "project-context", context: [], output: "context/brand-voice.md" },
      phases: { ...workspace.phases, INIT: { status: "in_progress", steps: [{ id: "config-brand-voice", label: "Define brand voice", status: "pending" }] }, STRATEGY: { status: "pending", steps: [] } },
    };
    render(<WorkflowPage workspace={initWorkspace} onStepAction={vi.fn().mockRejectedValue(new Error("State revision changed."))} />);
    fireEvent.click(screen.getByRole("button", { name: "Mark done" }));
    expect((await screen.findByRole("alert")).textContent).toContain("State revision changed.");
  });

  it("shows recorded SEO change outcomes", () => {
    const navigatePages = vi.fn();
    render(<OverviewPage workspace={workspace} updatedPaths={{}} onNavigateWorkflow={vi.fn()} onNavigatePages={navigatePages} onOpenFile={vi.fn()} />);
    expect(screen.getByText("SEO change outcomes")).toBeTruthy();
    expect(screen.getByText("Improve qualified clicks")).toBeTruthy();
    expect(screen.getByText("winning")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Open outcome reviews" }));
    expect(navigatePages).toHaveBeenCalledWith({ group: "review", source: "change" });
  });

  it("makes the overview purpose clear", () => {
    render(<OverviewPage workspace={workspace} updatedPaths={{}} onNavigateWorkflow={vi.fn()} onNavigatePages={vi.fn()} onOpenFile={vi.fn()} />);
    expect(screen.getByRole("heading", { name: "Project health" })).toBeTruthy();
    expect(screen.getByText(/focused view of performance/)).toBeTruthy();
    expect(screen.getByText("Watch closely", { selector: ".statusPill" })).toBeTruthy();
    expect(screen.getAllByText("Performance").length).toBeGreaterThan(0);
    expect(screen.getAllByRole("group").length).toBeGreaterThan(0);
  });

  it("opens the evidence status card from coverage", () => {
    render(<OverviewPage workspace={workspace} updatedPaths={{}} onNavigateWorkflow={vi.fn()} onNavigatePages={vi.fn()} onOpenFile={vi.fn()} />);
    const trigger = screen.getByRole("button", { name: "Evidence ready, click to see all" });
    expect(trigger.getAttribute("aria-expanded")).toBe("false");
    fireEvent.click(screen.getByText("Current coverage"));
    expect(trigger.getAttribute("aria-expanded")).toBe("true");
    expect(screen.getByRole("complementary", { name: "Evidence status" })).toBeTruthy();
    fireEvent.pointerDown(document.body);
    expect(trigger.getAttribute("aria-expanded")).toBe("false");
    fireEvent.click(trigger);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(trigger.getAttribute("aria-expanded")).toBe("false");
  });

  it("shows full-site page portfolio decisions", () => {
    const navigatePages = vi.fn();
    render(<OverviewPage workspace={workspace} updatedPaths={{}} onNavigateWorkflow={vi.fn()} onNavigatePages={navigatePages} onOpenFile={vi.fn()} />);
    expect(screen.getByText("Page portfolio")).toBeTruthy();
    expect(screen.getByText("Statistical guidance")).toBeTruthy();
    expect(screen.getByText("Effective queries")).toBeTruthy();
    expect(screen.getByText("Query concentration")).toBeTruthy();
    expect(screen.getByText("Top-5 query share")).toBeTruthy();
    expect(screen.getByText("0.31 → 0.34")).toBeTruthy();
    expect(screen.getByText("52.0% → 55.0%")).toBeTruthy();
    expect(screen.getByText("Verified technical effects")).toBeTruthy();
    expect(screen.getByText("Refresh this guide")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Open page actions" }));
    expect(navigatePages).toHaveBeenCalledWith({ group: "now", source: "portfolio" });
  });

  it("renders optional evidence without crashing", () => {
    render(<EvidenceStatusCard items={[{ id: "browser", label: "Browser", status: "complete" }, { id: "backlinks", label: "Backlinks", status: "not_collected" }]} />);
    expect(screen.getByText("Browser")).toBeTruthy();
    expect(screen.getByText("Backlinks")).toBeTruthy();
    expect(screen.getByText("Ready", { selector: ".statusPill" }).getAttribute("data-tone")).toBe("success");
    expect(screen.getByText("Not collected", { selector: ".statusPill" }).getAttribute("data-tone")).toBe("neutral");
  });

  it("opens the Pages workspace on Now and drills into evidence", async () => {
    const refresh = vi.fn().mockResolvedValue(undefined);
    render(<PagesWorkbenchPage projectId="shop" refreshKey={0} refreshing={false} onRefresh={refresh} onUpdated={vi.fn()} />);
    expect(await screen.findByRole("heading", { name: "Pages" })).toBeTruthy();
    expect(await screen.findByText("Refresh guide")).toBeTruthy();
    expect(screen.getByRole("img", { name: "Help: Query conflicts" })).toBeTruthy();
    expect(fetchPageView).toHaveBeenCalledWith("shop", expect.objectContaining({ dataset: "actions", group: "now" }));
    expect(screen.getByText("not collected")).toBeTruthy();
    fireEvent.click(screen.getByText("Refresh guide"));
    expect(await screen.findByRole("dialog", { name: "Page workspace details" })).toBeTruthy();
    expect(within(screen.getByRole("table", { name: "Search and business performance comparison" })).getByText("120")).toBeTruthy();
    expect(within(screen.getByRole("table", { name: "Top query performance" })).getByText("desk cable management")).toBeTruthy();
    expect(within(screen.getByRole("table", { name: "Top query performance" })).getByRole("link", { name: "desk cable management" }).getAttribute("href")).toContain("#/keywords?q=desk+cable+management");
    expect(within(screen.getByRole("table", { name: "Observed click change drivers" })).getByText("desk cable management")).toBeTruthy();
    expect(screen.getByText("Position 4–20 impressions")).toBeTruthy();
    expect(screen.getByText("CTR benchmark q-value")).toBeTruthy();
    expect(screen.getByText(/primary 64.3%/)).toBeTruthy();
    expect(screen.getByText("2 open issues")).toBeTruthy();
    expect(within(screen.getByRole("table", { name: "Internal link candidates" })).getByText("standing desk · desk")).toBeTruthy();
    expect((screen.getByRole("combobox", { name: "Change type" }) as HTMLSelectElement).value).toBe("internal_links");
    fireEvent.change(screen.getByPlaceholderText("What result do you expect, and why?"), { target: { value: "A clearer page will improve qualified clicks." } });
    fireEvent.click(screen.getByRole("button", { name: "Record change" }));
    await waitFor(() => expect(createSeoChange).toHaveBeenCalledWith("shop", expect.objectContaining({ urls: ["https://example.com/page"], change_type: "internal_links", hypothesis: "A clearer page will improve qualified clicks.", metrics: ["clicks", "position"] })));
    fireEvent.click(screen.getByRole("button", { name: "Refresh analysis" }));
    expect(refresh).toHaveBeenCalledOnce();
  });

  it("toggles Pages filters and persists visible columns", async () => {
    window.localStorage?.removeItem("pages-columns:shop:actions");
    const { container } = render(<PagesWorkbenchPage projectId="shop" refreshKey={0} refreshing={false} onRefresh={vi.fn()} onUpdated={vi.fn()} />);
    expect(await screen.findByRole("heading", { name: "Pages" })).toBeTruthy();
    expect(screen.getByRole("combobox", { name: "Source" })).toBeTruthy();
    expect(screen.getByText("high").getAttribute("data-tone")).toBe("warning");
    const columnMenu = container.querySelector("details") as HTMLDetailsElement;
    fireEvent.click(screen.getByText("Columns"));
    expect(columnMenu.open).toBe(true);
    fireEvent.pointerDown(document.body);
    expect(columnMenu.open).toBe(false);
    fireEvent.click(screen.getByRole("button", { name: "Toggle filters" }));
    expect(screen.queryByRole("combobox", { name: "Source" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Toggle filters" }));
    fireEvent.click(screen.getByText("Columns"));
    fireEvent.click(screen.getByLabelText("Action"));
    expect(screen.queryByRole("columnheader", { name: "Action" })).toBeNull();
    expect(window.localStorage?.getItem("pages-columns:shop:actions") || "").not.toContain("title");
  });

  it("applies a same-view Pages deep link after render", async () => {
    const { rerender } = render(<PagesWorkbenchPage projectId="shop" refreshKey={0} refreshing={false} initialGroup="now" onRefresh={vi.fn()} onUpdated={vi.fn()} />);
    await waitFor(() => expect(fetchPageView).toHaveBeenCalledWith("shop", expect.objectContaining({ group: "now", source: "" })));
    rerender(<PagesWorkbenchPage projectId="shop" refreshKey={0} refreshing={false} initialGroup="review" initialSource="change" onRefresh={vi.fn()} onUpdated={vi.fn()} />);
    await waitFor(() => expect(fetchPageView).toHaveBeenCalledWith("shop", expect.objectContaining({ group: "review", source: "change" })));
  });

  it("shows a failed Pages refresh without an unhandled rejection", async () => {
    render(<PagesWorkbenchPage projectId="shop" refreshKey={0} refreshing={false} onRefresh={vi.fn().mockRejectedValue(new Error("Refresh is already running."))} onUpdated={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Refresh analysis" }));
    expect((await screen.findByRole("alert")).textContent).toContain("Refresh is already running.");
  });

  it("updates a technical issue from the Pages drawer", async () => {
    const row = { row_key: "technical:fp-1", source: "technical", source_id: "fp-1", group: "now", urgency: "high", title: "Missing H1", url: "https://example.com/page", status: "open", reason: "Add an H1." };
    vi.mocked(fetchPageView).mockResolvedValue({ ...pageView, rows: [row] });
    vi.mocked(fetchPageDetail).mockResolvedValue({ ...pageDetail, row, source_record: { fingerprint: "fp-1", status: "open", owner: "" } });
    render(<PagesWorkbenchPage projectId="shop" refreshKey={0} refreshing={false} onRefresh={vi.fn()} onUpdated={vi.fn()} />);
    fireEvent.click(await screen.findByText("Missing H1"));
    fireEvent.change(await screen.findByPlaceholderText("seo"), { target: { value: "theme" } });
    fireEvent.change(screen.getByPlaceholderText("What changed?"), { target: { value: "Queued for template fix" } });
    fireEvent.click(screen.getByRole("button", { name: "Update issue" }));
    await waitFor(() => expect(updateTechnicalIssueStatus).toHaveBeenCalledWith("shop", "fp-1", "open", "theme", "Queued for template fix"));
  });

  it("keeps grouped technical actions read-only", async () => {
    const row = { row_key: "technical-group:MISSING_H1:product:open:unassigned", source: "technical", source_id: "", group: "now", urgency: "high", title: "Missing H1 · product (2)", url: "", status: "open", reason: "Add an H1.", read_only: true };
    vi.mocked(fetchPageView).mockResolvedValue({ ...pageView, rows: [row] });
    vi.mocked(fetchPageDetail).mockResolvedValue({ ...pageDetail, row, source_record: null });
    render(<PagesWorkbenchPage projectId="shop" refreshKey={0} refreshing={false} onRefresh={vi.fn()} onUpdated={vi.fn()} />);
    fireEvent.click(await screen.findByText("Missing H1 · product (2)"));
    expect(await screen.findByText(/Grouped action is read-only/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Update issue" })).toBeNull();
    expect(screen.queryByRole("heading", { name: "Record SEO change" })).toBeNull();
  });

  it("evaluates a due change before marking it reviewed", async () => {
    const row = { row_key: "change:chg-1", source: "change", source_id: "chg-1", group: "review", urgency: "critical", title: "Improve clicks", url: "https://example.com/page", status: "shipped", reason: "Review evidence." };
    vi.mocked(fetchPageView).mockResolvedValue({ ...pageView, rows: [row] });
    vi.mocked(fetchPageDetail).mockResolvedValue({ ...pageDetail, row, source_record: { id: "chg-1", status: "shipped" } });
    render(<PagesWorkbenchPage projectId="shop" refreshKey={0} refreshing={false} onRefresh={vi.fn()} onUpdated={vi.fn()} />);
    fireEvent.click(await screen.findByText("Improve clicks"));
    expect((await screen.findByRole("button", { name: "Mark reviewed" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(await screen.findByRole("button", { name: "Evaluate current evidence" }));
    expect(await screen.findByText("winning")).toBeTruthy();
    fireEvent.change(screen.getByPlaceholderText("What did the evidence show?"), { target: { value: "Comparable click growth" } });
    fireEvent.click(screen.getByRole("button", { name: "Mark reviewed" }));
    await waitFor(() => expect(updateSeoChangeStatus).toHaveBeenCalledWith("shop", "chg-1", "reviewed", "Comparable click growth"));
  });

  it("renders Markdown without enabling raw HTML", () => {
    const { container } = render(<MarkdownPreview content={'# Safe\n\n<script>alert("x")</script>\n\n[Source](https://example.com)'} />);
    expect(screen.getByRole("heading", { name: "Safe" })).toBeTruthy();
    expect(container.querySelector("script")).toBeNull();
    expect(screen.getByRole("link", { name: "Source" }).getAttribute("rel")).toBe("noreferrer");
  });

  it("reads local tutorials and follows links between them", async () => {
    render(<TutorialsPage />);
    expect(await screen.findByRole("heading", { name: "Foundations" })).toBeTruthy();
    fireEvent.click(await screen.findByRole("link", { name: "Growth" }));
    expect(await screen.findByRole("heading", { name: "Growth diagnosis" })).toBeTruthy();
    expect(fetchTutorial).toHaveBeenCalledWith("growth-diagnosis");
    expect(screen.getByText("Read only")).toBeTruthy();
  });

  it("renders the blog production workbench queue, ops and files", async () => {
    render(
      <ContentWorkbenchPage
        projectId="shop"
        section="produce"
        workspace={contentWorkspace}
        jobs={[{ id: "job1", project_id: "shop", action: "content:qc", status: "succeeded", created_at: "2026-07-29T00:00:00Z", started_at: null, finished_at: null, exit_code: 0, output: "QC ok" }]}
        refreshKey={0}
        onOpenFile={vi.fn()}
        onRunContentAction={vi.fn()}
        onUpdateStatus={vi.fn()}
      />,
    );
    expect(screen.getByRole("heading", { name: "Produce workbench" })).toBeTruthy();
    expect(screen.getAllByText("Ready Post").length).toBeGreaterThan(0);
    expect(screen.getByText("Resolve image refs")).toBeTruthy();
    expect(screen.getByText("review digest")).toBeTruthy();
    expect(screen.getByText("QC ok")).toBeTruthy();
    expect(screen.getAllByText("Approved", { selector: ".statusPill" }).every((pill) => pill.getAttribute("data-tone") === "success")).toBe(true);
    expect(screen.getByRole("link", { name: "desk shelf" }).getAttribute("href")).toContain("#/keywords?q=desk+shelf");
    await waitFor(() => expect(fetchFiles).toHaveBeenCalled());
    expect(screen.queryByText("content/briefs/rec1.md")).toBeNull();
    expect(screen.queryByText("content/reports/daily.md")).toBeNull();
    expect(screen.queryByText("content report")).toBeNull();
  });

  it("keeps brief drafting separate from production", async () => {
    const run = vi.fn().mockResolvedValue(undefined);
    render(
      <ContentWorkbenchPage
        projectId="shop"
        section="brief"
        workspace={{ ...contentWorkspace, content: { ...contentWorkspace.content, items: [{ ...contentWorkspace.content.items[0], status: "ready_to_write" }] } }}
        jobs={[]}
        refreshKey={0}
        onOpenFile={vi.fn()}
        onRunContentAction={run}
        onUpdateStatus={vi.fn()}
      />,
    );
    expect(screen.getByRole("heading", { name: "Brief workbench" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Brief" }));
    expect(run).toHaveBeenCalledWith({ action: "brief", item_id: "rec1" });
    expect(screen.queryByRole("button", { name: "Publish" })).toBeNull();
    expect(await screen.findByText("content/briefs/rec1.md")).toBeTruthy();
  });

  it("filters project files by folder and search text", async () => {
    vi.mocked(fetchFiles).mockResolvedValueOnce([
      { path: "context/state.md", name: "state.md", size: 120, modified_at: "2026-08-19T00:00:00Z" },
      { path: "reports/weekly.md", name: "weekly.md", size: 240, modified_at: "2026-08-19T00:00:00Z" },
      { path: "reports/decision.md", name: "decision.md", size: 360, modified_at: "2026-08-19T00:00:00Z" },
    ]);
    render(<FilesPage projectId="shop" refreshKey={0} onOpenFile={vi.fn()} />);
    expect(await screen.findByText("context/state.md")).toBeTruthy();
    fireEvent.change(screen.getByRole("combobox", { name: "Filter by folder" }), { target: { value: "reports" } });
    expect(screen.queryByText("context/state.md")).toBeNull();
    expect(screen.getByText("reports/weekly.md")).toBeTruthy();
    fireEvent.change(screen.getByRole("textbox", { name: "Search files" }), { target: { value: "decision" } });
    expect(screen.queryByText("reports/weekly.md")).toBeNull();
    expect(screen.getByText("reports/decision.md")).toBeTruthy();
  });

  it("lists owner cards and opens them in the Markdown reader", async () => {
    const openFile = vi.fn();
    vi.mocked(fetchFiles).mockResolvedValueOnce([
      { path: "strategy/owners/README.md", name: "README.md", size: 4200, modified_at: "2026-08-19T00:00:00Z" },
      { path: "strategy/owners/studio.md", name: "studio.md", size: 1200, modified_at: "2026-08-19T00:00:00Z" },
      { path: "strategy/owners/cable-tray.md", name: "cable-tray.md", size: 1600, modified_at: "2026-08-19T00:00:00Z" },
    ]);
    render(<OwnersPage projectId="shop" refreshKey={0} onOpenFile={openFile} />);

    expect(await screen.findByRole("heading", { name: "Owners" })).toBeTruthy();
    expect(screen.getByText("Owner card index")).toBeTruthy();
    expect(screen.getByText("Cable Tray")).toBeTruthy();
    fireEvent.change(screen.getByRole("textbox", { name: "Search owner cards" }), { target: { value: "studio" } });
    expect(screen.getByText("Studio")).toBeTruthy();
    expect(screen.queryByText("Cable Tray")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Open Studio" }));
    expect(openFile).toHaveBeenCalledWith("strategy/owners/studio.md");
  });

  it("renders reports notify as a dedicated workspace", async () => {
    const run = vi.fn().mockResolvedValue(undefined);
    render(<ReportsPage projectId="shop" jobs={[]} refreshKey={0} section="notify" onOpenFile={vi.fn()} onRunContentAction={run} />);
    expect(screen.getByRole("heading", { name: "Notifications" })).toBeTruthy();
    expect(screen.getByText(/Each run creates a Markdown file for review/)).toBeTruthy();
    expect(await screen.findByText("content/reports/daily.md")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Daily report" }));
    await waitFor(() => expect(run).toHaveBeenCalledWith({ action: "report", period: "daily" }));
  });

  it("renders SEO changes as a read-only report timeline", async () => {
    render(<ReportsPage projectId="shop" jobs={[]} refreshKey={0} section="seo-changes" onOpenFile={vi.fn()} onRunContentAction={vi.fn()} />);
    expect(await screen.findByRole("heading", { name: "SEO changes" })).toBeTruthy();
    expect(screen.getByText("Improve the product title")).toBeTruthy();
    expect(screen.getByText(/Content production work stays in the Content workspace/)).toBeTruthy();
    expect(screen.getAllByText("shipped", { selector: ".statusPill" })).toHaveLength(1);
    fireEvent.change(screen.getByRole("combobox", { name: "Filter SEO changes by type" }), { target: { value: "content" } });
    expect(screen.queryByText("Improve the product title")).toBeNull();
    expect(screen.getByText("Expand the guide")).toBeTruthy();
  });

  it("renders presentation readiness and starts PDF generation", async () => {
    const run = vi.fn().mockResolvedValue(undefined);
    render(<ReportsPage projectId="shop" jobs={[]} refreshKey={0} section="presentation" onOpenFile={vi.fn()} onRunContentAction={vi.fn()} onRunPresentation={run} />);
    expect(await screen.findByRole("heading", { name: "Presentation" })).toBeTruthy();
    expect(screen.getByText("Friday afternoon output")).toBeTruthy();
    expect(screen.getByText("business measurement regime changed inside the comparison range")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Generate PDF" }));
    await waitFor(() => expect(run).toHaveBeenCalledTimes(1));
  });

  it("renders reports weekly with the work archive and scaffolds the next week", async () => {
    const run = vi.fn().mockResolvedValue(undefined);
    render(<ReportsPage projectId="shop" jobs={[]} refreshKey={0} section="weekly" onOpenFile={vi.fn()} onRunContentAction={run} />);
    expect(screen.getByRole("heading", { name: "Weekly" })).toBeTruthy();
    expect(await screen.findByText("2026 Week 34")).toBeTruthy();
    expect(screen.getByText("速览 2/3")).toBeTruthy();
    expect(screen.getByText("遗留 1")).toBeTruthy();
    expect(screen.getByText("theme-fix-handoff")).toBeTruthy();
    expect(screen.queryByText("Scaffold the next week and carry over unfinished work")).toBeNull();
    expect(screen.getByRole("heading", { name: "Decision & outcome records" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /New weekly report/ }));
    await waitFor(() => expect(run).toHaveBeenCalledWith({ action: "reports-new" }));
  });

  it("renders weekly progress groups and carried-over tracks", async () => {
    render(<ReportsPage projectId="shop" jobs={[]} refreshKey={0} section="weekly" onOpenFile={vi.fn()} onRunContentAction={vi.fn()} />);
    expect(await screen.findByText("Follow-ups")).toBeTruthy();
    expect(screen.getByText("Overdue")).toBeTruthy();
    expect(screen.getByText("旧遗留项")).toBeTruthy();
    expect(screen.getByText("Still open")).toBeTruthy();
    expect(screen.getByText("顺延 2 周")).toBeTruthy();
    expect(screen.getByText("承接 1 项自 Week 33")).toBeTruthy();
  });

  it("filters reports by query through the archive endpoint", async () => {
    render(<ReportsPage projectId="shop" jobs={[]} refreshKey={0} section="weekly" onOpenFile={vi.fn()} onRunContentAction={vi.fn()} />);
    expect(await screen.findByRole("heading", { name: "Weekly" })).toBeTruthy();
    fireEvent.change(screen.getByRole("textbox", { name: "Search reports" }), { target: { value: "handoff" } });
    await waitFor(() => expect(fetchReportArchive).toHaveBeenCalledWith("shop", expect.objectContaining({ q: "handoff" })));
  });

  it("filters reports by month through the archive endpoint", async () => {
    render(<ReportsPage projectId="shop" jobs={[]} refreshKey={0} section="weekly" onOpenFile={vi.fn()} onRunContentAction={vi.fn()} />);
    expect(await screen.findByRole("heading", { name: "Weekly" })).toBeTruthy();
    fireEvent.change(screen.getByRole("combobox", { name: "Filter by month" }), { target: { value: "8" } });
    await waitFor(() => expect(fetchReportArchive).toHaveBeenCalledWith("shop", expect.objectContaining({ month: 8 })));
  });

  it("opens the markdown editor as an overlay and closes on backdrop or Escape", async () => {
    const close = vi.fn();
    render(<MarkdownOverlay projectId="shop" path="reports/2026_week_34_work_done.md" onClose={close} />);
    const dialog = await screen.findByRole("dialog", { name: /Markdown preview and editor/ });
    expect(dialog).toBeTruthy();
    expect(await screen.findByText("Week 34")).toBeTruthy();
    expect(screen.getByText("reports/2026_week_34_work_done.md")).toBeTruthy();
    expect(screen.queryByText("2026_week_34_work_done.md")).toBeNull();
    expect((screen.getByRole("button", { name: "Saved" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.mouseDown(dialog.parentElement as Element);
    expect(close).toHaveBeenCalledTimes(1);
    fireEvent.keyDown(window, { key: "Escape" });
    expect(close).toHaveBeenCalledTimes(2);
  });

  it("keeps the overlay open when interacting inside the editor panel", async () => {
    const close = vi.fn();
    render(<MarkdownOverlay projectId="shop" path="reports/2026_week_34_work_done.md" onClose={close} />);
    const dialog = await screen.findByRole("dialog", { name: /Markdown preview and editor/ });
    fireEvent.mouseDown(dialog);
    expect(close).not.toHaveBeenCalled();
  });

  it("opens the markdown overlay in preview view and allows switching", async () => {
    render(<MarkdownOverlay projectId="shop" path="reports/2026_week_34_work_done.md" onClose={vi.fn()} />);
    await screen.findByText("Week 34");
    expect(screen.getByRole("button", { name: "Preview view" }).getAttribute("aria-pressed")).toBe("true");
    fireEvent.click(screen.getByRole("button", { name: "Split view" }));
    expect(screen.getByRole("button", { name: "Split view" }).getAttribute("aria-pressed")).toBe("true");
    fireEvent.click(screen.getByRole("button", { name: "Source view" }));
    expect(screen.getByRole("button", { name: "Source view" }).getAttribute("aria-pressed")).toBe("true");
  });

  it("starts the overlay editor compact and adjusts the preview size", async () => {
    render(<MarkdownOverlay projectId="shop" path="reports/2026_week_34_work_done.md" onClose={vi.fn()} />);
    const editor = await screen.findByLabelText(/Markdown editor for reports/);
    expect(editor.style.getPropertyValue("--md-font-size")).toBe("14px");
    fireEvent.click(screen.getByRole("button", { name: "Larger preview" }));
    expect(editor.style.getPropertyValue("--md-font-size")).toBe("15px");
  });

  it("clamps the overlay preview size at the minimum", async () => {
    render(<MarkdownOverlay projectId="shop" path="reports/2026_week_34_work_done.md" onClose={vi.fn()} />);
    const editor = await screen.findByLabelText(/Markdown editor for reports/);
    const smaller = screen.getByRole("button", { name: "Smaller preview" }) as HTMLButtonElement;
    while (!smaller.disabled) fireEvent.click(smaller);
    expect(editor.style.getPropertyValue("--md-font-size")).toBe("12px");
    expect(smaller.disabled).toBe(true);
  });

  it("selects and re-crawls one or many 404 pages", async () => {
    const recrawl = vi.fn().mockResolvedValue(undefined);
    render(<TechnicalAuditPage projectId="shop" jobs={[]} refreshKey={0} onRunFull={vi.fn().mockResolvedValue(undefined)} onRecrawl={recrawl} auditSection="url-inventory" />);
    expect(await screen.findByRole("heading", { name: "Technical audit" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Select current page" }));
    const clear = screen.getByRole("button", { name: "Clear" });
    const recrawlButton = screen.getByRole("button", { name: "Re-crawl selected" });
    expect(clear.compareDocumentPosition(recrawlButton) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    fireEvent.click(recrawlButton);
    expect(recrawl).toHaveBeenCalledWith(["https://example.com/missing", "https://example.com/old"]);
  });

  it("continues a capped crawl from its persisted queue", async () => {
    const continueCrawl = vi.fn().mockResolvedValue(undefined);
    render(<TechnicalAuditPage projectId="shop" jobs={[]} refreshKey={0} onRunFull={vi.fn().mockResolvedValue(undefined)} onContinue={continueCrawl} onRecrawl={vi.fn().mockResolvedValue(undefined)} />);
    const button = await screen.findByRole("button", { name: "Continue crawl (3)" });
    fireEvent.click(button);
    expect(continueCrawl).toHaveBeenCalledOnce();
  });

  it("switches viewer datasets, persists columns, and opens the detail drawer", async () => {
    render(<TechnicalAuditPage projectId="shop" jobs={[]} refreshKey={0} onRunFull={vi.fn().mockResolvedValue(undefined)} onRecrawl={vi.fn().mockResolvedValue(undefined)} auditSection="url-inventory" />);
    expect(await screen.findByRole("tab", { name: "URL Inventory" })).toBeTruthy();
    fireEvent.click(screen.getByRole("tab", { name: "Link Inventory" }));
    expect(await screen.findByText("https://help.example.com/")).toBeTruthy();
    expect(vi.mocked(fetchTechAuditView)).toHaveBeenCalledWith("shop", expect.objectContaining({ dataset: "links", host_relation: "site_family" }));
    fireEvent.change(screen.getByRole("combobox", { name: "Run" }), { target: { value: "run-1" } });
    expect(vi.mocked(fetchTechAuditView)).toHaveBeenLastCalledWith("shop", expect.objectContaining({ run_id: "run-1" }));
    fireEvent.click(screen.getByText("https://help.example.com/"));
    expect(vi.mocked(fetchTechAuditDetail)).toHaveBeenLastCalledWith("shop", "links", "https://help.example.com/", "run-1");
    expect(await screen.findByRole("dialog", { name: "Technical audit details" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Heading outline" })).toBeTruthy();
    expect(screen.getByText("Primary heading")).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Metadata and links" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Metadata and links" }).compareDocumentPosition(screen.getByRole("heading", { name: "Heading outline" })) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.getByText("2 occurrences")).toBeTruthy();
    expect(screen.getByText("1 occurrence")).toBeTruthy();
    fireEvent.keyDown(document, { key: "Escape" });
    fireEvent.click(screen.getByRole("tab", { name: "Issues" }));
    expect(await screen.findByText("HTTP_4XX")).toBeTruthy();
    expect(screen.getByText("high").getAttribute("data-tone")).toBe("warning");
    fireEvent.click(screen.getByRole("tab", { name: "URL Inventory" }));
    fireEvent.click(screen.getByText("Columns"));
    fireEvent.click(await screen.findByLabelText("Title"));
    if (window.localStorage) expect(window.localStorage.getItem("tech-audit-columns:shop:pages")).toContain("url");
    fireEvent.click(screen.getAllByText("https://example.com/missing").at(-1)!);
    expect(await screen.findByRole("dialog", { name: "Technical audit details" })).toBeTruthy();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("dialog", { name: "Technical audit details" })).toBeNull();
  });

  it("updates status and confirms external publish actions", async () => {
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    const run = vi.fn().mockResolvedValue(undefined);
    const updateStatus = vi.fn().mockResolvedValue(undefined);
    render(
      <ContentWorkbenchPage
        projectId="shop"
        section="produce"
        workspace={contentWorkspace}
        jobs={[]}
        refreshKey={0}
        onOpenFile={vi.fn()}
        onRunContentAction={run}
        onUpdateStatus={updateStatus}
      />,
    );

    fireEvent.change(screen.getByPlaceholderText("Operator note"), { target: { value: "human approved" } });
    fireEvent.click(screen.getByRole("button", { name: /Update/i }));
    expect(updateStatus).toHaveBeenCalledWith("rec1", "approved", "human approved");

    fireEvent.click(screen.getByRole("button", { name: /^Publish$/i }));
    expect(screen.getByRole("alert").textContent).toContain("Blog ID is required");
    fireEvent.change(screen.getByPlaceholderText("Shopify blog ID"), { target: { value: "100" } });
    fireEvent.click(screen.getByRole("button", { name: /^Publish$/i }));
    expect(confirm).toHaveBeenCalledWith("Run Publish? This action can write to an external service.");
    expect(run).toHaveBeenCalledWith({ action: "publish", item_id: "rec1", blog_id: "100", confirm: true });

    fireEvent.click(screen.getByRole("button", { name: /gsc inspect/i }));
    expect(run).toHaveBeenCalledWith(expect.objectContaining({ action: "gsc-inspect", limit: 20 }));
    expect(screen.queryByRole("tab", { name: "Reports" })).toBeNull();
    confirm.mockRestore();
  });
});
