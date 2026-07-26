export type Severity = "critical" | "warning" | "passed";

export interface Finding {
  id: string;
  severity: Severity;
  title: string;
  detail: string;
}

export interface Heading {
  level: number;
  text: string;
}

export interface PageSnapshot {
  requested_url: string;
  final_url: string;
  document: {
    title: string;
    description: string;
    canonical: string;
    robots: string;
    lang: string;
    viewport: string;
    word_count: number;
  };
  headings: Heading[];
  images: {
    total: number;
    missing_alt: number;
    empty_alt: number;
    lazy_loaded: number;
    missing_dimensions: number;
  };
  links: {
    total: number;
    internal: number;
    external: number;
    nofollow: number;
    sponsored: number;
    ugc: number;
    empty_anchor: number;
  };
  structured_data: {
    blocks: number;
    types: string[];
    parse_errors: number;
  };
  hreflang: Array<{ lang: string; href: string }>;
  social: {
    open_graph: Record<string, string>;
    twitter: Record<string, string>;
  };
  performance_observation: {
    source: "browser_navigation_timing";
    dom_content_loaded_ms: number | null;
    load_ms: number | null;
    transfer_size_bytes: number | null;
    decoded_body_size_bytes: number | null;
    resource_count: number;
  };
  source_context: {
    user_agent: string;
    viewport: { width: number; height: number; device_pixel_ratio: number };
  };
}

export type BrowserCapture = Omit<PageSnapshot, "source_context"> & {
  schema_version: "browser-capture-v1";
  capture_id: string;
  captured_at: string;
  collection_status: "complete" | "partial" | "failed";
  source: {
    kind: "chrome_extension";
    extension_version: string;
    user_agent: string;
    viewport: { width: number; height: number; device_pixel_ratio: number };
  };
  findings: Finding[];
  summary: Record<Severity, number>;
  errors: string[];
  warnings: string[];
};
