import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { fetchTutorial, fetchTutorials } from "../api/client";
import type { TutorialDocument, TutorialSummary, Workspace } from "../api/types";
import { AppShell } from "../components/AppShell";
import { MarkdownPreview } from "../features/editor/MarkdownPreview";
import { EvidenceRail } from "../features/overview/EvidenceRail";
import { TutorialsPage } from "../features/tutorials/TutorialsPage";
import { WorkflowPage } from "../features/workflow/WorkflowPage";

vi.mock("../api/client", () => ({
  fetchTutorial: vi.fn(),
  fetchTutorials: vi.fn(),
}));

const project = {
  id: "shop",
  path: "/tmp/shop",
  name: "Example Shop",
  url: "https://example.com",
  type: "shopify",
  phase: "TECHNICAL_AUDIT",
  selectable: true,
  valid_state: true,
};

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
    diff: {},
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

beforeEach(() => {
  vi.mocked(fetchTutorials).mockResolvedValue(tutorialSummaries);
  vi.mocked(fetchTutorial).mockImplementation(async (slug) => tutorialDocuments[slug]);
});

describe("workbench frontend", () => {
  it("renders project navigation and routes button clicks", () => {
    const navigate = vi.fn();
    render(<AppShell projects={[project]} selectedProject="shop" activeView="overview" connected onProjectChange={vi.fn()} onNavigate={navigate} onRunAudit={vi.fn()}><p>Workspace</p></AppShell>);
    expect(screen.getAllByText("Example Shop").length).toBeGreaterThan(0);
    fireEvent.click(screen.getAllByRole("button", { name: /Workflow/i })[0]);
    expect(navigate).toHaveBeenCalledWith("workflow");
    fireEvent.click(screen.getAllByRole("button", { name: /Tutorials/i })[0]);
    expect(navigate).toHaveBeenCalledWith("tutorials");
  });

  it("shows the current workflow instruction and phase states", () => {
    render(<WorkflowPage workspace={workspace} onStepAction={vi.fn()} />);
    expect(screen.getAllByText("Collect evidence").length).toBeGreaterThan(0);
    expect(screen.getByText("technical-audit")).toBeTruthy();
    expect(screen.getByText("DISCOVERY")).toBeTruthy();
  });

  it("renders optional browser evidence", () => {
    render(<EvidenceRail items={[{ id: "browser", label: "Browser", status: "complete" }]} />);
    expect(screen.getByText("Browser")).toBeTruthy();
    expect(screen.getByText("Ready")).toBeTruthy();
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
});
