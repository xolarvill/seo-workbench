import { CheckCircle2, Download, FileChartColumn, Loader2, Presentation, RefreshCw, XCircle } from "lucide-react";
import { useState } from "react";

import { downloadPresentationPdf } from "../../api/client";
import type { Job } from "../../api/types";
import { StatusPill } from "../../components/StatusPill";
import { usePresentationStatus } from "../../hooks/useWorkbenchData";
import styles from "./PresentationSection.module.css";

type Props = {
  projectId: string;
  jobs: Job[];
  refreshKey: number;
  onRunPresentation: () => Promise<void>;
};

function whenLabel(value: string | undefined) {
  if (!value) return "No artifact yet";
  try {
    return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
  } catch {
    return value;
  }
}

export function PresentationSection({ projectId, jobs, refreshKey, onRunPresentation }: Props) {
  const { status, error: loadError } = usePresentationStatus(projectId, refreshKey);
  const [actionError, setActionError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const running = jobs.some((job) => ["presentation-weekly", "presentation:scheduled"].includes(job.action) && ["queued", "running"].includes(job.status));

  const generate = async () => {
    setActionError(null);
    try {
      await onRunPresentation();
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : String(reason));
    }
  };

  const download = async () => {
    if (!status?.artifact) return;
    setDownloading(true);
    setActionError(null);
    try {
      const blob = await downloadPresentationPdf(projectId);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = status.artifact.path.split("/").pop() || "seo-weekly-presentation.pdf";
      link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 0);
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setDownloading(false);
    }
  };

  return (
    <section className={styles.page} aria-labelledby="presentation-heading">
      <header className={styles.header}>
        <div><span>For team review</span><h1 id="presentation-heading">Presentation</h1><p>Generate a visual weekly SEO briefing for the whole team. It reads existing evidence and work records; it does not replace the internal Weekly archive.</p></div>
        <Presentation aria-hidden="true" size={28} strokeWidth={1.5} />
      </header>

      {loadError ? <p className={styles.error} role="alert">{loadError}</p> : null}
      {actionError ? <p className={styles.error} role="alert">{actionError}</p> : null}
      {!status ? <p className={styles.empty}>Checking evidence freshness…</p> : (
        <>
          <section className={styles.heroCard}>
            <div className={styles.heroCopy}>
              <span className={styles.kicker}>Friday afternoon output</span>
              <h2>SEO weekly briefing · W{String(status.target_week.week).padStart(2, "0")}</h2>
              <p>Default gate: statistics completed within {status.max_statistics_age_hours} hours, finalized GSC data no more than three days behind, and at least 28 days of GSC and business history.</p>
            </div>
            <div className={styles.heroActions}>
              <StatusPill value={status.status} context="evidence" />
              <button type="button" className={styles.primaryAction} disabled={!status.ready || running} onClick={() => void generate()}>
                {running ? <Loader2 aria-hidden="true" size={15} className={styles.spin} /> : <FileChartColumn aria-hidden="true" size={15} />}
                {running ? "Generating" : "Generate PDF"}
              </button>
              <button type="button" className={styles.secondaryAction} disabled={!status.artifact || downloading} onClick={() => void download()}>
                {downloading ? <Loader2 aria-hidden="true" size={15} className={styles.spin} /> : <Download aria-hidden="true" size={15} />}
                {downloading ? "Downloading" : "Download latest"}
              </button>
            </div>
          </section>

          <div className={styles.grid}>
            <section className={styles.card}>
              <header><span className={styles.kicker}>Data gate</span><h2>Before the meeting</h2></header>
              <ul className={styles.checkList}>
                {status.checks.map((check) => <li key={check.code}><span className={check.passed ? styles.checkGood : styles.checkBad}>{check.passed ? <CheckCircle2 aria-hidden="true" size={16} /> : <XCircle aria-hidden="true" size={16} />}</span><span><strong>{check.label}</strong><small>{check.detail}</small></span></li>)}
              </ul>
              {status.warnings.length ? <div className={styles.warning}><strong>Read with caveats</strong><ul>{status.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></div> : null}
            </section>

            <section className={styles.card}>
              <header><span className={styles.kicker}>Latest artifact</span><h2>Shareable output</h2></header>
              {status.artifact ? <div className={styles.artifact}><strong>{status.artifact.path}</strong><span>Generated {whenLabel(status.artifact.generated_at)}</span><span>{Math.max(1, Math.round(status.artifact.size / 1024))} KB PDF</span></div> : <p className={styles.empty}>No presentation has been generated for this project yet.</p>}
              <div className={styles.note}><RefreshCw aria-hidden="true" size={14} /><span>Run Statistics before Friday afternoon so the deck reflects finalized evidence.</span></div>
            </section>
          </div>
        </>
      )}
    </section>
  );
}
