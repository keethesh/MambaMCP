"""Mamba CLI dispatcher — routes to setup subcommands or the MCP bridge."""
from __future__ import annotations

import sys

SETUP_COMMANDS = {
    "setup",
    "start",
    "mcp",
    "install-python-deps",
    "verify-version",
    "preflight",
    "build",
    "clean",
    "run-tests",
    "install-ghidra-deps",
    "deploy",
    "start-ghidra",
    "ensure-prereqs",
    "bump-version",
    "clean-all",
}


def main() -> int:
    """Dispatch to setup CLI (if subcommand given) or bridge (default)."""
    if len(sys.argv) > 1 and sys.argv[1] in SETUP_COMMANDS:
        from tools.setup.cli import main as setup_main

        return setup_main()

    from bridge_mcp_ghidra import main as bridge_main

    return bridge_main()


if __name__ == "__main__":
    raise SystemExit(main())