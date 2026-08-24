import type { ContentJobAction, Job } from "../../api/types";
import type { ReportSection } from "../../components/AppShell";
import { NotifySection } from "./NotifySection";
import { PresentationSection } from "./PresentationSection";
import { SeoChangesSection } from "./SeoChangesSection";
import { WeeklySection } from "./WeeklySection";

type Props = {
  projectId: string;
  jobs: Job[];
  refreshKey: number;
  section: ReportSection;
  onOpenFile: (path: string) => void;
  onRunContentAction: (action: ContentJobAction) => Promise<void>;
  onRunPresentation?: () => Promise<void>;
};

export function ReportsPage({ projectId, jobs, refreshKey, section, onOpenFile, onRunContentAction, onRunPresentation }: Props) {
  if (section === "notify") {
    return <NotifySection projectId={projectId} jobs={jobs} refreshKey={refreshKey} onOpenFile={onOpenFile} onRunContentAction={onRunContentAction} />;
  }
  if (section === "presentation") return <PresentationSection projectId={projectId} jobs={jobs} refreshKey={refreshKey} onRunPresentation={onRunPresentation || (() => onRunContentAction({ action: "presentation-weekly" }))} />;
  if (section === "seo-changes") return <SeoChangesSection projectId={projectId} refreshKey={refreshKey} />;
  return <WeeklySection projectId={projectId} jobs={jobs} refreshKey={refreshKey} onOpenFile={onOpenFile} onRunContentAction={onRunContentAction} />;
}
