from __future__ import annotations


def build_forward_return_labels(prices: list[float], index: int, horizons: dict[str, int]) -> dict[str, float | None]:
    labels: dict[str, float | None] = {}
    if index < 0 or index >= len(prices):
        return {name: None for name in horizons}
    current = float(prices[index])
    if current == 0:
        return {name: None for name in horizons}
    for name, steps in horizons.items():
        future_index = index + int(steps)
        if future_index >= len(prices):
            labels[name] = None
            continue
        future = float(prices[future_index])
        labels[name] = (future - current) / current
    return labels
