"""Compatibility wrapper around Google Search Console evidence collectors."""

from seo_workbench_tools.gsc_probe import (
    authenticate,
    bind_property,
    collect_all,
    collect_inspection,
    collect_performance,
    collect_sitemaps,
    list_properties,
)

__all__ = [
    "authenticate",
    "bind_property",
    "collect_all",
    "collect_inspection",
    "collect_performance",
    "collect_sitemaps",
    "list_properties",
]
