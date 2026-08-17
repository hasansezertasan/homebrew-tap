---
status: accepted
date: 2026-08-17
decision-makers: [hasansezertasan]
consulted: []
informed: []
---

# Do not adopt Renovate's Homebrew manager for dependency updates

## Context and Problem Statement

This tap packages third-party PyPI Python CLIs as Homebrew formulae (each with
many pinned Python `resource` blocks) and prebuilt macOS apps as casks (`.dmg`).
Version bumps are currently automated by `brew`-native GitHub Actions workflows
(`update-formulas.yml`, `update-casks.yml`, plus the `repository_dispatch`
receivers). [Renovate](https://docs.renovatebot.com/modules/manager/homebrew/)
offers a dedicated Homebrew manager. Should we replace or supplement the custom
workflows with Renovate's Homebrew manager?

## Decision Drivers

* Updates must rewrite the main `url` **and** `sha256`.
* Updates must regenerate Python `resource` blocks (the deep, per-package
  dependency tree), resolved on macOS so platform-specific backends stay correct.
* Casks (`.dmg`) must be bumpable too.
* Bumps must be verifiable (`brew audit`) since `GITHUB_TOKEN` PRs don't trigger
  `tests.yml`.

## Considered Options

* **Option A — Keep the `brew`-native workflows** (`brew livecheck` +
  `brew bump-formula-pr` + `brew update-python-resources` + `brew bump-cask-pr`).
* **Option B — Adopt Renovate's Homebrew manager** (replace or supplement).

## Decision Outcome

Chosen option: **Option A (keep the `brew`-native workflows)**, because
Renovate's Homebrew manager cannot handle the shape of this tap and would either
do nothing or produce partial/broken bumps.

Renovate's Homebrew manager only detects **GitHub release/archive** and
**npmjs.org** URLs, and explicitly does **not** touch Python `resource` blocks or
casks. This tap's formulae all use **PyPI source URLs**
(`files.pythonhosted.org/...`) as their main `url` and rely heavily on resource
blocks; the sole cask (`keycast`) is out of scope entirely. No current item
qualifies as a Renovate candidate.

### Consequences

* Good, because version discovery, macOS-correct resource resolution, and
  inline audit/revert all remain in one `brew`-native place.
* Good, because casks and the `repository_dispatch` immediate-update path keep
  working unchanged.
* Bad, because we maintain custom workflow YAML rather than a single
  off-the-shelf tool.
* Neutral, because this decision is scoped to the **Homebrew manager only** — it
  does not preclude adopting Renovate (or Dependabot) for a genuine gap the
  current workflows don't cover: pinned GitHub Actions SHAs (see below).

### Confirmation

Verified by inspecting every file in `Formula/` and `Casks/`: all formula main
`url`s point at `files.pythonhosted.org` (not GitHub/NPM), every formula carries
`resource` blocks, and `keycast` is a cask. All three fall outside Renovate's
Homebrew manager support matrix.

## Pros and Cons of the Options

### Option A — Keep the `brew`-native workflows

* Good, because `brew update-python-resources` regenerates the full resource
  tree — the hardest, highest-value part of an update.
* Good, because resolution runs on a macOS runner, keeping platform-specific
  backends correct (e.g. `pynput`'s pyobjc frameworks vs. a Linux resolve
  swapping in evdev + python-xlib).
* Good, because bumps are verified inline with `brew audit` and reverted on
  failure, compensating for `GITHUB_TOKEN` PRs not triggering `tests.yml`.
* Good, because casks are covered by the parallel cask workflows + dispatch path.
* Bad, because it is bespoke YAML we own and maintain.

### Option B — Adopt Renovate's Homebrew manager

* Bad, because it only recognizes GitHub/NPM URLs — this tap's PyPI-sourced
  formulae are invisible to it and would be skipped.
* Bad, because it explicitly does not update Python `resource` blocks, so any
  bump it *could* make would leave stale, mismatched dependencies.
* Bad, because casks are unsupported.
* Neutral, because it computes `sha256` for new versions — irrelevant here given
  the above.

## More Information

Renovate's **`github-actions` manager** (a different manager from the Homebrew
one) *is* a real potential improvement: it can keep pinned action SHAs current
(e.g. `actions/checkout`, `peter-evans/create-pull-request`), which the current
workflows do not automate. That is out of scope for this decision and can be
evaluated separately.
