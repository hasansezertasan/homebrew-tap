# Homebrew Tap Development Guide

This repository is a Homebrew tap generated from
[`copier-homebrew-tap`](https://github.com/hasansezertasan/copier-homebrew-tap).
Keep scripts and workflows owner-agnostic: the workflows resolve `owner/tap`
from the Actions context, so nothing hardcodes an owner or repository name.

Skills for operating the tap (adding, fixing, triaging, removing, and verifying
formulae and casks, and which generated
fields need a human check) come from
[`homebrew-tap-skills`](https://github.com/hasansezertasan/homebrew-tap-skills),
a skills repository that also installs as a Claude Code or Codex plugin.
Install it, or read its `skills/<name>/SKILL.md` files directly when a task
matches one.

## Layout

- `Formula/*.rb` and `Casks/*.rb` hold the formulae and casks. A new tap starts
  with only a `README.md` in each, which retains the directory.
- `scripts/gen_readme_packages.py` owns the generated README package table.
- `tests/` holds the unit tests for the scripts.
- `.github/workflows/` tests, bottles, publishes, and updates packages.

## Invariants

- Add formulae and casks with the `homebrew-add` skill's scaffolders, never by
  hand and never with `brew create`.
- Run `mise run generate-readme` after any formula or cask change; CI fails a
  stale catalog table.
- Keep workflows least-privileged: every workflow starts with `permissions: {}`
  and each job opts in. Write access is limited to the update, publish, and
  Cobo-sync jobs that push or open pull requests, the `zizmor` SARIF upload
  (`security-events`), and the two lint workflows' sticky PR comments
  (`pull_request_target`, which never checks out PR code). Do not rely on the
  repository's default workflow permissions.
- Never interpolate an untrusted dispatch payload directly into shell source.
- Do not manually edit `.gitignore`; it is managed by Cobo and `cobo.lock`.
- Files tracked by `.copier-answers.yml` come from the template; pull template
  changes with `copier update` instead of editing them to diverge.

## Commands

```sh
mise install
mise run check
```
