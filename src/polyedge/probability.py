from .domain import MarketSnapshot, RowType, Signal, Side


def midpoint(bid: float, ask: float) -> float:
    return (bid + ask) / 2.0


def validate_probability(value: float, name: str) -> None:
    if not (0.0 <= value <= 1.0):
        raise ValueError(f"{name} must be in [0, 1], got {value}")


def generate_signal(snapshot: MarketSnapshot, threshold: float) -> Signal:
    validate_probability(snapshot.yes_bid, "yes_bid")
    validate_probability(snapshot.yes_ask, "yes_ask")
    validate_probability(snapshot.model_prob_yes, "model_prob_yes")

    if snapshot.yes_bid > snapshot.yes_ask:
        raise ValueError(
            f"yes_bid cannot exceed yes_ask: "
            f"{snapshot.yes_bid} > {snapshot.yes_ask}"
        )

    market_prob_yes = midpoint(snapshot.yes_bid, snapshot.yes_ask)

    if snapshot.row_type == RowType.SETTLEMENT:
        return Signal(
            market_id=snapshot.market_id,
            side=None,
            model_prob_yes=snapshot.model_prob_yes,
            market_prob_yes=market_prob_yes,
            edge_yes=0.0,
            edge_no=0.0,
            chosen_edge=0.0,
        )

    yes_ask = snapshot.yes_ask
    no_ask = 1.0 - snapshot.yes_bid

    edge_yes = snapshot.model_prob_yes - yes_ask
    edge_no = (1.0 - snapshot.model_prob_yes) - no_ask

    if edge_yes >= threshold and edge_yes >= edge_no:
        return Signal(
            market_id=snapshot.market_id,
            side=Side.BUY_YES,
            model_prob_yes=snapshot.model_prob_yes,
            market_prob_yes=market_prob_yes,
            edge_yes=edge_yes,
            edge_no=edge_no,
            chosen_edge=edge_yes,
        )

    if edge_no >= threshold:
        return Signal(
            market_id=snapshot.market_id,
            side=Side.BUY_NO,
            model_prob_yes=snapshot.model_prob_yes,
            market_prob_yes=market_prob_yes,
            edge_yes=edge_yes,
            edge_no=edge_no,
            chosen_edge=edge_no,
        )

    return Signal(
        market_id=snapshot.market_id,
        side=None,
        model_prob_yes=snapshot.model_prob_yes,
        market_prob_yes=market_prob_yes,
        edge_yes=edge_yes,
        edge_no=edge_no,
        chosen_edge=0.0,
    )