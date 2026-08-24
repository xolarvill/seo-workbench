from __future__ import annotations

import hashlib
import itertools
import random
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from statistics import mean
from typing import Any

from seo_workbench.statistics_history import load_daily_history, load_history_coverage
from seo_workbench.statistics_methods import benjamini_hochberg, percentile
from seo_workbench.tech_issues import load_issue_register
from seo_workbench.measurement_regimes import list_regimes


def evaluate_technical_issue_effects(project_dir: Path) -> dict[str, Any]:
    regimes = list_regimes(project_dir).get("regimes", [])
    return build_technical_issue_effects(
        load_issue_register(project_dir),
        load_daily_history(project_dir, "gsc"),
        load_history_coverage(project_dir).get("gsc", []),
        regime_dates={
            str(regime.get("effective_at") or "")
            for regime in regimes
            if regime.get("breaks_comparability") and regime.get("source") in {"gsc", "all"}
        },
    )


def build_technical_issue_effects(
    records: list[dict[str, Any]],
    gsc_rows: list[dict[str, Any]],
    coverage: list[str],
    *,
    regime_dates: set[str] | None = None,
) -> dict[str, Any]:
    indexed: dict[str, dict[str, dict[str, float]]] = defaultdict(dict)
    for row in gsc_rows:
        indexed[str(row.get("url") or "")][str(row.get("date") or "")] = {
            "clicks": float(row.get("clicks") or 0),
            "impressions": float(row.get("impressions") or 0),
        }
    covered = set(coverage)
    observations: dict[str, list[dict[str, Any]]] = defaultdict(list)
    known_rules = {str(record.get("rule_id") or "") for record in records if record.get("rule_id")}
    for record in records:
        rule, url = str(record.get("rule_id") or ""), str(record.get("url") or "")
        fix = _verified_fix_day(record)
        if not rule or not url or fix is None or url not in indexed:
            continue
        fixed, confidence = fix
        before = [(fixed - timedelta(days=offset)).isoformat() for offset in range(14, 0, -1)]
        after = [(fixed + timedelta(days=offset)).isoformat() for offset in range(1, 15)]
        crosses_regime = any(before[0] < regime <= after[-1] for regime in (regime_dates or set()))
        if any(day not in covered for day in before + after) or crosses_regime:
            continue
        previous_impressions = sum(float(indexed[url].get(day, {}).get("impressions", 0)) for day in before)
        if previous_impressions < 100:
            continue
        previous_clicks = sum(float(indexed[url].get(day, {}).get("clicks", 0)) for day in before)
        current_clicks = sum(float(indexed[url].get(day, {}).get("clicks", 0)) for day in after)
        observations[rule].append(
            {
                "url": url,
                "fixed_at": fixed.isoformat(),
                "previous_clicks_per_day": previous_clicks / 14,
                "current_clicks_per_day": current_clicks / 14,
                "clicks_per_day_change": (current_clicks - previous_clicks) / 14,
                "confidence": confidence,
            }
        )
    rules: dict[str, dict[str, Any]] = {}
    tests = []
    for rule in sorted(known_rules):
        selected = observations.get(rule, [])
        if len(selected) < 6:
            rules[rule] = {
                "status": "insufficient_data",
                "verified_fixes": len(selected),
                "provisional_fixes": sum(1 for item in selected if item["confidence"] == "provisional"),
                "reason": "at least six verified or provisional fixes with complete 14-day pre/post evidence are required",
                "causal_claim": False,
            }
            continue
        changes = [float(item["clicks_per_day_change"]) for item in selected]
        estimate = mean(changes)
        seed = int(hashlib.sha256(rule.encode()).hexdigest()[:16], 16)
        rng = random.Random(seed)
        draws = sorted(mean(rng.choice(changes) for _ in changes) for _ in range(1000))
        p_value = _sign_flip_p_value(changes, seed)
        rules[rule] = {
            "status": "tested",
            "verified_fixes": len(selected),
            "provisional_fixes": sum(1 for item in selected if item["confidence"] == "provisional"),
            "design": "verified-fix within-page pre/post association",
            "window_days": 14,
            "clicks_per_day_change": {
                "estimate": round(estimate, 4),
                "ci95": [round(percentile(draws, 0.025), 4), round(percentile(draws, 0.975), 4)],
            },
            "p_value_unadjusted": round(p_value, 6),
            "observations": selected,
            "causal_claim": False,
        }
        tests.append((rule, p_value))
    q_values = benjamini_hochberg(tests)
    pages: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rule, q_value in q_values.items():
        result = rules[rule]
        estimate = float(result["clicks_per_day_change"]["estimate"])
        result["q_value"] = round(q_value, 6)
        result["fdr_significant"] = q_value <= 0.05
        result["classification"] = (
            "positive_association"
            if q_value <= 0.05 and estimate > 0
            else "negative_association"
            if q_value <= 0.05 and estimate < 0
            else "no_clear_association"
        )
        for observation in result["observations"]:
            pages[str(observation["url"])].append(
                {
                    "rule_id": rule,
                    "classification": result["classification"],
                    "q_value": result["q_value"],
                    "causal_claim": False,
                }
            )
    return {
        "schema_version": "technical-statistics-v1",
        "status": "ok" if tests else "insufficient_data",
        "method": "14-day verified/provisional fix pre/post association; sign-flip tests; Benjamini-Hochberg FDR 0.05",
        "tested_rules": len(tests),
        "significant_rules": sum(q_value <= 0.05 for q_value in q_values.values()),
        "rules": rules,
        "pages": dict(pages),
        "causal_claim": False,
        "interpretation": "Association after verified fixes, plus provisional evidence from partial same-fingerprint audits; concurrent page and demand changes remain possible.",
    }


def _verified_fix_day(record: dict[str, Any]) -> tuple[date, str] | None:
    if record.get("status") == "verified" and record.get("verification_status") == "passed":
        confidence = "verified"
    elif record.get("status") == "fixed" and record.get("verification_status") == "provisional":
        confidence = "provisional"
    else:
        return None
    for event in record.get("history") or []:
        if event.get("event") == "status_changed" and event.get("status") == "fixed":
            try:
                fixed_at = datetime.fromisoformat(str(event.get("at") or "").replace("Z", "+00:00")).astimezone(
                    ZoneInfo("America/Los_Angeles")
                ).date()
                return fixed_at, confidence
            except ValueError:
                return None
    return None


def _sign_flip_p_value(changes: list[float], seed: int) -> float:
    observed = abs(mean(changes))
    if len(changes) <= 15:
        outcomes = [
            abs(mean(value * sign for value, sign in zip(changes, signs)))
            for signs in itertools.product((-1, 1), repeat=len(changes))
        ]
    else:
        rng = random.Random(seed)
        outcomes = [abs(mean(value * rng.choice((-1, 1)) for value in changes)) for _ in range(10000)]
    return sum(value >= observed - 1e-12 for value in outcomes) / len(outcomes)
