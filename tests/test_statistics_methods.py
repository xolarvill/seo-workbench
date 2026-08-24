from seo_workbench.statistics_methods import benjamini_hochberg, moving_block_differences


def test_benjamini_hochberg_controls_all_tested_pages() -> None:
    adjusted = benjamini_hochberg([("a", 0.01), ("b", 0.04), ("c", 0.2)])

    assert adjusted == {"c": 0.20000000000000004, "b": 0.06, "a": 0.03}


def test_moving_block_bootstrap_is_deterministic() -> None:
    first = moving_block_differences([1] * 28, [2] * 28, seed=7, samples=10)
    second = moving_block_differences([1] * 28, [2] * 28, seed=7, samples=10)

    assert first == second == [28] * 10
