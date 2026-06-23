# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a **Homebrew Tap** for Hasan Sezer Taşan's projects. It contains Ruby formula files that define how Homebrew installs third-party Python packages not available in the official Homebrew core.

## Common Commands

```bash
# Lint a formula for style and syntax issues
brew audit --strict --online <formula>  # Use formula name, not path!

# Test formula syntax only
brew test-bot --only-tap-syntax

# Tap local directory for testing
brew tap hasansezertasan/tap /Users/hasansezertasan/Developer/projects/hasansezertasan-homebrew-tap

# Install a formula locally for testing
brew install hasansezertasan/tap/<formula>

# Run formula tests
brew test <formula>

# Uninstall a formula
brew uninstall <formula>

# Check for available updates (requires livecheck block in formula)
brew livecheck <formula>

# Update a formula to a new version
brew bump-formula-pr --version=<version> <formula>

# Update Python resource blocks automatically
brew update-python-resources Formula/<formula>.rb
```

## Formula Structure

Formulas are Ruby classes in `Formula/`. For Python packages using virtualenv:

1. **Metadata**: `desc`, `homepage`, `url`, `sha256`, `license`
2. **Livecheck**: Add a `livecheck do` block with `strategy :pypi` for automatic version checking
3. **Dependencies**: Use `depends_on "python@3.x"` for Python version
4. **Resources**: Each Python dependency needs a separate `resource` block with PyPI source URL and sha256
5. **Install**: Use `virtualenv_install_with_resources` for Python packages
6. **Test**: Define a basic smoke test in the `test do` block

## Adding a New Formula

**Recommended: Use automated workflow below.** Manual formula creation is error-prone and time-consuming.

### Automated Workflow (Recommended)

```bash
# Step 1: Get the PyPI package URL
# Visit https://pypi.org/project/<package-name>/#files
# Copy the source distribution (.tar.gz) URL

# Step 2: Create formula with brew create
brew create https://files.pythonhosted.org/packages/.../package-x.y.z.tar.gz --python
# This auto-generates the formula in homebrew-core but with all dependencies detected

# Step 3: The formula needs manual completion in your tap
# brew create puts it in the wrong location, so you'll need to:
# - Copy metadata (desc, homepage, license) from the package's PyPI/GitHub page
# - Add livecheck block for auto-updates
# - Fix Python version if needed (prefer python@3.14, the current default)
# - Add build dependencies if needed (e.g., Rust for pydantic-core)
# - Write a proper test command (check package help for correct flags)
```

### Complete Example (from recent micoo formula)

```bash
# 1. Create formula from PyPI (auto-detects all Python dependencies)
brew create https://files.pythonhosted.org/packages/.../micoo-0.4.0.tar.gz --python

# 2. Create Formula/micoo.rb in your tap with:
# - desc: "Easy access to mise-cookbooks"
# - homepage: "https://github.com/hasansezertasan/micoo"
# - license: "MIT"
# - livecheck block with strategy :pypi
# - depends_on "rust" => :build  (if package uses pydantic-core or other Rust deps)
# - depends_on "python@3.14"  (current default Python)
# - All resource blocks from brew create
# - test do: system bin/"micoo", "version"  (NOT --version!)

# 3. Validate the formula
brew audit --strict --online micoo  # Use formula name, not path

# 4. Test installation locally
# First, tap your local directory:
brew untap hasansezertasan/tap 2>/dev/null
brew tap hasansezertasan/tap /Users/hasansezertasan/Developer/projects/hasansezertasan-homebrew-tap
# Then install:
brew install hasansezertasan/tap/micoo

# 5. Run tests
brew test micoo
```

### Key Learnings & Gotchas

1. **brew create location**: Creates formula in homebrew-core, not your tap. You need to copy/adapt it.
2. **Python version**: Use `python@3.14` (current default). Newer interpreters may lack binary wheels for some deps, forcing source builds — sccache/Cargo caching (see tests.yml) keeps Rust-heavy builds like `pydantic-core` fast across runs.
3. **Rust dependency**: Packages using `pydantic-core` need `depends_on "rust" => :build`.
4. **Test commands**: Not all packages support `--version`. Check the package's CLI help first.
5. **Audit syntax**: Use `brew audit --strict --online <formula-name>` not the file path.
6. **Dependency order**: Build dependencies (like Rust) must come before runtime dependencies.
7. **Livecheck**: `brew create` doesn't add livecheck - you must add it manually for auto-updates.

### Manual Workflow (Not Recommended)

Only use if automated workflow fails:

1. Create `Formula/<name>.rb` following existing pattern
2. Get source tarball URL from PyPI (prefer `.tar.gz` over wheels)
3. Calculate sha256: `curl -L <url> | shasum -a 256`
4. Add livecheck block with `strategy :pypi`
5. Manually add resource blocks for all dependencies (tedious!)
6. Run `brew audit --strict --online <formula-name>` to validate

## CI/CD Workflows

- **tests.yml**: Two jobs — `syntax` (Ubuntu, runs `--only-tap-syntax` on every PR/push touching `Formula/**` or this workflow) and `formulae` (macos-26, builds bottles for non-draft PRs, gated on `syntax`). Uses sccache + Cargo registry caching for Rust-heavy Python deps (`pydantic-core` etc.).
- **publish.yml**: Pulls bottles when PR has `pr-pull` label and pushes to main
- **update-formulas.yml**: Uses `brew livecheck` to check for updates weekly, creates PRs using `brew bump-formula-pr` and `brew update-python-resources`
- **update-formula-dispatch.yml**: Receives `repository_dispatch` events from package repos to trigger immediate updates

## Triggering Updates from Package Repos

Package repos can trigger immediate formula updates after PyPI publish using `repository_dispatch`. See the "Triggering from Package Repos" section in README.md for the workflow template and setup instructions.
