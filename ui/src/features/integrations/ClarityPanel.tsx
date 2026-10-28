import { Activity } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";

import { deleteClarityCredentials, fetchClarityEvidence, fetchClarityIntegration, fetchClarityRecordingLinks, fetchJobs, saveClarityCredentials, startClarityQuery, verifyClarityConnection } from "../../api/client";
import type { ClarityEvidence, ClarityIntegration, ClarityQuery } from "../../api/types";
import { confirmAction } from "../../components/ActionButton";
import { HelpTooltip } from "../../components/HelpTooltip";
import { StatusPill, statusLabel, statusTone } from "../../components/StatusPill";
import styles from "./IntegrationsPage.module.css";

const kinds = { query: "dashboard", recordings: "recordings", docs: "documentation" };

export function ClarityPanel({ projectId }: { projectId: string }) {
  const [integration, setIntegration] = useState<ClarityIntegration | null>(null);
  const [token, setToken] = useState("");
  const [remoteId, setRemoteId] = useState("");
  const [timezone, setTimezone] = useState("UTC");
  const [action, setAction] = useState<ClarityQuery["action"]>("query");
  const [query, setQuery] = useState("Total sessions");
  const [start, setStart] = useState(new Date(Date.now() - 86400000).toISOString().slice(0, 10));
  const [end, setEnd] = useState(new Date(Date.now() - 86400000).toISOString().slice(0, 10));
  const [url, setUrl] = useState("");
  const [device, setDevice] = useState("");
  const [channel, setChannel] = useState("");
  const [count, setCount] = useState(10);
  const [rageClick, setRageClick] = useState(false);
  const [deadClick, setDeadClick] = useState(false);
  const [jsError, setJsError] = useState(false);
  const [force, setForce] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [jobId, setJobId] = useState("");
  const [jobKind, setJobKind] = useState("dashboard");
  const [evidence, setEvidence] = useState<ClarityEvidence | null>(null);
  const [links, setLinks] = useState<string[]>([]);

  useEffect(() => {
    let active = true;
    fetchClarityIntegration(projectId).then(value => {
      if (!active) return;
      setIntegration(value); setRemoteId(value.project_id || ""); setTimezone(value.timezone || "UTC");
    }).catch(() => { if (active) setError("Clarity status is unavailable."); });
    return () => { active = false; };
  }, [projectId]);

  useEffect(() => {
    let active = true;
    setEvidence(null);
    setLinks([]);
    fetchClarityEvidence(projectId, kinds[action]).then(value => { if (active) setEvidence(value); }).catch(() => { if (active) setError("Clarity evidence is unavailable."); });
    return () => { active = false; };
  }, [projectId, action]);

  useEffect(() => {
    if (!jobId) return;
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const job = (await fetchJobs(projectId)).find(item => item.id === jobId);
        if (!active) return;
        if (job && ["succeeded", "failed", "cancelled"].includes(job.status)) {
          const value = await fetchClarityEvidence(projectId, jobKind);
          const recordingLinks = jobKind === "recordings" ? await fetchClarityRecordingLinks(projectId) : [];
          if (!active) return;
          setEvidence(value); setJobId(""); setBusy(false);
          setLinks(recordingLinks);
          if (job.status !== "succeeded") setError("Clarity query failed. Review the evidence status below.");
        } else timer = setTimeout(() => void poll(), 1000);
      } catch { if (active) { setError("Could not refresh the query status."); setJobId(""); setBusy(false); } }
    };
    void poll();
    return () => { active = false; clearTimeout(timer); };
  }, [jobId, projectId, jobKind]);

  async function mutate(operation: () => Promise<ClarityIntegration>) {
    setBusy(true); setError("");
    try { setIntegration(await operation()); setLinks([]); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Clarity request failed."); }
    finally { setToken(""); setBusy(false); }
  }

  async function run(event: FormEvent) {
    event.preventDefault(); setError(""); setBusy(true);
    const request: ClarityQuery = { action, force };
    if (action !== "recordings") request.query = query;
    if (action === "query") Object.assign(request, { start, end, timezone });
    if (action === "recordings") {
      // Date inputs represent complete UTC days; end is exclusive for recordings.
      const exclusiveEnd = new Date(`${end}T00:00:00Z`);
      exclusiveEnd.setUTCDate(exclusiveEnd.getUTCDate() + 1);
      Object.assign(request, { start: `${start}T00:00:00Z`, end: exclusiveEnd.toISOString(), count, rage_click: rageClick, dead_click: deadClick, js_error: jsError,
        ...(url ? { url } : {}), ...(device ? { device } : {}), ...(channel ? { channel } : {}) });
    }
    try { const job = await startClarityQuery(projectId, request); setJobKind(kinds[action]); setJobId(job.id); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Clarity query failed."); setBusy(false); }
  }

  return <article className={`${styles.integration} ${styles.clarity}`} aria-label="Clarity connection">
    <header className={styles.integrationHeader}><Activity aria-hidden="true" size={22} /><div><span>OPTIONAL BEHAVIOR ANALYTICS</span><h2>Microsoft Clarity</h2><p>Explore page engagement and find recording samples for this brand.</p></div><StatusPill value={statusLabel(integration?.status || "not_collected")} tone={statusTone(integration?.status, "evidence")} /></header>
    <div className={styles.clarityBody}>
      {error ? <p role="alert" className={styles.error}>{error}</p> : null}
      <p>Runtime: {integration?.runtime_ready ? "Ready" : "Needs setup"} · Credentials: {integration?.credential_verified ? "Verified" : "Unverified"} · Project identity: {integration?.identity_verified ? "Verified" : "Declared, unverified"} <HelpTooltip label="Clarity project identity">A successful API request does not independently prove that the token belongs to the declared project.</HelpTooltip></p>
      <form onSubmit={event => { event.preventDefault(); void mutate(() => saveClarityCredentials(projectId, token, remoteId, timezone)); }}>
        <div className={styles.clarityFields}>
          <label className={styles.field}><span>Clarity project ID</span><input value={remoteId} onChange={event => setRemoteId(event.target.value)} required disabled={busy} /></label>
          <label className={styles.field}><span>Query timezone</span><input value={timezone} onChange={event => setTimezone(event.target.value)} required disabled={busy} /><small>Explicit IANA timezone, for example UTC.</small></label>
          <label className={styles.field}><span>Clarity API token</span><input type="password" autoComplete="new-password" value={token} onChange={event => setToken(event.target.value)} required disabled={busy} /><small>Write-only; cleared after each save attempt.</small></label>
        </div>
        <div className={styles.actions}>
          <button type="submit" disabled={busy || !token || !remoteId || !timezone}>{integration?.configured ? "Verify and replace Clarity" : "Verify and connect Clarity"}</button>
          <button type="button" disabled={busy || !integration?.configured} onClick={() => void mutate(() => verifyClarityConnection(projectId))}>Verify Clarity connection</button>
          <button type="button" disabled={busy || !integration?.configured} onClick={() => { if (confirmAction("Disconnect Clarity for this brand? Existing evidence will remain.")) void mutate(() => deleteClarityCredentials(projectId)); }}>Disconnect Clarity</button>
        </div>
      </form>
      <form onSubmit={event => void run(event)}>
        <h3>Query Clarity <HelpTooltip label="Clarity evidence">Clarity observations remain separate from formal SEO statistics. Recording samples do not establish overall problem rates.</HelpTooltip></h3>
        <div className={styles.clarityFields}>
          <label className={styles.field}><span>Clarity operation</span><select value={action} onChange={event => setAction(event.target.value as ClarityQuery["action"])} disabled={busy}><option value="query">Analytics dashboard</option><option value="recordings">Recording samples</option><option value="docs">Documentation</option></select></label>
          {action !== "recordings" ? <label className={styles.field}><span>Clarity question</span><input value={query} onChange={event => setQuery(event.target.value)} maxLength={2000} required disabled={busy} /></label> : null}
          {action !== "docs" ? <><label className={styles.field}><span>Start date{action === "recordings" ? " (UTC)" : ""}</span><input type="date" value={start} onChange={event => setStart(event.target.value)} required disabled={busy} /></label><label className={styles.field}><span>End date, inclusive{action === "recordings" ? " (UTC)" : ""}</span><input type="date" value={end} min={start} onChange={event => setEnd(event.target.value)} required disabled={busy} /></label></> : null}
          {action === "recordings" ? <>
            <label className={styles.field}><span>Page URL (optional)</span><input type="url" value={url} onChange={event => setUrl(event.target.value)} disabled={busy} placeholder={integration?.site_url} /></label>
            <label className={styles.field}><span>Device</span><select value={device} onChange={event => setDevice(event.target.value)} disabled={busy}><option value="">All devices</option>{["Mobile", "PC", "Tablet"].map(item => <option key={item}>{item}</option>)}</select></label>
            <label className={styles.field}><span>Channel</span><select value={channel} onChange={event => setChannel(event.target.value)} disabled={busy}><option value="">All channels</option>{["OrganicSearch", "Direct", "Email", "Display", "Social", "PaidSearch", "Other", "Affiliate", "Referral", "Video", "Audio", "SMS", "AITools", "PaidAITools"].map(item => <option key={item}>{item}</option>)}</select></label>
            <label className={styles.field}><span>Maximum samples</span><input type="number" min={1} max={50} value={count} onChange={event => setCount(Number(event.target.value))} disabled={busy} /></label>
          </> : null}
        </div>
        <div className={styles.actions}>
          {action === "recordings" ? <>{[["Rage clicks", rageClick, setRageClick], ["Dead clicks", deadClick, setDeadClick], ["JavaScript errors", jsError, setJsError]].map(([label, checked, setter]) => <label key={String(label)}><input type="checkbox" checked={Boolean(checked)} onChange={event => (setter as (value: boolean) => void)(event.target.checked)} disabled={busy} />{String(label)}</label>)}</> : null}
          <label><input type="checkbox" checked={force} onChange={event => setForce(event.target.checked)} disabled={busy} />Refresh cached result</label>
          <button type="submit" disabled={busy || !integration?.configured || !integration?.runtime_ready}>{busy ? "Working…" : "Run Clarity query"}</button>
        </div>
      </form>
      <section aria-label="Clarity evidence"><h3>Latest {kinds[action]} evidence</h3><StatusPill value={statusLabel(evidence?.collection_status || "not_collected")} context="evidence" />
        <p>{evidence?.reason_code?.replaceAll("_", " ")} {evidence?.generated_at ? `· ${evidence.generated_at}` : ""}</p>
        {evidence?.warnings?.map(warning => <p key={warning}>{warning}</p>)}
        {evidence?.errors?.map(message => <p key={message}>{message}</p>)}
        {action === "recordings" && links.length ? <><p>Private recording links expire from this local viewer after 15 minutes.</p><ul>{links.map((link, index) => <li key={link}><a href={link} target="_blank" rel="noreferrer">Open recording sample {index + 1}</a></li>)}</ul></> : null}
        {evidence?.response !== undefined ? <pre className={styles.clarityResult}>{JSON.stringify(evidence.response, null, 2)}</pre> : null}
      </section>
    </div>
  </article>;
}
