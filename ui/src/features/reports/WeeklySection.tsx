import { AlertTriangle, CalendarClock, CalendarDays, FileText, FolderPlus, Loader2, Star } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { updateReportStar } from "../../api/client";
import type { CarriedOverTrack, ContentJobAction, Job, ReportFollowUp, WeeklyReportSummary } from "../../api/types";
import { ArtifactCard } from "../../components/ArtifactCard";
import { SearchField } from "../../components/WorkbenchControls";
import { useDebouncedValue, useReportArchive } from "../../hooks/useWorkbenchData";
import styles from "./WeeklySection.module.css";

type Props = {
  projectId: string;
  jobs: Job[];
  refreshKey: number;
  onOpenFile: (path: string) => void;
  onRunContentAction: (action: ContentJobAction) => Promise<void>;
};

const CATEGORY_ORDER = ["tech", "content", "ops", "decision", "outcome"];
const CATEGORY_LABELS: Record<string, string> = {
  tech: "Technical",
  content: "Content",
  ops: "Operations",
  decision: "Decisions",
  outcome: "Outcomes",
};
const MONTH_OPTIONS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

function ReportStarButton({ path, starred, onToggle }: { path: string; starred: boolean; onToggle: (path: string, starred: boolean, previous: boolean) => Promise<void> }) {
  const label = starred ? `Unstar ${path}` : `Star ${path}`;
  return <button type="button" className={styles.starButton} aria-label={label} aria-pressed={starred} title={label} onClick={() => void onToggle(path, !starred, starred)}><Star aria-hidden="true" size={16} fill={starred ? "currentColor" : "none"} /></button>;
}

function WeekCard({ onOpenFile, onToggleStar, starred, week }: { week: WeeklyReportSummary; onOpenFile: (path: string) => void; onToggleStar: (path: string, starred: boolean, previous: boolean) => Promise<void>; starred: boolean }) {
  const inherited = week.inherited_from.length ? `承接 ${week.inherited_from.length} 项自 Week ${week.inherited_from.map(String).join("/")}` : "";
  return (
    <ArtifactCard actions={<ReportStarButton path={week.path} starred={starred} onToggle={onToggleStar} />} label={`Open ${week.name}`} onOpen={() => onOpenFile(week.path)} badge={<><CalendarDays aria-hidden="true" size={14} />W{String(week.week).padStart(2, "0")}</>} title={`${week.year} Week ${String(week.week).padStart(2, "0")}`} meta={`${week.start} → ${week.end}`} stats={<>{week.total ? <span>速览 {week.checked}/{week.total}</span> : null}{week.carry_over ? <span>遗留 {week.carry_over}</span> : null}{inherited ? <span className={styles.inheritedTag}>{inherited}</span> : null}</>}>
      {week.follow_ups.length ? (
        <ul className={styles.followUps}>
          {week.follow_ups.map((follow) => (
            <li key={`${week.path}-${follow.date}`}>
              <time>{follow.date}</time><span>{follow.text}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </ArtifactCard>
  );
}

function FollowUpRow({ follow, onOpenFile }: { follow: ReportFollowUp; onOpenFile: (path: string) => void }) {
  return (
    <li>
      <button type="button" className={styles.followUpOpen} onClick={() => onOpenFile(follow.path)} aria-label={`Open week ${follow.week}`}>
        <time>{follow.date}</time>
        <span>{follow.text}</span>
        <small>W{String(follow.week).padStart(2, "0")}</small>
      </button>
    </li>
  );
}

function TrackRow({ track, onOpenFile }: { track: CarriedOverTrack; onOpenFile: (path: string) => void }) {
  return (
    <li className={styles.trackRow}>
      <span className={styles.trackTask}>{track.task}</span>
      <span className={styles.trackSpans}>顺延 {track.spans} 周</span>
      <span className={styles.trackWeeks}>
        {track.entries.map((entry) => (
          <button key={entry.path} type="button" onClick={() => onOpenFile(entry.path)} aria-label={`Open week ${entry.week}`}>
            W{String(entry.week).padStart(2, "0")}
          </button>
        ))}
      </span>
    </li>
  );
}

export function WeeklySection({ projectId, jobs, refreshKey, onOpenFile, onRunContentAction }: Props) {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [year, setYear] = useState("");
  const [month, setMonth] = useState("");
  const [starredOnly, setStarredOnly] = useState(false);
  const [starOverrides, setStarOverrides] = useState<Record<string, boolean>>({});
  const [starError, setStarError] = useState<string | null>(null);
  const debouncedQuery = useDebouncedValue(query, 250);
  const params = useMemo(() => ({
    q: debouncedQuery || undefined,
    category: category || undefined,
    year: year ? Number(year) : undefined,
    month: month ? Number(month) : undefined,
  }), [debouncedQuery, category, year, month]);
  const { archive, error: loadError } = useReportArchive(projectId, refreshKey, params);
  const [actionError, setActionError] = useState<string | null>(null);
  const running = jobs.some((job) => job.status === "running" || job.status === "queued");

  useEffect(() => {
    setStarOverrides({});
    setStarError(null);
  }, [projectId]);

  const isStarred = (path: string, fallback: boolean) => Object.prototype.hasOwnProperty.call(starOverrides, path) ? starOverrides[path] : fallback;

  const toggleStar = async (path: string, next: boolean, previous: boolean) => {
    setStarError(null);
    setStarOverrides((current) => ({ ...current, [path]: next }));
    try {
      await updateReportStar(projectId, path, next);
    } catch (reason) {
      setStarOverrides((current) => ({ ...current, [path]: previous }));
      setStarError(reason instanceof Error ? reason.message : String(reason));
    }
  };

  const scaffold = async () => {
    setActionError(null);
    try {
      await onRunContentAction({ action: "reports-new" });
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : String(reason));
    }
  };

  const visibleWeekly = (archive?.weekly || []).filter((week) => !starredOnly || isStarred(week.path, week.starred));
  const visibleSubReports = (archive?.sub_reports || []).filter((report) => !starredOnly || isStarred(report.path, report.starred));
  const categoryReports = visibleSubReports.reduce<Record<string, typeof visibleSubReports>>((result, report) => {
    (result[report.category] ||= []).push(report);
    return result;
  }, {});
  const categories = Object.entries(categoryReports).sort(([left], [right]) => {
    const leftIndex = CATEGORY_ORDER.indexOf(left);
    const rightIndex = CATEGORY_ORDER.indexOf(right);
    const leftRank = leftIndex === -1 ? CATEGORY_ORDER.length : leftIndex;
    const rightRank = rightIndex === -1 ? CATEGORY_ORDER.length : rightIndex;
    return leftRank - rightRank || left.localeCompare(right);
  });

  const yearOptions = useMemo(() => {
    const years = new Set<number>();
    archive?.weekly.forEach((week) => years.add(week.year));
    if (year) years.add(Number(year));
    return [...years].sort((left, right) => right - left);
  }, [archive, year]);

  const followUpGroups = useMemo(() => {
    const follow = archive?.progress.follow_ups || [];
    return {
      overdue: follow.filter((item) => item.state === "overdue"),
      upcoming: follow.filter((item) => item.state === "upcoming"),
      future: follow.filter((item) => item.state === "future" || item.state === "unknown"),
    };
  }, [archive]);

  const starredCount = (archive?.weekly || []).filter((week) => isStarred(week.path, week.starred)).length + (archive?.sub_reports || []).filter((report) => isStarred(report.path, report.starred)).length;
  const filtering = Boolean(params.q || params.category || params.year || params.month || starredOnly);
  const subReportCount = visibleSubReports.length;

  return (
    <section className={styles.page} aria-labelledby="weekly-heading">
      <h1 id="weekly-heading" className="srOnly">Weekly</h1>

      {actionError ? <p className={styles.error} role="alert">{actionError}</p> : null}
      {loadError ? <p className={styles.error} role="alert">{loadError}</p> : null}
      {starError ? <p className={styles.error} role="alert">{starError}</p> : null}

      {!archive ? null : (
        <>
          <div className={styles.filters}>
            <SearchField className={styles.searchField} label="Search reports" placeholder="Search reports by topic..." value={query} onChange={setQuery} />
            <label className={styles.selectField}><span>Category</span>
              <select aria-label="Filter by category" value={category} onChange={(event) => setCategory(event.target.value)}>
                <option value="">All</option>
                {CATEGORY_ORDER.map((key) => <option key={key} value={key}>{CATEGORY_LABELS[key] || key}</option>)}
              </select>
            </label>
            <label className={styles.selectField}><span>Year</span>
              <select aria-label="Filter by year" value={year} onChange={(event) => setYear(event.target.value)}>
                <option value="">All</option>
                {yearOptions.map((value) => <option key={value} value={String(value)}>{value}</option>)}
              </select>
            </label>
            <label className={styles.selectField}><span>Month</span>
              <select aria-label="Filter by month" value={month} onChange={(event) => setMonth(event.target.value)}>
                <option value="">All</option>
                {MONTH_OPTIONS.map((label, index) => <option key={label} value={String(index + 1)}>{label}</option>)}
              </select>
            </label>
            <button type="button" className={`${styles.starFilter} ${starredOnly ? styles.starFilterActive : ""}`} aria-label={starredOnly ? "Show all reports" : "Show starred reports"} aria-pressed={starredOnly} onClick={() => setStarredOnly((value) => !value)}><Star aria-hidden="true" size={15} fill={starredOnly ? "currentColor" : "none"} /><span>Starred</span><small>{starredCount}</small></button>
          </div>

          <div className={styles.progressGrid}>
            <section className={styles.card}>
              <div className={styles.cardHead}><span className={styles.kicker}>Due follow-ups</span><h2>Follow-ups</h2><small>{archive.progress.overdue} overdue · {archive.progress.upcoming} this week</small><CalendarClock aria-hidden="true" size={16} /></div>
              {archive.progress.follow_ups.length === 0 ? <span className={styles.empty}>No follow-up dates tracked yet.</span> : (
                <div className={styles.followGroups}>
                  {followUpGroups.overdue.length ? (
                    <div className={styles.followGroup}>
                      <h3 className={styles.groupOverdue}><AlertTriangle aria-hidden="true" size={13} />Overdue</h3>
                      <ul className={styles.followList}>{followUpGroups.overdue.map((follow) => <FollowUpRow key={`${follow.path}-${follow.date}`} follow={follow} onOpenFile={onOpenFile} />)}</ul>
                    </div>
                  ) : null}
                  {followUpGroups.upcoming.length ? (
                    <div className={styles.followGroup}>
                      <h3 className={styles.groupUpcoming}>This week</h3>
                      <ul className={styles.followList}>{followUpGroups.upcoming.map((follow) => <FollowUpRow key={`${follow.path}-${follow.date}`} follow={follow} onOpenFile={onOpenFile} />)}</ul>
                    </div>
                  ) : null}
                  {followUpGroups.future.length ? (
                    <div className={styles.followGroup}>
                      <h3>Later</h3>
                      <ul className={styles.followList}>{followUpGroups.future.slice(0, 5).map((follow) => <FollowUpRow key={`${follow.path}-${follow.date}`} follow={follow} onOpenFile={onOpenFile} />)}</ul>
                    </div>
                  ) : null}
                </div>
              )}
            </section>

            <section className={styles.card}>
              <div className={styles.cardHead}><span className={styles.kicker}>Carried over</span><h2>Still open</h2><small>{archive.progress.carried_over_tracks.length} tasks across 2+ weeks</small></div>
              {archive.progress.carried_over_tracks.length === 0 ? <span className={styles.empty}>Nothing carried across multiple weeks.</span> : (
                <ul className={styles.trackList}>
                  {archive.progress.carried_over_tracks.map((track) => <TrackRow key={track.task} track={track} onOpenFile={onOpenFile} />)}
                </ul>
              )}
            </section>
          </div>

          <div className={styles.block}>
            <div className={styles.blockHead}>
              <div className={styles.blockTitle}><span className={styles.kicker}>Work archive</span><h2>Weekly reports</h2><small>{archive.weekly.length} files · latest: {archive.latest_week ? `Week ${String(archive.latest_week.week).padStart(2, "0")}` : "none"}</small></div>
              <div className={styles.blockActions}>
                {running ? <span className={styles.running}><Loader2 aria-hidden="true" size={14} />Running</span> : null}
                <button type="button" className={styles.primaryAction} disabled={running} onClick={() => void scaffold()}>
                  <FolderPlus aria-hidden="true" size={15} /><span>New weekly report</span>
                </button>
              </div>
            </div>
            <div className={styles.weekList}>
              {visibleWeekly.map((week) => <WeekCard key={week.path} week={week} starred={isStarred(week.path, week.starred)} onToggleStar={toggleStar} onOpenFile={onOpenFile} />)}
              {visibleWeekly.length === 0 ? <span className={styles.empty}>{starredOnly ? "No starred weekly reports." : "No weekly reports yet — scaffold one to get started."}</span> : null}
            </div>
          </div>

          <div className={styles.block}>
            <div className={styles.blockHead}><div className={styles.blockTitle}><span className={styles.kicker}>Sub-reports</span><h2>Decision & outcome records</h2></div><small>{filtering ? `${subReportCount} matching` : `${subReportCount} records`}</small></div>
            {categories.length === 0 ? <span className={styles.empty}>{filtering ? "No sub-reports match the current filters." : "No sub-reports yet."}</span> : (
              <div className={styles.categoryGrid}>
                {categories.map(([key, reports]) => (
                  <section key={key} className={styles.category}>
                    <h3>{CATEGORY_LABELS[key] || key} <small>{reports.length}</small></h3>
                    <ul className={styles.subList}>
                      {reports.map((report) => (
                        <li key={report.path} className={styles.subItem}>
                          <button type="button" className={styles.subOpen} onClick={() => onOpenFile(report.path)} aria-label={`Open ${report.path}`}>
                            <FileText aria-hidden="true" size={14} /><time>{report.date.slice(0, 4)}-{report.date.slice(4, 6)}-{report.date.slice(6, 8)}</time><span>{report.topic}</span>
                          </button><ReportStarButton path={report.path} starred={isStarred(report.path, report.starred)} onToggle={toggleStar} />
                        </li>
                      ))}
                    </ul>
                  </section>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </section>
  );
}
