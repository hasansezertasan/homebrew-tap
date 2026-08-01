#!/usr/bin/env python3
"""Scaffold a Homebrew cask for a prebuilt macOS app from a GitHub release.

Reads a GitHub repo's latest release, picks a distributable artifact (``.dmg`` /
``.pkg`` / ``.zip``), computes its sha256, and writes ``Casks/<name>.rb`` following
this tap's conventions (version-templated download URL, ``github_latest`` livecheck,
an ``app``/``pkg`` stanza). Casks ship a pre-built app, so — unlike a formula —
there are no Python resources to resolve.

Standard library only — no third-party dependencies. Companion to
``add_formula.py``. See the "Adding a New Cask" section of README.md for usage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

GITHUB_API = "https://api.github.com"

# Artifact preference order when --artifact isn't given. A .dmg or .zip carries a
# .app bundle (`app` stanza); a .pkg is an installer (`pkg` stanza).
_ARTIFACT_PREFERENCE = (".dmg", ".pkg", ".zip")

# 64 zero hex digits: a syntactically valid placeholder sha256 for --seed mode.
# `brew bump-cask-pr` overwrites it (and the version) on the first real release.
_PLACEHOLDER_SHA = "0" * 64
_PLACEHOLDER_VERSION = "0.0.0"


def _request(url: str, *, accept: str = "application/vnd.github+json") -> urllib.request.Request:
    """Build a GitHub API request, authenticating from the environment if possible."""
    req = urllib.request.Request(url)
    req.add_header("Accept", accept)
    req.add_header("User-Agent", "homebrew-tap-add-cask")
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    return req


def fetch_json(url: str) -> dict:
    """Fetch and decode a JSON document from the GitHub API, failing loudly."""
    with urllib.request.urlopen(_request(url)) as response:  # noqa: S310 - trusted host
        return json.load(response)


def normalize(name: str) -> str:
    """Normalize a repo name to its cask token (lowercase, hyphen-separated)."""
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_repo(ref: str) -> tuple[str, str]:
    """Parse ``owner/repo`` or a GitHub URL into an ``(owner, repo)`` pair."""
    match = re.search(r"github\.com[/:]([^/]+)/([^/#?]+)", ref)
    if match:
        owner, repo = match.group(1), match.group(2)
    elif "/" in ref and ref.count("/") == 1:
        owner, repo = ref.split("/", 1)
    else:
        sys.exit(f"error: cannot parse GitHub repo from {ref!r}; pass 'owner/repo' "
                 "or a github.com URL")
    return owner, repo.removesuffix(".git")


def clean_desc(summary: str) -> str:
    """Format a repo description as a Homebrew ``desc``.

    Strips a leading article and trailing period, then capitalizes the first letter
    (``brew audit --strict`` requires a ``desc`` that starts with a capital).
    """
    desc = re.sub(r"^(?:A|An|The)\s+", "", (summary or "").strip().rstrip("."))
    return desc[:1].upper() + desc[1:] if desc else desc


def select_asset(assets: list[dict], wanted: str | None) -> dict:
    """Pick the release asset to package, honoring --artifact or the preference order."""
    if not assets:
        sys.exit("error: the latest release has no downloadable assets; pass --seed "
                 "to scaffold a placeholder, or --artifact once a release exists")
    if wanted:
        for asset in assets:
            if asset["name"] == wanted:
                return asset
        names = ", ".join(a["name"] for a in assets)
        sys.exit(f"error: no asset named {wanted!r}; available: {names}")
    for suffix in _ARTIFACT_PREFERENCE:
        for asset in assets:
            if asset["name"].endswith(suffix):
                return asset
    sys.exit("error: no .dmg/.pkg/.zip asset found; pass --artifact to choose one of: "
             + ", ".join(a["name"] for a in assets))


def sha256_of(url: str) -> str:
    """Download a release asset and return its sha256, streaming to bounded memory."""
    print(f"==> Downloading {url} to compute sha256", file=sys.stderr)
    digest = hashlib.sha256()
    with urllib.request.urlopen(_request(url, accept="application/octet-stream")) as response:  # noqa: S310
        for chunk in iter(lambda: response.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def templatize(text: str, version: str) -> str:
    """Replace literal occurrences of the version in a URL/filename with ``#{version}``."""
    return text.replace(version, "#{version}") if version else text


def stanza_for(artifact: str, token: str) -> tuple[str, str]:
    """Return the artifact stanza line and a verify-hint for the given asset.

    A ``.pkg`` installs via a ``pkg`` stanza. A ``.dmg``/``.zip`` carries a ``.app``
    bundle whose real name we can't know without mounting it, so we guess
    ``<token>.app`` and flag it for manual verification.
    """
    if artifact.endswith(".pkg"):
        return f'  pkg "{artifact}"', ""
    return (f'  app "{token}.app"',
            f'the .app name inside {artifact} is a guess ("{token}.app") — verify it')


def render(token: str, owner: str, repo: str, version: str, sha: str,
           url_template: str, desc: str, homepage: str, stanza: str) -> str:
    """Render the Ruby cask source."""
    return "\n".join([
        f'cask "{token}" do',
        f'  version "{version}"',
        f'  sha256 "{sha}"',
        "",
        f'  url "{url_template}"',
        f'  name "{repo}"',
        f'  desc "{desc}"',
        f'  homepage "{homepage}"',
        "",
        "  livecheck do",
        "    url :url",
        "    strategy :github_latest",
        "  end",
        "",
        "  # This app is macOS-only. If `brew audit --online` reports the cask's",
        "  # macOS floor is higher than the bundle's LSMinimumSystemVersion, pin it",
        "  # explicitly to match, e.g. `depends_on macos: :big_sur`.",
        "  depends_on :macos",
        "",
        stanza,
        "end",
        "",
    ])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("repo", help="GitHub repo as 'owner/repo' or a github.com URL")
    parser.add_argument("--artifact",
                        help="release asset filename to package (default: first "
                             ".dmg/.pkg/.zip)")
    parser.add_argument("--name",
                        help="override the cask token (default: normalized repo name)")
    parser.add_argument("--seed", action="store_true",
                        help="write a placeholder cask (version/sha256 filled by the "
                             "first `brew bump-cask-pr`) without downloading anything")
    args = parser.parse_args()

    owner, repo = parse_repo(args.repo)
    token = normalize(args.name or repo)
    meta = fetch_json(f"{GITHUB_API}/repos/{owner}/{repo}")
    desc = clean_desc(meta.get("description") or "TODO-set-description")
    homepage = meta.get("html_url") or f"https://github.com/{owner}/{repo}"

    if args.seed:
        # No release required: template a plausible URL the first bump will correct.
        artifact = args.artifact or f"{token}.dmg"
        version, sha = _PLACEHOLDER_VERSION, _PLACEHOLDER_SHA
        url_template = (f"https://github.com/{owner}/{repo}/releases/download/"
                        f"v#{{version}}/{artifact}")
        print(f"==> Seeding placeholder cask (version {version}); the first "
              "`brew bump-cask-pr` fills real values", file=sys.stderr)
    else:
        try:
            release = fetch_json(f"{GITHUB_API}/repos/{owner}/{repo}/releases/latest")
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                sys.exit(f"error: {owner}/{repo} has no published (non-draft, "
                         "non-prerelease) 'latest' release; use --seed to scaffold "
                         "a placeholder for the first release to fill in")
            raise
        tag = release["tag_name"]
        version = tag[1:] if re.fullmatch(r"v\d.*", tag) else tag
        asset = select_asset(release.get("assets", []), args.artifact)
        artifact = asset["name"]
        sha = sha256_of(asset["browser_download_url"])
        # Rebuild the URL from the tag + filename, templated on the version so
        # `brew bump-cask-pr` (and livecheck) can bump it in place.
        url_template = (f"https://github.com/{owner}/{repo}/releases/download/"
                        f"{templatize(tag, version)}/{templatize(artifact, version)}")

    stanza, hint = stanza_for(artifact, token)

    repo_root = Path(__file__).resolve().parent.parent
    out = repo_root / "Casks" / f"{token}.rb"
    out.parent.mkdir(exist_ok=True)
    out.write_text(render(token, owner, repo, version, sha, url_template, desc,
                          homepage, stanza))
    print(f"==> Wrote {out.relative_to(repo_root)} (version {version})")
    if hint:
        print(f"warning: {hint}", file=sys.stderr)
    print(f"\nNext: brew audit --cask --strict --online hasansezertasan/tap/{token}")


if __name__ == "__main__":
    main()
