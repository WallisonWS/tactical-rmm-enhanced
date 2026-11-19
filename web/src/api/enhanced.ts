import axios from "axios";
import { ref } from "vue";
import { getBaseUrl } from "@/boot/axios";
import { useAuthStore } from "@/stores/auth";

export const fleetDomainMap = ref<Record<string, { part_of_domain: boolean; domain: string }>>({});
export const fleetOutsideAdIds = ref<string[]>([]);
export const fleetInsideAdIds = ref<string[]>([]);

// ============================================================================
// Enhanced Tactical RMM API Client (Telemetry, Security/EDR, Network, Self-Heal, Winget, AI & Fleet KPIs)
// ============================================================================

export interface LiveTelemetrySnapshot {
  agent_id: string;
  hostname: string;
  platform: string;
  architecture?: string;
  cpu_load_percent: number;
  cpu_per_core?: number[];
  cpu_cores_logical?: number;
  ram_total_mb: number;
  ram_used_mb: number;
  ram_free_mb: number;
  ram_used_percent: number;
  disk_metrics?: Array<{
    mountpoint: string;
    fstype: string;
    total_gb: number;
    used_gb: number;
    free_gb: number;
    used_percent: number;
  }>;
  net_bytes_sent?: number;
  net_bytes_recv?: number;
  smart_health?: Array<{
    model: string;
    serial_number: string;
    status: string;
    media_type: string;
  }>;
  uptime_seconds?: number;
  needs_reboot: boolean;
  process_count?: number;
  cached_fallback?: boolean;
  timestamp?: string;
}

export interface SecurityAuditReport {
  agent_id: string;
  hostname: string;
  platform: string;
  security_score: number;
  antivirus_enabled: boolean;
  antivirus_name: string;
  realtime_protection: boolean;
  firewall_enabled: boolean;
  firewall_profiles: Array<{ name: string; enabled: boolean }>;
  disk_encrypted: boolean;
  encryption_detail: string;
  uac_enabled: boolean;
  rdp_enabled: boolean;
  smbv1_enabled: boolean;
  suspicious_processes: Array<{
    pid: number;
    name: string;
    reason: string;
    mem_mb: number;
    cpu_pct: string;
  }>;
  high_risk_open_ports: number[];
  local_admins: string[];
  startup_items_count: number;
  recommendations: string[];
  timestamp: string;
}

export interface NetConnectionInfo {
  protocol: string;
  local_addr: string;
  local_port: number;
  remote_addr: string;
  remote_port: number;
  state: string;
  pid: number;
  process: string;
}

export interface PortScanResult {
  host: string;
  open_ports: Array<{
    port: number;
    protocol: string;
    service: string;
    latency_ms: number;
  }>;
  scanned_count: number;
  duration_ms: number;
}

export interface NetDiagReport {
  target: string;
  dns_resolved_ips: string[];
  dns_latency_ms: number;
  ping_success: boolean;
  ping_output: string;
  tcp_80_reachable: boolean;
  tcp_443_reachable: boolean;
  local_ips: string[];
  public_ip: string;
  timestamp: string;
}

export interface FleetExecutiveSummary {
  total_agents: number;
  online_agents: number;
  offline_agents: number;
  overdue_agents: number;
  reboot_needed_agents: number;
  maintenance_agents: number;
  availability_percent: number;
  patch_compliance_percent: number;
  fleet_health_score: number;
  active_alerts: {
    total: number;
    error: number;
    warning: number;
  };
  failing_checks_count: number;
  agents_with_pending_patches: number;
  ad_joined_agents?: number;
  outside_ad_agents?: number;
  outside_ad_agent_ids?: string[];
  ad_joined_agent_ids?: string[];
  domain_map?: Record<string, { part_of_domain: boolean; domain: string }>;
  timestamp: string;
}

let _execSummaryCache: FleetExecutiveSummary | null = null;
let _execSummaryCacheAt = 0;
let _execSummaryInflight: Promise<FleetExecutiveSummary> | null = null;
const EXEC_SUMMARY_TTL_MS = 10_000;

export async function fetchFleetExecutiveSummary(
  force = false,
): Promise<FleetExecutiveSummary> {
  const now = Date.now();
  if (!force && _execSummaryCache && now - _execSummaryCacheAt < EXEC_SUMMARY_TTL_MS) {
    return _execSummaryCache;
  }
  if (!force && _execSummaryInflight) {
    return _execSummaryInflight;
  }

  const req = axios
    .get("/agents/executive-summary/", {
      params: force ? { force: 1 } : undefined,
    })
    .then(({ data }) => {
      if (data?.domain_map) {
        fleetDomainMap.value = data.domain_map;
      }
      if (Array.isArray(data?.outside_ad_agent_ids)) {
        fleetOutsideAdIds.value = data.outside_ad_agent_ids;
      }
      if (Array.isArray(data?.ad_joined_agent_ids)) {
        fleetInsideAdIds.value = data.ad_joined_agent_ids;
      }
      _execSummaryCache = data;
      _execSummaryCacheAt = Date.now();
      return data;
    })
    .finally(() => {
      if (_execSummaryInflight === req) {
        _execSummaryInflight = null;
      }
    });

  _execSummaryInflight = req;
  return req;
}

export async function fetchAgentLiveTelemetry(agentId: string): Promise<LiveTelemetrySnapshot> {
  const { data } = await axios.get(`/agents/${agentId}/telemetry/`);
  return data;
}

export async function fetchAgentSecurityAudit(agentId: string): Promise<SecurityAuditReport> {
  const { data } = await axios.get(`/agents/${agentId}/security-audit/`);
  return data;
}

export async function queryAgentSecurityDetails(
  agentId: string,
  queryType: "startup_items" | "local_users" | "bitlocker_status",
) {
  const { data } = await axios.post(`/agents/${agentId}/security-audit/`, {
    query_type: queryType,
  });
  return data;
}

export async function fetchAgentFirewallStatus(agentId: string) {
  const { data } = await axios.get(`/agents/${agentId}/firewall/`);
  return data;
}

export async function executeAgentFirewallRule(
  agentId: string,
  payload: {
    action: "enable_all" | "disable_all" | "block_port" | "allow_port" | "delete_rule";
    rule_name?: string;
    direction?: "in" | "out";
    protocol?: "TCP" | "UDP";
    port?: string;
    remote_ip?: string;
  },
) {
  const { data } = await axios.post(`/agents/${agentId}/firewall/`, payload);
  return data;
}

export async function fetchAgentNetConnections(agentId: string): Promise<NetConnectionInfo[]> {
  const { data } = await axios.get(`/agents/${agentId}/network/`);
  return data;
}

export async function runAgentPortScan(
  agentId: string,
  host: string,
  ports = "",
  timeoutMs = 600,
): Promise<PortScanResult> {
  const { data } = await axios.post(`/agents/${agentId}/network/`, {
    tool: "portscan",
    host,
    ports,
    timeout_ms: timeoutMs,
  });
  return data;
}

export async function runAgentNetDiag(
  agentId: string,
  target = "1.1.1.1",
): Promise<NetDiagReport> {
  const { data } = await axios.post(`/agents/${agentId}/network/`, {
    tool: "netdiag",
    target,
  });
  return data;
}

export async function triggerAgentSelfHeal(
  agentId: string,
  action: "self_heal" | "disk_cleanup" | "trim_memory" | "reset_network" = "self_heal",
  mode: "full" | "disk" | "services" | "network" | "winupdate" | "memory" = "full",
  fullReset = false,
) {
  const { data } = await axios.post(`/agents/${agentId}/self-heal/`, {
    action,
    mode,
    full_reset: fullReset,
  });
  return data;
}

export async function fetchAgentWingetPackages(agentId: string) {
  const { data } = await axios.get(`/agents/${agentId}/winget/`);
  return data;
}

export async function runAgentWingetOperation(
  agentId: string,
  operation: "install" | "upgrade",
  packageId = "all",
) {
  const { data } = await axios.post(`/agents/${agentId}/winget/`, {
    operation,
    package_id: packageId,
  });
  return data;
}

export async function runAgentAIDiagnostics(agentId: string) {
  const { data } = await axios.post(`/agents/${agentId}/ai-diagnostics/`);
  return data;
}

export interface HALinkHealthReport {
  agent_id: string;
  hostname: string;
  platform: string;
  agent_version?: string;
  api_reachable: boolean;
  api_latency_ms: number;
  nats_reachable: boolean;
  nats_latency_ms: number;
  nats_transport?: string;
  mesh_service_status: string;
  mesh_healthy: boolean;
  mesh_binary_exists?: boolean;
  mesh_process_count?: number;
  mesh_node_id?: string;
  mesh_id_synced?: boolean;
  proxy_configured: boolean;
  proxy_url: string;
  overall_status: "HEALTHY" | "DEGRADED" | "CRITICAL";
  recommendations: string[];
  timestamp: string;
}

export interface RDPSessionInfo {
  session_name: string;
  username: string;
  id: string;
  state: string;
}

export interface CorporateRDPStatus {
  hostname?: string;
  public_ip?: string;
  platform: string;
  rdp_enabled: boolean;
  nla_enabled: boolean;
  service_status: string;
  listening_port: number;
  port_reachable: boolean;
  local_ips: string[];
  active_sessions: RDPSessionInfo[];
  timestamp: string;
}

export async function fetchAgentHALinkHealth(agentId: string): Promise<HALinkHealthReport> {
  const { data } = await axios.get(`/agents/${agentId}/ha-link/`);
  return data;
}

export async function repairAgentHALink(agentId: string) {
  const { data } = await axios.post(`/agents/${agentId}/ha-link/`);
  return data;
}

export async function fetchAgentRDPStatus(agentId: string): Promise<CorporateRDPStatus> {
  const { data } = await axios.get(`/agents/${agentId}/rdp/`);
  return data;
}

export async function manageAgentRDP(
  agentId: string,
  action: "enable_rdp" | "disable_rdp" | "restart_rdp" | "logoff_session" | { action: string },
  enforceNLA = true,
  sessionId = "",
) {
  const normalizedAction = typeof action === "object" && action !== null ? action.action : action;
  const { data } = await axios.post(`/agents/${agentId}/rdp/`, {
    action: normalizedAction,
    enforce_nla: enforceNLA,
    session_id: sessionId,
  });
  return data;
}

export function resolveFirstReachableHost(
  rawIps?: string | null,
  hostname?: string | null,
  publicIp?: string | null,
): string {
  const candidates = String(rawIps || "")
    .split(",")
    .map((s) => s.split("/")[0].trim())
    .filter((ip) => ip && !ip.startsWith("127.") && ip !== "::1");
  return candidates[0] || String(hostname || "").trim() || String(publicIp || "").trim();
}

export function downloadNativeRDPFile(hostname: string, hostAddress: string, port = 3389) {
  const rdpContent = [
    `full address:s:${hostAddress}:${port}`,
    "prompt for credentials:i:1",
    "administrative session:i:1",
    "screen mode id:i:2",
    "use multimon:i:0",
    "desktopwidth:i:1920",
    "desktopheight:i:1080",
    "session bpp:i:32",
    "compression:i:1",
    "keyboardhook:i:2",
    "audiocapturemode:i:0",
    "videoplaybackmode:i:1",
    "connection type:i:7",
    "networkautodetect:i:1",
    "bandwidthautodetect:i:1",
    "enableworkspacereconnect:i:1",
    "enablecredsspsupport:i:1",
    "authentication level:i:2",
    "autoreconnection enabled:i:1",
  ].join("\r\n");

  const blob = new Blob([rdpContent], { type: "application/x-rdp;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${hostname || hostAddress}.rdp`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export interface HardwareDomainInventory {
  hostname: string;
  platform: string;
  manufacturer: string;
  model: string;
  serial_number: string;
  bios_version: string;
  domain_or_workgroup: string;
  part_of_domain: boolean;
  entra_id_joined: boolean;
  active_power_plan: string;
  gpus: string[];
  battery_present: boolean;
  battery_charge_pct: number;
  battery_status: string;
  printers_count: number;
  restore_points_count: number;
  timestamp: string;
}

export interface PrinterInfo {
  name: string;
  driver_name: string;
  port_name: string;
  printer_status: string;
  shared: boolean;
  job_count: number;
}

export interface RestorePointInfo {
  sequence_number: number;
  description: string;
  creation_time: string;
  event_type: string;
}

export async function fetchAgentHardwareInventory(
  agentId: string,
): Promise<HardwareDomainInventory> {
  const { data } = await axios.get(`/agents/${agentId}/hardware-inventory/`);
  return data;
}

export async function runAgentAdminAction(
  agentId: string,
  action: "gpupdate_force" | "high_performance_power" | "sync_time" | "clear_print_spooler",
) {
  const { data } = await axios.post(`/agents/${agentId}/hardware-inventory/`, {
    action,
  });
  return data;
}

export async function fetchAgentPrinters(agentId: string): Promise<PrinterInfo[]> {
  const { data } = await axios.get(`/agents/${agentId}/printers/`);
  return data;
}

export async function runAgentPrinterAction(
  agentId: string,
  action: "clear_queue" | "set_default" | "test_page",
  printerName: string,
) {
  const { data } = await axios.post(`/agents/${agentId}/printers/`, {
    action,
    printer_name: printerName,
  });
  return data;
}

export async function fetchAgentRestorePoints(
  agentId: string,
): Promise<{ restore_points: RestorePointInfo[] }> {
  const { data } = await axios.get(`/agents/${agentId}/it-support/`);
  return data;
}

export async function createAgentRestorePoint(agentId: string, description: string) {
  const { data } = await axios.post(`/agents/${agentId}/it-support/`, {
    tool_type: "system_restore",
    description,
  });
  return data;
}

export async function sendAgentITSupportMessage(
  agentId: string,
  title: string,
  message: string,
  timeoutSec = 60,
) {
  const { data } = await axios.post(`/agents/${agentId}/it-support/`, {
    tool_type: "broadcast_msg",
    title,
    message,
    timeout_sec: timeoutSec,
  });
  return data;
}

export interface WindowsServerADProfile {
  hostname: string;
  platform: string;
  os_caption: string;
  os_version: string;
  environment_mode: "active_directory" | "workgroup_standalone" | "linux_standalone";
  is_windows_server: boolean;
  is_domain_controller: boolean;
  part_of_domain: boolean;
  domain_name: string;
  workgroup_name: string;
  forest_name: string;
  domain_role_id: number;
  domain_role_label: string;
  domain_controller_name: string;
  domain_controller_address: string;
  ad_site_name: string;
  computer_dn: string;
  organizational_unit: string;
  secure_channel_valid: boolean;
  sysvol_reachable: boolean;
  netlogon_reachable: boolean;
  time_sync_source: string;
  deployed_via_gpo: boolean;
  deployment_mode: string;
  last_gpo_verify: string;
  applied_computer_gpos: string[];
  installed_server_roles: string[];
  ad_critical_services: Record<string, string>;
  recommended_agent_type: string;
  client_id?: number;
  client_name?: string;
  site_id?: number;
  site_name?: string;
  timestamp: string;
}

export async function fetchAgentADServerStatus(
  agentId: string,
): Promise<WindowsServerADProfile> {
  const { data } = await axios.get(`/agents/${agentId}/ad-server/`);
  return data;
}

export async function runAgentADServerAction(
  agentId: string,
  action:
    | "test_secure_channel"
    | "repair_secure_channel"
    | "gpupdate_registerdns"
    | "sync_standalone_ntp"
    | "dcdiag_server_health"
    | "generate_deploy_info",
) {
  const { data } = await axios.post(`/agents/${agentId}/ad-server/`, {
    action,
  });
  return data;
}

export interface FleetADAuditAgentItem {
  agent_id: string;
  hostname: string;
  client_name: string;
  site_name: string;
  monitoring_type: string;
  operating_system: string;
  logged_in_username: string;
  local_ips: string;
  part_of_domain: boolean;
  domain_or_workgroup: string;
  domain_name: string;
  workgroup_name: string;
  status: string;
}

export interface FleetOutsideADAuditReport {
  total_agents: number;
  outside_ad_count: number;
  inside_ad_count: number;
  detected_domains: string[];
  outside_ad_agents: FleetADAuditAgentItem[];
  inside_ad_agents: FleetADAuditAgentItem[];
  timestamp: string;
}

export async function fetchFleetOutsideADAudit(
  agentId: string,
): Promise<FleetOutsideADAuditReport> {
  const { data } = await axios.post(`/agents/${agentId}/ad-server/`, {
    action: "fleet_outside_ad_audit",
  });
  return data;
}

export async function joinAgentToADDomain(
  agentId: string,
  payload: {
    target_agent_id?: string;
    domain: string;
    username: string;
    password: string;
    ou_path?: string;
    dns_server?: string;
    new_hostname?: string;
    restart?: boolean;
  },
) {
  const { data } = await axios.post(`/agents/${agentId}/ad-server/`, {
    action: "join_ad_domain",
    ...payload,
  });
  return data;
}

export interface DiscoveredLANHost {
  ip_address: string;
  hostname: string;
  mac_address: string;
  discovery_source: string[];
  open_services: string[];
  estimated_type: string;
  smb_user: string;
  reachable: boolean;
  registered_in_rmm?: boolean;
  rmm_agent_id?: string;
  rmm_hostname?: string;
}

export interface UnitLANDiscoveryReport {
  server_hostname: string;
  server_platform: string;
  local_subnets: string[];
  total_found: number;
  computers_count: number;
  registered_count?: number;
  unregistered_count?: number;
  client_name?: string;
  site_name?: string;
  hosts: DiscoveredLANHost[];
  duration_ms: number;
  timestamp: string;
}

export async function runAgentLANDiscovery(
  agentId: string,
  subnet = "",
): Promise<UnitLANDiscoveryReport> {
  const { data } = await axios.post(`/agents/${agentId}/lan-discovery/`, {
    subnet,
  });
  return data;
}

export interface FleetSyncResult {
  status: string;
  total: number;
  online: number;
  offline: number;
  overdue: number;
  reboot_needed: number;
  recovered_count: number;
  recovered_hostnames: string[];
  demoted_count?: number;
  demoted_hostnames?: string[];
  deduplicated_count: number;
  deduplicated_hostnames: string[];
  timestamp: string;
}

export async function syncAndCleanupFleet(payload?: {
  deduplicate?: boolean;
  wake_overdue?: boolean;
}): Promise<FleetSyncResult> {
  const { data } = await axios.post("/agents/fleet-sync/", payload || {});
  return data;
}

export interface FleetBulkCLIResultItem {
  agent_id: string;
  hostname: string;
  client: string;
  site: string;
  plat: string;
  success: boolean;
  output: string;
}

export interface FleetBulkCLIResponse {
  status: string;
  total_targeted: number;
  success_count: number;
  failed_count: number;
  results: FleetBulkCLIResultItem[];
  timestamp: string;
}

export async function runFleetBulkCLI(payload: {
  target?: string;
  preset?: string;
  shell?: string;
  command?: string;
  timeout?: number;
  agent_ids?: string[];
  only_online?: boolean;
}): Promise<FleetBulkCLIResponse> {
  const { data } = await axios.post("/agents/fleet-bulk-cli/", payload);
  return data;
}

export async function pauseAgentMeshForBanking(agentId: string, keepalive = false): Promise<string> {
  if (keepalive && typeof fetch !== "undefined") {
    const token = useAuthStore().token;
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (token) headers.Authorization = `Token ${token}`;
    await fetch(`${getBaseUrl()}/agents/${agentId}/meshcentral/`, {
      method: "POST",
      headers,
      body: JSON.stringify({ action: "stop_mesh" }),
      keepalive: true,
      credentials: "include",
    });
    return "Modo Banco ativado";
  }

  const { data } = await axios.post(`/agents/${agentId}/meshcentral/`, { action: "stop_mesh" });
  return typeof data === "string" ? data : "Modo Banco ativado com sucesso.";
}

export interface ADDirectoryComputer {
  name: string;
  dns_hostname: string;
  distinguished_name: string;
  folder_group: string;
  folder_path: string;
  is_root_domain: boolean;
  is_default_container: boolean;
  enabled: boolean;
  is_dc: boolean;
  operating_system: string;
  os_version: string;
  description: string;
  last_logon: string;
  days_since_logon: number | null;
  in_tactical: boolean;
  sync_state: "online" | "offline" | "overdue" | "missing";
  agent_id: string | null;
  tactical_hostname: string | null;
  tactical_client: string | null;
  tactical_site: string | null;
  tactical_site_id: number | null;
  tactical_version: string | null;
  tactical_last_seen: string | null;
}

export interface ADDirectoryFolderSummary {
  folder: string;
  total: number;
  enabled: number;
  in_tactical: number;
  online: number;
  offline_or_overdue: number;
  missing: number;
  missing_enabled: number;
  missing_active_90d: number;
  is_default_container: boolean;
  is_root_domain: boolean;
}

export interface ADDirectoryProbeInfo {
  agent_id: string;
  hostname: string;
  client: string;
  site: string;
  monitoring_type?: string;
  domain?: string;
  is_dc?: boolean;
  part_of_domain?: boolean;
}

export interface ADDirectoryAuditReport {
  ok: boolean;
  error?: string;
  domain: string;
  netbios: string;
  default_nc: string;
  probe_agent: ADDirectoryProbeInfo;
  available_probes: ADDirectoryProbeInfo[];
  summary: {
    total_ad: number;
    enabled_ad: number;
    disabled_ad: number;
    present_in_tactical: number;
    online_in_tactical: number;
    offline_in_tactical: number;
    missing_from_tactical: number;
    missing_enabled: number;
    missing_active_90d: number;
    default_container_missing: number;
    root_domain_missing: number;
  };
  folder_summary: ADDirectoryFolderSummary[];
  diagnostics: string[];
  computers: ADDirectoryComputer[];
  timestamp: string;
}

export interface ADPushInstallResultItem {
  hostname: string;
  ip: string;
  success: boolean;
  method: string;
  status: string;
  detail: string;
}

export interface ADPushInstallResponse {
  ok: boolean;
  probe_agent: string;
  client: string;
  site: string;
  total: number;
  succeeded: number;
  failed: number;
  results: ADPushInstallResultItem[];
}

export interface ADPublishGPOResponse {
  ok: boolean;
  mode?: string;
  filename?: string;
  script?: string;
  netlogon_path?: string;
  gpo_linked?: boolean;
  gpupdate_count?: number;
  message?: string;
}

const adRequestConfig = {
  skipGlobalErrorNotify: true,
} as const;

export async function fetchADDirectoryAudit(
  options?:
    | string
    | {
        probeAgentId?: string;
        ldapServer?: string;
        username?: string;
        password?: string;
      },
): Promise<ADDirectoryAuditReport> {
  if (!options || typeof options === "string") {
    const params = options ? { probe_agent_id: options } : undefined;
    const { data } = await axios.get("/agents/ad-directory-audit/", {
      ...adRequestConfig,
      params,
    });
    return data;
  }
  if (options.ldapServer || options.username || options.password) {
    const { data } = await axios.post(
      "/agents/ad-directory-audit/",
      {
        probe_agent_id: options.probeAgentId || undefined,
        ldap_server: options.ldapServer || undefined,
        username: options.username || undefined,
        password: options.password || undefined,
      },
      adRequestConfig,
    );
    return data;
  }
  const params = options.probeAgentId ? { probe_agent_id: options.probeAgentId } : undefined;
  const { data } = await axios.get("/agents/ad-directory-audit/", {
    ...adRequestConfig,
    params,
  });
  return data;
}

export async function publishADGPO(payload: {
  mode: "publish_from_probe" | "generate_dc_script";
  site_id: number;
  probe_agent_id?: string;
  agent_type?: "both" | "workstation" | "server";
  rdp?: number;
  ping?: number;
  power?: number;
  banking_mode?: boolean;
  auto_link_gpo?: boolean;
  run_gpupdate?: boolean;
  api?: string;
}): Promise<ADPublishGPOResponse> {
  const { data } = await axios.post(
    "/agents/ad-publish-gpo/",
    {
      api: payload.api || getBaseUrl(),
      ...payload,
    },
    adRequestConfig,
  );
  return data;
}

export async function pushInstallADComputers(payload: {
  hostnames: string[];
  site_id: number;
  probe_agent_id?: string;
  agent_type?: "both" | "workstation" | "server";
  rdp?: number;
  ping?: number;
  power?: number;
  banking_mode?: boolean;
  force_reinstall?: boolean;
  username?: string;
  password?: string;
  api?: string;
}): Promise<ADPushInstallResponse> {
  const { data } = await axios.post(
    "/agents/ad-push-install/",
    {
      api: payload.api || getBaseUrl(),
      ...payload,
    },
    adRequestConfig,
  );
  return data;
}

export type InventoryCategory =
  | "ativo_monitorado"
  | "ativo_rede"
  | "passivo_rede"
  | "estacao_sem_agente"
  | "equipamento_medico"
  | "impressora_periferico";

export interface InventorySiteOption {
  id: number;
  name: string;
  client_id: number;
  client_name: string;
  label: string;
}

export interface InventoryCategoryOption {
  value: InventoryCategory;
  label: string;
}

export interface InventoryAssetRow {
  row_key: string;
  asset_id: number | null;
  agent_id: string | null;
  has_agent: boolean;
  client_id: number;
  client_name: string;
  site_id: number;
  site_name: string;
  category: InventoryCategory;
  category_label: string;
  asset_subtype: string;
  patrimonio: string;
  name: string;
  ip_address: string;
  public_ip: string;
  mac_address: string;
  manufacturer: string;
  model_name: string;
  serial_number: string;
  operating_system: string;
  logged_in_username: string;
  sector_location: string;
  responsible: string;
  status: string;
  source: string;
  notes: string;
  matched_agent_id: string | null;
  matched_agent_hostname: string;
  matched_agent_status: string;
  matched_agent_site: string;
  updated_at: string;
}

export interface InventorySummaryCounts {
  total: number;
  with_agent: number;
  agentless_total: number;
  ativos_rede: number;
  passivos_rede: number;
  estacoes_sem_agente: number;
  equipamentos_medicos: number;
  impressoras_perifericos: number;
  with_patrimonio: number;
  without_patrimonio: number;
  matched_with_agent: number;
}

export interface InventoryListResponse {
  sites: InventorySiteOption[];
  items: InventoryAssetRow[];
  summary: InventorySummaryCounts;
  categories: InventoryCategoryOption[];
  timestamp: string;
}

export interface InventoryImportRowInput {
  name: string;
  ip_address?: string;
  mac_address?: string;
  patrimonio?: string;
  manufacturer?: string;
  model_name?: string;
  serial_number?: string;
  operating_system?: string;
  sector_location?: string;
  responsible?: string;
  status?: string;
  notes?: string;
  category?: string;
  asset_subtype?: string;
}

export interface InventoryImportResponse {
  status: string;
  created: number;
  updated: number;
  skipped_agents: number;
  skipped_empty: number;
  site_name: string;
}

export async function fetchInventoryAssets(): Promise<InventoryListResponse> {
  const { data } = await axios.get("/agents/inventory-assets/", adRequestConfig);
  return data;
}

export async function saveInventoryAsset(payload: {
  asset_id?: number | null;
  agent_id?: string | null;
  site_id?: number;
  category?: InventoryCategory;
  asset_subtype?: string;
  patrimonio?: string;
  name?: string;
  ip_address?: string;
  mac_address?: string;
  manufacturer?: string;
  model_name?: string;
  serial_number?: string;
  operating_system?: string;
  sector_location?: string;
  responsible?: string;
  status?: string;
  notes?: string;
}): Promise<{ status: string; item: InventoryAssetRow }> {
  const { data } = await axios.post("/agents/inventory-assets/", payload, adRequestConfig);
  return data;
}

export async function deleteInventoryAsset(assetId: number): Promise<{ status: string }> {
  const { data } = await axios.delete(`/agents/inventory-assets/${assetId}/`, adRequestConfig);
  return data;
}

export async function importInventoryAssets(payload: {
  site_id: number;
  default_category: string;
  default_source?: string;
  replace_site_imports?: boolean;
  skip_matched_agents?: boolean;
  rows: InventoryImportRowInput[];
}): Promise<InventoryImportResponse> {
  const { data } = await axios.post("/agents/inventory-assets/import/", payload, adRequestConfig);
  return data;
}

export async function fetchAgentInventoryTag(agentId: string): Promise<InventoryAssetRow> {
  const { data } = await axios.get(`/agents/${agentId}/inventory-tag/`, adRequestConfig);
  return data;
}

export async function saveAgentInventoryTag(
  agentId: string,
  payload: {
    patrimonio?: string;
    sector_location?: string;
    responsible?: string;
    asset_subtype?: string;
    notes?: string;
  },
): Promise<InventoryAssetRow> {
  const { data } = await axios.post(`/agents/${agentId}/inventory-tag/`, payload, adRequestConfig);
  return data;
}

const ENTITY_BADGE_PALETTE = [
  "indigo-7",
  "teal-8",
  "blue-8",
  "cyan-9",
  "deep-purple-7",
  "blue-grey-8",
  "light-blue-9",
  "green-9",
];

export function getEntityBadgeColor(name?: string | null): string {
  const clean = String(name || "").trim().toLowerCase();
  if (!clean) return "blue-grey-7";
  let hash = 2166136261;
  for (let i = 0; i < clean.length; i += 1) {
    hash ^= clean.charCodeAt(i);
    hash = Math.imul(hash, 16777619) >>> 0;
  }
  return ENTITY_BADGE_PALETTE[hash % ENTITY_BADGE_PALETTE.length];
}


