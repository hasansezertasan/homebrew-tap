# My Tap (Third-Party Repositories)

## How do I install these formulae?

`brew install hasansezertasan/tap/<formula>`

Or `brew tap hasansezertasan/tap` and then `brew install <formula>`.

Or, in a `brew bundle` `Brewfile`:

```ruby
tap "hasansezertasan/tap"
brew "<formula>"
```

> **Note on `keycast`:** it ships as **both** a formula (the Python CLI, macOS
> only) and a cask (the prebuilt `.app`), so `brew install keycast` is ambiguous.
> Disambiguate explicitly:
>
> - `brew install --formula hasansezertasan/tap/keycast` — the command-line tool
> - `brew install --cask hasansezertasan/tap/keycast` — the GUI app bundle

## Automated Formula Updates

This tap uses two complementary workflows to keep formulas up-to-date:

### Scheduled Updates (`update-formulas.yml`)

A "pull" model that periodically checks for new versions.

- **Runs:** Weekly on Mondays at 9:00 UTC, or manually via GitHub Actions
- **How it works:**
  1. Lists all formulas in `Formula/`
  2. Runs `brew livecheck` on each to check PyPI for newer versions
  3. Updates version/sha256 with `brew bump-formula-pr`
  4. Updates Python dependencies with `brew update-python-resources`
  5. Creates a single PR with all updates

### Event-Driven Updates (`update-formula-dispatch.yml`)

A "push" model where package repos notify the tap immediately after publishing.

- **Runs:** When a package repo sends a `repository_dispatch` event
- **How it works:**
  1. Receives payload with `formula` name and optionally `version`
  2. Validates the formula exists
  3. Updates the formula and creates a PR

#### Triggering from Package Repos

Package repos can trigger immediate formula updates after PyPI publish.

<details>
<summary><strong>For Humans</strong></summary>

##### Option A: Let an LLM do it

Copy and paste this prompt into your AI coding assistant:

> Set up automatic Homebrew formula updates for this repository.
> Follow the instructions at: https://github.com/hasansezertasan/homebrew-tap#triggering-from-package-repos

##### Option B: Manual Setup

1. Create a **fine-grained** PAT scoped to this tap repo with **Contents: write**
   (the only permission `POST /repos/.../dispatches` requires — the tap opens
   the PR with its own `GITHUB_TOKEN`, so Pull requests: write is *not* needed)
2. Add it as `HOMEBREW_TAP_TOKEN` secret in the package repo
3. Copy the workflow below to your package repo at `.github/workflows/update-homebrew-formula.yml`

```yaml
# Triggers Homebrew formula update after a release is published
name: Update Homebrew Formula
on:
  # Trigger after release is published
  release:
    types: [published]
  # Or trigger manually
  workflow_dispatch:
jobs:
  update-formula:
    name: Trigger formula update
    runs-on: ubuntu-latest
    # Only run if the release workflow (PyPI publish) succeeded
    # Uncomment if you want to wait for another workflow
    # needs: [publish]
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

</details>

<details>
<summary><strong>For LLM Agents</strong></summary>

**Prerequisites:**

- A GitHub fine-grained PAT scoped to the tap repo with **Contents: write**
  (not the broad classic `repo` scope; Pull requests: write is not needed),
  stored as `HOMEBREW_TAP_TOKEN` in the repository secrets

**Instructions:**

1. Create `.github/workflows/update-homebrew-formula.yml` with this content:

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

2. Verify the file exists and has correct YAML syntax

**Important:**

- `formula` in the payload should match the repository name (e.g., "micoo" for micoo repo)
- `version` is extracted from the release tag (e.g., "v1.0.0" or "1.0.0")
- The workflow triggers on `release: published` events

</details>

### Flow

```
[package repo]                  [homebrew-tap]
     │                               │
     │ Release published             │
     ▼                               │
  repository_dispatch ──────────────►│
  (formula, version)                 ▼
                           update-formula-dispatch.yml
                                     │
                                     ▼
                                Creates PR
```

## Adding a New Formula

Use the `add-formula` helper to scaffold a complete, fully-resourced formula from a
PyPI package in one command. It resolves the entire dependency tree, pins every
resource to an sdist + sha256, and writes `Formula/<name>.rb` following this tap's
conventions.

```bash
# Core install only
mise run add-formula <package>

# Include optional extras (pin them up front to avoid a second build)
mise run add-formula <package> --extras tui

# Also audit, build-from-source, and smoke-test the result
mise run add-formula <package> --extras tui --check
```

Or call the script directly:

```bash
python3 scripts/add_formula.py <package> [--extras a,b] [--python python@3.13] \
    [--version X.Y.Z] [--check]
```

What it does:

1. Fetches the package's PyPI metadata (latest version, sdist URL + sha256, license,
   `requires_python`).
2. Picks a `python@3.x` dependency from `requires_python` (override with `--python`).
3. Resolves the full dependency tree — including the chosen `--extras` — via a
   `pip --dry-run` report against the target interpreter, then maps every dependency
   back to its PyPI **sdist** (source tarball, as Homebrew prefers) with sha256.
4. Writes `Formula/<name>.rb` with `desc`, `homepage`, `license`, a `livecheck`
   block, the `python@3.x` dependency, alphabetically-ordered `resource` blocks, and
   a `--version` smoke test.
5. With `--check`: copies the formula into the active tap, runs
   `brew audit --strict --online`, `brew install --build-from-source`, and `brew test`.

Notes:

- **Pin extras up front.** Discovering a missing extra later forces a second
  build-from-source. Decide the feature set before running.
- The generated `test do` block assumes the CLI supports `--version`. Verify against
  the package's CLI and adjust if needed.
- `--check` builds every dependency from source and is network-bound; omit it for a
  fast scaffold and let CI (`tests.yml`) build bottles instead.

## Adding a New Cask

Use the `add-cask` helper to scaffold a cask for a prebuilt macOS app (a `.dmg`,
`.pkg`, or `.zip` on GitHub Releases). Casks ship a pre-built app, so — unlike a
formula — there are no Python resources to resolve.

```bash
# From the latest GitHub release (downloads the artifact to compute sha256)
GITHUB_TOKEN=$(gh auth token) mise run add-cask owner/repo

# Seed a placeholder before the first release exists (the first
# `brew bump-cask-pr` fills in the real version and sha256)
mise run add-cask owner/repo --seed
```

Or call the script directly:

```bash
python3 scripts/add_cask.py owner/repo [--artifact NAME.dmg] [--name token] [--seed]
```

What it does:

1. Reads the repo metadata and its latest release from the GitHub API (set
   `GITHUB_TOKEN` to avoid rate limits).
2. Picks a `.dmg`/`.pkg`/`.zip` asset (override with `--artifact`), downloads it, and
   computes its sha256.
3. Writes `Casks/<name>.rb` with a version-templated download URL, a `github_latest`
   `livecheck` block, `depends_on :macos`, and an `app`/`pkg` stanza.

Notes:

- **Verify the `app "<name>.app"` stanza.** The `.app` name inside a `.dmg` is a guess;
  confirm the real bundle name.
- If `brew audit --online` reports the cask's macOS floor is higher than the bundle's
  `LSMinimumSystemVersion`, pin it explicitly (e.g. `depends_on macos: :big_sur`).
- Add a `caveats` block if the app needs permissions or Gatekeeper approval.

Audit with `brew audit --cask --strict --online hasansezertasan/tap/<name>`.

## Documentation

`brew help`, `man brew` or check [Homebrew's documentation](https://docs.brew.sh).
