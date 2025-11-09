import time
import requests
from datetime import datetime, timezone

GRAPHQL_URL = "https://api.github.com/graphql"

def graphql_query(query, variables, token, retries=5):
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v4+json"
    }

    for attempt in range(retries):
        response = requests.post(GRAPHQL_URL, json={"query": query, "variables": variables}, headers=headers)

        if response.status_code == 200:
            result = response.json()

            if "errors" in result:
                # Rate-limit or other errors
                for error in result["errors"]:
                    if error.get("type") == "RATE_LIMITED":
                        reset_at = result.get("data", {}).get("rateLimit", {}).get("resetAt")
                        if reset_at:
                            reset_dt = datetime.fromisoformat(reset_at.replace("Z", "+00:00"))
                            sleep_seconds = (reset_dt - datetime.now(timezone.utc)).total_seconds() + 5
                            print(f"⏳ Rate limit hit. Sleeping {int(sleep_seconds)}s...")
                            time.sleep(max(0, sleep_seconds))
                            break
                else:
                    raise Exception(result["errors"])
                continue
            return result
        elif response.status_code == 403:
            print("⚠️ 403 Forbidden. Sleeping 60s...")
            time.sleep(60)
        else:
            print(f"Retry {attempt+1}/{retries} after failure {response.status_code}")
            time.sleep(2 ** attempt)

    raise Exception("GraphQL query failed after retries.")