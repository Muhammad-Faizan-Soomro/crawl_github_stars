# 🕸️ GitHub Stars Crawler

A lightweight **GitHub GraphQL crawler** that collects repository metadata, stores it in **PostgreSQL**, and exports results as CSV — fully automated via **GitHub Actions**.

---

## ⚙️ Overview

This project:

* Fetches repositories (excluding forks) via **GitHub GraphQL API**
* Stores them in a **PostgreSQL** table
* Exports results to **`repositories.csv`**
* Runs automatically or manually using **GitHub Actions**

---

## 🗂️ Structure

```
crawl_github_stars/
│
├── core/                     # Business logic (use cases, entities)
│   ├── crawler.py            # Crawling orchestration logic
│   ├── queries.py            # GraphQL queries
│   └── models.py             # Domain models (Repository etc.)
│
├── infrastructure/           # Low-level details (DB, API, etc.)
│   ├── github_api.py         # GitHub GraphQL communication
│   ├── database.py           # PostgreSQL connection + upsert
│   └── setup_schema.sql      # DB schema
│
├── config/                   # Configuration and environment
│   └── settings.py
│
├── app/                      
│   └── main.py               # Entry point (main)
│
├── requirements.txt
├── .env
└── .github/
    └── workflows/
        └── crawl.yml         # GitHub Actions automation
```

---

## 🚀 Run Options

### 🧑‍💻 Locally

```bash
pip install -r requirements.txt
python app/main.py
```

### ⚙️ On GitHub Actions

Go to **Actions → GitHub Crawler → Run workflow**, wait for completion, and download `repositories.csv` from the **Artifacts** section.

---

## 📦 Environment Variables

| Variable       | Description                  |
| -------------- | ---------------------------- |
| `DATABASE_URL` | PostgreSQL connection string |
| `GITHUB_TOKEN` | GitHub token for API access  |

---

## 🧠 Scaling to 500 Million Repositories

If scaling up to **500M repositories**, key changes would include:

* **Distributed Architecture:** Use multiple worker nodes (e.g., via AWS Lambda or Kubernetes) to parallelize data collection.
* **Batch Processing:** Implement sharded queries and queue-based coordination (e.g., SQS, Kafka).
* **Incremental Crawling:** Continuously update only changed repositories (using `updatedAt` field).
* **Efficient Storage:** Replace PostgreSQL with horizontally scalable DBs (e.g., BigQuery, ClickHouse, or sharded Postgres).
* **Streaming & Compression:** Stream results to cloud storage (e.g., S3) instead of holding all in memory.
* **Leverage Public Datasets:** Instead of crawling repositories directly, use publicly available GitHub datasets (e.g., on BigQuery or GH Archive) to pre-fetch `node_id`s and only query detailed metadata for relevant repositories.

---

## 🧱 Schema Evolution for Richer Metadata

To support **issues, PRs, commits, comments, and reviews**, evolve the schema into a **normalized, relational model**:

* **Separate tables:**

  * `repositories`, `issues`, `pull_requests`, `commits`, `comments`, `reviews`, `checks`
* **Foreign keys:** Link each child entity to its parent (`repo_id`, `pr_id`, `issue_id`, etc.)
* **Incremental updates:** Use unique IDs and timestamps (`updated_at`) to upsert only modified records — ensuring minimal row changes.
* **Partitioning:** Use time-based or repo-based partitions for scalable updates.
* **Indexing:** Add indexes on foreign keys and timestamps to optimize delta updates.

This structure ensures efficient tracking of evolving entities like new comments or CI results without full-table rewrites.

---

## 🧾 Summary

**GitHub Stars Crawler** automates repository data collection with a clean schema, reliable automation, and scalable design principles — ready to extend toward large-scale GitHub analytics.