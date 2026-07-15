#!/usr/bin/env python3
"""
Walks requests/*/ttl-expiry.json, finds anything past its TTL, and opens a
destroy branch + PR for it (adds `destroy = true` marker file that a
follow-up `terraform destroy` job/workflow watches for).

Requires: GITHUB_TOKEN env var, run from the repo root inside CI.
Uses only the standard library + `requests` (pip install requests) so it
stays easy to read -- swap in PyGithub if you want a nicer API.
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import urllib.request

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
REPO = os.environ.get("GITHUB_REPOSITORY", "williamrobin15/infra-requests")
API = f"https://api.github.com/repos/{REPO}"


def gh_post(path: str, payload: dict):
    req = urllib.request.Request(
        f"{API}{path}",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def run(*cmd):
    subprocess.run(cmd, check=True)


def main():
    now = datetime.now(timezone.utc)
    for manifest in Path("requests").glob("*/ttl-expiry.json"):
        data = json.loads(manifest.read_text())
        ttl_hours = data.get("ttl_hours", 0)
        created_at = data.get("created_at")
        if not ttl_hours or ttl_hours == 0 or created_at in (None, "GENERATED_AT_MERGE_TIME"):
            continue  # ttl 0 == never expires (e.g. prod); not-yet-applied requests are skipped

        created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        expires = created + timedelta(hours=ttl_hours)
        if now < expires:
            continue

        service = data["service_name"]
        branch = f"destroy-{service}-{int(now.timestamp())}"
        request_dir = manifest.parent

        run("git", "config", "user.name", "infra-bot")
        run("git", "config", "user.email", "infra-bot@users.noreply.github.com")
        run("git", "checkout", "-b", branch)
        (request_dir / "DESTROY").write_text(f"requested_at={now.isoformat()}\n")
        run("git", "add", str(request_dir / "DESTROY"))
        run("git", "commit", "-m", f"chore: TTL expired for {service}, request destroy")
        run("git", "push", "-u", "origin", branch)

        gh_post(
            "/pulls",
            {
                "title": f"[auto] Destroy expired resource: {service}",
                "head": branch,
                "base": "main",
                "body": (
                    f"TTL of {ttl_hours}h expired for `{service}` "
                    f"(created {created_at}). Merging this will trigger "
                    f"`terraform destroy` for this request.\n\n"
                    f"For non-prod environments, consider enabling GitHub's "
                    f"auto-merge on this repo's default settings so this "
                    f"needs no manual click."
                ),
            },
        )
        print(f"Opened destroy PR for {service}")


if __name__ == "__main__":
    main()
