from dataclasses import dataclass
from datetime import datetime

@dataclass
class Repository:
    """Domain model representing a GitHub repository."""
    node_id: str
    name: str
    owner: str
    stars_count: int
    updated_at: datetime
    fetched_at: datetime

    @classmethod
    def from_github_node(cls, node: dict):
        """Factory method to create Repository from a GitHub API node."""
        return cls(
            node_id=node["id"],
            name=node["name"],
            owner=node["owner"]["login"],
            stars_count=node["stargazerCount"],
            updated_at=datetime.utcnow(),
            fetched_at=datetime.utcnow()
        )
