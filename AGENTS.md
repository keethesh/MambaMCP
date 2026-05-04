# AGENTS.md — Mamba MCP Project

You are a coding agent working on **Mamba**, a Model Context Protocol server that bridges Ghidra's reverse engineering capabilities with AI tools.

## Project Context

- **Repo**: https://github.com/keethesh/mamba-mcp
- **Forked from**: https://github.com/bethington/ghidra-mcp
- **Version**: 1.0.0
- **Language**: Java (Ghidra extension) + Python (MCP bridge)
- **Key feature**: ~111 default MCP tools (lazy-loaded), circuit breaker stability, single build system (Maven only), `pip install` support

## What Makes Mamba Different

Mamba is a clean fork of ghidra-mcp that prioritizes **stability and simplicity over feature count**:

- **~111 tools by default** instead of 225 — only essential tools load on connect
- **Circuit breaker** — fast-fails instead of hammering a broken Ghidra instance
- **Background health polling** — auto-detects disconnects before tool calls fail
- **Lazy loading** — load debugger, emulation, and niche tools on-demand
- **Maven only** — no Gradle confusion, no dual build systems
- **`pip install mamba-mcp`** — proper Python packaging, not just `requirements.txt`

## Directory Structure

- `src/` — Java source for Ghidra extension and headless server
- `bridge_mcp_ghidra.py` — Python MCP bridge (main entry point)
- `docs/` — Documentation and workflow prompts
- `tests/` — Python unit tests and endpoint catalog
- `tools/setup/` — Build and deployment CLI
- `pyproject.toml` — Python package definition
- `CHANGELOG.md` — Version history

## Current Priorities

1. Maintain lazy-loading behavior and tool group organization
2. Keep `tests/endpoints.json` in sync with Java endpoint registrations
3. Ensure CI passes: `pytest tests/unit/ -v --no-cov`
4. Build: `mvn clean package assembly:single -DskipTests`

## Guidelines

- Run tests before committing: `pytest tests/unit/ -v --no-cov`
- Build: `mvn clean package assembly:single -DskipTests`
- Quick compile check: `mvn clean compile -q`
- Follow existing code style
- Update CHANGELOG.md for user-facing changes
- Create PRs for review (don't push directly to main)
- Use `python -m tools.setup bump-version --new X.Y.Z` to bump version across all maintained files atomically

## Commands

- Build: `mvn clean package assembly:single -DskipTests`
- Quick compile: `mvn clean compile -q`
- Test (Python): `pytest tests/unit/ -v --no-cov`
- Preflight: `python -m tools.setup preflight --ghidra-path F:\ghidra_12.0.4_PUBLIC`
- Deploy: `python -m tools.setup ensure-prereqs --ghidra-path F:\ghidra_12.0.4_PUBLIC` then `python -m tools.setup build` then `python -m tools.setup deploy --ghidra-path F:\ghidra_12.0.4_PUBLIC`
- Version bump: `python -m tools.setup bump-version --new X.Y.Z`