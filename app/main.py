from config.settings import GITHUB_TOKEN, DB_URL
from infrastructure.database import get_connection
from core.crawler import crawl_repositories

def main():
    conn = get_connection(DB_URL)
    crawl_repositories(conn, GITHUB_TOKEN, target_repos=100000, batch_size=100)
    conn.close()

if __name__ == "__main__":
    main()