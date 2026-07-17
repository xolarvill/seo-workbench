import { ArrowLeft, Columns2, Eye, RefreshCw, Save, TextCursorInput } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { ApiError, fetchMarkdown, saveMarkdown } from "../../api/client";
import type { MarkdownFile } from "../../api/types";
import { CodeMirrorEditor } from "./CodeMirrorEditor";
import { MarkdownPreview } from "./MarkdownPreview";
import styles from "./MarkdownWorkspace.module.css";

type EditorMode = "source" | "split" | "preview";
type Conflict = { disk: MarkdownFile; local: string };

export default function MarkdownWorkspace({ projectId, path, onBack }: { projectId: string; path: string; onBack: () => void }) {
  const [file, setFile] = useState<MarkdownFile | null>(null);
  const [content, setContent] = useState("");
  const [mode, setMode] = useState<EditorMode>("split");
  const [status, setStatus] = useState("Loading");
  const [error, setError] = useState<string | null>(null);
  const [conflict, setConflict] = useState<Conflict | null>(null);
  const dirty = file ? content !== file.content : false;

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

  if (!file) return <div className={styles.loading}>{error || "Loading Markdown"}</div>;
  return (
    <section className={styles.workspace} aria-label={`Markdown editor for ${path}`}>
      <header className={styles.toolbar}>
        <button type="button" className={styles.back} onClick={onBack}><ArrowLeft aria-hidden="true" size={17} /> Files</button>
        <div className={styles.identity}><strong>{file.path.split("/").at(-1)}</strong><span>{file.path}</span></div>
        <div className={styles.modeSwitch} aria-label="Editor view">
          <button type="button" aria-pressed={mode === "source"} onClick={() => setMode("source")}><TextCursorInput aria-hidden="true" size={15} /><span>Source</span></button>
          <button type="button" aria-pressed={mode === "split"} onClick={() => setMode("split")}><Columns2 aria-hidden="true" size={15} /><span>Split</span></button>
          <button type="button" aria-pressed={mode === "preview"} onClick={() => setMode("preview")}><Eye aria-hidden="true" size={15} /><span>Preview</span></button>
        </div>
        <span className={dirty ? styles.dirty : styles.saved}>{dirty ? "Unsaved" : status}</span>
        <button type="button" className={styles.save} onClick={() => void save()} disabled={!dirty}><Save aria-hidden="true" size={16} /> Save</button>
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
        {mode !== "preview" ? <div className={styles.sourcePane}><CodeMirrorEditor value={content} onChange={setContent} onSave={() => void save()} /></div> : null}
        {mode !== "source" ? <MarkdownPreview content={conflict && mode === "split" ? conflict.disk.content : content} /> : null}
      </div>
    </section>
  );
}
