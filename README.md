# Mamba MCP

[![Tests](https://img.shields.io/github/actions/workflow/status/keethesh/mamba-mcp/tests.yml?branch=main&style=for-the-badge&label=Tests&logo=github-actions&logoColor=white)](https://github.com/keethesh/mamba-mcp/actions/workflows/tests.yml)
[![License](https://img.shields.io/github/license/keethesh/mamba-mcp?style=for-the-badge&color=green)](LICENSE)

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Java](https://img.shields.io/badge/Java-21-ED8B00?style=for-the-badge&logo=openjdk&logoColor=white)](https://openjdk.org/projects/jdk/21/)
[![Ghidra](https://img.shields.io/badge/Ghidra-12.0.4-brightgreen?style=for-the-badge&logoColor=white)](https://ghidra-sre.org/)
[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-6C5CE7?style=for-the-badge&logoColor=white)](https://modelcontextprotocol.io/)

Fast, stable MCP bridge for Ghidra — simplified setup, lazy loading, and sane defaults.

> Mamba is a clean fork of [ghidra-mcp](https://github.com/bethington/ghidra-mcp) focused on **stability and simplicity over feature count**. ~111 tools by default, circuit breaker resilience, and Maven-only build.

## What Mamba Is

**The problem with ghidra-mcp:** 225 tools means 225 things that can break. Niche endpoints bitrot. Complex features add coupling. When Ghidra crashes under load, you get cascading failures with no recovery.

**What Mamba does differently:**

- **~111 tools by default** — only essential tools load on connect. Debugger, emulation, and niche analysis tools load on-demand via `load_tool_group()`.
- **Circuit breaker** — 5 failures in 30s trips a 30s cooldown. No more hammering a dead Ghidra instance.
- **Background health polling** — a 15s background thread detects disconnects before tool calls fail, enabling fast-fail on the next call.
- **Exponential backoff** — retries use `2^attempt` seconds. A flaky instance gets breathing room, not repeated hammer blows.
- **Maven only** — one build system, one way to compile. No dual Gradle/Maven confusion.
- **`pip install mamba-mcp`** — proper Python packaging, not just `requirements.txt`.

| | ghidra-mcp | Mamba |
|---|---|---|
| Default tools on connect | 225 | ~111 |
| Circuit breaker | ❌ | ✅ |
| Health polling | ❌ | ✅ |
| Lazy tool loading | opt-in | default |
| Build systems | Gradle + Maven | Maven only |
| Python packaging | `requirements.txt` | `pyproject.toml` |

## Quick Start

### Prerequisites

- Java 21 LTS, Apache Maven 3.9+, Ghidra 12.0.4, Python 3.10+

### Install

```bash
pip install mamba-mcp
```

Or build from source:

```bash
git clone https://github.com/keethesh/mamba-mcp.git
cd mamba-mcp
mvn clean package assembly:single -DskipTests
```

### Deploy to Ghidra

```bash
python -m tools.setup ensure-prereqs --ghidra-path "F:\ghidra_12.0.4_PUBLIC"
python -m tools.setup build
python -m tools.setup deploy --ghidra-path "F:\ghidra_12.0.4_PUBLIC"
```

### Run

```bash
# Stdio transport (AI tools)
python bridge_mcp_ghidra.py

# HTTP transport (web clients)
python bridge_mcp_ghidra.py --transport streamable-http --mcp-port 8081
```

### In Ghidra

1. **Tools > Mamba > Start MCP Server** (after enabling in `File > Configure > Configure All Plugins`)
2. Configure MCP client:

```json
{
  "mcpServers": {
    "mamba": {
      "command": "python",
      "args": ["/path/to/bridge_mcp_ghidra.py"]
    }
  }
}
```

## Tool Groups

Mamba uses lazy loading — only 7 core groups load on connect (~111 tools). Load more on demand:

| Group | Tools | Description |
|---|---|---|
| `listing` | ~20 | Disassembly, memory, xrefs |
| `function` | ~25 | Decompile, analyze, call graphs |
| `program` | ~15 | Metadata, analysis control |
| `xref` | ~10 | Cross-reference queries |
| `comment` | ~10 | Comments, bookmarks, labels |
| `datatype` | ~20 | Structure, enum, typedef creation |
| `symbol` | ~10 | Imports, exports, strings |

Load more:

```bash
# Load debugger tools (live attach, breakpoints, memory)
bridge_mcp_ghidra.py --load-group debugger

# Load emulation tools (P-code emulation)
bridge_mcp_ghidra.py --load-group emulation

# Load everything (legacy behavior)
bridge_mcp_ghidra.py --no-lazy
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `GHIDRA_MCP_AUTH_TOKEN` | — | Bearer token for HTTP auth |
| `GHIDRA_MCP_ALLOW_SCRIPTS` | off | Enable inline script execution |
| `GHIDRA_MCP_FILE_ROOT` | — | Path root for filesystem endpoints |

### Bridge Flags

| Flag | Default | Description |
|---|---|---|
| `--transport` | `stdio` | `stdio`, `streamable-http`, `sse` |
| `--mcp-host` | `127.0.0.1` | HTTP bind host |
| `--mcp-port` | — | HTTP port (required for streamable-http) |
| `--lazy` | on | Load only default tool groups |
| `--no-lazy` | off | Load all tool groups on connect |
| `--default-groups` | see above | Comma-separated groups loaded in lazy mode |

## Architecture

```
AI/Automation Tools  <--MCP-->  Mamba Bridge (Python)  <--HTTP-->  Ghidra Plugin
   (Claude, etc.)              bridge_mcp_ghidra.py              MambaMCP.jar
                                   |                                |
                              MCP Protocol                    Ghidra API
                           (stdio/HTTP)                   (Program, Listing)
```

## Building

```bash
# Build JAR and extension ZIP
mvn clean package assembly:single -DskipTests

# Quick compile check
mvn clean compile -q

# Run tests
pytest tests/unit/ -v --no-cov
```

## Project Structure

```
mamba-mcp/
├── bridge_mcp_ghidra.py     # Python MCP bridge (~111 default tools)
├── src/main/java/            # Ghidra plugin (Java)
│   └── com/xebyte/
│       ├── MambaMCPPlugin.java        # GUI plugin
│       └── headless/                    # Headless server
├── tests/
│   ├── unit/                 # Python unit tests
│   └── endpoints.json        # Endpoint catalog
├── tools/setup/              # Build + deploy CLI
├── pyproject.toml            # Python package definition
└── pom.xml                   # Maven build
```

## Stability Features

### Circuit Breaker

When Ghidra is unresponsive, Mamba fails fast instead of retrying indefinitely:

```
State: CLOSED (normal)
  → 5 failures in 30s → OPEN (cooldown 30s)
  → cooldown expires → HALF-OPEN (probe request)
  → probe succeeds → CLOSED | probe fails → OPEN
```

### Health Polling

A background thread polls `/health` every 15s. When a disconnect is detected, the bridge marks the instance unhealthy so tool calls fast-fail rather than hang.

### Exponential Backoff

Retries use geometric backoff: 1s, 2s, 4s, 8s... instead of hammering a struggling instance.

## Relationship to ghidra-mcp

Mamba is a clean fork of [bethington/ghidra-mcp](https://github.com/bethington/ghidra-mcp) v5.6.0. Changes are opinionated remotions for stability:

- Removed 100+ rarely-used endpoints (debugger, emulation, niche analysis)
- Removed Gradle (Maven-only build)
- Added circuit breaker, health polling, exponential backoff
- Changed lazy loading from opt-in to default
- Created proper Python package (`pyproject.toml`)

GhidraMCP remains the full-featured option. Mamba is for teams that want a smaller, more predictable tool surface.

## License

Apache 2.0