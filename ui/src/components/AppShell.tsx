import {
  ChevronsUpDown,
  FileText,
  FolderOpen,
  GitBranch,
  House,
  MoreVertical,
  Play,
  ShieldCheck,
} from "lucide-react";
import type { ReactNode } from "react";

import type { ProjectSummary } from "../api/types";
import styles from "./AppShell.module.css";


export type ViewName = "overview" | "workflow" | "content" | "audits" | "files";

type AppShellProps = {
  projects: ProjectSummary[];
  selectedProject: string | null;
  activeView: ViewName;
  connected: boolean;
  onProjectChange: (projectId: string) => void;
  onNavigate: (view: ViewName) => void;
  onRunAudit: () => void;
  children: ReactNode;
};

const navigation = [
  { id: "overview" as const, label: "Overview", icon: House },
  { id: "workflow" as const, label: "Workflow", icon: GitBranch },
  { id: "content" as const, label: "Content", icon: FileText },
  { id: "audits" as const, label: "Audits", icon: ShieldCheck },
  { id: "files" as const, label: "Files", icon: FolderOpen },
];


export function AppShell({
  projects,
  selectedProject,
  activeView,
  connected,
  onProjectChange,
  onNavigate,
  onRunAudit,
  children,
}: AppShellProps) {
  const project = projects.find((item) => item.id === selectedProject);
  const primaryMobile = navigation.filter((item) => ["overview", "workflow", "files"].includes(item.id));

  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar} aria-label="Workbench navigation">
        <div className={styles.wordmark}>SEO<br />WORKBENCH</div>
        <label className={styles.projectPicker}>
          <span className={styles.projectMonogram}>{project?.name?.slice(0, 1).toUpperCase() || "S"}</span>
          <span className={styles.projectText}>
            <span>{project?.name || "Select project"}</span>
            <small>{project ? new URL(project.url).hostname : "Local workspace"}</small>
          </span>
          <select
            aria-label="Select project"
            value={selectedProject || ""}
            onChange={(event) => onProjectChange(event.target.value)}
          >
            {projects.map((item) => <option key={item.id} value={item.id}>{item.name || item.id}</option>)}
          </select>
          <ChevronsUpDown aria-hidden="true" size={16} />
        </label>
        <nav className={styles.navigation}>
          {navigation.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              className={activeView === id ? styles.activeNav : styles.navItem}
              type="button"
              onClick={() => onNavigate(id)}
            >
              <Icon aria-hidden="true" size={20} strokeWidth={1.5} />
              <span>{label}</span>
            </button>
          ))}
        </nav>
        <div className={styles.connection}>
          <span className={connected ? styles.connectedDot : styles.disconnectedDot} />
          <span>Local only</span>
          <span>·</span>
          <span>{connected ? "UI connected" : "Reconnecting"}</span>
        </div>
      </aside>

      <header className={styles.mobileHeader}>
        <span className={styles.mobileWordmark}>SEO WORKBENCH</span>
        <details className={styles.mobileMore}>
          <summary aria-label="More navigation"><MoreVertical aria-hidden="true" size={24} /></summary>
          <div>
            <button type="button" onClick={() => onNavigate("content")}>Content</button>
            <button type="button" onClick={() => onNavigate("audits")}>Audits</button>
          </div>
        </details>
      </header>

      <div className={styles.workspace}>
        <header className={styles.commandBar}>
          <div className={styles.mobileProject}>
            <strong>{project?.name || "SEO Workbench"}</strong>
            <span>{project ? new URL(project.url).hostname : "Local workspace"}</span>
          </div>
          <div className={styles.commandProject}>
            <strong>{project?.name || "SEO Workbench"}</strong>
            <span>{project ? new URL(project.url).hostname : "Local workspace"}</span>
            {project?.phase ? <b>{project.phase}</b> : null}
          </div>
          <button className={styles.primaryAction} type="button" onClick={onRunAudit}>
            <Play aria-hidden="true" size={17} fill="currentColor" />
            Run audit
          </button>
        </header>
        <main id="main-content" className={styles.main}>{children}</main>
      </div>

      <nav className={styles.mobileNav} aria-label="Mobile workbench navigation">
        {primaryMobile.map(({ id, label, icon: Icon }) => (
          <button key={id} type="button" className={activeView === id ? styles.mobileActive : undefined} onClick={() => onNavigate(id)}>
            <Icon aria-hidden="true" size={22} strokeWidth={1.5} />
            <span>{label}</span>
          </button>
        ))}
      </nav>
    </div>
  );
}
