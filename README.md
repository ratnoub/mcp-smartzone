# mcp-smartzone

Read-only [MCP](https://modelcontextprotocol.io) (Model Context Protocol) server for the
**Ruckus SmartZone (vSZ)** wireless controller, built with [FastMCP](https://github.com/modelcontextprotocol/python-sdk).

It exposes the vSZ public REST API as 35 read-only MCP tools so AI assistants
(Claude Desktop, GitHub Copilot CLI, etc.) can **inspect** your wireless
infrastructure — zones, APs, WLANs, clients, alarms, rogue APs, and more —
without any risk of changing configuration.

> All write operations (create / update / delete / enable / disable /
> disconnect / reboot / clear / block / unblock / mark) are intentionally
> **not** exposed.

## Features

- **35 read-only tools** across 12 categories (see [Tools](#tools))
- **Streamable HTTP** transport by default on `0.0.0.0:5754` → clients connect to `http://<IP>:5754/mcp`
- Also supports **SSE** and **stdio** transports
- **`--daemon`** mode: run detached in the background with PID + log files
- **serviceTicket auth** with automatic ticket caching & refresh
- **Security middleware** (opt-in): API key and/or IP allowlist
- **Config via YAML + environment variables**
- Installable with **pipx** (isolated venv, single `mcp-smartzone` command)

## Requirements

- Python **3.10+**
- A Ruckus SmartZone / vSZ controller with a public API account
  (a dedicated read-only account is recommended)

## Installation

### With pipx (recommended)

```bash
pipx install git+https://github.com/<you>/mcp-smartzone.git
# or from a local clone:
pipx install .
```

### With pip

```bash
pip install .
```

### From source (development)

```bash
git clone https://github.com/<you>/mcp-smartzone.git
cd mcp-smartzone
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS
pip install -e .
```

## Configuration

Copy the example config and fill in your controller details:

```bash
cp config.example.yaml config.yaml   # Windows: copy config.example.yaml config.yaml
```

```yaml
smartzone:
  controller:
    host: "https://192.168.1.10:8443"
    base_path: "/wsg/api/public/v11_0/"
    username: "mcp"
    password: "changeme"
```

**Config file search order:**

1. `--config <path>` CLI flag
2. `SMARTZONE_CONFIG` environment variable
3. `~/.config/mcp-smartzone/config.yaml` (Linux/macOS) or
   `%APPDATA%\mcp-smartzone\config.yaml` (Windows)
4. `./config.yaml` in the current working directory
5. `config.yaml` next to the source tree (development only)

**Environment variable overrides** (take precedence over the YAML file):

| Variable | Description | Default |
|---|---|---|
| `SMARTZONE_CONFIG` | Path to the YAML config file | — |
| `SMARTZONE_HOST` | Controller base URL | from YAML |
| `SMARTZONE_BASE_PATH` | API base path | `/wsg/api/public/v11_0/` |
| `SMARTZONE_USERNAME` | API username | from YAML |
| `SMARTZONE_PASSWORD` | API password | from YAML |
| `SMARTZONE_VERIFY_SSL` | Verify TLS certificates | `false` |
| `SMARTZONE_TIMEOUT` | HTTP timeout (seconds) | `30` |

> **Tip:** keep the password out of the YAML file by using
> `SMARTZONE_PASSWORD` (or a `.env` file in the working directory).

## Usage

```bash
# Foreground — streamable HTTP on 0.0.0.0:5754 (default)
mcp-smartzone

# Background daemon (detached; PID + log in the user data directory)
mcp-smartzone --daemon
mcp-smartzone --stop

# Other transports / options
mcp-smartzone --transport sse --host 0.0.0.0 --port 5754
mcp-smartzone --transport stdio
mcp-smartzone --config /path/to/config.yaml
```

| Option | Description | Default |
|---|---|---|
| `--daemon` | Run detached in the background | off |
| `--stop` | Stop the background daemon | — |
| `--transport` | `streamable-http`, `sse`, or `stdio` | `streamable-http` |
| `--host` | Bind address for HTTP transports | `0.0.0.0` |
| `--port` | Bind port for HTTP transports | `5754` |
| `--config` | Path to config.yaml | auto-discovered |

Daemon artifacts (PID file, log file) live in the user data directory:

| OS | Location |
|---|---|
| Windows | `%LOCALAPPDATA%\mcp-smartzone\` |
| Linux | `~/.local/share/mcp-smartzone/` |
| macOS | `~/Library/Application Support/mcp-smartzone/` |

### MCP client configuration

**Streamable HTTP** (server running with `--daemon` or in the foreground):

```json
{
  "mcpServers": {
    "smartzone": {
      "url": "http://192.168.1.10:5754/mcp"
    }
  }
}
```

**stdio** (client launches the server itself):

```json
{
  "mcpServers": {
    "smartzone": {
      "command": "mcp-smartzone",
      "args": ["--transport", "stdio"]
    }
  }
}
```

## Security

The HTTP transports are open by default. For network exposure, enable one or
both of the following (environment variables):

- **`MCP_API_KEY`** — every request must send
  `Authorization: Bearer <key>` (HTTP 401 otherwise).
- **`MCP_ALLOWED_IPS`** — comma-separated CIDR allowlist, e.g.
  `192.168.1.0/24,10.0.0.5/32` (HTTP 403 for other sources).

## Tools

All tools are prefixed `smartzone_` and are **read-only**.

| Category | Tools |
|---|---|
| System (4) | `get_system_info`, `get_controller_status`, `get_licenses`, `get_version` |
| Zones (3) | `list_zones`, `get_zone`, `get_zone_status` |
| Access Points (4) | `list_aps`, `get_ap`, `get_ap_status`, `get_ap_neighbors` |
| WLANs (3) | `list_wlans`, `get_wlan`, `get_wlan_status` |
| Clients (4) | `list_clients`, `get_client`, `get_client_history`, `get_client_count` |
| Alarms (3) | `list_alarms`, `get_alarm`, `get_alarm_count` |
| Domains (3) | `list_domains`, `get_domain`, `get_domain_status` |
| AAA (3) | `list_aaa_servers`, `get_aaa_server`, `get_aaa_status` |
| DHCP (3) | `list_dhcp_servers`, `get_dhcp_server`, `get_dhcp_status` |
| Monitoring (3) | `get_monitoring_status`, `get_monitoring_metrics`, `get_monitoring_history` |
| Rogue APs (2) | `list_rogue_aps`, `get_rogue_ap` |
| Blocked Clients (2) | `list_blocked_clients`, `get_blocked_client` |

## Development

```bash
pip install -e .
python -m mcp_smartzone            # same as the mcp-smartzone command
```

Project layout:

```
mcp_smartzone/
├── api/
│   ├── client.py      # async HTTP client, serviceTicket caching
│   └── config.py      # config loading (YAML + env)
├── tools/             # 12 tool modules, 35 read-only tools
├── server.py          # FastMCP server, daemon management, security
└── __main__.py        # python -m mcp_smartzone
```

## License

[MIT](LICENSE)