import {
  BarChart3,
  ChevronDown,
  ChevronUp,
  ChevronsUpDown,
  FileChartColumn,
  FileText,
  FolderOpen,
  GitBranch,
  House,
  KeyRound,
  Link2,
  MoreVertical,
  PanelsTopLeft,
  ShieldCheck,
  Tags,
  UserRound,
} from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";

import type { ProjectSummary } from "../api/types";
import styles from "./AppShell.module.css";


export type ViewName = "overview" | "owners" | "keywords" | "pages" | "link-building" | "statistics" | "workflow" | "content" | "reports" | "audits" | "files" | "integrations" | "tutorials";
export type AuditSection = "overview" | "automation" | "url-inventory" | "crawl-comparison" | "redirects" | "sitemaps" | "logs";
export type ContentSection = "brief" | "produce";
export type ReportSection = "weekly" | "seo-changes" | "presentation" | "notify";
export type ConnectionSection = "core" | "optional";

type AppShellProps = {
  projects: ProjectSummary[];
  selectedProject: string | null;
  activeView: ViewName;
  onProjectChange: (projectId: string) => void;
  onNavigate: (view: ViewName) => void;
  activeAuditSection?: AuditSection;
  onAuditSectionChange?: (section: AuditSection) => void;
  activeContentSection?: ContentSection;
  onContentSectionChange?: (section: ContentSection) => void;
  activeReportSection?: ReportSection;
  onReportSectionChange?: (section: ReportSection) => void;
  activeConnectionSection?: ConnectionSection;
  onConnectionSectionChange?: (section: ConnectionSection) => void;
  children: ReactNode;
};

const navigation = [
  { id: "overview" as const, label: "Home", icon: House },
  { id: "workflow" as const, label: "Plan", icon: GitBranch },
  { id: "owners" as const, label: "Owners", icon: UserRound },
  { id: "keywords" as const, label: "Keywords", icon: Tags },
  { id: "pages" as const, label: "Pages", icon: PanelsTopLeft },
  { id: "link-building" as const, label: "Link building", icon: Link2 },
  { id: "statistics" as const, label: "Statistics", icon: BarChart3 },
  { id: "audits" as const, label: "Audit", icon: ShieldCheck },
  { id: "content" as const, label: "Content", icon: FileText },
  { id: "reports" as const, label: "Reports", icon: FileChartColumn },
  { id: "integrations" as const, label: "Connections", icon: KeyRound },
  { id: "files" as const, label: "Files", icon: FolderOpen },
];

const auditSections: Array<{ id: AuditSection; label: string }> = [
  { id: "overview", label: "Summary" },
  { id: "automation", label: "Schedule" },
  { id: "url-inventory", label: "URL inventory" },
];

const reportSections: Array<{ id: ReportSection; label: string }> = [
  { id: "weekly", label: "Weekly" },
  { id: "seo-changes", label: "SEO changes" },
  { id: "presentation", label: "Presentation" },
  { id: "notify", label: "Notify" },
];

const contentSections: Array<{ id: ContentSection; label: string }> = [
  { id: "brief", label: "Brief" },
  { id: "produce", label: "Produce" },
];

const connectionSections: Array<{ id: ConnectionSection; label: string }> = [
  { id: "core", label: "Core sources" },
  { id: "optional", label: "Optional providers" },
];

const viewLabels: Record<ViewName, string> = {
  overview: "Home",
  owners: "Owners",
  keywords: "Keywords",
  pages: "Pages",
  "link-building": "Link building",
  statistics: "Statistics",
  workflow: "Plan",
  content: "Content",
  reports: "Reports",
  audits: "Audit",
  files: "Files",
  integrations: "Connections",
  tutorials: "Guides",
};

function displayHost(url: string) {
  try {
    return new URL(url).hostname.replace(/^www\./i, "");
  } catch {
    return url;
  }
}

type ExpandableNavItemProps = {
  view: ViewName;
  label: string;
  icon: React.ComponentType<{ size?: number; strokeWidth?: number }>;
  open: boolean;
  onToggle: () => void;
  subnavLabel: string;
  sections: ReadonlyArray<{ id: string; label: string }>;
  activeView: ViewName;
  activeSection: string | undefined;
  onSectionChange: (section: string) => void;
};

function ExpandableNavItem({ view, label, icon: Icon, open, onToggle, subnavLabel, sections, activeView, activeSection, onSectionChange }: ExpandableNavItemProps) {
  return (
    <div className={styles.technicalNavigation}>
      <button
        className={activeView === view ? styles.activeNav : styles.navItem}
        type="button"
        aria-expanded={open}
        onClick={onToggle}
      >
        <Icon aria-hidden="true" size={20} strokeWidth={1.5} />
        <span>{label}</span>
        {open ? <ChevronUp aria-hidden="true" size={16} /> : <ChevronDown aria-hidden="true" size={16} />}
      </button>
      {open ? (
        <div className={styles.technicalSubnav} aria-label={subnavLabel}>
          {sections.map((section) => (
            <button
              key={section.id}
              className={activeView === view && activeSection === section.id ? styles.activeTechnicalSubitem : styles.technicalSubitem}
              type="button"
              onClick={() => onSectionChange(section.id)}
            >
              {section.label}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}


export function AppShell({
  projects,
  selectedProject,
  activeView,
  onProjectChange,
  onNavigate,
  activeAuditSection = "overview",
  onAuditSectionChange,
  activeContentSection = "brief",
  onContentSectionChange,
  activeReportSection = "weekly",
  onReportSectionChange,
  activeConnectionSection = "core",
  onConnectionSectionChange,
  children,
}: AppShellProps) {
  const mobileMore = useRef<HTMLDetailsElement>(null);
  const [openViews, setOpenViews] = useState<Set<ViewName>>(() => new Set([activeView]));
  const project = projects.find((item) => item.id === selectedProject);
  const primaryMobile = navigation.filter((item) => ["overview", "keywords", "pages", "audits"].includes(item.id));
  const mobileMoreItems = [...navigation.filter((item) => !primaryMobile.includes(item)), { id: "tutorials" as const, label: "Guides" }];
  const expandable: Partial<Record<ViewName, { activeSection: string; sections: ReadonlyArray<{ id: string; label: string }>; subnavLabel: string; onSectionChange: (section: string) => void }>> = {
    audits: { activeSection: activeAuditSection, sections: auditSections, subnavLabel: "Audit sections", onSectionChange: (section) => onAuditSectionChange?.(section as AuditSection) },
    content: { activeSection: activeContentSection, sections: contentSections, subnavLabel: "Content sections", onSectionChange: (section) => onContentSectionChange?.(section as ContentSection) },
    reports: { activeSection: activeReportSection, sections: reportSections, subnavLabel: "Report sections", onSectionChange: (section) => onReportSectionChange?.(section as ReportSection) },
    integrations: { activeSection: activeConnectionSection, sections: connectionSections, subnavLabel: "Connection sections", onSectionChange: (section) => onConnectionSectionChange?.(section as ConnectionSection) },
  };
  const navigateMobile = (view: ViewName) => {
    mobileMore.current?.removeAttribute("open");
    onNavigate(view);
  };

  useEffect(() => {
    if (expandable[activeView]) setOpenViews((current) => new Set(current).add(activeView));
  }, [activeView]);

  const navigateSection = (view: ViewName, section: string) => {
    setOpenViews((current) => new Set(current).add(view));
    onNavigate(view);
    expandable[view]?.onSectionChange(section);
  };

  const renderNavItem = ({ id, label, icon: Icon }: (typeof navigation)[number]) => {
    const config = expandable[id];
    if (config) return <ExpandableNavItem key={id} view={id} label={label} icon={Icon} open={openViews.has(id)} onToggle={() => { setOpenViews((current) => { const next = new Set(current); next.has(id) ? next.delete(id) : next.add(id); return next; }); onNavigate(id); }} subnavLabel={config.subnavLabel} sections={config.sections} activeView={activeView} activeSection={config.activeSection} onSectionChange={(section) => navigateSection(id, section)} />;
    return <button key={id} className={activeView === id ? styles.activeNav : styles.navItem} type="button" onClick={() => onNavigate(id)}><Icon aria-hidden="true" size={20} strokeWidth={1.5} /><span>{label}</span></button>;
  };

  const breadcrumbSection = expandable[activeView];

  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar} aria-label="Workbench navigation">
        <div className={styles.wordmark}><img src="/seo-workbench-mark.svg" alt="" /><span>SEO Workbench</span></div>
        <label className={styles.projectPicker}>
          <span className={styles.projectMonogram}>{project?.name?.slice(0, 1).toUpperCase() || "S"}</span>
          <span className={styles.projectText}>
            <span>{project?.name || "Select project"}</span>
            <small>{project ? displayHost(project.url) : "Local workspace"}</small>
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
          <span className={styles.navGroupLabel}>Navigate</span>
          {navigation.filter(({ id }) => id !== "files" && id !== "integrations").map(renderNavItem)}
        </nav>
        <div className={styles.utilityNavigation}>
          <span className={styles.navGroupLabel}>Workspace</span>
          {navigation.filter(({ id }) => id === "files" || id === "integrations").map(renderNavItem)}
        </div>
        <div className={styles.helpNavigation}>
          <button
            className={activeView === "tutorials" ? styles.activeHelpNav : styles.helpNav}
            type="button"
            onClick={() => onNavigate("tutorials")}
            aria-current={activeView === "tutorials" ? "page" : undefined}
          >
            <span className={styles.helpGlyph} aria-hidden="true">?</span>
            <span>Guides</span>
          </button>
        </div>
      </aside>

      <header className={styles.mobileHeader}>
        <span className={styles.mobileWordmark}>SEO WORKBENCH</span>
        <details ref={mobileMore} className={styles.mobileMore}>
          <summary aria-label="More navigation"><MoreVertical aria-hidden="true" size={24} /></summary>
          <div>{mobileMoreItems.map((item) => <button key={item.id} type="button" aria-current={activeView === item.id ? "page" : undefined} onClick={() => navigateMobile(item.id)}>{item.label}</button>)}</div>
        </details>
      </header>

      <div className={styles.workspace}>
        <header className={styles.commandBar}>
          <div className={styles.mobileProject}>
            <strong>{project?.name || "SEO Workbench"}</strong>
            <span>{project ? displayHost(project.url) : "Local workspace"}</span>
          </div>
          <div className={styles.commandProject}>
            <span className={styles.commandIdentity}>
              <strong>{project?.name || "SEO Workbench"}</strong>
              <small>{project ? displayHost(project.url) : "Local workspace"}</small>
            </span>
            <span className={styles.breadcrumb}>{viewLabels[activeView]}{breadcrumbSection ? ` / ${breadcrumbSection.sections.find((section) => section.id === breadcrumbSection.activeSection)?.label || breadcrumbSection.sections[0]?.label || ""}` : ""}</span>
          </div>
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
