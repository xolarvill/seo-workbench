import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { Workspace } from "../api/types";
import { AppShell } from "../components/AppShell";
import { MarkdownPreview } from "../features/editor/MarkdownPreview";
import { WorkflowPage } from "../features/workflow/WorkflowPage";

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

describe("workbench frontend", () => {
  it("renders project navigation and routes button clicks", () => {
    const navigate = vi.fn();
    render(<AppShell projects={[project]} selectedProject="shop" activeView="overview" connected onProjectChange={vi.fn()} onNavigate={navigate} onRunAudit={vi.fn()}><p>Workspace</p></AppShell>);
    expect(screen.getAllByText("Example Shop").length).toBeGreaterThan(0);
    fireEvent.click(screen.getAllByRole("button", { name: /Workflow/i })[0]);
    expect(navigate).toHaveBeenCalledWith("workflow");
  });

  it("shows the current workflow instruction and phase states", () => {
    render(<WorkflowPage workspace={workspace} />);
    expect(screen.getAllByText("Collect evidence").length).toBeGreaterThan(0);
    expect(screen.getByText("technical-audit")).toBeTruthy();
    expect(screen.getByText("DISCOVERY")).toBeTruthy();
  });

  it("renders Markdown without enabling raw HTML", () => {
    const { container } = render(<MarkdownPreview content={'# Safe\n\n<script>alert("x")</script>\n\n[Source](https://example.com)'} />);
    expect(screen.getByRole("heading", { name: "Safe" })).toBeTruthy();
    expect(container.querySelector("script")).toBeNull();
    expect(screen.getByRole("link", { name: "Source" }).getAttribute("rel")).toBe("noreferrer");
  });
});
