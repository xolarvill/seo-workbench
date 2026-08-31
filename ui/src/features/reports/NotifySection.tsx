import { FileChartColumn, FileText, Loader2, Search, Send } from "lucide-react";
import { useState } from "react";

import type { ContentJobAction, Job } from "../../api/types";
import { ActionButton, confirmExternalAction } from "../../components/ActionButton";
import { useFiles } from "../../hooks/useWorkbenchData";
import styles from "./NotifySection.module.css";

type Props = {
  projectId: string;
  jobs: Job[];
  refreshKey: number;
  onOpenFile: (path: string) => void;
  onRunContentAction: (action: ContentJobAction) => Promise<void>;
};

type RunRequest = ContentJobAction & { label: string; danger?: boolean };

export function NotifySection({ projectId, jobs, refreshKey, onOpenFile, onRunContentAction }: Props) {
  const { files } = useFiles(projectId, refreshKey);
  const [reportPath, setReportPath] = useState("");
  const [role, setRole] = useState("seo");
  const [profile, setProfile] = useState("");
  const [error, setError] = useState<string | null>(null);
  const running = jobs.some((job) => job.status === "running" || job.status === "queued");
  const reportFiles = files.filter((file) => file.path.startsWith("content/reports/")).sort((left, right) => right.modified_at.localeCompare(left.modified_at));

  const run = async (request: RunRequest) => {
    setError(null);
    const { label: _label, danger: _danger, ...payload } = request;
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

  return (
    <section className={styles.page} aria-labelledby="notify-heading">
      <h1 id="notify-heading" className="srOnly">Notifications</h1>

      <div className={styles.grid}>
        <section className={styles.card}>
          <div><span className={styles.kicker}>Local output</span><h2>Content reports</h2><p>Daily and weekly reports are written to <code>content/reports/</code>. Each run creates a Markdown file for review.</p></div>
          <div className={styles.actions}>
            <ActionButton label="Daily report" description="Write the current daily report" icon={<FileChartColumn size={15} />} disabled={running} onClick={() => launch({ label: "Daily report", action: "report", period: "daily" })} />
            <ActionButton label="Weekly report" description="Write the current weekly report" icon={<FileChartColumn size={15} />} disabled={running} onClick={() => launch({ label: "Weekly report", action: "report", period: "weekly" })} />
          </div>
        </section>

        <section className={styles.card}>
          <div><span className={styles.kicker}>Index monitoring</span><h2>Inspection & notifications</h2><p>Inspect content URLs first, then optionally notify the configured reviewer with the result.</p></div>
          <div className={styles.actions}>
            <ActionButton label="Index queue" description="List content URLs waiting for inspection" icon={<Search size={15} />} disabled={running} onClick={() => launch({ label: "Index queue", action: "index-queue" })} />
            <ActionButton label="Index status + notify" description="Check indexing status and notify the reviewer" icon={<Send size={15} />} disabled={running || !profile.trim()} onClick={() => launch({ label: "Index status + notify", action: "index-status", role, profile: profile || undefined, danger: true })} />
            <label className={styles.field}><span>Report file to notify</span><input value={reportPath} onChange={(event) => setReportPath(event.target.value)} placeholder="content/reports/2026-08-12-daily.md" /></label>
            <ActionButton label="Notify report" description="Send a report file to the configured reviewer" icon={<Send size={15} />} disabled={running || !reportPath || !profile.trim()} onClick={() => launch({ label: "Notify report", action: "notify-report", report_path: reportPath, title: "Content report", role, profile: profile || undefined, danger: true })} />
          </div>
        </section>

        <section className={styles.card}>
          <div><span className={styles.kicker}>Defaults</span><h2>Report settings</h2><p>These values are used when reports or index results are sent to a reviewer.</p></div>
          <label className={styles.field}><span>Reviewer role</span><input value={role} onChange={(event) => setRole(event.target.value)} placeholder="seo" /></label>
          <label className={styles.field}><span>Feishu profile</span><input value={profile} onChange={(event) => setProfile(event.target.value)} placeholder="Required, e.g. hexcal-seo" /></label>
        </section>

        <section className={styles.card}>
          <div><span className={styles.kicker}>Generated files</span><h2>Report files</h2><p>Open the Markdown reports generated by the local CLI or this workspace.</p></div>
          <div className={styles.fileList}>
            {reportFiles.map((file) => <button type="button" key={file.path} onClick={() => onOpenFile(file.path)}><FileText aria-hidden="true" size={15} /><span>{file.path}</span></button>)}
            {reportFiles.length === 0 ? <span className={styles.empty}>No reports generated yet.</span> : null}
          </div>
        </section>
      </div>

      {error ? <p className={styles.error} role="alert">{error}</p> : null}
      {running ? <span className={styles.running}><Loader2 aria-hidden="true" size={14} />Running</span> : null}
    </section>
  );
}
