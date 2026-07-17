import { FileText, Folder, Search } from "lucide-react";
import { useMemo, useState } from "react";

import { useFiles } from "../../hooks/useWorkbenchData";
import styles from "./FilesPage.module.css";

type FilesPageProps = {
  projectId: string;
  root?: string;
  refreshKey: number;
  onOpenFile: (path: string) => void;
};

function readableSize(size: number) {
  if (size < 1024) return `${size} B`;
  return `${(size / 1024).toFixed(1)} KB`;
}

export function FilesPage({ projectId, root, refreshKey, onOpenFile }: FilesPageProps) {
  const { files, error } = useFiles(projectId, refreshKey);
  const [query, setQuery] = useState("");
  const filtered = useMemo(() => files.filter((file) => {
    const insideRoot = !root || file.path.startsWith(`${root}/`);
    return insideRoot && file.path.toLowerCase().includes(query.trim().toLowerCase());
  }), [files, query, root]);
  const grouped = useMemo(() => filtered.reduce<Record<string, typeof filtered>>((result, file) => {
    const group = file.path.split("/")[0];
    (result[group] ||= []).push(file);
    return result;
  }, {}), [filtered]);

  return (
    <section className={styles.page} aria-labelledby="files-heading">
      <header className={styles.header}>
        <div><span>Local Markdown</span><h1 id="files-heading">{root ? `${root} workspace` : "Project files"}</h1></div>
        <label className={styles.search}><Search aria-hidden="true" size={16} /><span className={styles.srOnly}>Search files</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search Markdown" /></label>
      </header>
      {error ? <p className={styles.error} role="alert">{error}</p> : null}
      {filtered.length === 0 ? <div className={styles.empty}><FileText aria-hidden="true" size={24} /><strong>No Markdown files found</strong><span>Files appear here when agents or the CLI create them in an editable project area.</span></div> : null}
      <div className={styles.groups}>
        {Object.entries(grouped).map(([group, groupFiles]) => (
          <section key={group} className={styles.group}>
            <h2><Folder aria-hidden="true" size={15} />{group}<span>{groupFiles?.length || 0}</span></h2>
            <div className={styles.fileList}>
              {(groupFiles || []).map((file) => (
                <button type="button" key={file.path} onClick={() => onOpenFile(file.path)}>
                  <FileText aria-hidden="true" size={16} strokeWidth={1.5} />
                  <span><strong>{file.name}</strong><small>{file.path}</small></span>
                  <time>{new Date(file.modified_at).toLocaleDateString()}</time>
                  <b>{readableSize(file.size)}</b>
                </button>
              ))}
            </div>
          </section>
        ))}
      </div>
    </section>
  );
}
