import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from "react";

import { fetchJobs, startAction, startContentAction, updateContentStatus, updateWorkflow } from "./api/client";
import type { ContentJobAction, Job, WorkbenchEvent } from "./api/types";
import { AppShell, type AuditSection, type ConnectionSection, type ContentSection, type ReportSection, type ViewName } from "./components/AppShell";
import { ActionPanel } from "./features/actions/ActionPanel";
import { ContentWorkbenchPage } from "./features/content/ContentWorkbenchPage";
import { FilesPage } from "./features/files/FilesPage";
import { OverviewPage } from "./features/overview/OverviewPage";
import { OwnersPage } from "./features/owners/OwnersPage";
import { PagesWorkbenchPage } from "./features/pages/PagesWorkbenchPage";
import { LinkBuildingPage } from "./features/link-building/LinkBuildingPage";
import { ReportsPage } from "./features/reports/ReportsPage";
import { StatisticsPage } from "./features/statistics/StatisticsPage";
import { TechnicalAuditPage } from "./features/technical-audit/TechnicalAuditPage";
import { TutorialsPage } from "./features/tutorials/TutorialsPage";
import { WorkflowPage } from "./features/workflow/WorkflowPage";
import { useProjects, useWorkbenchEvents, useWorkspace } from "./hooks/useWorkbenchData";

const MarkdownOverlay = lazy(() => import("./features/editor/MarkdownOverlay"));
const IntegrationsPage = lazy(() => import("./features/integrations/IntegrationsPage").then((module) => ({ default: module.IntegrationsPage })));
const KeywordsWorkbenchPage = lazy(() => import("./features/keywords/KeywordsWorkbenchPage").then((module) => ({ default: module.KeywordsWorkbenchPage })));
const VIEWS = new Set<ViewName>(["overview", "owners", "keywords", "pages", "link-building", "statistics", "workflow", "content", "reports", "audits", "files", "integrations", "tutorials"]);
const AUDIT_SECTIONS = new Set<AuditSection>(["overview", "automation", "url-inventory", "crawl-comparison", "redirects", "sitemaps", "logs"]);

function hashRoute() {
  const [path, query = ""] = window.location.hash.replace(/^#\/?/, "").split("?", 2);
  return { parts: path.split("/"), params: new URLSearchParams(query) };
}

type HashRoute = ReturnType<typeof hashRoute>;

function viewFromRoute(route: HashRoute): ViewName {
  const value = route.parts[0] as ViewName;
  return VIEWS.has(value) ? value : "overview";
}

function auditSectionFromRoute(route: HashRoute): AuditSection {
  const rawValue = route.parts[1];
  const value = rawValue === "issues" ? "url-inventory" : rawValue as AuditSection;
  return AUDIT_SECTIONS.has(value) ? value : "overview";
}

function reportSectionFromRoute(route: HashRoute): ReportSection {
  return route.parts[1] === "notify" ? "notify" : route.parts[1] === "seo-changes" ? "seo-changes" : "weekly";
}

function contentSectionFromRoute(route: HashRoute): ContentSection {
  return route.parts[1] === "produce" || route.params.has("item") ? "produce" : "brief";
}

function connectionSectionFromRoute(route: HashRoute): ConnectionSection {
  return route.parts[1] === "optional" ? "optional" : "core";
}

function fileView(path: string): ViewName {
  if (path.startsWith("strategy/owners/")) return "owners";
  if (path.startsWith("reports/") || path.startsWith("content/reports/")) return "reports";
  if (path.startsWith("strategy/briefs/") || path.startsWith("strategy/keyword-dives/")) return "content";
  if (path.startsWith("content/")) return "content";
  if (path.startsWith("audits/")) return "audits";
  return "files";
}

export function App() {
  const { projects, error: projectError } = useProjects();
  const [selectedProject, setSelectedProject] = useState<string | null>(() => new URLSearchParams(window.location.search).get("project"));
  const [route, setRoute] = useState<HashRoute>(hashRoute);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [updatedPaths, setUpdatedPaths] = useState<Record<string, string>>({});
  const [jobs, setJobs] = useState<Job[]>([]);
  const [actionsOpen, setActionsOpen] = useState(false);
  const { workspace, error: workspaceError, loading } = useWorkspace(selectedProject, refreshKey);
  const activeView = viewFromRoute(route);
  const activeAuditSection = auditSectionFromRoute(route);
  const activeContentSection = contentSectionFromRoute(route);
  const activeReportSection = reportSectionFromRoute(route);
  const activeConnectionSection = connectionSectionFromRoute(route);
  const routeParams = route.params;

  useEffect(() => {
    if (!selectedProject && projects.length > 0) setSelectedProject(projects[0].id);
    if (selectedProject && projects.length > 0 && !projects.some((project) => project.id === selectedProject)) {
      setSelectedProject(projects[0].id);
    }
  }, [projects, selectedProject]);

  useEffect(() => {
    if (!selectedProject) return;
    const params = new URLSearchParams(window.location.search);
    if (params.get("project") === selectedProject) return;
    params.set("project", selectedProject);
    window.history.replaceState(null, "", `${window.location.pathname}?${params}${window.location.hash}`);
  }, [selectedProject]);

  useEffect(() => {
    if (!selectedProject) return;
    let cancelled = false;
    setJobs([]);
    fetchJobs(selectedProject).then((value) => { if (!cancelled) setJobs(value); }).catch(() => { if (!cancelled) setJobs([]); });
    return () => { cancelled = true; };
  }, [selectedProject]);

  useEffect(() => {
    const onHashChange = () => setRoute(hashRoute());
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  const onEvent = useCallback((event: WorkbenchEvent) => {
    if (event.project_id && event.project_id !== selectedProject) return;
    setRefreshKey((value) => value + 1);
    if (event.path) setUpdatedPaths((value) => ({ ...value, [event.path!]: event.at }));
    if (event.job) setJobs((value) => [event.job!, ...value.filter((job) => job.id !== event.job!.id)]);
  }, [selectedProject]);
  useWorkbenchEvents(onEvent);

  const navigate = useCallback((view: ViewName, preserveFile = false) => {
    window.location.hash = `/${view}`;
    setRoute(hashRoute());
    if (!preserveFile && view !== "files" && view !== "content" && view !== "audits") setSelectedFile(null);
  }, []);

  const navigateAuditSection = useCallback((section: AuditSection) => {
    window.location.hash = `/audits/${section}`;
    setRoute(hashRoute());
    setSelectedFile(null);
  }, []);

  const navigateReportSection = useCallback((section: ReportSection) => {
    window.location.hash = `/reports/${section}`;
    setRoute(hashRoute());
    setSelectedFile(null);
  }, []);

  const navigateContentSection = useCallback((section: ContentSection) => {
    window.location.hash = `/content/${section}`;
    setRoute(hashRoute());
    setSelectedFile(null);
  }, []);

  const navigateConnectionSection = useCallback((section: ConnectionSection) => {
    window.location.hash = `/integrations/${section}`;
    setRoute(hashRoute());
    setSelectedFile(null);
  }, []);

  const navigatePages = useCallback((filters: { group: string; source: string }) => {
    const query = new URLSearchParams(filters).toString();
    window.location.hash = `/pages?${query}`;
    setRoute(hashRoute());
    setSelectedFile(null);
  }, []);

  const openFile = useCallback((path: string) => {
    setSelectedFile(path);
    if (path.startsWith("strategy/owners/")) {
      window.location.hash = "/owners";
      setRoute(hashRoute());
      return;
    }
    if (path.startsWith("reports/") || path.startsWith("content/reports/")) {
      window.location.hash = `/reports/${activeReportSection}`;
      setRoute(hashRoute());
      return;
    }
    navigate(fileView(path), true);
  }, [navigate, activeReportSection]);

  const fileRoot = useMemo(() => activeView === "content" ? "content" : activeView === "audits" ? "audits" : undefined, [activeView]);
  const error = projectError || workspaceError;

  const runAuditAction = useCallback(async (action: string) => {
    if (!selectedProject) throw new Error("Select a project before running evidence.");
    const job = await startAction(selectedProject, action);
    setJobs((value) => [job, ...value.filter((item) => item.id !== job.id)]);
    setRefreshKey((value) => value + 1);
  }, [selectedProject]);

  const runTechAuditRecrawl = useCallback(async (urls: string[]) => {
    if (!selectedProject) throw new Error("Select a project before re-crawling URLs.");
    const job = await startAction(selectedProject, "tech-audit-recrawl", urls);
    setJobs((value) => [job, ...value.filter((item) => item.id !== job.id)]);
    setRefreshKey((value) => value + 1);
  }, [selectedProject]);

  const continueTechAudit = useCallback(async () => {
    await runAuditAction("tech-audit-continue");
  }, [runAuditAction]);

  const runContentAction = useCallback(async (action: ContentJobAction) => {
    if (!selectedProject) throw new Error("Select a project before running content actions.");
    const job = await startContentAction(selectedProject, action);
    setJobs((value) => [job, ...value.filter((item) => item.id !== job.id)]);
  }, [selectedProject]);

  const changeContentStatus = useCallback(async (itemId: string, status: string, note: string) => {
    if (!selectedProject) throw new Error("Select a project before updating content.");
    await updateContentStatus(selectedProject, itemId, status, note);
    setRefreshKey((value) => value + 1);
  }, [selectedProject]);

  if (error && projects.length === 0) return <div className="error-screen" role="alert">{error}</div>;
  if (!selectedProject || (!workspace && loading)) return <div className="loading-screen"><span>Opening local workbench</span></div>;

  return (
    <AppShell
      projects={projects}
      selectedProject={selectedProject}
      activeView={activeView}
      onProjectChange={(projectId) => {
        setSelectedProject(projectId);
        setSelectedFile(null);
        window.location.hash = activeView === "audits" ? `/audits/${activeAuditSection}` : activeView === "content" ? `/content/${activeContentSection}` : activeView === "integrations" ? `/integrations/${activeConnectionSection}` : `/${activeView}`;
        setRoute(hashRoute());
      }}
      onNavigate={navigate}
      activeAuditSection={activeAuditSection}
      onAuditSectionChange={navigateAuditSection}
      activeContentSection={activeContentSection}
      onContentSectionChange={navigateContentSection}
      activeReportSection={activeReportSection}
      onReportSectionChange={navigateReportSection}
      activeConnectionSection={activeConnectionSection}
      onConnectionSectionChange={navigateConnectionSection}
    >
      {workspace ? (
        <>
          {activeView === "overview" ? <OverviewPage workspace={workspace} updatedPaths={updatedPaths} onNavigateWorkflow={() => navigate("workflow")} onNavigatePages={navigatePages} onOpenFile={openFile} /> : null}
          {activeView === "owners" ? <OwnersPage projectId={selectedProject} refreshKey={refreshKey} onOpenFile={openFile} /> : null}
          {activeView === "keywords" ? <Suspense fallback={<div className="loading-screen"><span>Opening keyword evidence</span></div>}><KeywordsWorkbenchPage projectId={selectedProject} refreshKey={refreshKey} refreshing={jobs.some((job) => job.action === "statistics-collect" && ["queued", "running"].includes(job.status))} initialQuery={routeParams.get("q") || ""} onRefresh={() => runAuditAction("statistics-collect")} onOpenFile={openFile} /></Suspense> : null}
          {activeView === "pages" ? <PagesWorkbenchPage projectId={selectedProject} refreshKey={refreshKey} refreshing={jobs.some((job) => job.action === "pages-refresh" && ["queued", "running"].includes(job.status))} initialGroup={routeParams.get("group") || "now"} initialSource={routeParams.get("source") || ""} initialQuery={routeParams.get("q") || ""} onRefresh={() => runAuditAction("pages-refresh")} onUpdated={() => setRefreshKey((value) => value + 1)} /> : null}
          {activeView === "link-building" ? <LinkBuildingPage projectId={selectedProject} refreshKey={refreshKey} /> : null}
          {activeView === "statistics" ? <StatisticsPage projectId={selectedProject} refreshKey={refreshKey} refreshing={jobs.some((job) => job.action === "statistics-collect" && ["queued", "running"].includes(job.status))} onRefresh={() => runAuditAction("statistics-collect")} onNavigatePages={navigatePages} /> : null}
          {activeView === "workflow" ? <WorkflowPage workspace={workspace} onOpenActions={() => setActionsOpen(true)} onOpenKeywords={() => navigate("keywords")} onOpenContent={() => navigate("content")} onStepAction={async (action) => {
            await updateWorkflow(selectedProject, action, workspace.step?.id);
            setRefreshKey((value) => value + 1);
          }} /> : null}
          {activeView === "tutorials" ? <TutorialsPage /> : null}
          {activeView === "integrations" ? (
            <Suspense fallback={<div className="loading-screen"><span>Opening integrations</span></div>}>
              <IntegrationsPage projectId={selectedProject} refreshKey={refreshKey} section={activeConnectionSection} onRunAction={runAuditAction} />
            </Suspense>
          ) : null}
          {activeView === "content" ? (
            <ContentWorkbenchPage
              key={activeContentSection}
              projectId={selectedProject}
              section={activeContentSection}
              workspace={workspace}
              jobs={jobs}
              refreshKey={refreshKey}
              onOpenFile={openFile}
              onRunContentAction={runContentAction}
              onUpdateStatus={changeContentStatus}
              initialItemId={routeParams.get("item")}
            />
          ) : null}
          {activeView === "reports" ? <ReportsPage projectId={selectedProject} jobs={jobs} refreshKey={refreshKey} section={activeReportSection} onOpenFile={openFile} onRunContentAction={runContentAction} /> : null}
          {activeView === "audits" ? (
            <TechnicalAuditPage
              projectId={selectedProject}
              jobs={jobs}
              refreshKey={refreshKey}
              onRunFull={() => runAuditAction("tech-audit")}
              onContinue={continueTechAudit}
              onRecrawl={runTechAuditRecrawl}
              auditSection={activeAuditSection}
              viewerDataset={routeParams.get("dataset") === "issues" ? "issues" : routeParams.get("dataset") === "links" ? "links" : "pages"}
              viewerKey={routeParams.get("key")}
              viewerRuleId={routeParams.get("rule_id")}
              viewerTemplate={routeParams.get("template")}
            />
          ) : activeView === "files" ? (
            <FilesPage projectId={selectedProject} root={fileRoot} refreshKey={refreshKey} onOpenFile={openFile} />
          ) : null}
        </>
      ) : <div className="error-screen" role="alert">{error || "Project workspace is unavailable."}</div>}
      {selectedFile && fileView(selectedFile) === activeView ? (
        <Suspense fallback={null}>
          <MarkdownOverlay projectId={selectedProject} path={selectedFile} onClose={() => setSelectedFile(null)} />
        </Suspense>
      ) : null}
      <ActionPanel
        open={actionsOpen}
        jobs={jobs}
        onClose={() => setActionsOpen(false)}
        onRun={(action) => {
          runAuditAction(action)
            .catch((reason: Error) => setJobs((value) => [{ id: `error-${Date.now()}`, project_id: selectedProject, action, status: "failed", created_at: new Date().toISOString(), started_at: null, finished_at: new Date().toISOString(), exit_code: null, output: reason.message }, ...value]));
        }}
      />
    </AppShell>
  );
}
