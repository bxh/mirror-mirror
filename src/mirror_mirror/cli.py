"""CLI entry point for mirror-mirror."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

import click
from dotenv import load_dotenv
from rich.console import Console

load_dotenv()

from .github import GitHubClient
from .report import build_markdown, copy_html_to_clipboard, markdown_to_html, print_report, save_report
from .summarize import elon_review, summarize

console = Console()


def _resolve_token(token: str | None) -> str:
    if token:
        return token
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token
    console.print(
        "[red]Error:[/red] No GitHub token found.\n"
        "Set GITHUB_TOKEN in a .env file, as an env var, or pass --token.\n"
        "Create a token at: https://github.com/settings/tokens"
    )
    sys.exit(1)


@click.command()
@click.option(
    "--token",
    envvar="GITHUB_TOKEN",
    help="GitHub personal access token (or set GITHUB_TOKEN / GH_TOKEN).",
)
@click.option(
    "--user",
    default=None,
    help="GitHub username. Defaults to the token owner.",
)
@click.option(
    "--days",
    default=7,
    show_default=True,
    help="Number of days to look back.",
)
@click.option(
    "--output",
    "-o",
    default=None,
    help="Save report to a markdown file.",
)
@click.option(
    "--raw",
    is_flag=True,
    default=False,
    help="Skip AI summary and output raw data only.",
)
@click.option(
    "--model",
    default="gpt-5-mini",
    show_default=True,
    help="OpenAI model to use for summarization.",
)
@click.option(
    "--org",
    default=None,
    help="Filter contributions to a specific GitHub organization.",
)
@click.option(
    "--roast",
    is_flag=True,
    default=False,
    help="Get your progress reviewed by Elon Musk.",
)
@click.option(
    "--copy",
    is_flag=True,
    default=False,
    help="Copy report as rich HTML to clipboard (paste directly into Gmail).",
)
def main(
    token: str | None,
    user: str | None,
    days: int,
    output: str | None,
    raw: bool,
    model: str,
    org: str | None,
    roast: bool,
    copy: bool,
) -> None:
    """Scan GitHub contributions and generate a weekly work report."""
    token = _resolve_token(token)
    client = GitHubClient(token)

    if user is None:
        with console.status("[bold blue]Identifying user..."):
            user = client.whoami()

    scope = f" in {org}" if org else ""
    console.print(f"[bold blue]Scanning contributions for @{user}{scope} (last {days} days)...[/bold blue]\n")

    with console.status("[bold blue]Fetching data from GitHub..."):
        contributions = client.fetch_contributions(username=user, days=days, org=org)

    raw_md = build_markdown(contributions)

    if raw:
        report_md = raw_md
    else:
        openai_key = os.environ.get("OPENAI_API_KEY")
        if not openai_key:
            console.print(
                "[red]Error:[/red] OPENAI_API_KEY not set.\n"
                "Set it in .env or as an env var.\n"
                "Get a key at: https://platform.openai.com/api-keys"
            )
            sys.exit(1)
        with console.status("[bold blue]Generating AI summary..."):
            report_md = summarize(raw_md, model=model)

    print_report(report_md)

    if roast and not raw:
        with console.status("[bold red]Elon is reviewing your work..."):
            roast_text = elon_review(raw_md, model=model)
        console.print()
        from rich.panel import Panel
        console.print(Panel(roast_text, title="Elon's Review", border_style="bold red", padding=(1, 2)))
        console.print()
        report_md += f"\n\n---\n\n**Elon's Review:**\n\n{roast_text}"

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    default_name = f"report-{user}-{timestamp}.md"
    path = save_report(report_md, output or default_name)
    console.print(f"[green]Report saved to {path}[/green]")

    if copy:
        html = markdown_to_html(report_md)
        if copy_html_to_clipboard(html):
            console.print("[green]Report copied to clipboard — paste into Gmail.[/green]")
        else:
            console.print("[yellow]Could not copy to clipboard. Try: --output report.html[/yellow]")


if __name__ == "__main__":
    main()
