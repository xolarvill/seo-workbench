import {
  Activity,
  BarChart3,
  Check,
  CircleAlert,
  Database,
  KeyRound,
  Link2,
  LockKeyhole,
  RefreshCw,
  SearchCheck,
  Store,
  Trash2,
  Upload,
} from "lucide-react";
import { type FormEvent, type ReactNode, useEffect, useRef, useState } from "react";

import {
  ApiError,
  deleteCruxKey,
  deleteDataForSeoCredentials,
  deleteGa4Binding,
  deleteGscBinding,
  deleteGscProfile,
  deleteShopifyCredentials,
  deleteShopifyCrawlerAccess,
  fetchGa4Properties,
  fetchDataForSeoIntegration,
  fetchGoogleIntegration,
  fetchGscProperties,
  fetchShopifyIntegration,
  importGa4Credentials,
  importGscCredentials,
  saveCruxKey,
  saveDataForSeoCredentials,
  saveGa4Binding,
  saveGscBinding,
  saveShopifyCredentials,
  saveShopifyCrawlerAccess,
  verifyShopifyCredentials,
} from "../../api/client";
import type { DataForSeoIntegration, Ga4Property, GoogleIntegration, GscProperty, ShopifyIntegration } from "../../api/types";
import { confirmAction } from "../../components/ActionButton";
import { StatusPill, statusLabel, statusTone } from "../../components/StatusPill";
import type { ConnectionSection } from "../../components/AppShell";
import styles from "./IntegrationsPage.module.css";


function messageFrom(error: unknown): string {
  if (error instanceof ApiError && typeof error.detail === "string") return error.detail;
  if (error instanceof Error) return error.message;
  return "The integration request could not be completed.";
}

function Status({ value }: { value: string }) {
  return <StatusPill value={statusLabel(value)} tone={statusTone(value, "evidence")} />;
}

function ConnectionSteps({ boundLabel, profileCount, status }: { boundLabel?: string | null; profileCount: number; status?: string }) {
  return <ol className={styles.steps}>
    <li data-state={profileCount ? "ready" : "current"}><span>1</span><div><strong>Auth profile</strong><small>{profileCount ? `${profileCount} available` : "Import credentials"}</small></div></li>
    <li data-state={boundLabel ? "ready" : profileCount ? "current" : "waiting"}><span>2</span><div><strong>Project property</strong><small>{boundLabel || "Not bound"}</small></div></li>
    <li data-state={status === "ready" ? "current" : "waiting"}><span>3</span><div><strong>Evidence</strong><small>{status === "ready" ? "Ready to collect" : "Complete setup first"}</small></div></li>
  </ol>;
}

function GooglePropertyPanel({ busy, canLoad, description, loading, onBind, onDisconnect, onLoad, onProfileChange, onPropertyChange, profileDetail, profiles, properties, propertyLabel, selectedProfile, selectedProperty }: { busy: boolean; canLoad: boolean; description: string; loading: boolean; onBind: () => void; onDisconnect?: () => void; onLoad: () => void; onProfileChange: (profile: string) => void; onPropertyChange: (property: string) => void; profileDetail?: ReactNode; profiles: Array<{ profile: string; status: string }>; properties: Array<{ label: string; value: string }>; propertyLabel: string; selectedProfile: string; selectedProperty: string }) {
  return <section className={styles.panel}>
    <div className={styles.panelHeading}><Link2 aria-hidden="true" size={17} /><div><h3>Bind this project</h3><p>{description}</p></div></div>
    <label className={styles.field}>
      <span>Auth profile</span>
      <select value={selectedProfile} onChange={(event) => onProfileChange(event.target.value)} disabled={!profiles.length || busy}>
        {profiles.length ? profiles.map((profile) => <option value={profile.profile} key={profile.profile}>{profile.profile} · {statusLabel(profile.status)}</option>) : <option value={selectedProfile}>No profiles</option>}
      </select>
      {profileDetail ? <small>{profileDetail}</small> : null}
    </label>
    <button type="button" disabled={!canLoad || busy} onClick={onLoad}>{loading ? "Loading properties" : "Load accessible properties"}</button>
    <label className={styles.field}>
      <span>{propertyLabel}</span>
      <select value={selectedProperty} onChange={(event) => onPropertyChange(event.target.value)} disabled={!properties.length || busy}>
        {properties.length ? properties.map((property) => <option key={property.value} value={property.value}>{property.label}</option>) : <option value="">Load properties to select</option>}
      </select>
    </label>
    <div className={styles.actions}>
      <button className={styles.primary} type="button" disabled={!selectedProperty || busy} onClick={onBind}>Bind property</button>
      {onDisconnect ? <button className={styles.danger} type="button" disabled={busy} onClick={onDisconnect}>Disconnect</button> : null}
    </div>
  </section>;
}

function formatDate(value?: string | null): string {
  if (!value) return "Not recorded";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function dateTimeLocal(value?: string | null): string {
  return value ? new Date(value).toISOString().slice(0, 16) : "";
}

type Props = {
  projectId: string;
  refreshKey: number;
  section?: ConnectionSection;
  onRunAction: (action: "crux" | "gsc" | "ga4") => Promise<void>;
};

export function IntegrationsPage({ projectId, refreshKey, section = "core", onRunAction }: Props) {
  const [integration, setIntegration] = useState<GoogleIntegration | null>(null);
  const [shopify, setShopify] = useState<ShopifyIntegration | null>(null);
  const [dataForSeo, setDataForSeo] = useState<DataForSeoIntegration | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [cruxKey, setCruxKey] = useState("");
  const [dataForSeoLogin, setDataForSeoLogin] = useState("");
  const [dataForSeoPassword, setDataForSeoPassword] = useState("");
  const [shopDomain, setShopDomain] = useState("");
  const [shopifyToken, setShopifyToken] = useState("");
  const [crawlerDomain, setCrawlerDomain] = useState("");
  const [crawlerSignature, setCrawlerSignature] = useState("");
  const [crawlerSignatureInput, setCrawlerSignatureInput] = useState("");
  const [crawlerSignatureAgent, setCrawlerSignatureAgent] = useState('"https://shopify.com"');
  const [crawlerExpiresAt, setCrawlerExpiresAt] = useState("");
  const [credentialType, setCredentialType] = useState<"oauth" | "service_account">("oauth");
  const [profileName, setProfileName] = useState("default");
  const [credentialFile, setCredentialFile] = useState<File | null>(null);
  const [selectedProfile, setSelectedProfile] = useState("default");
  const [properties, setProperties] = useState<GscProperty[]>([]);
  const [selectedProperty, setSelectedProperty] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);
  const [ga4ProfileName, setGa4ProfileName] = useState("ga4");
  const [ga4CredentialFile, setGa4CredentialFile] = useState<File | null>(null);
  const [ga4SelectedProfile, setGa4SelectedProfile] = useState("");
  const [ga4Properties, setGa4Properties] = useState<Ga4Property[]>([]);
  const [ga4SelectedProperty, setGa4SelectedProperty] = useState("");
  const ga4FileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let active = true;
    setError(null);
    setIntegration(null);
    setShopify(null);
    setShopDomain("");
    setShopifyToken("");
    setCrawlerDomain("");
    setCrawlerSignature("");
    setCrawlerSignatureInput("");
    setCrawlerSignatureAgent('"https://shopify.com"');
    setCrawlerExpiresAt("");
    Promise.all([fetchGoogleIntegration(projectId), fetchShopifyIntegration(projectId)])
      .then(([googleResult, shopifyResult]) => {
        if (!active) return;
        setIntegration(googleResult);
        setShopify(shopifyResult);
        setShopDomain(shopifyResult.shop_domain || "");
        setCrawlerDomain(shopifyResult.crawler_access.domain_host || "");
        setCrawlerExpiresAt(dateTimeLocal(shopifyResult.crawler_access.expires_at));
      })
      .catch((reason) => { if (active) setError(messageFrom(reason)); });
    return () => { active = false; };
  }, [projectId, refreshKey, section]);

  useEffect(() => {
    if (section !== "optional") return;
    let active = true;
    setDataForSeo(null);
    fetchDataForSeoIntegration(projectId)
      .then((result) => { if (active) setDataForSeo(result); })
      .catch((reason) => { if (active) setError(messageFrom(reason)); });
    return () => { active = false; };
  }, [projectId, refreshKey, section]);

  useEffect(() => {
    if (!integration) return;
    const preferred = integration.gsc.binding?.profile || integration.gsc.profiles[0]?.profile;
    if (preferred && !integration.gsc.profiles.some((profile) => profile.profile === selectedProfile)) {
      setSelectedProfile(preferred);
    }
  }, [integration, selectedProfile]);

  useEffect(() => {
    if (!integration?.ga4) return;
    const preferred = integration.ga4.binding?.profile || integration.ga4.profiles[0]?.profile;
    if (preferred && preferred !== ga4SelectedProfile) {
      setGa4SelectedProfile(preferred);
    }
    if (integration.ga4.binding?.property && integration.ga4.binding.property !== ga4SelectedProperty) {
      setGa4SelectedProperty(integration.ga4.binding.property);
    }
  }, [integration, ga4SelectedProfile, ga4SelectedProperty]);

  async function mutate(label: string, task: () => Promise<GoogleIntegration>, success: string) {
    setBusy(label);
    setError(null);
    setNotice(null);
    try {
      setIntegration(await task());
      setNotice(success);
    } catch (reason) {
      setError(messageFrom(reason));
    } finally {
      setBusy(null);
    }
  }

  async function submitCrux(event: FormEvent) {
    event.preventDefault();
    if (!cruxKey.trim()) return;
    await mutate("crux-save", () => saveCruxKey(projectId, cruxKey), "CrUX key stored. The value will not be shown again.");
    setCruxKey("");
  }

  async function submitDataForSeo(event: FormEvent) {
    event.preventDefault();
    if (!dataForSeoLogin.trim() || !dataForSeoPassword) return;
    setBusy("dataforseo-save");
    setError(null);
    setNotice(null);
    try {
      setDataForSeo(await saveDataForSeoCredentials(projectId, dataForSeoLogin, dataForSeoPassword));
      setDataForSeoLogin("");
      setDataForSeoPassword("");
      setNotice("DataForSEO credentials verified and stored. The values will not be shown again.");
    } catch (reason) {
      setError(messageFrom(reason));
    } finally {
      setBusy(null);
    }
  }

  async function submitShopify(event: FormEvent) {
    event.preventDefault();
    if (!shopDomain.trim() || !shopifyToken.trim()) return;
    setBusy("shopify-save");
    setError(null);
    setNotice(null);
    try {
      const result = await saveShopifyCredentials(projectId, shopDomain, shopifyToken);
      setShopify(result);
      setShopDomain(result.shop_domain || shopDomain);
      setShopifyToken("");
      setNotice("Shopify Admin API connected. The access token will not be shown again.");
    } catch (reason) {
      setError(messageFrom(reason));
    } finally {
      setBusy(null);
    }
  }

  async function submitShopifyCrawlerAccess(event: FormEvent) {
    event.preventDefault();
    if (!crawlerDomain.trim() || !crawlerSignature.trim() || !crawlerSignatureInput.trim() || !crawlerExpiresAt) return;
    setBusy("shopify-crawler-save");
    setError(null);
    setNotice(null);
    try {
      const result = await saveShopifyCrawlerAccess(
        projectId,
        crawlerDomain,
        crawlerSignature,
        crawlerSignatureInput,
        crawlerSignatureAgent,
        new Date(crawlerExpiresAt).toISOString(),
      );
      setShopify(result);
      setCrawlerDomain(result.crawler_access.domain_host || crawlerDomain);
      setCrawlerSignature("");
      setCrawlerSignatureInput("");
      setCrawlerExpiresAt(dateTimeLocal(result.crawler_access.expires_at));
      setNotice("Shopify Crawler Access saved. The signature will not be shown again.");
    } catch (reason) {
      setError(messageFrom(reason));
    } finally {
      setBusy(null);
    }
  }

  async function mutateShopify(label: string, task: () => Promise<ShopifyIntegration>, success: string) {
    setBusy(label);
    setError(null);
    setNotice(null);
    try {
      const result = await task();
      setShopify(result);
      setShopDomain(result.shop_domain || "");
      setCrawlerDomain(result.crawler_access.domain_host || "");
      setCrawlerExpiresAt(dateTimeLocal(result.crawler_access.expires_at));
      setNotice(success);
    } catch (reason) {
      setError(messageFrom(reason));
    } finally {
      setBusy(null);
    }
  }

  async function importCredential(event: FormEvent) {
    event.preventDefault();
    if (!credentialFile) return;
    setBusy("gsc-import");
    setError(null);
    setNotice(credentialType === "oauth" ? "Waiting for Google consent in your browser." : null);
    try {
      if (credentialFile.size > 128 * 1024) throw new Error("Credential file exceeds the 128 KB limit.");
      const parsed = JSON.parse(await credentialFile.text()) as unknown;
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error("Credential file must contain one JSON object.");
      const result = await importGscCredentials(
        projectId,
        profileName,
        credentialType,
        parsed as Record<string, unknown>,
      );
      setIntegration(result);
      setSelectedProfile(profileName);
      setCredentialFile(null);
      if (fileInput.current) fileInput.current.value = "";
      setNotice(credentialType === "oauth" ? "Google OAuth profile connected." : "Service account profile imported.");
    } catch (reason) {
      setError(messageFrom(reason));
      setNotice(null);
    } finally {
      setBusy(null);
    }
  }

  async function loadProperties() {
    setBusy("gsc-properties");
    setError(null);
    setNotice(null);
    try {
      const found = await fetchGscProperties(projectId, selectedProfile);
      setProperties(found);
      setSelectedProperty(found[0]?.site_url || "");
      setNotice(found.length ? `${found.length} accessible Search Console properties loaded.` : "No accessible Search Console properties were found.");
    } catch (reason) {
      setError(messageFrom(reason));
    } finally {
      setBusy(null);
    }
  }

  async function importGa4Credential(event: FormEvent) {
    event.preventDefault();
    if (!ga4CredentialFile) return;
    setBusy("ga4-import");
    setError(null);
    setNotice(null);
    try {
      if (ga4CredentialFile.size > 128 * 1024) throw new Error("Credential file exceeds the 128 KB limit.");
      const parsed = JSON.parse(await ga4CredentialFile.text()) as unknown;
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error("Credential file must contain one JSON object.");
      const result = await importGa4Credentials(projectId, ga4ProfileName, parsed as Record<string, unknown>);
      setIntegration(result);
      setGa4SelectedProfile(ga4ProfileName);
      setGa4CredentialFile(null);
      if (ga4FileInput.current) ga4FileInput.current.value = "";
      setNotice("GA4 analytics.readonly profile connected.");
    } catch (reason) {
      setError(messageFrom(reason));
      setNotice(null);
    } finally {
      setBusy(null);
    }
  }

  async function loadGa4Properties() {
    if (!ga4SelectedProfile) return;
    setBusy("ga4-properties");
    setError(null);
    setNotice(null);
    try {
      const found = await fetchGa4Properties(projectId, ga4SelectedProfile);
      setGa4Properties(found);
      setGa4SelectedProperty(found[0]?.property_id || "");
      setNotice(found.length ? `${found.length} accessible GA4 properties loaded.` : "No accessible GA4 properties were found.");
    } catch (reason) {
      setError(messageFrom(reason));
    } finally {
      setBusy(null);
    }
  }

  async function runEvidence(action: "crux" | "gsc" | "ga4") {
    setBusy(`${action}-verify`);
    setError(null);
    setNotice(null);
    try {
      await onRunAction(action);
      setNotice(`${action === "crux" ? "CrUX" : action === "ga4" ? "GA4" : "GSC"} evidence collection queued.`);
    } catch (reason) {
      setError(messageFrom(reason));
      setNotice(null);
    } finally {
      setBusy(null);
    }
  }

  if ((!integration || !shopify) && !error) return <div className={styles.state}>Loading local integration status</div>;

  const crux = integration?.crux;
  const gsc = integration?.gsc;
  const activeProfile = gsc?.profiles.find((profile) => profile.profile === selectedProfile);
  const boundProfile = gsc?.binding?.profile;
  const visibleShopifyScopes = shopify?.scopes.slice(0, 8) || [];

  return (
    <section className={styles.page} aria-label="SEO integrations">
      <header className={styles.pageHeader}>
        <h1 className="srOnly">SEO integrations</h1>
        <div className={styles.securityMark}>
          <LockKeyhole aria-hidden="true" size={18} />
          <span><strong>Local only</strong><small>Private files use mode 0600</small></span>
        </div>
      </header>

      {error ? <div className={styles.error} role="alert"><CircleAlert aria-hidden="true" size={17} /><span>{error}</span></div> : null}
      {notice ? <div className={styles.notice} role="status"><Check aria-hidden="true" size={17} /><span>{notice}</span></div> : null}

      {section === "core" ? <>
      {shopify?.applicable ? <article className={styles.integration}>
        <header className={styles.integrationHeader}>
          <Store aria-hidden="true" size={22} />
          <div><span>COMMERCE SOURCE</span><h2>Shopify Admin API</h2><p>Project-scoped store access for future product, collection, content, and theme evidence.</p></div>
          <Status value={shopify.status} />
        </header>
        <div className={styles.ledger}>
          <div><span>Credential scope</span><strong>This SEO project</strong></div>
          <div><span>API version</span><strong>{shopify.api_version}</strong></div>
          <div><span>Secret visibility</span><strong>Write only</strong></div>
        </div>
        {shopify.configured ? <section className={styles.shopifyDetails} aria-label="Shopify connection details">
          <div><span>Connected store</span><strong>{shopify.shop_name || shopify.shop_domain}</strong><small>{shopify.shop_domain}</small></div>
          <div><span>Granted scopes</span><strong>{shopify.scopes.length}</strong><small>{visibleShopifyScopes.join(", ") || "No resource scopes reported"}{shopify.scopes.length > visibleShopifyScopes.length ? `, +${shopify.scopes.length - visibleShopifyScopes.length} more` : ""}</small></div>
          <div data-warning={shopify.write_scope_count > 0 ? "true" : undefined}><span>Permission posture</span><strong>{shopify.write_scope_count ? `${shopify.write_scope_count} write scopes granted` : "Read scopes only"}</strong><small>Last verified {formatDate(shopify.verified_at)}</small></div>
        </section> : null}
        <form className={`${styles.configuration} ${styles.shopifyConfiguration}`} onSubmit={submitShopify}>
          <div className={styles.shopifyFields}>
            <label className={styles.field}>
              <span>Shopify shop domain</span>
              <input
                aria-label="Shopify shop domain"
                value={shopDomain}
                onChange={(event) => setShopDomain(event.target.value)}
                placeholder="store.myshopify.com"
                autoCapitalize="none"
                autoComplete="off"
                spellCheck={false}
                disabled={Boolean(busy)}
                required
              />
              <small>Use the permanent .myshopify.com domain, not the public storefront domain.</small>
            </label>
            <label className={styles.field}>
              <span>{shopify.configured ? "Replace Admin API access token" : "Admin API access token"}</span>
              <input
                aria-label="Admin API access token"
                type="password"
                value={shopifyToken}
                onChange={(event) => setShopifyToken(event.target.value)}
                placeholder={shopify.configured ? "Enter a new token to rotate" : "Enter the custom app access token"}
                autoComplete="off"
                spellCheck={false}
                disabled={Boolean(busy)}
                required
              />
              <small>The Workbench verifies the store and granted scopes before saving.</small>
            </label>
          </div>
          <div className={styles.actions}>
            <button className={styles.primary} type="submit" disabled={!shopDomain.trim() || !shopifyToken.trim() || Boolean(busy)}>
              <KeyRound aria-hidden="true" size={16} />{busy === "shopify-save" ? "Verifying" : shopify.configured ? "Replace connection" : "Connect Shopify"}
            </button>
            <button type="button" disabled={!shopify.configured || Boolean(busy)} onClick={() => void mutateShopify("shopify-verify", () => verifyShopifyCredentials(projectId), "Shopify connection verified.")}>
              <RefreshCw aria-hidden="true" size={15} />{busy === "shopify-verify" ? "Verifying" : "Verify connection"}
            </button>
            {shopify.removable ? <button className={styles.danger} type="button" disabled={Boolean(busy)} onClick={() => {
              if (confirmAction("Remove this project's Shopify Admin API credentials? Existing evidence files will remain.")) {
                void mutateShopify("shopify-delete", () => deleteShopifyCredentials(projectId), "Shopify connection removed.");
              }
            }}><Trash2 aria-hidden="true" size={15} />Remove connection</button> : null}
          </div>
        </form>
      </article> : null}

      {shopify?.applicable ? <article className={styles.integration}>
        <header className={styles.integrationHeader}>
          <LockKeyhole aria-hidden="true" size={22} />
          <div><span>SHOPIFY CRAWLER ACCESS</span><h2>Signed storefront crawl</h2><p>Use the Web Bot Auth signature generated by Shopify. It is attached automatically to requests for this project domain.</p></div>
          <Status value={shopify.crawler_access.status} />
        </header>
        <div className={styles.ledger}>
          <div><span>Signature scope</span><strong>{shopify.crawler_access.domain_host || "Project public domain"}</strong></div>
          <div><span>Expires</span><strong>{formatDate(shopify.crawler_access.expires_at)}</strong></div>
          <div><span>Secret visibility</span><strong>Write only</strong></div>
        </div>
        <form className={`${styles.configuration} ${styles.shopifyConfiguration}`} onSubmit={submitShopifyCrawlerAccess}>
          <div className={styles.shopifyFields}>
            <label className={styles.field}>
              <span>Public domain host</span>
              <input aria-label="Crawler access domain" value={crawlerDomain} onChange={(event) => setCrawlerDomain(event.target.value)} placeholder="www.example.com" autoCapitalize="none" autoComplete="off" spellCheck={false} disabled={Boolean(busy)} required />
              <small>Must match the host in this project's public URL.</small>
            </label>
            <label className={styles.field}>
              <span>Expiration date</span>
              <input aria-label="Crawler access expiration" type="datetime-local" value={crawlerExpiresAt} onChange={(event) => setCrawlerExpiresAt(event.target.value)} disabled={Boolean(busy)} required />
              <small>Shopify signatures expire automatically; save a new signature before this time.</small>
            </label>
          </div>
          <div className={styles.shopifyCrawlerFields}>
            <label className={styles.field}><span>Signature</span><textarea aria-label="Crawler Signature" value={crawlerSignature} onChange={(event) => setCrawlerSignature(event.target.value)} placeholder="Paste the Shopify Signature header" autoComplete="off" spellCheck={false} disabled={Boolean(busy)} required /></label>
            <label className={styles.field}><span>Signature-Input</span><textarea aria-label="Crawler Signature-Input" value={crawlerSignatureInput} onChange={(event) => setCrawlerSignatureInput(event.target.value)} placeholder="Paste the Shopify Signature-Input header" autoComplete="off" spellCheck={false} disabled={Boolean(busy)} required /></label>
            <label className={styles.field}><span>Signature-Agent</span><input aria-label="Crawler Signature-Agent" value={crawlerSignatureAgent} onChange={(event) => setCrawlerSignatureAgent(event.target.value)} disabled={Boolean(busy)} required /><small>Shopify's recommended value is &quot;https://shopify.com&quot;.</small></label>
          </div>
          <div className={styles.actions}>
            <button className={styles.primary} type="submit" disabled={!crawlerDomain.trim() || !crawlerSignature.trim() || !crawlerSignatureInput.trim() || !crawlerExpiresAt || Boolean(busy)}><KeyRound aria-hidden="true" size={16} />{busy === "shopify-crawler-save" ? "Storing" : shopify.crawler_access.configured ? "Replace crawler signature" : "Save crawler signature"}</button>
            {shopify.crawler_access.removable ? <button className={styles.danger} type="button" disabled={Boolean(busy)} onClick={() => {
              if (confirmAction("Remove this project's Shopify crawler signature?")) {
                void mutateShopify("shopify-crawler-delete", () => deleteShopifyCrawlerAccess(projectId), "Shopify crawler signature removed.");
              }
            }}><Trash2 aria-hidden="true" size={15} />Remove crawler signature</button> : null}
          </div>
        </form>
      </article> : null}

      <article className={styles.integration}>
        <header className={styles.integrationHeader}>
          <Activity aria-hidden="true" size={22} />
          <div><span>FIELD PERFORMANCE</span><h2>Chrome UX Report</h2><p>One workspace-level API key, used only for official CrUX requests.</p></div>
          {crux ? <Status value={crux.status} /> : null}
        </header>
        <div className={styles.ledger}>
          <div><span>Credential scope</span><strong>All local projects</strong></div>
          <div><span>Managed by</span><strong>{crux?.source === "environment" ? "Process environment" : crux?.source === "private_file" ? "Private runtime file" : "Not configured"}</strong></div>
          <div><span>Secret visibility</span><strong>Write only</strong></div>
        </div>
        <form className={styles.configuration} onSubmit={submitCrux}>
          <label className={styles.field}>
            <span>{crux?.configured ? "Replace API key" : "API key"}</span>
            <input
              aria-label="API key"
              type="password"
              value={cruxKey}
              onChange={(event) => setCruxKey(event.target.value)}
              placeholder={crux?.configured ? "Enter a new key to rotate" : "Enter Chrome UX Report API key"}
              autoComplete="off"
              spellCheck={false}
              disabled={crux?.source === "environment" || Boolean(busy)}
            />
            <small>{crux?.source === "environment" ? "Restart the UI with a different environment value to rotate this key." : "After saving, the key is never returned to this page."}</small>
          </label>
          <div className={styles.actions}>
            <button className={styles.primary} type="submit" disabled={!cruxKey.trim() || crux?.source === "environment" || Boolean(busy)}>
              <KeyRound aria-hidden="true" size={16} />{busy === "crux-save" ? "Storing" : crux?.configured ? "Rotate key" : "Store key"}
            </button>
            <button type="button" disabled={!crux?.configured || Boolean(busy)} onClick={() => runEvidence("crux")}>
              <RefreshCw aria-hidden="true" size={15} />{busy === "crux-verify" ? "Queuing" : "Verify with CrUX"}
            </button>
            {crux?.removable ? <button className={styles.danger} type="button" disabled={Boolean(busy)} onClick={() => {
              if (confirmAction("Remove the workspace CrUX API key? Existing evidence files will remain.")) {
                void mutate("crux-delete", () => deleteCruxKey(projectId), "CrUX key removed.");
              }
            }}><Trash2 aria-hidden="true" size={15} />Remove key</button> : null}
          </div>
        </form>
      </article>

      <article className={styles.integration}>
        <header className={styles.integrationHeader}>
          <SearchCheck aria-hidden="true" size={22} />
          <div><span>SEARCH EVIDENCE</span><h2>Google Search Console</h2><p>Reusable local auth profiles, bound separately to each SEO project.</p></div>
          {gsc ? <Status value={gsc.status} /> : null}
        </header>

        <ConnectionSteps profileCount={gsc?.profiles.length || 0} boundLabel={gsc?.binding?.property} status={gsc?.status} />

        <section className={styles.gscGrid}>
          <form className={styles.panel} onSubmit={importCredential}>
            <div className={styles.panelHeading}><Upload aria-hidden="true" size={17} /><div><h3>Add auth profile</h3><p>Use a new profile name when rotating credentials.</p></div></div>
            <div className={styles.twoFields}>
              <label className={styles.field}><span>Profile name</span><input value={profileName} onChange={(event) => setProfileName(event.target.value)} pattern="[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}" required disabled={Boolean(busy)} /></label>
              <label className={styles.field}><span>Credential type</span><select value={credentialType} onChange={(event) => setCredentialType(event.target.value as "oauth" | "service_account")} disabled={Boolean(busy)}><option value="oauth">Desktop OAuth</option><option value="service_account">Service account</option></select></label>
            </div>
            <label className={styles.fileField}>
              <span>Google credential JSON</span>
              <input ref={fileInput} type="file" accept="application/json,.json" onChange={(event) => setCredentialFile(event.target.files?.[0] || null)} disabled={Boolean(busy)} required />
              <small>{credentialFile?.name || "Select the downloaded Google JSON file, maximum 128 KB."}</small>
            </label>
            <button className={styles.primary} type="submit" disabled={!credentialFile || !profileName || Boolean(busy)}>{busy === "gsc-import" ? "Waiting for Google" : credentialType === "oauth" ? "Import and authorize" : "Import service account"}</button>
          </form>

          <GooglePropertyPanel
            busy={Boolean(busy)}
            canLoad={Boolean(activeProfile && activeProfile.status === "ready")}
            description="Only properties accessible to the selected profile are accepted."
            loading={busy === "gsc-properties"}
            onBind={() => void mutate("gsc-bind", () => saveGscBinding(projectId, selectedProfile, selectedProperty), "Search Console property bound to this project.")}
            onDisconnect={gsc?.binding?.property ? () => { if (confirmAction("Disconnect this Search Console property? Stored credentials and evidence will remain.")) void mutate("gsc-unbind", () => deleteGscBinding(projectId), "Search Console property disconnected."); } : undefined}
            onLoad={() => void loadProperties()}
            onProfileChange={(profile) => { setSelectedProfile(profile); setProperties([]); setSelectedProperty(""); }}
            onPropertyChange={setSelectedProperty}
            profileDetail={activeProfile?.principal || (activeProfile ? `${activeProfile.credential_type.replaceAll("_", " ")} · updated ${formatDate(activeProfile.updated_at)}` : "Add an auth profile first.")}
            profiles={gsc?.profiles || []}
            properties={properties.map((property) => ({ label: `${property.site_url} · ${property.permission_level}`, value: property.site_url }))}
            propertyLabel="Search Console property"
            selectedProfile={selectedProfile}
            selectedProperty={selectedProperty}
          />
        </section>

        {gsc?.profiles.length ? <section className={styles.profileLedger} aria-label="GSC credential profiles">
          <header><h3>Stored profiles</h3><span>Secrets hidden</span></header>
          {gsc.profiles.map((profile) => <div className={styles.profileRow} key={profile.profile}>
            <KeyRound aria-hidden="true" size={16} />
            <span><strong>{profile.profile}</strong><small>{profile.principal || profile.credential_type.replaceAll("_", " ")}</small></span>
            <Status value={profile.status} />
            <time>{formatDate(profile.updated_at)}</time>
            <button className={styles.iconDanger} type="button" aria-label={`Delete ${profile.profile} profile`} disabled={boundProfile === profile.profile || Boolean(busy)} onClick={() => {
              if (confirmAction(`Delete the ${profile.profile} credential profile? This cannot be undone.`)) {
                void mutate("gsc-profile-delete", () => deleteGscProfile(projectId, profile.profile), `Profile ${profile.profile} deleted.`);
              }
            }}><Trash2 aria-hidden="true" size={15} /></button>
          </div>)}
        </section> : null}

        <div className={styles.collectRow}>
          <div><SearchCheck aria-hidden="true" size={18} /><span><strong>Collect read-only Search Console evidence</strong><small>Search Analytics, Sitemap status, and a bounded URL Inspection sample.</small></span></div>
          <button className={styles.primary} type="button" disabled={gsc?.status !== "ready" || Boolean(busy)} onClick={() => runEvidence("gsc")}>{busy === "gsc-verify" ? "Queuing" : "Run GSC collection"}</button>
        </div>
      </article>

      <article className={styles.integration}>
        <header className={styles.integrationHeader}>
          <BarChart3 aria-hidden="true" size={22} />
          <div><span>ACQUISITION EVIDENCE</span><h2>Google Analytics 4</h2><p>Read-only analytics.readonly profile for channel and landing-page evidence, bound per project.</p></div>
          {integration?.ga4 ? <Status value={integration.ga4.status} /> : null}
        </header>

        <ConnectionSteps profileCount={integration?.ga4?.profiles.length || 0} boundLabel={integration?.ga4?.binding?.property ? `${integration.ga4.binding.property}${integration.ga4.binding.display_name ? ` · ${integration.ga4.binding.display_name}` : ""}` : null} status={integration?.ga4?.status} />

        <section className={styles.gscGrid}>
          <form className={styles.panel} onSubmit={importGa4Credential}>
            <div className={styles.panelHeading}><Upload aria-hidden="true" size={17} /><div><h3>Add GA4 auth profile</h3><p>Import a GA4 analytics.readonly token file. Use a new profile name when rotating.</p></div></div>
            <label className={styles.field}><span>Profile name</span><input value={ga4ProfileName} onChange={(event) => setGa4ProfileName(event.target.value)} pattern="[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}" required disabled={Boolean(busy)} /></label>
            <label className={styles.fileField}>
              <span>GA4 token JSON</span>
              <input ref={ga4FileInput} type="file" accept="application/json,.json" onChange={(event) => setGa4CredentialFile(event.target.files?.[0] || null)} disabled={Boolean(busy)} required />
              <small>{ga4CredentialFile?.name || "Select the GA4 token JSON file, maximum 128 KB."}</small>
            </label>
            <button className={styles.primary} type="submit" disabled={!ga4CredentialFile || !ga4ProfileName || Boolean(busy)}>{busy === "ga4-import" ? "Importing" : "Import GA4 token"}</button>
          </form>

          <GooglePropertyPanel
            busy={Boolean(busy)}
            canLoad={Boolean(ga4SelectedProfile)}
            description="Only GA4 properties accessible to the selected profile are accepted."
            loading={busy === "ga4-properties"}
            onBind={() => void mutate("ga4-bind", () => saveGa4Binding(projectId, ga4SelectedProfile, ga4SelectedProperty), "GA4 property bound to this project.")}
            onDisconnect={integration?.ga4?.binding?.property ? () => { if (confirmAction("Disconnect this GA4 property? Stored credentials and evidence will remain.")) void mutate("ga4-unbind", () => deleteGa4Binding(projectId), "GA4 property disconnected."); } : undefined}
            onLoad={() => void loadGa4Properties()}
            onProfileChange={(profile) => { setGa4SelectedProfile(profile); setGa4Properties([]); setGa4SelectedProperty(""); }}
            onPropertyChange={setGa4SelectedProperty}
            profiles={integration?.ga4?.profiles || []}
            properties={ga4Properties.map((property) => ({ label: `${property.property_id} · ${property.display_name} (${property.account_name})`, value: property.property_id }))}
            propertyLabel="GA4 property"
            selectedProfile={ga4SelectedProfile}
            selectedProperty={ga4SelectedProperty}
          />
        </section>

        <div className={styles.collectRow}>
          <div><BarChart3 aria-hidden="true" size={18} /><span><strong>Collect read-only GA4 evidence</strong><small>Channel overview and organic landing-page sessions, engaged sessions, and key events.</small></span></div>
          <button className={styles.primary} type="button" disabled={integration?.ga4?.status !== "ready" || Boolean(busy)} onClick={() => runEvidence("ga4")}>{busy === "ga4-verify" ? "Queuing" : "Run GA4 collection"}</button>
        </div>
      </article>
      </> : dataForSeo ? <article className={styles.integration}>
        <header className={styles.integrationHeader}>
          <Database aria-hidden="true" size={22} />
          <div><span>OPTIONAL KEYWORD DATA</span><h2>DataForSEO</h2><p>Project-scoped credentials for paid keyword evidence. Saving verifies the account with a free request; keyword calls stay disabled until a workflow explicitly requests them.</p></div>
          {dataForSeo ? <Status value={dataForSeo.status} /> : null}
        </header>
        <div className={styles.ledger}>
          <div><span>Transport</span><strong>REST API v3</strong></div>
          <div><span>Billing</span><strong>Metered per request</strong></div>
          <div><span>Secret visibility</span><strong>Write only</strong></div>
        </div>
        <form className={styles.configuration} onSubmit={submitDataForSeo}>
          <div className={styles.twoFields}>
            <label className={styles.field}>
              <span>{dataForSeo?.configured ? "Replace API login" : "API login"}</span>
              <input aria-label="DataForSEO API login" type="text" value={dataForSeoLogin} onChange={(event) => setDataForSeoLogin(event.target.value)} placeholder="API Access login" autoCapitalize="none" autoComplete="username" spellCheck={false} disabled={Boolean(busy)} required />
              <small>Use the login shown in DataForSEO API Access.</small>
            </label>
            <label className={styles.field}>
              <span>{dataForSeo?.configured ? "Replace API password" : "API password"}</span>
              <input aria-label="DataForSEO API password" type="password" value={dataForSeoPassword} onChange={(event) => setDataForSeoPassword(event.target.value)} placeholder="API password, not account password" autoComplete="new-password" spellCheck={false} disabled={Boolean(busy)} required />
              <small>This is different from the password used to sign in to the website.</small>
            </label>
          </div>
          <div className={styles.actions}>
            <button className={styles.primary} type="submit" disabled={!dataForSeoLogin.trim() || !dataForSeoPassword || Boolean(busy)}><KeyRound aria-hidden="true" size={16} />{busy === "dataforseo-save" ? "Verifying" : dataForSeo?.configured ? "Verify and replace" : "Verify and store"}</button>
            {dataForSeo?.removable ? <button className={styles.danger} type="button" disabled={Boolean(busy)} onClick={() => {
              if (confirmAction("Remove this project's DataForSEO credentials? Existing evidence files will remain.")) {
                setBusy("dataforseo-delete");
                setError(null);
                setNotice(null);
                void deleteDataForSeoCredentials(projectId)
                  .then((result) => { setDataForSeo(result); setNotice("DataForSEO credentials removed."); })
                  .catch((reason) => setError(messageFrom(reason)))
                  .finally(() => setBusy(null));
              }
            }}><Trash2 aria-hidden="true" size={15} />Remove credentials</button> : null}
          </div>
        </form>
      </article> : <div className={styles.state}>Loading optional provider status</div>}

      <footer className={styles.securityFooter}>
        <LockKeyhole aria-hidden="true" size={16} />
        <p><strong>Security boundary:</strong> secret values are accepted only by fixed local endpoints, written to ignored runtime files, and never included in status responses. Remote Workbench hosts cannot access this page's credential APIs.</p>
      </footer>
    </section>
  );
}
