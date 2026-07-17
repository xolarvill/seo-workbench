import type { FileSummary, MarkdownFile, ProjectSummary, Workspace } from "./types";


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
