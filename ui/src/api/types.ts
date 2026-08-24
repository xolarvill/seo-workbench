export type ProjectSummary = {
  id: string;
  path: string;
  name: string;
  url: string;
  type: string;
  phase: string;
  selectable: boolean;
  valid_state: boolean;
  error?: string;
};

export type Pagination = { offset: number; limit: number; total: number };
export type ViewColumn = { id: string; label: string; default: boolean };

export type EvidenceItem = {
  id: "raw" | "browser" | "technology" | "performance" | "crux" | "gsc" | "ga4" | "business" | "backlinks" | "diff";
  label: string;
  status: string;
};

export type GoogleCredentialProfile = {
  profile: string;
  credential_type: "oauth" | "service_account" | "unknown";
  status: "ready" | "reauth_required" | "incomplete";
  principal?: string | null;
  updated_at: string | null;
};

export type GooglePropertyBinding = {
  profile?: string;
  property?: string;
  permission_level?: string;
  bound_at?: string | null;
  status?: "invalid";
};

export type GoogleIntegration = {
  access: "local_only";
  crux: {
    status: string;
    configured: boolean;
    source: "environment" | "private_file" | "missing";
    removable: boolean;
  };
  gsc: {
    status: string;
    profiles: GoogleCredentialProfile[];
    binding: GooglePropertyBinding | null;
  };
  ga4: {
    status: string;
    configured: boolean;
    profiles: Ga4CredentialProfile[];
    binding: Ga4PropertyBinding | null;
    removable: boolean;
  };
  security: {
    secrets_returned: false;
    storage_mode: string;
    scope: string;
  };
};

export type Ga4CredentialProfile = {
  profile: string;
  credential_type: "oauth" | "unknown";
  status: "ready" | "reauth_required" | "incomplete";
  updated_at: string | null;
};

export type Ga4PropertyBinding = {
  profile?: string;
  property?: string;
  display_name?: string;
  bound_at?: string | null;
  status?: "invalid";
};

export type Ga4Property = {
  property_id: string;
  display_name: string;
  account_id: string;
  account_name: string;
};

export type GscProperty = {
  site_url: string;
  permission_level: string;
};

export type ShopifyIntegration = {
  access: "local_only";
  applicable: boolean;
  status: string;
  configured: boolean;
  source: "private_file" | "missing";
  shop_domain: string | null;
  shop_name: string | null;
  api_version: string;
  scopes: string[];
  write_scope_count: number;
  verified_at: string | null;
  removable: boolean;
  secret_visibility: "write_only";
  crawler_access: {
    configured: boolean;
    status: string;
    domain_host: string | null;
    expires_at: string | null;
    signature_agent: string | null;
    removable: boolean;
    secret_visibility: "write_only";
  };
};

export type DataForSeoIntegration = {
  access: "local_only";
  status: string;
  configured: boolean;
  source: "private_file" | "missing";
  verified_at: string | null;
  removable: boolean;
  secret_visibility: "write_only";
  transport: "rest_v3";
  billing: "metered";
};

export type FileSummary = {
  path: string;
  name: string;
  size: number;
  modified_at: string;
};

export type WeeklyReportSummary = {
  path: string;
  year: number;
  week: number;
  name: string;
  start: string;
  end: string;
  modified_at: string;
  size: number;
  checked: number;
  total: number;
  carry_over: number;
  inherited_from: number[];
  follow_ups: Array<{ date: string; text: string }>;
};

export type SubReportSummary = {
  path: string;
  date: string;
  category: string;
  topic: string;
  modified_at: string;
  size: number;
};

export type ReportFollowUp = {
  date: string;
  text: string;
  year: number;
  week: number;
  path: string;
  state: "overdue" | "upcoming" | "future" | "unknown";
};

export type CarriedOverTrack = {
  task: string;
  entries: Array<{ year: number; week: number; path: string }>;
  spans: number;
};

export type ReportProgress = {
  follow_ups: ReportFollowUp[];
  overdue: number;
  upcoming: number;
  carried_over_tracks: CarriedOverTrack[];
};

export type ReportArchiveParams = { q?: string; category?: string; year?: number; month?: number };

export type ReportArchive = {
  reports_dir: string;
  weekly: WeeklyReportSummary[];
  sub_reports: SubReportSummary[];
  categories: Record<string, SubReportSummary[]>;
  latest_week: { year: number; week: number } | null;
  filters: { query: string; category: string; year: number | null; month: number | null };
  progress: ReportProgress;
};

export type PresentationCheck = {
  code: string;
  label: string;
  passed: boolean;
  required: boolean;
  detail: string;
};

export type PresentationStatus = {
  ok?: boolean;
  schema_version: string;
  status: "ready" | "ready_with_warnings" | "blocked";
  ready: boolean;
  report_date: string;
  target_week: { year: number; week: number };
  max_statistics_age_hours: number;
  statistics: {
    status: string;
    completed_at?: string;
    age_hours?: number | null;
    common_finalized_end_date?: string | null;
  };
  checks: PresentationCheck[];
  warnings: string[];
  artifact: {
    path: string;
    manifest_path?: string;
    size: number;
    generated_at?: string;
    week?: { year: number; week: number } | null;
  } | null;
};

export type ContentQueueItem = {
  id: string;
  status: string;
  title?: string;
  slug?: string;
  live_url?: string;
  scheduled_at?: string;
  review_thread_id?: string;
  word_count?: number;
  updated_at?: string;
  note?: string;
  warnings?: Array<string | { code?: string; message?: string }>;
  target_keyword?: string;
  [key: string]: unknown;
};

export type ContentOpsAction = {
  id: string;
  cadence: string;
  due: boolean;
  count: number;
  command: string;
  items: ContentQueueItem[];
};

export type ClickChangeDecomposition = {
  method?: string;
  previous_observed_clicks?: number;
  current_observed_clicks?: number;
  observed_click_change?: number;
  exposure_effect?: number;
  ctr_effect?: number;
  reconciled?: boolean;
  top_drivers?: Array<{ query?: string; url?: string; click_change?: number; exposure_effect?: number; ctr_effect?: number }>;
};

export type QueryPortfolioWindow = {
  observed_query_count?: number;
  effective_queries?: number;
  hhi?: number;
  top_1_impression_share?: number;
  top_5_impression_share?: number;
  top_10_impression_share?: number;
};

export type QueryPortfolioStatistics = {
  basis?: string;
  previous?: QueryPortfolioWindow;
  current?: QueryPortfolioWindow;
  new_queries?: number;
  stable_queries?: number;
  lost_queries?: number;
  new_query_impression_share?: number;
  retained_query_impression_share?: number;
  lost_query_impression_share?: number;
};

export type RankingOpportunityStatistics = {
  basis?: string;
  current_impressions?: Record<string, number>;
  current_impression_share?: Record<string, number>;
  positions_4_20_impressions?: number;
  transitions?: Record<string, { cell_count?: number; current_impressions?: number }>;
};

export type CtrBenchmarkStatistics = {
  basis?: string;
  global_ctr?: number;
  prior_strength_impressions?: number;
  bands?: Record<string, unknown>;
  recoverable_clicks?: number;
  recoverable_clicks_unadjusted?: number;
  page_classifications?: Record<string, string>;
  multiple_testing?: Record<string, unknown>;
  actual_clicks?: number;
  actual_impressions?: number;
  expected_clicks?: number;
  click_residual?: number;
  standardized_residual?: number;
  p_value_unadjusted?: number;
  q_value?: number;
  classification?: string;
};

export type SearchChangeConfidenceStatistics = {
  status?: string;
  evidence_grade?: string;
  covered_days?: { previous?: number; current?: number };
  method?: string;
  click_change?: { observed?: number; ci95?: number[]; probability_increase?: number; direction?: string };
  ctr?: { previous?: { estimate?: number; ci95?: number[] }; current?: { estimate?: number; ci95?: number[] } };
  caveat?: string;
};

export type SearchTrendStatistics = {
  status?: string;
  method?: string;
  weeks?: number;
  weekly_clicks?: number[];
  click_slope_per_week?: number;
  normalized_slope?: number;
  direction?: string;
  latest_expected_clicks?: number;
  latest_anomaly_score?: number;
  latest_anomaly?: boolean;
};

export type CommercialValueStatistics = {
  observed_pages?: number;
  currency?: string;
  total_revenue?: number;
  revenue_hhi?: number;
  value_tier_cutoff?: number;
  opportunity_tier_cutoff?: number;
  attribution?: string;
  quadrant?: string;
  revenue_share?: number;
};

export type TechnicalIssueEffect = { rule_id?: string; classification?: string; [key: string]: unknown };
export type TechnicalIssueEffects = {
  schema_version?: string;
  status?: string;
  method?: string;
  tested_rules?: number;
  significant_rules?: number;
  rules?: string[];
  causal_claim?: boolean;
  interpretation?: string;
};

export type PortfolioStatistics = {
  click_change_decomposition?: ClickChangeDecomposition;
  query_portfolio?: QueryPortfolioStatistics;
  ranking_opportunity?: RankingOpportunityStatistics;
  ctr_benchmark?: CtrBenchmarkStatistics;
  search_change_confidence?: SearchChangeConfidenceStatistics;
  search_trend?: SearchTrendStatistics;
  commercial_value?: CommercialValueStatistics;
  technical_issue_effects?: TechnicalIssueEffects | TechnicalIssueEffect[];
  cross_source_consistency?: { status?: string; method?: string; [key: string]: unknown };
  organic_engagement?: { status?: string; previous?: Record<string, unknown>; current?: Record<string, unknown>; [key: string]: unknown };
};

export type StatisticsCoverageSource = {
  count: number;
  first?: string | null;
  last?: string | null;
};

export type StatisticsRegime = {
  id?: string;
  source?: string;
  effective_at?: string;
  description?: string;
  [key: string]: unknown;
};

export type StatisticsResponse = {
  ok: boolean;
  portfolio: {
    collection_status: string;
    schema_version?: string | null;
    generated_at?: string | null;
    count: number;
    comparability?: Record<string, unknown>;
    source_status?: Record<string, unknown>;
    statistics?: PortfolioStatistics;
  };
  coverage: {
    status: string;
    sources: Record<string, StatisticsCoverageSource>;
  };
  regimes: {
    schema_version?: string;
    collection_status?: string;
    count: number;
    error?: string;
    regimes: StatisticsRegime[];
  };
  business: {
    status: string;
    currency?: string;
    attribution?: Record<string, string>;
    windows: Record<string, Record<string, unknown>>;
  };
};

export type ContentQueueSummary = {
  items: ContentQueueItem[];
  counts: Record<string, number>;
  due_for_indexing: {
    count: number;
    urls?: string[];
    items?: ContentQueueItem[];
  };
  ops: {
    schema_version: string;
    generated_at: string;
    actions: ContentOpsAction[];
  };
  portfolio: {
    collection_status: string;
    count: number;
    counts: Record<string, number>;
    statistics?: PortfolioStatistics;
    items: Array<{ id: string; title: string; url: string; decision: string; recommendation: string }>;
  };
};

export type ContentJobAction = {
  action: string;
  item_id?: string | null;
  confirm?: boolean;
  role?: string;
  profile?: string;
  blog_id?: string;
  period?: "daily" | "weekly";
  report_path?: string;
  title?: string;
  limit?: number;
  allow_warnings?: boolean;
  no_writeback?: boolean;
  project_relative_path?: string;
};

export type WorkflowStep = {
  id: string;
  label: string;
  status: string;
  skip_reason?: string;
};

export type PhaseState = {
  status: string;
  steps: WorkflowStep[];
};

export type NextContract = {
  phase: string;
  step: string;
  label: string;
  skill: string;
  context: string[];
  output: string;
};

export type Workspace = {
  project_id: string;
  project: {
    name: string;
    url: string;
    type: string;
    description?: string;
  };
  phase: string;
  step: WorkflowStep | null;
  next: NextContract | null;
  phase_order: string[];
  phases: Record<string, PhaseState>;
  evidence: {
    items: EvidenceItem[];
    performance: {
      score: number | null;
      high_variance: boolean | null;
      metrics: { lcp: number | null; tbt: number | null; cls: number | null };
    };
    technology: {
      summary?: string;
      layers?: Record<string, string[]>;
      seo_impacts?: Array<{ area: string; risk: string; conclusion: string }>;
    };
    channels: Array<{
      channel: string;
      sessions: number;
      users: number;
      engaged: number;
      key_events: number;
    }>;
    business: {
      status: string;
      currency?: string;
      windows: Record<
        string,
        { start_date: string; end_date: string; urls: number; organic_sessions: number; engaged_sessions: number; key_events: number; revenue: number; orders: number }
      >;
    };
    diff: { changes?: number; regressions?: number; improvements?: number };
  };
  changes: {
    count: number;
    due: number;
    counts: Record<string, number>;
    items: Array<{
      id: string;
      status: string;
      change_type: string;
      changed_at: string;
      review_date: string;
      hypothesis: string;
      urls: string[];
      classification?: "winning" | "no_change" | "regressing" | "insufficient_data" | null;
    }>;
  };
  content: ContentQueueSummary;
  keywords?: KeywordSummary;
  recent_files: FileSummary[];
};

export type MarkdownFile = {
  path: string;
  content: string;
  revision: string;
  modified_at: string;
};

export type TutorialSummary = {
  slug: string;
  title: string;
  description: string;
  category: string;
  source: string;
};

export type TutorialDocument = TutorialSummary & {
  content: string;
  revision: string;
  modified_at: string;
};

export type WorkbenchEvent = {
  type: string;
  project_id?: string;
  path?: string;
  revision?: string;
  job?: Job;
  at: string;
};

export type Job = {
  id: string;
  project_id: string;
  action: string;
  status: "queued" | "running" | "succeeded" | "failed" | "cancelled";
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  exit_code: number | null;
  output: string;
};

export type TechAuditSchedule = {
  enabled: boolean;
  every_minutes?: number;
  notify_role?: string;
  profile?: string;
  updated_at?: string;
  last_run_at?: string;
  next_run_at?: string;
};

export type TechAuditPage = {
  page_id: string;
  url: string;
  final_url: string;
  status_code: number | null;
  indexability: { status?: string; indexable?: boolean | null };
  title: string;
  meta_description: string;
  meta_keywords: string;
  h1: string[];
  h2: string[];
  inlink_count: number;
  crawl_depth: number;
  response_time_ms: number | null;
  response_size: number;
  issue_ids: string[];
  priority: number;
  last_recrawl_at: string | null;
  last_recrawl_status: number | null;
};

export type TechAuditRun = {
  run_id?: string;
  kind?: string;
  status?: string;
  phase?: string;
  started_at?: string;
  finished_at?: string | null;
  elapsed_seconds?: number;
  processed_urls?: number;
  discovered_urls?: number;
  max_urls?: number;
  sitemap_count?: number;
  sitemap_entries?: number;
  error_count?: number;
  queued_remaining?: number;
};

export type TechAuditHistoryRecord = {
  run_id: string;
  kind: string;
  status: string;
  collection_status: string;
  started_at?: string;
  finished_at?: string | null;
  generated_at?: string;
  summary?: Record<string, number | string | boolean>;
  continuation_of?: string | null;
  active: boolean;
  snapshot_available: boolean;
};

export type TechAuditData = {
  status: "ready" | "no_data";
  snapshot: {
    generated_at?: string;
    run_id?: string;
    collection_status?: string;
    summary?: Record<string, number | string | boolean>;
  };
  history: TechAuditHistoryRecord[];
  run: TechAuditRun | null;
  summary: { pages: number; issues: number; four_oh_four: number; successful_pages: number; crawled_pages?: number; discovered_unique?: number; queued_remaining?: number; continuation_available?: boolean; queue_recovered?: boolean; crawl_batch?: number };
  schedule: TechAuditSchedule;
  last_recrawl: {
    generated_at?: string;
    run_id?: string;
    collection_status?: string;
    target_urls?: string[];
    summary?: Record<string, number | string | boolean>;
  } | null;
  pages: TechAuditPage[];
  pagination: { offset: number; limit: number; total: number };
};

export type TechAuditDataset = "pages" | "links" | "issues";

export type TechAuditViewColumn = ViewColumn;

export type TechAuditViewRow = {
  row_key: string;
  url?: string;
  [key: string]: unknown;
};

export type TechAuditViewResponse = {
  ok: boolean;
  dataset: TechAuditDataset;
  snapshot: TechAuditData["snapshot"];
  columns: TechAuditViewColumn[];
  rows: TechAuditViewRow[];
  pagination: Pagination;
};

export type TechAuditDetailResponse = {
  ok: boolean;
  dataset: TechAuditDataset;
  row: TechAuditViewRow;
  issues: Array<Record<string, unknown>>;
  recrawl: Record<string, unknown> | null;
  diff: { comparable: boolean; changes: Array<Record<string, unknown>>; warnings: string[] };
};

export type PageDataset = "actions" | "pages" | "query_conflicts";

export type PageViewColumn = ViewColumn;

export type PageViewRow = {
  row_key: string;
  url?: string;
  title?: string;
  statistics?: PortfolioStatistics;
  [key: string]: unknown;
};

export type PageSourceStatus = {
  status: string;
  generated_at?: string | null;
  schema_version?: string | null;
  age_days?: number | null;
  changed_since_refresh?: boolean;
  needs_refresh?: boolean;
  refresh_reasons?: string[];
};

export type PageViewResponse = {
  ok: boolean;
  dataset: PageDataset;
  columns: PageViewColumn[];
  rows: PageViewRow[];
  pagination: Pagination;
  summary: { groups: Record<string, number>; pages: number; query_conflicts: number; statistics?: PortfolioStatistics };
  sources: Record<string, PageSourceStatus>;
};

export type PageDetailResponse = {
  ok: boolean;
  dataset: PageDataset;
  row: PageViewRow;
  page: PageViewRow | null;
  source_record?: Record<string, unknown> | null;
  sources: Record<string, PageSourceStatus>;
  internal_link_candidates?: {
    status: string;
    reason?: string;
    rows: Array<{
      source_url: string;
      target_url: string;
      anchor_candidates: string[];
      already_linked: false;
      cluster_ref: string;
      reason: string;
    }>;
  };
};

export type BacklinkViewColumn = ViewColumn;

export type BacklinkViewRow = {
  id: string;
  source_url: string;
  source_domain: string;
  target_url: string;
  anchor: string;
  follow: boolean | null;
  provider_status: "active" | "lost";
  target_status_code: number | null;
  target_reclaim_candidate: boolean;
  first_seen?: string;
  last_seen?: string;
};

export type BacklinkViewResponse = {
  ok: boolean;
  collection_status: string;
  generated_at?: string | null;
  captured_at?: string | null;
  source?: { name?: string; id?: string; input_path?: string } | null;
  complete_snapshot: boolean;
  summary: Record<string, unknown>;
  comparison: Record<string, unknown>;
  top_anchors: Array<{ anchor: string; count: number }>;
  claims: Record<string, unknown>;
  columns: BacklinkViewColumn[];
  rows: BacklinkViewRow[];
  pagination: Pagination;
};

export type KeywordDataset = "keywords" | "topics" | "research";
export type KeywordDecision = "unreviewed" | "prioritize" | "hold" | "drop";

export type KeywordGscMetrics = {
  query?: string;
  raw_queries?: string[];
  clicks: number;
  impressions: number;
  ctr: number;
  position: number;
};

export type KeywordQueryEvidence = KeywordGscMetrics & {
  query: string;
  owner_urls: string[];
};

export type KeywordMarketEvidence = {
  provider: "dataforseo";
  location_code: number;
  language_code: string;
  collected_at: string;
  metrics_updated_at?: string | null;
  search_volume?: number | null;
  cpc?: number | null;
  competition?: number | null;
  competition_level?: string | null;
  intent?: string | null;
  monthly_searches?: Array<{ year: number; month: number; search_volume: number }>;
  search_volume_trend?: { monthly?: number | null; quarterly?: number | null; yearly?: number | null };
  serp?: {
    collected_at?: string;
    se_results_count?: number | null;
    item_types?: string[];
    results?: Array<{ rank?: number | null; title?: string | null; url?: string | null; domain?: string | null; description?: string | null }>;
  };
  cost_usd?: number;
};

export type KeywordRow = {
  row_key: string;
  keyword?: string;
  managed?: boolean;
  source?: string;
  intent?: string;
  priority_score?: number;
  volume_hint?: number;
  cpc_hint?: number;
  kd_hint?: number;
  market?: KeywordMarketEvidence | null;
  decision?: KeywordDecision;
  stage?: string;
  mapping?: string;
  cluster_ref?: string;
  target_url?: string;
  target_content_id?: string;
  note?: string;
  updated_at?: string | null;
  research_path?: string | null;
  research_updated_at?: string | null;
  gsc?: KeywordGscMetrics | null;
  cluster_gsc?: KeywordGscMetrics | null;
  observed_queries?: KeywordQueryEvidence[];
  content?: { id?: string; title?: string; status?: string; live_url?: string } | null;
  owner_urls?: string[];
  mapping_conflict?: boolean;
  cluster_mapping_conflict?: boolean;
  keyword_count?: number;
  keywords?: string[];
  representative_keyword?: string;
  query_count?: number;
  target_urls?: string[];
  target_content_ids?: string[];
  unassigned?: boolean;
  missing_content?: boolean;
  target_conflict?: boolean;
  content_conflict?: boolean;
  ownership_conflict?: boolean;
  impressions?: number;
};

export type KeywordSummary = {
  total: number;
  queue: number;
  queue_stages: Record<string, number>;
  unmanaged: number;
  unmapped: number;
  decisions: Record<string, number>;
  stages: Record<string, number>;
};

export type KeywordViewResponse = {
  ok: boolean;
  dataset: KeywordDataset;
  scope?: "" | "queue" | "map";
  rows: KeywordRow[];
  pagination: Pagination;
  summary: KeywordSummary;
  facets: Record<string, string[]>;
  sources: Record<string, { path: string; count: number; collection_status?: string; generated_at?: string | null }>;
  options: {
    clusters: Array<{ id: string; label: string }>;
    content_items: Array<{ id: string; label: string; status: string }>;
  };
  revision: string;
};

export type KeywordPatch = Partial<{
  decision: KeywordDecision;
  cluster_ref: string;
  target_url: string;
  target_content_id: string;
  note: string;
}>;

export type KeywordHandoff = {
  ok: boolean;
  keyword: string;
  existing_path: string | null;
  skill: string;
  context?: string[];
  output_path?: string;
  prompt?: string;
};

export type SeoChangeCreate = {
  urls: string[];
  change_type: "content" | "internal_links" | "metadata" | "performance" | "redirect" | "schema" | "technical" | "other";
  hypothesis: string;
  metrics: string[];
  changed_at?: string | null;
  review_date?: string | null;
  review_after_days?: number;
  status?: "planned" | "shipped";
  note?: string;
};

export type SeoChangeRecord = {
  schema_version?: string;
  id: string;
  created_at?: string;
  changed_at: string;
  review_date: string;
  status: "planned" | "shipped" | "reviewed" | "cancelled";
  change_type: SeoChangeCreate["change_type"];
  urls: string[];
  hypothesis: string;
  expected_metrics: string[];
  note?: string;
  updates?: Array<{ updated_at?: string; previous_status?: string; status?: string; note?: string }>;
};

export type SeoChangesResponse = {
  schema_version: string;
  collection_status: string;
  count: number;
  changes: SeoChangeRecord[];
};
