# Branch protection setup (GitHub UI — one-time, ~5 minutes)

This is what actually enforces "approval" and "guardrails must pass" — no
code needed, GitHub does it natively.

1. Go to the `infra-requests` repo → **Settings → Branches**.
2. Under **Branch protection rules**, click **Add rule**.
3. Branch name pattern: `main`
4. Enable:
   - **Require a pull request before merging**
   - **Require approvals** → set to `1` (or more)
   - **Require review from Code Owners** (this makes CODEOWNERS enforceable)
   - **Dismiss stale pull request approvals when new commits are pushed**
   - **Require status checks to pass before merging** → search and add:
     - `guardrails / plan-and-scan`
     - (tfsec / infracost show up as PR checks automatically once the
       workflow has run once — add them here after the first PR)
   - **Do not allow bypassing the above settings** (so even admins can't
     skip it — important if you want this to actually be a guardrail)
5. Save.

## Why this gives you "can't approve your own request" for free

GitHub has a hard rule: a PR author can never approve their own PR, even
with admin rights, when "Require approvals" is on. You don't need to write
any code for this — it's built into GitHub's review system.

## Repo settings (Settings → General → Pull Requests)

- Enable **"Allow auto-merge"** if you want non-prod TTL-expiry destroy PRs
  (opened by `ttl-cleanup.yml`) to merge themselves once checks pass,
  without waiting for a human.
- Leave auto-merge OFF for prod — the destroy PR should still need review.
