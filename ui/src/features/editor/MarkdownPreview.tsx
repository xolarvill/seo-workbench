import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import styles from "./MarkdownWorkspace.module.css";

type MarkdownPreviewProps = {
  content: string;
  documentPath?: string;
  onLocalLink?: (href: string) => boolean;
  projectId?: string;
};

function imageSource(src: string | undefined, projectId: string | undefined, documentPath: string | undefined) {
  if (!src || !projectId || !documentPath || /^(?:https?:|data:|blob:|\/\/)/i.test(src)) return src;
  const params = new URLSearchParams({ source: src, document: documentPath });
  return `/api/v1/projects/${encodeURIComponent(projectId)}/media?${params.toString()}`;
}

export function MarkdownPreview({ content, documentPath, onLocalLink, projectId }: MarkdownPreviewProps) {
  return (
    <article className={styles.preview}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children }) => {
            const external = Boolean(href && /^(?:https?:)?\/\//.test(href));
            return (
              <a
                href={href}
                target={external ? "_blank" : undefined}
                rel={external ? "noreferrer" : undefined}
                onClick={(event) => {
                  if (href && onLocalLink?.(href)) event.preventDefault();
                }}
              >
                {children}
              </a>
            );
          },
          img: ({ src, alt, title }) => <img src={imageSource(src, projectId, documentPath)} alt={alt || ""} title={title} loading="lazy" decoding="async" />,
        }}
      >{content}</ReactMarkdown>
    </article>
  );
}
