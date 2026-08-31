import { useState } from "react";
import { ArrowRight, Check, Circle, Clock3, Play } from "lucide-react";

import type { Workspace } from "../../api/types";
import styles from "./WorkflowPage.module.css";

type Destination = "keywords" | "content";

type GuideTask = {
  id: string;
  label: string;
  description: string;
  capability: string;
  availability: "Workspace" | "CLI / skill" | "Conditional";
  href?: string;
  destination?: Destination;
};

type PhaseGuide = {
  title: string;
  purpose: string;
  handoff: string;
  tasks: GuideTask[];
};

const phaseGuides: Record<string, PhaseGuide> = {
  INIT: {
    title: "Set the foundation",
    purpose: "Define the project context, search boundaries, and page ownership before strategy work begins.",
    handoff: "A shared project brief and clear owners",
    tasks: [
      { id: "config-brand-voice", label: "Define brand voice and audience", description: "Record positioning, editorial guardrails, and the evidence boundaries the project will use.", capability: "project-context", availability: "Workspace", href: "#/files" },
      { id: "config-target-keywords", label: "Set target search themes", description: "Capture the initial product, category, and information themes that guide discovery.", capability: "project-context", availability: "Workspace", href: "#/keywords", destination: "keywords" },
      { id: "create-owner-cards", label: "Create owner cards", description: "Give each durable search intent one target page and one accountable ownership record.", capability: "Owners workspace", availability: "Workspace", href: "#/owners" },
    ],
  },
  STRATEGY: {
    title: "Map demand and ownership",
    purpose: "Turn search language into priorities, topic structure, target URLs, and writer-ready opportunities.",
    handoff: "Approved opportunities with a clear target and brief",
    tasks: [
      { id: "keyword-dive-product", label: "Deep-dive priority product queries", description: "Read the SERP, classify intent, and understand what a credible product page must answer.", capability: "keyword-deep-dive", availability: "Workspace", href: "#/keywords", destination: "keywords" },
      { id: "keyword-dive-info", label: "Deep-dive information queries", description: "Separate useful information demand from topics that do not deserve a new page.", capability: "keyword-deep-dive", availability: "Workspace", href: "#/keywords", destination: "keywords" },
      { id: "cluster-plan", label: "Plan topic clusters and internal links", description: "Choose hubs, spokes, publishing order, and the internal links that pass context between them.", capability: "topic-cluster-planning", availability: "CLI / skill", href: "#/files" },
      { id: "content-briefs", label: "Prepare content briefs", description: "Convert confirmed opportunities into a structure, intent, evidence, and on-page handoff for production.", capability: "content-brief", availability: "Workspace", href: "#/content", destination: "content" },
    ],
  },
  CONTENT_PRODUCTION: {
    title: "Create or improve the page",
    purpose: "Move approved opportunities and existing-page improvements through writing, review, quality control, and release preparation.",
    handoff: "A reviewed page ready for controlled publishing and measurement",
    tasks: [
      { id: "draft-content", label: "Write or improve the content", description: "Use the approved brief, page evidence, first-party expertise, and search intent to create the draft.", capability: "write-content · improve-content", availability: "Workspace", href: "#/content", destination: "content" },
      { id: "revise-content", label: "Resolve review and quality notes", description: "Apply human edit notes, content QC findings, E-E-A-T gaps, and semantic improvements.", capability: "Content workbench", availability: "Workspace", href: "#/content", destination: "content" },
      { id: "prepare-publish", label: "Prepare the release", description: "Validate the payload, assets, metadata, links, and publishing gates before any site change.", capability: "Content publish path", availability: "Workspace", href: "#/content", destination: "content" },
    ],
  },
  QUALITY_REVIEW: {
    title: "Check search and page quality",
    purpose: "Make sure the page is useful to people, aligned with the SERP, and strong enough to deserve its target query.",
    handoff: "A page with known content gaps and explicit review decisions",
    tasks: [
      { id: "page-audits", label: "Run a page audit", description: "Review SEO performance, competitive position, content quality, and page-level opportunities.", capability: "page-audit", availability: "CLI / skill", href: "#/pages" },
      { id: "eeat-audit", label: "Review E-E-A-T signals", description: "Identify the experience, expertise, authority, and trust signals that the page still needs.", capability: "eeat-audit", availability: "CLI / skill", href: "#/content" },
      { id: "semantic-gap", label: "Close semantic gaps", description: "Compare the page with ranking competitors and turn missing entities and relationships into concrete edits.", capability: "semantic-gap-analysis", availability: "CLI / skill", href: "#/content" },
      { id: "featured-snippet", label: "Optimize eligible SERP formats", description: "Where the query supports it, reshape concise answers, lists, tables, and supporting structure for snippet opportunities.", capability: "featured-snippet-optimizer", availability: "CLI / skill", href: "#/content" },
    ],
  },
  TECHNICAL_AUDIT: {
    title: "Validate the technical foundation",
    purpose: "Check crawlability, rendering, indexing, templates, structured data, media, performance, and change drift with comparable evidence.",
    handoff: "Verified findings, implementation notes, and a recheck path",
    tasks: [
      { id: "headless-precheck", label: "Establish the crawl and rendering baseline", description: "Use the headless precheck when the architecture requires raw and rendered parity checks.", capability: "headless-precheck", availability: "Conditional", href: "#/audits/overview" },
      { id: "technical-audit", label: "Run the technical audit", description: "Collect bounded evidence, apply deterministic rules, and tie issues to pages and templates.", capability: "technical-audit", availability: "Workspace", href: "#/audits/url-inventory" },
      { id: "schema", label: "Validate structured data", description: "Check supported schema types, required properties, and the boundary between markup and eligibility claims.", capability: "schema", availability: "CLI / skill", href: "#/audits/url-inventory" },
      { id: "sitemap", label: "Validate sitemap coverage", description: "Compare sitemap entries with crawl and index evidence before treating a coverage gap as a site issue.", capability: "sitemap", availability: "CLI / skill", href: "#/audits/sitemaps" },
      { id: "images", label: "Check image SEO", description: "Review alt text, format, dimensions, responsive delivery, and image search metadata where relevant.", capability: "images", availability: "CLI / skill", href: "#/audits/url-inventory" },
      { id: "drift-baseline", label: "Record a comparable baseline", description: "Preserve the evidence needed to distinguish real regressions from different collection scopes or runtimes.", capability: "drift · CrUX · performance", availability: "Workspace", href: "#/audits/crawl-comparison" },
    ],
  },
  OFF_PAGE: {
    title: "Build external authority",
    purpose: "Understand the site's link profile and choose safe, phase-appropriate ways to earn or reclaim relevant external links.",
    handoff: "A provider-scoped backlink baseline and a defensible acquisition plan",
    tasks: [
      { id: "linkbuilding-strategy", label: "Set the link acquisition strategy", description: "Assess the site's authority phase, choose appropriate tactics, and keep anchor text and claims conservative.", capability: "linkbuilding", availability: "CLI / skill", href: "#/files" },
      { id: "backlinks-audit", label: "Audit the backlink profile", description: "Import a provider snapshot, inspect referring domains and anchors, and separate evidence from assumptions about toxicity.", capability: "backlinks", availability: "CLI / skill", href: "#/files" },
      { id: "backlink-reclaim", label: "Review link gaps and reclaim candidates", description: "Use same-source comparisons and technical inventory to identify confirmed losses or links pointing to known 404/410 targets.", capability: "backlinks · technical inventory", availability: "CLI / skill", href: "#/files" },
    ],
  },
  MONITORING: {
    title: "Measure outcomes and report",
    purpose: "Bring comparable search, business, technical, and change evidence together so the next decision is grounded in what was observed.",
    handoff: "A measured result, a recorded decision, and the next recommended focus",
    tasks: [
      { id: "technical-recheck", label: "Recheck implemented technical fixes", description: "Verify fixes with a later comparable audit. A partial or mismatched run cannot prove absence.", capability: "technical audit", availability: "Workspace", href: "#/audits/url-inventory" },
      { id: "drift-compare", label: "Compare compatible evidence", description: "Use audit diff, GSC, CrUX, GA4, and Statistics without merging incomparable windows or regimes.", capability: "GSC · GA4 · Shopify · Statistics", availability: "Workspace", href: "#/statistics" },
      { id: "seo-change-review", label: "Review recorded SEO changes", description: "Compare descriptive pre/post evidence for shipped changes and keep causal claims bounded by the available data.", capability: "Pages · SEO changes · Reports", availability: "Workspace", href: "#/reports/seo-changes" },
      { id: "backlinks-recheck", label: "Recheck external link changes", description: "Only call links new or lost when complete same-source snapshots support that conclusion.", capability: "backlinks", availability: "CLI / skill", href: "#/files" },
    ],
  },
};

const fallbackGuide = (phaseName: string, steps: Array<{ id: string; label: string }>): PhaseGuide => ({
  title: phaseName.replaceAll("_", " "),
  purpose: "Follow the project-defined steps and keep each output attached to its source workspace.",
  handoff: "The documented output for this project phase",
  tasks: steps.map((step) => ({
    id: step.id,
    label: step.label,
    description: "Use the project workflow contract for this step and record the resulting artifact.",
    capability: "Project workflow",
    availability: "CLI / skill",
  })),
});

function displayPhaseName(name: string) {
  return name.replaceAll("_", " ").toLowerCase().replace(/(^|\s)\w/g, (letter) => letter.toUpperCase());
}

function destinationLabel(task: GuideTask) {
  if (task.destination === "keywords") return "Open Keywords";
  if (task.destination === "content") return "Open Content";
  if (task.href?.startsWith("#/audits")) return "Open Audits";
  if (task.href?.startsWith("#/reports")) return "Open Reports";
  if (task.href === "#/statistics") return "Open Statistics";
  if (task.href === "#/pages") return "Open Pages";
  if (task.href === "#/owners") return "Open Owners";
  return "Open source";
}

function GuideLink({ task, onOpenKeywords, onOpenContent }: { task: GuideTask; onOpenKeywords?: () => void; onOpenContent?: () => void }) {
  const callback = task.destination === "keywords" ? onOpenKeywords : task.destination === "content" ? onOpenContent : undefined;
  return (
    <a
      className={styles.taskLink}
      href={task.href}
      onClick={callback ? (event) => { event.preventDefault(); callback(); } : undefined}
    >
      {destinationLabel(task)} <ArrowRight aria-hidden="true" size={14} />
    </a>
  );
}

export function WorkflowPage({ workspace, onStepAction, onOpenActions, onOpenKeywords, onOpenContent }: { workspace: Workspace; onStepAction: (action: "start" | "done" | "skip") => Promise<void> | void; onOpenActions?: () => void; onOpenKeywords?: () => void; onOpenContent?: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const canEditInit = workspace.phase === "INIT" && Boolean(workspace.step);
  const currentGuide = phaseGuides[workspace.phase] || fallbackGuide(workspace.phase, workspace.phases[workspace.phase]?.steps || []);
  const nextLabel = workspace.next?.label || workspace.step?.label || currentGuide.handoff;
  const run = async (action: "start" | "done" | "skip") => {
    setBusy(true);
    setError(null);
    try {
      await onStepAction(action);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className={styles.page} aria-labelledby="workflow-heading">
      <h1 id="workflow-heading" className="srOnly">SEO workflow</h1>
      <header className={styles.header}>
        <div className={styles.headerAside}>
          {onOpenActions ? <button className={styles.runActions} type="button" onClick={onOpenActions}><Play aria-hidden="true" size={14} fill="currentColor" />Run audit evidence</button> : null}
        </div>
      </header>

      <section className={styles.orientation} aria-label="How to use this workflow">
        <div><strong>Understand</strong><span>Read each stage as a decision and handoff, not a completion meter.</span></div>
        <div><strong>Execute</strong><span>Open the owning workspace when the guide points to a concrete operation.</span></div>
        <div><strong>Verify</strong><span>Keep the expected artifact and evidence boundary attached to the work.</span></div>
      </section>

      <section className={styles.locationPanel} aria-labelledby="current-location-heading">
        <div className={styles.locationCopy}>
          <span className={styles.kicker}>Current context</span>
          <h2 id="current-location-heading">{currentGuide.title}</h2>
          <p>{currentGuide.purpose}</p>
        </div>
        <div className={styles.locationMeta}>
          <span>Next handoff</span>
          <strong>{nextLabel}</strong>
          {workspace.next?.skill ? <code>{workspace.next.skill}</code> : null}
          {workspace.next?.output ? <small>Expected output: {workspace.next.output}</small> : null}
          {canEditInit ? <div className={styles.controls}>
            {workspace.step?.status !== "in_progress" ? <button type="button" disabled={busy} onClick={() => void run("start")}>Start</button> : null}
            <button type="button" disabled={busy} onClick={() => void run("done")}>Mark done</button>
            <button type="button" disabled={busy} onClick={() => void run("skip")}>Skip</button>
          </div> : null}
          {error ? <p className={styles.error} role="alert">{error}</p> : null}
        </div>
      </section>

      <ol className={styles.timeline} aria-label="Recommended SEO workflow stages">
        {workspace.phase_order.map((phaseName, index) => {
          const phase = workspace.phases[phaseName];
          const guide = phaseGuides[phaseName] || fallbackGuide(phaseName, phase?.steps || []);
          const current = phaseName === workspace.phase;
          const initComplete = phaseName === "INIT" && phase?.status === "done";
          const runtimeSteps = new Map((phase?.steps || []).map((step) => [step.id, step]));
          return (
            <li key={phaseName} className={[styles.stage, current ? styles.current : "", initComplete ? styles.initComplete : ""].filter(Boolean).join(" ")}>
              <div className={styles.stageMarker} aria-hidden="true">
                <span className={styles.markerIcon}>{initComplete ? <Check size={16} /> : current ? <Clock3 size={16} /> : <Circle size={14} />}</span>
                <span className={styles.stageIndex}>{String(index + 1).padStart(2, "0")}</span>
              </div>
              <div className={styles.stageBody}>
                <header className={styles.stageHeader}>
                  <div>
                    <span className={styles.stageKicker}>{displayPhaseName(phaseName)}</span>
                    <h2>{guide.title}</h2>
                  </div>
                  <span className={styles.stageState}>{initComplete ? "Foundation set" : current ? "Current context" : "Recommended stage"}</span>
                </header>
                <p className={styles.stagePurpose}>{guide.purpose}</p>
                <div className={styles.taskList}>
                  {guide.tasks.map((task, taskIndex) => {
                    const runtimeStep = runtimeSteps.get(task.id);
                    const taskDone = phaseName === "INIT" && runtimeStep?.status === "done";
                    const taskCurrent = current && runtimeStep?.id === workspace.step?.id;
                    return (
                      <div key={task.id} className={[styles.task, taskDone ? styles.taskDone : "", taskCurrent ? styles.taskCurrent : ""].filter(Boolean).join(" ")}>
                        <span className={styles.taskIndex}>{taskDone ? <Check aria-label="Done" size={14} /> : String(taskIndex + 1).padStart(2, "0")}</span>
                        <div className={styles.taskMain}>
                          <strong>{task.label}</strong>
                          <p>{task.description}</p>
                          <small>{task.availability} · {task.capability}</small>
                        </div>
                        {task.href ? <GuideLink task={task} onOpenKeywords={onOpenKeywords} onOpenContent={onOpenContent} /> : null}
                      </div>
                    );
                  })}
                </div>
                <div className={styles.handoff}><span>Handoff</span><strong>{guide.handoff}</strong></div>
              </div>
            </li>
          );
        })}
      </ol>
      <p className={styles.footerNote}>Plan is the shared map. Home can focus on immediate attention, while Keywords, Content, Pages, Audits, Reports, and CLI skills remain the owners of execution.</p>
    </section>
  );
}
