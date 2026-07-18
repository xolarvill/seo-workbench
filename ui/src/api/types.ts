export type ProjectSummary = {
  id: string;
  path: string;
  name: string;
  url: string;
  type: string;
  phase: string;
  selectable: boolean;
  valid_state: boolean;
  error?: string;
};

export type EvidenceItem = {
  id: "raw" | "technology" | "performance" | "crux" | "gsc" | "diff";
  label: string;
  status: string;
};

export type FileSummary = {
  path: string;
  name: string;
  size: number;
  modified_at: string;
};

export type WorkflowStep = {
  id: string;
  label: string;
  status: string;
  skip_reason?: string;
};

export type PhaseState = {
  status: string;
  steps: WorkflowStep[];
};

export type NextContract = {
  phase: string;
  step: string;
  label: string;
  skill: string;
  context: string[];
  output: string;
};

export type Workspace = {
  project_id: string;
  project: {
    name: string;
    url: string;
    type: string;
    description?: string;
  };
  phase: string;
  step: WorkflowStep | null;
  next: NextContract | null;
  phase_order: string[];
  phases: Record<string, PhaseState>;
  evidence: {
    items: EvidenceItem[];
    performance: {
      score: number | null;
      high_variance: boolean | null;
      metrics: { lcp: number | null; tbt: number | null; cls: number | null };
    };
    technology: {
      summary?: string;
      layers?: Record<string, string[]>;
      seo_impacts?: Array<{ area: string; risk: string; conclusion: string }>;
    };
    diff: { changes?: number; regressions?: number; improvements?: number };
  };
  recent_files: FileSummary[];
};

export type MarkdownFile = {
  path: string;
  content: string;
  revision: string;
  modified_at: string;
};

export type TutorialSummary = {
  slug: string;
  title: string;
  description: string;
  category: string;
  source: string;
};

export type TutorialDocument = TutorialSummary & {
  content: string;
  revision: string;
  modified_at: string;
};

export type WorkbenchEvent = {
  type: string;
  project_id?: string;
  path?: string;
  revision?: string;
  job?: Job;
  at: string;
};

export type Job = {
  id: string;
  project_id: string;
  action: string;
  status: "queued" | "running" | "succeeded" | "failed" | "cancelled";
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  exit_code: number | null;
  output: string;
};
