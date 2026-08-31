import { ArrowRight, BarChart3, Braces, ChevronDown, FileText, Gauge, GitBranch, TrendingUp } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";

import type { Workspace } from "../../api/types";
import { StatusPill, type StatusTone } from "../../components/StatusPill";
import { EvidenceStatusCard } from "./EvidenceRail";
import styles from "./Overview.module.css";


type OverviewPageProps = {
  workspace: Workspace;
  updatedPaths: Record<string, string>;
  onNavigateWorkflow: () => void;
  onNavigatePages: (filters: { group: string; source: string }) => void;
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

function scoreTone(score: number | null) {
  if (score === null || score === undefined) return styles.statusInfo;
  if (score < 50) return styles.statusDanger;
  if (score < 90) return styles.statusWarning;
  return styles.statusSuccess;
}

function healthLabel(score: number | null) {
  if (score === null || score === undefined) return "No score yet";
  if (score < 50) return "Needs attention";
  if (score < 90) return "Watch closely";
  return "Healthy";
}

function healthStatusTone(score: number | null): StatusTone {
  if (score === null || score === undefined) return "info";
  if (score < 50) return "danger";
  if (score < 90) return "warning";
  return "success";
}

function phaseLabel(phase: string) {
  return phase.replaceAll("_", " ");
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : null;
}

function numberLabel(value: unknown, digits = 1) {
  return typeof value === "number" ? value.toLocaleString(undefined, { maximumFractionDigits: digits }) : "No data";
}

function percentLabel(value: unknown) {
  return typeof value === "number" ? `${(value * 100).toFixed(1)}%` : "No data";
}

function DetailRow({ icon: Icon, title, subtitle, summary, children }: { icon: typeof Gauge; title: string; subtitle: string; summary: ReactNode; children: ReactNode }) {
  return <details className={styles.detailRow}>
    <summary>
      <span className={styles.detailRowTitle}><Icon aria-hidden="true" size={17} strokeWidth={1.7} /><span><strong>{title}</strong><small>{subtitle}</small></span></span>
      <span className={styles.detailRowSummary}>{summary}</span>
      <ChevronDown className={styles.detailRowChevron} aria-hidden="true" size={17} />
    </summary>
    <div className={styles.detailRowBody}>{children}</div>
  </details>;
}

function DetailGroup({ index, title, subtitle, children }: { index: string; title: string; subtitle: string; children: ReactNode }) {
  return <details className={styles.detailGroup} open>
    <summary className={styles.detailGroupHeader}>
      <span className={styles.groupIndex}>{index}</span>
      <span><strong>{title}</strong><small>{subtitle}</small></span>
      <ChevronDown className={styles.groupChevron} aria-hidden="true" size={18} />
    </summary>
    <div className={styles.detailGroupRows}>{children}</div>
  </details>;
}

export function OverviewPage({ workspace, updatedPaths, onNavigateWorkflow, onNavigatePages, onOpenFile }: OverviewPageProps) {
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const evidenceFactRef = useRef<HTMLDivElement>(null);
  const performance = workspace.evidence.performance;
  const layers = workspace.evidence.technology.layers || {};
  const diff = workspace.evidence.diff;
  const business = workspace.evidence.business;
  const currentBusiness = business.windows.current;
  const portfolioStatistics = asRecord(workspace.content.portfolio.statistics);
  const clickDecomposition = asRecord(portfolioStatistics?.click_change_decomposition);
  const queryPortfolio = asRecord(portfolioStatistics?.query_portfolio);
  const currentQueries = asRecord(queryPortfolio?.current);
  const previousQueries = asRecord(queryPortfolio?.previous);
  const rankingOpportunity = asRecord(portfolioStatistics?.ranking_opportunity);
  const commercialValue = asRecord(portfolioStatistics?.commercial_value);
  const searchConfidence = asRecord(portfolioStatistics?.search_change_confidence);
  const confidenceClickChange = asRecord(searchConfidence?.click_change);
  const searchTrend = asRecord(portfolioStatistics?.search_trend);
  const ctrBenchmark = asRecord(portfolioStatistics?.ctr_benchmark);
  const crossSource = asRecord(portfolioStatistics?.cross_source_consistency);
  const technicalEffects = asRecord(portfolioStatistics?.technical_issue_effects);
  const score = performance.score ?? 0;
  const nextLabel = workspace.next?.label || workspace.step?.label || "Workflow complete";
  const evidenceReady = workspace.evidence.items.filter((item) => ["ok", "ready", "complete"].includes(item.status)).length;

  useEffect(() => {
    if (!evidenceOpen) return;
    const closeOnOutsideClick = (event: PointerEvent) => {
      if (!evidenceFactRef.current?.contains(event.target as Node)) setEvidenceOpen(false);
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setEvidenceOpen(false);
    };
    document.addEventListener("pointerdown", closeOnOutsideClick);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutsideClick);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [evidenceOpen]);

  return (
    <div className={styles.overviewLayout}>
      <section className={styles.detailPane} aria-label="Overview details">
        <header className={styles.detailHeader}>
          <h2 className="srOnly">Project health</h2>
          <div className={styles.detailHeaderStatus}>
            <span>Evidence snapshot</span>
            <StatusPill value={healthLabel(performance.score)} tone={healthStatusTone(performance.score)} />
          </div>
        </header>
        <section className={styles.healthSummary} aria-label="Project health summary">
          <div className={styles.healthScore}>
            <span className={styles.eyebrow}>Project health score</span>
            <div><strong className={scoreTone(performance.score)}>{performance.score ?? "N/A"}</strong><span>/100</span></div>
            <b className={scoreTone(performance.score)}>{healthLabel(performance.score)}</b>
            <p>Score reflects overall SEO performance and data completeness.</p>
          </div>
          <div className={styles.healthFacts}>
            <div className={styles.evidenceFact} ref={evidenceFactRef}>
              <button className={styles.evidenceTrigger} type="button" aria-label="Evidence ready, click to see all" aria-expanded={evidenceOpen} aria-controls="evidence-status-card" onClick={() => setEvidenceOpen((open) => !open)}>
                <span>Evidence ready</span>
                <strong>{evidenceReady}/{workspace.evidence.items.length || "—"}</strong>
                <small>Current coverage</small>
                <span>Click to see all</span>
              </button>
              {evidenceOpen ? <EvidenceStatusCard items={workspace.evidence.items} /> : null}
            </div>
            <div><span>Reviews due</span><strong className={workspace.changes.due ? styles.statusWarning : styles.statusSuccess}>{workspace.changes.due}</strong><small>SEO changes</small></div>
            <div><span>Current phase</span><strong>{phaseLabel(workspace.phase)}</strong><small>{workspace.step?.label || "No pending step"}</small></div>
          </div>
          <button className={styles.nextAction} type="button" onClick={onNavigateWorkflow}>
            <span><small>Next action</small><strong>{nextLabel}</strong><em>Open workflow</em></span>
            <ArrowRight aria-hidden="true" size={20} />
          </button>
        </section>

        <div className={styles.detailBody}>
          <DetailGroup index="1" title="Performance" subtitle="Site performance and channel visibility">
            <DetailRow icon={Gauge} title="Mobile Lighthouse" subtitle="Latest lab run" summary={<><b className={scoreTone(performance.score)}>{performance.score ?? "N/A"}</b><span>/100</span><span>LCP {metric(performance.metrics.lcp, "lcp")}</span><span>TBT {metric(performance.metrics.tbt, "tbt")}</span><b className={performance.high_variance ? styles.statusWarning : styles.statusSuccess}>{performance.high_variance ? "Review" : "Stable"}</b></>}>
              <div className={styles.scoreBand}>
                <div><span>Score</span><strong className={scoreTone(performance.score)}>{performance.score ?? "N/A"}</strong><small>/100</small></div>
                <div className={styles.scoreTrack} aria-label={`Performance score ${performance.score ?? "not available"} out of 100`}><span className={scoreTone(performance.score)} style={{ transform: `scaleX(${Math.max(0, Math.min(score, 100)) / 100})` }} /></div>
              </div>
              <div className={styles.metricTable} role="table" aria-label="Performance metrics">
                <div className={styles.tableHead} role="row"><span>Metric</span><span>Value</span><span>Assessment</span></div>
                {[["LCP", metric(performance.metrics.lcp, "lcp")], ["TBT", metric(performance.metrics.tbt, "tbt")], ["CLS", metric(performance.metrics.cls, "cls")], ["Variance", performance.high_variance ? "High variance" : "Stable"]].map(([label, value]) => <div className={styles.tableRow} role="row" key={label}><strong>{label}</strong><span>{value}</span><b className={performance.high_variance ? styles.statusWarning : styles.statusSuccess}>{performance.high_variance ? "Review" : "Stable"}</b></div>)}
              </div>
            </DetailRow>
            <DetailRow icon={BarChart3} title="Channel overview" subtitle="GA4 sessions by acquisition channel" summary={workspace.evidence.channels.length ? <><b>{workspace.evidence.channels[0].channel}</b><span>{Math.round(workspace.evidence.channels[0].sessions).toLocaleString()} sessions</span><span>{Math.round(workspace.evidence.channels[0].users).toLocaleString()} users</span></> : <span>No data</span>}>
              {workspace.evidence.channels.length ? <div className={styles.metricTable} role="table" aria-label="Channel metrics"><div className={styles.tableHead} role="row"><span>Channel</span><span>Sessions</span><span>Users</span><span>Key events</span></div>{workspace.evidence.channels.slice(0, 6).map((channel) => <div className={styles.tableRow} role="row" key={channel.channel}><strong>{channel.channel}</strong><span>{Math.round(channel.sessions)}</span><span>{Math.round(channel.users)}</span><b className={channel.key_events > 0 ? styles.statusSuccess : undefined}>{Math.round(channel.key_events)}</b></div>)}</div> : <p className={styles.emptyCopy}>Run GA4 evidence to populate the channel overview.</p>}
            </DetailRow>
          </DetailGroup>

          <DetailGroup index="2" title="Growth and outcomes" subtitle="Business impact and SEO results">
            <DetailRow icon={TrendingUp} title="Business signals" subtitle={currentBusiness ? `${currentBusiness.start_date} → ${currentBusiness.end_date}` : "GA4 + Shopify page evidence"} summary={currentBusiness ? <><span>{Math.round(currentBusiness.organic_sessions).toLocaleString()} organic sessions</span><span>{Math.round(currentBusiness.key_events).toLocaleString()} key events</span><span>{currentBusiness.revenue.toLocaleString(undefined, { maximumFractionDigits: 0 })} {business.currency || "revenue"}</span></> : <span>No data</span>}>
              {currentBusiness ? <><div className={styles.diffNumbers}><div><strong>{Math.round(currentBusiness.organic_sessions).toLocaleString()}</strong><span>organic sessions</span></div><div><strong>{Math.round(currentBusiness.engaged_sessions).toLocaleString()}</strong><span>engaged sessions</span></div><div><strong>{Math.round(currentBusiness.key_events).toLocaleString()}</strong><span>key events</span></div></div><div className={styles.diffNumbers}><div><strong>{currentBusiness.revenue.toLocaleString(undefined, { maximumFractionDigits: 0 })}</strong><span>{business.currency ? `${business.currency} product revenue` : "product revenue"}</span></div><div><strong>{Math.round(currentBusiness.orders).toLocaleString()}</strong><span>all-channel product orders</span></div></div></> : <p className={styles.emptyCopy}>Run GA4, Shopify orders, and business signals evidence.</p>}
            </DetailRow>
            <DetailRow icon={TrendingUp} title="SEO change outcomes" subtitle="Recorded changes and review evidence" summary={<><span>{workspace.changes.count} recorded</span><span className={workspace.changes.due ? styles.statusWarning : undefined}>{workspace.changes.due} due</span><span className={styles.statusSuccess}>{workspace.changes.counts.reviewed || 0} reviewed</span></>}>
              <div className={styles.diffNumbers}><div><strong>{workspace.changes.count}</strong><span>recorded</span></div><div className={workspace.changes.due ? styles.statusWarning : undefined}><strong>{workspace.changes.due}</strong><span>due</span></div><div className={styles.statusSuccess}><strong>{workspace.changes.counts.reviewed || 0}</strong><span>reviewed</span></div></div>
              {workspace.changes.items.map((change) => <div className={styles.architectureRow} key={change.id}><strong>{(change.classification || change.status).replaceAll("_", " ")}</strong><span title={change.hypothesis}>{change.hypothesis}</span></div>)}
              {workspace.changes.items.length === 0 ? <p className={styles.emptyCopy}>Record an SEO change to start outcome review.</p> : null}
              <button className={styles.cardLink} type="button" onClick={() => onNavigatePages({ group: "review", source: "change" })}>Open outcome reviews <ArrowRight size={14} /></button>
            </DetailRow>
            <DetailRow icon={BarChart3} title="Page portfolio" subtitle="Full-site decisions from combined evidence" summary={<><span>{workspace.content.portfolio.count} observed</span><b className={styles.statusWarning}>{workspace.content.portfolio.counts.refresh || 0} refresh</b><b className={styles.statusSuccess}>{workspace.content.portfolio.counts.defend || 0} defend</b></>}>
              <div className={styles.diffNumbers}><div><strong>{workspace.content.portfolio.count}</strong><span>observed</span></div><div className={styles.statusWarning}><strong>{workspace.content.portfolio.counts.refresh || 0}</strong><span>refresh</span></div><div className={styles.statusSuccess}><strong>{workspace.content.portfolio.counts.defend || 0}</strong><span>defend</span></div></div>
              {workspace.content.portfolio.items.map((item) => <div className={styles.architectureRow} key={item.id || item.url}><strong>{item.decision.replaceAll("_", " ")}</strong><span title={item.recommendation}>{item.title || item.url}</span></div>)}
              {workspace.content.portfolio.collection_status === "not_collected" ? <p className={styles.emptyCopy}>Run pages refresh after GSC or technical audit evidence.</p> : null}
              <button className={styles.cardLink} type="button" onClick={() => onNavigatePages({ group: "now", source: "portfolio" })}>Open page actions <ArrowRight size={14} /></button>
            </DetailRow>
            <DetailRow icon={BarChart3} title="Statistical guidance" subtitle="Observed query mix, click drivers, ranking opportunity, and commercial context" summary={clickDecomposition ? <><span>{numberLabel(clickDecomposition.observed_click_change)} observed click change</span><span>{numberLabel(clickDecomposition.exposure_effect)} exposure effect</span><span>{numberLabel(clickDecomposition.ctr_effect)} CTR effect</span></> : <span>No data</span>}>
              {clickDecomposition ? <><div className={styles.diffNumbers}><div><strong>{numberLabel(clickDecomposition.observed_click_change)}</strong><span>observed click change</span></div><div><strong>{numberLabel(clickDecomposition.exposure_effect)}</strong><span>exposure effect</span></div><div><strong>{numberLabel(clickDecomposition.ctr_effect)}</strong><span>CTR effect</span></div></div><div className={styles.metricTable} role="table" aria-label="Portfolio statistical guidance"><div className={styles.tableHead} role="row"><span>Indicator</span><span>Value</span><span>Meaning</span></div><div className={styles.tableRow} role="row"><strong>Evidence strength</strong><span>{String(searchConfidence?.evidence_grade || searchConfidence?.status || "No data").replaceAll("_", " ")}</span><b>Daily coverage + volume</b></div><div className={styles.tableRow} role="row"><strong>Click change 95% interval</strong><span>{Array.isArray(confidenceClickChange?.ci95) ? confidenceClickChange.ci95.join(" → ") : "No data"}</span><b>{String(confidenceClickChange?.direction || "uncertain")}</b></div><div className={styles.tableRow} role="row"><strong>8-week trend</strong><span>{String(searchTrend?.direction || searchTrend?.status || "No data").replaceAll("_", " ")}</span><b>{searchTrend?.latest_anomaly === true ? "Latest anomaly" : "Robust weekly slope"}</b></div><div className={styles.tableRow} role="row"><strong>CTR opportunity</strong><span>{numberLabel(ctrBenchmark?.recoverable_clicks, 0)} clicks</span><b>FDR-controlled internal benchmark</b></div><div className={styles.tableRow} role="row"><strong>GSC ↔ GA4</strong><span>{String(crossSource?.status || "No data").replaceAll("_", " ")}</span><b>Tracking consistency</b></div><div className={styles.tableRow} role="row"><strong>Verified technical effects</strong><span>{numberLabel(technicalEffects?.significant_rules, 0)} / {numberLabel(technicalEffects?.tested_rules, 0)}</span><b>Associations after fixes</b></div><div className={styles.tableRow} role="row"><strong>Effective queries</strong><span>{numberLabel(currentQueries?.effective_queries)}</span><b>Observed diversity</b></div><div className={styles.tableRow} role="row"><strong>Query concentration</strong><span>{typeof currentQueries?.hhi === "number" ? `${numberLabel(currentQueries.hhi, 3)} → ${numberLabel(previousQueries?.hhi, 3)}` : "No data"}</span><b>HHI current → previous</b></div><div className={styles.tableRow} role="row"><strong>Top-5 query share</strong><span>{`${percentLabel(currentQueries?.top_5_impression_share)} → ${percentLabel(previousQueries?.top_5_impression_share)}`}</span><b>Impression concentration</b></div><div className={styles.tableRow} role="row"><strong>New / stable / lost</strong><span>{`${numberLabel(queryPortfolio?.new_queries, 0)} / ${numberLabel(queryPortfolio?.stable_queries, 0)} / ${numberLabel(queryPortfolio?.lost_queries, 0)}`}</span><b>Observed coverage</b></div><div className={styles.tableRow} role="row"><strong>Position 4–20</strong><span>{numberLabel(rankingOpportunity?.positions_4_20_impressions, 0)}</span><b>Opportunity impressions</b></div><div className={styles.tableRow} role="row"><strong>Revenue HHI</strong><span>{numberLabel(commercialValue?.revenue_hhi, 3)}</span><b>All-channel concentration</b></div></div><p className={styles.emptyCopy}>Intervals and trends use private daily history. CTR opportunity and verified technical effects use FDR control. All results remain observational; product value is not SEO revenue attribution.</p></> : <p className={styles.emptyCopy}>Run Pages refresh with comparable GSC query-page evidence.</p>}
              <button className={styles.cardLink} type="button" onClick={() => onNavigatePages({ group: "", source: "" })}>Inspect page statistics <ArrowRight size={14} /></button>
            </DetailRow>
          </DetailGroup>

          <DetailGroup index="3" title="Operations and technical context" subtitle="Delivery workflow, technical systems, and supporting evidence">
            <DetailRow icon={GitBranch} title="Workflow" subtitle={phaseLabel(workspace.phase)} summary={<><b>{nextLabel}</b><span>{workspace.phase_order.length} phases</span></>}>
              <button className={styles.nextAction} type="button" onClick={onNavigateWorkflow}><span><small>Next action</small><strong>{nextLabel}</strong><em>Open workflow</em></span><ArrowRight aria-hidden="true" size={20} /></button>
              <ol className={styles.phaseList}>{workspace.phase_order.map((phase) => { const current = phase === workspace.phase; const complete = workspace.phases[phase]?.status === "done"; return <li className={current ? styles.currentPhase : complete ? styles.completePhase : undefined} key={phase}><span /><strong>{phaseLabel(phase)}</strong><small>{current ? "Current" : complete ? "Complete" : "Upcoming"}</small></li>; })}</ol>
            </DetailRow>
            <DetailRow icon={Braces} title="Technology architecture" subtitle="Detected stack" summary={<span>{Object.keys(layers).length ? `${Object.keys(layers).length} layers detected` : "No data"}</span>}>
              {Object.entries(layers).slice(0, 5).map(([layer, technologies]) => <div className={styles.architectureRow} key={layer}><strong>{layerLabels[layer] || layer.replaceAll("_", " ")}</strong><span>{technologies.join(" · ")}</span></div>)}
              {Object.keys(layers).length === 0 ? <p className={styles.emptyCopy}>Run technology evidence to populate architecture layers.</p> : null}
            </DetailRow>
            <DetailRow icon={BarChart3} title="Diff evidence" subtitle="Latest comparable snapshots" summary={<><span>{diff.changes ?? "N/A"} changes</span><b className={styles.statusDanger}>{diff.regressions ?? "N/A"} regressions</b><b className={styles.statusSuccess}>{diff.improvements ?? "N/A"} improvements</b></>}>
              <div className={styles.diffNumbers}><div><strong>{diff.changes ?? "N/A"}</strong><span>changes</span></div><div className={styles.statusDanger}><strong>{diff.regressions ?? "N/A"}</strong><span>regressions</span></div><div className={styles.statusSuccess}><strong>{diff.improvements ?? "N/A"}</strong><span>improvements</span></div></div>
            </DetailRow>
            <DetailRow icon={FileText} title="Recent workspace files" subtitle="Latest local edits" summary={<span>{workspace.recent_files.length} files</span>}>
              <div className={styles.fileTable}>{workspace.recent_files.slice(0, 5).map((file) => { const updated = updatedPaths[file.path]; return <button className={updated ? styles.updatedFile : styles.fileRow} key={file.path} type="button" onClick={() => onOpenFile(file.path)}><FileText aria-hidden="true" size={17} strokeWidth={1.5} /><span><strong>{file.name}</strong><small>{updated ? "Agent updated" : file.path}</small></span><time>{updated ? "now" : fileTime(file.modified_at)}</time></button>; })}</div>
            </DetailRow>
          </DetailGroup>
        </div>
      </section>
    </div>
  );
}
