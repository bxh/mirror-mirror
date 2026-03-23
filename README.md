# mirror-mirror

Scan your GitHub contributions and generate AI-summarized weekly work reports — ready to paste into an email. Optionally get roasted by Elon.

Tracks **commits**, **pull requests**, **code reviews**, and **issues** — then uses OpenAI to distill them into a two-section status update (Last Week / This Week).

## Setup

```bash
uv sync
```

Create a `.env` file in the project root:

```
GITHUB_TOKEN=ghp_...
OPENAI_API_KEY=sk-...
```

- **GitHub token** — create at [github.com/settings/tokens](https://github.com/settings/tokens) with `repo` and `read:user` scopes.
- **OpenAI API key** — get one at [platform.openai.com/api-keys](https://platform.openai.com/api-keys).

## Usage

```bash
# Generate an AI-summarized report (last 7 days)
uv run mirror

# Filter to a specific GitHub org
uv run mirror --org CareEvolution

# Specify a different user or time range
uv run mirror --user octocat --days 14

# Use a different OpenAI model
uv run mirror --model gpt-4o

# Skip AI summary, output raw data only
uv run mirror --raw

# Save to a specific file
uv run mirror -o weekly-report.md

# Get roasted by Elon Musk
uv run mirror --roast
```

### Options

| Flag | Description | Default |
|------|-------------|---------|
| `--token` | GitHub PAT (or set `GITHUB_TOKEN` / `GH_TOKEN`) | — |
| `--user` | GitHub username | token owner |
| `--days` | Number of days to look back | `7` |
| `--org` | Filter to a specific GitHub organization | all orgs |
| `--model` | OpenAI model for summarization | `gpt-5-mini` |
| `--raw` | Skip AI summary, output raw data | off |
| `--roast` | Append an Elon Musk-style progress review | off |
| `-o, --output` | Output file path | `report-<user>-<date>.md` |

The report is printed to the terminal and saved as a markdown file.
