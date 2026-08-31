import { useEffect, useMemo, useState } from "react";
import { ArrowDown, ArrowUp, Filter, RefreshCw, Search } from "lucide-react";

import { createSeoChange, evaluateSeoChange, fetchPageDetail, fetchPageView, updateContentStatus, updateSeoChangeStatus, updateTechnicalIssueStatus, type PageViewParams } from "../../api/client";
import { HelpTooltip } from "../../components/HelpTooltip";
import { Drawer } from "../../components/Drawer";
import { ProgressiveLoadingStatus, ProgressiveSkeletonRows, type SkeletonColumn } from "../../components/ProgressiveLoading";
import { StatusPill } from "../../components/StatusPill";
import { ColumnPicker, Pagination, SearchField, pageLabel, useStoredColumns } from "../../components/WorkbenchControls";
import type { PageDataset, PageDetailResponse, PageViewColumn, PageViewRow, SeoChangeCreate } from "../../api/types";
import { useDebouncedValue, useViewData } from "../../hooks/useWorkbenchData";
import { appHref } from "../../routes";
import styles from "./PagesWorkbenchPage.module.css";

type Props = {
  projectId: string;
  refreshKey: number;
  refreshing: boolean;
  initialGroup?: string;
  initialSource?: string;
  initialQuery?: string;
  onRefresh: () => Promise<void>;
  onUpdated: () => void;
};

const contentStatuses = ["planned", "ready_to_write", "drafting", "review", "revision_requested", "approved", "scheduled", "submitted_for_indexing", "indexed", "indexing_issue"];
const changeTypes: SeoChangeCreate["change_type"][] = ["content", "internal_links", "metadata", "performance", "redirect", "schema", "technical", "other"];

const datasets: Array<{ id: PageDataset; label: string }> = [
  { id: "actions", label: "Actions" },
  { id: "pages", label: "All pages" },
  { id: "query_conflicts", label: "Query conflicts" },
];

const defaultSort: Record<PageDataset, string> = {
  actions: "urgency",
  pages: "impressions",
  query_conflicts: "total_impressions",
};

const skeletonColumns: Record<PageDataset, SkeletonColumn[]> = {
  actions: [{ id: "page", label: "Page", width: "44%" }, { id: "stage", label: "Stage", width: "18%" }, { id: "source", label: "Source", width: "18%" }, { id: "status", label: "Status", width: "24%" }],
  pages: [{ id: "url", label: "URL", width: "48%" }, { id: "type", label: "Type", width: "18%" }, { id: "clicks", label: "Clicks", width: "18%" }, { id: "position", label: "Position", width: "24%" }],
  query_conflicts: [{ id: "query", label: "Query", width: "44%" }, { id: "owners", label: "Owners", width: "18%" }, { id: "impressions", label: "Impressions", width: "22%" }, { id: "share", label: "Primary share", width: "24%" }],
};

const stageMeta = {
  now: { label: "First Priority: NOW", description: "Needs action" },
  review: { label: "Second Priority: REVIEW", description: "Validate outcomes" },
  watch: { label: "Third Priority: WATCH", description: "Keep stable" },
} as const;

const NOT_OBSERVED_HELP = "Not observed means this evidence source did not provide a value. It does not prove that the page is missing or not indexed.";
const sourceHelp: Record<string, string> = {
  portfolio: "Combines the latest GSC pages, technical audit inventory, and live content URLs into one local page view. It is not a live crawl.",
  gsc: "Read-only Google Search Console evidence, including page/query performance and indexing samples.",
  technical: "The latest deterministic crawl and SEO issue inventory. Partial means the audit did not complete cleanly.",
  ga4: "Read-only Google Analytics 4 landing-page sessions, engaged sessions, and key events split by acquisition channel.",
  business: "Merged business signals: GA4 organic/engaged sessions and key events plus all-channel Shopify product revenue/orders, keyed by URL.",
  statistics_history: "Private date-by-page history used for uncertainty, trend, engagement, and GSC-to-GA4 consistency checks.",
};
const columnHelp: Record<string, { label: string; text: string }> = {
  status: { label: "Status", text: "Open means the issue or action is identified and still needs a decision, fix, or verification. It is not the page's HTTP status." },
  url: { label: "URL", text: "The affected page address. Not observed means the available evidence did not provide a URL; it does not prove the page is missing or not indexed." },
  opportunity_impressions: { label: "Position 4–20", text: "Observed GSC query-page impressions whose aggregate average position is 4–20. This is an opportunity signal, not a click forecast." },
  commercial_quadrant: { label: "Value × opportunity", text: "Combines all-channel Shopify product value with observed search opportunity. It is prioritization context, not SEO revenue attribution." },
  recoverable_clicks: { label: "CTR opportunity", text: "Estimated clicks below the site's leave-page-out CTR benchmark after Benjamini–Hochberg false-discovery control. It is an internal diagnostic, not a forecast." },
  evidence_strength: { label: "Evidence", text: "Strength of the daily comparison based on complete window coverage and observed click/impression volume." },
  cross_source_status: { label: "GSC ↔ GA4", text: "Robust shift check for the GA4 organic-sessions-to-GSC-clicks relationship. A warning can indicate tracking or consent changes, not an SEO result." },
  primary_owner_share: { label: "Primary share", text: "The leading URL's share of observed impressions for this exact query." },
};

function stringify(value: unknown, max = 120): string {
  if (value === null || value === undefined || value === "") return "Not observed";
  if (typeof value === "object") {
    if (Array.isArray(value)) return value.map((item) => stringify(item, max)).join(", ") || "None";
    const record = value as Record<string, unknown>;
    return stringify(record.status ?? record.value ?? JSON.stringify(record), max);
  }
  const result = String(value);
  return result.length > max ? `${result.slice(0, max - 1)}…` : result;
}

function cellValue(row: PageViewRow, column: PageViewColumn) {
  const value = row[column.id];
  if (value === null || value === undefined || value === "") return <span className={styles.notObserved} title={NOT_OBSERVED_HELP}>Not observed</span>;
  if (column.id === "urgency") return <StatusPill value={value} context="urgency" />;
  if (column.id === "status" || column.id === "decision") return <StatusPill value={value} context="status" />;
  if (column.id === "source_status") return <StatusPill value={value} context="evidence" />;
  if (column.id === "ctr" && typeof value === "number") return `${(value * 100).toFixed(2)}%`;
  if (column.id === "primary_owner_share" && typeof value === "number") return `${(value * 100).toFixed(1)}%`;
  if (column.id === "position" && typeof value === "number") return value.toFixed(1);
  if (column.id === "query") return <a href={appHref("keywords", { q: String(value) })} onClick={(event) => event.stopPropagation()}>{String(value)}</a>;
  if (["commercial_quadrant", "click_driver", "cross_source_status"].includes(column.id)) return String(value).replaceAll("_", " ");
  return stringify(value);
}

function DetailList({ items }: { items: Array<[string, unknown]> }) {
  return <dl className={styles.detailList}>{items.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{stringify(value, 280)}</dd></div>)}</dl>;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : null;
}

function asRecords(value: unknown): Array<Record<string, unknown>> {
  return Array.isArray(value) ? value.map(asRecord).filter((item): item is Record<string, unknown> => Boolean(item)) : [];
}

function metricValue(metric: string, value: unknown): string {
  if (typeof value !== "number") return "Not observed";
  if (metric === "ctr") return `${(value * 100).toFixed(2)}%`;
  return value.toLocaleString(undefined, { maximumFractionDigits: metric === "position" ? 1 : 2 });
}

function metricDelta(metric: string, value: unknown): string {
  const delta = asRecord(value);
  const absolute = delta?.absolute;
  if (typeof absolute !== "number") return "Not comparable";
  const sign = absolute > 0 ? "+" : "";
  const absoluteLabel = metric === "ctr" ? `${sign}${(absolute * 100).toFixed(2)} pp` : `${sign}${metricValue(metric, absolute)}`;
  return typeof delta?.relative === "number" ? `${absoluteLabel} (${delta.relative > 0 ? "+" : ""}${(delta.relative * 100).toFixed(1)}%)` : absoluteLabel;
}

function SearchPerformance({ page }: { page: PageViewRow }) {
  const metrics = asRecord(page.metrics);
  const previous = asRecord(metrics?.previous);
  const current = asRecord(metrics?.current);
  const delta = asRecord(metrics?.delta);
  const currency = String(page.business_currency || "currency not reported");
  const rows = [["clicks", "Clicks"], ["impressions", "Impressions"], ["ctr", "CTR"], ["position", "Position"], ["organic_sessions", "Organic sessions"], ["engaged_sessions", "Engaged sessions"], ["key_events", "GA4 key events"], ["conversions", "Conversions"], ["revenue", `Product revenue (${currency})`], ["orders", "Product orders (all channel)"]].filter(([metric]) => previous?.[metric] !== undefined || current?.[metric] !== undefined);
  return <table className={styles.evidenceTable} aria-label="Search and business performance comparison"><thead><tr><th>Metric</th><th>Previous</th><th>Current</th><th>Change</th></tr></thead><tbody>{rows.map(([metric, label]) => <tr key={metric}><th>{label}</th><td>{metricValue(metric, previous?.[metric])}</td><td>{metricValue(metric, current?.[metric])}</td><td>{metricDelta(metric, delta?.[metric])}</td></tr>)}</tbody></table>;
}

function StatisticalEvidence({ page }: { page: PageViewRow }) {
  const statistics = asRecord(page.statistics);
  const decomposition = asRecord(statistics?.click_change_decomposition);
  const queryPortfolio = asRecord(statistics?.query_portfolio);
  const currentQueries = asRecord(queryPortfolio?.current);
  const ranking = asRecord(statistics?.ranking_opportunity);
  const rankShares = asRecord(ranking?.current_impression_share);
  const commercial = asRecord(statistics?.commercial_value);
  const confidence = asRecord(statistics?.search_change_confidence);
  const clickChange = asRecord(confidence?.click_change);
  const trend = asRecord(statistics?.search_trend);
  const ctrBenchmark = asRecord(statistics?.ctr_benchmark);
  const engagement = asRecord(statistics?.organic_engagement);
  const currentEngagement = asRecord(engagement?.current);
  const currentEngagementRate = asRecord(currentEngagement?.engagement_rate);
  const crossSource = asRecord(statistics?.cross_source_consistency);
  const technicalEffects = asRecords(statistics?.technical_issue_effects);
  const drivers = asRecords(decomposition?.top_drivers);
  if (!statistics || (!decomposition && !queryPortfolio && !ranking && !commercial)) return <p className={styles.sectionEmpty}>No statistical projection is available for this page.</p>;
  return <div className={styles.queryEvidence}>
    <DetailList items={[
      ["Observed click change", decomposition?.observed_click_change],
      ["Exposure effect", decomposition?.exposure_effect],
      ["CTR effect", decomposition?.ctr_effect],
      ["Observed queries", currentQueries?.observed_query_count],
      ["Effective queries", currentQueries?.effective_queries],
      ["New / stable / lost", queryPortfolio ? `${stringify(queryPortfolio.new_queries)} / ${stringify(queryPortfolio.stable_queries)} / ${stringify(queryPortfolio.lost_queries)}` : null],
      ["Position 4–20 impressions", ranking?.positions_4_20_impressions],
      ["Top 3 impression share", typeof rankShares?.top_3 === "number" ? `${(rankShares.top_3 * 100).toFixed(1)}%` : null],
      ["Commercial quadrant", commercial?.quadrant ? String(commercial.quadrant).replaceAll("_", " ") : null],
      ["Product revenue share", typeof commercial?.revenue_share === "number" ? `${(commercial.revenue_share * 100).toFixed(1)}%` : null],
      ["Evidence strength", confidence?.evidence_grade],
      ["Click change 95% interval", Array.isArray(clickChange?.ci95) ? clickChange.ci95.join(" → ") : null],
      ["Probability of increase", typeof clickChange?.probability_increase === "number" ? `${(clickChange.probability_increase * 100).toFixed(1)}%` : null],
      ["8-week click trend", trend?.direction],
      ["Latest robust anomaly", trend?.latest_anomaly === true ? "Yes" : trend?.status === "ok" ? "No" : null],
      ["CTR benchmark", ctrBenchmark?.classification],
      ["CTR opportunity clicks", ctrBenchmark?.recoverable_clicks],
      ["CTR benchmark q-value", ctrBenchmark?.q_value],
      ["Organic engagement rate", typeof currentEngagementRate?.estimate === "number" ? `${(currentEngagementRate.estimate * 100).toFixed(1)}%` : null],
      ["GSC ↔ GA4 consistency", crossSource?.status],
      ["Verified technical effects", technicalEffects.length ? technicalEffects.map((effect) => `${stringify(effect.rule_id)}: ${stringify(effect.classification)}`).join(" · ") : null],
    ]} />
    {drivers.length ? <table className={styles.evidenceTable} aria-label="Observed click change drivers"><thead><tr><th>Query</th><th>Click change</th><th>Exposure</th><th>CTR</th></tr></thead><tbody>{drivers.slice(0, 5).map((driver) => <tr key={`${String(driver.query)}:${String(driver.url)}`}><th>{stringify(driver.query, 70)}</th><td>{metricValue("clicks", driver.click_change)}</td><td>{metricValue("clicks", driver.exposure_effect)}</td><td>{metricValue("clicks", driver.ctr_effect)}</td></tr>)}</tbody></table> : null}
    <p className={styles.sectionEmpty}>Query statistics cover observed GSC query-page rows only. Product value is all-channel context, not SEO attribution.</p>
  </div>;
}

function urlLabel(value: unknown): string {
  try {
    const url = new URL(String(value));
    return `${url.hostname}${url.pathname}`;
  } catch {
    return stringify(value);
  }
}

function QueryOwnership({ page, row }: { page: PageViewRow; row: PageViewRow }) {
  const queries = asRecords(page.top_queries);
  const conflicts = asRecords(page.multiple_page_queries);
  const directOwners = asRecords(row.owners);
  return <div className={styles.queryEvidence}>
    {queries.length ? <table className={styles.evidenceTable} aria-label="Top query performance"><thead><tr><th>Query</th><th>Clicks</th><th>Impressions</th><th>Position</th></tr></thead><tbody>{queries.map((query) => <tr key={String(query.query)}><th><a href={appHref("keywords", { q: String(query.query) })}>{stringify(query.query, 80)}</a></th><td>{metricValue("clicks", query.clicks)}</td><td>{metricValue("impressions", query.impressions)}</td><td>{metricValue("position", query.position)}</td></tr>)}</tbody></table> : <p className={styles.sectionEmpty}>No query data observed for this page.</p>}
    {conflicts.map((conflict) => { const ownership = asRecord(conflict.ownership); return <article className={styles.conflict} key={String(conflict.query)}><strong><a href={appHref("keywords", { q: String(conflict.query) })}>{stringify(conflict.query, 100)}</a></strong><span>{stringify(conflict.owner_count)} pages · {metricValue("impressions", conflict.total_impressions)} impressions{typeof ownership?.primary_owner_share === "number" ? ` · primary ${(ownership.primary_owner_share * 100).toFixed(1)}% · HHI ${metricValue("hhi", ownership.hhi)}` : ""}</span><ul>{asRecords(conflict.owners).map((owner) => <li key={String(owner.url)}><a href={String(owner.url)} target="_blank" rel="noreferrer">{urlLabel(owner.url)}</a><b>{metricValue("impressions", owner.impressions)}</b></li>)}</ul></article>; })}
    {!conflicts.length && directOwners.length ? <article className={styles.conflict}><strong>{stringify(row.query, 100)}</strong><span>{directOwners.length} competing pages · {metricValue("impressions", row.total_impressions)} impressions{typeof row.primary_owner_share === "number" ? ` · primary ${(row.primary_owner_share * 100).toFixed(1)}%` : ""}</span><ul>{directOwners.map((owner) => <li key={String(owner.url)}><a href={String(owner.url)} target="_blank" rel="noreferrer">{urlLabel(owner.url)}</a><b>{metricValue("impressions", owner.impressions)}</b></li>)}</ul></article> : null}
    {!conflicts.length && !directOwners.length ? <p className={styles.sectionEmpty}>No multi-page query conflict observed.</p> : null}
  </div>;
}

function TechnicalEvidence({ page }: { page: PageViewRow }) {
  const technical = asRecord(page.technical);
  const indexability = asRecord(technical?.indexability);
  const sources = asRecord(page.sources);
  const issueCount = technical?.issue_count;
  return <>
    {sources ? <div className={styles.sourceChips}>{Object.entries(sources).map(([name, observed]) => <span key={name} data-observed={Boolean(observed)}>{name.replaceAll("_", " ")}: {observed ? "observed" : "not observed"}</span>)}</div> : null}
    <DetailList items={[
      ["Page type", page.page_type],
      ["HTTP status", technical?.status_code],
      ["Indexability", indexability?.status ?? (indexability?.indexable === true ? "indexable" : indexability?.indexable === false ? "not indexable" : null)],
      ["Canonical", technical?.canonical],
      ["H1", technical?.h1],
      ["Open issues", typeof issueCount === "number" ? `${issueCount} open issue${issueCount === 1 ? "" : "s"}` : null],
      ["Crawl depth", technical?.crawl_depth],
      ["Internal links", typeof technical?.inlink_count === "number" || typeof technical?.outlink_count === "number" ? `${stringify(technical?.inlink_count)} in / ${stringify(technical?.outlink_count)} out` : null],
      ["Response time", typeof technical?.response_time_ms === "number" ? `${technical.response_time_ms} ms` : null],
      ["Crawl status", technical?.crawl_status || technical?.error],
    ]} />
  </>;
}

function InternalLinkCandidates({ evidence }: { evidence: PageDetailResponse["internal_link_candidates"] }) {
  const rows = evidence?.rows || [];
  if (!rows.length) return <p className={styles.sectionEmpty}>{evidence?.reason || "No evidence-backed internal link candidates."}</p>;
  return <div className={styles.queryEvidence}>
    <table className={styles.evidenceTable} aria-label="Internal link candidates"><thead><tr><th>Source</th><th>Target</th><th>Anchor candidates</th></tr></thead><tbody>{rows.map((candidate) => <tr key={`${candidate.source_url}:${candidate.target_url}`}><td><a href={candidate.source_url} target="_blank" rel="noreferrer">{urlLabel(candidate.source_url)}</a></td><td><a href={candidate.target_url} target="_blank" rel="noreferrer">{urlLabel(candidate.target_url)}</a></td><td>{candidate.anchor_candidates.join(" · ") || "Not observed"}</td></tr>)}</tbody></table>
    <p className={styles.sectionEmpty}>{evidence?.reason}</p>
  </div>;
}

function DetailDrawer({ projectId, detail, onClose, onUpdated }: { projectId: string; detail: PageDetailResponse; onClose: () => void; onUpdated: () => void }) {
  const row = detail.row;
  const page = detail.page || row;
  const source = String(row.source || "");
  const sourceId = String(row.source_id || "");
  const sourceRecord = detail.source_record || {};
  const internalLinkRows = detail.internal_link_candidates?.rows || [];
  const today = new Date().toISOString().slice(0, 10);
  const decision = String(row.status || page.decision || "");
  const suggestedMetrics = decision === "improve_snippet" ? ["ctr", "clicks"] : decision === "expand_and_link" || internalLinkRows.length ? ["clicks", "position"] : ["clicks", "impressions"];
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [changeType, setChangeType] = useState<SeoChangeCreate["change_type"]>(source === "technical" ? "technical" : decision === "improve_snippet" ? "metadata" : decision === "expand_and_link" || internalLinkRows.length ? "internal_links" : "content");
  const [hypothesis, setHypothesis] = useState("");
  const [metrics, setMetrics] = useState<string[]>(suggestedMetrics);
  const [changedAt, setChangedAt] = useState(today);
  const [reviewDays, setReviewDays] = useState(28);
  const [note, setNote] = useState("");
  const [changeNote, setChangeNote] = useState("");
  const [owner, setOwner] = useState(String(sourceRecord.owner || row.owner || ""));
  const [technicalStatus, setTechnicalStatus] = useState(String(sourceRecord.status || row.status || "open"));
  const [contentStatus, setContentStatus] = useState(String(sourceRecord.status || row.status || "planned"));
  const [outcome, setOutcome] = useState<Record<string, unknown> | null>(null);
  const contentItem = asRecord(page.content_item) || (source === "content" ? sourceRecord : null);
  const historyItems: Array<[string, unknown]> = [
    ["Task source", row.source],
    ["Due date", row.due_date],
    ...(contentItem ? [["Content status", contentItem.status], ["Target keyword", contentItem.target_keyword], ["Scheduled at", contentItem.scheduled_at], ["Content id", contentItem.id]] as Array<[string, unknown]> : []),
    ...(source === "change" ? [["Change type", sourceRecord.change_type], ["Hypothesis", sourceRecord.hypothesis], ["Changed at", sourceRecord.changed_at], ["Review date", sourceRecord.review_date], ["Review status", sourceRecord.status]] as Array<[string, unknown]> : []),
    ...(source === "technical" ? [["Issue rule", sourceRecord.rule_id], ["Severity", sourceRecord.severity], ["Owner", sourceRecord.owner], ["Issue status", sourceRecord.status], ["Decision note", sourceRecord.decision_note]] as Array<[string, unknown]> : []),
  ];
  const mutate = async (task: () => Promise<unknown>, success: string, close = true) => {
    setBusy(true); setError(null); setMessage(null);
    try {
      await task();
      setMessage(success);
      onUpdated();
      if (close) onClose();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setBusy(false);
    }
  };

  const toggleMetric = (metric: string) => {
    setMetrics((current) => current.includes(metric) ? current.filter((item) => item !== metric) : [...current, metric]);
  };

  const record = () => {
    if (!page.url || !hypothesis.trim() || metrics.length === 0) { setError("URL, hypothesis and at least one metric are required."); return; }
    void mutate(
      () => createSeoChange(projectId, { urls: [String(page.url)], change_type: changeType, hypothesis: hypothesis.trim(), metrics, changed_at: changedAt, review_after_days: reviewDays, status: "shipped", note: changeNote.trim() }),
      "SEO change recorded.",
    );
  };

  const evaluate = async () => {
    setBusy(true); setError(null); setMessage(null);
    try {
      const result = await evaluateSeoChange(projectId, sourceId);
      setOutcome(result.report);
      setMessage("Outcome evidence generated. Review it before marking complete.");
      onUpdated();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setBusy(false);
    }
  };

  const canRecord = Boolean(page.url) && source !== "change" && !row.read_only;
  return (
      <Drawer label="Page workspace details" closeLabel="Close page details" eyebrow={stringify(row.source || detail.dataset)} title={stringify(row.title || row.query || page.title || "Page details")} url={page.url ? String(page.url) : undefined} onClose={onClose}>
        <section><h3>Why this needs attention</h3><DetailList items={[["Stage", row.group], ["Urgency", row.urgency], ["Decision / status", row.status || page.decision], ["Reason", row.reason || page.recommendation]]} /></section>
        <section><h3>Search performance</h3><SearchPerformance page={page} /></section>
        <section><h3>Statistical guidance</h3><StatisticalEvidence page={page} /></section>
        <section><h3>Query ownership</h3><QueryOwnership page={page} row={row} /></section>
        <section><h3>Technical evidence</h3><TechnicalEvidence page={page} /></section>
        <section><h3>Internal link candidates</h3><InternalLinkCandidates evidence={detail.internal_link_candidates} /></section>
        <section><h3>Content and change history</h3><DetailList items={historyItems} /></section>
        <section className={styles.actionsSection}>
          <h3>Available actions</h3>
          {source === "technical" && !row.read_only ? <div className={styles.actionForm}><label><span>Status</span><select value={technicalStatus} onChange={(event) => setTechnicalStatus(event.target.value)}>{["open", "planned", "fixed", "accepted"].map((value) => <option value={value} key={value}>{value}</option>)}</select></label><label><span>Owner</span><input value={owner} onChange={(event) => setOwner(event.target.value)} placeholder="seo" /></label><label className={styles.wideField}><span>Decision note</span><textarea value={note} onChange={(event) => setNote(event.target.value)} placeholder={technicalStatus === "accepted" ? "Required reason for accepting this risk" : "What changed?"} /></label><button type="button" disabled={busy} onClick={() => void mutate(() => updateTechnicalIssueStatus(projectId, sourceId, technicalStatus, owner, note), "Technical issue updated.")}>Update issue</button></div> : null}
          {source === "technical" && row.read_only ? <p className={styles.muted}>Grouped action is read-only. Open the source workspace to update individual issues.</p> : null}
          {source === "content" ? <div className={styles.actionForm}><label><span>Content status</span><select value={contentStatus} onChange={(event) => setContentStatus(event.target.value)}>{contentStatuses.map((value) => <option value={value} key={value}>{value.replaceAll("_", " ")}</option>)}</select></label><label className={styles.wideField}><span>Operator note</span><textarea value={note} onChange={(event) => setNote(event.target.value)} placeholder="Why is the status changing?" /></label><button type="button" disabled={busy} onClick={() => void mutate(() => updateContentStatus(projectId, sourceId, contentStatus, note), "Content status updated.")}>Update content</button></div> : null}
          {source === "change" ? <div className={styles.actionForm}><button type="button" disabled={busy} onClick={() => void evaluate()}>Evaluate current evidence</button>{outcome ? <DetailList items={[["Classification", outcome.classification], ["Comparability", outcome.comparability], ["Metrics", outcome.metrics], ["Statistical evidence", outcome.statistical_evidence], ["Interpretation", outcome.interpretation]]} /> : null}<label className={styles.wideField}><span>Review note</span><textarea value={note} onChange={(event) => setNote(event.target.value)} placeholder="What did the evidence show?" /></label><button type="button" disabled={busy || !outcome || !note.trim()} onClick={() => void mutate(() => updateSeoChangeStatus(projectId, sourceId, "reviewed", note), "SEO change marked reviewed.")}>Mark reviewed</button></div> : null}
          {canRecord ? <div className={styles.changeForm}><h4>Record SEO change</h4><p>Creates a local review record. It does not modify the site.</p><label><span>URL</span><input value={String(page.url)} readOnly /></label><label><span>Change type</span><select value={changeType} onChange={(event) => setChangeType(event.target.value as SeoChangeCreate["change_type"])}>{changeTypes.map((value) => <option value={value} key={value}>{value.replaceAll("_", " ")}</option>)}</select></label><label className={styles.wideField}><span>Hypothesis</span><textarea value={hypothesis} onChange={(event) => setHypothesis(event.target.value)} placeholder="What result do you expect, and why?" /></label><fieldset className={styles.metricChoices}><legend>Expected metrics</legend>{["clicks", "impressions", "ctr", "position"].map((value) => <label key={value}><input type="checkbox" checked={metrics.includes(value)} onChange={() => toggleMetric(value)} />{value}</label>)}</fieldset><label><span>Changed at</span><input type="date" value={changedAt} onChange={(event) => setChangedAt(event.target.value)} /></label><label><span>Review after</span><input type="number" min={1} max={3650} value={reviewDays} onChange={(event) => setReviewDays(Number(event.target.value))} /></label><label className={styles.wideField}><span>Note</span><input value={changeNote} onChange={(event) => setChangeNote(event.target.value)} placeholder="Optional implementation note" /></label><button type="button" disabled={busy} onClick={record}>Record change</button></div> : null}
          {error ? <p className={styles.actionError} role="alert">{error}</p> : null}
          {message ? <p className={styles.actionSuccess} role="status">{message}</p> : null}
          <p className={styles.muted}>Publishing, redirects, re-crawls and other site-changing operations remain in their source workspace.</p>
          {row.target_view && row.target_view !== "#/pages" ? <a className={styles.sourceLink} href={String(row.target_view)}>Open source workspace</a> : null}
        </section>
      </Drawer>
  );
}

export function PagesWorkbenchPage({ projectId, refreshKey, refreshing, initialGroup = "now", initialSource = "", initialQuery = "", onRefresh, onUpdated }: Props) {
  const [dataset, setDataset] = useState<PageDataset>("actions");
  const [group, setGroup] = useState(initialGroup);
  const [query, setQuery] = useState(initialQuery);
  const [source, setSource] = useState(initialSource);
  const [pageType, setPageType] = useState("");
  const [decision, setDecision] = useState("");
  const [status, setStatus] = useState("");
  const [sort, setSort] = useState(defaultSort.actions);
  const [direction, setDirection] = useState<"asc" | "desc">("asc");
  const [pageSize, setPageSize] = useState(50);
  const [offset, setOffset] = useState(0);
  const [filtersOpen, setFiltersOpen] = useState(true);
  const [detail, setDetail] = useState<PageDetailResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [refreshPending, setRefreshPending] = useState(false);
  const debouncedQuery = useDebouncedValue(query);

  useEffect(() => {
    setDataset("actions");
    setGroup(initialGroup);
    setSource(initialSource);
    setQuery(initialQuery);
    setOffset(0);
    setDetail(null);
  }, [projectId, initialGroup, initialSource, initialQuery]);

  const params = useMemo<PageViewParams>(() => ({
    dataset,
    group: dataset === "actions" ? group : "",
    q: debouncedQuery,
    source,
    page_type: dataset === "pages" ? pageType : "",
    decision: dataset === "pages" ? decision : "",
    status,
    sort,
    direction,
    limit: pageSize,
    offset,
  }), [dataset, group, debouncedQuery, source, pageType, decision, status, sort, direction, pageSize, offset]);

  const { data, error, loading, setError } = useViewData(projectId, params, refreshKey, fetchPageView);
  const { toggle: toggleColumn, visible: visibleIds } = useStoredColumns(`pages-columns:${projectId}:${dataset}`, data?.columns);
  const columns = data?.columns.filter((column) => visibleIds.includes(column.id)) || [];
  const tableColumns = columns.length ? columns : skeletonColumns[dataset];

  const changeDataset = (next: PageDataset) => {
    setDataset(next);
    setSort(defaultSort[next]);
    setDirection(next === "actions" ? "asc" : "desc");
    setOffset(0);
    setDetail(null);
  };
  const openRow = (row: PageViewRow) => {
    setDetailLoading(true);
    fetchPageDetail(projectId, dataset, row.row_key)
      .then(setDetail)
      .catch((reason: Error) => setError(reason.message))
      .finally(() => setDetailLoading(false));
  };
  const clearFilters = () => {
    setQuery(""); setSource(""); setPageType(""); setDecision(""); setStatus(""); setOffset(0);
  };
  const summaries = data?.summary.groups || {};
  const runRefresh = async () => {
    setRefreshPending(true);
    setError(null);
    try {
      await onRefresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setRefreshPending(false);
    }
  };
  const refreshBusy = refreshing || refreshPending;

  return (
    <section className={styles.page} aria-labelledby="pages-heading">
      <h1 id="pages-heading" className="srOnly">Pages</h1>
      <header className={styles.header}>
        <div className={styles.headerActions}>
          <button className={styles.refreshButton} type="button" disabled={refreshBusy} onClick={() => void runRefresh()}><RefreshCw size={16} className={refreshBusy ? styles.spinning : undefined} />{refreshBusy ? "Refreshing" : "Refresh analysis"}</button>
          <HelpTooltip label="Refresh analysis" align="right">Rebuilds this Pages view from local evidence — no crawl, no GSC collection.</HelpTooltip>
        </div>
      </header>

      <div className={styles.stageGrid} aria-label="Action stages">
        {(["now", "review", "watch"] as const).map((stage) => <button key={stage} type="button" aria-pressed={dataset === "actions" && group === stage} className={dataset === "actions" && group === stage ? styles.activeStage : styles.stage} onClick={() => { setDataset("actions"); setGroup(stage); setSort("urgency"); setDirection("asc"); setOffset(0); }}><span>{stageMeta[stage].label}</span><strong>{data ? summaries[stage] || 0 : "—"}</strong><small>{stageMeta[stage].description}</small></button>)}
      </div>

      <div className={styles.sourceRail} aria-label="Evidence freshness">
        {Object.entries(data?.sources || {}).map(([name, item]) => <div key={name} data-status={item.needs_refresh ? "needs_refresh" : item.status} title={item.refresh_reasons?.join(". ")}><span className={styles.sourceLabel}>{name}<HelpTooltip label={`${name} evidence`}>{sourceHelp[name] || "Evidence freshness for this Pages source."}</HelpTooltip></span><StatusPill value={item.needs_refresh ? "needs refresh" : item.status} context="evidence" /><small>{item.changed_since_refresh ? "Newer evidence available" : item.generated_at ? `${new Date(item.generated_at).toLocaleString()}${item.age_days === null || item.age_days === undefined ? "" : ` · ${Math.floor(item.age_days)}d old`}` : "No snapshot"}</small></div>)}
      </div>

      <div className={styles.viewer}>
        <div className={styles.tabs} role="tablist" aria-label="Page workspace datasets">
          {datasets.map((item) => <button key={item.id} type="button" role="tab" aria-selected={dataset === item.id} className={dataset === item.id ? styles.activeTab : styles.tab} onClick={() => changeDataset(item.id)}>{item.label}{item.id === "query_conflicts" ? <HelpTooltip label="Query conflicts">Queries with multiple competing URLs. Review them for search-intent ownership and possible cannibalization; this is a review queue, not a penalty.</HelpTooltip> : null}{item.id === "pages" ? <b>{data?.summary.pages || 0}</b> : item.id === "query_conflicts" ? <b>{data?.summary.query_conflicts || 0}</b> : null}</button>)}
        </div>
        <div className={styles.toolbar}>
          <SearchField label="Search page workspace" value={query} onChange={(value) => { setQuery(value); setOffset(0); }} placeholder={dataset === "query_conflicts" ? "Search query or owner URL" : "Search page, reason or owner"} />
          <label><span>Sort</span><select value={sort} onChange={(event) => { setSort(event.target.value); setOffset(0); }}>{(dataset === "actions" ? [["urgency", "Urgency"], ["title", "Action"], ["source", "Source"], ["status", "Status"], ["due_date", "Due date"]] : dataset === "pages" ? [["impressions", "Impressions"], ["clicks", "Clicks"], ["position", "Position"], ["opportunity_impressions", "Position 4–20"], ["recoverable_clicks", "CTR opportunity"], ["evidence_strength", "Evidence"], ["trend", "8-week trend"], ["cross_source_status", "GSC ↔ GA4"], ["commercial_quadrant", "Value × opportunity"], ["click_driver", "Click driver"], ["url", "URL"], ["decision", "Decision"], ["technical_issues", "Issues"]] : [["total_impressions", "Impressions"], ["primary_owner_share", "Primary share"], ["ownership_hhi", "Owner HHI"], ["owner_count", "Owners"], ["query", "Query"]]).map(([id, label]) => <option value={id} key={id}>{label}</option>)}</select></label>
          <button className={styles.directionButton} type="button" onClick={() => { setDirection((value) => value === "asc" ? "desc" : "asc"); setOffset(0); }}>{direction === "asc" ? <ArrowDown size={14} /> : <ArrowUp size={14} />}{direction === "asc" ? "Asc" : "Desc"}</button>
          <ColumnPicker columns={data?.columns} visible={visibleIds} onToggle={toggleColumn} />
        </div>
        <div className={styles.filters} id="pages-filter-bar">
          <button className={styles.filterToggle} type="button" aria-label="Toggle filters" aria-expanded={filtersOpen} aria-controls="pages-filter-controls" onClick={() => setFiltersOpen((value) => !value)}><Filter size={14} aria-hidden="true" /></button>
          {filtersOpen ? <div className={styles.filterControls} id="pages-filter-controls">
            {dataset === "actions" ? <label><span>Stage</span><select value={group} onChange={(event) => { setGroup(event.target.value); setOffset(0); }}><option value="">All</option><option value="now">Now</option><option value="review">Review</option><option value="watch">Watch</option><option value="done">Done</option></select></label> : null}
            {dataset !== "query_conflicts" ? <label><span>Source</span><select value={source} onChange={(event) => { setSource(event.target.value); setOffset(0); }}><option value="">All</option>{(dataset === "actions" ? ["portfolio", "content", "technical", "change"] : ["gsc_current", "gsc_previous", "technical", "content"]).map((value) => <option value={value} key={value}>{value.replaceAll("_", " ")}</option>)}</select></label> : null}
            {dataset === "pages" ? <><label><span>Type</span><select value={pageType} onChange={(event) => { setPageType(event.target.value); setOffset(0); }}><option value="">All</option>{["home", "product", "collection", "article", "page", "other"].map((value) => <option value={value} key={value}>{value}</option>)}</select></label><label><span>Decision</span><select value={decision} onChange={(event) => { setDecision(event.target.value); setOffset(0); }}><option value="">All</option>{["refresh", "consolidate_review", "improve_snippet", "expand_and_link", "defend", "monitor", "wait_for_data"].map((value) => <option value={value} key={value}>{value.replaceAll("_", " ")}</option>)}</select></label></> : null}
            {dataset !== "query_conflicts" ? <label><span>Status</span><input value={status} onChange={(event) => { setStatus(event.target.value); setOffset(0); }} placeholder="Any status" /></label> : null}
            {(query || source || pageType || decision || status) ? <button type="button" onClick={clearFilters}>Clear</button> : null}
          </div> : null}
          <span className={styles.resultCount}>{data ? pageLabel(offset, pageSize, data.pagination.total) : "—"}</span>
        </div>
        {error ? <p className={styles.error} role="alert">{error}</p> : null}
        <ProgressiveLoadingStatus loading={loading && !error} complete={Boolean(data && !loading)} label="page records" total={data?.pagination.total} />
        <div className={styles.tableScroll} aria-busy={loading}>
          <table><thead><tr>{tableColumns.map((column) => { const help = columnHelp[column.id]; return <th className={help ? styles.tooltipHeader : undefined} key={column.id}><span className={styles.columnHeading}>{column.label || column.id}{help ? <HelpTooltip label={help.label}>{help.text}</HelpTooltip> : null}</span></th>; })}</tr></thead><tbody>{loading && !data ? <ProgressiveSkeletonRows columns={tableColumns} /> : data?.rows.map((row) => <tr key={row.row_key} tabIndex={0} onClick={() => openRow(row)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); openRow(row); } }}>{columns.map((column) => <td className={column.id === "url" ? styles.urlColumn : undefined} key={column.id} title={stringify(row[column.id], 400)}>{cellValue(row, column)}</td>)}</tr>)}</tbody></table>
          {!loading && !data?.rows.length ? <div className={styles.empty}><Search size={22} /><strong>No work matches this view.</strong><span>{dataset === "actions" ? "Choose another stage or refresh the analysis." : "Broaden the filters or refresh the source evidence."}</span></div> : null}
        </div>
        <Pagination offset={offset} limit={pageSize} total={data?.pagination.total || 0} loading={loading} onOffsetChange={setOffset} onLimitChange={(value) => { setPageSize(value); setOffset(0); }} />
      </div>
      {detailLoading ? <div className={styles.detailLoading} role="status">Loading details…</div> : null}
      {detail ? <DetailDrawer projectId={projectId} detail={detail} onClose={() => setDetail(null)} onUpdated={onUpdated} /> : null}
    </section>
  );
}
