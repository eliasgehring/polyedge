import pytest

from polyedge.bookmaker_odds import (
    parse_the_odds_api_moneylines,
)


def sample_payload():
    return [
        {
            "id": "event_1",
            "sport_key": "basketball_wnba",
            "commence_time": "2026-08-05T02:00:00Z",
            "home_team": "Home Team",
            "away_team": "Away Team",
            "bookmakers": [
                {
                    "key": "example_book",
                    "title": "Example Book",
                    "last_update": "2026-08-04T09:33:13Z",
                    "markets": [
                        {
                            "key": "h2h",
                            "last_update": (
                                "2026-08-04T09:33:13Z"
                            ),
                            "outcomes": [
                                {
                                    "name": "Home Team",
                                    "price": 1.50,
                                },
                                {
                                    "name": "Away Team",
                                    "price": 2.70,
                                },
                            ],
                        }
                    ],
                }
            ],
        }
    ]


def test_parses_timestamped_two_way_moneyline():
    quotes = parse_the_odds_api_moneylines(
        sample_payload()
    )

    assert len(quotes) == 1

    quote = quotes[0]

    assert quote.event_id == "event_1"
    assert quote.bookmaker_key == "example_book"
    assert quote.home_decimal_odds == 1.50
    assert quote.away_decimal_odds == 2.70
    assert quote.home_fair_prob == pytest.approx(
        0.642857142857
    )
    assert quote.away_fair_prob == pytest.approx(
        0.357142857143
    )
    assert (
        quote.home_fair_prob
        + quote.away_fair_prob
    ) == pytest.approx(1.0)

    assert quote.market_last_update.isoformat() == (
        "2026-08-04T09:33:13+00:00"
    )


def test_rejects_missing_home_outcome():
    payload = sample_payload()
    payload[0]["bookmakers"][0]["markets"][0][
        "outcomes"
    ][0]["name"] = "Wrong Team"

    with pytest.raises(ValueError):
        parse_the_odds_api_moneylines(payload)


def test_rejects_timestamp_without_timezone():
    payload = sample_payload()
    payload[0]["bookmakers"][0]["last_update"] = (
        "2026-08-04T09:33:13"
    )

    with pytest.raises(ValueError):
        parse_the_odds_api_moneylines(payload)


def test_skips_bookmaker_without_h2h_market():
    payload = sample_payload()
    payload[0]["bookmakers"][0]["markets"] = [
        {
            "key": "spreads",
            "last_update": "2026-08-04T09:33:13Z",
            "outcomes": [],
        }
    ]

    quotes = parse_the_odds_api_moneylines(payload)

    assert quotes == []
