# mcp-smartzone

Server [MCP](https://modelcontextprotocol.io) (Model Context Protocol) **read-only** untuk
wireless controller **Ruckus SmartZone (vSZ)**, dibangun dengan [FastMCP](https://github.com/modelcontextprotocol/python-sdk).

Server ini mengekspos API REST publik vSZ sebagai 38 tool MCP read-only sehingga
asisten AI (Claude Desktop, GitHub Copilot CLI, dll.) dapat **memeriksa**
infrastruktur wireless Anda — zone, AP, WLAN, client, alarm, rogue AP, dan
lain-lain — tanpa risiko mengubah konfigurasi.

Dibangun di atas paket [FastMCP](https://github.com/jlowin/fastmcp) standalone
(`fastmcp>=4.0`), yang menyediakan server `FastMCP`, registrasi tool, dan
transport streamable-HTTP / SSE / stdio.

> Semua operasi tulis (create / update / delete / enable / disable /
> disconnect / reboot / clear / block / unblock / mark) sengaja
> **tidak** diekspos.

## Fitur

- **38 tool read-only** di 13 kategori (lihat [Tools](#tools))
- **Tool pelaporan** — top-N AP / WLAN / client berdasarkan jumlah client atau
  traffic, serta `get_system_summary` satu-panggilan berisi info controller +
  jumlah AP/client/zone/WLAN
- **Tool `query` generik** — cari AP, client, WLAN, zone, dan entri DP-PSK
  dengan filter dan full-text search
- Transport **Streamable HTTP** secara default di `0.0.0.0:5754` → klien
  terhubung ke `http://<IP>:5754/mcp`
- Mendukung juga transport **SSE** dan **stdio**
- Mode **`--daemon`**: berjalan terdetas di background dengan file PID + log
- **Autentikasi serviceTicket** dengan caching & refresh ticket otomatis
- **Middleware keamanan** (opsional): API key dan/atau allowlist IP
- **Konfigurasi via YAML + variabel lingkungan**
- Bisa diinstal dengan **pipx** (venv terisolasi, satu perintah `mcp-smartzone`)

## Persyaratan

- Python **3.10+**
- Ruckus SmartZone / vSZ controller dengan akun API publik
  (disarankan menggunakan akun read-only khusus)

## Instalasi

### Dengan pipx (disarankan)

```bash
pipx install git+https://github.com/ratnoub/mcp-smartzone.git
# atau dari clone lokal:
pipx install .
```

### Dengan pip

```bash
pip install .
```

### Dari source (development)

```bash
git clone https://github.com/ratnoub/mcp-smartzone.git
cd mcp-smartzone
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS
pip install -e .
```

## Konfigurasi

Salin contoh konfigurasi dan isi detail controller Anda:

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

**Urutan pencarian file konfigurasi:**

1. Flag CLI `--config <path>`
2. Variabel lingkungan `SMARTZONE_CONFIG`
3. `~/.config/mcp-smartzone/config.yaml` (Linux/macOS) atau
   `%APPDATA%\mcp-smartzone\config.yaml` (Windows)
4. `./config.yaml` di direktori kerja saat ini
5. `config.yaml` di samping source tree (hanya development)

**Override via variabel lingkungan** (mengalahkan file YAML):

| Variabel | Keterangan | Default |
|---|---|---|
| `SMARTZONE_CONFIG` | Path ke file konfigurasi YAML | — |
| `SMARTZONE_HOST` | URL dasar controller | dari YAML |
| `SMARTZONE_BASE_PATH` | Path dasar API | `/wsg/api/public/v11_0/` |
| `SMARTZONE_USERNAME` | Username API | dari YAML |
| `SMARTZONE_PASSWORD` | Password API | dari YAML |
| `SMARTZONE_VERIFY_SSL` | Verifikasi sertifikat TLS | `false` |
| `SMARTZONE_TIMEOUT` | Timeout HTTP (detik) | `30` |

> **Tips:** simpan password di luar file YAML dengan menggunakan
> `SMARTZONE_PASSWORD` (atau file `.env` di direktori kerja).

## Penggunaan

```bash
# Foreground — streamable HTTP di 0.0.0.0:5754 (default)
mcp-smartzone

# Daemon background (terdetas; PID + log di direktori data user)
mcp-smartzone --daemon
mcp-smartzone --stop

# Transport / opsi lain
mcp-smartzone --transport sse --host 0.0.0.0 --port 5754
mcp-smartzone --transport stdio
mcp-smartzone --config /path/to/config.yaml
```

| Opsi | Keterangan | Default |
|---|---|---|
| `--daemon` | Jalankan terdetas di background | off |
| `--stop` | Hentikan daemon background | — |
| `--transport` | `streamable-http`, `sse`, atau `stdio` | `streamable-http` |
| `--host` | Alamat bind untuk transport HTTP | `0.0.0.0` |
| `--port` | Port bind untuk transport HTTP | `5754` |
| `--config` | Path ke config.yaml | otomatis |

Artefak daemon (file PID, file log) berada di direktori data user:

| OS | Location |
|---|---|
| Windows | `%LOCALAPPDATA%\mcp-smartzone\` |
| Linux | `~/.local/share/mcp-smartzone/` |
| macOS | `~/Library/Application Support/mcp-smartzone/` |

### Konfigurasi klien MCP

**Streamable HTTP** (server berjalan dengan `--daemon` atau foreground):

```json
{
  "mcpServers": {
    "smartzone": {
      "url": "http://192.168.1.10:5754/mcp"
    }
  }
}
```

**stdio** (klien yang menjalankan server):

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

## Keamanan

Transport HTTP terbuka secara default. Untuk eksposur jaringan, aktifkan salah
satu atau keduanya (variabel lingkungan):

- **`MCP_API_KEY`** — setiap request harus mengirim
  `Authorization: Bearer <key>` (HTTP 401 jika tidak).
- **`MCP_ALLOWED_IPS`** — allowlist CIDR dipisah koma, mis.
  `192.168.1.0/24,10.0.0.5/32` (HTTP 403 untuk sumber lain).

## Tools

Semua tool berawalan `smartzone_` dan bersifat **read-only**.

| Kategori | Tools |
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

### Tool pelaporan & query

- **`smartzone_get_system_summary`** — ringkasan satu-panggilan: nama /
  model / versi / uptime / IP manajemen controller plus jumlah total, online,
  dan offline AP, serta jumlah total client / zone / WLAN.
- **`smartzone_query`** — pencarian generik di `ap`, `client`, `wlan`, `zone`,
  dan `dpsk` dengan filter bertipe (mis. `{"type": "ZONE", "value": "HQ"}`)
  dan full-text search.
- **`smartzone_get_ap_statistics`** — ringkasan operasional per-AP (state,
  uptime, channel, lokasi) digabung dengan counter traffic (TX/RX bytes,
  airtime, noise, latency, retry, MCS) dari query API.
- **`smartzone_top_aps`** — top-N AP berdasarkan jumlah client atau total traffic.
- **`smartzone_top_wlans`** — top-N WLAN berdasarkan jumlah client atau traffic.
- **`smartzone_top_clients`** — top-N client berdasarkan traffic atau durasi sesi.

## Development

```bash
pip install -e .
python -m mcp_smartzone            # sama dengan perintah mcp-smartzone
```

Struktur proyek:

```
mcp_smartzone/
├── api/
│   ├── client.py      # async HTTP client, caching serviceTicket
│   └── config.py      # pemuatan konfigurasi (YAML + env)
├── tools/             # 13 modul tool, 38 tool read-only
├── server.py          # server FastMCP, manajemen daemon, keamanan
└── __main__.py        # python -m mcp_smartzone
```

## Lisensi

[MIT](LICENSE)