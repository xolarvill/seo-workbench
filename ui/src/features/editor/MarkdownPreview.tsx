import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import styles from "./MarkdownWorkspace.module.css";

export function MarkdownPreview({ content }: { content: string }) {
  return (
    <article className={styles.preview}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children }) => <a href={href} target="_blank" rel="noreferrer">{children}</a>,
        }}
      >{content}</ReactMarkdown>
    </article>
  );
}
