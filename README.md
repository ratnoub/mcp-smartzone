# mcp-smartzone

Read-only [MCP](https://modelcontextprotocol.io) (Model Context Protocol) server for the
**Ruckus SmartZone (vSZ)** wireless controller, built with [FastMCP](https://github.com/modelcontextprotocol/python-sdk).

It exposes the vSZ public REST API as 38 read-only MCP tools so AI assistants
(Claude Desktop, GitHub Copilot CLI, etc.) can **inspect** your wireless
infrastructure — zones, APs, WLANs, clients, alarms, rogue APs, and more —
without any risk of changing configuration.

Built on the standalone [FastMCP](https://github.com/jlowin/fastmcp) package
(`fastmcp>=4.0`), which provides the `FastMCP` server, tool registration, and
the streamable-HTTP / SSE / stdio transports.

> All write operations (create / update / delete / enable / disable /
> disconnect / reboot / clear / block / unblock / mark) are intentionally
> **not** exposed.

## Features

- **38 read-only tools** across 13 categories (see [Tools](#tools))
- **Reporting tools** — top-N APs / WLANs / clients by clients or traffic, and a
  one-call `get_system_summary` with controller info + AP/client/zone/WLAN counts
- **Generic `query` tool** — search APs, clients, WLANs, zones, and DP-PSK
  entries with filters and full-text search
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
| System (5) | `get_system_info`, `get_system_inventory`, `get_system_summary`, `get_controller_list`, `get_cluster_state` |
| Zones (3) | `list_zones`, `get_zone`, `list_zone_ap_groups` |
| Access Points (8) | `list_aps`, `get_ap`, `get_ap_operational`, `get_ap_radio`, `get_ap_statistics`, `list_ap_lldp_neighbors`, `list_ap_mesh_neighbors`, `query_aps` |
| WLANs (3) | `list_wlans`, `get_wlan`, `get_wlan_statistics` |
| Clients (3) | `list_clients`, `get_client`, `query_clients` |
| Alarms (2) | `list_alarms`, `get_alarm` |
| Domains (2) | `list_domains`, `get_domain` |
| AAA / Auth (2) | `list_auth_servers`, `get_auth_server` |
| DHCP (2) | `list_dhcp_pools`, `get_dhcp_pool` |
| VLAN (2) | `list_vlan_pools`, `get_vlan_pool` |
| Rogue APs (1) | `list_rogue_aps` |
| Blocked Clients (1) | `list_blocked_clients` |
| Query & Reports (4) | `query`, `top_aps`, `top_wlans`, `top_clients` |

### Reporting & query tools

- **`smartzone_get_system_summary`** — one-call overview: controller name /
  model / version / uptime / management IP plus total, online, and offline AP
  counts, and total client / zone / WLAN counts.
- **`smartzone_query`** — generic search across `ap`, `client`, `wlan`, `zone`,
  and `dpsk` with typed filters (e.g. `{"type": "ZONE", "value": "HQ"}`) and
  full-text search.
- **`smartzone_get_ap_statistics`** — per-AP operational summary (state,
  uptime, channels, location) combined with traffic counters (TX/RX bytes,
  airtime, noise, latency, retry, MCS) from the query API.
- **`smartzone_top_aps`** — top-N APs ranked by client count or total traffic.
- **`smartzone_top_wlans`** — top-N WLANs ranked by client count or traffic.
- **`smartzone_top_clients`** — top-N clients ranked by traffic or session
  duration.

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
├── tools/             # 13 tool modules, 38 read-only tools
├── server.py          # FastMCP server, daemon management, security
└── __main__.py        # python -m mcp_smartzone
```

## License

[MIT](LICENSE)