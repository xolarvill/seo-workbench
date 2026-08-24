from __future__ import annotations

import csv
import json
import math
import re
import urllib.parse
import urllib.request
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable
from xml.etree import ElementTree as ET

from seo_workbench import state
from seo_workbench_tools.files import atomic_write_text


W_VOL = 0.35
W_KD = 0.30
W_CPC = 0.15
W_INTENT = 0.20
VOL_CAP = 5000
CPC_CAP = 5.0

SOURCE_TRUST = {
    "semrush_manual": 1.0,
    "ads": 0.95,
    "gsc": 0.90,
    "autocomplete": 0.65,
    "sitemap": 0.40,
}

INTENT_WEIGHT = {
    "transactional": 1.0,
    "commercial": 0.8,
    "navigational": 0.3,
    "informational": 0.5,
    "": 0.4,
}

KD_PRIOR = {"gsc": 0.55, "autocomplete": 0.50, "sitemap": 0.45, "ads": 0.50}
VOL_PRIOR = {"autocomplete": 0.25, "sitemap": 0.15}
INTENT_PRIOR = {"autocomplete": 0.55, "gsc": 0.40, "sitemap": 0.40, "ads": 0.55}

HEXCAL_BRAND_PATTERN = re.compile(
    r"\b(hexcal|hex\s*cal|hexal|excal|hexacal|hexcel|hexical|hexcall|hex\s*ergo|hexcalstudio)\b",
    re.IGNORECASE,
)
HEXCAL_COMPETITOR_PATTERN = re.compile(
    r"\b(uplift|humanscale|ergotron|desky|progressive\s*desk|grovemade|secretlab|"
    r"deskhaus|flexispot|flexi\s*spot|fezibo|varidesk)\b",
    re.IGNORECASE,
)
NAV_PATTERN = re.compile(
    r"\b(log\s*in|login|sign\s*in|coupon|promo\s*code|discount\s*code|customer\s*service|"
    r"warranty|tracking|return\s*policy|near\s*me|phone\s*number|store\s*hours|reddit)\b",
    re.IGNORECASE,
)


@dataclass
class KeywordRecord:
    keyword: str
    source: str
    seed_keyword: str = ""
    competitor_domain: str = ""
    volume_hint: float = 0.0
    ctr_hint: float = 0.0
    position_hint: float = 0.0
    kd_hint: float = 0.0
    cpc_hint: float = 0.0
    intent: str = ""
    priority_score: float = 0.0

    def normalized(self) -> "KeywordRecord":
        self.keyword = normalize_keyword(self.keyword)
        self.priority_score = priority_score(
            self.source,
            self.volume_hint,
            self.kd_hint,
            self.cpc_hint,
            self.intent,
        )
        return self


def priority_score(source: str, volume: float, kd: float, cpc: float, intent: str) -> float:
    trust = SOURCE_TRUST.get(source, 0.40)
    is_semrush = source == "semrush_manual"

    if source in VOL_PRIOR and volume <= 0:
        vol_factor = VOL_PRIOR[source]
    elif volume > 0:
        vol_factor = min(math.log10(volume + 1) / math.log10(VOL_CAP + 1), 1.0)
    else:
        vol_factor = VOL_PRIOR.get(source, 0.0)

    kd_factor = (100 - kd) / 100 if is_semrush and kd > 0 else KD_PRIOR.get(source, 0.45)
    cpc_factor = min(cpc / CPC_CAP, 1.0) if source in {"semrush_manual", "ads"} and cpc > 0 else 0.0
    if is_semrush and intent:
        intent_factor = INTENT_WEIGHT.get(intent, INTENT_WEIGHT[""])
    else:
        intent_factor = INTENT_PRIOR.get(source, INTENT_WEIGHT[""])

    composite = W_VOL * vol_factor + W_KD * kd_factor + W_CPC * cpc_factor + W_INTENT * intent_factor
    return round(trust * composite * 100, 2)


def collect_keywords(
    project_dir: Path,
    *,
    google_ads_csv: list[Path] | None = None,
    semrush_xlsx: list[Path] | None = None,
    gsc_search_json: list[Path] | None = None,
    autocomplete_seeds: list[str] | None = None,
    competitor_domains: list[str] | None = None,
    top_n: int = 50,
    timeout: float = 15,
    dry_run: bool = False,
) -> dict[str, Any]:
    project_name = str((state.load_state(project_dir).get("project") or {}).get("name") or "").strip().casefold()
    exclusion_patterns = (HEXCAL_BRAND_PATTERN, HEXCAL_COMPETITOR_PATTERN) if project_name == "hexcal" else ()
    records: list[KeywordRecord] = []
    for path in semrush_xlsx or []:
        records.extend(read_semrush_xlsx(path, exclusion_patterns=exclusion_patterns))
    for path in google_ads_csv or []:
        records.extend(read_google_ads_csv(path, exclusion_patterns=exclusion_patterns))
    for path in gsc_search_json or []:
        records.extend(read_gsc_search_analytics(path, exclusion_patterns=exclusion_patterns))
    for seed in autocomplete_seeds or []:
        records.extend(autocomplete_records(seed, timeout=timeout))
    for domain in competitor_domains or []:
        records.extend(sitemap_records(domain, top_n=top_n, timeout=timeout))

    records = [
        record.normalized()
        for record in records
        if record.keyword and not is_noise_keyword(record.keyword, exclusion_patterns=exclusion_patterns)
    ]
    merged = merge_records(records)
    output = state.safe_project_path(project_dir, "strategy/keyword-pool.jsonl")
    if not dry_run:
        write_keyword_pool(output, merged)
    return {
        "collected": len(records),
        "written": len(merged) if not dry_run else 0,
        "path": str(output),
        "dry_run": dry_run,
        "sources": _source_counts(merged),
    }


SEMRUSH_INTENT = {
    "i": "informational",
    "informational": "informational",
    "信息": "informational",
    "c": "commercial",
    "commercial": "commercial",
    "商务": "commercial",
    "t": "transactional",
    "transactional": "transactional",
    "交易": "transactional",
    "n": "navigational",
    "navigational": "navigational",
    "导航": "navigational",
}
SEMRUSH_KD_MAX = 49
SEMRUSH_VOLUME_MIN = 100
SEMRUSH_VOLUME_MIN_COMMERCIAL = 30


def read_semrush_xlsx(
    path: Path,
    *,
    exclusion_patterns: tuple[re.Pattern[str], ...] = (),
) -> list[KeywordRecord]:
    rows = _xlsx_rows(path)
    if not rows:
        return []
    header = [_header(cell) for cell in rows[0]]
    columns = {name: index for index, name in enumerate(header)}
    keyword_col = _first_col(columns, "keyword", "关键词")
    volume_col = _first_col(columns, "volume", "searchvolume", "搜索量")
    kd_col = _first_col(columns, "kd", "kd%", "keyworddifficulty")
    cpc_col = _first_col(columns, "cpc")
    intent_col = _first_col(columns, "intent", "意图")
    if keyword_col is None or volume_col is None:
        raise ValueError(f"Semrush XLSX must include keyword and volume columns: {path}")
    records: list[KeywordRecord] = []
    for row in rows[1:]:
        keyword = normalize_keyword(_cell(row, keyword_col))
        if not keyword or is_noise_keyword(keyword, exclusion_patterns=exclusion_patterns):
            continue
        volume = _float(_cell(row, volume_col))
        kd = _float(_cell(row, kd_col)) if kd_col is not None else 0.0
        cpc = _float(str(_cell(row, cpc_col)).replace("$", "")) if cpc_col is not None else 0.0
        intent = _semrush_intent(_cell(row, intent_col)) if intent_col is not None else ""
        min_volume = SEMRUSH_VOLUME_MIN_COMMERCIAL if intent in {"commercial", "transactional"} else SEMRUSH_VOLUME_MIN
        if kd > SEMRUSH_KD_MAX or volume < min_volume:
            continue
        records.append(
            KeywordRecord(
                keyword=keyword,
                source="semrush_manual",
                volume_hint=volume,
                kd_hint=kd,
                cpc_hint=cpc,
                intent=intent,
            )
        )
    return records


def read_gsc_search_analytics(
    path: Path,
    *,
    exclusion_patterns: tuple[re.Pattern[str], ...] = (),
) -> list[KeywordRecord]:
    report = json.loads(Path(path).read_text(encoding="utf-8"))
    query = ((report.get("windows") or {}).get("current") or {}).get("query") or {}
    rows = query.get("rows") or []
    records = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        keys = row.get("keys") or []
        keyword = normalize_keyword(str(keys[0] if keys else ""))
        impressions = float(row.get("impressions") or 0)
        ctr = float(row.get("ctr") or 0) * 100
        clicks = impressions * ctr / 100
        if not keyword or any(pattern.search(keyword) for pattern in exclusion_patterns) or impressions < 10 or clicks < 2:
            continue
        records.append(
            KeywordRecord(
                keyword=keyword,
                source="gsc",
                volume_hint=impressions,
                ctr_hint=ctr,
                position_hint=float(row.get("position") or 0),
            )
        )
    return _dedupe_gsc(records)


def read_google_ads_csv(
    path: Path,
    *,
    exclusion_patterns: tuple[re.Pattern[str], ...] = (),
) -> list[KeywordRecord]:
    raw = Path(path).read_bytes()
    text = _decode_ads_csv(raw)
    lines = text.splitlines()
    header_index = next((i for i, line in enumerate(lines) if line.split("\t")[0].strip().lower() == "keyword"), None)
    if header_index is None:
        raise ValueError(f"Google Ads CSV has no Keyword header: {path}")

    reader = csv.reader(lines[header_index:], delimiter="\t")
    header = next(reader, [])
    cols = {name.strip().lower(): index for index, name in enumerate(header)}
    keyword_col = cols.get("keyword")
    volume_col = cols.get("avg. monthly searches")
    cpc_col = cols.get("top of page bid (high range)")
    if keyword_col is None or volume_col is None:
        raise ValueError(f"Google Ads CSV must include Keyword and Avg. monthly searches: {path}")

    records: list[KeywordRecord] = []
    for row in reader:
        if not row or len(row) <= max(keyword_col, volume_col):
            continue
        keyword = normalize_keyword(row[keyword_col])
        if not keyword or any(pattern.search(keyword) for pattern in exclusion_patterns):
            continue
        volume = parse_ads_volume(row[volume_col])
        if volume <= 0:
            continue
        cpc = 0.0
        if cpc_col is not None and cpc_col < len(row):
            cpc = parse_money(row[cpc_col])
        records.append(KeywordRecord(keyword=keyword, source="ads", volume_hint=volume, cpc_hint=cpc))
    return records


def _dedupe_gsc(records: list[KeywordRecord]) -> list[KeywordRecord]:
    buckets: dict[str, KeywordRecord] = {}
    for record in records:
        key = _token_set_key(record.keyword)
        if not key:
            continue
        existing = buckets.get(key)
        if existing is None or record.volume_hint > existing.volume_hint:
            if existing is not None:
                record.volume_hint += existing.volume_hint
            buckets[key] = record
        else:
            existing.volume_hint += record.volume_hint
    return list(buckets.values())


def _token_set_key(keyword: str) -> str:
    tokens = []
    for token in re.split(r"[\s\-_/,]+", keyword.lower()):
        token = token.strip()
        if not token or token in {"a", "an", "the", "for", "to", "of", "with", "in", "on"}:
            continue
        if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
            token = token[:-1]
        tokens.append(token)
    return " ".join(sorted(tokens))


def _decode_ads_csv(raw: bytes) -> str:
    for encoding in ("utf-16", "utf-8-sig"):
        try:
            text = raw.decode(encoding)
        except UnicodeError:
            continue
        if any(line.split("\t")[0].strip().lower() == "keyword" for line in text.splitlines()):
            return text
    return raw.decode("utf-8-sig")


def _xlsx_rows(path: Path) -> list[list[str]]:
    with zipfile.ZipFile(path) as archive:
        shared = _shared_strings(archive)
        sheet_name = sorted(name for name in archive.namelist() if name.startswith("xl/worksheets/sheet"))[0]
        root = ET.fromstring(archive.read(sheet_name))
    rows = []
    for row_el in root.iter():
        if _localname(row_el.tag) != "row":
            continue
        values = []
        for cell in row_el:
            if _localname(cell.tag) != "c":
                continue
            values.append(_xlsx_cell(cell, shared))
        rows.append(values)
    return rows


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    strings = []
    for item in root.iter():
        if _localname(item.tag) == "si":
            strings.append("".join(child.text or "" for child in item.iter() if _localname(child.tag) == "t"))
    return strings


def _xlsx_cell(cell: ET.Element, shared: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    value = next((child.text or "" for child in cell if _localname(child.tag) == "v"), "")
    if cell_type == "s":
        try:
            return shared[int(value)]
        except (ValueError, IndexError):
            return ""
    if cell_type == "inlineStr":
        return "".join(child.text or "" for child in cell.iter() if _localname(child.tag) == "t")
    return value


def _header(value: str) -> str:
    return re.sub(r"[^a-z0-9%\u4e00-\u9fff]+", "", value.strip().lower())


def _first_col(columns: dict[str, int], *names: str) -> int | None:
    normalized = [_header(name) for name in names]
    for name in normalized:
        if name in columns:
            return columns[name]
    return None


def _cell(row: list[str], index: int | None) -> str:
    if index is None or index >= len(row):
        return ""
    return str(row[index] or "")


def _float(value: str) -> float:
    try:
        return float(str(value or "").replace(",", "").strip())
    except ValueError:
        return 0.0


def _semrush_intent(value: str) -> str:
    text = str(value or "").strip().lower().split(",")[0].strip()
    return SEMRUSH_INTENT.get(text, "")


def autocomplete_records(seed: str, *, timeout: float = 15, fetcher: Callable[[str, float], bytes] | None = None) -> list[KeywordRecord]:
    seed_norm = normalize_keyword(seed)
    if not seed_norm:
        return []
    query = urllib.parse.urlencode({"client": "firefox", "q": seed_norm, "hl": "en", "gl": "us"})
    url = f"https://suggestqueries.google.com/complete/search?{query}"
    payload = fetcher(url, timeout) if fetcher else _fetch(url, timeout)
    data = json.loads(payload.decode("utf-8"))
    suggestions = data[1] if isinstance(data, list) and len(data) > 1 and isinstance(data[1], list) else []
    seen: set[str] = set()
    records: list[KeywordRecord] = []
    for suggestion in suggestions:
        keyword = normalize_keyword(str(suggestion))
        if not keyword or keyword == seed_norm or keyword in seen:
            continue
        seen.add(keyword)
        records.append(KeywordRecord(keyword=keyword, source="autocomplete", seed_keyword=seed_norm))
    return records


def sitemap_records(
    domain: str,
    *,
    top_n: int = 50,
    timeout: float = 15,
    fetcher: Callable[[str, float], bytes] | None = None,
) -> list[KeywordRecord]:
    domain = domain.strip().removeprefix("https://").removeprefix("http://").rstrip("/")
    records: list[KeywordRecord] = []
    for path in ("/sitemap.xml", "/sitemap_index.xml", "/sitemap_blogs_1.xml"):
        records.extend(parse_sitemap(fetcher(f"https://{domain}{path}", timeout) if fetcher else _fetch(f"https://{domain}{path}", timeout), domain))
        if records:
            break
    return records[:top_n]


def parse_sitemap(xml_bytes: bytes, domain: str = "") -> list[KeywordRecord]:
    root = ET.fromstring(xml_bytes)
    records: list[KeywordRecord] = []
    if _localname(root.tag) == "sitemapindex":
        return records
    if _localname(root.tag) != "urlset":
        return records
    for url_el in root.iter():
        if _localname(url_el.tag) != "url":
            continue
        loc = ""
        for child in url_el:
            if _localname(child.tag) == "loc" and child.text:
                loc = child.text.strip()
                break
        if not loc or not is_blog_url(loc):
            continue
        title = title_from_slug(slug_from_url(loc))
        keyword = normalize_keyword(title)
        if keyword:
            records.append(KeywordRecord(keyword=keyword, source="sitemap", competitor_domain=domain, volume_hint=1.0))
    return records


def merge_records(records: list[KeywordRecord]) -> list[KeywordRecord]:
    priority = {"semrush_manual": 0, "ads": 1, "gsc": 2, "sitemap": 3, "autocomplete": 4}
    by_keyword: dict[str, KeywordRecord] = {}
    extra_volume: dict[str, float] = {}
    for record in records:
        keyword = normalize_keyword(record.keyword)
        if not keyword:
            continue
        record.keyword = keyword
        existing = by_keyword.get(keyword)
        if existing is None:
            by_keyword[keyword] = record
            extra_volume[keyword] = 0.0
            continue
        if priority.get(record.source, 9) < priority.get(existing.source, 9):
            by_keyword[keyword] = record
        extra_volume[keyword] = extra_volume.get(keyword, 0.0) + record.volume_hint
    for keyword, record in by_keyword.items():
        record.volume_hint += extra_volume.get(keyword, 0.0) * 0.1
        record.priority_score = priority_score(record.source, record.volume_hint, record.kd_hint, record.cpc_hint, record.intent)
    return sorted(by_keyword.values(), key=lambda item: (-item.priority_score, item.keyword))


def write_keyword_pool(path: Path, records: list[KeywordRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, "".join(json.dumps(asdict(record), ensure_ascii=False) + "\n" for record in records))


def parse_ads_volume(raw: str) -> float:
    text = (raw or "").strip().replace(",", "")
    if not text:
        return 0.0

    def one(token: str) -> float:
        token = token.strip().upper()
        multiplier = 1.0
        if token.endswith("K"):
            multiplier, token = 1_000.0, token[:-1]
        elif token.endswith("M"):
            multiplier, token = 1_000_000.0, token[:-1]
        try:
            return float(token) * multiplier
        except ValueError:
            return 0.0

    for dash in ("–", "—", " - ", "-"):
        if dash in text:
            parts = [part for part in text.split(dash) if part.strip()]
            if len(parts) == 2:
                return (one(parts[0]) + one(parts[1])) / 2
    return one(text)


def parse_money(raw: str) -> float:
    try:
        return float((raw or "").replace("$", "").replace(",", "").strip() or 0)
    except ValueError:
        return 0.0


def normalize_keyword(keyword: str) -> str:
    return re.sub(r"\s+", " ", (keyword or "").strip().lower())


def is_noise_keyword(keyword: str, *, exclusion_patterns: tuple[re.Pattern[str], ...] = ()) -> bool:
    return bool(NAV_PATTERN.search(keyword) or any(pattern.search(keyword) for pattern in exclusion_patterns))


def is_blog_url(url: str) -> bool:
    if re.search(r"/(products?|shop|collections?|cart|checkout|account|search|policies|about|contact)/?", url, re.I):
        return False
    slug = slug_from_url(url)
    return bool(slug and "." not in slug and slug.count("-") >= 3)


def slug_from_url(url: str) -> str:
    return urllib.parse.urlparse(url).path.rstrip("/").split("/")[-1]


def title_from_slug(slug: str) -> str:
    title = slug.replace("-", " ").replace("_", " ")
    title = re.sub(r"\s+\d{4,}$", "", title)
    return title.strip().title()


def _fetch(url: str, timeout: float) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 SEO Workbench"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def _localname(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def _source_counts(records: list[KeywordRecord]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        counts[record.source] = counts.get(record.source, 0) + 1
    return counts
