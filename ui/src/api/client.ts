import type { BacklinkViewResponse, ContentJobAction, ContentQueueSummary, ContentQueueItem, DataForSeoIntegration, FileSummary, Ga4Property, GoogleIntegration, GscProperty, Job, KeywordDataset, KeywordHandoff, KeywordPatch, KeywordViewResponse, MarkdownFile, PageDataset, PageDetailResponse, PageViewResponse, ProjectSummary, ReportArchive, ReportArchiveParams, SeoChangeCreate, SeoChangesResponse, ShopifyIntegration, StatisticsResponse, TechAuditData, TechAuditDataset, TechAuditDetailResponse, TechAuditSchedule, TechAuditViewResponse, TutorialDocument, TutorialSummary, Workspace } from "./types";


export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, message: string, detail: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = window.sessionStorage.getItem("seo_workbench_token");
  const response = await fetch(path, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options?.headers },
    ...options,
  });
  const raw = await response.text();
  let payload: ({ detail?: unknown } & T) | null = null;
  try {
    payload = (raw ? JSON.parse(raw) : {}) as { detail?: unknown } & T;
  } catch {
    throw new ApiError(response.status, `Workbench returned an invalid response (${response.status}).`, null);
  }
  if (!response.ok) {
    const detail = payload.detail;
    const message = typeof detail === "string"
      ? detail
      : Array.isArray(detail) && typeof detail[0]?.msg === "string"
        ? detail[0].msg
        : detail && typeof detail === "object" && "message" in detail && typeof detail.message === "string"
          ? detail.message
          : `Workbench request failed with ${response.status}`;
    throw new ApiError(response.status, message, detail);
  }
  return payload;
}

function queryString<T extends object>(params: T) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") search.set(key, String(value));
  });
  return search.toString();
}

export async function fetchProjects(): Promise<ProjectSummary[]> {
  const payload = await request<{ projects: ProjectSummary[] }>("/api/v1/projects");
  return payload.projects;
}

export async function fetchWorkspace(projectId: string): Promise<Workspace> {
  const payload = await request<{ workspace: Workspace }>(`/api/v1/projects/${encodeURIComponent(projectId)}/workspace`);
  return payload.workspace;
}

export async function fetchGoogleIntegration(projectId: string): Promise<GoogleIntegration> {
  const payload = await request<{ integration: GoogleIntegration }>(
    `/api/v1/projects/${encodeURIComponent(projectId)}/integrations/google`,
  );
  return payload.integration;
}

export async function saveCruxKey(projectId: string, apiKey: string): Promise<GoogleIntegration> {
  const payload = await request<{ integration: GoogleIntegration }>(
    `/api/v1/projects/${encodeURIComponent(projectId)}/integrations/google/crux`,
    { method: "PUT", body: JSON.stringify({ api_key: apiKey }) },
  );
  return payload.integration;
}

export async function deleteCruxKey(projectId: string): Promise<GoogleIntegration> {
  const payload = await request<{ integration: GoogleIntegration }>(
    `/api/v1/projects/${encodeURIComponent(projectId)}/integrations/google/crux`,
    { method: "DELETE" },
  );
  return payload.integration;
}

export async function importGscCredentials(
  projectId: string,
  profile: string,
  credentialType: "oauth" | "service_account",
  credential: Record<string, unknown>,
): Promise<GoogleIntegration> {
  const payload = await request<{ integration: GoogleIntegration }>(
    `/api/v1/projects/${encodeURIComponent(projectId)}/integrations/google/gsc/credentials`,
    {
      method: "POST",
      body: JSON.stringify({ profile, credential_type: credentialType, credential }),
    },
  );
  return payload.integration;
}

export async function fetchGscProperties(projectId: string, profile: string): Promise<GscProperty[]> {
  const payload = await request<{ properties: GscProperty[] }>(
    `/api/v1/projects/${encodeURIComponent(projectId)}/integrations/google/gsc/properties`,
    { method: "POST", body: JSON.stringify({ profile }) },
  );
  return payload.properties;
}

export async function saveGscBinding(projectId: string, profile: string, property: string): Promise<GoogleIntegration> {
  const payload = await request<{ integration: GoogleIntegration }>(
    `/api/v1/projects/${encodeURIComponent(projectId)}/integrations/google/gsc/binding`,
    { method: "PUT", body: JSON.stringify({ profile, property }) },
  );
  return payload.integration;
}

export async function deleteGscBinding(projectId: string): Promise<GoogleIntegration> {
  const payload = await request<{ integration: GoogleIntegration }>(
    `/api/v1/projects/${encodeURIComponent(projectId)}/integrations/google/gsc/binding`,
    { method: "DELETE" },
  );
  return payload.integration;
}

export async function deleteGscProfile(projectId: string, profile: string): Promise<GoogleIntegration> {
  const payload = await request<{ integration: GoogleIntegration }>(
    `/api/v1/projects/${encodeURIComponent(projectId)}/integrations/google/gsc/profiles/${encodeURIComponent(profile)}`,
    { method: "DELETE" },
  );
  return payload.integration;
}

export async function importGa4Credentials(
  projectId: string,
  profile: string,
  credential: Record<string, unknown>,
): Promise<GoogleIntegration> {
  const payload = await request<{ integration: GoogleIntegration }>(
    `/api/v1/projects/${encodeURIComponent(projectId)}/integrations/google/ga4/credentials`,
    { method: "POST", body: JSON.stringify({ profile, credential }) },
  );
  return payload.integration;
}

export async function fetchGa4Properties(projectId: string, profile: string): Promise<Ga4Property[]> {
  const payload = await request<{ properties: Ga4Property[] }>(
    `/api/v1/projects/${encodeURIComponent(projectId)}/integrations/google/ga4/properties`,
    { method: "POST", body: JSON.stringify({ profile }) },
  );
  return payload.properties;
}

export async function saveGa4Binding(projectId: string, profile: string, property: string): Promise<GoogleIntegration> {
  const payload = await request<{ integration: GoogleIntegration }>(
    `/api/v1/projects/${encodeURIComponent(projectId)}/integrations/google/ga4/binding`,
    { method: "PUT", body: JSON.stringify({ profile, property }) },
  );
  return payload.integration;
}

export async function deleteGa4Binding(projectId: string): Promise<GoogleIntegration> {
  const payload = await request<{ integration: GoogleIntegration }>(
    `/api/v1/projects/${encodeURIComponent(projectId)}/integrations/google/ga4/binding`,
    { method: "DELETE" },
  );
  return payload.integration;
}

export async function fetchShopifyIntegration(projectId: string): Promise<ShopifyIntegration> {
  const payload = await request<{ integration: ShopifyIntegration }>(
    `/api/v1/projects/${encodeURIComponent(projectId)}/integrations/shopify`,
  );
  return payload.integration;
}

export async function saveShopifyCredentials(projectId: string, shopDomain: string, accessToken: string): Promise<ShopifyIntegration> {
  const payload = await request<{ integration: ShopifyIntegration }>(
    `/api/v1/projects/${encodeURIComponent(projectId)}/integrations/shopify/credentials`,
    { method: "PUT", body: JSON.stringify({ shop_domain: shopDomain, access_token: accessToken }) },
  );
  return payload.integration;
}

export async function verifyShopifyCredentials(projectId: string): Promise<ShopifyIntegration> {
  const payload = await request<{ integration: ShopifyIntegration }>(
    `/api/v1/projects/${encodeURIComponent(projectId)}/integrations/shopify/verify`,
    { method: "POST", body: "{}" },
  );
  return payload.integration;
}

export async function deleteShopifyCredentials(projectId: string): Promise<ShopifyIntegration> {
  const payload = await request<{ integration: ShopifyIntegration }>(
    `/api/v1/projects/${encodeURIComponent(projectId)}/integrations/shopify/credentials`,
    { method: "DELETE" },
  );
  return payload.integration;
}

export async function saveShopifyCrawlerAccess(
  projectId: string,
  domainHost: string,
  signature: string,
  signatureInput: string,
  signatureAgent: string,
  expiresAt: string,
): Promise<ShopifyIntegration> {
  const payload = await request<{ integration: ShopifyIntegration }>(
    `/api/v1/projects/${encodeURIComponent(projectId)}/integrations/shopify/crawler-access`,
    {
      method: "PUT",
      body: JSON.stringify({
        domain_host: domainHost,
        signature,
        signature_input: signatureInput,
        signature_agent: signatureAgent,
        expires_at: expiresAt,
      }),
    },
  );
  return payload.integration;
}

export async function deleteShopifyCrawlerAccess(projectId: string): Promise<ShopifyIntegration> {
  const payload = await request<{ integration: ShopifyIntegration }>(
    `/api/v1/projects/${encodeURIComponent(projectId)}/integrations/shopify/crawler-access`,
    { method: "DELETE" },
  );
  return payload.integration;
}

export async function fetchDataForSeoIntegration(projectId: string): Promise<DataForSeoIntegration> {
  const payload = await request<{ integration: DataForSeoIntegration }>(
    `/api/v1/projects/${encodeURIComponent(projectId)}/integrations/dataforseo`,
  );
  return payload.integration;
}

export async function saveDataForSeoCredentials(projectId: string, apiLogin: string, apiPassword: string): Promise<DataForSeoIntegration> {
  const payload = await request<{ integration: DataForSeoIntegration }>(
    `/api/v1/projects/${encodeURIComponent(projectId)}/integrations/dataforseo/credentials`,
    { method: "PUT", body: JSON.stringify({ api_login: apiLogin, api_password: apiPassword }) },
  );
  return payload.integration;
}

export async function deleteDataForSeoCredentials(projectId: string): Promise<DataForSeoIntegration> {
  const payload = await request<{ integration: DataForSeoIntegration }>(
    `/api/v1/projects/${encodeURIComponent(projectId)}/integrations/dataforseo/credentials`,
    { method: "DELETE" },
  );
  return payload.integration;
}

export async function fetchFiles(projectId: string): Promise<FileSummary[]> {
  const payload = await request<{ files: FileSummary[] }>(`/api/v1/projects/${encodeURIComponent(projectId)}/files`);
  return payload.files;
}

export async function fetchReportArchive(projectId: string, params: ReportArchiveParams = {}): Promise<ReportArchive> {
  const query = queryString(params);
  return request<ReportArchive>(`/api/v1/projects/${encodeURIComponent(projectId)}/reports${query ? `?${query}` : ""}`);
}

export async function fetchMarkdown(projectId: string, path: string): Promise<MarkdownFile> {
  const payload = await request<{ file: MarkdownFile }>(
    `/api/v1/projects/${encodeURIComponent(projectId)}/files/${path.split("/").map(encodeURIComponent).join("/")}`,
  );
  return payload.file;
}

export async function fetchTutorials(): Promise<TutorialSummary[]> {
  const payload = await request<{ tutorials: TutorialSummary[] }>("/api/v1/tutorials");
  return payload.tutorials;
}

export async function fetchTutorial(slug: string): Promise<TutorialDocument> {
  const payload = await request<{ tutorial: TutorialDocument }>(`/api/v1/tutorials/${encodeURIComponent(slug)}`);
  return payload.tutorial;
}

export async function saveMarkdown(
  projectId: string,
  path: string,
  content: string,
  baseRevision: string | null,
): Promise<{ revision: string; modified_at: string }> {
  const payload = await request<{ file: { revision: string; modified_at: string } }>(
    `/api/v1/projects/${encodeURIComponent(projectId)}/files/${path.split("/").map(encodeURIComponent).join("/")}`,
    {
      method: "PUT",
      body: JSON.stringify({ content, base_revision: baseRevision }),
    },
  );
  return payload.file;
}

export async function fetchJobs(projectId: string): Promise<Job[]> {
  const payload = await request<{ jobs: Job[] }>(`/api/v1/projects/${encodeURIComponent(projectId)}/jobs`);
  return payload.jobs;
}

export async function fetchTechAudit(projectId: string): Promise<TechAuditData> {
  return request<TechAuditData>(`/api/v1/projects/${encodeURIComponent(projectId)}/tech-audit`);
}

export type TechAuditViewParams = {
  dataset: TechAuditDataset;
  run_id?: string;
  q?: string;
  status?: string;
  indexability?: string;
  host_relation?: string;
  rule_id?: string;
  template?: string;
  category?: string;
  severity?: string;
  priority_tier?: string;
  sort?: string;
  direction?: "asc" | "desc";
  limit?: number;
  offset?: number;
};

export async function fetchTechAuditView(projectId: string, params: TechAuditViewParams): Promise<TechAuditViewResponse> {
  return request<TechAuditViewResponse>(`/api/v1/projects/${encodeURIComponent(projectId)}/tech-audit/view?${queryString(params)}`);
}

export async function fetchTechAuditDetail(projectId: string, dataset: TechAuditDataset, key: string, runId = ""): Promise<TechAuditDetailResponse> {
  return request<TechAuditDetailResponse>(`/api/v1/projects/${encodeURIComponent(projectId)}/tech-audit/view/detail?${queryString({ dataset, key, run_id: runId })}`);
}

export async function deleteTechAuditRun(projectId: string, runId: string): Promise<{ deleted_run_id: string; latest_run_id: string | null }> {
  return request(`/api/v1/projects/${encodeURIComponent(projectId)}/tech-audit/history/${encodeURIComponent(runId)}`, { method: "DELETE" });
}

export type PageViewParams = {
  dataset: PageDataset;
  group?: string;
  q?: string;
  source?: string;
  page_type?: string;
  decision?: string;
  status?: string;
  sort?: string;
  direction?: "asc" | "desc";
  limit?: number;
  offset?: number;
};

export async function fetchPageView(projectId: string, params: PageViewParams): Promise<PageViewResponse> {
  return request<PageViewResponse>(`/api/v1/projects/${encodeURIComponent(projectId)}/pages/view?${queryString(params)}`);
}

export async function fetchPageDetail(projectId: string, dataset: PageDataset, key: string): Promise<PageDetailResponse> {
  return request<PageDetailResponse>(`/api/v1/projects/${encodeURIComponent(projectId)}/pages/view/detail?${queryString({ dataset, key })}`);
}

export type BacklinkViewParams = {
  q?: string;
  status?: string;
  follow?: string;
  reclaim_only?: boolean;
  sort?: string;
  direction?: "asc" | "desc";
  limit?: number;
  offset?: number;
};

export async function fetchBacklinkView(projectId: string, params: BacklinkViewParams = {}): Promise<BacklinkViewResponse> {
  return request<BacklinkViewResponse>(`/api/v1/projects/${encodeURIComponent(projectId)}/backlinks/view?${queryString(params)}`);
}

export type KeywordViewParams = {
  dataset: KeywordDataset;
  q?: string;
  decision?: string;
  stage?: string;
  intent?: string;
  source?: string;
  mapping?: string;
  scope?: "" | "queue" | "map";
  sort?: string;
  direction?: "asc" | "desc";
  limit?: number;
  offset?: number;
};

export async function fetchKeywordView(projectId: string, params: KeywordViewParams): Promise<KeywordViewResponse> {
  return request<KeywordViewResponse>(`/api/v1/projects/${encodeURIComponent(projectId)}/keywords/view?${queryString(params)}`);
}

export async function updateKeywords(projectId: string, keywords: string[], patch: KeywordPatch, baseRevision: string): Promise<{ updated: number; revision: string }> {
  return request(`/api/v1/projects/${encodeURIComponent(projectId)}/keywords`, {
    method: "PATCH",
    body: JSON.stringify({ keywords, patch, base_revision: baseRevision }),
  });
}

export async function fetchKeywordHandoff(projectId: string, keyword: string): Promise<KeywordHandoff> {
  return request<KeywordHandoff>(`/api/v1/projects/${encodeURIComponent(projectId)}/keywords/handoff?${queryString({ keyword })}`);
}

export async function collectKeywordDataForSeo(projectId: string, keyword: string): Promise<{ keyword: string; cost_usd: number; generated_at: string }> {
  return request(`/api/v1/projects/${encodeURIComponent(projectId)}/keywords/dataforseo`, {
    method: "POST",
    body: JSON.stringify({ keyword, location_code: 2840, language_code: "en", confirm: true }),
  });
}

export async function openCodex(): Promise<void> {
  await request("/api/v1/codex/open", { method: "POST", body: "{}" });
}

export async function fetchStatistics(projectId: string): Promise<StatisticsResponse> {
  return request<StatisticsResponse>(`/api/v1/projects/${encodeURIComponent(projectId)}/statistics`);
}

export async function createSeoChange(projectId: string, change: SeoChangeCreate): Promise<Record<string, unknown>> {
  return request(`/api/v1/projects/${encodeURIComponent(projectId)}/seo-changes`, { method: "POST", body: JSON.stringify(change) });
}

export async function fetchSeoChanges(projectId: string): Promise<SeoChangesResponse> {
  return request<SeoChangesResponse>(`/api/v1/projects/${encodeURIComponent(projectId)}/seo-changes`);
}

export async function updateSeoChangeStatus(projectId: string, changeId: string, status: string, note = ""): Promise<Record<string, unknown>> {
  return request(`/api/v1/projects/${encodeURIComponent(projectId)}/seo-changes/${encodeURIComponent(changeId)}/status`, { method: "PUT", body: JSON.stringify({ status, note }) });
}

export async function evaluateSeoChange(projectId: string, changeId: string): Promise<{ report: Record<string, unknown> }> {
  const started = await request<{ job: Job }>(`/api/v1/projects/${encodeURIComponent(projectId)}/seo-changes/${encodeURIComponent(changeId)}/evaluate-job`, { method: "POST", body: "{}" });
  for (let attempt = 0; attempt < 120; attempt += 1) {
    const job = (await fetchJobs(projectId)).find((item) => item.id === started.job.id);
    if (job?.status === "succeeded") {
      return request(`/api/v1/projects/${encodeURIComponent(projectId)}/seo-changes/${encodeURIComponent(changeId)}/outcome`);
    }
    if (job?.status === "failed" || job?.status === "cancelled") throw new Error(job.output || "Outcome evaluation failed.");
    await new Promise((resolve) => window.setTimeout(resolve, 500));
  }
  throw new Error("Outcome evaluation is still running; check the task panel.");
}

export async function updateTechnicalIssueStatus(projectId: string, fingerprint: string, status: string, owner = "", note = ""): Promise<Record<string, unknown>> {
  return request(`/api/v1/projects/${encodeURIComponent(projectId)}/tech-audit/issues/${encodeURIComponent(fingerprint)}/status`, { method: "PUT", body: JSON.stringify({ status, owner, note }) });
}

export async function updateTechAuditSchedule(projectId: string, schedule: TechAuditSchedule): Promise<TechAuditSchedule> {
  const payload = await request<{ schedule: TechAuditSchedule }>(
    `/api/v1/projects/${encodeURIComponent(projectId)}/tech-audit/schedule`,
    { method: "PUT", body: JSON.stringify(schedule) },
  );
  return payload.schedule;
}

export async function startAction(projectId: string, action: string, urls: string[] = []): Promise<Job> {
  const payload = await request<{ job: Job }>(`/api/v1/projects/${encodeURIComponent(projectId)}/actions`, {
    method: "POST",
    body: JSON.stringify({ action, ...(urls.length ? { urls } : {}) }),
  });
  return payload.job;
}

export async function startContentAction(projectId: string, action: ContentJobAction): Promise<Job> {
  const payload = await request<{ job: Job }>(`/api/v1/projects/${encodeURIComponent(projectId)}/content/actions`, {
    method: "POST",
    body: JSON.stringify(action),
  });
  return payload.job;
}

export async function updateContentStatus(
  projectId: string,
  itemId: string,
  status: string,
  note = "",
): Promise<{ item: ContentQueueItem; queue: ContentQueueSummary }> {
  const payload = await request<{ item: ContentQueueItem; queue: ContentQueueSummary }>(
    `/api/v1/projects/${encodeURIComponent(projectId)}/content/queue/${encodeURIComponent(itemId)}/status`,
    {
      method: "PUT",
      body: JSON.stringify({ status, note }),
    },
  );
  return payload;
}

export async function updateWorkflow(projectId: string, action: "start" | "done" | "skip" | "reset", stepId?: string): Promise<void> {
  await request(`/api/v1/projects/${encodeURIComponent(projectId)}/workflow`, {
    method: "POST",
    body: JSON.stringify({ action, step_id: stepId || null }),
  });
}
