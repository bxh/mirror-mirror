"""Report generation from GitHub contributions."""

from __future__ import annotations

import platform
import subprocess
import sys
from collections import defaultdict

import markdown as md
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from .github import Contributions

_EMAIL_CSS = """\
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; color: #24292f; line-height: 1.6; }
h1 { font-size: 1.4em; border-bottom: 1px solid #d1d9e0; padding-bottom: 0.3em; }
h2 { font-size: 1.2em; margin-top: 1.2em; border-bottom: 1px solid #d1d9e0; padding-bottom: 0.2em; }
h3 { font-size: 1em; margin-top: 1em; }
table { border-collapse: collapse; margin: 0.8em 0; }
th, td { border: 1px solid #d1d9e0; padding: 6px 12px; text-align: left; }
th { background: #f6f8fa; font-weight: 600; }
a { color: #0969da; text-decoration: none; }
a:hover { text-decoration: underline; }
ul { padding-left: 1.5em; }
li { margin: 0.25em 0; }
blockquote { margin: 0.4em 0 0.4em 1em; padding-left: 0.8em; border-left: 3px solid #d1d9e0; color: #656d76; }
code { background: #f6f8fa; padding: 0.15em 0.3em; border-radius: 3px; font-size: 0.9em; }
hr { border: none; border-top: 1px solid #d1d9e0; margin: 1.5em 0; }
"""


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


def markdown_to_html(markdown_text: str) -> str:
    """Convert markdown to a self-contained HTML document with inline styles for email."""
    body = md.markdown(
        markdown_text,
        extensions=["tables", "fenced_code"],
    )
    return (
        '<!DOCTYPE html><html><head><meta charset="utf-8">'
        f"<style>{_EMAIL_CSS}</style></head>"
        f"<body>{body}</body></html>"
    )


def copy_html_to_clipboard(html: str) -> bool:
    """Copy HTML to system clipboard as rich text. Returns True on success."""
    if platform.system() == "Darwin":
        hex_data = html.encode("utf-8").hex()
        script = (
            "set the clipboard to "
            "{«class HTML»:«data HTML" + hex_data + "»}"
        )
        try:
            subprocess.run(
                ["osascript", "-e", script],
                check=True,
                capture_output=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    if platform.system() == "Linux":
        for cmd in ("xclip", "xsel"):
            try:
                subprocess.run(
                    [cmd, "-selection", "clipboard", "-t", "text/html"],
                    input=html.encode("utf-8"),
                    check=True,
                    capture_output=True,
                )
                return True
            except FileNotFoundError:
                continue
        return False

    # Fallback: plain text via pbcopy/clip/xclip
    try:
        subprocess.run(
            ["pbcopy"] if platform.system() == "Darwin" else ["clip"],
            input=html.encode("utf-8"),
            check=True,
            capture_output=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


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
    if path.endswith(".html"):
        content = markdown_to_html(markdown_text)
    else:
        content = markdown_text
    with open(path, "w") as f:
        f.write(content)
    return path
