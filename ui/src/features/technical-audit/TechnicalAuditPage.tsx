import { useEffect, useMemo, useState } from "react";
import { Clock3, Play, RefreshCw } from "lucide-react";

import type { AuditSection } from "../../components/AppShell";
import type { Job, TechAuditDataset, TechAuditSchedule } from "../../api/types";
import { deleteTechAuditRun, updateTechAuditSchedule } from "../../api/client";
import { confirmAction } from "../../components/ActionButton";
import { HelpTooltip } from "../../components/HelpTooltip";
import { useTechAudit } from "../../hooks/useWorkbenchData";
import { TechnicalAuditViewer } from "./TechnicalAuditViewer";
import styles from "./TechnicalAuditPage.module.css";

type TechnicalAuditPageProps = {
  projectId: string;
  jobs: Job[];
  refreshKey: number;
  onRunFull: () => Promise<void>;
  onContinue?: () => Promise<void>;
  onRecrawl: (urls: string[]) => Promise<void>;
  auditSection?: AuditSection;
  viewerDataset?: TechAuditDataset;
  viewerKey?: string | null;
  viewerRuleId?: string | null;
  viewerTemplate?: string | null;
};

const intervals = [15, 30, 60, 180, 720, 1440, 4320];

function formatTime(value?: string | null) {
  if (!value) return "Not run";
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(value));
}

function intervalLabel(minutes: number) {
  if (minutes < 60) return `${minutes} min`;
  if (minutes % 1440 === 0) return `${minutes / 1440} day${minutes === 1440 ? "" : "s"}`;
  return `${minutes / 60} hr`;
}

function phaseLabel(phase?: string) {
  return ({ robots: "Preparing crawl", sitemap: "Loading sitemaps", crawl: "Crawling URLs", finalizing: "Saving raw evidence", processing: "Normalizing issues", complete: "Crawl complete", failed: "Crawl failed" } as Record<string, string>)[phase || ""] || "Starting crawl";
}

function formatElapsed(seconds?: number) {
  if (seconds === undefined) return "—";
  const total = Math.max(0, Math.round(seconds));
  const minutes = Math.floor(total / 60);
  return minutes ? `${minutes}m ${total % 60}s` : `${total}s`;
}

export function TechnicalAuditPage({ projectId, jobs, refreshKey, onRunFull, onContinue, onRecrawl, auditSection = "overview", viewerDataset = "pages", viewerKey, viewerRuleId, viewerTemplate }: TechnicalAuditPageProps) {
  const { data, error, loading, refresh } = useTechAudit(projectId, refreshKey);
  const [enabled, setEnabled] = useState(false);
  const [everyMinutes, setEveryMinutes] = useState(60);
  const [notifyRole, setNotifyRole] = useState("");
  const [profile, setProfile] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    if (window.scrollY > 0) window.scrollTo({ top: 0, behavior: "smooth" });
  }, [auditSection]);

  useEffect(() => {
    if (!data) return;
    setEnabled(Boolean(data.schedule.enabled));
    setEveryMinutes(data.schedule.every_minutes || 60);
    setNotifyRole(data.schedule.notify_role || "");
    setProfile(data.schedule.profile || "");
  }, [data]);

  const running = jobs.some((job) => (job.status === "queued" || job.status === "running") && (job.action === "tech-audit" || job.action === "tech-audit-continue" || job.action === "tech-audit-recrawl" || job.action === "tech-audit:scheduled"));
  const crawlRunning = running || data?.run?.status === "running";
  const continuationAvailable = Boolean(data?.summary.continuation_available && onContinue);
  const recentJob = useMemo(() => jobs.find((job) => job.action.startsWith("tech-audit") && job.status !== "queued"), [jobs]);

  const run = (task: () => Promise<void>) => {
    setActionError(null);
    task().catch((reason: Error) => setActionError(reason.message));
  };

  const saveSchedule = () => {
    setActionError(null);
    const payload: TechAuditSchedule = { enabled, every_minutes: everyMinutes, notify_role: notifyRole.trim(), profile: profile.trim() };
    updateTechAuditSchedule(projectId, payload).then(refresh).catch((reason: Error) => setActionError(reason.message));
  };

  const deleteRun = async (runId: string): Promise<boolean> => {
    if (!confirmAction(`Delete audit run ${runId}? Its snapshot and URL evidence will be removed.`)) return false;
    await deleteTechAuditRun(projectId, runId);
    await refresh();
    return true;
  };

  return (
    <section className={styles.page} aria-labelledby="technical-audit-heading">
      <h1 id="technical-audit-heading" className="srOnly">Technical audit</h1>
      <header className={styles.header}>
        <div className={styles.headerActions}>
          <div className={styles.actionWithHelp}><button className={styles.secondaryButton} type="button" onClick={refresh} disabled={loading}><RefreshCw aria-hidden="true" size={15} />Refresh</button><HelpTooltip label="Refresh technical audit view">Reloads the latest local audit evidence into this view. It does not start a new crawl.</HelpTooltip></div>
          {continuationAvailable ? <button className={styles.secondaryButton} type="button" onClick={() => run(onContinue!)} disabled={crawlRunning}><Play aria-hidden="true" size={15} fill="currentColor" />Continue crawl ({data?.summary.queued_remaining ?? 0})</button> : null}
          <div className={styles.actionWithHelp}><button className={styles.primaryButton} type="button" onClick={() => run(onRunFull)} disabled={crawlRunning}><Play aria-hidden="true" size={15} fill="currentColor" />Run full crawl</button><HelpTooltip label="Run full crawl">Starts the technical crawler and collects fresh HTTP, sitemap, and URL evidence. Additional evidence collectors are available from the Plan page.</HelpTooltip></div>
        </div>
      </header>

      {error || actionError ? <p className={styles.error} role="alert">{error || actionError}</p> : null}

      {data?.run?.status === "running" ? (() => {
        const run = data.run;
        const determinate = Boolean(run.max_urls);
        const progress = determinate ? Math.min(100, Math.round(((run.processed_urls || 0) / (run.max_urls || 1)) * 100)) : 0;
        return (
          <section className={styles.liveRun} aria-live="polite" aria-label="Crawl progress">
            <div className={styles.liveRunTop}>
              <span className={styles.spinner} aria-hidden="true" />
              <div><span className={styles.eyebrow}>Live crawl</span><strong>{phaseLabel(run.phase)}</strong><small>{formatElapsed(run.elapsed_seconds)} · {run.run_id || "current run"}</small></div>
              <b>{run.processed_urls || 0}{run.max_urls ? ` / ${run.max_urls}` : ""}</b>
            </div>
            <div className={styles.progressTrack} data-indeterminate={determinate ? "false" : "true"} role="progressbar" aria-valuemin={0} aria-valuemax={determinate ? run.max_urls : undefined} aria-valuenow={determinate ? run.processed_urls || 0 : undefined} aria-label={phaseLabel(run.phase)}><span style={{ transform: `scaleX(${progress / 100})` }} /></div>
            <p>{run.sitemap_count ? `${run.sitemap_count} sitemaps loaded · ${run.discovered_urls || 0} unique URLs discovered · ${run.queued_remaining || 0} queued` : "Preparing robots.txt and sitemap discovery"}{run.error_count ? ` · ${run.error_count} errors` : ""}</p>
          </section>
        );
      })() : null}

      {auditSection === "overview" ? (
        <div className={styles.metrics} aria-label="Technical audit summary">
          <div><span>Latest crawl</span><strong className={styles.date}>{formatTime(data?.snapshot.generated_at)}</strong><small>{data?.snapshot.collection_status || "No snapshot"}</small></div>
          <div><span>URLs crawled</span><strong>{data?.summary.crawled_pages ?? data?.summary.pages ?? "—"}</strong><small>{data?.summary.queued_remaining ? `${data.summary.queued_remaining} queued · ${data.summary.discovered_unique ?? "—"} discovered` : "Latest complete snapshot"}</small></div>
          <div><span>404 queue</span><strong>{data?.summary.four_oh_four ?? "—"}</strong><small>Internal pages</small></div>
          <div><span>Issues</span><strong>{data?.summary.issues ?? "—"}</strong><small>Deterministic hits</small></div>
        </div>
      ) : null}

      {auditSection === "automation" ? <div className={styles.singleColumn}>
        <section className={styles.card} aria-labelledby="schedule-heading">
          <div className={styles.cardHeading}><div><span className={styles.eyebrow}>Automation</span><h2 id="schedule-heading">Scheduled crawl</h2></div><Clock3 aria-hidden="true" size={20} /></div>
          <p className={styles.muted}>Runs the same CLI crawl and sends new high-impact issues through the bound Feishu profile.</p>
          <label className={styles.switchRow}><input type="checkbox" checked={enabled} onChange={(event) => setEnabled(event.target.checked)} /><span>{enabled ? "Enabled" : "Disabled"}</span></label>
          <div className={styles.formGrid}>
            <label><span>Interval</span><select value={everyMinutes} onChange={(event) => setEveryMinutes(Number(event.target.value))}>{intervals.map((value) => <option value={value} key={value}>{intervalLabel(value)}</option>)}</select></label>
            <label><span>Feishu role</span><input value={notifyRole} onChange={(event) => setNotifyRole(event.target.value)} placeholder="Optional, e.g. seo" /></label>
            <label><span>Profile</span><input value={profile} onChange={(event) => setProfile(event.target.value)} placeholder="Required when a Feishu role is set" /></label>
          </div>
          <div className={styles.scheduleFooter}><small>Next run: {formatTime(data?.schedule.next_run_at)}</small><button className={styles.secondaryButton} type="button" onClick={saveSchedule}>Save schedule</button></div>
          <p className={styles.note}>The local UI scheduler runs while this workbench process is open. The saved schedule remains available to the CLI for cron or launchd.</p>
        </section>
      </div> : null}
      {auditSection === "url-inventory" ? <TechnicalAuditViewer id="technical-audit-viewer" initialDataset={viewerDataset} initialKey={viewerKey} initialRuleId={viewerRuleId} initialTemplate={viewerTemplate} projectId={projectId} crawlRunning={crawlRunning} refreshKey={refreshKey} history={data?.history || []} totalHint={data?.summary.pages} onDeleteRun={deleteRun} onRecrawl={onRecrawl} /> : null}
      {auditSection === "overview" && recentJob?.output ? <details className={styles.jobOutput}><summary>Latest crawl output · {recentJob.status}</summary><pre>{recentJob.output}</pre></details> : null}
    </section>
  );
}
