import json
import os
import urllib.error
import urllib.parse
import urllib.request


API_URL = "https://api.the-odds-api.com/v4/sports/"


def main() -> None:
    api_key = os.environ.get("THE_ODDS_API_KEY")

    if not api_key:
        raise SystemExit(
            "THE_ODDS_API_KEY is not loaded."
        )

    query = urllib.parse.urlencode(
        {
            "apiKey": api_key,
            "all": "true",
        }
    )

    request = urllib.request.Request(
        f"{API_URL}?{query}",
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
            payload = json.load(response)

            remaining = response.headers.get(
                "x-requests-remaining"
            )
            used = response.headers.get(
                "x-requests-used"
            )
            last_cost = response.headers.get(
                "x-requests-last"
            )

    except urllib.error.HTTPError as exc:
        body = exc.read().decode(
            "utf-8",
            errors="replace",
        )
        raise SystemExit(
            f"HTTP {exc.code}: {body}"
        ) from exc

    if not isinstance(payload, list):
        raise SystemExit(
            "Expected the API to return a list."
        )

    basketball = [
        sport
        for sport in payload
        if sport.get("group") == "Basketball"
    ]

    print("CONNECTION SUCCESSFUL")
    print(f"Sports returned      : {len(payload)}")
    print(f"Basketball sports    : {len(basketball)}")
    print(f"Credits used total   : {used}")
    print(f"Credits remaining    : {remaining}")
    print(f"Cost of this request : {last_cost}")

    print("\nBASKETBALL SPORT KEYS")

    for sport in basketball:
        print(
            f"{sport.get('key', ''):32s} "
            f"active={str(sport.get('active')):5s} "
            f"{sport.get('title', '')}"
        )


if __name__ == "__main__":
    main()
