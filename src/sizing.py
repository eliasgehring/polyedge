from legacy_models import Signal


def compute_trade_size(
    signal: Signal,
    max_position_size: float,
    edge_size_multiplier: float,
) -> float:
    if signal.action == "HOLD":
        return 0.0

    raw_size = abs(signal.edge) * edge_size_multiplier

    if raw_size <= 0:
        return 0.0

    return min(raw_size, max_position_size)