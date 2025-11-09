import os
import psycopg2
from psycopg2.extras import execute_values

def get_connection(db_url: str):
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    return conn

def upsert_repos(conn, repo_list):
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
        execute_values(cur, sql, [
            (
                r.node_id,
                r.name,
                r.owner,
                r.stars_count,
                r.updated_at,
                r.fetched_at
            ) for r in repo_list
        ])
    conn.commit()