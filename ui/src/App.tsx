import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from "react";

import type { WorkbenchEvent } from "./api/types";
import { AppShell, type ViewName } from "./components/AppShell";
import { FilesPage } from "./features/files/FilesPage";
import { OverviewPage } from "./features/overview/OverviewPage";
import { WorkflowPage } from "./features/workflow/WorkflowPage";
import { useProjects, useWorkbenchEvents, useWorkspace } from "./hooks/useWorkbenchData";

const MarkdownWorkspace = lazy(() => import("./features/editor/MarkdownWorkspace"));
const VIEWS = new Set<ViewName>(["overview", "workflow", "content", "audits", "files"]);

function viewFromHash(): ViewName {
  const value = window.location.hash.replace(/^#\/?/, "").split("/")[0] as ViewName;
  return VIEWS.has(value) ? value : "overview";
}

export function App() {
  const { projects, error: projectError } = useProjects();
  const [selectedProject, setSelectedProject] = useState<string | null>(() => new URLSearchParams(window.location.search).get("project"));
  const [activeView, setActiveView] = useState<ViewName>(viewFromHash);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [connected, setConnected] = useState(false);
  const [updatedPaths, setUpdatedPaths] = useState<Record<string, string>>({});
  const { workspace, error: workspaceError, loading } = useWorkspace(selectedProject, refreshKey);

  useEffect(() => {
    if (!selectedProject && projects.length > 0) setSelectedProject(projects[0].id);
    if (selectedProject && projects.length > 0 && !projects.some((project) => project.id === selectedProject)) {
      setSelectedProject(projects[0].id);
    }
  }, [projects, selectedProject]);

  useEffect(() => {
    const onHashChange = () => setActiveView(viewFromHash());
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  const onEvent = useCallback((event: WorkbenchEvent) => {
    if (event.project_id && event.project_id !== selectedProject) return;
    setRefreshKey((value) => value + 1);
    if (event.path) setUpdatedPaths((value) => ({ ...value, [event.path!]: event.at }));
  }, [selectedProject]);
  const onConnection = useCallback((value: boolean) => setConnected(value), []);
  useWorkbenchEvents(onEvent, onConnection);

  const navigate = useCallback((view: ViewName) => {
    window.location.hash = `/${view}`;
    setActiveView(view);
    if (view !== "files" && view !== "content" && view !== "audits") setSelectedFile(null);
  }, []);

  const openFile = useCallback((path: string) => {
    setSelectedFile(path);
    const view: ViewName = path.startsWith("content/") ? "content" : path.startsWith("audits/") ? "audits" : "files";
    navigate(view);
  }, [navigate]);

  const fileRoot = useMemo(() => activeView === "content" ? "content" : activeView === "audits" ? "audits" : undefined, [activeView]);
  const error = projectError || workspaceError;

  if (error && projects.length === 0) return <div className="error-screen" role="alert">{error}</div>;
  if (!selectedProject || (!workspace && loading)) return <div className="loading-screen"><span>Opening local workbench</span></div>;

  return (
    <AppShell
      projects={projects}
      selectedProject={selectedProject}
      activeView={activeView}
      connected={connected}
      onProjectChange={(projectId) => { setSelectedProject(projectId); setSelectedFile(null); }}
      onNavigate={navigate}
      onRunAudit={() => navigate("audits")}
    >
      {workspace ? (
        <>
          {activeView === "overview" ? <OverviewPage workspace={workspace} updatedPaths={updatedPaths} onNavigateWorkflow={() => navigate("workflow")} onOpenFile={openFile} /> : null}
          {activeView === "workflow" ? <WorkflowPage workspace={workspace} /> : null}
          {activeView === "files" || activeView === "content" || activeView === "audits" ? (
            selectedFile ? (
              <Suspense fallback={<div className="loading-screen"><span>Loading editor</span></div>}>
                <MarkdownWorkspace projectId={selectedProject} path={selectedFile} onBack={() => setSelectedFile(null)} />
              </Suspense>
            ) : (
              <FilesPage projectId={selectedProject} root={fileRoot} refreshKey={refreshKey} onOpenFile={openFile} />
            )
          ) : null}
        </>
      ) : <div className="error-screen" role="alert">{error || "Project workspace is unavailable."}</div>}
    </AppShell>
  );
}
