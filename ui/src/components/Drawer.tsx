import { ExternalLink, X } from "lucide-react";
import { useRef, type ReactNode } from "react";

import { Sheet, SheetClose, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { cn } from "@/lib/utils";

import styles from "./Drawer.module.css";

/**
 * Shared detail drawer. Radix Dialog supplies the modal semantics, focus
 * trap, Escape handling, and focus restoration; the module classes keep the
 * existing right-side panel appearance.
 */
export function Drawer({ children, closeLabel = "Close details", eyebrow, label, onClose, title, url }: { children: ReactNode; closeLabel?: string; eyebrow: ReactNode; label: string; onClose: () => void; title: ReactNode; url?: string }) {
  // This drawer has no Dialog.Trigger, so restore the element focused at open.
  const restoreRef = useRef<HTMLElement | null>(document.activeElement as HTMLElement | null);
  return (
    <Sheet open onOpenChange={(open) => { if (!open) onClose(); }}>
      <SheetContent
        side="right"
        aria-label={label}
        aria-describedby={undefined}
        className={cn(styles.drawer, "block gap-0")}
        onCloseAutoFocus={(event) => { event.preventDefault(); restoreRef.current?.focus(); }}
        overlay={<SheetClose asChild><button type="button" className={styles.backdrop} aria-label={closeLabel} /></SheetClose>}
      >
        <header className={styles.header}>
          <div>
            <span className={styles.eyebrow}>{eyebrow}</span>
            <SheetTitle asChild aria-label={label}><h2>{title}</h2></SheetTitle>
          </div>
          <SheetClose asChild>
            <button className={styles.close} type="button" aria-label={closeLabel}><X aria-hidden="true" size={18} /></button>
          </SheetClose>
        </header>
        {url ? <a className={styles.url} href={url} target="_blank" rel="noreferrer">{url}<ExternalLink aria-hidden="true" size={13} /></a> : null}
        {children}
      </SheetContent>
    </Sheet>
  );
}
