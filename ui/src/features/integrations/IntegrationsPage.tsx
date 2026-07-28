import {
  Activity,
  Check,
  CircleAlert,
  KeyRound,
  Link2,
  LockKeyhole,
  RefreshCw,
  SearchCheck,
  Trash2,
  Upload,
} from "lucide-react";
import { type FormEvent, useEffect, useRef, useState } from "react";

import {
  ApiError,
  deleteCruxKey,
  deleteGscBinding,
  deleteGscProfile,
  fetchGoogleIntegration,
  fetchGscProperties,
  importGscCredentials,
  saveCruxKey,
  saveGscBinding,
} from "../../api/client";
import type { GoogleIntegration, GscProperty } from "../../api/types";
import styles from "./IntegrationsPage.module.css";


function messageFrom(error: unknown): string {
  if (error instanceof ApiError && typeof error.detail === "string") return error.detail;
  if (error instanceof Error) return error.message;
  return "The integration request could not be completed.";
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    ready: "Ready",
    needs_key: "Needs key",
    needs_auth: "Needs authentication",
    not_bound: "Not bound",
    reauth_required: "Reauthentication required",
    incomplete: "Incomplete",
    unsafe_path: "Unsafe path",
    missing_profile: "Profile missing",
    invalid_binding: "Invalid binding",
  };
  return labels[status] || status.replaceAll("_", " ");
}

function Status({ value }: { value: string }) {
  const ready = value === "ready";
  return (
    <span className={ready ? styles.statusReady : styles.statusAttention}>
      {ready ? <Check aria-hidden="true" size={13} /> : <CircleAlert aria-hidden="true" size={13} />}
      {statusLabel(value)}
    </span>
  );
}

function formatDate(value?: string | null): string {
  if (!value) return "Not recorded";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

type Props = {
  projectId: string;
  refreshKey: number;
  onRunAction: (action: "crux" | "gsc") => Promise<void>;
};

export function IntegrationsPage({ projectId, refreshKey, onRunAction }: Props) {
  const [integration, setIntegration] = useState<GoogleIntegration | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [cruxKey, setCruxKey] = useState("");
  const [credentialType, setCredentialType] = useState<"oauth" | "service_account">("oauth");
  const [profileName, setProfileName] = useState("default");
  const [credentialFile, setCredentialFile] = useState<File | null>(null);
  const [selectedProfile, setSelectedProfile] = useState("default");
  const [properties, setProperties] = useState<GscProperty[]>([]);
  const [selectedProperty, setSelectedProperty] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let active = true;
    setError(null);
    fetchGoogleIntegration(projectId)
      .then((result) => { if (active) setIntegration(result); })
      .catch((reason) => { if (active) setError(messageFrom(reason)); });
    return () => { active = false; };
  }, [projectId, refreshKey]);

  useEffect(() => {
    if (!integration) return;
    const preferred = integration.gsc.binding?.profile || integration.gsc.profiles[0]?.profile;
    if (preferred && !integration.gsc.profiles.some((profile) => profile.profile === selectedProfile)) {
      setSelectedProfile(preferred);
    }
  }, [integration, selectedProfile]);

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

  async function runEvidence(action: "crux" | "gsc") {
    setBusy(`${action}-verify`);
    setError(null);
    setNotice(null);
    try {
      await onRunAction(action);
      setNotice(`${action === "crux" ? "CrUX" : "GSC"} evidence collection queued.`);
    } catch (reason) {
      setError(messageFrom(reason));
    } finally {
      setBusy(null);
    }
  }

  if (!integration && !error) return <div className={styles.state}>Loading local integration status</div>;

  const crux = integration?.crux;
  const gsc = integration?.gsc;
  const activeProfile = gsc?.profiles.find((profile) => profile.profile === selectedProfile);
  const boundProfile = gsc?.binding?.profile;

  return (
    <section className={styles.page} aria-label="SEO integrations">
      <header className={styles.pageHeader}>
        <div>
          <span>LOCAL TRUST LEDGER</span>
          <h1>SEO integrations</h1>
          <p>Configure Google evidence sources without exposing secret values to project files, logs, or API responses.</p>
        </div>
        <div className={styles.securityMark}>
          <LockKeyhole aria-hidden="true" size={18} />
          <span><strong>Local only</strong><small>Private files use mode 0600</small></span>
        </div>
      </header>

      {error ? <div className={styles.error} role="alert"><CircleAlert aria-hidden="true" size={17} /><span>{error}</span></div> : null}
      {notice ? <div className={styles.notice} role="status"><Check aria-hidden="true" size={17} /><span>{notice}</span></div> : null}

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
              if (window.confirm("Remove the workspace CrUX API key? Existing evidence files will remain.")) {
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

        <ol className={styles.steps}>
          <li data-state={gsc?.profiles.length ? "ready" : "current"}><span>1</span><div><strong>Auth profile</strong><small>{gsc?.profiles.length ? `${gsc.profiles.length} available` : "Import credentials"}</small></div></li>
          <li data-state={gsc?.binding?.property ? "ready" : gsc?.profiles.length ? "current" : "waiting"}><span>2</span><div><strong>Project property</strong><small>{gsc?.binding?.property || "Not bound"}</small></div></li>
          <li data-state={gsc?.status === "ready" ? "current" : "waiting"}><span>3</span><div><strong>Evidence</strong><small>{gsc?.status === "ready" ? "Ready to collect" : "Complete setup first"}</small></div></li>
        </ol>

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

          <section className={styles.panel}>
            <div className={styles.panelHeading}><Link2 aria-hidden="true" size={17} /><div><h3>Bind this project</h3><p>Only properties accessible to the selected profile are accepted.</p></div></div>
            <label className={styles.field}>
              <span>Auth profile</span>
              <select value={selectedProfile} onChange={(event) => { setSelectedProfile(event.target.value); setProperties([]); setSelectedProperty(""); }} disabled={!gsc?.profiles.length || Boolean(busy)}>
                {gsc?.profiles.length ? gsc.profiles.map((profile) => <option value={profile.profile} key={profile.profile}>{profile.profile} · {statusLabel(profile.status)}</option>) : <option value="default">No profiles</option>}
              </select>
              <small>{activeProfile?.principal || (activeProfile ? `${activeProfile.credential_type.replaceAll("_", " ")} · updated ${formatDate(activeProfile.updated_at)}` : "Add an auth profile first.")}</small>
            </label>
            <button type="button" disabled={!activeProfile || activeProfile.status !== "ready" || Boolean(busy)} onClick={loadProperties}>{busy === "gsc-properties" ? "Loading properties" : "Load accessible properties"}</button>
            <label className={styles.field}>
              <span>Search Console property</span>
              <select value={selectedProperty} onChange={(event) => setSelectedProperty(event.target.value)} disabled={!properties.length || Boolean(busy)}>
                {properties.length ? properties.map((property) => <option key={property.site_url} value={property.site_url}>{property.site_url} · {property.permission_level}</option>) : <option value="">Load properties to select</option>}
              </select>
            </label>
            <div className={styles.actions}>
              <button className={styles.primary} type="button" disabled={!selectedProperty || Boolean(busy)} onClick={() => mutate("gsc-bind", () => saveGscBinding(projectId, selectedProfile, selectedProperty), "Search Console property bound to this project.")}>Bind property</button>
              {gsc?.binding?.property ? <button className={styles.danger} type="button" disabled={Boolean(busy)} onClick={() => {
                if (window.confirm("Disconnect this Search Console property? Stored credentials and evidence will remain.")) {
                  void mutate("gsc-unbind", () => deleteGscBinding(projectId), "Search Console property disconnected.");
                }
              }}>Disconnect</button> : null}
            </div>
          </section>
        </section>

        {gsc?.profiles.length ? <section className={styles.profileLedger} aria-label="GSC credential profiles">
          <header><h3>Stored profiles</h3><span>Secrets hidden</span></header>
          {gsc.profiles.map((profile) => <div className={styles.profileRow} key={profile.profile}>
            <KeyRound aria-hidden="true" size={16} />
            <span><strong>{profile.profile}</strong><small>{profile.principal || profile.credential_type.replaceAll("_", " ")}</small></span>
            <Status value={profile.status} />
            <time>{formatDate(profile.updated_at)}</time>
            <button className={styles.iconDanger} type="button" aria-label={`Delete ${profile.profile} profile`} disabled={boundProfile === profile.profile || Boolean(busy)} onClick={() => {
              if (window.confirm(`Delete the ${profile.profile} credential profile? This cannot be undone.`)) {
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

      <footer className={styles.securityFooter}>
        <LockKeyhole aria-hidden="true" size={16} />
        <p><strong>Security boundary:</strong> secret values are accepted only by fixed local endpoints, written to ignored runtime files, and never included in status responses. Remote Workbench hosts cannot access this page's credential APIs.</p>
      </footer>
    </section>
  );
}
