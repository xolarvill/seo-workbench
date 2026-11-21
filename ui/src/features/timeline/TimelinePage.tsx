import { ArrowUpRight, GitCommitVertical, ListFilter, LockKeyhole, X } from "lucide-react";
import { useMemo, useState } from "react";

import type { SeoChangeRecord } from "../../api/types";
import { StatusPill, statusLabel } from "../../components/StatusPill";
import { SearchField } from "../../components/WorkbenchControls";
import { Sheet, SheetClose, SheetContent, SheetDescription, SheetTitle } from "../../components/ui/sheet";
import { useSeoChanges } from "../../hooks/useWorkbenchData";
import { cn } from "../../lib/utils";
import styles from "./TimelinePage.module.css";

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

const statusFilters: Array<{ value: SeoChangeRecord["status"] | ""; label: string }> = [
  { value: "", label: "All" },
  { value: "planned", label: "Planned" },
  { value: "shipped", label: "Shipped" },
  { value: "reviewed", label: "Reviewed" },
  { value: "cancelled", label: "Cancelled" },
];

function parseDate(value?: string) {
  if (!value) return null;
  const [year, month, day] = value.split("-").map(Number);
  return year && month && day ? new Date(year, month - 1, day) : null;
}

function formatDate(value?: string) {
  const date = parseDate(value);
  return date ? new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short", year: "numeric" }).format(date) : "Not set";
}

function dayOf(value?: string) {
  const date = parseDate(value);
  return date ? new Intl.DateTimeFormat("en-GB", { day: "2-digit" }).format(date) : "—";
}

function weekdayOf(value?: string) {
  const date = parseDate(value);
  return date ? new Intl.DateTimeFormat("en-GB", { weekday: "short" }).format(date).toUpperCase() : "—";
}

function monthOf(value?: string) {
  const date = parseDate(value);
  return date ? new Intl.DateTimeFormat("en-GB", { month: "long", year: "numeric" }).format(date).toUpperCase() : "UNDATED";
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

function TimelineEntry({ change, index, onOpen }: { change: SeoChangeRecord; index: number; onOpen: () => void }) {
  const urls = change.urls || [];
  const metricCount = change.expected_metrics?.length || 0;
  return (
    <li className={styles.entry} style={{ animationDelay: `${Math.min(index, 8) * 35}ms` }}>
      <time className={styles.entryDate} dateTime={change.changed_at}>
        <strong>{dayOf(change.changed_at)}</strong>
        <span>{weekdayOf(change.changed_at)}</span>
      </time>
      <span className={styles.entryNode} data-status={change.status} aria-hidden="true" />
      <button
        type="button"
        className={styles.entryCard}
        aria-haspopup="dialog"
        onClick={onOpen}
        onPointerMove={(event) => {
          const rect = event.currentTarget.getBoundingClientRect();
          event.currentTarget.style.setProperty("--mx", `${event.clientX - rect.left}px`);
          event.currentTarget.style.setProperty("--my", `${event.clientY - rect.top}px`);
        }}
      >
        <span className={styles.entryTop}>
          <span className={styles.type}>{typeLabel(change.change_type)}</span>
          <StatusPill value={change.status} context="status" />
        </span>
        <strong className={styles.entryTitle}>{change.hypothesis}</strong>
        <span className={styles.entryMeta}>
          <span className={styles.entryMobileDate}>{formatDate(change.changed_at)}</span>
          <span className={styles.entryUrl}>{urls[0] ? `${urlLabel(urls[0])}${urls.length > 1 ? ` +${urls.length - 1}` : ""}` : "No pages"}</span>
          <span className={styles.metaDot} aria-hidden="true" />
          <span>{metricCount} expected {metricCount === 1 ? "metric" : "metrics"}</span>
        </span>
        <span className={styles.entryFoot}>
          <span className={styles.entryAction}><span>Open entry</span><ArrowUpRight aria-hidden="true" size={14} /></span>
          <span className={styles.entryReview}>Review {formatDate(change.review_date)}</span>
        </span>
      </button>
    </li>
  );
}

function EntrySheet({ change, onClose }: { change: SeoChangeRecord | null; onClose: () => void }) {
  const urls = change?.urls || [];
  const updates = change?.updates || [];
  const metrics = change?.expected_metrics || [];
  return (
    <Sheet open={Boolean(change)} onOpenChange={(open) => { if (!open) onClose(); }}>
      <SheetContent side="right" className={cn(styles.sheet, "w-full gap-0 border-separator p-0 sm:max-w-[560px]")}>
        <SheetTitle className="srOnly">Timeline entry {change?.id ?? ""}</SheetTitle>
        <SheetDescription className="srOnly">Read-only record of a planned, shipped, or reviewed SEO change.</SheetDescription>
        <div className={styles.sheetBar}>
          <span className={styles.sheetKicker}>Change ledger · {change ? statusLabel(change.status) : ""}</span>
          <SheetClose asChild>
            <button type="button" className={styles.sheetClose} aria-label="Close timeline entry"><X aria-hidden="true" size={17} /></button>
          </SheetClose>
        </div>
        {change ? <div className={styles.sheetBody}>
          <header className={styles.sheetHead}>
            <span className={styles.type}>{typeLabel(change.change_type)}</span>
            <strong className={styles.sheetTitle}>{change.hypothesis}</strong>
            <div className={styles.sheetStatus}>
              <StatusPill value={change.status} context="status" />
              <code>{change.id}</code>
            </div>
          </header>
          <dl className={styles.facts}>
            <div><dt>Changed</dt><dd>{formatDate(change.changed_at)}</dd></div>
            <div><dt>Review due</dt><dd>{formatDate(change.review_date)}</dd></div>
          </dl>
          <section className={styles.block}>
            <h3>Expected metrics</h3>
            {metrics.length ? <div className={styles.chips}>{metrics.map((metric) => <span key={metric}>{metric}</span>)}</div> : <p className={styles.none}>None recorded.</p>}
          </section>
          <section className={styles.block}>
            <h3>Pages</h3>
            {urls.length ? <ul className={styles.urls}>{urls.map((url) => <li key={url}><span title={url}>{urlLabel(url)}</span></li>)}</ul> : <p className={styles.none}>No pages recorded.</p>}
          </section>
          {change.note ? <section className={styles.block}><h3>Note</h3><p className={styles.note}>{change.note}</p></section> : null}
          {updates.length ? <section className={styles.block}>
            <h3>History</h3>
            <ol className={styles.history}>
              {updates.map((update, index) => (
                <li key={`${update.updated_at || "update"}-${index}`}>
                  <span className={styles.historyDot} aria-hidden="true" />
                  <div>
                    <time>{formatDate(update.updated_at?.slice(0, 10))}</time>
                    <p>{update.note || (update.status ? `Status changed to ${update.status}.` : "Status updated.")}</p>
                  </div>
                </li>
              ))}
            </ol>
          </section> : null}
          <p className={styles.readOnly}><LockKeyhole aria-hidden="true" size={14} /> Read-only ledger. Status changes are recorded by the workspace, not from this page.</p>
        </div> : null}
      </SheetContent>
    </Sheet>
  );
}

export function TimelinePage({ projectId, refreshKey }: { projectId: string; refreshKey: number }) {
  const { data, error } = useSeoChanges(projectId, refreshKey);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<SeoChangeRecord["status"] | "">("");
  const [changeType, setChangeType] = useState<SeoChangeRecord["change_type"] | "">("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
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
  const groups = useMemo(() => {
    const byMonth = new Map<string, SeoChangeRecord[]>();
    filtered.forEach((change) => {
      const key = change.changed_at?.slice(0, 7) || "undated";
      const bucket = byMonth.get(key);
      if (bucket) bucket.push(change);
      else byMonth.set(key, [change]);
    });
    return [...byMonth.entries()];
  }, [filtered]);
  const selected = changes.find((change) => change.id === selectedId) || null;

  return (
    <section className={styles.page} aria-labelledby="timeline-heading">
      <h1 id="timeline-heading" className="srOnly">Timeline</h1>

      <div className={styles.toolbar}>
        <div className={styles.segments} role="group" aria-label="Filter timeline by status">
          {statusFilters.map((item) => (
            <button key={item.value} type="button" className={styles.segment} aria-pressed={status === item.value} onClick={() => setStatus(item.value)}>
              {item.label}
            </button>
          ))}
        </div>
        <SearchField label="Search timeline" placeholder="Search hypothesis, URL, or ID…" value={query} onChange={setQuery} />
        <label className={styles.typeFilter}>
          <span>Type</span>
          <select aria-label="Filter timeline by type" value={changeType} onChange={(event) => setChangeType(event.target.value as SeoChangeRecord["change_type"] | "")}>
            {changeTypes.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
          </select>
        </label>
        <span className={styles.resultCount}>{filtered.length} / {changes.length}</span>
      </div>

      {error ? <p className={styles.error} role="alert">{error}</p> : null}

      {!data ? <p className={styles.loading}>Loading timeline…</p> : changes.length === 0 ? (
        <div className={styles.empty}>
          <span className={styles.emptyMark}><GitCommitVertical aria-hidden="true" size={20} /></span>
          <strong>No changes recorded yet</strong>
          <p>Entries appear here when this project records a change in its SEO change ledger.</p>
        </div>
      ) : filtered.length === 0 ? (
        <div className={styles.empty}>
          <span className={styles.emptyMark}><ListFilter aria-hidden="true" size={20} /></span>
          <strong>No entries match those filters</strong>
          <button type="button" className={styles.clear} onClick={() => { setQuery(""); setStatus(""); setChangeType(""); }}>Clear filters</button>
        </div>
      ) : (
        <div className={styles.timeline} aria-label="Timeline entries">
          {groups.map(([key, entries]) => (
            <section className={styles.month} key={key}>
              <p className={styles.monthLabel}>{monthOf(entries[0].changed_at)}<span>{entries.length}</span></p>
              <ol className={styles.entries}>
                {entries.map((change, index) => (
                  <TimelineEntry key={change.id} change={change} index={index} onOpen={() => setSelectedId(change.id)} />
                ))}
              </ol>
            </section>
          ))}
        </div>
      )}

      <EntrySheet change={selected} onClose={() => setSelectedId(null)} />
    </section>
  );
}
