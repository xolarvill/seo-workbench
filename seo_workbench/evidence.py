"""Compatibility wrappers around the existing evidence collectors."""

from __future__ import annotations

from seo_workbench_tools.evidence_bundle import collect, write_bundle
from seo_workbench_tools.workflow_evidence import collect_from_state, page_urls_from_state

__all__ = ["collect", "write_bundle", "collect_from_state", "page_urls_from_state"]
