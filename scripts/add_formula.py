#!/usr/bin/env python3
"""Scaffold a complete Homebrew formula for a PyPI package.

Resolves the full dependency tree (including chosen extras) via a ``pip --dry-run``
report, maps every dependency back to its PyPI source distribution (sdist) with a
sha256, and writes ``Formula/<name>.rb`` following this tap's conventions.

Standard library only — no third-party dependencies. See the "Adding a New Formula"
section of README.md for usage.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

PYPI = "https://pypi.org/pypi"

# Minimal SPDX mapping for the common "License :: OSI Approved :: ..." classifiers.
_LICENSE_BY_CLASSIFIER = {
    "MIT License": "MIT",
    "MIT No Attribution License (MIT-0)": "MIT-0",
    "ISC License (ISCL)": "ISC",
    "Apache Software License": "Apache-2.0",
    "BSD License": "BSD-3-Clause",
    "GNU General Public License v3 (GPLv3)": "GPL-3.0-only",
    "GNU General Public License v2 (GPLv2)": "GPL-2.0-only",
    "Mozilla Public License 2.0 (MPL 2.0)": "MPL-2.0",
}


def fetch_json(url: str) -> dict:
    """Fetch and decode a JSON document, failing loudly on HTTP errors."""
    with urllib.request.urlopen(url) as response:  # noqa: S310 - trusted PyPI host
        return json.load(response)


def pypi_release(name: str, version: str | None = None) -> dict:
    """Return the PyPI JSON payload for a package (latest release unless pinned)."""
    suffix = f"/{version}" if version else ""
    return fetch_json(f"{PYPI}/{name}{suffix}/json")


def normalize(name: str) -> str:
    """Normalize a project name to its PEP 503 form (Homebrew resource naming)."""
    return re.sub(r"[-_.]+", "-", name).lower()


def class_name(name: str) -> str:
    """Derive a Ruby class name from a package name (e.g. ``markdown-it-py``)."""
    return "".join(part.capitalize() for part in re.split(r"[-_.]+", name))


def spdx_license(info: dict) -> str:
    """Best-effort SPDX license, preferring the PEP 639 expression field."""
    expression = (info.get("license_expression") or "").strip()
    if expression:
        return expression
    for classifier in info.get("classifiers", []):
        prefix = "License :: OSI Approved :: "
        if classifier.startswith(prefix):
            label = classifier[len(prefix):]
            if label in _LICENSE_BY_CLASSIFIER:
                return _LICENSE_BY_CLASSIFIER[label]
    raw = (info.get("license") or "").strip()
    if raw and len(raw) <= 40 and "\n" not in raw:
        return raw
    return "TODO-set-SPDX-license"


def clean_desc(summary: str) -> str:
    """Format a PyPI summary as a Homebrew ``desc`` (no leading article, no period)."""
    desc = summary.strip().rstrip(".")
    return re.sub(r"^(?:A|An|The)\s+", "", desc)


def min_python(requires_python: str | None) -> str | None:
    """Extract the minimum ``3.x`` series from a ``requires_python`` spec."""
    if not requires_python:
        return None
    matches = re.findall(r">=?\s*3\.(\d+)", requires_python)
    if not matches:
        return None
    return f"3.{min(int(m) for m in matches)}"


def brew_python(series: str) -> tuple[str, str]:
    """Return the ``python@3.x`` formula name and its interpreter path.

    Falls back to the running interpreter if the brew formula is not installed,
    which is enough for ``pip --dry-run`` marker evaluation.
    """
    formula = f"python@{series}"
    try:
        prefix = subprocess.run(
            ["brew", "--prefix", formula],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        interpreter = Path(prefix) / "libexec" / "bin" / "python"
        if interpreter.exists():
            return formula, str(interpreter)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    print(f"warning: {formula} not found via brew; using {sys.executable} for "
          "dependency resolution", file=sys.stderr)
    return formula, sys.executable


def resolve_tree(interpreter: str, requirement: str) -> list[tuple[str, str]]:
    """Resolve a requirement to a flat list of ``(name, version)`` dependencies."""
    result = subprocess.run(
        [interpreter, "-m", "pip", "install", "--quiet",
         "--disable-pip-version-check", "--dry-run", "--ignore-installed",
         "--report", "-", requirement],
        capture_output=True, text=True, check=True,
    )
    report = json.loads(result.stdout)
    return [
        (item["metadata"]["name"], item["metadata"]["version"])
        for item in report["install"]
    ]


def sdist_for(name: str, version: str) -> tuple[str, str, bool]:
    """Return ``(url, sha256, is_sdist)`` for a package version, preferring the sdist."""
    payload = pypi_release(name, version)
    for entry in payload["urls"]:
        if entry["packagetype"] == "sdist":
            return entry["url"], entry["digests"]["sha256"], True
    # Wheel-only release: fall back to the first wheel so the formula still resolves.
    entry = payload["urls"][0]
    return entry["url"], entry["digests"]["sha256"], False


def render(name: str, info: dict, sdist_url: str, sdist_sha: str,
           python_formula: str, resources: list[tuple[str, str, str]]) -> str:
    """Render the Ruby formula source."""
    homepage = (info.get("project_urls") or {}).get("Homepage") \
        or info.get("home_page") or f"https://pypi.org/project/{name}/"
    lines = [
        f"class {class_name(name)} < Formula",
        "  include Language::Python::Virtualenv",
        "",
        f'  desc "{clean_desc(info["summary"])}"',
        f'  homepage "{homepage}"',
        f'  url "{sdist_url}"',
        f'  sha256 "{sdist_sha}"',
        f'  license "{spdx_license(info)}"',
        "",
        "  livecheck do",
        "    url :stable",
        "    strategy :pypi",
        "  end",
        "",
        f'  depends_on "{python_formula}"',
        "",
    ]
    for res_name, url, sha in resources:
        lines += [
            f'  resource "{res_name}" do',
            f'    url "{url}"',
            f'    sha256 "{sha}"',
            "  end",
            "",
        ]
    lines += [
        "  def install",
        "    virtualenv_install_with_resources",
        "  end",
        "",
        "  test do",
        f'    assert_match version.to_s, shell_output("#{{bin}}/{name} --version")',
        "  end",
        "end",
        "",
    ]
    return "\n".join(lines)


def run_checks(repo: Path, name: str, tap: str) -> None:
    """Copy the formula into the active tap and run audit, install, and test."""
    user, _, short = tap.partition("/")
    brew_repo = subprocess.run(
        ["brew", "--repository"], capture_output=True, text=True, check=True,
    ).stdout.strip()
    tap_formula = Path(brew_repo) / "Library" / "Taps" / user / \
        f"homebrew-{short}" / "Formula" / f"{name}.rb"
    if not tap_formula.parent.is_dir():
        sys.exit(f"error: tap '{tap}' is not tapped at {tap_formula.parent}; run "
                 f"`brew tap {tap} {repo}` first")
    shutil.copy(repo / "Formula" / f"{name}.rb", tap_formula)
    ref = f"{tap}/{name}"
    try:
        for cmd in (
            ["brew", "audit", "--strict", "--online", ref],
            ["brew", "install", "--build-from-source", ref],
            ["brew", "test", ref],
        ):
            print(f"\n==> {' '.join(cmd)}")
            subprocess.run(cmd, check=True)
    finally:
        tap_formula.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("package", help="PyPI package name")
    parser.add_argument("--extras", default="",
                        help="comma-separated extras to include (e.g. 'tui')")
    parser.add_argument("--version", help="package version (default: latest on PyPI)")
    parser.add_argument("--python",
                        help="override python formula (e.g. 'python@3.13')")
    parser.add_argument("--check", action="store_true",
                        help="audit, build-from-source, and test the result")
    parser.add_argument("--tap", default="hasansezertasan/tap",
                        help="tap name used by --check")
    args = parser.parse_args()

    release = pypi_release(args.package, args.version)
    info = release["info"]
    name = normalize(info["name"])
    version = info["version"]
    sdist_url, sdist_sha, ok = sdist_for(info["name"], version)
    if not ok:
        print(f"warning: {name} {version} has no sdist; using a wheel URL",
              file=sys.stderr)

    series = min_python(info.get("requires_python"))
    if args.python:
        python_formula, interpreter = args.python, brew_python(
            args.python.split("@", 1)[1])[1]
    elif series:
        python_formula, interpreter = brew_python(series)
    else:
        sys.exit("error: could not infer Python version; pass --python python@3.x")

    requirement = f"{args.package}=={version}"
    if args.extras:
        requirement = f"{args.package}[{args.extras}]=={version}"
    print(f"==> Resolving {requirement} with {interpreter}")

    resources: list[tuple[str, str, str]] = []
    for dep_name, dep_version in resolve_tree(interpreter, requirement):
        if normalize(dep_name) == name:
            continue
        url, sha, dep_ok = sdist_for(dep_name, dep_version)
        if not dep_ok:
            print(f"warning: {dep_name} {dep_version} has no sdist; using a wheel",
                  file=sys.stderr)
        resources.append((normalize(dep_name), url, sha))
    resources.sort(key=lambda r: r[0])

    repo = Path(__file__).resolve().parent.parent
    out = repo / "Formula" / f"{name}.rb"
    out.write_text(render(name, info, sdist_url, sdist_sha, python_formula, resources))
    print(f"==> Wrote {out.relative_to(repo)} "
          f"({len(resources)} resources, {python_formula})")

    if args.check:
        run_checks(repo, name, args.tap)
    else:
        print(f"\nNext: brew audit --strict --online {args.tap}/{name}  "
              "(or re-run with --check)")


if __name__ == "__main__":
    main()
