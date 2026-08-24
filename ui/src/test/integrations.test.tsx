import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  fetchGoogleIntegration,
  fetchDataForSeoIntegration,
  fetchGscProperties,
  fetchShopifyIntegration,
  saveShopifyCrawlerAccess,
  saveCruxKey,
  saveDataForSeoCredentials,
  saveGscBinding,
  saveShopifyCredentials,
} from "../api/client";
import type { DataForSeoIntegration, GoogleIntegration, ShopifyIntegration } from "../api/types";
import { IntegrationsPage } from "../features/integrations/IntegrationsPage";

vi.mock("../api/client", async (importOriginal) => {
  const original = await importOriginal<typeof import("../api/client")>();
  return {
    ...original,
    fetchGoogleIntegration: vi.fn(),
    fetchDataForSeoIntegration: vi.fn(),
    fetchGscProperties: vi.fn(),
    fetchShopifyIntegration: vi.fn(),
    saveShopifyCrawlerAccess: vi.fn(),
    saveCruxKey: vi.fn(),
    saveDataForSeoCredentials: vi.fn(),
    saveGscBinding: vi.fn(),
    saveShopifyCredentials: vi.fn(),
  };
});

const emptyIntegration: GoogleIntegration = {
  access: "local_only",
  crux: { status: "needs_key", configured: false, source: "missing", removable: false },
  gsc: { status: "needs_auth", profiles: [], binding: null },
  ga4: { status: "needs_auth", configured: false, profiles: [], binding: null, removable: false },
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
  crawler_access: {
    configured: false,
    status: "missing",
    domain_host: "www.example.com",
    expires_at: null,
    signature_agent: null,
    removable: false,
    secret_visibility: "write_only",
  },
};

const emptyDataForSeo: DataForSeoIntegration = {
  access: "local_only",
  status: "needs_credentials",
  configured: false,
  source: "missing",
  verified_at: null,
  removable: false,
  secret_visibility: "write_only",
  transport: "rest_v3",
  billing: "metered",
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
  crawler_access: {
    configured: true,
    status: "ready",
    domain_host: "www.example.com",
    expires_at: "2030-01-01T00:00:00Z",
    signature_agent: '"https://shopify.com"',
    removable: true,
    secret_visibility: "write_only",
  },
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(fetchGoogleIntegration).mockResolvedValue(emptyIntegration);
  vi.mocked(fetchShopifyIntegration).mockResolvedValue(emptyShopify);
  vi.mocked(fetchDataForSeoIntegration).mockResolvedValue(emptyDataForSeo);
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

  it("stores Shopify Web Bot Auth without displaying the signature", async () => {
    vi.mocked(saveShopifyCrawlerAccess).mockResolvedValue(readyShopify);
    render(<IntegrationsPage projectId="store" refreshKey={0} onRunAction={vi.fn()} />);

    expect(await screen.findByRole("heading", { name: "Signed storefront crawl" })).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Crawler Signature"), { target: { value: "sig1=:private:" } });
    fireEvent.change(screen.getByLabelText("Crawler Signature-Input"), { target: { value: 'sig1=("@authority");expires=4102444800' } });
    fireEvent.change(screen.getByLabelText("Crawler access expiration"), { target: { value: "2030-01-01T00:00" } });
    fireEvent.click(screen.getByRole("button", { name: "Save crawler signature" }));

    expect(saveShopifyCrawlerAccess).toHaveBeenCalledWith(
      "store",
      "www.example.com",
      "sig1=:private:",
      'sig1=("@authority");expires=4102444800',
      '"https://shopify.com"',
      expect.any(String),
    );
    expect(await screen.findByText("Shopify Crawler Access saved. The signature will not be shown again.")).toBeTruthy();
    expect(screen.queryByDisplayValue("sig1=:private:")).toBeNull();
  });

  it("shows the local security boundary and stores a write-only CrUX key", async () => {
    vi.mocked(saveCruxKey).mockResolvedValue(readyIntegration);
    render(<IntegrationsPage projectId="store" refreshKey={0} onRunAction={vi.fn()} />);

    expect(await screen.findByRole("heading", { name: "SEO integrations" })).toBeTruthy();
    expect(fetchDataForSeoIntegration).not.toHaveBeenCalled();
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
    fireEvent.click(screen.getAllByRole("button", { name: "Load accessible properties" })[0]);
    expect(await screen.findByText("1 accessible Search Console properties loaded.")).toBeTruthy();
    fireEvent.click(screen.getAllByRole("button", { name: "Bind property" })[0]);

    expect(saveGscBinding).toHaveBeenCalledWith("store", "default", "sc-domain:example.com");
    expect(await screen.findByText("Search Console property bound to this project.")).toBeTruthy();
  });

  it("uses the shared success tone for ready integrations", async () => {
    vi.mocked(fetchShopifyIntegration).mockResolvedValue(readyShopify);
    render(<IntegrationsPage projectId="store" refreshKey={0} onRunAction={vi.fn()} />);

    const readyPills = await screen.findAllByText("Ready", { selector: ".statusPill" });
    expect(readyPills).toHaveLength(2);
    expect(readyPills.every((pill) => pill.getAttribute("data-tone") === "success")).toBe(true);
  });

  it("stores DataForSEO credentials from the optional providers tab without displaying them", async () => {
    vi.mocked(saveDataForSeoCredentials).mockResolvedValue({
      ...emptyDataForSeo,
      status: "ready",
      configured: true,
      source: "private_file",
      removable: true,
      verified_at: "2026-08-19T08:00:00Z",
    });
    render(<IntegrationsPage projectId="store" refreshKey={0} section="optional" onRunAction={vi.fn()} />);

    await screen.findByRole("heading", { name: "DataForSEO" });
    expect(screen.queryByRole("heading", { name: "Google Search Console" })).toBeNull();
    expect(screen.getByRole("heading", { name: "DataForSEO" })).toBeTruthy();
    fireEvent.change(screen.getByLabelText("DataForSEO API login"), { target: { value: "api@example.com" } });
    fireEvent.change(screen.getByLabelText("DataForSEO API password"), { target: { value: "private-password" } });
    fireEvent.click(screen.getByRole("button", { name: "Verify and store" }));

    expect(saveDataForSeoCredentials).toHaveBeenCalledWith("store", "api@example.com", "private-password");
    expect(await screen.findByText("DataForSEO credentials verified and stored. The values will not be shown again.")).toBeTruthy();
    expect(screen.queryByDisplayValue("api@example.com")).toBeNull();
    expect(screen.queryByDisplayValue("private-password")).toBeNull();
  });
});
