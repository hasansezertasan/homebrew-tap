---
name: homebrew-formula-dispatch
description: Use when wiring a package repo to auto-update its Homebrew formula in hasansezertasan/homebrew-tap after a release. Run this INSIDE the package repo (not the tap). Triggers include "set up automatic homebrew formula updates", "trigger homebrew-tap on release", "add the homebrew dispatch workflow", and the README copy-paste prompt.
---

# Wiring a Package Repo to Trigger Homebrew Formula Updates

## What this does

Adds a GitHub Actions workflow to a **package repo** (e.g. `micoo`, `peta`, `keycast`)
that fires a `repository_dispatch` at `hasansezertasan/homebrew-tap` when a release is
published. The tap's `update-formula-dispatch.yml` then bumps the version, refreshes
Python resources, and opens the PR — all on the tap side, with the tap's own
`GITHUB_TOKEN`.

**Run this skill from the package repo you want to wire up — not from the tap.** The
skill only writes one file plus a secret reminder; the bump logic lives in the tap.

## Prerequisite: the dispatch token

The package repo needs a secret named `HOMEBREW_TAP_TOKEN`:

- A **fine-grained** PAT scoped to `hasansezertasan/homebrew-tap`
- Permission: **Contents: write** — and *only* that. `POST /repos/.../dispatches`
  requires Contents: write for fine-grained PATs. **Pull requests: write is NOT needed**
  — the tap opens the PR itself. Do not use the broad classic `repo` scope.

The user creates this at github.com → Settings → Developer settings → fine-grained
tokens, then adds it under the package repo's Settings → Secrets → Actions as
`HOMEBREW_TAP_TOKEN`. You cannot create it for them; remind them and verify the workflow
references it.

## Write the workflow

Create `.github/workflows/update-homebrew-formula.yml` in the package repo:

```yaml
name: Update Homebrew Formula
on:
  release:
    types: [published]
  workflow_dispatch:
jobs:
  update-formula:
    name: Trigger formula update
    runs-on: ubuntu-latest
    steps:
      - name: Trigger homebrew-tap update
        uses: peter-evans/repository-dispatch@v3
        with:
          token: ${{ secrets.HOMEBREW_TAP_TOKEN }}
          repository: hasansezertasan/homebrew-tap
          event-type: update-formula
          client-payload: |
            {
              "formula": "${{ github.event.repository.name }}",
              "version": "${{ github.event.release.tag_name }}"
            }
      - name: Summary
        run: |
          echo "Triggered Homebrew formula update for ${{ github.event.repository.name }}"
          echo "Version: ${{ github.event.release.tag_name }}"
          echo ""
          echo "Check the homebrew-tap repo for the PR:"
          echo "https://github.com/hasansezertasan/homebrew-tap/pulls"
```

## Verify

- **YAML is valid** and the file is at `.github/workflows/update-homebrew-formula.yml`.
- **`formula` matches the tap's formula name.** The payload uses
  `github.event.repository.name`. If the repo name differs from the formula file name in
  `Formula/<name>.rb`, hardcode the correct `formula` value instead.
- **`version` maps to the release tag.** The tap's `brew bump-formula-pr` accepts tags
  like `v1.0.0` or `1.0.0`.
- **The `HOMEBREW_TAP_TOKEN` secret exists** in the package repo (remind the user; you
  can't see repo secrets).

## Casks work the same way

If the package ships a **cask** (a prebuilt app) instead of/in addition to a formula,
the dispatch is `event-type: update-cask` with payload `{ "cask": "<name>", "version":
"..." }`, handled by the tap's `update-cask-dispatch.yml`. `keycast`'s `release.yml`
already does this after attaching its `.dmg`. Adapt the workflow above accordingly.

## Notes

- This is the **push** path. The tap also runs a weekly `livecheck` cron
  (`update-formulas.yml` / `update-casks.yml`) as a fallback for a missed dispatch, so a
  repo without this workflow still gets updated — just slower.
- The producer only **signals**; all bump logic stays in the tap so it lives in one
  place. Don't add `brew bump-*` steps to the package repo.
