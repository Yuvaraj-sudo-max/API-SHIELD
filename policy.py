"""
policy.py - Rate limit policy models and manager for API Shield.
Implements SRS Section 3.2, 3.3, 7, and 11.
"""

import json
import os
from typing import Dict, Any, Optional, List


class RateLimitRule:
    """
    Represents one rate-limit rule and its validation logic (SRS Section 3.2 & 11).
    """

    def __init__(
        self,
        name: str,
        endpoint: str,
        limit: int,
        window: int,
        algorithm: str = "fixed_window",
        active: bool = True,
    ):
        self.name = str(name).strip() if name is not None else ""
        self.endpoint = str(endpoint).strip() if endpoint is not None else ""
        self.limit = int(limit)
        self.window = int(window)
        self.algorithm = str(algorithm).strip() if algorithm is not None else "fixed_window"
        self.active = bool(active)
        self.validate()

    def validate(self) -> None:
        """
        Validates policy fields according to SRS Section 3.3 & Business Rules:
        - name must be a non-empty string.
        - endpoint must start with '/'.
        - limit must be greater than 0 (BR-03).
        - window must be greater than 0 (BR-04).
        - algorithm must be 'fixed_window' or 'sliding_window'.
        """
        if not self.name:
            raise ValueError("Policy name must be a non-empty string.")

        if not self.endpoint.startswith("/"):
            raise ValueError("Endpoint must start with '/'.")

        if self.limit <= 0:
            raise ValueError("Limit must be greater than 0.")

        if self.window <= 0:
            raise ValueError("Window must be greater than 0.")

        if self.algorithm not in ("fixed_window", "sliding_window"):
            raise ValueError("Algorithm must be 'fixed_window' or 'sliding_window'.")

    def get_key(self, client_id: str) -> str:
        """
        Generates Redis base key part for this client and endpoint (BR-08).
        """
        return f"{client_id}:{self.endpoint}"

    def to_dict(self) -> Dict[str, Any]:
        """Converts policy rule to JSON serializable dictionary."""
        return {
            "name": self.name,
            "endpoint": self.endpoint,
            "limit": self.limit,
            "window": self.window,
            "algorithm": self.algorithm,
            "active": self.active,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RateLimitRule":
        """Instantiates RateLimitRule from dictionary with validation."""
        required_fields = ["name", "endpoint", "limit", "window"]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: '{field}'")

        return cls(
            name=data["name"],
            endpoint=data["endpoint"],
            limit=data["limit"],
            window=data["window"],
            algorithm=data.get("algorithm", "fixed_window"),
            active=data.get("active", True),
        )


class PolicyManager:
    """
    Manages policies in-memory and persists to JSON file (SRS Section 7 & 11).
    """

    def __init__(self, storage_file: Optional[str] = None):
        self.policies: Dict[str, RateLimitRule] = {}
        self.storage_file = storage_file
        if storage_file and os.path.exists(storage_file):
            self.load_from_file(storage_file)

    def create_policy(self, policy_data: Dict[str, Any]) -> RateLimitRule:
        """
        Creates a new policy. Validates input and rejects duplicate names (SRS 3.3).
        """
        name = policy_data.get("name")
        if not name or not isinstance(name, str) or not name.strip():
            raise ValueError("Policy name must be a non-empty string.")

        name = name.strip()
        if name in self.policies:
            raise ValueError(f"Policy with name '{name}' already exists.")

        rule = RateLimitRule.from_dict(policy_data)
        self.policies[name] = rule
        self._persist()
        return rule

    def update_policy(self, name: str, policy_data: Dict[str, Any]) -> RateLimitRule:
        """
        Updates an existing policy. Validates input (SRS Section 7).
        """
        if name not in self.policies:
            raise KeyError(f"Policy '{name}' not found.")

        data = dict(policy_data)
        data["name"] = name  # preserve identifier
        rule = RateLimitRule.from_dict(data)
        self.policies[name] = rule
        self._persist()
        return rule

    def activate_policy(self, name: str) -> RateLimitRule:
        """
        Activates a policy (SRS Section 7 & 7.1).
        """
        if name not in self.policies:
            raise KeyError(f"Policy '{name}' not found.")
        self.policies[name].active = True
        self._persist()
        return self.policies[name]

    def deactivate_policy(self, name: str) -> RateLimitRule:
        """
        Deactivates a policy (SRS Section 7 & 7.1).
        """
        if name not in self.policies:
            raise KeyError(f"Policy '{name}' not found.")
        self.policies[name].active = False
        self._persist()
        return self.policies[name]

    def delete_policy(self, name: str) -> bool:
        """
        Deletes a policy by name and persists changes.
        """
        if name in self.policies:
            del self.policies[name]
            self._persist()
            return True
        return False

    def get_policy(self, name: str) -> Optional[RateLimitRule]:
        """
        Returns policy by name or None.
        """
        return self.policies.get(name)

    def get_policy_for_endpoint(self, endpoint: str) -> Optional[RateLimitRule]:
        """
        Returns active matching policy for the endpoint.
        BR-01: An inactive policy shall not limit requests.
        BR-02: If no policy exists for an endpoint, request shall be allowed.
        BR-10: Policy changes shall affect new rate-limit checks after active.
        """
        for policy in self.policies.values():
            if policy.active and policy.endpoint == endpoint:
                return policy
        return None

    def list_policies(self) -> List[Dict[str, Any]]:
        """Returns list of all policy dictionaries."""
        return [p.to_dict() for p in self.policies.values()]

    def load_from_file(self, filepath: str) -> None:
        """Loads policies from JSON file."""
        if not os.path.exists(filepath):
            return

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return
                data = json.loads(content)

            self.policies.clear()
            if isinstance(data, list):
                for item in data:
                    rule = RateLimitRule.from_dict(item)
                    self.policies[rule.name] = rule
            elif isinstance(data, dict):
                for name, item in data.items():
                    if "name" not in item:
                        item["name"] = name
                    rule = RateLimitRule.from_dict(item)
                    self.policies[rule.name] = rule
        except Exception:
            # Silently tolerate file reading issue or leave empty
            pass

    def save_to_file(self, filepath: str) -> None:
        """Saves current policies to JSON file."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump([p.to_dict() for p in self.policies.values()], f, indent=2)

    def _persist(self) -> None:
        if self.storage_file:
            self.save_to_file(self.storage_file)
