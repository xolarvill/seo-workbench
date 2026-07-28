import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  fetchGoogleIntegration,
  fetchGscProperties,
  fetchShopifyIntegration,
  saveCruxKey,
  saveGscBinding,
  saveShopifyCredentials,
} from "../api/client";
import type { GoogleIntegration, ShopifyIntegration } from "../api/types";
import { IntegrationsPage } from "../features/integrations/IntegrationsPage";

vi.mock("../api/client", async (importOriginal) => {
  const original = await importOriginal<typeof import("../api/client")>();
  return {
    ...original,
    fetchGoogleIntegration: vi.fn(),
    fetchGscProperties: vi.fn(),
    fetchShopifyIntegration: vi.fn(),
    saveCruxKey: vi.fn(),
    saveGscBinding: vi.fn(),
    saveShopifyCredentials: vi.fn(),
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

const emptyShopify: ShopifyIntegration = {
  access: "local_only",
  applicable: true,
  status: "needs_credentials",
  configured: false,
  source: "missing",
  shop_domain: null,
  shop_name: null,
  api_version: "2026-07",
  scopes: [],
  write_scope_count: 0,
  verified_at: null,
  removable: false,
  secret_visibility: "write_only",
};

const readyShopify: ShopifyIntegration = {
  ...emptyShopify,
  status: "ready",
  configured: true,
  source: "private_file",
  shop_domain: "example-store.myshopify.com",
  shop_name: "Example Store",
  scopes: ["read_content", "read_products"],
  verified_at: "2026-07-28T09:00:00Z",
  removable: true,
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(fetchGoogleIntegration).mockResolvedValue(emptyIntegration);
  vi.mocked(fetchShopifyIntegration).mockResolvedValue(emptyShopify);
});

describe("SEO integrations page", () => {
  it("verifies and stores a write-only Shopify Admin API token", async () => {
    vi.mocked(saveShopifyCredentials).mockResolvedValue(readyShopify);
    render(<IntegrationsPage projectId="store" refreshKey={0} onRunAction={vi.fn()} />);

    expect(await screen.findByRole("heading", { name: "Shopify Admin API" })).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Shopify shop domain"), { target: { value: "example-store.myshopify.com" } });
    fireEvent.change(screen.getByLabelText("Admin API access token"), { target: { value: "shpat_private_token" } });
    fireEvent.click(screen.getByRole("button", { name: "Connect Shopify" }));

    expect(saveShopifyCredentials).toHaveBeenCalledWith("store", "example-store.myshopify.com", "shpat_private_token");
    expect(await screen.findByText("Shopify Admin API connected. The access token will not be shown again.")).toBeTruthy();
    expect(screen.queryByDisplayValue("shpat_private_token")).toBeNull();
    expect(screen.getByText("Example Store")).toBeTruthy();
    expect(screen.getByText("Read scopes only")).toBeTruthy();
  });

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
