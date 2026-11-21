import {
  BarChart3,
  BellRing,
  CalendarClock,
  CalendarDays,
  Check,
  ChevronRight,
  CircleHelp,
  FileChartColumn,
  FileText,
  FolderOpen,
  GitBranch,
  GitCommitHorizontal,
  House,
  KeyRound,
  LayoutDashboard,
  Link2,
  ListChecks,
  MoreVertical,
  PanelLeftClose,
  PanelLeftOpen,
  PanelsTopLeft,
  PenLine,
  Plug,
  Presentation,
  Search,
  Settings,
  ShieldCheck,
  Tags,
  UserRound,
  X,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

import type { ProjectSummary } from "../api/types";
import styles from "./AppShell.module.css";

const SIDEBAR_STATE_KEY = "seo-workbench:sidebar";

const navItemClass = "flex min-h-9 w-full items-center gap-2.5 rounded-lg px-2.5 text-left text-[13px] font-medium transition-colors";
const navIdleClass = "text-ink-muted hover:bg-surface-soft hover:text-ink";
const navActiveClass = "bg-surface-soft font-semibold text-ink";

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

type NavSection = { id: string; label: string; icon: LucideIcon };

const navigation = [
  { id: "overview" as const, label: "Home", icon: House },
  { id: "workflow" as const, label: "Methods", icon: GitBranch },
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

const auditSections: NavSection[] = [
  { id: "overview", label: "Summary", icon: LayoutDashboard },
  { id: "automation", label: "Schedule", icon: CalendarClock },
  { id: "url-inventory", label: "URL inventory", icon: ListChecks },
];

const reportSections: NavSection[] = [
  { id: "weekly", label: "Weekly", icon: CalendarDays },
  { id: "seo-changes", label: "SEO changes", icon: GitCommitHorizontal },
  { id: "presentation", label: "Presentation", icon: Presentation },
  { id: "notify", label: "Notify", icon: BellRing },
];

const contentSections: NavSection[] = [
  { id: "brief", label: "Brief", icon: FileText },
  { id: "produce", label: "Produce", icon: PenLine },
];

const connectionSections: NavSection[] = [
  { id: "core", label: "Core sources", icon: KeyRound },
  { id: "optional", label: "Optional providers", icon: Plug },
];

const viewLabels: Record<ViewName, string> = {
  overview: "Home",
  owners: "Owners",
  keywords: "Keywords",
  pages: "Pages",
  "link-building": "Link building",
  statistics: "Statistics",
  workflow: "Methods",
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

function readCollapsedState() {
  try {
    return window.localStorage.getItem(SIDEBAR_STATE_KEY) === "collapsed";
  } catch {
    return false;
  }
}

function NavIcon({ icon: Icon }: { icon: LucideIcon }) {
  return <Icon aria-hidden="true" size={18} strokeWidth={1.7} className="shrink-0" />;
}

type NavButtonProps = {
  active: boolean;
  collapsed: boolean;
  current?: boolean;
  expanded?: boolean;
  hasPopup?: "dialog";
  icon: LucideIcon;
  label: string;
  onClick: () => void;
  showChevron?: boolean;
};

/** One sidebar row: icon, label, and an optional disclosure chevron. */
function NavButton({ active, collapsed, current = true, expanded, hasPopup, icon: Icon, label, onClick, showChevron = false }: NavButtonProps) {
  const button = (
    <button
      type="button"
      aria-current={active && current ? "page" : undefined}
      aria-expanded={showChevron ? expanded : undefined}
      aria-haspopup={hasPopup}
      onClick={onClick}
      className={cn(navItemClass, active ? navActiveClass : navIdleClass, expanded && !active && "font-semibold text-ink", collapsed && "size-9 min-h-9 justify-center px-0")}
    >
      <NavIcon icon={Icon} />
      <span className={cn("truncate", collapsed && "sr-only")}>{label}</span>
      {showChevron ? (
        <ChevronRight
          aria-hidden="true"
          size={16}
          className={cn("ml-auto shrink-0 text-ink-muted transition-transform duration-150", expanded && "rotate-90", collapsed && "hidden")}
        />
      ) : null}
    </button>
  );

  if (!collapsed) return button;
  return (
    <Tooltip>
      <TooltipTrigger asChild>{button}</TooltipTrigger>
      <TooltipContent side="right" sideOffset={10}>{label}</TooltipContent>
    </Tooltip>
  );
}

type ExpandableNavItemProps = {
  view: ViewName;
  label: string;
  icon: LucideIcon;
  open: boolean;
  onToggle: () => void;
  subnavLabel: string;
  sections: ReadonlyArray<NavSection>;
  activeView: ViewName;
  activeSection: string | undefined;
  onSectionChange: (section: string) => void;
  collapsed: boolean;
};

function ExpandableNavItem({ view, label, icon, open, onToggle, subnavLabel, sections, activeView, activeSection, onSectionChange, collapsed }: ExpandableNavItemProps) {
  return (
    <div>
      <NavButton
        active={activeView === view && !open}
        collapsed={collapsed}
        expanded={open}
        icon={icon}
        label={label}
        onClick={onToggle}
        showChevron
      />
      {open && !collapsed ? (
        <div className={styles.subnav} aria-label={subnavLabel}>
          {sections.map((section) => {
            const SectionIcon = section.icon;
            const isActive = activeView === view && activeSection === section.id;
            return (
              <button
                key={section.id}
                type="button"
                aria-current={isActive ? "page" : undefined}
                onClick={() => onSectionChange(section.id)}
                className={isActive ? styles.subnavItemActive : styles.subnavItem}
              >
                <SectionIcon aria-hidden="true" size={16} strokeWidth={1.7} className="shrink-0" />
                <span className="truncate">{section.label}</span>
              </button>
            );
          })}
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
  const searchRef = useRef<HTMLInputElement>(null);
  const settingsTrigger = useRef<HTMLDivElement>(null);
  const [openViews, setOpenViews] = useState<Set<ViewName>>(() => new Set([activeView]));
  const [collapsed, setCollapsed] = useState(readCollapsedState);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const project = projects.find((item) => item.id === selectedProject);
  const primaryMobile = navigation.filter((item) => ["overview", "keywords", "pages", "audits"].includes(item.id));
  const mobileMoreItems = [...navigation.filter((item) => !primaryMobile.includes(item)), { id: "tutorials" as const, label: "Guides" }];
  const expandable: Partial<Record<ViewName, { activeSection: string; sections: ReadonlyArray<NavSection>; subnavLabel: string; onSectionChange: (section: string) => void }>> = {
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

  useEffect(() => {
    try {
      window.localStorage.setItem(SIDEBAR_STATE_KEY, collapsed ? "collapsed" : "expanded");
    } catch {
      // The sidebar still works when storage is unavailable.
    }
  }, [collapsed]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setCollapsed(false);
        requestAnimationFrame(() => searchRef.current?.focus());
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const toggleCollapsed = () => {
    const next = !collapsed;
    setCollapsed(next);
    if (next) setQuery("");
  };

  const expandSearch = () => {
    setCollapsed(false);
    requestAnimationFrame(() => searchRef.current?.focus());
  };

  const normalizedQuery = query.trim().toLowerCase();
  const queryActive = normalizedQuery.length > 0;
  const matches = (label: string) => label.toLowerCase().includes(normalizedQuery);
  const isVisible = (id: ViewName, label: string) =>
    !queryActive || matches(label) || (expandable[id]?.sections.some((section) => matches(section.label)) ?? false);
  const primaryNavigation = navigation.filter(({ id, label }) => id !== "files" && id !== "integrations" && isVisible(id, label));
  const workspaceNavigation = navigation.filter(({ id, label }) => (id === "files" || id === "integrations") && isVisible(id, label));
  const noMatches = queryActive && primaryNavigation.length === 0 && workspaceNavigation.length === 0;

  const navigateSection = (view: ViewName, section: string) => {
    setOpenViews((current) => new Set(current).add(view));
    onNavigate(view);
    expandable[view]?.onSectionChange(section);
  };

  const renderNavItem = ({ id, label, icon: Icon }: (typeof navigation)[number]) => {
    const config = expandable[id];
    if (config) {
      const sections = queryActive
        ? matches(label)
          ? config.sections
          : config.sections.filter((section) => matches(section.label))
        : config.sections;
      return (
        <ExpandableNavItem
          key={id}
          view={id}
          label={label}
          icon={Icon}
          open={queryActive || openViews.has(id)}
          onToggle={() => {
            if (collapsed) setCollapsed(false);
            setOpenViews((current) => {
              const next = new Set(current);
              next.has(id) ? next.delete(id) : next.add(id);
              return next;
            });
            onNavigate(id);
          }}
          subnavLabel={config.subnavLabel}
          sections={sections}
          activeView={activeView}
          activeSection={config.activeSection}
          onSectionChange={(section) => navigateSection(id, section)}
          collapsed={collapsed}
        />
      );
    }
    return (
      <NavButton
        key={id}
        active={activeView === id}
        collapsed={collapsed}
        icon={Icon}
        label={label}
        onClick={() => onNavigate(id)}
      />
    );
  };

  const breadcrumbSection = expandable[activeView];

  return (
    <div className={styles.shell} data-collapsed={collapsed ? "true" : undefined}>
      <aside aria-label="Workbench navigation" className={cn(styles.sidebar, "sticky top-3 mx-3 flex h-[calc(100vh-24px)] w-[var(--sidebar-width)] shrink-0 flex-col overflow-hidden rounded-2xl border border-separator bg-surface shadow-[0_1px_2px_rgba(16,24,40,0.04),0_16px_40px_rgba(16,24,40,0.07)] transition-[width] duration-200 ease-out")}>
        <div className={cn("px-2 pb-2", collapsed ? "flex flex-col items-center gap-1 px-0 pt-2" : "flex items-center gap-1.5 pt-3")}>
          {collapsed ? (
            <>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button type="button" aria-label="Expand sidebar" onClick={() => setCollapsed(false)} className="grid size-9 place-items-center rounded-lg text-ink-muted transition-colors hover:bg-surface-soft hover:text-ink">
                    <PanelLeftOpen aria-hidden="true" size={18} strokeWidth={1.7} />
                  </button>
                </TooltipTrigger>
                <TooltipContent side="right" sideOffset={10}>Expand sidebar</TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button type="button" aria-label="Search navigation" onClick={expandSearch} className="grid size-9 place-items-center rounded-lg text-ink-muted transition-colors hover:bg-surface-soft hover:text-ink">
                    <Search aria-hidden="true" size={18} strokeWidth={1.7} />
                  </button>
                </TooltipTrigger>
                <TooltipContent side="right" sideOffset={10}>Search navigation</TooltipContent>
              </Tooltip>
            </>
          ) : (
            <>
              <div className="relative min-w-0 flex-1">
                <Search aria-hidden="true" size={15} strokeWidth={1.8} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-ink-muted" />
                <input
                  ref={searchRef}
                  type="search"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  onKeyDown={(event) => { if (event.key === "Escape") setQuery(""); }}
                  aria-label="Search navigation"
                  placeholder="Search"
                  className="h-9 w-full rounded-lg border border-separator-strong bg-canvas pl-8 pr-14 text-[13px] text-ink placeholder:text-muted-foreground focus:border-primary focus:bg-surface focus:outline-none focus:ring-2 focus:ring-primary-wash"
                />
                {query ? (
                  <button type="button" aria-label="Clear search" onClick={() => setQuery("")} className="absolute right-1.5 top-1/2 grid size-6 -translate-y-1/2 place-items-center rounded-md text-ink-muted transition-colors hover:bg-surface-soft hover:text-ink">
                    <X aria-hidden="true" size={14} />
                  </button>
                ) : (
                  <kbd className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 rounded border border-separator-strong bg-surface px-1.5 py-0.5 font-mono text-[10px] leading-none text-ink-muted">Ctrl K</kbd>
                )}
              </div>
              <button type="button" aria-label="Collapse sidebar" onClick={toggleCollapsed} className="grid size-8 shrink-0 place-items-center rounded-lg text-muted-foreground transition-colors hover:bg-surface-soft hover:text-ink">
                <PanelLeftClose aria-hidden="true" size={17} strokeWidth={1.7} />
              </button>
            </>
          )}
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-2 pb-2">
          {primaryNavigation.length > 0 ? (
            <nav aria-label="Workbench" className={cn("grid gap-0.5", collapsed && "justify-items-center")}>
              {!collapsed ? <p className="px-2 pb-1 pt-2 font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-ink-muted">Navigate</p> : null}
              {primaryNavigation.map(renderNavItem)}
            </nav>
          ) : null}
          {workspaceNavigation.length > 0 ? (
            <nav aria-label="Workspace" className={cn("mt-3 grid gap-0.5", collapsed && "justify-items-center")}>
              {!collapsed ? <p className="px-2 pb-1 pt-2 font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-ink-muted">Workspace</p> : null}
              {workspaceNavigation.map(renderNavItem)}
            </nav>
          ) : null}
          {noMatches ? <p className="px-2 py-6 text-center text-xs text-muted-foreground">No matches</p> : null}
        </div>

        <div ref={settingsTrigger} className="grid gap-0.5 p-2">
          <NavButton active={settingsOpen} current={false} collapsed={collapsed} hasPopup="dialog" icon={Settings} label="Settings" onClick={() => setSettingsOpen(true)} />
          <NavButton active={activeView === "tutorials"} collapsed={collapsed} icon={CircleHelp} label="Guides" onClick={() => onNavigate("tutorials")} />
        </div>
      </aside>

      <Dialog open={settingsOpen} onOpenChange={setSettingsOpen}>
        <DialogContent
          aria-describedby="settings-description"
          onCloseAutoFocus={(event) => {
            event.preventDefault();
            settingsTrigger.current?.querySelector("button")?.focus();
          }}
        >
          <DialogHeader>
            <DialogTitle asChild><h3>Settings</h3></DialogTitle>
            <DialogDescription id="settings-description">Choose the project this workspace uses.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-2">
            <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-ink-muted">Project</p>
            <div role="radiogroup" aria-label="Project" className="grid max-h-[50vh] gap-1 overflow-y-auto">
              {projects.length > 0 ? projects.map((item) => {
                const selected = item.id === selectedProject;
                return (
                  <button
                    key={item.id}
                    type="button"
                    role="radio"
                    aria-checked={selected}
                    onClick={() => {
                      onProjectChange(item.id);
                      setSettingsOpen(false);
                    }}
                    className={cn(
                      "flex items-center gap-3 rounded-lg border px-3 py-2.5 text-left transition-colors",
                      selected ? "border-primary bg-primary-wash" : "border-separator hover:border-separator-strong hover:bg-surface-soft",
                    )}
                  >
                    <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-graphite font-mono text-[11px] font-medium text-white">{(item.name || item.id).slice(0, 1).toUpperCase()}</span>
                    <span className="grid min-w-0 flex-1 gap-0.5">
                      <span className="truncate text-[13px] font-semibold text-ink">{item.name || item.id}</span>
                      <small className="truncate text-[11px] font-normal text-muted-foreground">{displayHost(item.url)}</small>
                    </span>
                    {selected ? <Check aria-hidden="true" size={16} className="shrink-0 text-primary" /> : null}
                  </button>
                );
              }) : <p className="py-4 text-center text-xs text-muted-foreground">No projects available.</p>}
            </div>
          </div>
        </DialogContent>
      </Dialog>

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
