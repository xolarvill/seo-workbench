import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  fetchGoogleIntegration,
  fetchGscProperties,
  saveCruxKey,
  saveGscBinding,
} from "../api/client";
import type { GoogleIntegration } from "../api/types";
import { IntegrationsPage } from "../features/integrations/IntegrationsPage";

vi.mock("../api/client", async (importOriginal) => {
  const original = await importOriginal<typeof import("../api/client")>();
  return {
    ...original,
    fetchGoogleIntegration: vi.fn(),
    fetchGscProperties: vi.fn(),
    saveCruxKey: vi.fn(),
    saveGscBinding: vi.fn(),
  };
});

const emptyIntegration: GoogleIntegration = {
  access: "local_only",
  crux: { status: "needs_key", configured: false, source: "missing", removable: false },
  gsc: { status: "needs_auth", profiles: [], binding: null },
  security: { secrets_returned: false, storage_mode: "0600", scope: "local runtime" },
};

const readyIntegration: GoogleIntegration = {
  ...emptyIntegration,
  crux: { status: "ready", configured: true, source: "private_file", removable: true },
  gsc: {
    status: "not_bound",
    profiles: [{ profile: "default", credential_type: "oauth", status: "ready", updated_at: "2026-07-28T08:00:00Z" }],
    binding: null,
  },
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(fetchGoogleIntegration).mockResolvedValue(emptyIntegration);
});

describe("Google integrations page", () => {
  it("shows the local security boundary and stores a write-only CrUX key", async () => {
    vi.mocked(saveCruxKey).mockResolvedValue(readyIntegration);
    render(<IntegrationsPage projectId="store" refreshKey={0} onRunAction={vi.fn()} />);

    expect(await screen.findByRole("heading", { name: "SEO integrations" })).toBeTruthy();
    expect(screen.getByText("Needs key")).toBeTruthy();
    expect(screen.getAllByText("Local only").length).toBeGreaterThan(0);

    fireEvent.change(screen.getByLabelText("API key"), { target: { value: "private-crux-key" } });
    fireEvent.click(screen.getByRole("button", { name: "Store key" }));

    expect(saveCruxKey).toHaveBeenCalledWith("store", "private-crux-key");
    expect(await screen.findByText("CrUX key stored. The value will not be shown again.")).toBeTruthy();
    expect(screen.queryByDisplayValue("private-crux-key")).toBeNull();
  });

  it("loads accessible GSC properties and binds the selected project", async () => {
    vi.mocked(fetchGoogleIntegration).mockResolvedValue(readyIntegration);
    vi.mocked(fetchGscProperties).mockResolvedValue([
      { site_url: "sc-domain:example.com", permission_level: "siteOwner" },
    ]);
    vi.mocked(saveGscBinding).mockResolvedValue({
      ...readyIntegration,
      gsc: {
        ...readyIntegration.gsc,
        status: "ready",
        binding: { profile: "default", property: "sc-domain:example.com", permission_level: "siteOwner" },
      },
    });
    render(<IntegrationsPage projectId="store" refreshKey={0} onRunAction={vi.fn()} />);

    expect(await screen.findByText("default · Ready")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Load accessible properties" }));
    expect(await screen.findByText("1 accessible Search Console properties loaded.")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Bind property" }));

    expect(saveGscBinding).toHaveBeenCalledWith("store", "default", "sc-domain:example.com");
    expect(await screen.findByText("Search Console property bound to this project.")).toBeTruthy();
  });
});
