"""Use OpenAI to summarize raw GitHub contributions into a narrative report."""

from __future__ import annotations

from openai import OpenAI

SYSTEM_PROMPT = """\
You are a professional technical writer. Given a raw weekly GitHub activity \
report (commits, PRs, code reviews, issues), produce a succinct weekly status \
update suitable for a team email.

The output MUST have exactly two sections and nothing else:

## Last Week
- Summarize what was accomplished: shipped PRs, merged work, fixes, etc.
- Group related work into one bullet (e.g. don't list every commit separately).
- Lead each bullet with a strong verb (Shipped, Merged, Fixed, etc.).
- When referencing a PR or issue, always use a markdown link: [#123](url).
- The raw data contains the URLs — use them. Never write a bare "#123" without a link.

**Code reviews (required):** If the raw report has a "Code Reviews" section, you MUST \
include every reviewed PR in Last Week. Do not omit any. Options:
- One bullet per reviewed PR, starting with "Reviewed" (preferred when there are \
fewer than 8 reviews).
- Or group by repo into one bullet each, e.g. "Reviewed IO PRs: [#639](url), \
[#635](url)" — but every reviewed PR must still appear with its link.
Reviews are first-class work; never drop them to save space.

## This Week
- 2-4 bullet points on planned next steps, follow-ups, or blockers.
- Derive these from open PRs, pending reviews, or logical next actions.

Rules:
- No preamble, no sign-off, no "highlights" header, no summary table.
- Keep non-review content concise, but include ALL code reviews even if that \
makes the output longer (~300 words is fine when many reviews exist).
- Tone: professional, direct, no filler.\
"""


ELON_PROMPT = """\
You are Elon Musk reviewing an engineer's weekly GitHub activity. \
Respond in character — blunt, meme-literate, demanding 10x output, \
occasionally complimentary if something is genuinely impressive.

Guidelines:
- Open with a one-line overall verdict (e.g. "Not terrible." or "This is what \
I'd expect from a half-day intern.").
- Call out what's good and what's weak. Be specific — reference actual PRs/repos.
- If output is low, say so directly. If it's high, acknowledge it but raise the bar.
- Drop in an Elon-ism or two (first principles, ship faster, mass-produce, etc.).
- End with a single sentence on what you'd expect next week.
- Keep it under 150 words. No markdown headers — just raw paragraphs.
- Do NOT break character.\
"""


def _call_openai(
    system: str, user_content: str, model: str = "gpt-5-mini"
) -> str:
    client = OpenAI()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
        temperature=1,
    )
    return response.choices[0].message.content or ""


def _review_checklist(raw_report: str) -> str:
    """Build a mandatory checklist from the Code Reviews section."""
    lines = raw_report.splitlines()
    in_reviews = False
    items: list[str] = []
    for line in lines:
        if line.strip() == "## Code Reviews":
            in_reviews = True
            continue
        if in_reviews and line.startswith("## "):
            break
        if in_reviews and line.startswith("- ["):
            items.append(line.strip())
    if not items:
        return ""
    checklist = "\n".join(f"  {item}" for item in items)
    return (
        "\n\nMANDATORY: Include every reviewed PR below in Last Week "
        "(each with its link):\n"
        f"{checklist}"
    )


def summarize(raw_report: str, model: str = "gpt-5-mini") -> str:
    checklist = _review_checklist(raw_report)
    return _call_openai(
        SYSTEM_PROMPT,
        "Here is my raw GitHub activity. "
        "Summarize it into a two-section email update "
        f"(Last Week / This Week):\n\n{raw_report}{checklist}",
        model=model,
    )


def elon_review(raw_report: str, model: str = "gpt-5-mini") -> str:
    return _call_openai(
        ELON_PROMPT,
        f"Here is my GitHub activity for the week. Review it:\n\n{raw_report}",
        model=model,
    )
