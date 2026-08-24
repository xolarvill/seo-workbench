import { useEffect, useMemo, useState, type ReactNode } from "react";
import { ArrowDown, ArrowUp, Bot, ExternalLink, RefreshCw, Search } from "lucide-react";

import { ApiError, collectKeywordDataForSeo, fetchKeywordHandoff, fetchKeywordView, openCodex, updateKeywords, type KeywordViewParams } from "../../api/client";
import type { KeywordDataset, KeywordDecision, KeywordPatch, KeywordRow, KeywordViewResponse } from "../../api/types";
import { confirmAction } from "../../components/ActionButton";
import { HelpTooltip } from "../../components/HelpTooltip";
import { Drawer } from "../../components/Drawer";
import { ProgressiveLoadingStatus, ProgressiveSkeletonRows, type SkeletonColumn } from "../../components/ProgressiveLoading";
import { StatusPill } from "../../components/StatusPill";
import { Pagination, SearchField, pageLabel } from "../../components/WorkbenchControls";
import { useDebouncedValue, useViewData } from "../../hooks/useWorkbenchData";
import { appHref } from "../../routes";
import styles from "./KeywordsWorkbenchPage.module.css";

type Props = {
  projectId: string;
  refreshKey: number;
  refreshing: boolean;
  initialQuery?: string;
  onRefresh: () => Promise<void>;
  onOpenFile: (path: string) => void;
};

type EditableField = keyof KeywordPatch;
type Scope = "" | "queue" | "map";

const tabs: Array<{ id: KeywordDataset; label: string }> = [
  { id: "keywords", label: "Opportunity Pool" },
  { id: "topics", label: "Topic Map" },
  { id: "research", label: "Research" },
];
const datasetLabels: Record<KeywordDataset, string> = { keywords: "keywords", topics: "topics", research: "research rows" };
const skeletonColumns: Record<KeywordDataset, SkeletonColumn[]> = {
  keywords: ["select", "keyword", "decision", "stage", "owner", "volume", "cpc", "competition", "score", "intent", "impressions", "position", "next"].map((id) => ({ id })),
  topics: ["cluster", "keywords", "targets", "content", "impressions", "flags"].map((id) => ({ id })),
  research: ["keyword", "decision", "research", "updated", "priority", "action"].map((id) => ({ id })),
};
const decisions: KeywordDecision[] = ["unreviewed", "prioritize", "hold", "drop"];
const editableFields: Array<{ id: EditableField; label: string }> = [
  { id: "decision", label: "Decision" },
  { id: "cluster_ref", label: "Cluster" },
  { id: "target_url", label: "Target URL" },
  { id: "target_content_id", label: "Content item" },
  { id: "note", label: "Note" },
];

const stageLabels: Record<string, string> = {
  needs_decision: "Needs decision",
  needs_mapping: "Needs mapping",
  mapped: "Mapped",
  demand_check: "Demand check",
  researched: "Researched",
  handed_off: "Handed off",
  held: "Held",
  dropped: "Dropped",
};

const tabHelp: Record<KeywordDataset, { label: string; text: ReactNode }> = {
  keywords: { label: "Opportunity Pool", text: <><strong>Decide what each query is worth before production.</strong><ul><li>Decision queue: rows that need your judgment now (seeds, high-demand queries without an owner, conflicts).</li><li>All: all observed GSC queries, read-only — they are evidence, not to-dos.</li><li>Queries with an existing owner should be held or dropped — do not create competing pages.</li></ul></> },
  topics: { label: "Topic Map", text: <><strong>Cluster view: inspect owner gaps and conflicts at the query-family level.</strong><ul><li>Multiple URLs ranking for the same query = ownership conflict (cannibalization).</li><li>unassigned / missing content = possible candidate gap.</li></ul></> },
  research: { label: "Research", text: <><strong>Deep-dive outputs for researched keywords.</strong><ul><li>Artifacts: strategy/keyword-dives/*.md (SERP top 10, intent, competitors, 90-day plan).</li><li>Research precedes the content brief (handoff to Content workbench).</li></ul></> },
};

const columnHelp: Record<string, { label: string; text: ReactNode }> = {
  decision: { label: "Decision", text: <><strong>Is this query worth investing in?</strong><ul><li>Prioritize: move forward</li><li>Hold: park</li><li>Drop: abandon.</li><li>Notice: do not create a competing page for a query that already has an owner.</li></ul></> },
  stage: { label: "Stage", text: <><strong>Keyword-side pipeline position (steps 1-4 of the article pipeline).</strong><ul><li>needs decision → mapped → demand check → researched → handed off.</li><li>Content-side steps (brief, production, publish) live in the Content workbench.</li></ul></> },
  owner: { label: "Owner", text: <><strong>Which page owns this query family (observed from GSC).</strong><ul><li>A candidate is a query family with no intended owner.</li><li>Multiple URLs ranking for one query = conflict (cannibalization).</li><li>gap = no observed owner yet.</li></ul></> },
  volume: { label: "Volume", text: <><strong>Monthly search volume (market side).</strong><ul><li>DataForSEO measurement preferred; falls back to source hints when not collected.</li></ul></> },
  cpc: { label: "CPC", text: "Cost per click (DataForSEO or source hint)" },
  competition: { label: "Competition", text: "Competition (DataForSEO). High competition ≠ not worth it — differentiation decides." },
  score: { label: "Score", text: "Workbench strategic priority score: source trust × volume/difficulty/CPC/intent weighting." },
  intent: { label: "Intent", text: "Query intent: informational / commercial / transactional / navigational — drives content format and conversion path." },
  impressions: { label: "GSC impressions", text: "Observed GSC impressions for this family on the site. Different source from market volume (DataForSEO)." },
  position: { label: "Position", text: "Observed average GSC position." },
  next: { label: "Next step", text: <><strong>The single next action for this row, derived from its pipeline state.</strong><ul><li>Collect data: DataForSEO demand evidence.</li><li>Deep dive: agent research handoff.</li><li>Brief: hand off to the Content workbench (brief production lives there).</li></ul></> },
  cluster: { label: "Cluster", text: "Query family: a group of related queries (from content-pipeline cluster definitions)." },
  targets: { label: "Targets", text: "Assigned target URLs for this family (observed or intended owner)." },
  content: { label: "Content", text: "Linked content item (content pipeline)." },
  flags: { label: "Flags", text: <><strong>Gap and conflict markers.</strong><ul><li>unassigned / missing content: candidate gaps.</li><li>ownership conflict: multiple URLs ranking for one query (cannibalization).</li></ul></> },
  updated: { label: "Updated", text: "Deep-dive file last-updated time." },
  priority: { label: "Priority", text: "Workbench strategic priority score (same as Score)." },
  action: { label: "Action", text: "Open existing research or trigger a new agent deep dive." },
};

function Th({ help, children }: { help?: { label: string; text: ReactNode }; children: ReactNode }) {
  return <th className={help ? styles.tooltipHeader : undefined}><span className={styles.columnHeading}>{children}{help ? <HelpTooltip label={help.label}>{help.text}</HelpTooltip> : null}</span></th>;
}

function number(value: number | undefined, digits = 0) {
  return value === undefined || value === null ? "—" : value.toLocaleString(undefined, { maximumFractionDigits: digits });
}

function currency(value: number | undefined | null) {
  return value === undefined || value === null ? "—" : `$${number(value, 2)}`;
}

function marketVolume(row: KeywordRow) {
  return row.market?.search_volume ?? (row.source === "semrush_manual" || row.source === "ads" ? row.volume_hint : undefined);
}

function marketCpc(row: KeywordRow) {
  return row.market?.cpc ?? (row.source === "semrush_manual" || row.source === "ads" ? row.cpc_hint : undefined);
}

function marketIntent(row: KeywordRow) {
  return row.market?.intent || row.intent || "—";
}

function targetPageHref(url: string) {
  return appHref("pages", { q: url });
}

function keywordHref(keyword: string) {
  return appHref("keywords", { q: keyword });
}

function valueForField(data: KeywordViewResponse, field: EditableField, value: string, setValue: (value: string) => void) {
  if (field === "decision") return <select aria-label="Batch decision" value={value} onChange={(event) => setValue(event.target.value)}>{decisions.map((item) => <option key={item} value={item}>{item}</option>)}</select>;
  if (field === "cluster_ref") return <select aria-label="Batch cluster" value={value} onChange={(event) => setValue(event.target.value)}><option value="">Clear cluster</option>{data.options.clusters.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select>;
  if (field === "target_content_id") return <select aria-label="Batch content item" value={value} onChange={(event) => setValue(event.target.value)}><option value="">Clear content item</option>{data.options.content_items.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select>;
  return <input aria-label={`Batch ${field.replaceAll("_", " ")}`} value={value} onChange={(event) => setValue(event.target.value)} placeholder={field === "target_url" ? "/collections/example" : "Operator note"} />;
}

function ownerCell(row: KeywordRow) {
  const observed = row.owner_urls || [];
  const intended = row.target_url || (row.target_content_id ? `content:${row.target_content_id}` : "");
  if (observed.length > 1) {
    return <span className={styles.ownerCell}>{observed.slice(0, 3).map((url) => <a key={url} href={targetPageHref(url)} onClick={(event) => event.stopPropagation()}>{url}</a>)}<StatusPill value="conflict" context="status" tone="danger" /></span>;
  }
  if (observed.length === 1) {
    return <span className={styles.ownerCell}>{intended ? <a href={targetPageHref(observed[0])} onClick={(event) => event.stopPropagation()}>{observed[0]}</a> : <a href={targetPageHref(observed[0])} onClick={(event) => event.stopPropagation()}>{observed[0]}</a>}</span>;
  }
  if (intended) {
    return <span className={styles.ownerCell}>{intended.startsWith("content:") ? <a href={appHref("content", { item: intended.slice(8) })} onClick={(event) => event.stopPropagation()}>{intended}</a> : <a href={targetPageHref(intended)} onClick={(event) => event.stopPropagation()}>{intended}</a>}</span>;
  }
  return <span className={styles.ownerGap}>gap — no owner</span>;
}

function nextStepCell(row: KeywordRow, onCollectMarket: (row: KeywordRow) => Promise<void>, onHandoff: (row: KeywordRow) => Promise<void>) {
  const stage = row.stage || "needs_decision";
  if (stage === "mapped") return <button type="button" className={styles.textButton} onClick={(event) => { event.stopPropagation(); void onCollectMarket(row); }}>Collect data</button>;
  if (stage === "demand_check") return <button type="button" className={styles.textButton} onClick={(event) => { event.stopPropagation(); void onHandoff(row); }}>Deep dive</button>;
  if (stage === "researched") return <a href="#/content" onClick={(event) => event.stopPropagation()}>Brief →</a>;
  if (stage === "handed_off") return row.content?.id ? <a href={appHref("content", { item: row.content.id })} onClick={(event) => event.stopPropagation()}>{row.content.status || "in content"} →</a> : <span className={styles.muted}>in content</span>;
  if (stage === "needs_decision") return <span className={styles.muted}>Decide</span>;
  if (stage === "needs_mapping") return <span className={styles.muted}>Assign target</span>;
  return <span className={styles.muted}>—</span>;
}

function Stepper({ row }: { row: KeywordRow }) {
  const decided = row.decision !== "unreviewed" && Boolean(row.decision);
  const mapped = Boolean(row.cluster_ref || row.target_url || row.target_content_id);
  const demand = Boolean(row.market);
  const researched = Boolean(row.research_path);
  const content = row.content;
  const steps: Array<{ done: boolean; label: string }> = [
    { done: decided, label: "1 · Decide" },
    { done: mapped, label: "2 · Map" },
    { done: demand, label: "3 · Demand" },
    { done: researched, label: "4 · Deep dive" },
  ];
  return <section className={styles.stepperSection}>
    <h3>Pipeline<HelpTooltip label="Pipeline position">Keyword-side steps 1-4; the brief handoff at step 5 and everything after lives in the Content workbench (brief production will be a content sub-tab).</HelpTooltip></h3>
    <div className={styles.stepper}>
      {steps.map((step) => <span key={step.label} className={step.done ? styles.stepDone : undefined}>{step.done ? "✔" : "○"} {step.label}</span>)}
    </div>
    <p className={styles.handoff}>⇣ Step 5 · handoff: <strong>brief</strong> → Content workbench {content ? null : "(create the brief there)"}</p>
    <div className={styles.contentSide}>
      <span className={styles.contentSideLabel}>Steps 5-8 · content side</span>
      {content ? <><StatusPill value={content.status || "planned"} context="status" />{content.live_url ? <a href={content.live_url} rel="noreferrer" target="_blank">live url <ExternalLink size={11} /></a> : content.id ? <a href={appHref("content", { item: content.id })}>open item</a> : null}</> : <span className={styles.muted}>Not handed off yet.</span>}
    </div>
  </section>;
}

function KeywordDrawer({ row, data, busy, onClose, onSave, onHandoff, onCollectMarket }: { row: KeywordRow; data: KeywordViewResponse; busy: boolean; onClose: () => void; onSave: (patch: KeywordPatch) => Promise<void>; onHandoff: (row: KeywordRow) => Promise<void>; onCollectMarket: (row: KeywordRow) => Promise<void> }) {
  const [decision, setDecision] = useState<KeywordDecision>(row.decision || "unreviewed");
  const [cluster, setCluster] = useState(row.cluster_ref || "");
  const [targetUrl, setTargetUrl] = useState(row.target_url || "");
  const [contentId, setContentId] = useState(row.target_content_id || "");
  const [note, setNote] = useState(row.note || "");
  const dataForSeoAvailable = Boolean(data.sources.dataforseo);

  return <Drawer label="Keyword details" closeLabel="Close keyword details" eyebrow={row.source || "keyword"} title={row.keyword} onClose={onClose}>
      <div className={styles.drawerPills}><StatusPill value={row.decision || "unreviewed"} context="status" /><StatusPill value={row.stage || "needs_decision"} context="status" />{row.managed === false ? <StatusPill value="Query candidate" context="evidence" /> : null}{row.mapping_conflict ? <StatusPill value="ownership conflict" context="status" tone="danger" /> : null}</div>
      <Stepper row={row} />
      <section><h3>Strategy and ownership<HelpTooltip label="Strategy and ownership">Decisions and assignment: Decision, Cluster, Target URL, Content item — the owner contract for this query.</HelpTooltip></h3><div className={styles.editForm}>
        <label><span>Decision</span><select value={decision} onChange={(event) => setDecision(event.target.value as KeywordDecision)}>{decisions.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
        <label><span>Cluster</span><select value={cluster} onChange={(event) => setCluster(event.target.value)}><option value="">Unassigned</option>{data.options.clusters.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
        <label><span>Target URL</span><input value={targetUrl} onChange={(event) => setTargetUrl(event.target.value)} placeholder="/collections/example" /></label>
        <label><span>Content item</span><select value={contentId} onChange={(event) => setContentId(event.target.value)}><option value="">Unassigned</option>{data.options.content_items.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
        <label className={styles.wide}><span>Note</span><textarea value={note} onChange={(event) => setNote(event.target.value)} /></label>
        <div className={styles.drawerActions}><div className={styles.actionWithHelp}><button type="button" disabled={busy} onClick={() => void onHandoff(row)}><Bot size={15} />{row.research_path ? "Open research" : "Agent deep dive"}</button><HelpTooltip label="Agent deep dive"><><strong>Hand research to the agent (Codex).</strong><ul><li>Runs skills/keyword-deep-dive and writes strategy/keyword-dives/*.md.</li><li>Covers SERP top 10, intent, competitors, 90-day plan.</li></ul></></HelpTooltip></div><button type="button" disabled={busy} onClick={() => void onSave({ decision, cluster_ref: cluster, target_url: targetUrl, target_content_id: contentId, note })}>Save keyword</button></div>
      </div></section>
      <section><h3>Query evidence<HelpTooltip label="Query evidence">On-site GSC evidence: impressions, clicks, position, and which URLs rank (observed owners).</HelpTooltip></h3><dl className={styles.detailList}>
        <div><dt>Priority</dt><dd>{number(row.priority_score, 1)}</dd></div><div><dt>Intent</dt><dd>{row.intent || "Not observed"}</dd></div>
        <div><dt>Exact query</dt><dd>{row.gsc?.query || "Not observed"}</dd></div><div><dt>Exact impressions</dt><dd>{number(row.gsc?.impressions)}</dd></div>
        <div><dt>Cluster queries</dt><dd>{row.observed_queries?.length || "Not observed"}</dd></div><div><dt>Cluster impressions</dt><dd>{number(row.cluster_gsc?.impressions)}</dd></div>
        <div><dt>Cluster clicks</dt><dd>{number(row.cluster_gsc?.clicks, 1)}</dd></div><div><dt>Cluster position</dt><dd>{number(row.cluster_gsc?.position, 1)}</dd></div>
        <div><dt>Research</dt><dd>{row.research_path ? <button type="button" className={styles.textButton} onClick={() => void onHandoff(row)}>{row.research_path}</button> : "Not collected"}</dd></div>
      </dl>{row.observed_queries?.length ? <div className={styles.queryEvidence}><table><thead><tr><th>Observed query</th><th>Clicks</th><th>Impressions</th><th>Position</th><th>Ranking URLs</th></tr></thead><tbody>{row.observed_queries.map((item) => <tr key={item.query}><td>{item.raw_queries?.join(", ") || item.query}</td><td>{number(item.clicks, 1)}</td><td>{number(item.impressions)}</td><td>{number(item.position, 1)}</td><td>{item.owner_urls.length ? item.owner_urls.map((url) => <a key={url} href={targetPageHref(url)}>{url}</a>) : "Not observed"}</td></tr>)}</tbody></table></div> : null}</section>
      <section><div className={styles.sectionHeading}><div><h3>Market and SERP evidence<HelpTooltip label="Market and SERP evidence">DataForSEO market data: demand size, 12-month trend, SERP shape, and ranking pages.</HelpTooltip></h3><p>DataForSEO · United States · English</p></div><div className={styles.actionWithHelp}><button type="button" disabled={busy || !dataForSeoAvailable} onClick={() => void onCollectMarket(row)}><RefreshCw size={14} />{!dataForSeoAvailable ? "Available after restart" : row.market ? "Refresh paid data" : "Collect paid data"}</button><HelpTooltip label="Collect paid data"><><strong>Collect market evidence via DataForSEO.</strong><ul><li>volume / CPC / competition / 12-month trend / live SERP.</li><li>Billed per request (~$0.014 per keyword); artifacts land in audits/keywords/dataforseo/.</li></ul></></HelpTooltip></div></div>
        <dl className={styles.marketMetrics}>
          <div><dt>Volume</dt><dd>{number(marketVolume(row))}</dd></div><div><dt>CPC</dt><dd>{currency(marketCpc(row))}</dd></div><div><dt>Competition</dt><dd>{number(row.market?.competition ?? undefined, 2)}</dd></div><div><dt>Score</dt><dd>{number(row.priority_score, 1)}</dd></div><div><dt>Intent</dt><dd>{marketIntent(row)}</dd></div>
        </dl>
        {row.market?.monthly_searches?.length ? <div className={styles.trend} aria-label="12 month search volume trend">{[...row.market.monthly_searches].sort((a, b) => a.year * 12 + a.month - (b.year * 12 + b.month)).map((item) => { const peak = Math.max(...row.market!.monthly_searches!.map((point) => point.search_volume), 1); return <div key={`${item.year}-${item.month}`}><span style={{ height: `${Math.max(4, item.search_volume / peak * 100)}%` }} /><small>{new Date(item.year, item.month - 1).toLocaleString(undefined, { month: "short" })}</small><b>{number(item.search_volume)}</b></div>; })}</div> : <p className={styles.noEvidence}>Trend not collected.</p>}
        {row.market?.serp?.results?.length ? <div className={styles.serpResults}><div><strong>SERP analysis</strong><span>{number(row.market.serp.se_results_count ?? undefined)} results · {row.market.serp.item_types?.length || 0} feature types</span></div><ol>{row.market.serp.results.map((item) => <li key={`${item.rank}-${item.url}`}><span>{item.rank}</span><div><a href={item.url || undefined} target="_blank" rel="noreferrer">{item.title || item.url}</a><small>{item.domain}</small><p>{item.description}</p></div></li>)}</ol></div> : <p className={styles.noEvidence}>SERP analysis not collected.</p>}
        {row.market ? <p className={styles.evidenceMeta}>Collected {new Date(row.market.collected_at).toLocaleString()} · request cost ${number(row.market.cost_usd, 4)}</p> : null}
      </section>
      <p className={styles.boundary}>This workspace records local decisions only. It does not publish, redirect, crawl, or submit indexing requests.</p>
    </Drawer>;
}

export function KeywordsWorkbenchPage({ projectId, refreshKey, refreshing, initialQuery = "", onRefresh, onOpenFile }: Props) {
  const [dataset, setDataset] = useState<KeywordDataset>("keywords");
  const [scope, setScope] = useState<Scope>("queue");
  const [query, setQuery] = useState(initialQuery);
  const [decision, setDecision] = useState("");
  const [stage, setStage] = useState("");
  const [intent, setIntent] = useState("");
  const [source, setSource] = useState("");
  const [mapping, setMapping] = useState("");
  const [sort, setSort] = useState("priority_score");
  const [direction, setDirection] = useState<"asc" | "desc">("desc");
  const [offset, setOffset] = useState(0);
  const [pageSize, setPageSize] = useState(50);
  const [message, setMessage] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [detail, setDetail] = useState<KeywordRow | null>(null);
  const [batchField, setBatchField] = useState<EditableField>("decision");
  const [batchValue, setBatchValue] = useState("prioritize");
  const [busy, setBusy] = useState(false);
  const [localRefresh, setLocalRefresh] = useState(0);
  const debouncedQuery = useDebouncedValue(query);

  useEffect(() => {
    setQuery(initialQuery);
    setDecision("");
    setOffset(0);
  }, [projectId, initialQuery]);

  const params = useMemo<KeywordViewParams>(() => ({ dataset, q: debouncedQuery, decision, stage, intent, source, mapping, scope, sort, direction, limit: pageSize, offset }), [dataset, debouncedQuery, decision, stage, intent, source, mapping, scope, sort, direction, pageSize, offset]);
  const { data, error, loading, setError } = useViewData(projectId, params, `${refreshKey}:${localRefresh}`, fetchKeywordView);

  const changeDataset = (next: KeywordDataset) => {
    setDataset(next); setOffset(0); setSelected(new Set()); setDetail(null); setDecision(""); setMapping(""); setStage("");
    setSort(next === "topics" ? "impressions" : next === "research" ? "research_updated_at" : "priority_score");
    setDirection("desc");
  };
  const changeScope = (next: Scope) => {
    setScope(next); setOffset(0); setSelected(new Set()); setDetail(null); setDecision(""); setMapping(""); setStage(""); setSort("priority_score"); setDirection("desc");
  };
  const toggle = (keyword: string) => setSelected((current) => { const next = new Set(current); next.has(keyword) ? next.delete(keyword) : next.add(keyword); return next; });
  const pageKeywords = data?.rows.map((row) => row.keyword).filter((value): value is string => Boolean(value)) || [];
  const pageSelected = pageKeywords.length > 0 && pageKeywords.every((keyword) => selected.has(keyword));
  const selectPage = () => setSelected((current) => { const next = new Set(current); pageSelected ? pageKeywords.forEach((item) => next.delete(item)) : pageKeywords.forEach((item) => next.add(item)); return next; });

  const selectAllFiltered = async () => {
    if (!data) return;
    if (data.pagination.total > 1_000) { setError("The filtered result exceeds the 1,000-keyword batch limit. Narrow the filters first."); return; }
    try {
      const all = await fetchKeywordView(projectId, { ...params, limit: 1_000, offset: 0 });
      setSelected(new Set(all.rows.map((row) => row.keyword).filter((value): value is string => Boolean(value))));
      setMessage(`Selected all ${all.pagination.total} filtered keywords.`);
    } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); }
  };

  const save = async (keywords: string[], patch: KeywordPatch) => {
    if (!data || !keywords.length) return;
    setBusy(true); setError(null); setMessage(null);
    try {
      const result = await updateKeywords(projectId, keywords, patch, data.revision);
      setMessage(`${result.updated} keyword${result.updated === 1 ? "" : "s"} updated.`);
      setSelected(new Set()); setDetail(null); setLocalRefresh((value) => value + 1);
    } catch (reason) {
      if (reason instanceof ApiError && reason.status === 409) {
        setError("The keyword pool changed in another session. The view was reloaded; review and apply the edit again.");
        setLocalRefresh((value) => value + 1);
      } else setError(reason instanceof Error ? reason.message : String(reason));
    } finally { setBusy(false); }
  };

  const handoff = async (row: KeywordRow) => {
    if (!row.keyword) return;
    setBusy(true); setError(null); setMessage(null);
    try {
      const result = await fetchKeywordHandoff(projectId, row.keyword);
      if (result.existing_path) { onOpenFile(result.existing_path); return; }
      if (!result.prompt) throw new Error("Agent handoff prompt is unavailable.");
      await navigator.clipboard.writeText(result.prompt);
      await openCodex();
      setMessage(`Agent request copied. Expected output: ${result.output_path}`);
    } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); }
    finally { setBusy(false); }
  };

  const collectMarket = async (row: KeywordRow) => {
    if (!row.keyword || !confirmAction(`Collect paid DataForSEO keyword and live SERP evidence for “${row.keyword}”?`)) return;
    setBusy(true); setError(null); setMessage(null);
    try {
      const result = await collectKeywordDataForSeo(projectId, row.keyword);
      setMessage(`DataForSEO evidence collected for ${result.keyword}. Request cost: $${number(result.cost_usd, 4)}.`);
      setDetail(null); setLocalRefresh((value) => value + 1);
    } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); }
    finally { setBusy(false); }
  };

  const refreshStatistics = async () => {
    setError(null);
    try { await onRefresh(); setMessage("Statistics collection started. Keyword metrics will update from the existing evidence path."); }
    catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); }
  };

  const summary = data?.summary;
  const queueStages = summary?.queue_stages || {};
  const queueTotal = Number.isFinite(summary?.queue) ? (summary?.queue as number) : null;
  const mapTotal = Number.isFinite(summary?.total) && Number.isFinite(summary?.queue) ? (summary!.total as number) - (summary!.queue as number) : null;
  const funnel = summary ? [
    { label: "Decide", count: queueStages.needs_decision ?? 0, hint: "awaiting decision", stage: "needs_decision" },
    { label: "Map", count: queueStages.needs_mapping ?? 0, hint: "assign owner", stage: "needs_mapping" },
    { label: "Demand", count: (queueStages.mapped ?? 0) + (queueStages.demand_check ?? 0), hint: "market evidence", stage: "mapped,demand_check" },
    { label: "Research", count: queueStages.researched ?? 0, hint: "deep dives ready", stage: "researched" },
  ] : [];
  const funnelClick = (stageValue: string) => {
    setDataset("keywords"); setScope("queue"); setDecision(""); setMapping(""); setStage(stageValue); setOffset(0);
  };
  const inQueue = scope !== "map";
  return <section className={styles.page} aria-labelledby="keywords-heading" aria-busy={loading}>
    <header className={styles.header}><div><span>Search demand → ownership → outcome</span><h1 id="keywords-heading">Keywords</h1><p>Decide, map, research, and hand search performance to content — without creating a second metrics store.</p></div><div className={styles.headerActions}><button type="button" disabled={refreshing} onClick={() => void refreshStatistics()}><RefreshCw size={15} className={refreshing ? styles.spinning : undefined} />{refreshing ? "Collecting" : "Refresh statistics"}</button><HelpTooltip label="Keyword evidence refresh" align="right"><><strong>Refresh keyword metrics from existing evidence paths.</strong><ul><li>Runs the existing Statistics collection; no new data source.</li><li>Missing evidence stays unknown — never treated as zero.</li></ul></></HelpTooltip></div></header>
    <ProgressiveLoadingStatus loading={loading && !error} complete={Boolean(data && !loading)} label={datasetLabels[dataset]} total={data?.pagination.total} notice={message || undefined} />
    <div className={styles.funnel} aria-label="Keyword pipeline summary">
      {funnel.map((item) => <button key={item.label} type="button" onClick={() => funnelClick(item.stage)}><span>{item.label}</span><strong>{item.count ?? "—"}</strong><small>{item.hint}</small></button>)}
      <a className={styles.funnelLink} href="#/content"><span>In content</span><strong>{summary?.stages.handed_off ?? "—"}</strong><small>handed to content</small></a>
    </div>
    <div className={styles.viewer}>
      <div className={styles.scopeBar}>
        <div className={styles.scopeToggle} aria-label="Keyword workspace scope">
          <button type="button" className={scope === "queue" ? styles.activeScope : undefined} onClick={() => changeScope("queue")}>Decision queue<strong>{queueTotal ?? "—"}</strong></button>
          <button type="button" className={scope === "map" ? styles.activeScope : undefined} onClick={() => changeScope("map")}>All<strong>{mapTotal ?? "—"}</strong></button>
        </div>
        {scope === "map" ? <p className={styles.scopeHint}>Evidence view: all observed GSC queries, read-only. Decide a row from its drawer to move it into the decision queue.</p> : <p className={styles.scopeHint}>Only rows needing your judgment appear here. Decide or map them to clear the queue.{summary && (summary.decisions.hold || summary.decisions.drop) ? <> Decided: <strong>{summary.decisions.hold || 0} held</strong> · <strong>{summary.decisions.drop || 0} dropped</strong> — see them in the All.</> : null}</p>}
      </div>
      <div className={styles.tabs} role="tablist" aria-label="Keyword workspace views">{tabs.map((tab) => <button key={tab.id} type="button" role="tab" aria-selected={dataset === tab.id} className={dataset === tab.id ? styles.activeTab : undefined} onClick={() => changeDataset(tab.id)}>{tab.label}<HelpTooltip label={tabHelp[tab.id].label}>{tabHelp[tab.id].text}</HelpTooltip></button>)}</div>
      <div className={styles.toolbar}><SearchField label="Search keywords" value={query} onChange={(value) => { setQuery(value); setOffset(0); }} placeholder="Search keyword or note" /><label><span>Sort</span><select value={sort} onChange={(event) => { setSort(event.target.value); setOffset(0); }}>{dataset === "topics" ? <><option value="impressions">Impressions</option><option value="keyword_count">Keywords</option><option value="priority_score">Priority</option></> : dataset === "research" ? <><option value="research_updated_at">Updated</option><option value="priority_score">Priority</option><option value="keyword">Keyword</option></> : <><option value="priority_score">Score</option><option value="volume">Volume</option><option value="cpc">CPC</option><option value="competition">Competition</option><option value="impressions">GSC impressions</option><option value="clicks">GSC clicks</option><option value="position">Position</option><option value="keyword">Keyword</option></>}</select></label><button type="button" className={styles.direction} onClick={() => { setDirection((value) => value === "asc" ? "desc" : "asc"); setOffset(0); }}>{direction === "asc" ? <ArrowDown size={14} /> : <ArrowUp size={14} />}{direction}</button></div>
      <div className={styles.filters}>{dataset !== "topics" ? <><label><span>Decision</span><select value={decision} onChange={(event) => { setDecision(event.target.value); setOffset(0); }}><option value="">All</option>{data?.facets.decision?.map((item) => <option key={item} value={item}>{item}</option>)}</select></label><label><span>Stage</span><select value={stage} onChange={(event) => { setStage(event.target.value); setOffset(0); }}><option value="">All</option>{data?.facets.stage?.map((item) => <option key={item} value={item}>{stageLabels[item] || item}</option>)}</select></label><label><span>Intent</span><select value={intent} onChange={(event) => { setIntent(event.target.value); setOffset(0); }}><option value="">All</option>{data?.facets.intent?.map((item) => <option key={item} value={item}>{item}</option>)}</select></label><label><span>Source</span><select value={source} onChange={(event) => { setSource(event.target.value); setOffset(0); }}><option value="">All</option>{data?.facets.source?.map((item) => <option key={item} value={item}>{item}</option>)}</select></label><label><span>Mapping</span><select value={mapping} onChange={(event) => { setMapping(event.target.value); setOffset(0); }}><option value="">All</option><option value="mapped">Mapped</option><option value="unmapped">Unmapped</option></select></label></> : null}<span>{data ? pageLabel(offset, pageSize, data.pagination.total) : "—"}</span></div>
      {inQueue && dataset === "keywords" && selected.size ? <div className={styles.batchBar}><strong>{selected.size} selected</strong><button type="button" onClick={() => void selectAllFiltered()}>Select all {data?.pagination.total || 0} filtered</button><label><span>Field</span><select value={batchField} onChange={(event) => { const field = event.target.value as EditableField; setBatchField(field); setBatchValue(field === "decision" ? "prioritize" : ""); }}>{editableFields.map((field) => <option key={field.id} value={field.id}>{field.label}</option>)}</select></label>{data ? valueForField(data, batchField, batchValue, setBatchValue) : null}<button type="button" disabled={busy} onClick={() => void save(Array.from(selected), { [batchField]: batchValue } as KeywordPatch)}>Apply</button><button type="button" onClick={() => setSelected(new Set())}>Clear</button></div> : null}
      {error ? <p className={styles.error} role="alert">{error}</p> : null}
      <div className={styles.tableScroll} aria-busy={loading}><table>
        <thead><tr>{dataset === "keywords" ? <>{inQueue ? <th><input type="checkbox" aria-label="Select current page" checked={pageSelected} onChange={selectPage} /></th> : null}<Th>Keyword</Th><Th help={columnHelp.decision}>Decision</Th><Th help={columnHelp.stage}>Stage</Th><Th help={columnHelp.owner}>Owner</Th><Th help={columnHelp.volume}>Volume</Th><Th help={columnHelp.cpc}>CPC</Th><Th help={columnHelp.competition}>Comp.</Th><Th help={columnHelp.score}>Score</Th><Th help={columnHelp.intent}>Intent</Th><Th help={columnHelp.impressions}>GSC imp.</Th><Th help={columnHelp.position}>Position</Th><Th help={columnHelp.next}>Next step</Th></> : dataset === "topics" ? <><Th help={columnHelp.cluster}>Cluster</Th><Th>Keyword and queries</Th><Th help={columnHelp.targets}>Targets</Th><Th help={columnHelp.content}>Content</Th><Th help={columnHelp.impressions}>GSC imp.</Th><Th help={columnHelp.flags}>Flags</Th></> : <><Th>Keyword</Th><Th help={columnHelp.decision}>Decision</Th><Th help={columnHelp.research}>Research</Th><Th help={columnHelp.updated}>Updated</Th><Th help={columnHelp.priority}>Priority</Th><Th help={columnHelp.action}>Action</Th></>}</tr></thead>
        <tbody>{loading && !data ? <ProgressiveSkeletonRows columns={skeletonColumns[dataset]} /> : data?.rows.map((row) => dataset === "keywords" ? <tr key={row.row_key} onClick={() => setDetail(row)}>{inQueue ? <td onClick={(event) => event.stopPropagation()}><input type="checkbox" aria-label={`Select ${row.keyword}`} checked={selected.has(row.keyword || "")} onChange={() => row.keyword && toggle(row.keyword)} /></td> : null}<td><button className={styles.keywordButton} type="button">{row.keyword}</button>{row.managed === false ? <small>Query candidate{row.gsc?.query && row.gsc.query !== row.keyword ? ` · ${row.gsc.query}` : ""}</small> : row.market ? <small>DataForSEO · {new Date(row.market.collected_at).toLocaleDateString()}</small> : null}</td><td><StatusPill value={row.decision || "unreviewed"} context="status" /></td><td><StatusPill value={row.stage || "needs_decision"} context="status" /></td><td>{ownerCell(row)}</td><td className={styles.numeric}>{number(marketVolume(row))}</td><td className={styles.numeric}>{currency(marketCpc(row))}</td><td className={styles.numeric}>{number(row.market?.competition ?? undefined, 2)}</td><td className={styles.numeric}>{number(row.priority_score, 1)}</td><td>{marketIntent(row)}</td><td className={styles.numeric}>{number(row.gsc?.impressions)}</td><td className={styles.numeric}>{number(row.gsc?.position, 1)}</td><td>{nextStepCell(row, collectMarket, handoff)}</td></tr> : dataset === "topics" ? <tr key={row.row_key}><td>{row.cluster_ref || "Unassigned"}</td><td><strong>{row.representative_keyword || row.keywords?.[0] || "Unassigned"}</strong><small>{row.keyword_count || 0} keywords · {row.query_count || 0} observed queries</small><small>{row.keywords?.join(", ")}</small></td><td>{row.target_urls?.length ? row.target_urls.map((url) => <a key={url} href={targetPageHref(url)}>{url}</a>) : "No targets"}</td><td>{row.target_content_ids?.length ? row.target_content_ids.map((id) => <a key={id} href={appHref("content", { item: id })}>{id}</a>) : row.missing_content ? <StatusPill value="missing content" context="status" tone="danger" /> : "—"}</td><td className={styles.numeric}>{number(row.impressions)}</td><td><span className={styles.flags}>{row.unassigned ? <StatusPill value="unassigned" context="status" tone="warning" /> : null}{row.missing_content ? <StatusPill value="missing content" context="status" tone="warning" /> : null}{row.ownership_conflict ? <StatusPill value="ownership conflict" context="status" tone="danger" /> : null}{row.target_conflict ? <StatusPill value="target conflict" context="status" tone="danger" /> : null}{row.content_conflict ? <StatusPill value="content conflict" context="status" tone="danger" /> : null}</span></td></tr> : <tr key={row.row_key}><td>{row.keyword ? <a href={keywordHref(row.keyword)}>{row.keyword}</a> : "—"}</td><td><StatusPill value={row.decision || "unreviewed"} context="status" /></td><td>{row.research_path ? <button type="button" className={styles.textButton} onClick={() => void handoff(row)}>{row.research_path}</button> : "Not collected"}</td><td>{row.research_updated_at ? new Date(row.research_updated_at).toLocaleDateString() : "—"}</td><td className={styles.numeric}>{number(row.priority_score, 1)}</td><td><button type="button" className={styles.textButton} onClick={() => void handoff(row)}>{row.research_path ? "Open" : "Deep dive"}</button></td></tr>)}</tbody></table>{!loading && !data?.rows.length ? <div className={styles.empty}><Search size={22} /><strong>No keywords match this view.</strong><span>{inQueue ? "The decision queue is clear — nothing needs your judgment now." : "Broaden the filters or collect the missing evidence."}</span></div> : null}</div>
      <Pagination offset={offset} limit={pageSize} total={data?.pagination.total || 0} loading={loading} onOffsetChange={setOffset} onLimitChange={(value) => { setPageSize(value); setOffset(0); }} />
    </div>
    <footer className={styles.sourceFoot}>{Object.entries(data?.sources || {}).map(([name, item]) => <span key={name}><b>{name.replaceAll("_", " ")}</b>{item.generated_at ? new Date(item.generated_at).toLocaleString() : `${item.count} records`}</span>)}<a href="#/content">Content workbench <ExternalLink size={13} /></a></footer>
    {detail && data ? <KeywordDrawer row={detail} data={data} busy={busy} onClose={() => setDetail(null)} onSave={(patch) => save([detail.keyword || ""], patch)} onHandoff={handoff} onCollectMarket={collectMarket} /> : null}
  </section>;
}
