import type { BrowserCapture } from "./types";


export const DEFAULT_WORKBENCH_URL = "http://127.0.0.1:8765";

export interface WorkbenchProject {
  id: string;
  name: string;
  url: string;
  type: string;
  phase: string;
}

interface StoredConnection {
  baseUrl: string;
  token: string;
}

const normalizeBaseUrl = (value: string) => {
  const url = new URL(value);
  if (url.protocol !== "http:" || !["127.0.0.1", "localhost"].includes(url.hostname)) {
    throw new Error("Workbench URL must use local http://127.0.0.1 or http://localhost.");
  }
  return url.origin;
};

const request = async <T>(baseUrl: string, path: string, options: RequestInit = {}, token = ""): Promise<T> => {
  const response = await fetch(`${normalizeBaseUrl(baseUrl)}${path}`, {
    ...options,
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  const payload = await response.json().catch(() => ({})) as { detail?: string } & T;
  if (!response.ok) throw new Error(payload.detail || `Workbench returned ${response.status}.`);
  return payload;
};

export async function loadConnection(): Promise<StoredConnection> {
  const stored = await chrome.storage.local.get(["workbenchBaseUrl", "workbenchToken"]);
  return {
    baseUrl: typeof stored.workbenchBaseUrl === "string" ? stored.workbenchBaseUrl : DEFAULT_WORKBENCH_URL,
    token: typeof stored.workbenchToken === "string" ? stored.workbenchToken : "",
  };
}

export async function setBaseUrl(baseUrl: string): Promise<string> {
  const normalized = normalizeBaseUrl(baseUrl);
  await chrome.storage.local.set({ workbenchBaseUrl: normalized });
  return normalized;
}

export async function health(baseUrl: string): Promise<boolean> {
  const payload = await request<{ ok: boolean; extension_protocol_version?: string }>(baseUrl, "/api/v1/health");
  return payload.ok && payload.extension_protocol_version === "1";
}

export async function projects(baseUrl: string, token: string): Promise<WorkbenchProject[]> {
  const payload = await request<{ projects: WorkbenchProject[] }>(baseUrl, "/api/v1/extension/projects", {}, token);
  return payload.projects;
}

const verifier = () => {
  const bytes = crypto.getRandomValues(new Uint8Array(36));
  return btoa(String.fromCharCode(...bytes)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
};

const sha256 = async (value: string) => [...new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value)))]
  .map((byte) => byte.toString(16).padStart(2, "0")).join("");

export async function pair(baseUrl: string, onApprovalOpened: () => void): Promise<string> {
  const secret = verifier();
  const started = await request<{ pairing_id: string; approval_url: string }>(baseUrl, "/api/v1/extension/pairings", {
    method: "POST",
    body: JSON.stringify({ verifier_hash: await sha256(secret), extension_version: chrome.runtime.getManifest().version }),
  });
  await chrome.tabs.create({ url: started.approval_url });
  onApprovalOpened();
  for (let attempt = 0; attempt < 150; attempt += 1) {
    await new Promise((resolve) => window.setTimeout(resolve, 1000));
    const response = await fetch(`${normalizeBaseUrl(baseUrl)}/api/v1/extension/pairings/${started.pairing_id}/token`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ verifier: secret }),
    });
    if (response.status === 202) continue;
    const payload = await response.json().catch(() => ({})) as { token?: string; detail?: string };
    if (!response.ok || !payload.token) throw new Error(payload.detail || "Workbench pairing failed.");
    await chrome.storage.local.set({ workbenchBaseUrl: normalizeBaseUrl(baseUrl), workbenchToken: payload.token });
    return payload.token;
  }
  throw new Error("Workbench approval timed out. Start pairing again.");
}

export async function saveCapture(baseUrl: string, token: string, projectId: string, capture: BrowserCapture): Promise<string> {
  const payload = await request<{ artifact: string }>(baseUrl, `/api/v1/extension/projects/${encodeURIComponent(projectId)}/captures`, {
    method: "POST",
    body: JSON.stringify({ capture }),
  }, token);
  return payload.artifact;
}

export async function openCodex(baseUrl: string, token: string): Promise<void> {
  await request(baseUrl, "/api/v1/extension/open-codex", { method: "POST", body: "{}" }, token);
}

export async function disconnect(baseUrl: string, token: string): Promise<void> {
  try {
    await request(baseUrl, "/api/v1/extension/session", { method: "DELETE" }, token);
  } finally {
    await chrome.storage.local.remove("workbenchToken");
  }
}

export async function openWorkbench(baseUrl: string, projectId: string): Promise<void> {
  await chrome.tabs.create({ url: `${normalizeBaseUrl(baseUrl)}/?project=${encodeURIComponent(projectId)}` });
}
