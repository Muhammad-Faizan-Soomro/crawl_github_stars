REPO_SEARCH_QUERY = """
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
