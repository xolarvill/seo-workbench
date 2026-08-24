import { Check, LoaderCircle } from "lucide-react";
import { useEffect, useState, type CSSProperties } from "react";

import styles from "./ProgressiveLoading.module.css";

type ProgressiveLoadingStatusProps = {
  loading: boolean;
  complete: boolean;
  label: string;
  total?: number;
  notice?: string;
};

export function ProgressiveLoadingStatus({ loading, complete, label, total, notice }: ProgressiveLoadingStatusProps) {
  const [visible, setVisible] = useState(false);
  const [started, setStarted] = useState(false);
  const [noticeVisible, setNoticeVisible] = useState(false);

  useEffect(() => {
    if (loading) {
      setStarted(true);
      setVisible(true);
      return;
    }
    if (!complete || !started) return;
    const timer = window.setTimeout(() => setVisible(false), 1800);
    return () => window.clearTimeout(timer);
  }, [complete, loading, started]);

  useEffect(() => {
    if (!notice) {
      setNoticeVisible(false);
      return;
    }
    setNoticeVisible(true);
    const timer = window.setTimeout(() => setNoticeVisible(false), 1800);
    return () => window.clearTimeout(timer);
  }, [notice]);

  if (!visible && !(notice && noticeVisible)) return null;
  if (notice && noticeVisible) return <div className={styles.status} data-complete="true" role="status" aria-live="polite"><span className={styles.statusIcon} aria-hidden="true"><Check size={15} /></span><span>{notice}</span></div>;
  const count = typeof total === "number" ? `${total.toLocaleString()} ` : "";
  return <div className={styles.status} data-complete={!loading && complete} role="status" aria-live="polite"><span className={styles.statusIcon} aria-hidden="true">{loading ? <LoaderCircle size={15} /> : <Check size={15} />}</span><span>{loading ? `Loading ${label}…` : `${count}${label} loaded`}</span></div>;
}

export type SkeletonColumn = { id: string; label?: string; width?: string };

export function ProgressiveSkeletonRows({ columns, rows = 7 }: { columns: SkeletonColumn[]; rows?: number }) {
  return Array.from({ length: rows }, (_, rowIndex) => <tr className={styles.skeletonRow} key={`skeleton-${rowIndex}`} aria-hidden="true">{columns.map((column, columnIndex) => <td key={column.id}><span className={styles.skeletonCell} style={{ "--skeleton-width": column.width || `${Math.max(48, 82 - columnIndex * 9)}%` } as CSSProperties} /></td>)}</tr>);
}

export function ProgressiveSkeletonCard() {
  return <div className={styles.skeletonCard} aria-hidden="true"><span className={`${styles.skeletonLine} ${styles.skeletonLineShort}`} /><span className={`${styles.skeletonLine} ${styles.skeletonLineMetric}`} /><span className={styles.skeletonLine} /></div>;
}
