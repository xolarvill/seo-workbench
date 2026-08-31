import { FileText } from "lucide-react";
import { useMemo, useState } from "react";

import type { FileSummary } from "../../api/types";
import { ArtifactCard } from "../../components/ArtifactCard";
import { SearchField } from "../../components/WorkbenchControls";
import { useFiles } from "../../hooks/useWorkbenchData";
import styles from "./OwnersPage.module.css";

const OWNER_ROOT = "strategy/owners/";

type Props = {
  projectId: string;
  refreshKey: number;
  onOpenFile: (path: string) => void;
};

function ownerTitle(file: FileSummary) {
  if (file.name.toLowerCase() === "readme.md") return "Owner card index";
  return file.name.replace(/\.md$/i, "").split("-").map((word) => word.charAt(0).toUpperCase() + word.slice(1)).join(" ");
}

function OwnerFile({ file, onOpenFile }: { file: FileSummary; onOpenFile: (path: string) => void }) {
  const title = ownerTitle(file);
  const index = file.name.toLowerCase() === "readme.md";
  return <ArtifactCard label={`Open ${title}`} onOpen={() => onOpenFile(file.path)} badge={<><FileText aria-hidden="true" size={14} />{index ? "Index" : "Owner"}</>} title={title} meta={`${file.path} · ${new Date(file.modified_at).toLocaleDateString()}`} stats={<span>Read</span>} />;
}

export function OwnersPage({ projectId, refreshKey, onOpenFile }: Props) {
  const { files, error } = useFiles(projectId, refreshKey);
  const [query, setQuery] = useState("");
  const ownerFiles = useMemo(() => files.filter((file) => file.path.startsWith(OWNER_ROOT)), [files]);
  const filtered = useMemo(() => {
    const value = query.trim().toLowerCase();
    return ownerFiles.filter((file) => !value || `${ownerTitle(file)} ${file.path}`.toLowerCase().includes(value));
  }, [ownerFiles, query]);

  return (
    <section className={styles.page} aria-labelledby="owners-heading">
      <h1 id="owners-heading" className="srOnly">Owners</h1>

      <div className={styles.filters} aria-label="Owner filters">
        <SearchField className={styles.searchField} label="Search owner cards" placeholder="Search owner cards..." value={query} onChange={setQuery} />
        <span className={styles.filterCount}>{filtered.length} {filtered.length === 1 ? "card" : "cards"}</span>
      </div>

      {error ? <p className={styles.error} role="alert">{error}</p> : null}
      <div className={styles.block}>
        <div className={styles.blockHead}>
          <div className={styles.blockTitle}><span className={styles.kicker}>Strategy workspace</span><h2>Owner cards</h2><small>{ownerFiles.length} Markdown files</small></div>
        </div>
        <div className={styles.weekList}>
          {filtered.map((file) => <OwnerFile key={file.path} file={file} onOpenFile={onOpenFile} />)}
          {!filtered.length ? <span className={styles.empty}>No owner cards match this search.</span> : null}
        </div>
      </div>
    </section>
  );
}
