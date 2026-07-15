"""Compatibility wrapper around the local technology evidence collector."""

from __future__ import annotations

from seo_workbench_tools.technology_probe import collect, collect_from_state, write_report

__all__ = ["collect", "collect_from_state", "write_report"]
