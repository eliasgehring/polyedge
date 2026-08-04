from typing import Dict, Iterable, Tuple


TEAM_ALIASES: Dict[str, Tuple[str, ...]] = {
    "ATL": ("Atlanta Hawks", "Hawks"),
    "BOS": ("Boston Celtics", "Celtics"),
    "BKN": ("Brooklyn Nets", "Nets"),
    "CHA": ("Charlotte Hornets", "Hornets"),
    "CHI": ("Chicago Bulls", "Bulls"),
    "CLE": ("Cleveland Cavaliers", "Cavaliers"),
    "DAL": ("Dallas Mavericks", "Mavericks"),
    "DEN": ("Denver Nuggets", "Nuggets"),
    "DET": ("Detroit Pistons", "Pistons"),
    "GSW": ("Golden State Warriors", "Warriors"),
    "HOU": ("Houston Rockets", "Rockets"),
    "IND": ("Indiana Pacers", "Pacers"),
    "LAC": (
        "Los Angeles Clippers",
        "LA Clippers",
        "Clippers",
    ),
    "LAL": ("Los Angeles Lakers", "Lakers"),
    "MEM": ("Memphis Grizzlies", "Grizzlies"),
    "MIA": ("Miami Heat", "Heat"),
    "MIL": ("Milwaukee Bucks", "Bucks"),
    "MIN": (
        "Minnesota Timberwolves",
        "Timberwolves",
    ),
    "NOP": (
        "New Orleans Pelicans",
        "Pelicans",
    ),
    "NYK": ("New York Knicks", "Knicks"),
    "OKC": (
        "Oklahoma City Thunder",
        "Thunder",
    ),
    "ORL": ("Orlando Magic", "Magic"),
    "PHI": (
        "Philadelphia 76ers",
        "76ers",
    ),
    "PHX": ("Phoenix Suns", "Suns"),
    "POR": (
        "Portland Trail Blazers",
        "Trail Blazers",
    ),
    "SAC": ("Sacramento Kings", "Kings"),
    "SAS": ("San Antonio Spurs", "Spurs"),
    "TOR": ("Toronto Raptors", "Raptors"),
    "UTA": ("Utah Jazz", "Jazz"),
    "WAS": ("Washington Wizards", "Wizards"),
}


def normalize_team_name(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError(
            "Team name must be a string"
        )

    normalized = " ".join(
        value.casefold().strip().split()
    )

    if not normalized:
        raise ValueError(
            "Team name must not be empty"
        )

    return normalized


def build_alias_index(
    aliases_by_team: Dict[
        str,
        Iterable[str],
    ],
) -> Dict[str, str]:
    index: Dict[str, str] = {}

    for team_code, aliases in aliases_by_team.items():
        for alias in aliases:
            normalized = normalize_team_name(alias)

            existing = index.get(normalized)

            if (
                existing is not None
                and existing != team_code
            ):
                raise ValueError(
                    f"Alias {alias!r} maps to both "
                    f"{existing} and {team_code}"
                )

            index[normalized] = team_code

    return index


ALIAS_TO_TEAM_CODE = build_alias_index(
    TEAM_ALIASES
)


def canonical_nba_team(value: str) -> str:
    normalized = normalize_team_name(value)

    try:
        return ALIAS_TO_TEAM_CODE[normalized]
    except KeyError as exc:
        raise ValueError(
            f"Unknown NBA team name: {value!r}"
        ) from exc


def nba_matchup_matches(
    manifest_home: str,
    manifest_away: str,
    provider_home: str,
    provider_away: str,
) -> bool:
    return (
        canonical_nba_team(manifest_home)
        == canonical_nba_team(provider_home)
        and canonical_nba_team(manifest_away)
        == canonical_nba_team(provider_away)
    )
