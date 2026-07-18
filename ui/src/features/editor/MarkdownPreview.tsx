import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import styles from "./MarkdownWorkspace.module.css";

type MarkdownPreviewProps = {
  content: string;
  onLocalLink?: (href: string) => boolean;
};

export function MarkdownPreview({ content, onLocalLink }: MarkdownPreviewProps) {
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
        }}
      >{content}</ReactMarkdown>
    </article>
  );
}
