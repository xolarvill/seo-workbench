import { ArrowRight, RefreshCw } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";

import { fetchStatistics } from "../../api/client";
import { HelpTooltip } from "../../components/HelpTooltip";
import { ProgressiveLoadingStatus, ProgressiveSkeletonCard } from "../../components/ProgressiveLoading";
import { StatusPill, statusTone, type StatusTone } from "../../components/StatusPill";
import type { StatisticsResponse } from "../../api/types";
import styles from "./StatisticsPage.module.css";

type Props = {
  projectId: string;
  refreshKey: number;
  refreshing: boolean;
  onRefresh: () => void;
  onNavigatePages: (filters: { group: string; source: string }) => void;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : null;
}

function asRecords(value: unknown): Array<Record<string, unknown>> {
  return Array.isArray(value) ? value.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object") : [];
}

function stringify(value: unknown): string {
  if (value === null || value === undefined) return "";
  return String(value);
}

function numberLabel(value: unknown, digits = 1) {
  return typeof value === "number" ? value.toLocaleString(undefined, { maximumFractionDigits: digits }) : "No data";
}

function percentLabel(value: unknown, digits = 1) {
  return typeof value === "number" ? `${(value * 100).toFixed(digits)}%` : "No data";
}

function whenLabel(value: unknown) {
  if (!value) return "No snapshot";
  try {
    return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(String(value)));
  } catch {
    return String(value);
  }
}

const transitionLabels: Record<string, string> = {
  top_3: "Top 3",
  positions_4_10: "4–10",
  positions_11_20: "11–20",
  positions_20_plus: "20+",
};

function transitionLabel(value: string) {
  return transitionLabels[value] || value.replaceAll("_", " ").replace("positions ", "p");
}

function deltaTone(value: unknown): StatusTone {
  if (typeof value !== "number" || value === 0) return "neutral";
  return value > 0 ? "success" : "danger";
}

function Card({ title, subtitle, help, children }: { title: string; subtitle?: ReactNode; help?: ReactNode; children: ReactNode }) {
  return <section className={styles.card}><header className={styles.cardHeader}><h2>{title}{help ? <HelpTooltip label={title} align="center">{help}</HelpTooltip> : null}</h2>{subtitle ? <span>{subtitle}</span> : null}</header><div className={styles.cardBody}>{children}</div></section>;
}

function TrendBars({ weekly, tone }: { weekly: unknown; tone?: StatusTone }) {
  const values = (Array.isArray(weekly) ? weekly.filter((item): item is number => typeof item === "number") : []).slice(-8);
  if (values.length === 0) return <p className={styles.empty}>No weekly click series.</p>;
  const max = Math.max(...values, 1);
  return <div className={styles.barChart} aria-label="8-week click trend">
    {values.map((value, index) => <div className={styles.barColumn} key={index}><span className={styles.bar} data-tone={tone || "info"} style={{ height: `${Math.max(5, Math.round((value / max) * 100))}%` }} title={`${numberLabel(value, 0)} clicks`} /><small>{numberLabel(value, 0)}</small></div>)}
  </div>;
}

function TransitionsTable({ transitions }: { transitions: unknown }) {
  const source = asRecord(transitions);
  if (!source) return <p className={styles.empty}>No ranking transition evidence.</p>;
  const rows = Object.entries(source).map(([key, value]) => {
    const [from, to] = key.split("->");
    const cell = asRecord(value);
    return { from: stringify(from), to: stringify(to), count: cell?.cell_count, impressions: cell?.current_impressions };
  }).sort((a, b) => ((b.impressions as number) || 0) - ((a.impressions as number) || 0)).slice(0, 10);
  return <table className={styles.table} aria-label="Ranking position transitions">
    <thead><tr><th>Direction</th><th>Pages</th><th>Impressions</th></tr></thead>
    <tbody>{rows.map((row, index) => <tr key={index}><th>{transitionLabel(row.from)} → {transitionLabel(row.to)}</th><td>{numberLabel(row.count, 0)}</td><td>{numberLabel(row.impressions, 0)}</td></tr>)}</tbody>
  </table>;
}

type DetailRowEntry = [string, unknown, ReactNode?, StatusTone?];

function DetailRows({ rows }: { rows: Array<DetailRowEntry> }) {
  return <div className={styles.detailRows}>{rows.map(([label, value, help, tone]) => <div key={label}><span>{label}{help ? <HelpTooltip label={label}>{help}</HelpTooltip> : null}</span><strong>{tone ? <StatusPill value={value} context="evidence" tone={tone} /> : stringify(value)}</strong></div>)}</div>;
}

export function StatisticsPage({ projectId, refreshKey, refreshing, onRefresh, onNavigatePages }: Props) {
  const [data, setData] = useState<StatisticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchStatistics(projectId)
      .then((value) => { if (!cancelled) setData(value); })
      .catch((reason: Error) => { if (!cancelled) setError(reason.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [projectId, refreshKey]);

  const portfolio = asRecord(data?.portfolio);
  const stats = asRecord(portfolio?.statistics);
  const decomposition = asRecord(stats?.click_change_decomposition);
  const queryPortfolio = asRecord(stats?.query_portfolio);
  const currentQueries = asRecord(queryPortfolio?.current);
  const previousQueries = asRecord(queryPortfolio?.previous);
  const ranking = asRecord(stats?.ranking_opportunity);
  const confidence = asRecord(stats?.search_change_confidence);
  const clickChange = asRecord(confidence?.click_change);
  const trend = asRecord(stats?.search_trend);
  const ctrBenchmark = asRecord(stats?.ctr_benchmark);
  const multipleTesting = asRecord(ctrBenchmark?.multiple_testing);
  const commercial = asRecord(stats?.commercial_value);
  const technicalEffects = asRecord(stats?.technical_issue_effects);
  const comparability = asRecord(portfolio?.comparability);
  const sourceStatus = asRecord(portfolio?.source_status);
  const coverage = asRecord(data?.coverage);
  const coverageSources = asRecord(coverage?.sources);
  const regimes = asRecord(data?.regimes);
  const regimeItems = asRecords(regimes?.regimes);
  const business = asRecord(data?.business);
  const businessWindows = asRecord(business?.windows);
  const organicCommerce = asRecord(businessWindows?.current);
  const commerceTracking = asRecord(organicCommerce?.commerce_tracking);

  return (
    <section className={styles.page} aria-labelledby="statistics-heading" aria-busy={loading}>
      <header className={styles.header}>
        <div><span>Statistical evidence</span><h1 id="statistics-heading">Statistics</h1><p>Comparable GSC, GA4 and Shopify windows with private daily history behind every interval and trend.</p></div>
        <div className={styles.headerActions}>
          <button className={styles.refreshButton} type="button" disabled={refreshing} onClick={onRefresh}><RefreshCw size={16} className={refreshing ? styles.spinning : undefined} />{refreshing ? "Collecting" : "Run statistics collection"}</button>
          <HelpTooltip label="Run statistics collection" align="right"><><strong>Runs the full evidence pipeline.</strong><ul><li>GSC → GA4 → Shopify → business → history → portfolio.</li><li>Any gate failure (e.g. missing finalized GSC windows) fails the whole run — read the job output for the failing step.</li></ul></></HelpTooltip>
        </div>
      </header>

      <ProgressiveLoadingStatus loading={loading && !error} complete={Boolean(data && !loading)} label="statistical evidence" />
      {error ? <p className={styles.error} role="alert">{error}</p> : null}
      {!data && loading ? <div className={styles.loadingGrid} aria-hidden="true">{Array.from({ length: 6 }, (_, index) => <ProgressiveSkeletonCard key={index} />)}</div> : !data ? null : (
        <>
          <div className={styles.statusGrid}>
            <Card title="Collection status" subtitle={<StatusPill value={portfolio?.collection_status} context="evidence" />}>
              <div className={styles.diffNumbers}>
                <div><strong>{numberLabel(portfolio?.count, 0)}</strong><span>observed pages</span></div>
                <div><strong><StatusPill value={comparability?.comparable === true ? "comparable" : comparability?.comparable === false ? "incomparable" : "No data"} context="evidence" /></strong><span>GSC windows</span></div>
              </div>
              <p className={styles.meta}>{stringify(portfolio?.schema_version)} · updated {whenLabel(portfolio?.generated_at)}</p>
              {Array.isArray(comparability?.issues) && comparability.issues.length ? <ul className={styles.issueList}>{(comparability.issues as unknown[]).map((issue, index) => <li key={index}>{stringify(issue)}</li>)}</ul> : null}
              {Object.entries(sourceStatus || {}).map(([name, value]) => { const item = asRecord(value); return <div className={styles.coverageRow} key={name}><span>{name}</span><StatusPill value={item?.status || value} context="evidence" />{item?.reason ? <small>{stringify(item.reason)}</small> : null}</div>; })}
            </Card>

            <Card title="Daily history coverage" subtitle={<StatusPill value={coverage?.status} context="evidence" />} help={<><strong>Private daily history powers intervals, trends and GSC ↔ GA4 checks.</strong><ul><li>Kept for 120 days.</li><li>Missing coverage widens or removes intervals — never filled in as zeros.</li></ul></>}>
              {Object.keys(coverageSources || {}).length === 0 ? <p className={styles.empty}>No private daily history yet — run statistics collection regularly.</p> : Object.entries(coverageSources || {}).map(([name, item]) => { const source = asRecord(item); return <div className={styles.coverageRow} key={name}><span>{name}</span><strong>{numberLabel(source?.count, 0)} days</strong><small>{stringify(source?.first)} → {stringify(source?.last)}</small></div>; })}
            </Card>

            <Card title="Measurement regimes" subtitle="read-only" help={<><strong>Comparability guard.</strong><ul><li>Records changes that alter what a metric means: property, tracking, consent, currency, template scope.</li><li>A break inside a comparison window makes it incomparable — the gate refuses to compare across it.</li><li>Read-only here; record changes from the CLI.</li></ul></>}>
              {regimes?.error ? <p className={styles.error}>{stringify(regimes.error)}</p> : null}
              {regimeItems.length === 0 ? <p className={styles.empty}>No measurement regimes recorded. Add regimes from the CLI when GSC, GA4, Shopify or consent definitions change.</p> : regimeItems.map((regime) => <div className={styles.coverageRow} key={stringify(regime.id || regime.effective_at)}><span>{stringify(regime.source)}</span><strong>{stringify(regime.effective_at)}</strong><small>{stringify(regime.description)}</small></div>)}
            </Card>

            <Card title="Organic commerce funnel" subtitle={<StatusPill value={commerceTracking?.status || business?.status} context="evidence" />} help={<><strong>GA4 Organic Search landing-page-associated totals.</strong><ul><li>Views, carts, checkouts and purchases are aggregates for sessions that began on each landing page.</li><li>Tracking coverage checks standard ecommerce events across all traffic; funnel totals remain Organic Search.</li><li>This is not a user path or causal attribution. Shopify revenue remains separate all-channel context.</li></ul></>}>
              {business?.status !== "ok" ? <p className={styles.empty}>No comparable GA4 and Shopify business evidence yet.</p> : <>
                <div className={styles.diffNumbers}>
                  <div><strong>{numberLabel(organicCommerce?.organic_product_views, 0)}</strong><span>product views</span></div>
                  <div><strong>{numberLabel(organicCommerce?.organic_add_to_carts, 0)}</strong><span>add to carts</span></div>
                  <div><strong>{numberLabel(organicCommerce?.organic_checkouts, 0)}</strong><span>checkouts</span></div>
                  <div><strong>{numberLabel(organicCommerce?.organic_purchases, 0)}</strong><span>purchases</span></div>
                </div>
                <p className={styles.meta}>{stringify(business?.currency)} {numberLabel(organicCommerce?.organic_revenue, 2)} organic purchase revenue · {stringify(organicCommerce?.start_date)} → {stringify(organicCommerce?.end_date)}</p>
                {Array.isArray(commerceTracking?.missing_events) && commerceTracking.missing_events.length ? <p className={styles.meta}>Not observed: {(commerceTracking.missing_events as string[]).join(", ")}</p> : null}
              </>}
            </Card>
          </div>

          {stats ? (
            <div className={styles.blocksGrid}>
              <Card title="Click change decomposition" subtitle="clicks = impressions × CTR" help={<><strong>Splits click change into two effects.</strong><ul><li>Exposure: impressions and position mix.</li><li>CTR: conversion of exposure into clicks.</li><li>Diagnostic only — describes what moved, not why.</li></ul></>}>
                <div className={styles.diffNumbers}>
                  <div><strong className={styles.deltaValue} data-tone={deltaTone(decomposition?.observed_click_change)}>{numberLabel(decomposition?.observed_click_change, 0)}</strong><span>observed change</span></div>
                  <div><strong className={styles.deltaValue} data-tone={deltaTone(decomposition?.exposure_effect)}>{numberLabel(decomposition?.exposure_effect, 0)}</strong><span>exposure effect</span></div>
                  <div><strong className={styles.deltaValue} data-tone={deltaTone(decomposition?.ctr_effect)}>{numberLabel(decomposition?.ctr_effect, 0)}</strong><span>CTR effect</span></div>
                </div>
                <DetailRows rows={[
                  ["Evidence strength", stringify(confidence?.evidence_grade || confidence?.status || "No data").replaceAll("_", " "), undefined, statusTone(confidence?.evidence_grade || confidence?.status, "evidence")],
                  ["95% interval", Array.isArray(clickChange?.ci95) ? clickChange.ci95.join(" → ") : "No data", <><strong>Descriptive uncertainty from private daily history.</strong><ul><li>Not causal attribution.</li><li>Wide interval = low information; short coverage makes intervals wider, not more precise.</li></ul></>],
                  ["Probability of increase", typeof clickChange?.probability_increase === "number" ? `${(clickChange.probability_increase * 100).toFixed(1)}%` : "No data", <><strong>Share of the bootstrap distribution above zero.</strong><ul><li>A descriptive read of uncertainty, not a business probability.</li></ul></>],
                  ["Direction", stringify(clickChange?.direction || "uncertain"), undefined, statusTone(clickChange?.direction, "evidence")],
                ]} />
              </Card>

              <Card title="8-week click trend" subtitle="private daily history" help={<><strong>Robust weekly slope (Theil–Sen) ignores single-week outliers.</strong><ul><li>A flagged anomaly means one point deviates, not that the trend reversed.</li><li>Needs enough weekly coverage to be meaningful.</li></ul></>}>
                <TrendBars weekly={trend?.weekly_clicks} tone={typeof trend?.click_slope_per_week === "number" ? deltaTone(trend.click_slope_per_week) : statusTone(trend?.direction || trend?.status, "evidence")} />
                <DetailRows rows={[
                  ["Direction", stringify(trend?.direction || trend?.status || "No data").replaceAll("_", " "), undefined, statusTone(trend?.direction || trend?.status, "evidence")],
                  ["Slope per week", numberLabel(trend?.click_slope_per_week), undefined, deltaTone(trend?.click_slope_per_week)],
                  ["Latest anomaly", trend?.latest_anomaly === true ? "Yes" : trend?.status === "ok" ? "No" : "No data", undefined, trend?.latest_anomaly === true ? "warning" : trend?.status === "ok" ? "success" : "neutral"],
                ]} />
              </Card>

              <Card title="Query portfolio" subtitle="observed queries only" help={<><strong>Covers observed GSC query-page rows only.</strong><ul><li>Hidden queries are not represented.</li><li>HHI measures concentration — higher means fewer queries drive impressions.</li></ul></>}>
                <DetailRows rows={[
                  ["Effective queries", numberLabel(currentQueries?.effective_queries)],
                  ["HHI (current → previous)", typeof currentQueries?.hhi === "number" ? `${numberLabel(currentQueries.hhi, 3)} → ${numberLabel(previousQueries?.hhi, 3)}` : "No data"],
                  ["Top-5 share (current → previous)", `${percentLabel(currentQueries?.top_5_impression_share)} → ${percentLabel(previousQueries?.top_5_impression_share)}`],
                  ["Observed queries", numberLabel(currentQueries?.observed_query_count, 0)],
                  ["New / stable / lost", `${numberLabel(queryPortfolio?.new_queries, 0)} / ${numberLabel(queryPortfolio?.stable_queries, 0)} / ${numberLabel(queryPortfolio?.lost_queries, 0)}`],
                  ["Position 4–20 impressions", numberLabel(ranking?.positions_4_20_impressions, 0)],
                ]} />
              </Card>

              <Card title="Ranking transitions" subtitle="position bucket movement">
                <TransitionsTable transitions={ranking?.transitions} />
              </Card>

              <Card title="CTR benchmark" subtitle="internal, FDR-controlled" help={<><strong>Internal, within-property benchmark.</strong><ul><li>Expected CTR is a Bayesian leave-page-out estimate, shrunken toward the global CTR per position band.</li><li>Recoverable clicks count only pages that survive Benjamini–Hochberg FDR (q ≤ 0.05).</li><li>Not Google data and not a forecast.</li></ul></>}>
                <div className={styles.diffNumbers}>
                  <div><strong>{percentLabel(ctrBenchmark?.global_ctr, 3)}</strong><span>global CTR</span></div>
                  <div><strong>{numberLabel(ctrBenchmark?.recoverable_clicks, 0)}</strong><span>recoverable clicks</span></div>
                  <div><strong>{numberLabel(ctrBenchmark?.recoverable_clicks_unadjusted, 0)}</strong><span>recoverable unadjusted</span></div>
                </div>
                <p className={styles.meta}>{stringify(multipleTesting?.method || "Benjamini–Hochberg false-discovery control")}</p>
              </Card>

              <Card title="Commercial value" subtitle={stringify(commercial?.currency) || "all-channel context"}>
                <DetailRows rows={[
                  ["Revenue HHI", numberLabel(commercial?.revenue_hhi, 3)],
                  ["Total revenue", `${stringify(commercial?.currency)} ${numberLabel(commercial?.total_revenue, 0)}`.trim()],
                  ["Attribution", stringify(commercial?.attribution || "No data").replaceAll("_", " ")],
                  ["Observed pages", numberLabel(commercial?.observed_pages, 0)],
                ]} />
              </Card>

              <Card title="Verified technical effects" subtitle="association, not causal" help={<><strong>Associations, never causal impact.</strong><ul><li>Verified fixes with 14-day pre/post windows, controls, sign-flip tests and FDR.</li><li>Zero significant rules can mean insufficient evidence, not proof of no effect.</li></ul></>}>
                <div className={styles.diffNumbers}>
                  <div><strong>{numberLabel(technicalEffects?.significant_rules, 0)} / {numberLabel(technicalEffects?.tested_rules, 0)}</strong><span>significant / tested</span></div>
                  <div><strong><StatusPill value={technicalEffects?.status} context="evidence" /></strong><span>status</span></div>
                </div>
                <p className={styles.meta}>{stringify(technicalEffects?.interpretation)}</p>
                {Array.isArray(technicalEffects?.rules) && technicalEffects.rules.length ? <div className={styles.ruleChips}>{(technicalEffects.rules as string[]).slice(0, 12).map((rule) => <span key={rule}>{rule}</span>)}</div> : null}
              </Card>
            </div>
          ) : <p className={styles.empty}>No statistical projection yet — run statistics collection after comparable GSC evidence.</p>}

          <footer className={styles.footer}>
            <p>Intervals and trends use private daily history. CTR opportunity and verified technical effects use FDR control. All results are observational; product value is not SEO revenue attribution.</p>
            <button className={styles.pageLink} type="button" onClick={() => onNavigatePages({ group: "", source: "" })}>Inspect page statistics <ArrowRight size={14} /></button>
          </footer>
        </>
      )}
    </section>
  );
}
