import type { ReactNode } from "react";

import styles from "./ArtifactCard.module.css";

export function ArtifactCard({ actions, badge, children, label, meta, onOpen, stats, title }: { actions?: ReactNode; badge: ReactNode; children?: ReactNode; label: string; meta: ReactNode; onOpen: () => void; stats?: ReactNode; title: ReactNode }) {
  return <article className={styles.card}><div className={styles.row}><button type="button" className={styles.open} onClick={onOpen} aria-label={label}><span className={styles.badge}>{badge}</span><span className={styles.meta}><strong>{title}</strong><small>{meta}</small></span>{stats ? <span className={styles.stats}>{stats}</span> : null}</button>{actions ? <div className={styles.actions}>{actions}</div> : null}</div>{children}</article>;
}
