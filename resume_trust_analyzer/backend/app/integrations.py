from __future__ import annotations

import httpx


class GitHubClient:
    def __init__(self, token: str | None = None):
        self.token = token
        self.base_url = "https://api.github.com"

    async def collect_profile_summary(self, username: str) -> dict:
        headers = {"Accept": "application/vnd.github+json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        async with httpx.AsyncClient(timeout=8.0, headers=headers) as client:
            user_response = await client.get(f"{self.base_url}/users/{username}")
            user_response.raise_for_status()
            repos_response = await client.get(
                f"{self.base_url}/users/{username}/repos",
                params={"sort": "updated", "per_page": 100},
            )
            repos_response.raise_for_status()

        user = user_response.json()
        repos = repos_response.json()

        languages = sorted({repo.get("language") for repo in repos if repo.get("language")})
        has_react_projects = any(
            "react" in (repo.get("name") or "").lower()
            or "react" in (repo.get("description") or "").lower()
            for repo in repos
        )

        active_months = len({
            (repo.get("updated_at") or "")[:7]
            for repo in repos
            if repo.get("updated_at")
        })

        return {
            "profile_created_at": user.get("created_at"),
            "public_repos": user.get("public_repos", 0),
            "active_months": active_months,
            "languages": languages,
            "has_react_projects": has_react_projects,
            "has_tests": False,
            "has_readme": False,
        }


class HHClient:
    def __init__(self, token: str | None = None):
        self.token = token
        self.base_url = "https://api.hh.ru"

    async def search_vacancies(self, text: str) -> dict:
        headers = {"User-Agent": "resume-trust-analyzer/1.0"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        async with httpx.AsyncClient(timeout=8.0, headers=headers) as client:
            response = await client.get(
                f"{self.base_url}/vacancies",
                params={"text": text, "per_page": 20},
            )
            response.raise_for_status()
            return response.json()


class StackExchangeClient:
    base_url = "https://api.stackexchange.com/2.3"

    async def get_user_tags(self, user_id: str) -> dict:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(
                f"{self.base_url}/users/{user_id}/tags",
                params={"site": "stackoverflow", "pagesize": 30, "order": "desc", "sort": "popular"},
            )
            response.raise_for_status()
            return response.json()
