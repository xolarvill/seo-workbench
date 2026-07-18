import { BookOpenText, LockKeyhole } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { fetchTutorial, fetchTutorials } from "../../api/client";
import type { TutorialDocument, TutorialSummary } from "../../api/types";
import { MarkdownPreview } from "../editor/MarkdownPreview";
import styles from "./TutorialsPage.module.css";


function localTarget(href: string): string | null {
  const target = href.split("#", 1)[0].replace(/^\.\//, "");
  if (!target.endsWith(".md")) return null;
  try {
    return decodeURIComponent(target);
  } catch {
    return target;
  }
}


export function TutorialsPage() {
  const [tutorials, setTutorials] = useState<TutorialSummary[]>([]);
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);
  const [document, setDocument] = useState<TutorialDocument | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchTutorials()
      .then((items) => {
        setTutorials(items);
        setSelectedSlug((current) => current || items[0]?.slug || null);
      })
      .catch((reason: Error) => setError(reason.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selectedSlug) return;
    setDocument(null);
    setError(null);
    fetchTutorial(selectedSlug)
      .then(setDocument)
      .catch((reason: Error) => setError(reason.message));
  }, [selectedSlug]);

  const groups = useMemo(() => {
    const found = new Map<string, TutorialSummary[]>();
    tutorials.forEach((tutorial) => found.set(tutorial.category, [...(found.get(tutorial.category) || []), tutorial]));
    return [...found.entries()];
  }, [tutorials]);

  const openLocalLink = (href: string) => {
    const target = localTarget(href);
    if (!target) return false;
    const tutorial = tutorials.find((item) => item.source === target);
    if (!tutorial) return false;
    setSelectedSlug(tutorial.slug);
    return true;
  };

  if (loading) return <div className={styles.state}>Loading local tutorials</div>;
  if (error && tutorials.length === 0) return <div className={styles.state} role="alert">{error}</div>;

  return (
    <section className={styles.page} aria-label="SEO tutorials">
      <aside className={styles.index}>
        <div className={styles.indexHeading}>
          <BookOpenText aria-hidden="true" size={18} strokeWidth={1.5} />
          <div>
            <span>LOCAL GUIDE LIBRARY</span>
            <strong>{tutorials.length} tutorials</strong>
          </div>
        </div>
        <label className={styles.mobilePicker}>
          <span>Tutorial</span>
          <select value={selectedSlug || ""} onChange={(event) => setSelectedSlug(event.target.value)}>
            {tutorials.map((tutorial) => <option key={tutorial.slug} value={tutorial.slug}>{tutorial.title}</option>)}
          </select>
        </label>
        <div className={styles.groups}>
          {groups.map(([category, items]) => (
            <section key={category} className={styles.group}>
              <h2>{category}</h2>
              {items.map((tutorial) => (
                <button
                  key={tutorial.slug}
                  className={selectedSlug === tutorial.slug ? styles.activeTutorial : styles.tutorial}
                  type="button"
                  onClick={() => setSelectedSlug(tutorial.slug)}
                  aria-current={selectedSlug === tutorial.slug ? "page" : undefined}
                >
                  <strong>{tutorial.title}</strong>
                  <span>{tutorial.description}</span>
                </button>
              ))}
            </section>
          ))}
        </div>
      </aside>

      <div className={styles.reader}>
        <header className={styles.readerHeader}>
          <div>
            <span>Source</span>
            <strong>{document?.source || "Opening tutorial"}</strong>
          </div>
          <p><LockKeyhole aria-hidden="true" size={13} /> Read only</p>
        </header>
        {error ? <div className={styles.state} role="alert">{error}</div> : null}
        {document ? <MarkdownPreview content={document.content} onLocalLink={openLocalLink} /> : !error ? <div className={styles.state}>Opening tutorial</div> : null}
      </div>
    </section>
  );
}
