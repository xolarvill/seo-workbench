from __future__ import annotations

import random


def benjamini_hochberg(tests: list[tuple[str, float]]) -> dict[str, float]:
    ranked = sorted(tests, key=lambda item: (item[1], item[0]))
    result: dict[str, float] = {}
    running = 1.0
    total = len(ranked)
    for rank in range(total, 0, -1):
        key, p_value = ranked[rank - 1]
        running = min(running, p_value * total / rank)
        result[key] = min(running, 1.0)
    return result


def moving_block_differences(
    before: list[float],
    after: list[float],
    *,
    seed: int,
    samples: int = 500,
    block_days: int = 7,
) -> list[float]:
    rng = random.Random(seed)
    return sorted(
        _block_total(after, rng, block_days) - _block_total(before, rng, block_days)
        for _ in range(samples)
    )


def moving_block_did(
    target_before: list[float],
    target_after: list[float],
    control_before: list[float],
    control_after: list[float],
    *,
    control_scale: float,
    seed: int,
    samples: int = 500,
    block_days: int = 7,
) -> list[float]:
    rng = random.Random(seed)
    return sorted(
        (_block_total(target_after, rng, block_days) - _block_total(target_before, rng, block_days))
        - control_scale
        * (_block_total(control_after, rng, block_days) - _block_total(control_before, rng, block_days))
        for _ in range(samples)
    )


def percentile(values: list[float], probability: float) -> float:
    position = (len(values) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def _block_total(values: list[float], rng: random.Random, block_days: int) -> float:
    sampled = []
    while len(sampled) < len(values):
        start = rng.randrange(len(values))
        sampled.extend(values[(start + offset) % len(values)] for offset in range(block_days))
    return sum(sampled[: len(values)])
