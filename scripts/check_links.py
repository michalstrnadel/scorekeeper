#!/usr/bin/env python3
"""Check internal links in git-tracked markdown files.

Both the files scanned and the link targets they may point at come from
``git ls-files`` — not the filesystem. A link that resolves locally but points
at an untracked file (e.g. the gitignored ``drafts/``) would 404 on GitHub,
and this catches exactly that.

Checked: relative file links (inline and reference-style, images included) and
GitHub-style heading anchors (``#slug``), both same-file and cross-file.
Skipped: external URLs and mailto — nondeterministic and rate-limited in CI
(lychee is the designated opt-in tool if external checking is ever wanted).

Usage: python3 scripts/check_links.py [--no-anchors]
Exit 0 when clean; exit 1 listing ``file:line: broken link -> target``.
Stdlib-only by design (repo convention: the backends are urllib-only too).
"""

from __future__ import annotations

import argparse
import posixpath
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

INLINE_LINK = re.compile(r"\[[^\]]*\]\(\s*<?([^)>\s]+)>?[^)]*\)")
REFERENCE_DEF = re.compile(r"^\s{0,3}\[[^\]]+\]:\s+<?(\S+?)>?\s*(?:\"[^\"]*\")?\s*$")
HEADING = re.compile(r"^#{1,6}\s+(.*?)\s*#*\s*$")
EXPLICIT_ANCHOR = re.compile(r"<a\s+(?:id|name)=[\"']([^\"']+)[\"']")
FENCE = re.compile(r"^(```|~~~)")
INLINE_CODE = re.compile(r"`[^`]*`")


def tracked_files() -> set[str]:
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout
    return {p for p in out.split("\0") if p}


def strip_fences(lines: list[str]) -> list[str]:
    """Blank out fenced code blocks, preserving line numbers."""
    result, in_fence = [], False
    for line in lines:
        if FENCE.match(line.strip()):
            in_fence = not in_fence
            result.append("")
        else:
            result.append("" if in_fence else line)
    return result


def slugify(heading: str) -> str:
    """GitHub's anchor algorithm, close enough for tracked docs."""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading)  # linked headings keep the label
    text = re.sub(r"[`*_]", "", text).strip().lower()
    return "".join(ch for ch in text if ch.isalnum() or ch in "- _").replace(" ", "-")


def heading_slugs(lines: list[str]) -> set[str]:
    slugs: set[str] = set()
    counts: dict[str, int] = {}
    for line in lines:
        m = HEADING.match(line)
        if m:
            base = slugify(m.group(1))
            n = counts.get(base, 0)
            counts[base] = n + 1
            slugs.add(base if n == 0 else f"{base}-{n}")
        for a in EXPLICIT_ANCHOR.finditer(line):
            slugs.add(a.group(1))
    return slugs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-anchors", action="store_true", help="skip #fragment checking")
    args = parser.parse_args()

    tracked = tracked_files()
    tracked_dirs = {""}
    for path in tracked:
        parent = posixpath.dirname(path)
        while parent and parent not in tracked_dirs:
            tracked_dirs.add(parent)
            parent = posixpath.dirname(parent)

    md_lines: dict[str, list[str]] = {}
    for path in sorted(tracked):
        if path.endswith(".md"):
            raw = (ROOT / path).read_text(encoding="utf-8").splitlines()
            md_lines[path] = strip_fences(raw)
    slug_cache: dict[str, set[str]] = {}

    def slugs_of(path: str) -> set[str]:
        if path not in slug_cache:
            slug_cache[path] = heading_slugs(md_lines[path])
        return slug_cache[path]

    broken: list[str] = []
    checked = 0
    for path, lines in md_lines.items():
        for lineno, line in enumerate(lines, start=1):
            line = INLINE_CODE.sub("", line)
            targets = [m.group(1) for m in INLINE_LINK.finditer(line)]
            ref = REFERENCE_DEF.match(line)
            if ref:
                targets.append(ref.group(1))
            for target in targets:
                if target.startswith(("http://", "https://", "mailto:", "data:")):
                    continue
                checked += 1
                where, _, fragment = target.partition("#")
                where = urllib.parse.unquote(where)
                if not where:  # same-file anchor
                    if not args.no_anchors and fragment and fragment not in slugs_of(path):
                        broken.append(f"{path}:{lineno}: broken anchor -> #{fragment}")
                    continue
                resolved = posixpath.normpath(posixpath.join(posixpath.dirname(path), where))
                if resolved not in tracked and resolved.rstrip("/") not in tracked_dirs:
                    broken.append(f"{path}:{lineno}: broken link -> {target}")
                    continue
                if (
                    not args.no_anchors
                    and fragment
                    and resolved.endswith(".md")
                    and resolved in md_lines
                    and fragment not in slugs_of(resolved)
                ):
                    broken.append(f"{path}:{lineno}: broken anchor -> {target}")

    if broken:
        print("\n".join(broken))
        print(f"\n{len(broken)} broken link(s) across {len(md_lines)} tracked markdown files")
        return 1
    print(f"OK: {checked} internal links across {len(md_lines)} tracked markdown files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
