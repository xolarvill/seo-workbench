import { BarChart3, Braces, Check, CircleAlert, FileSearch, Gauge, Link2, ScanSearch, SearchX } from "lucide-react";

import type { EvidenceItem } from "../../api/types";
import { StatusPill, statusLabel, statusTone } from "../../components/StatusPill";
import styles from "./Overview.module.css";


const icons = {
  raw: FileSearch,
  browser: ScanSearch,
  technology: Braces,
  performance: Gauge,
  crux: BarChart3,
  gsc: SearchX,
  backlinks: Link2,
  diff: CircleAlert,
};

const toneClasses = { danger: styles.statusDanger, warning: styles.statusWarning, info: styles.statusInfo, success: styles.statusSuccess, neutral: styles.statusInfo };


export function EvidenceStatusCard({ items }: { items: EvidenceItem[] }) {
  return (
    <aside className={styles.evidenceStatusCard} id="evidence-status-card" aria-label="Evidence status">
      <div className={styles.evidenceCardHeader}>
        <div><span>Evidence status</span><strong>All evidence sources</strong></div>
        <small>{items.length} sources</small>
      </div>
      <div className={styles.evidenceCardGrid}>
        {items.map((item) => {
          const Icon = icons[item.id as keyof typeof icons] || FileSearch;
          const tone = statusTone(item.status, "evidence");
          return (
            <div className={styles.evidenceItem} key={item.id}>
              <span className={`${styles.statusIcon} ${toneClasses[tone]}`}>
                {tone === "success" ? <Check size={13} aria-hidden="true" /> : null}
              </span>
              <Icon aria-hidden="true" size={22} strokeWidth={1.5} />
              <span>
                <strong>{item.label}</strong>
                <StatusPill value={statusLabel(item.status)} context="evidence" />
              </span>
            </div>
          );
        })}
      </div>
    </aside>
  );
}
