import type { FileSummary, GoogleIntegration, GscProperty, Job, MarkdownFile, ProjectSummary, ShopifyIntegration, TutorialDocument, TutorialSummary, Workspace } from "./types";


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
  const response = await fetch(path, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  const payload = (await response.json()) as { detail?: unknown } & T;
  if (!response.ok) {
    throw new ApiError(response.status, `Workbench request failed with ${response.status}`, payload.detail);
  }
  return payload;
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

export async function fetchFiles(projectId: string): Promise<FileSummary[]> {
  const payload = await request<{ files: FileSummary[] }>(`/api/v1/projects/${encodeURIComponent(projectId)}/files`);
  return payload.files;
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

export async function startAction(projectId: string, action: string): Promise<Job> {
  const payload = await request<{ job: Job }>(`/api/v1/projects/${encodeURIComponent(projectId)}/actions`, {
    method: "POST",
    body: JSON.stringify({ action }),
  });
  return payload.job;
}

export async function updateWorkflow(projectId: string, action: "start" | "done" | "skip" | "reset", stepId?: string): Promise<void> {
  await request(`/api/v1/projects/${encodeURIComponent(projectId)}/workflow`, {
    method: "POST",
    body: JSON.stringify({ action, step_id: stepId || null }),
  });
}
