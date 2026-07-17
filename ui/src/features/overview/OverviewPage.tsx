import { ArrowRight, FileText } from "lucide-react";

import type { Workspace } from "../../api/types";
import { EvidenceRail } from "./EvidenceRail";
import styles from "./Overview.module.css";


type OverviewPageProps = {
  workspace: Workspace;
  updatedPaths: Record<string, string>;
  onNavigateWorkflow: () => void;
  onOpenFile: (path: string) => void;
};

const layerLabels: Record<string, string> = {
  commerce: "Commerce",
  delivery: "Delivery",
  acquisition_data: "Acquisition and data",
  frontend: "Frontend",
  content_metadata: "Content metadata",
  trust_compliance: "Trust and compliance",
};

function metric(value: number | null, kind: "lcp" | "tbt" | "cls") {
  if (value === null || value === undefined) return "No data";
  if (kind === "lcp") return `${(value / 1000).toFixed(1)} s`;
  if (kind === "tbt") return `${Math.round(value)} ms`;
  return value.toFixed(3);
}

function fileTime(value: string) {
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(value));
}


export function OverviewPage({ workspace, updatedPaths, onNavigateWorkflow, onOpenFile }: OverviewPageProps) {
  const performance = workspace.evidence.performance;
  const layers = workspace.evidence.technology.layers || {};
  const diff = workspace.evidence.diff;
  const score = performance.score ?? 0;

  return (
    <div className={styles.overviewLayout}>
      <section className={styles.overviewContent} aria-label="Project overview">
        <div className={styles.primaryGrid}>
          <section className={styles.performanceSection}>
            <div className={styles.sectionHeading}>
              <h1>Performance evidence</h1>
              <span>Lighthouse · mobile</span>
            </div>
            <div className={styles.scoreBand}>
              <div><span>Score</span><strong>{performance.score ?? "N/A"}</strong><small>/100</small></div>
              <div className={styles.scoreTrack} aria-label={`Performance score ${performance.score ?? "not available"} out of 100`}>
                <span style={{ transform: `scaleX(${Math.max(0, Math.min(score, 100)) / 100})` }} />
              </div>
            </div>
            <div className={styles.metricTable} role="table" aria-label="Performance metrics">
              <div className={styles.tableHead} role="row"><span>Metric</span><span>Value</span><span>Assessment</span></div>
              {[
                ["LCP", metric(performance.metrics.lcp, "lcp")],
                ["TBT", metric(performance.metrics.tbt, "tbt")],
                ["CLS", metric(performance.metrics.cls, "cls")],
                ["Variance", performance.high_variance ? "High variance" : "Stable"],
              ].map(([label, value]) => (
                <div className={styles.tableRow} role="row" key={label}>
                  <strong>{label}</strong><span>{value}</span><b className={performance.high_variance ? styles.regressionText : styles.ready}>Review</b>
                </div>
              ))}
            </div>
          </section>

          <section className={styles.workflowSection}>
            <div className={styles.sectionHeading}><h2>Workflow</h2><span>{workspace.phase}</span></div>
            <button className={styles.nextAction} type="button" onClick={onNavigateWorkflow}>
              <span><small>Next action</small><strong>{workspace.next?.label || workspace.step?.label || "Workflow complete"}</strong></span>
              <ArrowRight aria-hidden="true" size={20} />
            </button>
            <ol className={styles.phaseList}>
              {workspace.phase_order.map((phase) => {
                const current = phase === workspace.phase;
                const complete = workspace.phases[phase]?.status === "done";
                return (
                  <li className={current ? styles.currentPhase : complete ? styles.completePhase : undefined} key={phase}>
                    <span />
                    <strong>{phase.replaceAll("_", " ")}</strong>
                    <small>{current ? "Current" : complete ? "Complete" : "Upcoming"}</small>
                  </li>
                );
              })}
            </ol>
            <p className={styles.localState}>State stored locally</p>
          </section>
        </div>

        <div className={styles.secondaryGrid}>
          <section className={styles.architectureSection}>
            <div className={styles.sectionHeading}><h2>Technology architecture</h2></div>
            {Object.entries(layers).slice(0, 5).map(([layer, technologies]) => (
              <div className={styles.architectureRow} key={layer}>
                <strong>{layerLabels[layer] || layer.replaceAll("_", " ")}</strong>
                <span>{technologies.join(" · ")}</span>
              </div>
            ))}
            {Object.keys(layers).length === 0 ? <p className={styles.emptyCopy}>Run technology evidence to populate architecture layers.</p> : null}
          </section>

          <section className={styles.diffSection}>
            <div className={styles.sectionHeading}><h2>Diff evidence</h2><span>Latest comparable snapshots</span></div>
            <div className={styles.diffNumbers}>
              <div><strong>{diff.changes ?? "N/A"}</strong><span>changes</span></div>
              <div className={styles.regressionText}><strong>{diff.regressions ?? "N/A"}</strong><span>regressions</span></div>
              <div className={styles.ready}><strong>{diff.improvements ?? "N/A"}</strong><span>improvements</span></div>
            </div>
          </section>

          <section className={styles.recentSection}>
            <div className={styles.sectionHeading}><h2>Recent workspace files</h2></div>
            <div className={styles.fileTable}>
              {workspace.recent_files.slice(0, 5).map((file) => {
                const updated = updatedPaths[file.path];
                return (
                  <button className={updated ? styles.updatedFile : styles.fileRow} key={file.path} type="button" onClick={() => onOpenFile(file.path)}>
                    <FileText aria-hidden="true" size={17} strokeWidth={1.5} />
                    <span><strong>{file.name}</strong><small>{updated ? "Agent updated" : file.path}</small></span>
                    <time>{updated ? "now" : fileTime(file.modified_at)}</time>
                  </button>
                );
              })}
            </div>
          </section>
        </div>
      </section>
      <EvidenceRail items={workspace.evidence.items} />
    </div>
  );
}
