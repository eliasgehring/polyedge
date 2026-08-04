import pytest

from polyedge.nba_team_identity import (
    canonical_nba_team,
    nba_matchup_matches,
)


def test_full_and_short_names_have_same_identity():
    assert canonical_nba_team(
        "Boston Celtics"
    ) == "BOS"

    assert canonical_nba_team(
        "Celtics"
    ) == "BOS"


def test_handles_multiword_nickname():
    assert canonical_nba_team(
        "Portland Trail Blazers"
    ) == "POR"

    assert canonical_nba_team(
        "Trail Blazers"
    ) == "POR"


def test_normalizes_case_and_spacing():
    assert canonical_nba_team(
        "  new   york KNICKS "
    ) == "NYK"


def test_matches_home_and_away_orientation():
    assert nba_matchup_matches(
        manifest_home="Celtics",
        manifest_away="Knicks",
        provider_home="Boston Celtics",
        provider_away="New York Knicks",
    )


def test_does_not_accept_reversed_orientation():
    assert not nba_matchup_matches(
        manifest_home="Celtics",
        manifest_away="Knicks",
        provider_home="New York Knicks",
        provider_away="Boston Celtics",
    )


def test_rejects_unknown_team_instead_of_guessing():
    with pytest.raises(
        ValueError,
        match="Unknown NBA team name",
    ):
        canonical_nba_team(
            "York Basketball Club"
        )
