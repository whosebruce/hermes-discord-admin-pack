#!/usr/bin/env python3
"""Read-only preflight for Hermes native free-response threading support.

This is a source capability check, not a substitute for the behavioral test suite.
"""
import ast
import sys
from pathlib import Path


def native_threading_present(repo: Path) -> bool:
    try:
        defaults = (repo / "hermes_cli/config_defaults.py").read_text()
        adapter = (repo / "plugins/platforms/discord/adapter.py").read_text()
        tree = ast.parse(adapter)
    except (OSError, SyntaxError):
        return False
    methods = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    return (
        '"free_response_auto_thread"' in defaults
        and "_discord_free_response_auto_thread" in methods
        and "DISCORD_FREE_RESPONSE_AUTO_THREAD" in adapter
        and "DISCORD_AUTO_THREAD_FREE_RESPONSE" not in adapter
        and "_discord_auto_thread_free_response" not in methods
    )


if __name__ == "__main__":
    ready = native_threading_present(Path(sys.argv[1]))
    print(f"native_threading_support={str(ready).lower()}")
    if not ready:
        print("Use current Hermes with native free_response_auto_thread support and no retired threading patch.", file=sys.stderr)
    raise SystemExit(0 if ready else 1)
