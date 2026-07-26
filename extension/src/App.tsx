import {
  AlertTriangle,
  Braces,
  Check,
  ChevronRight,
  CircleAlert,
  Clipboard,
  Download,
  ExternalLink,
  FileText,
  Image,
  Link2,
  LoaderCircle,
  MonitorUp,
  RefreshCw,
  ScanSearch,
  Unplug,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { buildCapture, inspectPage } from "./inspector";
import type { BrowserCapture, Finding } from "./types";


type TabName = "overview" | "structure" | "assets" | "signals" | "workbench";

const tabs: Array<{ id: TabName; label: string }> = [
  { id: "overview", label: "Overview" },
  { id: "structure", label: "Structure" },
  { id: "assets", label: "Assets" },
  { id: "signals", label: "Signals" },
  { id: "workbench", label: "Workbench" },
];

const displayUrl = (value: string) => {
  try {
    const url = new URL(value);
    return `${url.hostname}${url.pathname === "/" ? "" : url.pathname}`;
  } catch {
    return value;
  }
};

function MetricRow({ label, value, note, state = "neutral" }: { label: string; value: string | number; note?: string; state?: "good" | "warn" | "bad" | "neutral" }) {
  return (
    <div className="metric-row">
      <div className="metric-copy">
        <span className="metric-label">{label}</span>
        {note && <span className="metric-note">{note}</span>}
      </div>
      <span className={`metric-value ${state}`}>{value}</span>
    </div>
  );
}

function FindingRow({ finding }: { finding: Finding }) {
  const Icon = finding.severity === "critical" ? CircleAlert : finding.severity === "warning" ? AlertTriangle : Check;
  return (
    <div className="finding-row">
      <Icon size={15} aria-hidden="true" />
      <div>
        <strong>{finding.title}</strong>
        <span>{finding.detail}</span>
      </div>
    </div>
  );
}

function EmptyState({ error, onRetry }: { error: string; onRetry: () => void }) {
  return (
    <main className="empty-state">
      <ScanSearch size={32} aria-hidden="true" />
      <h1>This page cannot be inspected</h1>
      <p>{error}</p>
      <button className="primary-button" onClick={onRetry}><RefreshCw size={15} /> Try again</button>
    </main>
  );
}

export function App() {
  const [activeTab, setActiveTab] = useState<TabName>("overview");
  const [capture, setCapture] = useState<BrowserCapture | null>(null);
  const [status, setStatus] = useState<"scanning" | "ready" | "error">("scanning");
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  const scan = useCallback(async () => {
    setStatus("scanning");
    setError("");
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tab?.id || !tab.url || !/^https?:/.test(tab.url)) {
        throw new Error("Open a public http or https page, then reopen SEO Workbench.");
      }
      const [result] = await chrome.scripting.executeScript({ target: { tabId: tab.id }, func: inspectPage });
      if (!result?.result) throw new Error("Chrome did not return a page snapshot.");
      setCapture(buildCapture(result.result, chrome.runtime.getManifest().version));
      setStatus("ready");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The active page could not be inspected.");
      setStatus("error");
    }
  }, []);

  useEffect(() => { void scan(); }, [scan]);

  const download = () => {
    if (!capture) return;
    const blob = new Blob([`${JSON.stringify(capture, null, 2)}\n`], { type: "application/json" });
    const href = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = href;
    anchor.download = `seo-workbench-${new URL(capture.final_url).hostname}-${capture.captured_at.replace(/[:.]/g, "-")}.json`;
    anchor.click();
    URL.revokeObjectURL(href);
  };

  const copyHandoff = async () => {
    if (!capture) return;
    await navigator.clipboard.writeText([
      `Review the SEO Workbench browser capture for ${capture.final_url}.`,
      `Critical: ${capture.summary.critical}; warnings: ${capture.summary.warning}; passed: ${capture.summary.passed}.`,
      ...capture.findings.filter((item) => item.severity !== "passed").map((item) => `- ${item.title}: ${item.detail}`),
    ].join("\n"));
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <img src="/icons/icon-32.png" alt="" />
          <div><strong>SEO Workbench</strong><span>On-page SEO inspector</span></div>
        </div>
        <div className="local-status" title="The extension is working locally without a Workbench connection">
          <span /> LOCAL
        </div>
      </header>

      <section className={`scan-rail ${status}`} aria-live="polite">
        <div className="scan-progress" />
        <span>{status === "scanning" ? "Inspecting active page…" : status === "ready" ? "Inspection complete" : "Inspection stopped"}</span>
      </section>

      {status === "error" ? <EmptyState error={error} onRetry={() => void scan()} /> : (
        <>
          <section className="page-context">
            <div className="eyebrow">ACTIVE PAGE</div>
            <h1>{capture?.document.title || "Reading page…"}</h1>
            <p>{capture ? displayUrl(capture.final_url) : "Waiting for Chrome"}</p>
            <button className="icon-button" onClick={() => void scan()} aria-label="Inspect page again" title="Inspect page again">
              <RefreshCw size={16} className={status === "scanning" ? "spin" : ""} />
            </button>
          </section>

          {capture && (
            <section className="score-strip" aria-label="Inspection summary">
              <div className="score critical"><span>{capture.summary.critical}</span>Critical</div>
              <div className="score warning"><span>{capture.summary.warning}</span>Warnings</div>
              <div className="score passed"><span>{capture.summary.passed}</span>Passed</div>
            </section>
          )}

          <nav className="tabs" aria-label="Inspection sections">
            {tabs.map((tab) => (
              <button key={tab.id} className={activeTab === tab.id ? "active" : ""} onClick={() => setActiveTab(tab.id)}>
                {tab.label}
              </button>
            ))}
          </nav>

          <main className="panel-content">
            {status === "scanning" && !capture ? <div className="loading"><LoaderCircle className="spin" /><span>Collecting document signals</span></div> : capture && (
              <>
                {activeTab === "overview" && <Overview capture={capture} />}
                {activeTab === "structure" && <Structure capture={capture} />}
                {activeTab === "assets" && <Assets capture={capture} />}
                {activeTab === "signals" && <Signals capture={capture} />}
                {activeTab === "workbench" && <Workbench />}
              </>
            )}
          </main>

          {capture && (
            <footer className="action-bar">
              <button className="secondary-button" onClick={download}><Download size={15} /> Export JSON</button>
              <button className="primary-button" onClick={() => void copyHandoff()}>{copied ? <Check size={15} /> : <Clipboard size={15} />}{copied ? "Copied" : "Copy handoff"}</button>
            </footer>
          )}
        </>
      )}
    </div>
  );
}

function Overview({ capture }: { capture: BrowserCapture }) {
  const titleLength = capture.document.title.length;
  const descriptionLength = capture.document.description.length;
  return (
    <>
      <section className="section-block">
        <div className="section-heading"><FileText size={15} /><h2>Search metadata</h2></div>
        <MetricRow label="Title" value={`${titleLength}/60`} state={!titleLength ? "bad" : titleLength > 60 ? "warn" : "good"} note={capture.document.title || "Not declared"} />
        <MetricRow label="Description" value={`${descriptionLength}/160`} state={!descriptionLength || descriptionLength > 160 ? "warn" : "good"} note={capture.document.description || "Not declared"} />
        <MetricRow label="Canonical" value={capture.document.canonical ? "Declared" : "Missing"} state={capture.document.canonical ? "good" : "warn"} note={capture.document.canonical || undefined} />
        <MetricRow label="Robots" value={capture.document.robots || "Default"} />
      </section>
      <section className="section-block">
        <div className="section-heading"><CircleAlert size={15} /><h2>Findings</h2><span>{capture.findings.length}</span></div>
        <div className="finding-list">{capture.findings.map((item) => <FindingRow key={item.id} finding={item} />)}</div>
      </section>
    </>
  );
}

function Structure({ capture }: { capture: BrowserCapture }) {
  return (
    <>
      <section className="section-block">
        <div className="section-heading"><FileText size={15} /><h2>Heading outline</h2><span>{capture.headings.length}</span></div>
        {capture.headings.length ? <div className="outline-list">{capture.headings.map((heading, index) => (
          <div key={`${heading.level}-${index}`} style={{ paddingLeft: `${(heading.level - 1) * 12}px` }}><span>H{heading.level}</span>{heading.text || "Empty heading"}</div>
        ))}</div> : <p className="muted-copy">No headings found.</p>}
      </section>
      <section className="section-block">
        <div className="section-heading"><Braces size={15} /><h2>Structured data</h2></div>
        <MetricRow label="JSON-LD blocks" value={capture.structured_data.blocks} />
        <MetricRow label="Parse errors" value={capture.structured_data.parse_errors} state={capture.structured_data.parse_errors ? "bad" : "good"} />
        <div className="tag-list">{capture.structured_data.types.map((type) => <span key={type}>{type}</span>)}</div>
      </section>
      <section className="section-block">
        <div className="section-heading"><ExternalLink size={15} /><h2>Language alternates</h2><span>{capture.hreflang.length}</span></div>
        {capture.hreflang.map((item) => <MetricRow key={`${item.lang}-${item.href}`} label={item.lang} value={displayUrl(item.href)} />)}
        {!capture.hreflang.length && <p className="muted-copy">No hreflang declarations found.</p>}
      </section>
    </>
  );
}

function Assets({ capture }: { capture: BrowserCapture }) {
  return (
    <>
      <section className="section-block">
        <div className="section-heading"><Image size={15} /><h2>Images</h2><span>{capture.images.total}</span></div>
        <MetricRow label="Missing alt" value={capture.images.missing_alt} state={capture.images.missing_alt ? "warn" : "good"} />
        <MetricRow label="Empty alt" value={capture.images.empty_alt} />
        <MetricRow label="Lazy loaded" value={capture.images.lazy_loaded} />
        <MetricRow label="Missing dimensions" value={capture.images.missing_dimensions} state={capture.images.missing_dimensions ? "warn" : "good"} />
      </section>
      <section className="section-block">
        <div className="section-heading"><Link2 size={15} /><h2>Links</h2><span>{capture.links.total}</span></div>
        <MetricRow label="Internal / External" value={`${capture.links.internal} / ${capture.links.external}`} />
        <MetricRow label="Nofollow" value={capture.links.nofollow} />
        <MetricRow label="Sponsored / UGC" value={`${capture.links.sponsored} / ${capture.links.ugc}`} />
        <MetricRow label="Empty anchor" value={capture.links.empty_anchor} state={capture.links.empty_anchor ? "warn" : "good"} />
      </section>
    </>
  );
}

function Signals({ capture }: { capture: BrowserCapture }) {
  const timing = capture.performance_observation;
  return (
    <>
      <section className="section-block">
        <div className="section-heading"><MonitorUp size={15} /><h2>Browser observation</h2></div>
        <p className="scope-note">Navigation Timing from this tab. This is not a Lighthouse or field performance score.</p>
        <MetricRow label="DOM content loaded" value={timing.dom_content_loaded_ms === null ? "Unavailable" : `${timing.dom_content_loaded_ms} ms`} />
        <MetricRow label="Load event" value={timing.load_ms === null ? "Unavailable" : `${timing.load_ms} ms`} />
        <MetricRow label="Transferred" value={timing.transfer_size_bytes === null ? "Unavailable" : `${Math.round(timing.transfer_size_bytes / 1024)} KB`} />
        <MetricRow label="Resources observed" value={timing.resource_count} />
      </section>
      <section className="section-block">
        <div className="section-heading"><ExternalLink size={15} /><h2>Social metadata</h2></div>
        <MetricRow label="Open Graph fields" value={Object.keys(capture.social.open_graph).length} />
        <MetricRow label="Twitter fields" value={Object.keys(capture.social.twitter).length} />
        <MetricRow label="Document language" value={capture.document.lang || "Missing"} state={capture.document.lang ? "good" : "warn"} />
        <MetricRow label="Word count" value={capture.document.word_count} />
      </section>
    </>
  );
}

function Workbench() {
  return (
    <section className="connection-card">
      <div className="connection-icon"><Unplug size={22} /></div>
      <div className="eyebrow">OPTIONAL CONNECTION</div>
      <h2>Keep working offline</h2>
      <p>This inspector is complete on its own. Connect the local SEO Workbench only when you want durable project evidence and agent handoff.</p>
      <button className="connect-preview" disabled>Connection arrives in the next implementation layer <ChevronRight size={15} /></button>
    </section>
  );
}
