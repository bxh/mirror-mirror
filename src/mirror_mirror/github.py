"""GitHub API client for fetching user contributions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import httpx

GITHUB_API = "https://api.github.com"


@dataclass
class PullRequest:
    repo: str
    number: int
    title: str
    url: str
    state: str
    created_at: datetime
    merged: bool


@dataclass
class Issue:
    repo: str
    number: int
    title: str
    url: str
    state: str
    created_at: datetime


@dataclass
class Review:
    repo: str
    pr_number: int
    pr_title: str
    pr_url: str
    state: str
    submitted_at: datetime
    body: str = ""


@dataclass
class Commit:
    repo: str
    sha: str
    message: str
    url: str
    authored_at: datetime


@dataclass
class Contributions:
    username: str
    since: datetime
    until: datetime
    commits: list[Commit] = field(default_factory=list)
    pull_requests: list[PullRequest] = field(default_factory=list)
    reviews: list[Review] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)


class GitHubClient:
    def __init__(self, token: str) -> None:
        self._client = httpx.Client(
            base_url=GITHUB_API,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30,
        )

    def _get(self, url: str, params: dict | None = None) -> list[dict]:
        """GET with automatic pagination."""
        results: list[dict] = []
        while url:
            resp = self._client.get(url, params=params)
            resp.raise_for_status()
            results.extend(resp.json())
            params = None  # params already encoded in next link
            url = resp.links.get("next", {}).get("url", "")
        return results

    def whoami(self) -> str:
        resp = self._client.get("/user")
        resp.raise_for_status()
        return resp.json()["login"]

    def fetch_contributions(
        self, username: str | None = None, days: int = 7
    ) -> Contributions:
        if username is None:
            username = self.whoami()

        now = datetime.now(timezone.utc)
        since = now - timedelta(days=days)
        iso_since = since.strftime("%Y-%m-%dT%H:%M:%SZ")

        contributions = Contributions(
            username=username, since=since, until=now
        )

        contributions.pull_requests = self._fetch_pull_requests(
            username, iso_since
        )
        contributions.reviews = self._fetch_reviews(username, iso_since)
        contributions.issues = self._fetch_issues(username, iso_since)
        contributions.commits = self._fetch_commits(username, iso_since)

        return contributions

    def _fetch_pull_requests(
        self, username: str, since: str
    ) -> list[PullRequest]:
        created = self._search(
            "search/issues", f"author:{username} type:pr created:>={since}"
        )
        merged = self._search(
            "search/issues", f"author:{username} type:pr merged:>={since}"
        )
        seen: set[str] = set()
        items: list[dict] = []
        for item in created + merged:
            key = item["html_url"]
            if key not in seen:
                seen.add(key)
                items.append(item)
        return [
            PullRequest(
                repo=self._repo_from_url(item["repository_url"]),
                number=item["number"],
                title=item["title"],
                url=item["html_url"],
                state=item["state"],
                created_at=_parse_dt(item["created_at"]),
                merged=item.get("pull_request", {}).get("merged_at")
                is not None,
            )
            for item in items
        ]

    def _fetch_reviews(self, username: str, since: str) -> list[Review]:
        query = f"reviewed-by:{username} type:pr updated:>={since}"
        items = self._search("search/issues", query)
        since_dt = _parse_dt(since)
        reviews: list[Review] = []
        for item in items:
            repo = self._repo_from_url(item["repository_url"])
            review_date = self._latest_review_date(
                repo, item["number"], username
            )
            if review_date is None or review_date < since_dt:
                continue
            body = (item.get("body") or "")[:500]
            reviews.append(
                Review(
                    repo=repo,
                    pr_number=item["number"],
                    pr_title=item["title"],
                    pr_url=item["html_url"],
                    state="reviewed",
                    submitted_at=review_date,
                    body=body,
                )
            )
        return reviews

    def _latest_review_date(
        self, repo: str, pr_number: int, username: str
    ) -> datetime | None:
        """Get the most recent review date by this user on a PR."""
        resp = self._client.get(
            f"/repos/{repo}/pulls/{pr_number}/reviews"
        )
        if resp.status_code != 200:
            return None
        user_reviews = [
            r for r in resp.json()
            if (r.get("user") or {}).get("login", "").lower() == username.lower()
            and r.get("submitted_at")
        ]
        if not user_reviews:
            return None
        return max(_parse_dt(r["submitted_at"]) for r in user_reviews)

    def _fetch_issues(self, username: str, since: str) -> list[Issue]:
        query = f"author:{username} type:issue created:>={since}"
        items = self._search("search/issues", query)
        return [
            Issue(
                repo=self._repo_from_url(item["repository_url"]),
                number=item["number"],
                title=item["title"],
                url=item["html_url"],
                state=item["state"],
                created_at=_parse_dt(item["created_at"]),
            )
            for item in items
        ]

    def _fetch_commits(self, username: str, since: str) -> list[Commit]:
        query = f"author:{username} author-date:>={since}"
        resp = self._client.get(
            "/search/commits",
            params={"q": query, "sort": "author-date", "per_page": 100},
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
        return [
            Commit(
                repo=item["repository"]["full_name"],
                sha=item["sha"][:7],
                message=item["commit"]["message"].split("\n")[0],
                url=item["html_url"],
                authored_at=_parse_dt(item["commit"]["author"]["date"]),
            )
            for item in items
        ]

    def _search(self, endpoint: str, query: str) -> list[dict]:
        resp = self._client.get(
            f"/{endpoint}",
            params={"q": query, "sort": "created", "per_page": 100},
        )
        resp.raise_for_status()
        return resp.json().get("items", [])

    @staticmethod
    def _repo_from_url(api_url: str) -> str:
        parts = api_url.rstrip("/").split("/")
        return f"{parts[-2]}/{parts[-1]}"


def _parse_dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))
