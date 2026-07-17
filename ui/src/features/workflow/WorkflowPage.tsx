import { Check, Circle, Clock3 } from "lucide-react";

import type { Workspace } from "../../api/types";
import styles from "./WorkflowPage.module.css";

export function WorkflowPage({ workspace }: { workspace: Workspace }) {
  return (
    <section className={styles.page} aria-labelledby="workflow-heading">
      <header className={styles.header}>
        <div><span>Execution state</span><h1 id="workflow-heading">SEO workflow</h1></div>
        <p>The UI reads the same local state used by the CLI and agents.</p>
      </header>
      <div className={styles.nextPanel}>
        <span>Current instruction</span>
        <strong>{workspace.next?.label || workspace.step?.label || "Workflow complete"}</strong>
        {workspace.next?.skill ? <code>{workspace.next.skill}</code> : null}
        {workspace.next?.output ? <small>Expected output: {workspace.next.output}</small> : null}
      </div>
      <ol className={styles.phases}>
        {workspace.phase_order.map((phaseName, index) => {
          const phase = workspace.phases[phaseName];
          const current = phaseName === workspace.phase;
          const done = phase?.status === "done";
          return (
            <li key={phaseName} className={current ? styles.current : done ? styles.done : undefined}>
              <div className={styles.phaseMarker}>
                {done ? <Check aria-hidden="true" size={16} /> : current ? <Clock3 aria-hidden="true" size={16} /> : <Circle aria-hidden="true" size={14} />}
                <span>{String(index + 1).padStart(2, "0")}</span>
              </div>
              <div className={styles.phaseBody}>
                <header><h2>{phaseName.replaceAll("_", " ")}</h2><span>{phase?.status || "pending"}</span></header>
                <div className={styles.steps}>
                  {(phase?.steps || []).map((step) => (
                    <div key={step.id} className={step.status === "done" ? styles.stepDone : current && step.id === workspace.step?.id ? styles.stepCurrent : undefined}>
                      <span>{step.status === "done" ? "✓" : "·"}</span><strong>{step.label}</strong><small>{step.status}</small>
                    </div>
                  ))}
                </div>
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
