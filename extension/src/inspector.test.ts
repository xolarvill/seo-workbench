import { describe, expect, it } from "vitest";

import { evaluate } from "./inspector";
import type { PageSnapshot } from "./types";


const snapshot = (overrides: Partial<PageSnapshot["document"]> = {}): PageSnapshot => ({
  requested_url: "https://example.com/",
  final_url: "https://example.com/",
  document: { title: "Example", description: "Useful summary", canonical: "https://example.com/", robots: "", lang: "en", viewport: "width=device-width", word_count: 10, ...overrides },
  headings: [{ level: 1, text: "Example" }],
  images: { total: 1, missing_alt: 0, empty_alt: 0, lazy_loaded: 0, missing_dimensions: 0 },
  links: { total: 0, internal: 0, external: 0, nofollow: 0, sponsored: 0, ugc: 0, empty_anchor: 0 },
  structured_data: { blocks: 0, types: [], parse_errors: 0 },
  hreflang: [],
  social: { open_graph: {}, twitter: {} },
  performance_observation: { source: "browser_navigation_timing", dom_content_loaded_ms: null, load_ms: null, transfer_size_bytes: null, decoded_body_size_bytes: null, resource_count: 0 },
  source_context: { user_agent: "test", viewport: { width: 1280, height: 720, device_pixel_ratio: 1 } },
});

describe("evaluate", () => {
  it("separates missing and overlong metadata findings", () => {
    expect(evaluate(snapshot({ title: "", description: "x".repeat(161) })).map(({ id, severity }) => [id, severity])).toEqual([
      ["title", "critical"],
      ["description", "warning"],
      ["canonical", "passed"],
      ["h1", "passed"],
      ["image-alt", "passed"],
      ["jsonld", "passed"],
    ]);
  });
});
