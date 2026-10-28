import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { fetchClarityIntegration, fetchClarityEvidence, saveClarityCredentials, startClarityQuery, fetchJobs } from "../api/client";
import type { Job } from "../api/types";
import { ClarityPanel } from "../features/integrations/ClarityPanel";

vi.mock("../api/client", () => ({
  fetchClarityIntegration: vi.fn(), fetchClarityEvidence: vi.fn(), saveClarityCredentials: vi.fn(),
  startClarityQuery: vi.fn(), fetchJobs: vi.fn(), deleteClarityCredentials: vi.fn(), verifyClarityConnection: vi.fn(),
  fetchClarityRecordingLinks: vi.fn().mockResolvedValue([]),
}));
const ready = { configured: true, status: "ready", runtime_ready: true, credential_verified: true,
  identity_verified: false, project_id: "abc123", timezone: "UTC", site_url: "https://example.com" };

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(fetchClarityIntegration).mockResolvedValue(ready);
  vi.mocked(fetchClarityEvidence).mockResolvedValue({ collection_status: "not_collected" });
});

describe("Clarity connection", () => {
  it("distinguishes a successful request from provider-described partial evidence", async () => {
    vi.mocked(fetchClarityEvidence).mockResolvedValue({ collection_status: "partial", transport_status: "ok", scope_status: "provider_described", identity_status: "operator_declared", capability_status: "available", provider_query_description: "Counts non-bot unique sessions in UTC." });
    render(<ClarityPanel projectId="store" />);
    await screen.findByText("Counts non-bot unique sessions in UTC.");
    expect(screen.getByText(/The request succeeded/)).toBeTruthy();
    expect(screen.getByText("provider described")).toBeTruthy();
    expect(screen.getByText("Provider explanation; not independent execution verification.")).toBeTruthy();
  });
  it("clears the write-only token after a failed save", async () => {
    vi.mocked(saveClarityCredentials).mockRejectedValue(new Error("Verification failed"));
    render(<ClarityPanel projectId="store" />);
    await screen.findByDisplayValue("abc123");
    fireEvent.change(screen.getByLabelText(/^Clarity API token/), { target: { value: "secret-token" } });
    fireEvent.click(screen.getByRole("button", { name: "Verify and replace Clarity" }));
    await screen.findByText("Verification failed");
    expect((screen.getByLabelText(/^Clarity API token/) as HTMLInputElement).value).toBe("");
    expect(screen.queryByText("secret-token")).toBeNull();
  });

  it("queues bounded recording filters and loads completed evidence", async () => {
    vi.mocked(startClarityQuery).mockResolvedValue({ id: "job1" } as Job);
    vi.mocked(fetchJobs).mockResolvedValue([{ id: "job1", status: "succeeded" } as Job]);
    render(<ClarityPanel projectId="store" />);
    await screen.findByDisplayValue("abc123");
    fireEvent.change(screen.getByLabelText("Clarity operation"), { target: { value: "recordings" } });
    fireEvent.click(screen.getByLabelText("Rage clicks"));
    fireEvent.click(screen.getByRole("button", { name: "Run Clarity query" }));
    await waitFor(() => expect(startClarityQuery).toHaveBeenCalled());
    const payload = vi.mocked(startClarityQuery).mock.calls[0][1];
    expect(payload.action).toBe("recordings");
    expect(payload.count).toBe(10);
    expect(payload.rage_click).toBe(true);
    expect(payload.start).toMatch(/T00:00:00Z$/);
    await waitFor(() => expect(fetchClarityEvidence).toHaveBeenCalledWith("store", "recordings"));
  });

  it("does not reuse a previous brand's configuration", async () => {
    const { rerender } = render(<ClarityPanel key="first" projectId="first" />);
    await screen.findByDisplayValue("abc123");
    fireEvent.change(screen.getByLabelText(/^Clarity API token/), { target: { value: "private" } });
    vi.mocked(fetchClarityIntegration).mockResolvedValue({ ...ready, configured: false, project_id: undefined });
    rerender(<ClarityPanel key="second" projectId="second" />);
    await waitFor(() => expect(fetchClarityIntegration).toHaveBeenCalledWith("second"));
    expect((screen.getByLabelText(/^Clarity API token/) as HTMLInputElement).value).toBe("");
    expect((screen.getByLabelText("Clarity project ID") as HTMLInputElement).value).toBe("");
  });
});
