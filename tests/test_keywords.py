import json
import zipfile
from pathlib import Path

from seo_workbench import state
from seo_workbench.cli import main
from seo_workbench.keywords import (
    autocomplete_records,
    merge_records,
    parse_ads_volume,
    parse_sitemap,
    priority_score,
    read_google_ads_csv,
    read_gsc_search_analytics,
    read_semrush_xlsx,
    HEXCAL_BRAND_PATTERN,
    HEXCAL_COMPETITOR_PATTERN,
    KeywordRecord,
)


def test_priority_score_matches_hexcal_source_priors() -> None:
    semrush = priority_score("semrush_manual", 1000, 20, 2.5, "commercial")
    sitemap = priority_score("sitemap", 0, 0, 0, "")

    assert semrush > sitemap
    assert priority_score("ads", 1000, 0, 2.5, "") > priority_score("autocomplete", 0, 0, 0, "")


def test_google_ads_csv_parser_supports_ranges_and_cpc(tmp_path: Path) -> None:
    csv_path = tmp_path / "ads.csv"
    csv_path.write_text(
        "Metadata\n"
        "Keyword\tAvg. monthly searches\tTop of page bid (high range)\n"
        "standing desk cable tray\t1K - 10K\t$2.50\n"
        "hexcal studio\t100\t$1.00\n",
        encoding="utf-8",
    )

    records = read_google_ads_csv(csv_path, exclusion_patterns=(HEXCAL_BRAND_PATTERN, HEXCAL_COMPETITOR_PATTERN))

    assert len(records) == 1
    assert records[0].keyword == "standing desk cable tray"
    assert records[0].volume_hint == 5500
    assert records[0].cpc_hint == 2.5
    assert parse_ads_volume("1K – 10K") == 5500


def test_generic_keyword_parser_does_not_apply_hexcal_exclusions(tmp_path: Path) -> None:
    csv_path = tmp_path / "ads.csv"
    csv_path.write_text(
        "Keyword\tAvg. monthly searches\nhexcal studio\t100\n",
        encoding="utf-8",
    )

    assert [record.keyword for record in read_google_ads_csv(csv_path)] == ["hexcal studio"]


def test_semrush_xlsx_parser_filters_by_kd_volume_and_brand(tmp_path: Path) -> None:
    xlsx = tmp_path / "semrush.xlsx"
    _write_minimal_xlsx(
        xlsx,
        [
            ["Keyword", "Intent", "Volume", "Keyword Difficulty", "CPC"],
            ["standing desk cable tray", "Commercial", "40", "20", "2.5"],
            ["too hard keyword", "Informational", "1000", "80", "1"],
            ["hexcal studio", "Commercial", "1000", "10", "1"],
        ],
    )

    records = read_semrush_xlsx(xlsx, exclusion_patterns=(HEXCAL_BRAND_PATTERN, HEXCAL_COMPETITOR_PATTERN))

    assert len(records) == 1
    assert records[0].source == "semrush_manual"
    assert records[0].keyword == "standing desk cable tray"
    assert records[0].intent == "commercial"


def test_gsc_search_analytics_parser_filters_and_dedupes_queries(tmp_path: Path) -> None:
    report = tmp_path / "gsc.json"
    report.write_text(
        json.dumps(
            {
                "windows": {
                    "current": {
                        "query": {
                            "rows": [
                                {"keys": ["desk cables"], "impressions": 20, "ctr": 0.2, "position": 8},
                                {"keys": ["cable desk"], "impressions": 10, "ctr": 0.3, "position": 7},
                                {"keys": ["hexcal studio"], "impressions": 100, "ctr": 0.5, "position": 1},
                                {"keys": ["low signal"], "impressions": 9, "ctr": 1.0, "position": 1},
                            ]
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    records = read_gsc_search_analytics(report, exclusion_patterns=(HEXCAL_BRAND_PATTERN, HEXCAL_COMPETITOR_PATTERN))

    assert len(records) == 1
    assert records[0].keyword == "desk cables"
    assert records[0].volume_hint == 30


def test_autocomplete_records_dedupes_seed_and_suggestions() -> None:
    def fetcher(url: str, timeout: float) -> bytes:
        return json.dumps(["desk setup", ["desk setup", "small desk setup", "Small Desk Setup"]]).encode()

    records = autocomplete_records("Desk Setup", fetcher=fetcher)

    assert [record.keyword for record in records] == ["small desk setup"]
    assert records[0].seed_keyword == "desk setup"


def test_parse_sitemap_keeps_blog_shaped_urls() -> None:
    xml = b"""<?xml version="1.0"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url><loc>https://example.com/blogs/articles/minimal-desk-setup-small-apartments</loc></url>
      <url><loc>https://example.com/products/desk</loc></url>
    </urlset>
    """

    records = parse_sitemap(xml, "example.com")

    assert len(records) == 1
    assert records[0].keyword == "minimal desk setup small apartments"
    assert records[0].source == "sitemap"


def test_merge_records_keeps_stronger_source_and_scores() -> None:
    records = merge_records(
        [
            KeywordRecord(keyword="Desk Setup", source="autocomplete"),
            KeywordRecord(keyword="desk setup", source="ads", volume_hint=1000, cpc_hint=1.5),
        ]
    )

    assert len(records) == 1
    assert records[0].source == "ads"
    assert records[0].priority_score > 0


def test_keywords_collect_cli_writes_keyword_pool(tmp_path: Path, capsys) -> None:
    project_dir = tmp_path / "project"
    state.init_state("shopify", "Store", "https://example.com", project_dir=project_dir)
    csv_path = tmp_path / "ads.csv"
    csv_path.write_text(
        "Keyword\tAvg. monthly searches\tTop of page bid (high range)\n"
        "monitor arm setup\t1,300\t$3.00\n",
        encoding="utf-8",
    )

    assert main(["--project-dir", str(project_dir), "keywords", "collect", "--google-ads-csv", str(csv_path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    rows = [json.loads(line) for line in (project_dir / "strategy/keyword-pool.jsonl").read_text().splitlines()]

    assert payload["written"] == 1
    assert rows[0]["keyword"] == "monitor arm setup"
    assert rows[0]["source"] == "ads"


def _write_minimal_xlsx(path: Path, rows: list[list[str]]) -> None:
    strings = []
    string_ids = {}

    def sid(value: str) -> int:
        if value not in string_ids:
            string_ids[value] = len(strings)
            strings.append(value)
        return string_ids[value]

    sheet_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for col_index, value in enumerate(row):
            cell = f"{chr(ord('A') + col_index)}{row_index}"
            cells.append(f'<c r="{cell}" t="s"><v>{sid(value)}</v></c>')
        sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    shared = '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">' + "".join(f"<si><t>{value}</t></si>" for value in strings) + "</sst>"
    sheet = '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>' + "".join(sheet_rows) + "</sheetData></worksheet>"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("xl/sharedStrings.xml", shared)
        archive.writestr("xl/worksheets/sheet1.xml", sheet)
