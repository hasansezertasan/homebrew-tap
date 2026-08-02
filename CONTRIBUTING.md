# Contributing

Thanks for your interest in contributing! This tap distributes the projects and
tools hasansezertasan maintains to macOS/Linux users via [Homebrew](https://brew.sh),
mirroring the [Scoop bucket](https://github.com/hasansezertasan/scoop-bucket). It
carries two kinds of item:

- **Formula** — `Formula/*.rb`: a Python CLI from PyPI, installed into a virtualenv
  with its full dependency tree pinned to sdists. Mirrors the bucket's uv/pipx shim.
- **Cask** — `Casks/*.rb`: a prebuilt macOS app (`.dmg`/`.pkg`/`.zip`) downloaded from
  GitHub Releases. Mirrors the bucket's binary manifest.

Most changes are automated version bumps (see [Updating a version](#updating-a-version)).
Manual contributions are usually fixes to a formula/cask or a workflow.

## Adding a formula or cask

Scaffold with the helper scripts instead of hand-writing resource blocks or running
`brew create` (it writes into homebrew-core, the wrong place). Route by **what
upstream ships**:

| Upstream artifact | Kind | Command |
|---|---|---|
| A Python CLI on PyPI (`pip install`) | **formula** | `mise run add-formula <package>` |
| A prebuilt macOS `.dmg`/`.pkg`/`.zip` on GitHub Releases | **cask** | `mise run add-cask <owner/repo>` |
| **Both** — a Python CLI *and* a prebuilt app (the `keycast` pattern) | both | both commands |

```bash
# formula: resolves the full dependency tree to sdists + sha256s
mise run add-formula cobo
mise run add-formula <package> --extras tui --check   # pin extras; audit+build+test

# cask: downloads the artifact to hash it, writes a version-templated URL
GITHUB_TOKEN=$(gh auth token) mise run add-cask owner/repo
mise run add-cask owner/repo --seed                   # no release yet: placeholder
```

The scripts fill in metadata, the `livecheck` block, and (for a formula) the
`resource` blocks. Then verify the touch-ups they **can't** infer — system
(non-Python) `depends_on`, the `test do` command, the guessed cask `.app` name, a
raised macOS floor. The README's [Adding a New Formula](README.md#adding-a-new-formula)
and [Adding a New Cask](README.md#adding-a-new-cask) sections and the `homebrew-add`
skill cover the details.

## Testing locally

```bash
brew audit --strict --online hasansezertasan/tap/<name>   # formula
brew audit --cask --strict --online hasansezertasan/tap/<name>   # cask
brew install hasansezertasan/tap/<name>
brew test hasansezertasan/tap/<name>
```

The stdlib scaffolder scripts also have unit tests:

```bash
python3 -m unittest discover -s tests -v
```

- **One formula or cask per PR** (a "ships both" addition may add its formula and
  cask together, since they're one logical package).
- **Never push straight to `main`** — always via PR. Use Conventional Branch names
  (`feat-<name>-formula`) and Conventional Commit titles (`feat: add <name> formula`).

## Updating a version

You normally don't have to: `brew livecheck` + `brew bump-formula-pr` /
`brew bump-cask-pr` run automatically from the `update-formulas.yml` /
`update-casks.yml` (weekly cron + manual) and `update-formula-dispatch.yml` /
`update-cask-dispatch.yml` (fired by a package's release pipeline) workflows, which
open a PR with the bump.

Producer repos only **signal**: they fire a `repository_dispatch` and never write
to the tap or open the PR themselves — the tap does the bump and opens the PR with
its own `GITHUB_TOKEN`. A producer's `TAP_TOKEN` therefore needs only **Contents:
write** (not Pull requests: write).

To do it by hand: `brew bump-formula-pr --version=<v> <name>` (or `bump-cask-pr`),
then open a PR. CI audits and builds the change.

See [`CLAUDE.md`](CLAUDE.md) for the full architecture notes.

## Questions?

Open an issue on this repository, or on the relevant package repo.
