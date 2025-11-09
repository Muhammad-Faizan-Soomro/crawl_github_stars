CREATE TABLE IF NOT EXISTS repositories (
    id SERIAL PRIMARY KEY,
    node_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    owner TEXT NOT NULL,
    stars_count INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT NOW(),
    fetched_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (owner, name)
);

CREATE INDEX IF NOT EXISTS idx_repositories_owner ON repositories(owner);