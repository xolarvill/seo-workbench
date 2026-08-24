import { ExternalLink, X } from "lucide-react";
import { useEffect, useRef, type ReactNode } from "react";

import styles from "./Drawer.module.css";

const focusableSelector = "a[href], button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex='-1'])";

export function Drawer({ children, closeLabel = "Close details", eyebrow, label, onClose, title, url }: { children: ReactNode; closeLabel?: string; eyebrow: ReactNode; label: string; onClose: () => void; title: ReactNode; url?: string }) {
  const drawer = useRef<HTMLElement>(null);
  const close = useRef<HTMLButtonElement>(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    close.current?.focus();
    const keydown = (event: KeyboardEvent) => {
      if (event.key === "Escape") { event.preventDefault(); onCloseRef.current(); return; }
      if (event.key !== "Tab") return;
      const focusable = Array.from(drawer.current?.querySelectorAll<HTMLElement>(focusableSelector) || []);
      const first = focusable[0];
      const last = focusable.at(-1);
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
    };
    document.addEventListener("keydown", keydown);
    return () => { document.removeEventListener("keydown", keydown); previous?.focus(); };
  }, []);

  return <><button className={styles.backdrop} type="button" aria-label={closeLabel} onClick={onClose} /><aside ref={drawer} className={styles.drawer} role="dialog" aria-modal="true" aria-label={label}><header className={styles.header}><div><span className={styles.eyebrow}>{eyebrow}</span><h2>{title}</h2></div><button ref={close} className={styles.close} type="button" aria-label={closeLabel} onClick={onClose}><X aria-hidden="true" size={18} /></button></header>{url ? <a className={styles.url} href={url} target="_blank" rel="noreferrer">{url}<ExternalLink aria-hidden="true" size={13} /></a> : null}{children}</aside></>;
}
