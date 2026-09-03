#!/usr/bin/env python3
"""Regenerate the recent-activity section of the profile README from public GitHub events."""

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

USER = os.environ.get("GITHUB_ACTOR", "THEECECODER")
README = Path(__file__).resolve().parent.parent / "README.md"
START = "<!-- ACTIVITY:START -->"
END = "<!-- ACTIVITY:END -->"
MAX_ITEMS = 5

EVENT_TEMPLATES = {
    "PushEvent": "Pushed {count} commit(s) to [{repo}](https://github.com/{repo})",
    "PullRequestEvent": "{action_pr} PR [#{number}](https://github.com/{repo}/pull/{number}) in [{repo}](https://github.com/{repo})",
    "IssuesEvent": "{action_pr} issue [#{number}](https://github.com/{repo}/issues/{number}) in [{repo}](https://github.com/{repo})",
    "CreateEvent": "Created {ref_type} in [{repo}](https://github.com/{repo})",
    "WatchEvent": "Starred [{repo}](https://github.com/{repo})",
    "ForkEvent": "Forked [{repo}](https://github.com/{repo})",
    "ReleaseEvent": "Published a release in [{repo}](https://github.com/{repo})",
}


def fetch_events():
    request = urllib.request.Request(
        f"https://api.github.com/users/{USER}/events/public?per_page=100",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"{USER}-profile-readme",
        },
    )
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def describe(event):
    template = EVENT_TEMPLATES.get(event["type"])
    if template is None:
        return None
    payload = event.get("payload", {})
    return template.format(
        repo=event["repo"]["name"],
        count=len(payload.get("commits", [])) or 1,
        number=(payload.get("pull_request") or payload.get("issue") or {}).get("number", ""),
        action_pr=payload.get("action", "updated").capitalize(),
        ref_type=payload.get("ref_type", "a ref"),
    )


def render(events):
    lines = []
    for event in events:
        line = describe(event)
        if line is None:
            continue
        when = datetime.strptime(event["created_at"], "%Y-%m-%dT%H:%M:%SZ").strftime("%d %b %Y")
        lines.append(f"{len(lines) + 1}. {line} — _{when}_")
        if len(lines) == MAX_ITEMS:
            break
    if not lines:
        lines.append("_No public activity in the last 90 days._")
    updated = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")
    body = "\n".join(lines)
    return f"{START}\n### ⚡ Recent Activity\n\n{body}\n\n<sub>Last updated: {updated}</sub>\n{END}"


def main():
    try:
        events = fetch_events()
    except (urllib.error.URLError, TimeoutError) as error:
        print(f"failed to fetch events: {error}", file=sys.stderr)
        return 1

    section = render(events)
    readme = README.read_text(encoding="utf-8")
    if START in readme and END in readme:
        readme = re.sub(
            re.escape(START) + r".*?" + re.escape(END), lambda _: section, readme, flags=re.DOTALL
        )
    else:
        readme = readme.rstrip("\n") + "\n\n" + section + "\n"
    README.write_text(readme, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
