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
  id: "raw" | "browser" | "technology" | "performance" | "crux" | "gsc" | "diff";
  label: string;
  status: string;
};

export type GoogleCredentialProfile = {
  profile: string;
  credential_type: "oauth" | "service_account" | "unknown";
  status: "ready" | "reauth_required" | "incomplete";
  principal?: string | null;
  updated_at: string | null;
};

export type GooglePropertyBinding = {
  profile?: string;
  property?: string;
  permission_level?: string;
  bound_at?: string | null;
  status?: "invalid";
};

export type GoogleIntegration = {
  access: "local_only";
  crux: {
    status: string;
    configured: boolean;
    source: "environment" | "private_file" | "missing";
    removable: boolean;
  };
  gsc: {
    status: string;
    profiles: GoogleCredentialProfile[];
    binding: GooglePropertyBinding | null;
  };
  security: {
    secrets_returned: false;
    storage_mode: string;
    scope: string;
  };
};

export type GscProperty = {
  site_url: string;
  permission_level: string;
};

export type ShopifyIntegration = {
  access: "local_only";
  applicable: boolean;
  status: string;
  configured: boolean;
  source: "private_file" | "missing";
  shop_domain: string | null;
  shop_name: string | null;
  api_version: string;
  scopes: string[];
  write_scope_count: number;
  verified_at: string | null;
  removable: boolean;
  secret_visibility: "write_only";
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
