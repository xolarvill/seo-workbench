import { CircleHelp } from "lucide-react";
import { useId, type ReactNode } from "react";

import styles from "./HelpTooltip.module.css";

export function HelpTooltip({ label, children, align = "left" }: { label: string; children: ReactNode; align?: "left" | "center" | "right" }) {
  const tooltipId = useId();
  return <span className={`${styles.helpTooltip} ${align === "right" ? styles.helpTooltipRight : align === "center" ? styles.helpTooltipCenter : ""}`} tabIndex={0} role="img" aria-label={`Help: ${label}`} aria-describedby={tooltipId}>
    <CircleHelp aria-hidden="true" size={14} strokeWidth={1.8} />
    <span id={tooltipId} role="tooltip">{children}</span>
  </span>;
}
