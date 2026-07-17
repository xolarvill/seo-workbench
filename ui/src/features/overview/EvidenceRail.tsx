import { BarChart3, Braces, Check, CircleAlert, FileSearch, Gauge, SearchX } from "lucide-react";

import type { EvidenceItem } from "../../api/types";
import styles from "./Overview.module.css";


const icons = {
  raw: FileSearch,
  technology: Braces,
  performance: Gauge,
  crux: BarChart3,
  gsc: SearchX,
  diff: CircleAlert,
};

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    ok: "Ready",
    ready: "Ready",
    partial: "Partial",
    needs_key: "Needs key",
    not_bound: "Not bound",
    missing: "No data",
    failed: "Failed",
    no_data: "No data",
  };
  return labels[status] || status.replaceAll("_", " ");
}

function tone(status: string) {
  if (["ok", "ready"].includes(status)) return styles.ready;
  if (["failed", "not_bound"].includes(status)) return styles.failed;
  return styles.warning;
}


export function EvidenceRail({ items }: { items: EvidenceItem[] }) {
  return (
    <aside className={styles.evidenceRail} aria-label="Evidence status">
      <h2>Evidence rail</h2>
      <div className={styles.evidenceTrack}>
        {items.map((item) => {
          const Icon = icons[item.id];
          return (
            <div className={styles.evidenceItem} key={item.id}>
              <span className={`${styles.statusIcon} ${tone(item.status)}`}>
                {item.status === "ok" ? <Check size={13} aria-hidden="true" /> : null}
              </span>
              <Icon aria-hidden="true" size={22} strokeWidth={1.5} />
              <span>
                <strong>{item.label}</strong>
                <small className={tone(item.status)}>{statusLabel(item.status)}</small>
              </span>
            </div>
          );
        })}
      </div>
    </aside>
  );
}
