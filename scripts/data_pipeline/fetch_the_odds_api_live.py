import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


API_ROOT = "https://api.the-odds-api.com"
SPORT_KEY = "basketball_wnba"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> None:
    api_key = os.environ.get("THE_ODDS_API_KEY")

    if not api_key:
        raise SystemExit(
            "THE_ODDS_API_KEY is not loaded."
        )

    params = {
        "apiKey": api_key,
        "regions": "us",
        "markets": "h2h",
        "oddsFormat": "decimal",
        "dateFormat": "iso",
    }

    query = urllib.parse.urlencode(params)
    endpoint = f"/v4/sports/{SPORT_KEY}/odds/"
    url = f"{API_ROOT}{endpoint}?{query}"

    requested_at = utc_now_iso()

    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "polyedge-research/0.1",
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=30,
        ) as response:
            raw_body = response.read()
            headers = {
                key.lower(): value
                for key, value in response.headers.items()
            }

    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode(
            "utf-8",
            errors="replace",
        )
        raise SystemExit(
            f"API returned HTTP {exc.code}:\n{error_body}"
        ) from exc

    except urllib.error.URLError as exc:
        raise SystemExit(
            f"Could not connect to The Odds API: {exc}"
        ) from exc

    received_at = utc_now_iso()

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise SystemExit(
            "The API response was not valid JSON."
        ) from exc

    if not isinstance(payload, list):
        raise SystemExit(
            "Expected the odds endpoint to return a list."
        )

    capture_id = datetime.now(
        timezone.utc
    ).strftime("%Y%m%dT%H%M%SZ")

    output_dir = Path(
        "data/raw/the_odds_api/live"
    )
    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    raw_path = (
        output_dir
        / f"{SPORT_KEY}_{capture_id}.json"
    )
    metadata_path = (
        output_dir
        / f"{SPORT_KEY}_{capture_id}.metadata.json"
    )

    raw_path.write_bytes(raw_body)

    metadata = {
        "provider": "the_odds_api",
        "sport_key": SPORT_KEY,
        "endpoint": endpoint,
        "request_parameters": {
            "regions": "us",
            "markets": "h2h",
            "oddsFormat": "decimal",
            "dateFormat": "iso",
        },
        "requested_at_utc": requested_at,
        "received_at_utc": received_at,
        "raw_file": str(raw_path),
        "raw_sha256": hashlib.sha256(
            raw_body
        ).hexdigest(),
        "quota": {
            "requests_last": headers.get(
                "x-requests-last"
            ),
            "requests_used": headers.get(
                "x-requests-used"
            ),
            "requests_remaining": headers.get(
                "x-requests-remaining"
            ),
        },
    }

    metadata_path.write_text(
        json.dumps(
            metadata,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print("LIVE ODDS CAPTURE SUCCESSFUL")
    print(f"Events returned       : {len(payload)}")
    print(f"Raw JSON              : {raw_path}")
    print(f"Metadata              : {metadata_path}")
    print(
        "Cost of request       : "
        f"{headers.get('x-requests-last')}"
    )
    print(
        "Credits remaining     : "
        f"{headers.get('x-requests-remaining')}"
    )

    if not payload:
        print(
            "\nNo upcoming WNBA events were returned."
        )
        return

    event = payload[0]

    print("\nSAMPLE EVENT")
    print(f"Event ID              : {event.get('id')}")
    print(f"Commence time         : {event.get('commence_time')}")
    print(f"Home team             : {event.get('home_team')}")
    print(f"Away team             : {event.get('away_team')}")

    bookmakers = event.get("bookmakers", [])
    print(f"Bookmakers returned   : {len(bookmakers)}")

    for bookmaker in bookmakers[:3]:
        print("\nBOOKMAKER")
        print(f"Key                   : {bookmaker.get('key')}")
        print(f"Title                 : {bookmaker.get('title')}")
        print(
            "Bookmaker last update : "
            f"{bookmaker.get('last_update')}"
        )

        h2h_market = next(
            (
                market
                for market in bookmaker.get("markets", [])
                if market.get("key") == "h2h"
            ),
            None,
        )

        if h2h_market is None:
            print("No h2h market returned.")
            continue

        print(
            "Market last update    : "
            f"{h2h_market.get('last_update')}"
        )

        for outcome in h2h_market.get("outcomes", []):
            print(
                f"  {outcome.get('name')}: "
                f"{outcome.get('price')}"
            )


if __name__ == "__main__":
    main()
