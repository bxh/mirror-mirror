"""Report generation from GitHub contributions."""

from __future__ import annotations

from collections import defaultdict

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from .github import Contributions


def build_markdown(contrib: Contributions) -> str:
    since_str = contrib.since.strftime("%Y-%m-%d")
    until_str = contrib.until.strftime("%Y-%m-%d")

    lines: list[str] = []
    lines.append(f"# Weekly Work Report — @{contrib.username}")
    lines.append(f"**Period:** {since_str} to {until_str}\n")

    lines.append(f"## Summary")
    lines.append(f"| Category | Count |")
    lines.append(f"|----------|-------|")
    lines.append(f"| Commits | {len(contrib.commits)} |")
    lines.append(f"| Pull Requests | {len(contrib.pull_requests)} |")
    lines.append(f"| Code Reviews | {len(contrib.reviews)} |")
    lines.append(f"| Issues | {len(contrib.issues)} |")
    lines.append("")

    if contrib.pull_requests:
        lines.append("## Pull Requests")
        by_repo: dict[str, list] = defaultdict(list)
        for pr in contrib.pull_requests:
            by_repo[pr.repo].append(pr)
        for repo, prs in sorted(by_repo.items()):
            lines.append(f"### {repo}")
            for pr in prs:
                status = "merged" if pr.merged else pr.state
                lines.append(
                    f"- [{pr.title}]({pr.url}) (#{pr.number}, {status})"
                )
        lines.append("")

    if contrib.reviews:
        lines.append("## Code Reviews")
        by_repo_r: dict[str, list] = defaultdict(list)
        for r in contrib.reviews:
            by_repo_r[r.repo].append(r)
        for repo, revs in sorted(by_repo_r.items()):
            lines.append(f"### {repo}")
            for r in revs:
                lines.append(
                    f"- [{r.pr_title}]({r.pr_url}) (#{r.pr_number})"
                )
                if r.body:
                    summary = r.body.replace("\n", " ").strip()
                    lines.append(f"  > {summary}")
        lines.append("")

    if contrib.commits:
        lines.append("## Commits")
        by_repo_c: dict[str, list] = defaultdict(list)
        for c in contrib.commits:
            by_repo_c[c.repo].append(c)
        for repo, commits in sorted(by_repo_c.items()):
            lines.append(f"### {repo}")
            for c in commits:
                lines.append(f"- [`{c.sha}`]({c.url}) {c.message}")
        lines.append("")

    if contrib.issues:
        lines.append("## Issues")
        by_repo_i: dict[str, list] = defaultdict(list)
        for issue in contrib.issues:
            by_repo_i[issue.repo].append(issue)
        for repo, issues in sorted(by_repo_i.items()):
            lines.append(f"### {repo}")
            for issue in issues:
                lines.append(
                    f"- [{issue.title}]({issue.url}) (#{issue.number}, {issue.state})"
                )
        lines.append("")

    if not any(
        [
            contrib.commits,
            contrib.pull_requests,
            contrib.reviews,
            contrib.issues,
        ]
    ):
        lines.append("*No contributions found for this period.*\n")

    return "\n".join(lines)


def print_report(markdown_text: str) -> None:
    console = Console()
    console.print()
    console.print(
        Panel(
            Markdown(markdown_text),
            border_style="bright_blue",
            padding=(1, 2),
        )
    )
    console.print()


def save_report(markdown_text: str, path: str) -> str:
    with open(path, "w") as f:
        f.write(markdown_text)
    return path
