import { ArrowLeft, Check, Columns2, Eye, Minus, Plus, RefreshCw, Save, Star, TextCursorInput } from "lucide-react";
import { useCallback, useEffect, useState, type CSSProperties } from "react";

import { ApiError, fetchMarkdown, saveMarkdown, updateReportStar } from "../../api/client";
import type { MarkdownFile } from "../../api/types";
import { CodeMirrorEditor } from "./CodeMirrorEditor";
import { MarkdownPreview } from "./MarkdownPreview";
import styles from "./MarkdownWorkspace.module.css";

type EditorMode = "source" | "split" | "preview";
type Conflict = { disk: MarkdownFile; local: string };

const FONT_KEY = "seo-workbench:markdown-font-size";
const FONT_MIN = 12;
const FONT_MAX = 20;

function storedFontSize(frame: boolean): number {
  try {
    const raw = Number(window.localStorage.getItem(FONT_KEY));
    if (Number.isFinite(raw)) return Math.min(FONT_MAX, Math.max(FONT_MIN, raw));
  } catch {
    // localStorage unavailable; fall back to the default for the frame
  }
  return frame ? 14 : 17;
}

export default function MarkdownWorkspace({ projectId, path, onBack, frame = false }: { projectId: string; path: string; onBack: () => void; frame?: boolean }) {
  const [file, setFile] = useState<MarkdownFile | null>(null);
  const [content, setContent] = useState("");
  const [mode, setMode] = useState<EditorMode>("preview");
  const [, setStatus] = useState("Loading");
  const [error, setError] = useState<string | null>(null);
  const [conflict, setConflict] = useState<Conflict | null>(null);
  const [fontSize, setFontSize] = useState(() => storedFontSize(frame));
  const dirty = file ? content !== file.content : false;

  const changeFontSize = (delta: number) => {
    setFontSize((current) => {
      const next = Math.min(FONT_MAX, Math.max(FONT_MIN, current + delta));
      try { window.localStorage.setItem(FONT_KEY, String(next)); } catch { /* ignore */ }
      return next;
    });
  };

  const load = useCallback(async () => {
    try {
      const next = await fetchMarkdown(projectId, path);
      setFile(next); setContent(next.content); setStatus("Saved"); setError(null); setConflict(null);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to load file"); }
  }, [path, projectId]);
  useEffect(() => { void load(); }, [load]);

  const save = useCallback(async () => {
    if (!file) return;
    setStatus("Saving"); setError(null);
    try {
      const saved = await saveMarkdown(projectId, path, content, file.revision);
      setFile({ ...file, content, revision: saved.revision, modified_at: saved.modified_at });
      setStatus("Saved"); setConflict(null);
    } catch (reason) {
      if (reason instanceof ApiError && reason.status === 409) {
        const disk = await fetchMarkdown(projectId, path);
        setConflict({ disk, local: content }); setStatus("Conflict");
      } else { setError(reason instanceof Error ? reason.message : "Unable to save file"); setStatus("Unsaved"); }
    }
  }, [content, file, path, projectId]);

  const toggleStar = useCallback(async () => {
    if (!file || typeof file.starred !== "boolean") return;
    const previous = file.starred;
    setError(null);
    setFile((current) => current ? { ...current, starred: !previous } : current);
    try {
      const updated = await updateReportStar(projectId, path, !previous);
      setFile((current) => current ? { ...current, starred: updated.starred } : current);
    } catch (reason) {
      setFile((current) => current ? { ...current, starred: previous } : current);
      setError(reason instanceof Error ? reason.message : "Unable to update report star");
    }
  }, [file, path, projectId]);

  if (!file) return <div className={styles.loading}>{error || "Loading Markdown"}</div>;
  return (
    <section className={frame ? styles.workspaceFrame : styles.workspace} style={{ "--md-font-size": `${fontSize}px` } as CSSProperties} aria-label={`Markdown editor for ${path}`}>
      <header className={styles.toolbar}>
        <button type="button" className={styles.back} onClick={onBack}><ArrowLeft aria-hidden="true" size={17} /> {frame ? "Close" : "Files"}</button>
        <div className={styles.identity}>
          <span>{file.path}</span>
          {typeof file.starred === "boolean" ? <button type="button" className={styles.reportStar} aria-label={file.starred ? "Remove report star" : "Star report"} aria-pressed={file.starred} title={file.starred ? "Remove report star" : "Star report"} onClick={() => void toggleStar()}><Star aria-hidden="true" size={17} fill={file.starred ? "currentColor" : "none"} /></button> : null}
        </div>
        <div className={styles.modeSwitch} aria-label="Editor view">
          <button type="button" aria-label="Source view" aria-pressed={mode === "source"} onClick={() => setMode("source")}><TextCursorInput aria-hidden="true" size={15} /><span>Source</span></button>
          <button type="button" aria-label="Split view" aria-pressed={mode === "split"} onClick={() => setMode("split")}><Columns2 aria-hidden="true" size={15} /><span>Split</span></button>
          <button type="button" aria-label="Preview view" aria-pressed={mode === "preview"} onClick={() => setMode("preview")}><Eye aria-hidden="true" size={15} /><span>Preview</span></button>
        </div>
        <div className={styles.fontSwitch} aria-label="Preview size">
          <button type="button" aria-label="Smaller preview" disabled={fontSize <= FONT_MIN} onClick={() => changeFontSize(-1)}><Minus aria-hidden="true" size={14} /></button>
          <span>{fontSize}px</span>
          <button type="button" aria-label="Larger preview" disabled={fontSize >= FONT_MAX} onClick={() => changeFontSize(1)}><Plus aria-hidden="true" size={14} /></button>
        </div>
        <button type="button" className={styles.save} onClick={() => void save()} disabled={!dirty} aria-label={dirty ? "Save" : "Saved"}>
          {dirty ? <Save aria-hidden="true" size={16} /> : <Check aria-hidden="true" size={16} />}
          {dirty ? "Save" : "Saved"}
        </button>
      </header>
      {error ? <div className={styles.error} role="alert">{error}</div> : null}
      {conflict ? (
        <div className={styles.conflict} role="alert">
          <strong>This file changed outside the editor.</strong><span>Compare both versions before replacing local work.</span>
          <button type="button" onClick={() => setMode("split")}>Compare changes</button>
          <button type="button" onClick={() => { setFile(conflict.disk); setContent(conflict.disk.content); setConflict(null); setStatus("Saved"); }}><RefreshCw aria-hidden="true" size={14} /> Reload disk version</button>
          <button type="button" onClick={() => setConflict(null)}>Keep editing</button>
        </div>
      ) : null}
      <div className={`${styles.editorGrid} ${styles[mode]}`}>
        {mode !== "preview" ? <div className={styles.sourcePane}><CodeMirrorEditor value={content} onChange={setContent} onSave={() => void save()} fontSize={fontSize} /></div> : null}
        {mode !== "source" ? <MarkdownPreview content={conflict && mode === "split" ? conflict.disk.content : content} /> : null}
      </div>
    </section>
  );
}
