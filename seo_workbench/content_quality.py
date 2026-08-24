from __future__ import annotations

import html as html_lib
import json
import re
from pathlib import Path
from typing import Any

from seo_workbench import state
from seo_workbench_tools.files import atomic_write_text


AI_WATERMARK_RE = re.compile(r"[​‌‍﻿⁠⁡⁢⁣⁤]")
AI_DASH_RE = re.compile(r"\s+[—–]+\s+")
HTML_TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")
FAQ_HEADER_RE = re.compile(r"<h2[^>]*>\s*(?:Frequently\s+Asked\s+Questions|FAQ|FAQs)\s*</h2>", re.I)
QA_RE = re.compile(r"<h3[^>]*>(.*?)</h3>(.*?)(?=<h[23][^>]*>|$)", re.I | re.S)

AI_CLICHE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bIn today'?s (?:world|fast[- ]paced world|digital age|modern (?:world|era|workplace))\b[,.]?\s*", re.I), ""),
    (re.compile(r"\bLet'?s dive (?:in|into [a-zA-Z ]+?)\b\.?\s*", re.I), ""),
    (re.compile(r"\bIn conclusion,?\s*", re.I), ""),
    (re.compile(r"\bWhen it comes to\b", re.I), "For"),
    (re.compile(r"\bseamlessly\b", re.I), "smoothly"),
    (re.compile(r"\bseamless\b", re.I), "smooth"),
    (re.compile(r"\bleverag(e|es|ed|ing)\b", re.I), r"us\1"),
    (re.compile(r"\brobust\b", re.I), "solid"),
    (re.compile(r"\bcutting[- ]edge\b", re.I), "modern"),
    (re.compile(r"\bstate[- ]of[- ]the[- ]art\b", re.I), "modern"),
    (re.compile(r"\bgame[- ]changer\b", re.I), "shift"),
    (re.compile(r"\bdelve(s|d)? into\b", re.I), r"explore\1"),
    (re.compile(r"\ba testament to\b", re.I), "proof of"),
]

UNIT_ALIASES = {
    "lbs": "lb",
    "lb": "lb",
    "kg": "kg",
    "w": "w",
    "mm": "mm",
    "cm": "cm",
    "m": "m",
    "nm": "nm",
    "v": "v",
    "a": "a",
    "hz": "hz",
    "inch": "in",
    "in": "in",
    '"': "in",
}
UNITS_PATTERN = "|".join(re.escape(unit) for unit in sorted(UNIT_ALIASES, key=len, reverse=True))
NUM_RE = r"\d[\d,]*(?:\.\d+)?"
TOKEN_RE = re.compile(rf"({NUM_RE})\s*({UNITS_PATTERN})\b", re.I)
INCH_QUOTE_RE = re.compile(rf'({NUM_RE})\s*(")')


def run_content_qc(project_dir: Path, item_id: str) -> tuple[dict[str, Any], Path]:
    record = _find_pipeline_record(project_dir, item_id)
    project_name = str((state.load_state(project_dir).get("project") or {}).get("name") or "").strip().lower()
    report = build_qc_report(
        record,
        spec_whitelist=load_spec_whitelist(project_dir),
        brand_terms=(project_name,) if project_name else (),
    )
    output_dir = state.safe_project_path(project_dir, "audits/content-qc")
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{_safe_name(item_id)}.json"
    atomic_write_text(path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report, path


def build_qc_report(
    record: dict[str, Any],
    *,
    spec_whitelist: set[str] | None = None,
    brand_terms: tuple[str, ...] = (),
) -> dict[str, Any]:
    html = record.get("draft_html") or ""
    title = record.get("title") or record.get("cluster_name") or ""
    target_keyword = record.get("target_keyword") or record.get("representative_keyword") or ""
    cleaned, scrub_stats = scrub_ai_signatures(html)
    density = keyword_density(target_keyword, cleaned)
    faq = extract_faq(cleaned)
    specs = spec_whitelist or set()
    spec_warnings = spec_provenance_warnings(cleaned, specs, have_specs=bool(specs), brand_terms=brand_terms)
    warnings = []
    if not html:
        warnings.append({"code": "draft_html.missing", "message": "draft_html is empty"})
    if not title:
        warnings.append({"code": "title.missing", "message": "title is empty"})
    if scrub_stats["watermarks"] or scrub_stats["cliches"]:
        warnings.append({"code": "ai_signature", "message": "AI signature scrubber found removable patterns"})
    density_message = density_warning(target_keyword, cleaned)
    if density_message:
        warnings.append({"code": "keyword_density", "message": density_message})
    for token in spec_warnings:
        warnings.append({"code": "spec_provenance", "message": f"Product spec token needs source check: {token}"})

    return {
        "collection_status": "ok",
        "item_id": record.get("id", ""),
        "title": title,
        "status": record.get("status", ""),
        "word_count": accurate_word_count(cleaned),
        "scrub_stats": scrub_stats,
        "keyword_density": {
            "target_keyword": target_keyword,
            "occurrences": density[0],
            "word_count": density[1],
            "density": density[2],
        },
        "schemas": {"blog_posting": bool(title), "faq_qa_count": len(faq)},
        "warnings": warnings,
    }


def scrub_ai_signatures(html: str) -> tuple[str, dict[str, int]]:
    cleaned, watermarks = AI_WATERMARK_RE.subn("", html or "")
    cleaned, dashes = AI_DASH_RE.subn(", ", cleaned)
    cliches = 0
    for pattern, replacement in AI_CLICHE_PATTERNS:
        cleaned, count = pattern.subn(replacement, cleaned)
        cliches += count
    cleaned = re.sub(r" {2,}", " ", cleaned)
    cleaned = re.sub(r"(?m)^[ \t]*[,.]\s*", "", cleaned)
    return cleaned, {"watermarks": watermarks, "em_dashes": dashes, "cliches": cliches}


def accurate_word_count(html: str) -> int:
    text = WS_RE.sub(" ", HTML_TAG_RE.sub(" ", html or "")).strip()
    return len(re.findall(r"\b[\w'-]+\b", text))


def extract_faq(html: str) -> list[dict[str, str]]:
    match = FAQ_HEADER_RE.search(html or "")
    if not match:
        return []
    section = html[match.end() :]
    next_h2 = re.search(r"<h2[^>]*>", section, re.I)
    if next_h2:
        section = section[: next_h2.start()]
    faqs: list[dict[str, str]] = []
    for qa in QA_RE.finditer(section):
        question = strip_html_text(qa.group(1))
        answer = strip_html_text(qa.group(2))
        if question and answer:
            faqs.append({"question": question, "answer": answer})
    return faqs


def strip_html_text(value: str) -> str:
    return WS_RE.sub(" ", html_lib.unescape(HTML_TAG_RE.sub(" ", value or ""))).strip()


def keyword_density(target_keyword: str, html: str) -> tuple[int, int, float]:
    text = strip_html_text(html).lower()
    word_count = len(re.findall(r"\b[\w'-]+\b", text))
    keyword = (target_keyword or "").strip().lower()
    if not keyword or word_count == 0:
        return 0, word_count, 0.0
    occurrences = len(re.findall(r"\b" + re.escape(keyword) + r"\b", text))
    return occurrences, word_count, occurrences / word_count


def density_warning(target_keyword: str, html: str) -> str | None:
    occurrences, words, density = keyword_density(target_keyword, html)
    keyword = (target_keyword or "").strip()
    if not keyword or words == 0:
        return None
    if density > 0.02:
        return f"keyword density is high: {density * 100:.2f}% ({occurrences}/{words})"
    if len(keyword.split()) <= 2 and density < 0.01:
        return f"keyword density is low: {density * 100:.2f}% ({occurrences}/{words})"
    if len(keyword.split()) >= 3 and occurrences == 0:
        return "long-tail keyword is missing from body text"
    return None


def spec_provenance_warnings(
    html: str,
    whitelist: set[str],
    *,
    have_specs: bool,
    brand_terms: tuple[str, ...] = (),
) -> list[str]:
    text = strip_html_text(html)
    lower = text.lower()
    warnings: list[str] = []
    seen: set[str] = set()
    for token, start, end in extract_spec_tokens(text):
        window = lower[max(0, start - 60) : end + 60]
        if brand_terms and not any(term in window for term in brand_terms):
            continue
        if not brand_terms and not have_specs:
            continue
        if have_specs and token in whitelist:
            continue
        if token not in seen:
            seen.add(token)
            warnings.append(token)
    return warnings


def extract_spec_tokens(text: str) -> list[tuple[str, int, int]]:
    tokens: list[tuple[str, int, int]] = []
    for match in TOKEN_RE.finditer(text or ""):
        tokens.append((normalize_spec_token(match.group(1), match.group(2)), match.start(), match.end()))
    for match in INCH_QUOTE_RE.finditer(text or ""):
        tokens.append((normalize_spec_token(match.group(1), match.group(2)), match.start(), match.end()))
    return tokens


def normalize_spec_token(number: str, unit: str) -> str:
    number = number.replace(",", "")
    if "." in number:
        number = number.rstrip("0").rstrip(".")
    return f"{number}{UNIT_ALIASES.get(unit.lower(), unit.lower())}"


def load_spec_whitelist(project_dir: Path) -> set[str]:
    path = state.safe_project_path(project_dir, "context/product-specs.md")
    if not path.exists():
        return set()
    return {token for token, _, _ in extract_spec_tokens(path.read_text(encoding="utf-8"))}


def _find_pipeline_record(project_dir: Path, item_id: str) -> dict[str, Any]:
    path = state.safe_project_path(project_dir, "content/blog-pipeline.jsonl")
    if not path.exists():
        raise FileNotFoundError(f"{path} not found; import content first")
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("id") == item_id:
            return record
    raise ValueError(f"content pipeline item not found: {item_id}")


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-") or "content-qc"
