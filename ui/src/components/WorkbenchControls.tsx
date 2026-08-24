import { ChevronLeft, ChevronRight, Columns3, Search, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import type { ViewColumn } from "../api/types";

import styles from "./WorkbenchControls.module.css";

export function pageLabel(offset: number, limit: number, total: number) {
  return total ? `${offset + 1}–${Math.min(offset + limit, total)} of ${total}` : "0 records";
}

export function SearchField({ className, label, onChange, placeholder, value }: { className?: string; label: string; onChange: (value: string) => void; placeholder?: string; value: string }) {
  return <label className={`${styles.search} ${className || ""}`} data-workbench-search><Search aria-hidden="true" size={15} /><span className={styles.srOnly}>{label}</span><input aria-label={label} value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} />{value ? <button type="button" aria-label={`Clear ${label.toLowerCase()}`} onClick={() => onChange("")}><X aria-hidden="true" size={14} /></button> : null}</label>;
}

export function Pagination({ limit, loading = false, offset, onLimitChange, onOffsetChange, total }: { limit: number; loading?: boolean; offset: number; onLimitChange: (limit: number) => void; onOffsetChange: (offset: number) => void; total: number }) {
  return <footer className={styles.pagination}><span>{pageLabel(offset, limit, total)}</span><label>Rows <select aria-label="Rows per page" value={limit} onChange={(event) => onLimitChange(Number(event.target.value))}><option value={50}>50</option><option value={100}>100</option><option value={200}>200</option></select></label><button type="button" aria-label="Previous page" disabled={offset === 0 || loading} onClick={() => onOffsetChange(Math.max(0, offset - limit))}><ChevronLeft aria-hidden="true" size={15} /></button><button type="button" aria-label="Next page" disabled={offset + limit >= total || loading} onClick={() => onOffsetChange(offset + limit)}><ChevronRight aria-hidden="true" size={15} /></button></footer>;
}

export function useStoredColumns(storageKey: string, columns: ViewColumn[] | undefined) {
  const [preferences, setPreferences] = useState<Record<string, string[]>>({});
  useEffect(() => {
    const saved = window.localStorage?.getItem(storageKey);
    if (!saved) return;
    try { setPreferences((current) => ({ ...current, [storageKey]: JSON.parse(saved) as string[] })); } catch { /* stale preference */ }
  }, [storageKey]);
  const visible = preferences[storageKey] || columns?.filter((column) => column.default).map((column) => column.id) || [];
  const toggle = (id: string) => {
    const next = visible.includes(id) ? visible.filter((value) => value !== id) : [...visible, id];
    if (!next.length) return;
    setPreferences((current) => ({ ...current, [storageKey]: next }));
    window.localStorage?.setItem(storageKey, JSON.stringify(next));
  };
  return { toggle, visible };
}

export function ColumnPicker({ columns, onToggle, visible }: { columns: ViewColumn[] | undefined; onToggle: (id: string) => void; visible: string[] }) {
  const ref = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    const close = (event: PointerEvent) => {
      if (ref.current?.open && !ref.current.contains(event.target as Node)) ref.current.open = false;
    };
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, []);
  return <details ref={ref} className={styles.columnMenu}><summary><Columns3 aria-hidden="true" size={14} />Columns</summary><div>{columns?.map((column) => <label key={column.id}><input type="checkbox" checked={visible.includes(column.id)} onChange={() => onToggle(column.id)} />{column.label}</label>)}</div></details>;
}
