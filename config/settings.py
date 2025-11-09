import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
DB_URL = os.getenv("DATABASE_URL")

if not GITHUB_TOKEN or not DB_URL:
    raise EnvironmentError("Please set GITHUB_TOKEN and DATABASE_URL in your environment.")