import { useMemo, useState } from "react";

import { HelpTooltip } from "../../components/HelpTooltip";
import { StatusPill } from "../../components/StatusPill";
import { SearchField } from "../../components/WorkbenchControls";
import type { SeoChangeRecord } from "../../api/types";
import { useSeoChanges } from "../../hooks/useWorkbenchData";
import styles from "./SeoChangesSection.module.css";

const changeTypes: Array<{ value: SeoChangeRecord["change_type"] | ""; label: string }> = [
  { value: "", label: "All types" },
  { value: "content", label: "Content SEO" },
  { value: "internal_links", label: "Internal links" },
  { value: "metadata", label: "Metadata" },
  { value: "performance", label: "Performance" },
  { value: "redirect", label: "Redirect" },
  { value: "schema", label: "Schema" },
  { value: "technical", label: "Technical" },
  { value: "other", label: "Other" },
];

const statuses: Array<{ value: SeoChangeRecord["status"] | ""; label: string }> = [
  { value: "", label: "All statuses" },
  { value: "planned", label: "Planned" },
  { value: "shipped", label: "Shipped" },
  { value: "reviewed", label: "Reviewed" },
  { value: "cancelled", label: "Cancelled" },
];

function formatDate(value: string | undefined) {
  if (!value) return "Not observed";
  const [year, month, day] = value.split("-").map(Number);
  return year && month && day ? new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short", year: "numeric" }).format(new Date(year, month - 1, day)) : value;
}

function urlLabel(value: string) {
  try {
    const url = new URL(value);
    return `${url.hostname}${url.pathname}`;
  } catch {
    return value;
  }
}

function typeLabel(value: SeoChangeRecord["change_type"]) {
  return changeTypes.find((item) => item.value === value)?.label || value.replaceAll("_", " ");
}

function ChangeCard({ change }: { change: SeoChangeRecord }) {
  const urls = change.urls || [];
  const updates = change.updates || [];
  return (
    <article className={styles.changeCard}>
      <div className={styles.timelineRail} aria-hidden="true"><time>{formatDate(change.changed_at)}</time><span data-status={change.status} /></div>
      <div className={styles.changeBody}>
        <header className={styles.changeHeader}>
          <div><span className={styles.type}>{typeLabel(change.change_type)}</span><h2>{change.hypothesis}</h2><code>{change.id}</code></div>
          <StatusPill value={change.status} context="status" />
        </header>
        <div className={styles.meta}><span>Changed {formatDate(change.changed_at)}</span><span>Review {formatDate(change.review_date)}</span></div>
        <dl className={styles.details}>
          <div><dt>Expected metrics</dt><dd><span className={styles.chips}>{(change.expected_metrics || []).map((metric) => <span key={metric}>{metric}</span>)}</span></dd></div>
          <div><dt>Pages</dt><dd className={styles.urls}>{urls.slice(0, 3).map((url) => <span key={url} title={url}>{urlLabel(url)}</span>)}{urls.length > 3 ? <span>+ {urls.length - 3} more</span> : null}</dd></div>
        </dl>
        {change.note ? <p className={styles.note}>{change.note}</p> : null}
        {updates.length ? <p className={styles.update}>Last status update {formatDate(updates[updates.length - 1].updated_at?.slice(0, 10))}: {updates[updates.length - 1].note || "status changed"}</p> : null}
      </div>
    </article>
  );
}

export function SeoChangesSection({ projectId, refreshKey }: { projectId: string; refreshKey: number }) {
  const { data, error } = useSeoChanges(projectId, refreshKey);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<SeoChangeRecord["status"] | "">("");
  const [changeType, setChangeType] = useState<SeoChangeRecord["change_type"] | "">("");
  const changes = data?.changes || [];
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return changes.filter((change) => {
      if (status && change.status !== status) return false;
      if (changeType && change.change_type !== changeType) return false;
      if (!needle) return true;
      return [change.id, change.hypothesis, change.note, ...change.urls].join(" ").toLowerCase().includes(needle);
    });
  }, [changes, changeType, query, status]);
  const counts = useMemo(() => changes.reduce<Record<string, number>>((result, change) => { result[change.status] = (result[change.status] || 0) + 1; return result; }, {}), [changes]);

  return (
    <section className={styles.page} aria-labelledby="seo-changes-heading">
      <h1 id="seo-changes-heading" className="srOnly">SEO changes</h1>
      {error ? <p className={styles.error} role="alert">{error}</p> : null}
      {!data ? <p className={styles.empty}>Loading SEO changes…</p> : (
        <>
          <div className={styles.summary} aria-label="SEO change summary">
            <div><span>Total</span><strong>{data.count}</strong></div>
            <div><span>Open</span><strong>{(counts.planned || 0) + (counts.shipped || 0)}</strong></div>
            <div><span>Reviewed</span><strong>{counts.reviewed || 0}</strong></div>
          </div>
          <div className={styles.filters}>
            <SearchField label="Search SEO changes" placeholder="Search hypothesis, URL, or ID…" value={query} onChange={setQuery} />
            <label><span>Status</span><select aria-label="Filter SEO changes by status" value={status} onChange={(event) => setStatus(event.target.value as SeoChangeRecord["status"] | "")} >{statuses.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
            <label><span>Type</span><select aria-label="Filter SEO changes by type" value={changeType} onChange={(event) => setChangeType(event.target.value as SeoChangeRecord["change_type"] | "")} >{changeTypes.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
            <HelpTooltip label="SEO change scope">This view reads strategy/seo-changes.jsonl. It is a read-only ledger; it does not publish, redirect, or change content.</HelpTooltip>
            <small className={styles.resultCount}>{filtered.length} of {data.count}</small>
          </div>
          {filtered.length ? <div className={styles.timeline} aria-label="SEO changes timeline">{filtered.map((change) => <ChangeCard key={change.id} change={change} />)}</div> : <p className={styles.empty}>No SEO changes match the current filters.</p>}
        </>
      )}
    </section>
  );
}
