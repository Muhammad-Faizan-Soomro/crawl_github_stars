import os
import sys
import time
import math
import requests
import psycopg2
from psycopg2.extras import execute_values
from psycopg2 import sql
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

# ------------------------------
# CONFIGURATION
# ------------------------------

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
DB_URL = os.getenv("DATABASE_URL")

if not GITHUB_TOKEN or not DB_URL:
    print("Please set GITHUB_TOKEN and DATABASE_URL environment variables")
    sys.exit(1)

GRAPHQL_API_URL = "https://api.github.com/graphql"

# ------------------------------
# DATABASE CONNECTION + SCHEMA SETUP
# ------------------------------

def get_db_connection():
    """Create a database connection and ensure schema is set up."""
    try:
        # Connect to the database
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True
        print("✅ Connected to database successfully.")

        # Execute schema file (setup_schema.sql)
        setup_schema(conn)

        return conn

    except psycopg2.Error as e:
        print("❌ Database connection failed:", e)
        raise


def setup_schema(conn):
    """Execute SQL commands from setup_schema.sql file to create tables."""
    schema_file = "./setup_schema.sql"

    # Check if file exists
    if not os.path.exists(schema_file):
        print(f"⚠️ Schema file '{schema_file}' not found. Skipping schema setup.")
        return

    try:
        with open(schema_file, "r", encoding="utf-8") as f:
            schema_sql = f.read()

        with conn.cursor() as cur:
            cur.execute(schema_sql)
            print("🧱 Schema setup completed successfully.")

    except psycopg2.Error as e:
        print("❌ Error executing schema file:", e)
        raise

# ------------------------------
# HELPER FUNCTIONS
# ------------------------------

def graphql_query(query, variables=None, retries=3):
    for attempt in range(retries):
        headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
        response = requests.post(GRAPHQL_API_URL, json={"query": query, "variables": variables}, headers=headers)
        
        if response.status_code == 200:
            result = response.json()

            # ✅ Check GitHub rate limit
            rate_info = result.get("data", {}).get("rateLimit", {})
            remaining = rate_info.get("remaining")
            reset_at = rate_info.get("resetAt")

            if remaining is not None and remaining < 10:
                # Sleep until reset
                reset_seconds = (datetime.fromisoformat(reset_at[:-1]) - datetime.utcnow()).total_seconds()
                print(f"⏳ Rate limit nearly exhausted, sleeping for {int(reset_seconds)} seconds...")
                time.sleep(max(0, reset_seconds))
            
            return result

        elif response.status_code == 403:
            print(f"⚠️ Rate limit hit (403), sleeping for 60s...")
            time.sleep(60)

        else:
            print(f"Request failed ({response.status_code}), retrying in {2 ** attempt}s...")
            time.sleep(2 ** attempt)

    raise Exception(f"GraphQL query failed after {retries} attempts")
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v4+json"
    }

    for attempt in range(retries):
        response = requests.post(
            GRAPHQL_API_URL,
            json={"query": query, "variables": variables},
            headers=headers
        )

        # Check for HTTP-level errors
        if response.status_code != 200:
            print(f"Request failed ({response.status_code}), retrying in {2 ** attempt}s...")
            time.sleep(2 ** attempt)
            continue

        result = response.json()

        # Handle API-level errors
        if "errors" in result:
            for error in result["errors"]:
                # Explicit rate limit hit
                if error.get("type") == "RATE_LIMITED":
                    reset_at = None
                    # Try to parse resetAt from any rateLimit field if available
                    try:
                        reset_at = result["data"]["rateLimit"]["resetAt"]
                    except Exception:
                        pass
                    if reset_at:
                        reset_dt = datetime.fromisoformat(reset_at.replace("Z", "+00:00"))
                        sleep_for = (reset_dt - datetime.now(timezone.utc)).total_seconds()
                    else:
                        sleep_for = 60  # fallback
                    sleep_for = max(0, sleep_for)
                    print(f"Rate limit hit. Sleeping for {sleep_for:.1f} seconds...")
                    time.sleep(sleep_for)
                    break  # retry after sleep
            else:
                raise Exception(f"GraphQL errors: {result['errors']}")
            continue  # retry outer loop after sleeping

        # Extract rate limit info from response
        rate_info = result.get("data", {}).get("rateLimit")
        if rate_info:
            remaining = rate_info.get("remaining", 1)
            reset_at = rate_info.get("resetAt")
            if remaining < 50 and reset_at:
                reset_dt = datetime.fromisoformat(reset_at.replace("Z", "+00:00"))
                sleep_for = (reset_dt - datetime.now(timezone.utc)).total_seconds()
                sleep_for = max(0, sleep_for)
                print(f"Low rate limit remaining ({remaining}). Sleeping until reset ({sleep_for:.1f}s)...")
                time.sleep(sleep_for)

        # Success path — return result
        return result

    # If all retries failed
    raise Exception(f"GraphQL query failed after {retries} attempts")

# ------------------------------
# PARTITIONED SEARCH
# ------------------------------

# GitHub Search API only returns first 1000 results per query
# So we partition by repository creation date
def generate_search_queries(target_count=100000, partition_size=1000):
    # Example partition: created:>=2010-01-01 created:<2011-01-01
    # For simplicity, we can partition by year
    years = list(range(2008, 2024))  # Adjust range if needed
    queries = []
    for i in range(len(years) - 1):
        query_str = f"created:{years[i]}-01-01..{years[i+1]-1}-12-31"
        queries.append(query_str)
    return queries

# ------------------------------
# FETCH REPOSITORIES FROM SEARCH
# ------------------------------

def fetch_repos_from_search(query_string, first=100, after_cursor=None):
    """
    Fetches a page of repositories from GraphQL search API.
    """
    graphql_query_string = """
    query ($query: String!, $first: Int!, $after: String) {
      search(query: $query, type: REPOSITORY, first: $first, after: $after) {
        pageInfo {
          hasNextPage
          endCursor
        }
        nodes {
          ... on Repository {
            id
            name
            owner { login }
            stargazerCount
          }
        }
      }
      rateLimit {
        remaining
        resetAt
      }
    }
    """
    variables = {"query": query_string, "first": first, "after": after_cursor}
    result = graphql_query(graphql_query_string, variables)
    data = result["data"]
    return data

# ------------------------------
# DATABASE UPSERT
# ------------------------------

def upsert_repos(conn, repo_list):
    """
    repo_list = [
        {"id": ..., "name": ..., "owner": ..., "stars": ...},
        ...
    ]
    """
    if not repo_list:
        return

    with conn.cursor() as cur:
        sql = """
        INSERT INTO repositories (node_id, name, owner, stars_count, updated_at, fetched_at)
        VALUES %s
        ON CONFLICT (node_id) DO UPDATE
        SET stars_count = EXCLUDED.stars_count,
            updated_at = EXCLUDED.updated_at,
            fetched_at = EXCLUDED.fetched_at;
        """
        # Prepare data
        values = [
            (
                r["id"],
                r["name"],
                r["owner"],
                r["stars_count"],
                datetime.utcnow(),
                datetime.utcnow()
            )
            for r in repo_list
        ]
        execute_values(cur, sql, values)
    conn.commit()

# ------------------------------
# MAIN CRAWLER LOOP
# ------------------------------

def main(target_repos=100000, batch_size=100):
    conn = get_db_connection()
    total_fetched = 0
    search_queries = generate_search_queries()

    for query_str in search_queries:
        print(f"Searching with query: {query_str}")
        has_next = True
        after_cursor = None

        while has_next and total_fetched < target_repos:
            data = fetch_repos_from_search(query_str, first=batch_size, after_cursor=after_cursor)
            nodes = data["search"]["nodes"]
            page_info = data["search"]["pageInfo"]

            # Prepare for database
            repo_list = []
            for node in nodes:
                repo_list.append({
                    "id": node["id"],  # GitHub node_id
                    "name": node["name"],
                    "owner": node["owner"]["login"],
                    "stars_count": node["stargazerCount"]
                })

            # Insert/update in DB
            upsert_repos(conn, repo_list)
            total_fetched += len(repo_list)
            print(f"Fetched {total_fetched} repositories so far...")

            # Pagination
            has_next = page_info["hasNextPage"]
            after_cursor = page_info["endCursor"]

            if total_fetched >= target_repos:
                break

    print(f"Crawling complete. Total repos fetched: {total_fetched}")
    conn.close()

# ------------------------------
# RUN SCRIPT
# ------------------------------

if __name__ == "__main__":
    main(target_repos=100000, batch_size=100)