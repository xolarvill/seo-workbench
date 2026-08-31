import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Clock3,
  FileText,
  Loader2,
  MessageSquareText,
  Search,
  Send,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import type { ContentJobAction, ContentQueueItem, FileSummary, Job, Workspace } from "../../api/types";
import type { ContentSection } from "../../components/AppShell";
import { ActionButton, confirmExternalAction } from "../../components/ActionButton";
import { HelpTooltip } from "../../components/HelpTooltip";
import { StatusPill } from "../../components/StatusPill";
import { SearchField } from "../../components/WorkbenchControls";
import { useFiles } from "../../hooks/useWorkbenchData";
import { appHref } from "../../routes";
import styles from "./ContentWorkbenchPage.module.css";

type Props = {
  projectId: string;
  section: ContentSection;
  workspace: Workspace;
  jobs: Job[];
  refreshKey: number;
  onOpenFile: (path: string) => void;
  onRunContentAction: (action: ContentJobAction) => Promise<void>;
  onUpdateStatus: (itemId: string, status: string, note: string) => Promise<void>;
  initialItemId?: string | null;
};

type RunRequest = ContentJobAction & { label: string; danger?: boolean };

const STATUS_FLOW = ["planned", "ready_to_write", "drafting", "review", "revision_requested", "approved", "scheduled", "submitted_for_indexing", "indexing_issue", "indexed"];
const BRIEF_STATUSES = new Set(["planned", "ready_to_write", "revision_requested"]);
const BRIEF_JOBS = new Set(["content:brief", "content:revise-brief", "content:serp-competitors", "content:cluster-brief", "content:import-clusters"]);
const STATUS_LABELS: Record<string, string> = {
  planned: "Planned",
  ready_to_write: "Ready",
  drafting: "Drafting",
  review: "Review",
  revision_requested: "Revision",
  approved: "Approved",
  scheduled: "Scheduled",
  submitted_for_indexing: "Submitted",
  indexing_issue: "Indexing issue",
  indexed: "Indexed",
};

function titleOf(item: ContentQueueItem | null) {
  return String(item?.title || item?.slug || item?.id || "No item selected");
}

function warningText(value: unknown) {
  if (!value) return "";
  if (typeof value === "string") return value;
  if (typeof value === "object") {
    const record = value as { code?: unknown; message?: unknown };
    return String(record.message || record.code || "");
  }
  return String(value);
}

function latestJob(jobs: Job[], section: ContentSection) {
  return jobs.find((job) => job.action.startsWith("content:") && (section === "brief" ? BRIEF_JOBS.has(job.action) : !BRIEF_JOBS.has(job.action)) && !["content:report", "content:notify-report", "content:index-queue", "content:index-status"].includes(job.action));
}

function relatedFiles(files: FileSummary[], item: ContentQueueItem | null, section: ContentSection) {
  const contentOnly = files.filter((file) => section === "brief"
    ? file.path.startsWith("strategy/briefs/") || file.path.startsWith("strategy/keyword-dives/") || file.path.startsWith("content/briefs/")
    : file.path.startsWith("content/") && !file.path.startsWith("content/reports/") && !file.path.startsWith("content/briefs/"));
  if (!item) return contentOnly.slice(0, 8);
  const needles = [item.id, item.slug, item.title].filter(Boolean).map((value) => String(value).toLowerCase());
  const scored = contentOnly
    .map((file) => ({
      file,
      score: needles.some((needle) => file.path.toLowerCase().includes(needle)) ? 0 : 1,
    }));
  return scored.sort((left, right) => left.score - right.score || left.file.path.localeCompare(right.file.path)).map((item) => item.file).slice(0, 10);
}

export function ContentWorkbenchPage({ projectId, section, workspace, jobs, refreshKey, onOpenFile, onRunContentAction, onUpdateStatus, initialItemId }: Props) {
  const { files } = useFiles(projectId, refreshKey);
  const briefMode = section === "brief";
  const allItems = workspace.content?.items || [];
  const queue = briefMode ? allItems.filter((item) => BRIEF_STATUSES.has(item.status)) : allItems;
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [selectedId, setSelectedId] = useState<string | null>(initialItemId || queue[0]?.id || null);
  const [status, setStatus] = useState("");
  const [note, setNote] = useState("");
  const [blogId, setBlogId] = useState("");
  const [pathValue, setPathValue] = useState("");
  const [role, setRole] = useState("seo");
  const [profile, setProfile] = useState("");
  const [limit, setLimit] = useState("20");
  const [noWriteback, setNoWriteback] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const running = jobs.some((job) => job.status === "running" || job.status === "queued");
  const selected = queue.find((item) => item.id === selectedId) || queue[0] || null;
  const contentFiles = useMemo(() => relatedFiles(files, selected, section), [files, selected, section]);
  const contentJob = latestJob(jobs, section);

  useEffect(() => {
    if (initialItemId && queue.some((item) => item.id === initialItemId)) setSelectedId(initialItemId);
    if (!selectedId && queue[0]?.id) setSelectedId(queue[0].id);
    if (selected && !status) setStatus(selected.status);
  }, [queue, selected, selectedId, status, initialItemId]);

  const statuses = useMemo(() => {
    const seen = new Set(["all", ...STATUS_FLOW, ...Object.keys(workspace.content?.counts || {})]);
    return Array.from(seen);
  }, [workspace.content?.counts]);
  const filtered = queue.filter((item) => {
    const matchesStatus = statusFilter === "all" || item.status === statusFilter;
    const haystack = `${item.id} ${item.title || ""} ${item.slug || ""} ${item.status}`.toLowerCase();
    return matchesStatus && haystack.includes(query.trim().toLowerCase());
  });

  const run = async (request: RunRequest) => {
    setError(null);
    const { label: _label, danger: _danger, ...payload } = request;
    if (payload.blog_id === "") delete payload.blog_id;
    if (payload.project_relative_path === "") delete payload.project_relative_path;
    if (payload.report_path === "") delete payload.report_path;
    if (payload.profile === "") delete payload.profile;
    if (payload.role === "") delete payload.role;
    try {
      await onRunContentAction(payload);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    }
  };

  const launch = (request: RunRequest) => {
    if (request.danger && !confirmExternalAction(request.label)) return;
    void run(request.danger ? { ...request, confirm: true } : request);
  };

  const itemAction = (label: string, action: string, extra: Partial<ContentJobAction> = {}, danger = false) => {
    if (!selected) return;
    launch({ label, action, item_id: selected.id, ...extra, danger });
  };

  const requireBlogId = (action: "publish-dry-run" | "publish") => {
    if (!blogId.trim()) {
      setError("Blog ID is required.");
      return;
    }
    itemAction(action === "publish" ? "Publish" : "Publish dry-run", action, { blog_id: blogId.trim() }, action === "publish");
  };

  const updateSelectedStatus = async () => {
    if (!selected) return;
    setError(null);
    try {
      await onUpdateStatus(selected.id, status || selected.status, note);
      setNote("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    }
  };

  const dueActions = (workspace.content?.ops?.actions || []).filter((action) => action.id !== "content_report" && (briefMode ? ["write_brief", "revise_brief"].includes(action.id) : !["write_brief", "revise_brief"].includes(action.id)));
  const warnings = (selected?.warnings || []).map(warningText).filter(Boolean);

  return (
    <section className={styles.page} aria-labelledby="content-heading">
      <h1 id="content-heading" className="srOnly">{briefMode ? "Brief workbench" : "Produce workbench"}</h1>
      <header className={styles.header}>
        <div className={styles.summary}>
          <strong>{queue.length}</strong><span>{briefMode ? "candidates" : "items"}</span>
          <strong>{briefMode ? contentFiles.filter((file) => file.path.startsWith("strategy/briefs/") || file.path.startsWith("content/briefs/")).length : workspace.content?.due_for_indexing?.count || 0}</strong><span>{briefMode ? "briefs" : "inspection due"}</span>
        </div>
      </header>

      <div className={styles.layout}>
        <aside className={styles.queuePane} aria-label={briefMode ? "Brief queue" : "Production queue"}>
          <SearchField className={styles.search} label="Search content queue" value={query} onChange={setQuery} placeholder="Search queue" />
          <select className={styles.filter} value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} aria-label="Filter by status">
            {statuses.map((item) => <option key={item} value={item}>{item === "all" ? "All statuses" : STATUS_LABELS[item] || item}</option>)}
          </select>
          <div className={styles.queueList}>
            {filtered.map((item) => (
              <button key={item.id} type="button" className={item.id === selected?.id ? styles.selectedItem : styles.queueItem} onClick={() => { setSelectedId(item.id); setStatus(item.status); }}>
                <span><strong>{titleOf(item)}</strong><small>{item.slug || item.id}</small></span>
                <StatusPill value={STATUS_LABELS[item.status] || item.status} context="status" />
              </button>
            ))}
            {filtered.length === 0 ? <div className={styles.empty}><FileText aria-hidden="true" size={22} /><strong>{briefMode ? "No brief candidates" : "No content items"}</strong>{briefMode ? <small>Research handoffs appear here after they are linked to a planned content item.</small> : null}</div> : null}
          </div>
        </aside>

        <article className={styles.detailPane}>
          <header className={styles.itemHeader}>
            <div>
              <span>{selected?.id || "queue"}</span>
              <h2>{titleOf(selected)}</h2>
            </div>
            {selected ? <StatusPill value={STATUS_LABELS[selected.status] || selected.status} context="status" /> : null}
          </header>

          {selected ? (
            <>
              <dl className={styles.meta}>
                <div><dt>Slug</dt><dd>{selected.slug || "-"}</dd></div>
                <div><dt>Target keyword</dt><dd>{selected.target_keyword ? <a href={appHref("keywords", { q: selected.target_keyword })}>{selected.target_keyword}</a> : "-"}</dd></div>
                <div><dt>Words</dt><dd>{selected.word_count || "-"}</dd></div>
                <div><dt>Scheduled</dt><dd>{selected.scheduled_at || "-"}</dd></div>
                <div><dt>Review thread</dt><dd>{selected.review_thread_id || "-"}</dd></div>
                <div><dt>Live URL</dt><dd>{selected.live_url ? <a href={selected.live_url} rel="noreferrer" target="_blank">{selected.live_url}</a> : "-"}</dd></div>
              </dl>

              {warnings.length ? <div className={styles.warnings}>{warnings.map((warning) => <span key={warning}><AlertTriangle aria-hidden="true" size={14} />{warning}</span>)}</div> : null}

              <section className={styles.controls} aria-label="Status update">
                <select value={status || selected.status} onChange={(event) => setStatus(event.target.value)}>
                  {STATUS_FLOW.map((item) => <option key={item} value={item}>{STATUS_LABELS[item]}</option>)}
                </select>
                <input value={note} onChange={(event) => setNote(event.target.value)} placeholder="Operator note" />
                <button type="button" onClick={() => void updateSelectedStatus()} disabled={running}><CheckCircle2 aria-hidden="true" size={16} />Update</button>
              </section>

              <section className={`${styles.actionGroups} ${briefMode ? styles.briefActions : ""}`} aria-label={briefMode ? "Brief actions" : "Production actions"}>
                {briefMode ? <>
                  <div>
                    <h3>Draft</h3>
                    <ActionButton label="Brief" description="Create the content brief" icon={<FileText size={15} />} disabled={running} onClick={() => itemAction("Brief", "brief")} />
                    <ActionButton label="SERP" description="Review competing search results" icon={<Search size={15} />} disabled={running} onClick={() => itemAction("SERP", "serp-competitors")} />
                  </div>
                  <div>
                    <h3>Revise</h3>
                    <ActionButton label="Revise brief" description="Apply feedback to the brief" icon={<ArrowRight size={15} />} disabled={running} onClick={() => itemAction("Revise", "revise-brief")} />
                  </div>
                </> : <>
                <div>
                  <h3>Quality</h3>
                  <ActionButton label="QC" description="Run the content quality check" icon={<CheckCircle2 size={15} />} disabled={running} onClick={() => itemAction("QC", "qc")} />
                </div>
                <div>
                  <h3>Assets</h3>
                  <ActionButton label="Candidates" description="Find possible images for the draft" disabled={running || !profile.trim()} onClick={() => itemAction("Candidates", "asset-candidates", { limit: Number(limit) || 20, profile: profile || undefined })} />
                  <ActionButton label="Describe" description="Generate descriptions for images" disabled={running || !profile.trim()} onClick={() => itemAction("Describe", "describe-candidates", { limit: Number(limit) || 20, profile: profile || undefined, no_writeback: noWriteback }, !noWriteback)} />
                  <ActionButton label="Download" description="Save selected assets locally" disabled={running || !profile.trim()} onClick={() => itemAction("Download", "download-assets", { profile: profile || undefined })} />
                  <ActionButton label="Upload" description="Send approved assets to storage" disabled={running} onClick={() => itemAction("Upload", "upload-assets", {}, true)} />
                  <ActionButton label="Apply" description="Attach assets to this draft" disabled={running} onClick={() => itemAction("Apply", "apply-assets")} />
                </div>
                <div>
                  <h3>Review</h3>
                  <ActionButton label="Push" description="Send the draft for human review" icon={<MessageSquareText size={15} />} disabled={running || !profile.trim()} onClick={() => itemAction("Push review", "review-push", { role, profile: profile || undefined }, true)} />
                  <ActionButton label="Digest" description="Summarize reviewer feedback" disabled={running || !profile.trim()} onClick={() => launch({ label: "Review digest", action: "review-digest", profile: profile || undefined })} />
                </div>
                <div>
                  <h3>Publish</h3>
                  <label className={styles.field}><span>Shopify blog ID</span><input aria-label="Shopify blog ID" value={blogId} onChange={(event) => setBlogId(event.target.value)} placeholder="Shopify blog ID" /></label>
                  <ActionButton label="Dry-run" description="Preview the Shopify payload only" disabled={running} onClick={() => requireBlogId("publish-dry-run")} />
                  <ActionButton label="Publish" description="Publish to Shopify after confirmation" icon={<Send size={15} />} disabled={running} onClick={() => requireBlogId("publish")} />
                </div>
                </>}
              </section>
            </>
          ) : <div className={styles.emptyLarge}><FileText aria-hidden="true" size={28} /><strong>No queue item selected</strong></div>}
        </article>

        <aside className={styles.opsPane} aria-label="Content operations">
          <section>
            <div className={styles.sectionHeading}><h2>Due actions</h2></div>
            {dueActions.map((action) => (
              <button key={action.id} type="button" disabled={running || !action.due} onClick={() => {
                if (action.id === "write_brief") itemAction("Brief", "brief");
                if (action.id === "revise_brief") itemAction("Revise", "revise-brief");
                if (action.id === "content_report") launch({ label: "Daily report", action: "report", period: "daily" });
                if (action.id === "gsc_inspect") launch({ label: "GSC inspect", action: "gsc-inspect", limit: Number(limit) || 10 });
                if (action.id === "review_digest") launch({ label: "Review digest", action: "review-digest", profile: profile || undefined });
              }}>
                <Clock3 aria-hidden="true" size={15} /><span>{action.id.replaceAll("_", " ")}</span><small>{action.due ? "Ready" : "Not due"}</small>
              </button>
            ))}
          </section>

          <section>
            <div className={styles.sectionHeading}><h2>{briefMode ? "Intake" : "Global"}</h2><HelpTooltip label={briefMode ? "Brief intake" : "Global content settings"}>{briefMode ? "Turn researched keyword clusters into brief inputs, then draft against an existing content item." : "These project-level defaults are reused by imports, asset actions, reviews, and index checks."}</HelpTooltip></div>
            <p className={styles.sectionHint}>{briefMode ? "Research → brief, using the existing project evidence." : "Defaults for actions below."}</p>
            {briefMode ? <>
              <label className={styles.field}><span>Cluster file</span><input value={pathValue} onChange={(event) => setPathValue(event.target.value)} placeholder="strategy/keyword-clusters.json" /></label>
              <button type="button" disabled={running} onClick={() => launch({ label: "Cluster brief", action: "cluster-brief" })}>Cluster brief</button>
              <button type="button" disabled={running || !pathValue} onClick={() => launch({ label: "Import clusters", action: "import-clusters", project_relative_path: pathValue })}>Import clusters</button>
            </> : <>
              <label className={styles.field}><span>Feishu profile</span><input value={profile} onChange={(event) => setProfile(event.target.value)} placeholder="Required, e.g. hexcal-seo" /></label>
              <label className={styles.field}><span>Reviewer role</span><input value={role} onChange={(event) => setRole(event.target.value)} placeholder="seo" /></label>
              <label className={styles.field}><span>Asset limit</span><input value={limit} onChange={(event) => setLimit(event.target.value)} placeholder="20" inputMode="numeric" /></label>
              <label className={styles.field}><span>Import file</span><input value={pathValue} onChange={(event) => setPathValue(event.target.value)} placeholder="content/drafts/input.json" /></label>
              <button type="button" disabled={running || !profile.trim()} onClick={() => launch({ label: "Import Feishu", action: "import-feishu", profile: profile || undefined })}>Import Feishu</button>
              <button type="button" disabled={running || !pathValue} onClick={() => launch({ label: "Import draft", action: "import-draft", project_relative_path: pathValue })}>Import draft</button>
            </>}
          </section>
        </aside>
      </div>
      <section className={styles.latestJob}>
        <div className={styles.sectionHeading}><div><h2>Latest {briefMode ? "brief" : "production"} job</h2><p className={styles.sectionHint}>The most recent {briefMode ? "brief" : "production"} action and its command output.</p></div></div>
        {contentJob ? <div className={styles.job}><span>{contentJob.action}</span><StatusPill value={contentJob.status} context="status" />{contentJob.output ? <pre>{contentJob.output}</pre> : null}</div> : <p className={styles.muted}>No content job yet. Run a content action to see its status and command output here.</p>}
      </section>

      <section className={styles.files} aria-label="Content files">
        <header><h2>{briefMode ? "Brief sources" : "Production files"}</h2><span>{contentFiles.length}</span></header>
        <div>
          {contentFiles.map((file) => (
            <button key={file.path} type="button" onClick={() => onOpenFile(file.path)}><FileText aria-hidden="true" size={15} /><span>{file.path}</span></button>
          ))}
          {contentFiles.length === 0 ? <span className={styles.muted}>No content files yet.</span> : null}
        </div>
      </section>

      {!briefMode ? <label className={styles.writeback}><input type="checkbox" checked={noWriteback} onChange={(event) => setNoWriteback(event.target.checked)} />Skip MMX writeback</label> : null}
      {error ? <p className={styles.error} role="alert">{error}</p> : null}

      {running ? <span className={styles.running}><Loader2 aria-hidden="true" size={14} />Running</span> : null}
    </section>
  );
}
