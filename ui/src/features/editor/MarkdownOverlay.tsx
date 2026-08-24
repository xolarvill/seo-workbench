import { useCallback, useEffect } from "react";

import MarkdownWorkspace from "./MarkdownWorkspace";
import styles from "./MarkdownOverlay.module.css";

type Props = {
  projectId: string;
  path: string;
  onClose: () => void;
};

export default function MarkdownOverlay({ projectId, path, onClose }: Props) {
  const handleKey = useCallback((event: KeyboardEvent) => {
    if (event.key === "Escape") onClose();
  }, [onClose]);

  useEffect(() => {
    window.addEventListener("keydown", handleKey);
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", handleKey);
      document.body.style.overflow = previous;
    };
  }, [handleKey]);

  return (
    <div className={styles.backdrop} role="presentation" onMouseDown={onClose}>
      <section
        className={styles.panel}
        role="dialog"
        aria-modal="true"
        aria-label={`Markdown preview and editor for ${path}`}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <MarkdownWorkspace projectId={projectId} path={path} onBack={onClose} frame />
      </section>
    </div>
  );
}
