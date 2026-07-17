import { Activity, Gauge, GitCompareArrows, Globe2, SearchCheck, ServerCog, X } from "lucide-react";

import type { Job } from "../../api/types";
import styles from "./ActionPanel.module.css";

const actions = [
  { id: "evidence", label: "Basic evidence", detail: "Fetch raw HTML, redirects, metadata and route samples.", icon: Globe2 },
  { id: "technology", label: "Technology", detail: "Detect runtime technologies and explain SEO architecture impact.", icon: ServerCog },
  { id: "performance", label: "Lighthouse", detail: "Run the reliable multi-run lab performance benchmark.", icon: Gauge },
  { id: "crux", label: "CrUX field data", detail: "Collect current and historical real-user performance.", icon: Activity },
  { id: "gsc", label: "Search Console", detail: "Collect read-only performance, indexing and Sitemap evidence.", icon: SearchCheck },
  { id: "audit-diff", label: "Audit diff", detail: "Compare the latest compatible evidence snapshots.", icon: GitCompareArrows },
];

export function ActionPanel({ open, jobs, onClose, onRun }: { open: boolean; jobs: Job[]; onClose: () => void; onRun: (action: string) => void }) {
  const running = jobs.find((job) => job.status === "running" || job.status === "queued");
  const latest = jobs[0];
  return (
    <>
      {open ? <button className={styles.scrim} type="button" aria-label="Close audit actions" onClick={onClose} /> : null}
      <aside className={`${styles.panel} ${open ? styles.open : ""}`} aria-hidden={!open} aria-labelledby="action-panel-heading">
        <header><div><span>Local execution</span><h2 id="action-panel-heading">Run audit evidence</h2></div><button type="button" onClick={onClose} aria-label="Close"><X aria-hidden="true" size={20} /></button></header>
        <p className={styles.intro}>Each collector runs as the same project-scoped CLI command an agent would use.</p>
        <div className={styles.actions}>
          {actions.map(({ id, label, detail, icon: Icon }) => (
            <button type="button" key={id} onClick={() => onRun(id)} disabled={Boolean(running)}>
              <Icon aria-hidden="true" size={19} strokeWidth={1.5} />
              <span><strong>{label}</strong><small>{detail}</small></span>
              <b>{running?.action === id ? "Running" : "Run"}</b>
            </button>
          ))}
        </div>
        {latest ? (
          <section className={styles.latest} aria-live="polite">
            <span>Latest task</span><strong>{latest.action}</strong><b data-status={latest.status}>{latest.status}</b>
            {latest.output ? <details><summary>Task output</summary><pre>{latest.output}</pre></details> : null}
          </section>
        ) : null}
      </aside>
    </>
  );
}
