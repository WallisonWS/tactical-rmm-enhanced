# REA Reverse-Engineering Dossier: Tactical RMM Enhanced (`tactical-rmm-enhanced`)

> **Methodology:** `morluto/rea` (Reverse Engineer Anything — *Decompile / Inspect &rarr; Understand with Evidence &rarr; Recreate &amp; Enhance*)
> **Repositories Consolidated &amp; Enhanced:**
> 1. `amidaware/tacticalrmm` (`api/`, `natsapi/`, `docker/`, `ansible/`)
> 2. `amidaware/tacticalrmm-web` (`web/`)
> 3. `amidaware/rmmagent` (`rmmagent/`)

---

## 1. Architectural Evidence Ledger

| Evidence ID | Subsystem | Source Location | Observed Protocol / Contract |
| :--- | :--- | :--- | :--- |
| `ev_trmm_nats_rpc` | Go Agent RPC Dispatcher | `rmmagent/agent/rpc.go` (`L75-L1475`) | Subscribes on NATS subject `a.AgentID` using MessagePack (`ugorji/go/codec`). Dispatches 60 RPC functions (`42` original + `18` new REA-enhanced functions). |
| `ev_trmm_nats_checkin` | Go Agent &rarr; NATS API Bridge | `rmmagent/agent/checkin.go` (`L23-L104`) &amp; `natsapi/svc.go` (`L49-L195`) | Publishes `agent-hello`, `agent-publicip`, `agent-agentinfo`, `agent-disks`, `agent-winsvc`, `agent-wmi` via MessagePack to `natsapi`, which updates `agents_agent` directly in PostgreSQL. |
| `ev_trmm_ws_consumers` | Django Channels ASGI WebSockets | `api/tacticalrmm/tacticalrmm/urls.py` (`L81-L101`) &amp; `agents/consumers.py` | Exposes `ws/dashinfo/`, `ws/agent/<agent_id>/cmd/` (`CommandStreamConsumer`), `ws/agent/<agent_id>/terminal/<session_id>/` (`TerminalStreamConsumer`), and `ws/trmmcli/`. |
| `ev_trmm_checkrunner` | Distributed Agent Check Runner | `rmmagent/agent/checks.go` (`L29-L388`) &amp; `api/tacticalrmm/checks/models.py` | Polls `/api/v3/<agentid>/checkrunner/` every `check_interval` seconds, runs concurrent goroutines (`diskspace`, `cpuload`, `memory`, `ping`, `script`, `winsvc`, `eventlog`), and PATCHes results to `/api/v3/checkrunner/`. |
| `ev_trmm_policy_engine` | Hierarchical Automation Policy Engine | `api/tacticalrmm/automation/models.py` (`L21-L384`) | Evaluates policy inheritance across Global (`CoreSettings`), `Client`, `Site`, and `Agent` scopes with `enforced` precedence and `block_policy_inheritance` overrides. |
| `ev_trmm_file_transfer` | Chunked File Browser &amp; Streaming Engine | `rmmagent/agent/rpc.go` (`L920-L1273`) &amp; `web/src/services/fileTransfer/` | Implements pipelined chunk uploads/downloads (`8 MiB` default chunks), SHA-256 worker verification, archive building, and remote extraction over NATS + REST `/api/v3/file-transfers/`. |
| `ev_trmm_web_dashboard` | Vue 3 + Quasar SPA | `web/src/views/DashboardView.vue` &amp; `web/src/components/SubTableTabs.vue` | Split-pane layout: Client/Site `q-tree` (left), `AgentTable.vue` virtual-scroll grid (top-right), and `SubTableTabs.vue` (bottom-right) plus `RemoteBackground.vue` popout view. |

---

## 2. Complete NATS RPC Catalog (Original + 18 New Enhanced Functions)

### 2.1 Original Tactical RMM NATS Functions (`42` Operations)
- **Connectivity &amp; Lifecycle:** `ping`, `agentupdate`, `uninstall`, `recover`, `shutdown`, `rebootnow`, `needsreboot`, `publicip`
- **Telemetry &amp; Inventory:** `sysinfo`, `wmi`, `cpuloadavg`, `softwarelist`, `procs`, `killproc`, `eventlog`
- **Windows Services:** `winservices`, `winsvcdetail`, `winsvcaction`, `editwinsvc`
- **Windows Registry (7 Ops):** `registry_browse`, `registry_create_key`, `registry_delete_key`, `registry_rename_key`, `registry_create_value`, `registry_delete_value`, `registry_rename_value`, `registry_modify_value`
- **Command &amp; Script Execution:** `rawcmd` (with real-time NATS streaming), `runscript`, `runscriptfull`
- **Checks &amp; Scheduled Tasks:** `runchecks`, `runtask`, `schedtask`, `delschedtask`, `listschedtasks`
- **Runtimes &amp; Patching:** `patchmgmt`, `getwinupdates`, `installwinupdates`, `installchoco`, `installwithchoco`, `installpython`, `installnushell`, `installdeno`
- **Interactive PTY Terminal (4 Ops):** `terminal_start`, `terminal_input`, `terminal_resize`, `terminal_kill`
- **File Browser &amp; Transfer (15 Ops):** `files_list`, `files_exists`, `files_properties`, `files_mkdir`, `files_rename`, `files_delete`, `files_upload_prepare`, `files_upload_chunk_available`, `files_upload_finalize`, `files_upload_abort`, `files_download_ack`, `files_download_prepare`, `files_download_finalize`, `files_download_archive_prepare`, `files_extract_prepare`, `files_extract_cancel`

### 2.2 New REA-Engineered Agent NATS Functions (`18` New Operations)
1. `netconnections` (`rmmagent/agent/network_tools.go`): Enumerates active TCP/UDP sockets, listening ports, remote endpoints, and owning PIDs/processes across Windows (`netstat -ano`) and Linux (`ss -tulnp`).
2. `portscan` (`rmmagent/agent/network_tools.go`): High-concurrency TCP port scanner (64 worker goroutines) with service fingerprinting and millisecond latency measurement.
3. `netdiag` (`rmmagent/agent/network_tools.go`): Multi-stage network diagnostics (DNS lookup latency, ICMP ping status, TCP/80 &amp; TCP/443 reachability, LAN &amp; Public IP discovery).
4. `security_audit` (`rmmagent/agent/security_edr.go`): Computes a `0–100` Endpoint Security Posture Score inspecting Antivirus/Defender status, Real-Time Protection, Host Firewall profiles, BitLocker/LUKS Disk Encryption, UAC, RDP, SMBv1, suspicious processes, high-risk listening ports, and local administrators.
5. `firewall_status` (`rmmagent/agent/security_edr.go`): Inspects Domain, Private, and Public firewall profile states (`Get-NetFirewallProfile` / `ufw`).
6. `firewall_rule` (`rmmagent/agent/security_edr.go`): Remotely enables/disables all firewall profiles or blocks/allows/deletes specific TCP/UDP port rules.
7. `startup_items` (`rmmagent/agent/security_edr.go`): Enumerates persistence and autorun commands (`Win32_StartupCommand`).
8. `local_users` (`rmmagent/agent/security_edr.go`): Lists local user accounts, enabled status, administrator membership, last logon, and password expiration.
9. `bitlocker_status` (`rmmagent/agent/security_edr.go`): Queries system volume encryption status and protection state.
10. `self_heal` (`rmmagent/agent/self_healing.go`): Autonomous endpoint remediation engine supporting `full`, `disk`, `services`, `network`, `winupdate`, and `memory` modes. Automatically restarts stopped Automatic services, repairs `wuauserv`/`bits`/`cryptsvc`, clears temp caches, and flushes DNS/ARP.
11. `disk_cleanup` (`rmmagent/agent/self_healing.go`): Deep temporary and update cache cleanup reporting exact files removed and bytes freed.
12. `trim_memory` (`rmmagent/agent/self_healing.go`): Triggers runtime garbage collection and OS working-set optimization.
13. `reset_network` (`rmmagent/agent/self_healing.go`): Flushes DNS resolver cache, clears ARP tables, and optionally resets Winsock/TCP-IP stack.
14. `winget_list` (`rmmagent/agent/winget_manager.go`): Scans installed software for available updates via `winget upgrade` (Windows) or `apt list --upgradable` (Linux).
15. `winget_install` (`rmmagent/agent/winget_manager.go`): Silently installs third-party packages by Winget ID (`--silent --accept-package-agreements`).
16. `winget_upgrade` (`rmmagent/agent/winget_manager.go`): Silently upgrades individual packages or all outdated packages (`winget upgrade --all --silent`).
17. `telemetry_snapshot` (`rmmagent/agent/telemetry.go`): Real-time hardware telemetry snapshot including per-core CPU load, RAM breakdown, partition metrics, network TX/RX counters, uptime, and S.M.A.R.T. status.
18. `smart_health` (`rmmagent/agent/telemetry.go`): Physical drive S.M.A.R.T. health status, serial numbers, and media type inspection.

---

## 3. Backend API &amp; Frontend Dashboard Enhancements

### 3.1 New Django REST Framework Endpoints (`api/tacticalrmm/agents/views_enhanced.py`)
- `GET /agents/executive-summary/` (`FleetExecutiveSummaryView`)
- `GET /agents/<agent_id>/telemetry/` (`AgentLiveTelemetryView`)
- `GET|POST /agents/<agent_id>/security-audit/` (`AgentSecurityAuditView`)
- `GET|POST /agents/<agent_id>/firewall/` (`AgentFirewallManagerView`)
- `GET|POST /agents/<agent_id>/network/` (`AgentNetworkToolsView`)
- `POST /agents/<agent_id>/self-heal/` (`AgentSelfHealingView`)
- `GET|POST /agents/<agent_id>/winget/` (`AgentWingetManagerView`)
- `POST /agents/<agent_id>/ai-diagnostics/` (`AgentAIDiagnosticsView`)

### 3.2 New Vue 3 + Quasar Components (`web/src/`)
- `web/src/components/dashboard/ExecutiveKPIBar.vue`: Global Fleet Health Score, Availability %, Patch Compliance %, Active Alerts breakdown, and 1-click KPI sync on the main Dashboard.
- `web/src/components/agents/TelemetryTab.vue`: Per-core CPU bars, RAM gauges, Storage volume bars, Physical Disk S.M.A.R.T. status, and Network RX/TX counters.
- `web/src/components/agents/SecurityEDRTab.vue`: Security Score badge, EDR/Hardening checklist, interactive Host Firewall rule manager, Autoruns viewer, and Local Admins auditor.
- `web/src/components/agents/NetworkToolsTab.vue`: Filterable active TCP/UDP sockets table, concurrent Port Scanner UI, and Network Diagnostics runner.
- `web/src/components/agents/SelfHealWingetTab.vue`: 1-Click Self-Healing buttons, Winget silent installer &amp; mass upgrader, and AI Root-Cause Diagnostics assistant with clickable remediation playbooks.
