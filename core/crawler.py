from datetime import datetime, timedelta
from infrastructure.github_api import graphql_query
from infrastructure.database import upsert_repos
from core.queries import REPO_SEARCH_QUERY
from core.models import Repository

def generate_search_queries():
    start_date = datetime(2008, 1, 1)
    end_date = datetime(2024, 12, 31)
    current = start_date
    queries = []

    while current < end_date:
        next_day = current + timedelta(days=1)
        queries.append(f"created:{current.date()}..{next_day.date() - timedelta(days=1)} fork:false")
        current = next_day
    return queries

def crawl_repositories(conn, token, target_repos=100000, batch_size=100):
    total = 0
    for query_str in generate_search_queries():
        print(f"🔍 Query: {query_str}")
        has_next = True
        after_cursor = None

        while has_next and total < target_repos:
            batch = min(batch_size, target_repos - total)
            result = graphql_query(REPO_SEARCH_QUERY, {"query": query_str, "first": batch, "after": after_cursor}, token)
            data = result["data"]["search"]

            repos = [
                Repository.from_github_node(node)
                for node in data["nodes"]
            ]

            upsert_repos(conn, repos)
            total += len(repos)
            print(f"Fetched {total} repos so far...")

            has_next = data["pageInfo"]["hasNextPage"]
            after_cursor = data["pageInfo"]["endCursor"]

            if total >= target_repos:
                break
    print(f"✅ Finished crawling {total} repositories.")
