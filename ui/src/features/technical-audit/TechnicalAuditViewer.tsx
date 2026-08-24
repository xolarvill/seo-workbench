import { useEffect, useMemo, useState } from "react";
import { ArrowDown, ArrowUp, CheckSquare, ExternalLink, Filter, RotateCcw, Search, Trash2 } from "lucide-react";
import { type ReactNode } from "react";

import { fetchTechAuditDetail, fetchTechAuditView, type TechAuditViewParams } from "../../api/client";
import { HelpTooltip } from "../../components/HelpTooltip";
import { Drawer } from "../../components/Drawer";
import { ProgressiveLoadingStatus, ProgressiveSkeletonRows, type SkeletonColumn } from "../../components/ProgressiveLoading";
import { StatusPill } from "../../components/StatusPill";
import { ColumnPicker, Pagination, SearchField, useStoredColumns } from "../../components/WorkbenchControls";
import type { TechAuditDataset, TechAuditDetailResponse, TechAuditHistoryRecord, TechAuditViewColumn, TechAuditViewRow } from "../../api/types";
import { useDebouncedValue, useViewData } from "../../hooks/useWorkbenchData";
import styles from "./TechnicalAuditViewer.module.css";

type TechnicalAuditViewerProps = {
  id?: string;
  initialDataset?: TechAuditDataset;
  initialKey?: string | null;
  initialRuleId?: string | null;
  initialTemplate?: string | null;
  projectId: string;
  crawlRunning: boolean;
  refreshKey: number;
  history: TechAuditHistoryRecord[];
  totalHint?: number;
  onDeleteRun: (runId: string) => Promise<boolean>;
  onRecrawl: (urls: string[]) => Promise<void>;
};

const tabs: Array<{ id: TechAuditDataset; label: string }> = [
  { id: "pages", label: "URL Inventory" },
  { id: "links", label: "Link Inventory" },
  { id: "issues", label: "Issues" },
];

const sortOptions: Record<TechAuditDataset, Array<{ id: string; label: string }>> = {
  pages: [
    { id: "url", label: "URL" },
    { id: "status_code", label: "Status" },
    { id: "priority", label: "Priority" },
    { id: "response_time_ms", label: "Response time" },
    { id: "crawl_depth", label: "Crawl depth" },
    { id: "inlink_count", label: "Inlinks" },
    { id: "outlink_count", label: "Outlinks" },
    { id: "title", label: "Title" },
  ],
  links: [
    { id: "url", label: "URL" },
    { id: "status_code", label: "Status" },
    { id: "source_count", label: "Sources" },
    { id: "host_relation", label: "Host relation" },
  ],
  issues: [
    { id: "priority", label: "Priority" },
    { id: "severity", label: "Severity" },
    { id: "url", label: "URL" },
    { id: "rule_id", label: "Rule" },
    { id: "click_delta", label: "Click change" },
    { id: "title", label: "Issue" },
  ],
};

const defaultFilters = { status: "", indexability: "", host_relation: "", rule_id: "", template: "", category: "", severity: "", priority_tier: "" };
type FilterState = typeof defaultFilters;
const filtersForDataset = (dataset: TechAuditDataset): FilterState => dataset === "links" ? { ...defaultFilters, host_relation: "site_family" } : defaultFilters;

const datasetHelp: Record<TechAuditDataset, string> = {
  pages: "One row per crawled URL with HTTP status, indexability, metadata, performance, and link totals.",
  links: "One row per linked URL relationship, grouped by source count and host relationship. Use it to inspect link discovery, not page metadata.",
  issues: "One row per detected technical issue or rule hit, grouped by severity and priority.",
};

const datasetLabels: Record<TechAuditDataset, string> = { pages: "URLs", links: "links", issues: "issues" };
const skeletonColumns: Record<TechAuditDataset, SkeletonColumn[]> = {
  pages: [{ id: "url", width: "48%" }, { id: "status", width: "14%" }, { id: "indexability", width: "18%" }, { id: "title", width: "28%" }],
  links: [{ id: "url", width: "48%" }, { id: "status", width: "14%" }, { id: "sources", width: "18%" }, { id: "host", width: "28%" }],
  issues: [{ id: "priority", width: "18%" }, { id: "severity", width: "18%" }, { id: "url", width: "46%" }, { id: "rule", width: "28%" }],
};

function stringify(value: unknown, max = 120): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "object") {
    if (Array.isArray(value)) return value.map((item) => stringify(item, max)).join(", ") || "—";
    const record = value as Record<string, unknown>;
    return stringify(record.status ?? record.value ?? JSON.stringify(record), max);
  }
  const result = String(value);
  return result.length > max ? `${result.slice(0, max - 1)}…` : result;
}

function cellValue(row: TechAuditViewRow, column: TechAuditViewColumn): string {
  const value = row[column.id];
  if (column.id === "indexability") return stringify((value as Record<string, unknown> | undefined)?.status);
  if (column.id === "response_time_ms" && value !== null && value !== undefined) return `${String(value)} ms`;
  if (column.id === "response_size" && value !== null && value !== undefined) return `${String(value)} B`;
  if (column.id === "h1" || column.id === "h2") return stringify(value, 80);
  if (column.id === "priority" && typeof value === "number") return value.toFixed(1);
  return stringify(value);
}

function filterParams(filters: FilterState): Omit<TechAuditViewParams, "dataset" | "limit" | "offset"> {
  return Object.fromEntries(Object.entries(filters).filter(([, value]) => value)) as Omit<TechAuditViewParams, "dataset" | "limit" | "offset">;
}

function detailLabel(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function DetailValue({ value, depth = 0 }: { value: unknown; depth?: number }): ReactNode {
  if (value === null || value === undefined || value === "") return <span className={styles.valueEmpty}>—</span>;
  if (depth >= 3) return <span>{stringify(value, 240)}</span>;
  if (Array.isArray(value)) {
    return value.length ? <div className={styles.valueList}>{value.map((item, index) => <div className={styles.valueListItem} key={`${index}-${stringify(item, 40)}`}><DetailValue value={item} depth={depth + 1} /></div>)}</div> : <span className={styles.valueEmpty}>—</span>;
  }
  if (typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>);
    return entries.length ? <div className={styles.valueObject}>{entries.map(([key, nestedValue]) => <div className={styles.valueObjectRow} key={key}><span className={styles.valueObjectKey}>{detailLabel(key)}</span><span className={styles.valueObjectValue}><DetailValue value={nestedValue} depth={depth + 1} /></span></div>)}</div> : <span className={styles.valueEmpty}>—</span>;
  }
  return <span>{stringify(value, 240)}</span>;
}

function DetailList({ items }: { items: Array<[string, unknown]> }) {
  return (
    <dl className={styles.detailList}>
      {items.map(([label, value]) => <div key={label}><dt>{label}</dt><dd><DetailValue value={value} /></dd></div>)}
    </dl>
  );
}

const headingLevels = ["h1", "h2", "h3", "h4", "h5", "h6"] as const;
type HeadingLevel = typeof headingLevels[number];

function headingValues(row: TechAuditViewRow, level: HeadingLevel): string[] {
  const value = row[level];
  if (Array.isArray(value)) return value.map((item) => stringify(item, 240)).filter((item) => item !== "—");
  const text = stringify(value, 240);
  return text === "—" ? [] : [text];
}

function headingLevelClass(level: HeadingLevel) {
  return styles[`headingLevel${level.slice(1)}` as keyof typeof styles];
}

function HeadingOutline({ row }: { row: TechAuditViewRow }) {
  const [search, setSearch] = useState("");
  const headings = headingLevels.flatMap((level) => headingValues(row, level).map((text) => ({ level, text })));
  const visibleHeadings = headings.filter(({ text }) => text.toLowerCase().includes(search.trim().toLowerCase()));

  return (
    <section className={`${styles.detailSection} ${styles.headingSection}`}>
      <div className={styles.headingHeader}>
        <div><h3>Heading outline</h3><span>Page headings grouped by level</span></div>
        <strong>{headings.length} total</strong>
      </div>
      <div className={styles.headingCounts} aria-label="Heading counts">
        {headingLevels.map((level) => <span className={headingLevelClass(level)} key={level}><b>{level.toUpperCase()}</b><strong>{headingValues(row, level).length}</strong></span>)}
      </div>
      <SearchField className={styles.headingSearch} label="Search heading text" placeholder="Search heading text..." value={search} onChange={setSearch} />
      {visibleHeadings.length ? <div className={styles.headingTree} aria-label="Heading outline tree">
        {visibleHeadings.map(({ level, text }, index) => <div className={`${styles.headingNode} ${headingLevelClass(level)}`} key={`${level}-${index}-${text}`}>
          <span className={styles.headingBranch} aria-hidden="true" />
          <b>{level.toUpperCase()}</b>
          <span>{text}</span>
        </div>)}
      </div> : <p className={styles.emptyHeading}>{search ? "No matching headings." : "No headings collected for this URL."}</p>}
    </section>
  );
}

const severityRank: Record<string, number> = { low: 1, medium: 2, high: 3, critical: 4 };

function issueGroups(issues: Array<Record<string, unknown>>) {
  const groups = new Map<string, { label: string; severity: string; issues: Array<Record<string, unknown>> }>();
  for (const issue of issues) {
    const label = stringify(issue.rule_id || issue.code || issue.title || "Unknown issue");
    const key = label.toLowerCase();
    const severity = String(issue.severity || "").toLowerCase();
    const group = groups.get(key) || { label, severity, issues: [] };
    group.issues.push(issue);
    if ((severityRank[severity] || 0) > (severityRank[group.severity] || 0)) group.severity = severity;
    groups.set(key, group);
  }
  return [...groups.values()];
}

function IssueGroups({ issues }: { issues: Array<Record<string, unknown>> }) {
  const groups = issueGroups(issues);
  return <div className={styles.issueGroups}>
    <p className={styles.issueGroupsSummary}>{issues.length} occurrences across {groups.length} rules</p>
    {groups.map((group) => {
      const guidance = [...new Set(group.issues.map((issue) => String(issue.remediation_guidance || "").trim()).filter(Boolean))];
      return <details className={styles.issueGroup} key={group.label}>
        <summary className={styles.issueGroupSummary}>
          <span className={styles.issueGroupTitle}><strong>{group.label}</strong><span>{group.issues.length} {group.issues.length === 1 ? "occurrence" : "occurrences"}</span></span>
          <StatusPill value={group.severity} context="urgency" />
        </summary>
        {guidance.length ? <p className={styles.issueGroupGuidance}>{guidance.join(" · ")}</p> : null}
        <div className={styles.issueGroupBody}>
          {group.issues.map((issue, index) => <div className={styles.issueOccurrence} key={String(issue.fingerprint || `${group.label}-${index}`)}>
            <span className={styles.issueOccurrenceTitle}>{stringify(issue.url || issue.source_url || issue.target_url, 240)} · occurrence {index + 1}</span>
            <div className={styles.evidenceBlock}><DetailValue value={issue.evidence || {}} /></div>
          </div>)}
        </div>
      </details>;
    })}
  </div>;
}

function DetailDrawer({ detail, onClose }: { detail: TechAuditDetailResponse; onClose: () => void }) {
  const row = detail.row;
  const url = String(row.url || row.row_key);
  return (
      <Drawer label="Technical audit details" eyebrow="Row details" title={stringify(row.title || row.rule_id || "Technical audit")} url={url} onClose={onClose}>
        <section className={styles.detailSection}>
          <h3>HTTP and indexability</h3>
          <DetailList items={[["Status code", row.status_code], ["Final URL", row.final_url], ["Internal / external", row.internal_external], ["Host relation", row.host_relation], ["Content type", row.content_type], ["Response time", row.response_time_ms ? `${String(row.response_time_ms)} ms` : null], ["Response size", row.response_size ? `${String(row.response_size)} B` : null], ["Indexability", row.indexability], ["Meta robots", row.meta_robots], ["X-Robots-Tag", row.x_robots_tag]]} />
        </section>
        <section className={styles.detailSection}>
          <h3>Metadata and links</h3>
          <DetailList items={[["Title", row.title], ["Meta description", row.meta_description], ["Meta keywords", row.meta_keywords], ["Canonical", row.canonical], ["Canonical declarations", row.canonical_values], ["Hreflang", row.hreflang], ["Redirect chain", row.redirect_chain], ["Redirect loop", row.redirect_loop], ["Inlinks", row.inlinks || row.inlink_count], ["Outlinks", row.outlinks || row.outlink_count], ["Anchor text", row.anchor_text], ["Rel", row.rel]]} />
        </section>
        <HeadingOutline row={row} />
        <section className={styles.detailSection}>
          <h3>Search performance</h3>
          <DetailList items={[["Clicks", row.gsc_clicks], ["Impressions", row.gsc_impressions], ["Click change", row.click_delta], ["Priority", row.priority], ["Priority tier", row.priority_tier]]} />
        </section>
        <section className={styles.detailSection}>
          <h3>Rule hits</h3>
          {detail.issues.length ? <IssueGroups issues={detail.issues} /> : <p className={styles.muted}>No current issue hit for this row.</p>}
        </section>
        <section className={styles.detailSection}>
          <h3>History</h3>
          <DetailList items={[["Latest manual re-crawl", detail.recrawl], ["Diff comparable", detail.diff.comparable], ["Issue / priority changes", detail.diff.changes]]} />
        </section>
      </Drawer>
  );
}

export function TechnicalAuditViewer({ id, initialDataset = "pages", initialKey, initialRuleId, initialTemplate, projectId, crawlRunning, refreshKey, history, totalHint, onDeleteRun, onRecrawl }: TechnicalAuditViewerProps) {
  const [dataset, setDataset] = useState<TechAuditDataset>(initialDataset);
  const [filters, setFilters] = useState<FilterState>(() => ({ ...filtersForDataset(initialDataset), rule_id: initialRuleId || "", template: initialTemplate || "" }));
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState("url");
  const [direction, setDirection] = useState<"asc" | "desc">("asc");
  const [pageSize, setPageSize] = useState(50);
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [detail, setDetail] = useState<TechAuditDetailResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [runId, setRunId] = useState("");
  const debouncedSearch = useDebouncedValue(search);

  const params = useMemo<TechAuditViewParams>(() => ({ dataset, run_id: runId || undefined, q: debouncedSearch, ...filterParams(filters), sort, direction, limit: pageSize, offset }), [dataset, runId, debouncedSearch, filters, sort, direction, pageSize, offset]);
  const { data, error, loading, setData, setError } = useViewData(projectId, params, refreshKey, fetchTechAuditView);
  const { toggle: toggleColumn, visible: visibleIds } = useStoredColumns(`tech-audit-columns:${projectId}:${dataset}`, data?.columns);
  const visibleColumns = data?.columns.filter((column) => visibleIds.includes(column.id)) || [];
  const tableColumns = visibleColumns.length ? visibleColumns : skeletonColumns[dataset];
  const selectedVisible = data?.rows.filter((row) => selected.has(row.row_key)).length || 0;

  useEffect(() => {
    setDataset(initialDataset);
    setFilters({ ...filtersForDataset(initialDataset), rule_id: initialRuleId || "", template: initialTemplate || "" });
    setSearch("");
    setSort("url");
    setDirection("asc");
    setOffset(0);
  }, [initialDataset, initialRuleId, initialTemplate]);

  useEffect(() => {
    if (runId && !history.some((item) => item.run_id === runId)) setRunId("");
  }, [history, runId]);

  useEffect(() => {
    if (!initialKey) return;
    let cancelled = false;
    setDetailLoading(true);
    fetchTechAuditDetail(projectId, initialDataset, initialKey, runId)
      .then((value) => { if (!cancelled) setDetail(value); })
      .catch((reason: Error) => { if (!cancelled) setError(reason.message); })
      .finally(() => { if (!cancelled) setDetailLoading(false); });
    return () => { cancelled = true; };
  }, [projectId, initialDataset, initialKey, runId, refreshKey]);

  const changeDataset = (next: TechAuditDataset) => {
    setDataset(next);
    setOffset(0);
    setSearch("");
    setFilters(filtersForDataset(next));
    setSort("url");
    setDirection("asc");
    setDetail(null);
  };

  const changeRun = (next: string) => {
    setRunId(next);
    setOffset(0);
    setSelected(new Set());
    setDetail(null);
  };

  const updateFilter = (key: keyof FilterState, value: string) => {
    setFilters((current) => ({ ...current, [key]: value }));
    setOffset(0);
  };

  const loadDetail = (row: TechAuditViewRow) => {
    setDetailLoading(true);
    fetchTechAuditDetail(projectId, dataset, row.row_key, runId)
      .then(setDetail)
      .catch((reason: Error) => setError(reason.message))
      .finally(() => setDetailLoading(false));
  };

  const selectFiltered = async () => {
    if (!data || data.pagination.total > 1_000) { setError("Select filtered is limited to 1,000 rows."); return; }
    setError(null);
    const keys: string[] = [];
    for (let currentOffset = 0; currentOffset < data.pagination.total; currentOffset += 200) {
      const page = await fetchTechAuditView(projectId, { ...params, limit: 200, offset: currentOffset });
      keys.push(...page.rows.map((row) => row.row_key));
    }
    setSelected(new Set(keys));
  };

  const recrawlSelected = () => {
    if (selected.size === 0 || selected.size > 1_000 || crawlRunning) return;
    void onRecrawl([...selected]).then(() => setSelected(new Set())).catch((reason: Error) => setError(reason.message));
  };

  const deleteSelectedRun = () => {
    const target = runId || data?.snapshot.run_id || "";
    const record = history.find((item) => item.run_id === target);
    if (!target || !record || record.active || !record.snapshot_available) return;
    void onDeleteRun(target).then((deleted) => {
      if (deleted) {
        setRunId("");
        setData(null);
        setDetail(null);
        setSelected(new Set());
      }
    }).catch((reason: Error) => setError(reason.message));
  };

  const selectPage = () => {
    const keys = data?.rows.map((row) => row.row_key) || [];
    setSelected((current) => new Set([...current, ...keys].slice(0, 1_000)));
  };

  const openRow = (row: TechAuditViewRow) => {
    if (!row.row_key) return;
    loadDetail(row);
  };

  return (
    <section id={id} className={styles.viewer} aria-labelledby="inventory-viewer-heading">
      <div className={styles.viewerHeading}><div><span className={styles.eyebrow}>Audit history</span><h2 id="inventory-viewer-heading">Technical audit viewer</h2></div><div className={styles.historyControls}><label className={styles.compactControl}><span>Run</span><select value={runId} onChange={(event) => changeRun(event.target.value)}><option value="">Latest</option>{history.map((item) => <option key={item.run_id} value={item.run_id} disabled={item.active || !item.snapshot_available}>{item.run_id} · {item.status}</option>)}</select></label><button className={styles.toolbarButton} type="button" onClick={deleteSelectedRun} disabled={!history.some((item) => item.run_id === (runId || data?.snapshot.run_id || "") && !item.active && item.snapshot_available)}><Trash2 size={14} />Delete run</button><span className={styles.snapshot}>{data?.snapshot.generated_at ? new Date(data.snapshot.generated_at).toLocaleString() : "No snapshot"}</span></div></div>
      <div className={styles.tabs} role="tablist" aria-label="Technical audit datasets">
        {tabs.map((tab) => <button key={tab.id} className={dataset === tab.id ? styles.activeTab : styles.tab} type="button" role="tab" aria-label={tab.label} aria-selected={dataset === tab.id} onClick={() => changeDataset(tab.id)}>{tab.label}<HelpTooltip label={tab.label}>{datasetHelp[tab.id]}</HelpTooltip></button>)}
      </div>
      <div className={styles.toolbar}>
        <SearchField label="Search technical audit" value={search} onChange={(value) => { setSearch(value); setOffset(0); }} placeholder={dataset === "issues" ? "Search URL, rule or remediation" : "Search URL or metadata"} />
        <label className={styles.compactControl}><span>Sort</span><select value={sort} onChange={(event) => { setSort(event.target.value); setOffset(0); }}>{sortOptions[dataset].map((option) => <option key={option.id} value={option.id}>{option.label}</option>)}</select></label>
        <button className={styles.toolbarButton} type="button" onClick={() => { setDirection((current) => current === "asc" ? "desc" : "asc"); setOffset(0); }} aria-label={`Sort ${direction === "asc" ? "descending" : "ascending"}`}>{direction === "asc" ? <ArrowDown size={14} /> : <ArrowUp size={14} />} {direction === "asc" ? "Asc" : "Desc"}</button>
        <ColumnPicker columns={data?.columns} visible={visibleIds} onToggle={toggleColumn} />
      </div>
      <div className={styles.filterBar}>
        <Filter size={14} aria-hidden="true" />
        {dataset !== "issues" ? <label><span>Status</span><input value={filters.status} onChange={(event) => updateFilter("status", event.target.value)} placeholder="200,404" /></label> : null}
        {dataset !== "issues" ? <label><span>Indexability</span><select value={filters.indexability} onChange={(event) => updateFilter("indexability", event.target.value)}><option value="">All</option><option value="indexable">Indexable</option><option value="noindex">Noindex</option><option value="not_crawled">Not crawled</option></select></label> : null}
        {dataset !== "pages" ? <label><span>Host</span><select value={filters.host_relation} onChange={(event) => updateFilter("host_relation", event.target.value)}><option value="site_family">Site family</option><option value="same_host">Same host</option><option value="subdomain">Subdomain</option><option value="external">External</option><option value="all">All hosts</option></select></label> : null}
        {dataset === "issues" ? <><label><span>Rule</span><input value={filters.rule_id} onChange={(event) => updateFilter("rule_id", event.target.value)} placeholder="HTTP_4XX" /></label><label><span>Template</span><input value={filters.template} onChange={(event) => updateFilter("template", event.target.value)} placeholder="product" /></label><label><span>Category</span><input value={filters.category} onChange={(event) => updateFilter("category", event.target.value)} placeholder="metadata" /></label><label><span>Severity</span><select value={filters.severity} onChange={(event) => updateFilter("severity", event.target.value)}><option value="">All</option><option value="critical">Critical</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select></label><label><span>Priority</span><select value={filters.priority_tier} onChange={(event) => updateFilter("priority_tier", event.target.value)}><option value="">All</option><option value="critical">Critical</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select></label></> : null}
      </div>
      <ProgressiveLoadingStatus loading={loading && !error} complete={Boolean(data && !loading)} label={datasetLabels[dataset]} total={dataset === "pages" ? totalHint || data?.pagination.total : data?.pagination.total} />
      {error ? <p className={styles.error} role="alert">{error}</p> : null}
      {dataset === "pages" ? <div className={styles.selectionBar}><span><strong>{selected.size}</strong> selected</span><button type="button" className={styles.linkButton} onClick={selectPage} disabled={!data?.rows.length || selected.size >= 1_000}><CheckSquare size={14} />Select current page</button><button type="button" className={styles.linkButton} onClick={() => void selectFiltered()} disabled={!data?.pagination.total || data.pagination.total > 1_000}><CheckSquare size={14} />Select filtered</button>{selected.size ? <button type="button" className={styles.linkButton} onClick={() => setSelected(new Set())}>Clear</button> : null}<button type="button" className={styles.recrawlButton} onClick={recrawlSelected} disabled={crawlRunning || selected.size === 0}><RotateCcw size={14} />Re-crawl selected</button></div> : null}
      <div className={styles.tableScroll} aria-busy={loading}>
        <table className={styles.inventoryTable}>
          <thead><tr>{dataset === "pages" ? <th className={styles.selectColumn} aria-label="Selection" /> : null}{tableColumns.map((column) => <th key={column.id}>{column.label || column.id}</th>)}</tr></thead>
          <tbody>
            {loading && !data ? <ProgressiveSkeletonRows columns={tableColumns} /> : data?.rows.map((row) => <tr key={row.row_key} className={selected.has(row.row_key) ? styles.selectedRow : undefined} onClick={() => openRow(row)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); openRow(row); } }} tabIndex={0} aria-selected={selected.has(row.row_key)}>
              {dataset === "pages" ? <td className={styles.selectColumn} onClick={(event) => event.stopPropagation()}><input type="checkbox" aria-label={`Select ${row.url || row.row_key}`} checked={selected.has(row.row_key)} onChange={() => setSelected((current) => { const next = new Set(current); if (next.has(row.row_key)) next.delete(row.row_key); else if (next.size < 1_000) next.add(row.row_key); return next; })} /></td> : null}
              {visibleColumns.map((column) => <td key={column.id} className={column.id === "url" ? styles.urlColumn : undefined} title={stringify(row[column.id], 400)}>{column.id === "url" ? <span>{cellValue(row, column)} <ExternalLink size={12} aria-hidden="true" /></span> : column.id === "status_code" ? <StatusPill value={row[column.id]} context="http" /> : ["severity", "priority_tier"].includes(column.id) ? <StatusPill value={row[column.id]} context="urgency" /> : cellValue(row, column)}</td>)}
            </tr>)}
          </tbody>
        </table>
        {!loading && !data?.rows.length ? <div className={styles.empty}><Search size={20} /><strong>No rows match these filters.</strong><span>Try a broader query or run a fresh crawl.</span></div> : null}
      </div>
      <Pagination offset={offset} limit={pageSize} total={data?.pagination.total || 0} loading={loading} onOffsetChange={setOffset} onLimitChange={(value) => { setPageSize(value); setOffset(0); }} />
      {detailLoading ? <div className={styles.detailLoading} role="status">Loading details…</div> : null}
      {detail ? <DetailDrawer detail={detail} onClose={() => setDetail(null)} /> : null}
    </section>
  );
}
