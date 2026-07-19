#!/usr/bin/env python3
"""Scan public release surfaces for likely secrets, identifiers, and local data."""
from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path
from typing import Iterable

PATTERNS = {
    "discord_snowflake": re.compile(r"(?<![A-Za-z0-9])\d{17,20}(?![A-Za-z0-9])"),
    "email_address": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    "private_ipv4": re.compile(r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b"),
    "linux_home_path": re.compile(r"/home/(?!user(?:/|\b)|runner(?:/|\b)|USERNAME(?:/|\b)|YOUR_USER(?:/|\b))[A-Za-z0-9._-]+/"),
    "mac_home_path": re.compile(r"/Users/(?!USERNAME(?:/|\b)|YOUR_USER(?:/|\b))[A-Za-z0-9._-]+/"),
    "private_key": re.compile(r"BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY"),
    "credential_assignment": re.compile(
        r"(?im)(?:\b[A-Z][A-Z0-9_]*(?:TOKEN|API_KEY|PASSWORD|SECRET)\s*=\s*['\"]?[A-Za-z0-9_./:+-]+|^\s*(?:api[_-]?key|token|password|secret)\s*:\s*['\"]?(?!(?:str|int|float|bool|Any|Optional)\b)[A-Za-z0-9_./:+-]+)"
    ),
}
PLACEHOLDER_WORDS = ("redacted", "placeholder", "example", "your_", "your-", "changeme", "dummy")


def git_bytes(repo: Path, *args: str) -> bytes:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=True)
    return result.stdout


def git_text(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=True, text=True)
    return result.stdout


def is_placeholder(match: re.Match[str]) -> bool:
    value = match.group(0).lower()
    return any(word in value for word in PLACEHOLDER_WORDS)


def scan_blob(surface: str, label: str, data: bytes, operator_patterns: list[str]) -> list[tuple[str, str, str, int]]:
    if b"\x00" in data[:4096]:
        return []
    text = data.decode("utf-8", errors="replace")
    findings: list[tuple[str, str, str, int]] = []
    for name, pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            if name == "credential_assignment" and is_placeholder(match):
                continue
            findings.append((surface, label, name, text.count("\n", 0, match.start()) + 1))
    lowered = text.lower()
    for item in operator_patterns:
        start = 0
        needle = item.lower()
        while needle and (index := lowered.find(needle, start)) >= 0:
            findings.append((surface, label, "operator_pattern", text.count("\n", 0, index) + 1))
            start = index + len(needle)
    return findings


def working_blobs(repo: Path) -> Iterable[tuple[str, bytes]]:
    paths = git_bytes(repo, "ls-files", "-co", "--exclude-standard", "-z").split(b"\0")
    for raw in paths:
        if not raw:
            continue
        rel = raw.decode("utf-8", errors="replace")
        path = repo / rel
        if path.is_file():
            yield rel, path.read_bytes()


def index_blobs(repo: Path) -> Iterable[tuple[str, bytes]]:
    entries = git_bytes(repo, "ls-files", "-s", "-z").split(b"\0")
    seen: set[str] = set()
    for raw in entries:
        if not raw or b"\t" not in raw:
            continue
        meta, path_raw = raw.split(b"\t", 1)
        parts = meta.split()
        if len(parts) < 3 or parts[2] != b"0":
            continue
        oid = parts[1].decode()
        if oid in seen:
            continue
        seen.add(oid)
        yield path_raw.decode("utf-8", errors="replace"), git_bytes(repo, "cat-file", "-p", oid)


def history_blobs(repo: Path) -> Iterable[tuple[str, bytes]]:
    rows = git_text(repo, "rev-list", "--objects", "--all").splitlines()
    seen: set[str] = set()
    for row in rows:
        oid, _, label = row.partition(" ")
        if oid in seen:
            continue
        seen.add(oid)
        obj_type = git_text(repo, "cat-file", "-t", oid).strip()
        if obj_type != "blob":
            continue
        yield label or oid[:12], git_bytes(repo, "cat-file", "-p", oid)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--surface", choices=("working", "index", "history", "all"), default="all")
    parser.add_argument("--patterns-file", help="Optional ignored local file containing one literal private pattern per line")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    operator_patterns: list[str] = []
    if args.patterns_file:
        pattern_path = Path(args.patterns_file).expanduser()
        operator_patterns = [line.strip() for line in pattern_path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith("#")]

    sources = []
    if args.surface in ("working", "all"):
        sources.append(("working", working_blobs(repo)))
    if args.surface in ("index", "all"):
        sources.append(("index", index_blobs(repo)))
    if args.surface in ("history", "all"):
        sources.append(("history", history_blobs(repo)))

    findings: list[tuple[str, str, str, int]] = []
    scanned = 0
    for surface, blobs in sources:
        for label, data in blobs:
            scanned += 1
            findings.extend(scan_blob(surface, label, data, operator_patterns))

    unique = sorted(set(findings))
    for surface, label, kind, line in unique:
        print(f"finding surface={surface} path={label} type={kind} line={line}")
    print(f"blobs_scanned={scanned}")
    print(f"findings={len(unique)}")
    return 1 if unique else 0


if __name__ == "__main__":
    raise SystemExit(main())
