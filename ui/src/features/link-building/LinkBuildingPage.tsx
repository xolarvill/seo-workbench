import { ArrowDown, ArrowUp, Filter, Search } from "lucide-react";
import { useMemo, useState, type ReactNode } from "react";

import { fetchBacklinkView, type BacklinkViewParams } from "../../api/client";
import { HelpTooltip } from "../../components/HelpTooltip";
import { ProgressiveLoadingStatus, ProgressiveSkeletonCard, ProgressiveSkeletonRows, type SkeletonColumn } from "../../components/ProgressiveLoading";
import { StatusPill } from "../../components/StatusPill";
import { Pagination, SearchField, pageLabel } from "../../components/WorkbenchControls";
import type { BacklinkViewRow } from "../../api/types";
import { useDebouncedValue, useViewData } from "../../hooks/useWorkbenchData";
import styles from "./LinkBuildingPage.module.css";

type Props = { projectId: string; refreshKey: number };

const skeletonColumns: SkeletonColumn[] = [
  { id: "source_domain", width: "28%" },
  { id: "source_url", width: "34%" },
  { id: "target_url", width: "34%" },
  { id: "provider_status", width: "18%" },
  { id: "target_status_code", width: "16%" },
];

const sortOptions = [
  ["source_domain", "Referring domain"],
  ["provider_status", "Status"],
  ["target_url", "Target URL"],
  ["target_status_code", "Target HTTP"],
  ["follow", "Follow"],
] as const;

function valueLabel(value: unknown, fallback = "—") {
  return value === null || value === undefined || value === "" ? fallback : String(value);
}

function numberLabel(value: unknown) {
  return typeof value === "number" ? value.toLocaleString() : "—";
}

function followLabel(value: boolean | null) {
  return value === true ? "follow" : value === false ? "nofollow" : "unknown";
}

function Card({ title, subtitle, children }: { title: string; subtitle?: ReactNode; children: ReactNode }) {
  return <section className={styles.card}><header className={styles.cardHeader}><h2>{title}</h2>{subtitle ? <span>{subtitle}</span> : null}</header><div className={styles.cardBody}>{children}</div></section>;
}

function linkCell(row: BacklinkViewRow, id: string) {
  if (id === "source_url" || id === "target_url") {
    const value = row[id];
    return <a href={value} target="_blank" rel="noreferrer" title={value}>{value}</a>;
  }
  if (id === "provider_status") return <StatusPill value={row.provider_status} context="evidence" tone={row.provider_status === "active" ? "success" : "danger"} />;
  if (id === "follow") return <StatusPill value={followLabel(row.follow)} context="evidence" />;
  if (id === "target_status_code") return row.target_status_code ? <StatusPill value={row.target_status_code} context="http" /> : <span className={styles.notObserved}>Not observed</span>;
  if (id === "target_reclaim_candidate") return row.target_reclaim_candidate ? <StatusPill value="candidate" tone="warning" /> : <span className={styles.notObserved}>No</span>;
  return valueLabel(row[id as keyof BacklinkViewRow]);
}

export function LinkBuildingPage({ projectId, refreshKey }: Props) {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [follow, setFollow] = useState("");
  const [reclaimOnly, setReclaimOnly] = useState(false);
  const [sort, setSort] = useState<BacklinkViewParams["sort"]>("source_domain");
  const [direction, setDirection] = useState<"asc" | "desc">("asc");
  const [pageSize, setPageSize] = useState(50);
  const [offset, setOffset] = useState(0);
  const debouncedQuery = useDebouncedValue(query);
  const params = useMemo<BacklinkViewParams>(() => ({ q: debouncedQuery, status, follow, reclaim_only: reclaimOnly, sort, direction, limit: pageSize, offset }), [debouncedQuery, status, follow, reclaimOnly, sort, direction, pageSize, offset]);
  const { data, error, loading } = useViewData(projectId, params, refreshKey, fetchBacklinkView);

  const summary = data?.summary || {};
  const comparison = data?.comparison || {};
  const columns = data?.columns.filter((column) => column.default) || skeletonColumns;
  const hasSnapshot = data?.collection_status !== "not_collected";
  const clearFilters = () => { setQuery(""); setStatus(""); setFollow(""); setReclaimOnly(false); setOffset(0); };

  return (
    <section className={styles.page} aria-labelledby="link-building-heading" aria-busy={loading}>
      <header className={styles.header}>
        <div><span>External link evidence</span><h1 id="link-building-heading">Link building</h1><p>Manage provider-scoped backlink evidence, link changes and safe reclaim candidates.</p></div>
        <HelpTooltip label="Backlink evidence" align="right">Read-only view of the latest local backlink snapshot. Import or recheck evidence with the existing backlinks CLI workflow.</HelpTooltip>
      </header>

      <ProgressiveLoadingStatus loading={loading && !error} complete={Boolean(data && !loading)} label="backlink records" total={data?.pagination.total} />
      {error ? <p className={styles.error} role="alert">{error}</p> : null}
      {!data && loading ? <div className={styles.loadingGrid} aria-hidden="true">{Array.from({ length: 4 }, (_, index) => <ProgressiveSkeletonCard key={index} />)}</div> : null}

      {data ? <>
        <div className={styles.summaryGrid}>
          <Card title="Collection status" subtitle={<StatusPill value={data.collection_status} context="evidence" />}>
            <strong className={styles.metric}>{valueLabel(data.source?.name, "No provider")}</strong>
            <span className={styles.meta}>{data.collection_status === "not_collected" ? "No snapshot" : data.complete_snapshot ? "Complete snapshot" : "Partial snapshot"} · {valueLabel(data.captured_at, "No capture time")}</span>
          </Card>
          <Card title="Active links" subtitle="latest snapshot">
            <strong className={styles.metric}>{numberLabel(summary.active_links)}</strong>
            <span className={styles.meta}>{numberLabel(summary.links)} total records · {numberLabel(summary.referring_domains)} referring domains</span>
          </Card>
          <Card title="Target coverage" subtitle="active links">
            <strong className={styles.metric}>{numberLabel(summary.target_pages)}</strong>
            <span className={styles.meta}>{numberLabel(summary.target_reclaim_candidates)} reclaim candidates from 404/410 evidence</span>
          </Card>
          <Card title="Snapshot comparison" subtitle={<StatusPill value={valueLabel(comparison.status, "no baseline")} context="evidence" />}>
            <div className={styles.comparisonNumbers}><span><strong>{Array.isArray(comparison.new_observed) ? comparison.new_observed.length : 0}</strong> new</span><span><strong>{Array.isArray(comparison.lost) ? comparison.lost.length : 0}</strong> lost</span><span><strong>{Array.isArray(comparison.missing_unconfirmed) ? comparison.missing_unconfirmed.length : 0}</strong> unconfirmed</span></div>
            <span className={styles.meta}>{comparison.comparable === true ? "Same-source complete snapshots are comparable." : "Missing links stay unconfirmed until both same-source snapshots are complete."}</span>
          </Card>
        </div>

        <div className={styles.contextGrid}>
          <Card title="Top anchors" subtitle="active links">
            {data.top_anchors.length ? <div className={styles.anchorList}>{data.top_anchors.slice(0, 8).map((item) => <div key={item.anchor}><span title={item.anchor}>{item.anchor}</span><strong>{item.count.toLocaleString()}</strong></div>)}</div> : <p className={styles.empty}>No anchor text observed.</p>}
          </Card>
          <Card title="Evidence boundary" subtitle="read-only">
            <p className={styles.note}>Authority and toxicity scores are not calculated. Reclaim candidates only describe active links pointing to known 404/410 targets; they do not publish redirects or outreach.</p>
          </Card>
        </div>

        <section className={styles.viewer} aria-labelledby="backlink-records-heading">
          <header className={styles.viewerHeader}><div><span>Provider snapshot</span><h2 id="backlink-records-heading">Backlink records</h2></div><span className={styles.resultCount}>{pageLabel(offset, pageSize, data.pagination.total)}</span></header>
          <div className={styles.toolbar}>
            <SearchField label="Search backlinks" value={query} onChange={(value) => { setQuery(value); setOffset(0); }} placeholder="Search domain, URL or anchor" />
            <label><span>Status</span><select value={status} onChange={(event) => { setStatus(event.target.value); setOffset(0); }}><option value="">All</option><option value="active">Active</option><option value="lost">Lost</option></select></label>
            <label><span>Follow</span><select value={follow} onChange={(event) => { setFollow(event.target.value); setOffset(0); }}><option value="">All</option><option value="follow">Follow</option><option value="nofollow">Nofollow</option><option value="unknown">Unknown</option></select></label>
            <label className={styles.check}><input type="checkbox" checked={reclaimOnly} onChange={(event) => { setReclaimOnly(event.target.checked); setOffset(0); }} /><span>Reclaim candidates</span></label>
            <label><span>Sort</span><select value={sort} onChange={(event) => { setSort(event.target.value); setOffset(0); }}>{sortOptions.map(([id, label]) => <option value={id} key={id}>{label}</option>)}</select></label>
            <button className={styles.directionButton} type="button" onClick={() => { setDirection((value) => value === "asc" ? "desc" : "asc"); setOffset(0); }}>{direction === "asc" ? <ArrowDown size={14} /> : <ArrowUp size={14} />}{direction === "asc" ? "Asc" : "Desc"}</button>
            {(query || status || follow || reclaimOnly) ? <button className={styles.clearButton} type="button" onClick={clearFilters}><Filter size={14} />Clear</button> : null}
          </div>
          <div className={styles.tableScroll} aria-busy={loading}>
            <table><thead><tr>{columns.map((column) => <th key={column.id}>{column.label}</th>)}</tr></thead><tbody>{loading && !data?.rows.length ? <ProgressiveSkeletonRows columns={skeletonColumns} /> : data.rows.map((row) => <tr key={row.id}>{columns.map((column) => <td key={column.id} className={column.id.endsWith("url") ? styles.urlColumn : undefined}>{linkCell(row, column.id)}</td>)}</tr>)}</tbody></table>
            {!loading && !data.rows.length ? <div className={styles.empty}><Search size={22} /><strong>{hasSnapshot ? "No backlinks match this view." : "No backlink snapshot collected."}</strong><span>{hasSnapshot ? "Broaden the filters or import a newer provider snapshot." : "Import a provider snapshot with the existing backlinks CLI workflow."}</span></div> : null}
          </div>
          <Pagination offset={offset} limit={pageSize} total={data.pagination.total} loading={loading} onOffsetChange={setOffset} onLimitChange={(value) => { setPageSize(value); setOffset(0); }} />
        </section>
      </> : null}
    </section>
  );
}
