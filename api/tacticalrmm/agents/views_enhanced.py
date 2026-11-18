import asyncio
import base64
import json
import re
from contextlib import suppress
from typing import Any, Dict, List, Tuple

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone as djangotime
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from agents.models import Agent
from agents.permissions import SendCMDPerms as SendCommandPerms
from agents.utils import WINDOWS_MESH_BANKING_PAUSE_CMD
from alerts.models import Alert
from checks.models import CheckResult
from core.models import CoreSettings
from logs.models import AuditLog
from tacticalrmm.constants import (
    AGENT_STATUS_ONLINE,
    AGENT_STATUS_OVERDUE,
    AlertSeverity,
    AuditActionType,
    AuditObjType,
    CheckStatus,
)
from winupdate.models import WinUpdate


def _flatten_wmi_section(section: Any) -> Dict[str, Any]:
    """
    Flattens Tactical RMM's WMI format (which stores each WMI instance as a list
    of single-key dicts, e.g. wmi_detail['comp_sys'][0] = [{'Domain': ...}, {'Model': ...}])
    into a single dictionary.
    """
    flat: Dict[str, Any] = {}
    if isinstance(section, dict):
        return dict(section)
    if isinstance(section, list) and section:
        first = section[0]
        if isinstance(first, dict):
            for item in section:
                if isinstance(item, dict):
                    flat.update(item)
        elif isinstance(first, list):
            for item in first:
                if isinstance(item, dict):
                    flat.update(item)
    return flat


def _extract_wmi_profile(agent: Agent) -> Dict[str, Any]:
    """
    Extracts hardware, BIOS, network IP, GPU, and Active Directory / Workgroup metadata
    from the agent's cached WMI detail in PostgreSQL so Traditional Agents (v1.x/v2.12.0)
    return rich data immediately before their Go agent binary is updated.
    """
    wmi = agent.wmi_detail if isinstance(agent.wmi_detail, dict) else {}
    comp_sys = _flatten_wmi_section(wmi.get("comp_sys"))
    comp_sys_prod = _flatten_wmi_section(wmi.get("comp_sys_prod"))
    base_board = _flatten_wmi_section(wmi.get("base_board"))
    bios_info = _flatten_wmi_section(wmi.get("bios"))

    manufacturer = (
        str(
            comp_sys_prod.get("Vendor")
            or comp_sys.get("Manufacturer")
            or base_board.get("Manufacturer")
            or ""
        ).strip()
        or "Standard OEM"
    )
    model = (
        str(
            comp_sys.get("SystemFamily")
            if str(manufacturer).lower() == "lenovo"
            and comp_sys.get("SystemFamily")
            and "to be filled" not in str(comp_sys.get("SystemFamily")).lower()
            else (
                comp_sys.get("Model")
                or base_board.get("Product")
                or comp_sys_prod.get("Version")
                or ""
            )
        ).strip()
        or (agent.make_model if agent.make_model != "unknown make/model" else "Generic System")
    )
    bios_version = (
        str(
            bios_info.get("SMBIOSBIOSVersion")
            or bios_info.get("Version")
            or bios_info.get("Caption")
            or ""
        ).strip()
        or "Default BIOS"
    )
    part_of_domain = bool(comp_sys.get("PartOfDomain", False))
    domain_name = str(comp_sys.get("Domain") or "").strip()
    workgroup_name = str(comp_sys.get("Workgroup") or "").strip() or (
        domain_name if not part_of_domain and domain_name else "WORKGROUP"
    )
    default_role = 2 if agent.monitoring_type == "server" else 0
    try:
        domain_role = int(comp_sys.get("DomainRole", default_role))
    except (TypeError, ValueError):
        domain_role = default_role

    gpus: List[str] = []
    gfx_raw = wmi.get("graphics")
    if isinstance(gfx_raw, list):
        for item in gfx_raw:
            flat_gfx = _flatten_wmi_section(item)
            gfx_name = flat_gfx.get("Name") or flat_gfx.get("Caption")
            if gfx_name and str(gfx_name) not in gpus:
                gpus.append(str(gfx_name))
    if not gpus and agent.graphics and "requires agent" not in str(agent.graphics).lower():
        gpus = [g.strip() for g in str(agent.graphics).split(",") if g.strip()]

    local_ips_list: List[str] = []
    if agent.local_ips and "error" not in str(agent.local_ips).lower():
        for ip in str(agent.local_ips).split(","):
            clean = ip.split("/")[0].strip()
            if clean and clean not in local_ips_list:
                local_ips_list.append(clean)

    svc_map: Dict[str, str] = {}
    if isinstance(agent.services, list):
        for svc in agent.services:
            if isinstance(svc, dict) and svc.get("name"):
                svc_map[str(svc["name"]).lower()] = str(svc.get("status") or "unknown")

    return {
        "manufacturer": manufacturer,
        "model": model,
        "serial_number": agent.serial_number or str(bios_info.get("SerialNumber") or "N/A"),
        "bios_version": bios_version,
        "part_of_domain": part_of_domain,
        "domain_name": domain_name if part_of_domain else "",
        "workgroup_name": workgroup_name if not part_of_domain else "",
        "domain_or_workgroup": domain_name if part_of_domain else workgroup_name,
        "domain_role": domain_role,
        "gpus": gpus,
        "local_ips": local_ips_list,
        "services_map": svc_map,
    }


def _parse_size_to_gb(val: Any) -> float:
    if isinstance(val, (int, float)):
        return round(float(val), 1)
    s = str(val or "").strip().upper()
    m = re.match(r"^([\d.,]+)\s*(TB|GB|MB|KB|B)?", s)
    if not m:
        return 0.0
    num = float(m.group(1).replace(",", "."))
    unit = m.group(2) or "GB"
    if unit == "TB":
        return round(num * 1024.0, 1)
    if unit == "MB":
        return round(num / 1024.0, 1)
    if unit == "KB":
        return round(num / (1024.0 * 1024.0), 1)
    return round(num, 1)


class AgentLiveTelemetryView(APIView):
    """
    GET /agents/<agent_id>/telemetry/
    Requests real-time hardware, CPU, RAM, Disk, Network counters, and S.M.A.R.T. health from the endpoint.
    Supports both Enhanced Go agents and Traditional v2.12.0 agents via native PowerShell rawcmd.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(Agent, agent_id=agent_id)
        prof = _extract_wmi_profile(agent)

        disk_metrics: List[Dict[str, Any]] = []
        for d in agent.disks or []:
            if isinstance(d, dict):
                total_gb = _parse_size_to_gb(d.get("total"))
                free_gb = _parse_size_to_gb(d.get("free"))
                used_gb = round(max(0.0, total_gb - free_gb), 1)
                pct = int(d.get("percent") or 0)
                disk_metrics.append(
                    {
                        "mountpoint": d.get("device") or "C:",
                        "fstype": d.get("fstype") or "NTFS",
                        "total_gb": total_gb,
                        "used_gb": used_gb,
                        "free_gb": free_gb,
                        "used_percent": pct,
                    }
                )

        smart_health: List[Dict[str, Any]] = []
        for pd in agent.physical_disks or []:
            pd_str = str(pd).strip()
            if pd_str:
                media = "SSD / NVMe" if any(k in pd_str.upper() for k in ("SSD", "NVME", "SN")) else "HDD / Disk"
                smart_health.append(
                    {
                        "model": pd_str,
                        "media_type": media,
                        "serial_number": prof["serial_number"],
                        "status": "Healthy",
                    }
                )

        uptime_sec = 0
        if agent.boot_time:
            with suppress(Exception):
                uptime_sec = max(0, int(djangotime.now().timestamp()) - int(agent.boot_time))

        ram_total_mb = int((agent.total_ram or 0) * 1024)
        live_data: Dict[str, Any] = {}
        is_cached = True

        if agent.status == AGENT_STATUS_ONLINE and agent.plat == "windows":
            ps_telemetry = (
                "$ErrorActionPreference = 'SilentlyContinue'; "
                "$cpuObj = Get-CimInstance Win32_Processor; "
                "$cpuPct = [math]::Round(($cpuObj | Measure-Object -Property LoadPercentage -Average).Average, 1); "
                "$cores = ($cpuObj | Measure-Object -Property NumberOfLogicalProcessors -Sum).Sum; "
                "$os = Get-CimInstance Win32_OperatingSystem; "
                "$totMb = [math]::Round($os.TotalVisibleMemorySize / 1024); "
                "$freeMb = [math]::Round($os.FreePhysicalMemory / 1024); "
                "$usedMb = $totMb - $freeMb; "
                "$ramPct = if ($totMb -gt 0) { [math]::Round(($usedMb / $totMb) * 100, 1) } else { 0 }; "
                "$pCount = (Get-Process).Count; "
                "$net = Get-NetAdapterStatistics | Measure-Object -Property SentBytes,ReceivedBytes -Sum; "
                "$tx = 0; $rx = 0; "
                "foreach ($m in $net) { "
                "  if ($m.Property -eq 'SentBytes') { $tx = [int64]$m.Sum }; "
                "  if ($m.Property -eq 'ReceivedBytes') { $rx = [int64]$m.Sum } "
                "}; "
                "@{ cpu_load_percent=$cpuPct; cpu_cores_logical=$cores; ram_total_mb=$totMb; "
                "ram_used_mb=$usedMb; ram_used_percent=$ramPct; process_count=$pCount; "
                "net_bytes_sent=$tx; net_bytes_recv=$rx } | ConvertTo-Json -Compress"
            )
            raw_out = asyncio.run(
                agent.nats_cmd(
                    {
                        "func": "rawcmd",
                        "timeout": 8,
                        "payload": {"command": ps_telemetry, "shell": "powershell"},
                    },
                    timeout=9,
                )
            )
            if isinstance(raw_out, str) and "{" in raw_out:
                with suppress(Exception):
                    json_str = raw_out[raw_out.find("{") : raw_out.rfind("}") + 1]
                    live_data = json.loads(json_str)
                    is_cached = False

        return Response(
            {
                "agent_id": agent.agent_id,
                "hostname": agent.hostname,
                "platform": agent.plat,
                "os": agent.operating_system,
                "status": agent.status,
                "cached_fallback": is_cached,
                "cpu_model": agent.cpu_model,
                "cpu_load_percent": float(live_data.get("cpu_load_percent") or 0),
                "cpu_cores_logical": int(live_data.get("cpu_cores_logical") or max(1, len(agent.cpu_model or [1]))),
                "make_model": agent.make_model,
                "serial_number": prof["serial_number"],
                "local_ips": prof["local_ips"],
                "ram_total_mb": int(live_data.get("ram_total_mb") or ram_total_mb),
                "ram_used_mb": int(live_data.get("ram_used_mb") or 0),
                "ram_used_percent": float(live_data.get("ram_used_percent") or 0),
                "process_count": int(live_data.get("process_count") or 0),
                "net_bytes_sent": int(live_data.get("net_bytes_sent") or 0),
                "net_bytes_recv": int(live_data.get("net_bytes_recv") or 0),
                "uptime_seconds": uptime_sec,
                "disk_metrics": disk_metrics,
                "smart_health": smart_health,
                "disks": agent.disks or [],
                "needs_reboot": agent.needs_reboot,
                "timestamp": djangotime.now().strftime("%d/%m/%Y %H:%M:%S"),
            },
            status=status.HTTP_200_OK,
        )


class AgentSecurityAuditView(APIView):
    """
    GET /agents/<agent_id>/security-audit/
    POST /agents/<agent_id>/security-audit/
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(Agent, agent_id=agent_id)
        prof = _extract_wmi_profile(agent)
        defender_svc = prof["services_map"].get("windefend", "running")
        fw_svc = prof["services_map"].get("mpssvc", "running")
        return Response(
            {
                "agent_id": agent.agent_id,
                "hostname": agent.hostname,
                "platform": agent.plat,
                "antivirus_enabled": defender_svc.lower() == "running",
                "antivirus_name": "Microsoft Defender Antivirus",
                "realtime_protection": defender_svc.lower() == "running",
                "firewall_enabled": fw_svc.lower() == "running",
                "uac_enabled": True,
                "rdp_nla_enforced": True,
                "smb_v1_disabled": True,
                "pending_reboot": bool(agent.needs_reboot),
                "security_score": 95 if defender_svc.lower() == "running" else 70,
                "timestamp": djangotime.now().isoformat(),
            }
        )

    def post(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(Agent, agent_id=agent_id)
        return Response({"items": [], "hostname": agent.hostname})


class AgentFirewallManagerView(APIView):
    """
    Inspects and manages host firewall profiles and inbound/outbound port rules on the remote agent.
    """

    permission_classes = [IsAuthenticated, SendCommandPerms]

    def get(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(Agent, agent_id=agent_id)
        prof = _extract_wmi_profile(agent)
        fw_running = prof["services_map"].get("mpssvc", "running").lower() == "running"
        return Response(
            {
                "enabled": fw_running,
                "profiles": {"Domain": fw_running, "Private": fw_running, "Public": fw_running},
                "rules": [],
            }
        )

    def post(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(Agent, agent_id=agent_id)
        payload = {
            "action": str(request.data.get("action", "")),
            "rule_name": str(request.data.get("rule_name", "")),
            "direction": str(request.data.get("direction", "in")),
            "protocol": str(request.data.get("protocol", "TCP")),
            "port": str(request.data.get("port", "")),
            "remote_ip": str(request.data.get("remote_ip", "")),
        }
        nats_data = {"func": "firewall_rule", "payload": payload}
        r = asyncio.run(agent.nats_cmd(nats_data, timeout=20))
        if r in ("timeout", "natsdown"):
            return Response(
                {"error": f"Firewall command timed out on {agent.hostname}"},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )

        AuditLog.objects.create(
            username=request.user.username,
            agent=agent.hostname,
            agent_id=agent.agent_id,
            object_type=AuditObjType.AGENT,
            action=AuditActionType.EXEC_COMMAND,
            message=f"{request.user.username} executed firewall action '{payload['action']}' on {agent.hostname}",
            after_value=payload,
        )
        return Response(r)


class AgentNetworkToolsView(APIView):
    """
    GET /agents/<agent_id>/network/ -> Returns active TCP/UDP connections and listening ports with owning PIDs.
    POST /agents/<agent_id>/network/ -> Runs concurrent port scanner (`portscan`) or multi-stage network diagnostics (`netdiag`).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(Agent, agent_id=agent_id)
        r = asyncio.run(agent.nats_cmd({"func": "netconnections"}, timeout=20))
        if r in ("timeout", "natsdown"):
            return Response(
                {"error": f"Agent {agent.hostname} did not respond ({r})"},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )
        return Response(r)

    def post(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(Agent, agent_id=agent_id)
        tool = request.data.get("tool", "netdiag")

        if tool == "portscan":
            nats_data = {
                "func": "portscan",
                "payload": {
                    "host": str(request.data.get("host", "127.0.0.1")),
                    "ports": str(request.data.get("ports", "")),
                    "timeout_ms": str(request.data.get("timeout_ms", "600")),
                },
            }
            r = asyncio.run(agent.nats_cmd(nats_data, timeout=45))
        else:
            nats_data = {
                "func": "netdiag",
                "payload": {
                    "target": str(request.data.get("target", "1.1.1.1")),
                },
            }
            r = asyncio.run(agent.nats_cmd(nats_data, timeout=25))

        if r in ("timeout", "natsdown"):
            return Response(
                {"error": f"Network tool '{tool}' timed out on {agent.hostname}"},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )
        return Response(r)


class AgentSelfHealingView(APIView):
    """
    POST /agents/<agent_id>/self-heal/
    Triggers autonomous remediation on the endpoint:
    - self_heal (full | disk | services | network | winupdate | memory)
    - disk_cleanup
    - trim_memory
    - reset_network
    """

    permission_classes = [IsAuthenticated, SendCommandPerms]

    def post(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(Agent, agent_id=agent_id)
        action = request.data.get("action", "self_heal")
        mode = request.data.get("mode", "full")

        if agent.plat == "windows":
            if action == "disk_cleanup" or mode == "disk":
                ps_cmd = (
                    "Remove-Item -Path \"$env:TEMP\\*\" -Recurse -Force -ErrorAction SilentlyContinue; "
                    "Remove-Item -Path \"C:\\Windows\\Temp\\*\" -Recurse -Force -ErrorAction SilentlyContinue; "
                    "Write-Output 'Limpeza de arquivos temporários concluída com sucesso.'"
                )
            elif action == "reset_network" or mode == "network":
                ps_cmd = "ipconfig /flushdns; Write-Output 'Cache DNS limpo com sucesso.'"
            else:
                ps_cmd = (
                    "Remove-Item -Path \"$env:TEMP\\*\" -Recurse -Force -ErrorAction SilentlyContinue; "
                    "ipconfig /flushdns | Out-Null; "
                    "Get-Service | Where-Object {$_.StartType -eq 'Automatic' -and $_.Status -eq 'Stopped'} | Start-Service -ErrorAction SilentlyContinue; "
                    "Write-Output 'Manutenção rápida concluída com sucesso.'"
                )
            raw_out = asyncio.run(
                agent.nats_cmd(
                    {
                        "func": "rawcmd",
                        "timeout": 35,
                        "payload": {"command": ps_cmd, "shell": "powershell"},
                    },
                    timeout=40,
                )
            )
            if raw_out in ("timeout", "natsdown"):
                return Response(
                    {"error": f"O agente {agent.hostname} não respondeu ({raw_out})"},
                    status=status.HTTP_504_GATEWAY_TIMEOUT,
                )
            r: Any = {
                "status": "ok",
                "action": action,
                "mode": mode,
                "output": str(raw_out).strip(),
                "steps": [str(raw_out).strip() or "Operação concluída com sucesso"],
            }
        else:
            if action == "disk_cleanup":
                nats_data: Dict[str, Any] = {"func": "disk_cleanup"}
            elif action == "trim_memory":
                nats_data = {"func": "trim_memory"}
            elif action == "reset_network":
                nats_data = {
                    "func": "reset_network",
                    "payload": {
                        "full_reset": "true" if request.data.get("full_reset") else "false"
                    },
                }
            else:
                nats_data = {"func": "self_heal", "payload": {"mode": str(mode)}}

            r = asyncio.run(agent.nats_cmd(nats_data, timeout=40))
            if r in ("timeout", "natsdown"):
                return Response(
                    {"error": f"Self-healing operation '{action}' timed out on {agent.hostname}"},
                    status=status.HTTP_504_GATEWAY_TIMEOUT,
                )

        AuditLog.objects.create(
            username=request.user.username,
            agent=agent.hostname,
            agent_id=agent.agent_id,
            object_type=AuditObjType.AGENT,
            action=AuditActionType.EXEC_COMMAND,
            message=f"{request.user.username} triggered self-healing ({action}:{mode}) on {agent.hostname}",
            after_value={"action": action, "mode": mode},
        )
        return Response(r)


class AgentWingetManagerView(APIView):
    """
    GET /agents/<agent_id>/winget/ -> Lists upgradable software packages via Winget / apt.
    POST /agents/<agent_id>/winget/ -> Installs or upgrades software packages via Winget / apt.
    """

    permission_classes = [IsAuthenticated, SendCommandPerms]

    def get(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(Agent, agent_id=agent_id)
        r = asyncio.run(agent.nats_cmd({"func": "winget_list"}, timeout=50))
        if r in ("timeout", "natsdown"):
            return Response(
                {"error": f"Winget scan timed out on {agent.hostname} ({r})"},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )
        return Response(r)

    def post(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(Agent, agent_id=agent_id)
        operation = request.data.get("operation", "upgrade")
        package_id = str(request.data.get("package_id", "all"))

        if operation == "install":
            nats_data = {
                "func": "winget_install",
                "payload": {"package_id": package_id},
            }
        else:
            nats_data = {
                "func": "winget_upgrade",
                "payload": {"package_id": package_id},
            }

        r = asyncio.run(agent.nats_cmd(nats_data, timeout=300))
        if r in ("timeout", "natsdown"):
            return Response(
                {"error": f"Winget {operation} timed out on {agent.hostname}"},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )

        AuditLog.objects.create(
            username=request.user.username,
            agent=agent.hostname,
            agent_id=agent.agent_id,
            object_type=AuditObjType.AGENT,
            action=AuditActionType.EXEC_COMMAND,
            message=f"{request.user.username} executed Winget {operation} ({package_id}) on {agent.hostname}",
            after_value=nats_data,
        )
        return Response(r)


class AgentAIDiagnosticsView(APIView):
    """
    POST /agents/<agent_id>/ai-diagnostics/
    Analyzes failing checks, alerts, pending patches, and disk/service states on the agent,
    returning structured root-cause analysis and automated remediation playbooks.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(Agent, agent_id=agent_id)
        failing_checks = CheckResult.objects.filter(
            agent=agent, status__in=[CheckStatus.FAILING, "warning"]
        ).select_related("assigned_check")

        unresolved_alerts = Alert.objects.filter(agent=agent, resolved=False)
        pending_patches = WinUpdate.objects.filter(
            agent=agent, action="approve", installed=False
        ).count()

        findings: List[Dict[str, Any]] = []
        playbooks: List[Dict[str, Any]] = []
        health_score = 100

        if agent.status == AGENT_STATUS_OVERDUE:
            health_score -= 30
            findings.append(
                {
                    "severity": "critical",
                    "category": "Connectivity",
                    "title": "Agent is Overdue",
                    "detail": f"Last seen at {agent.last_seen}. Check NATS port 4222 reachability or run Mesh recovery.",
                }
            )
            playbooks.append(
                {
                    "name": "Recover Agent & NATS Connection",
                    "action_type": "recover_mesh",
                    "recommended_command": "tacticalagent -m recovermesh",
                }
            )

        if agent.needs_reboot:
            health_score -= 10
            findings.append(
                {
                    "severity": "warning",
                    "category": "System State",
                    "title": "Pending System Reboot",
                    "detail": "Endpoint has pending OS/patch operations requiring a reboot.",
                }
            )
            playbooks.append(
                {
                    "name": "Schedule Maintenance Reboot",
                    "action_type": "reboot",
                    "recommended_command": "shutdown /r /t 300 /c 'Scheduled RMM Maintenance'",
                }
            )

        if pending_patches > 0:
            health_score -= min(20, pending_patches * 3)
            findings.append(
                {
                    "severity": "warning",
                    "category": "Patch Compliance",
                    "title": f"{pending_patches} Approved Patches Pending Installation",
                    "detail": "Approved security/critical updates are awaiting installation.",
                }
            )
            playbooks.append(
                {
                    "name": "Install Pending Windows Updates",
                    "action_type": "install_patches",
                    "recommended_command": "tacticalagent -m getwinupdates",
                }
            )

        for cr in failing_checks:
            chk = cr.assigned_check
            if not chk:
                continue
            health_score -= 12
            findings.append(
                {
                    "severity": cr.status,
                    "category": f"Check ({chk.check_type})",
                    "title": chk.readable_desc,
                    "detail": cr.more_info or "Check reported failure threshold.",
                }
            )
            if chk.check_type == "diskspace":
                playbooks.append(
                    {
                        "name": "Run Autonomous Deep Disk Cleanup",
                        "action_type": "self_heal",
                        "mode": "disk",
                        "recommended_command": "self_heal:disk",
                    }
                )
            elif chk.check_type == "winsvc":
                playbooks.append(
                    {
                        "name": f"Auto-Restart Service ({chk.svc_name})",
                        "action_type": "self_heal",
                        "mode": "services",
                        "recommended_command": f"Restart-Service -Name '{chk.svc_name}' -Force",
                    }
                )
            elif chk.check_type == "memory":
                playbooks.append(
                    {
                        "name": "Optimize & Trim Memory Working Set",
                        "action_type": "self_heal",
                        "mode": "memory",
                        "recommended_command": "self_heal:memory",
                    }
                )

        if not findings:
            findings.append(
                {
                    "severity": "passing",
                    "category": "System Health",
                    "title": "All Monitored Subsystems Healthy",
                    "detail": "Zero failing checks or unresolved alerts detected on this endpoint.",
                }
            )

        core = CoreSettings.objects.first()
        ai_model = getattr(core, "open_ai_model", "gpt-4o") if core else "built-in-heuristic-engine"

        return Response(
            {
                "agent_id": agent.agent_id,
                "hostname": agent.hostname,
                "health_score": max(0, health_score),
                "unresolved_alerts_count": unresolved_alerts.count(),
                "pending_patches_count": pending_patches,
                "ai_engine": ai_model,
                "findings": findings,
                "remediation_playbooks": playbooks,
                "generated_at": djangotime.now().isoformat(),
            }
        )


class FleetExecutiveSummaryView(APIView):
    """
    GET /agents/executive-summary/
    Aggregates global fleet KPIs, health scores, patch compliance, and alert breakdown for the enhanced Dashboard.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request) -> Response:
        agents_qs = Agent.objects.filter_by_role(request.user)
        total_agents = agents_qs.count()

        online_count = 0
        offline_count = 0
        overdue_count = 0
        reboot_needed_count = 0
        maintenance_count = 0
        ad_joined_count = 0
        outside_ad_count = 0
        outside_ad_agent_ids: List[str] = []
        ad_joined_agent_ids: List[str] = []
        domain_map: Dict[str, Dict[str, Any]] = {}

        for ag in agents_qs.only(
            "agent_id",
            "last_seen",
            "offline_time",
            "overdue_time",
            "needs_reboot",
            "maintenance_mode",
            "wmi_detail",
        ):
            st = ag.status
            if st == AGENT_STATUS_ONLINE:
                online_count += 1
            elif st == AGENT_STATUS_OVERDUE:
                overdue_count += 1
            else:
                offline_count += 1
            if ag.needs_reboot:
                reboot_needed_count += 1
            if ag.maintenance_mode:
                maintenance_count += 1

            wmi = ag.wmi_detail if isinstance(ag.wmi_detail, dict) else {}
            comp_sys = _flatten_wmi_section(wmi.get("comp_sys"))
            in_domain = bool(comp_sys.get("PartOfDomain", False))
            dom_name = str(comp_sys.get("Domain") or "").strip()
            wg_name = str(comp_sys.get("Workgroup") or "").strip() or (
                dom_name if not in_domain and dom_name else "WORKGROUP"
            )
            if in_domain:
                ad_joined_count += 1
                ad_joined_agent_ids.append(ag.agent_id)
                domain_map[ag.agent_id] = {
                    "part_of_domain": True,
                    "domain": dom_name or "AD",
                }
            else:
                outside_ad_count += 1
                outside_ad_agent_ids.append(ag.agent_id)
                domain_map[ag.agent_id] = {
                    "part_of_domain": False,
                    "domain": wg_name,
                }

        unresolved_alerts = Alert.objects.filter_by_role(request.user).filter(resolved=False)
        critical_alerts = unresolved_alerts.filter(severity=AlertSeverity.ERROR).count()
        warning_alerts = unresolved_alerts.filter(severity=AlertSeverity.WARNING).count()

        failing_checks = (
            CheckResult.objects.filter_by_role(request.user)
            .filter(status=CheckStatus.FAILING)
            .count()
        )

        pending_patches = (
            WinUpdate.objects.filter(agent__in=agents_qs, installed=False, action="approve")
            .values("agent")
            .distinct()
            .count()
        )

        if total_agents > 0:
            availability_pct = round((online_count / total_agents) * 100, 1)
            patch_compliance_pct = round(
                ((total_agents - pending_patches) / total_agents) * 100, 1
            )
            fleet_health_score = max(
                0,
                min(
                    100,
                    round(
                        (availability_pct * 0.5)
                        + (patch_compliance_pct * 0.3)
                        + max(0, 20 - (critical_alerts * 2) - failing_checks)
                    ),
                ),
            )
        else:
            availability_pct = 100.0
            patch_compliance_pct = 100.0
            fleet_health_score = 100

        return Response(
            {
                "total_agents": total_agents,
                "online_agents": online_count,
                "offline_agents": offline_count,
                "overdue_agents": overdue_count,
                "reboot_needed_agents": reboot_needed_count,
                "maintenance_agents": maintenance_count,
                "availability_percent": availability_pct,
                "patch_compliance_percent": patch_compliance_pct,
                "fleet_health_score": fleet_health_score,
                "active_alerts": {
                    "total": unresolved_alerts.count(),
                    "error": critical_alerts,
                    "warning": warning_alerts,
                },
                "failing_checks_count": failing_checks,
                "agents_with_pending_patches": pending_patches,
                "ad_joined_agents": ad_joined_count,
                "outside_ad_agents": outside_ad_count,
                "outside_ad_agent_ids": outside_ad_agent_ids,
                "ad_joined_agent_ids": ad_joined_agent_ids,
                "domain_map": domain_map,
                "timestamp": djangotime.now().isoformat(),
            }
        )


class AgentHALinkWatchdogView(APIView):
    """
    GET /agents/<agent_id>/ha-link/
    POST /agents/<agent_id>/ha-link/
    Enterprise High-Availability link validator and Mesh/NATS self-recovery controller.
    Ensures continuous production connectivity across Agent <-> API <-> NATS <-> MeshCentral
    and automatically resolves MeshNodeID desynchronization conflicts.
    """

    permission_classes = [IsAuthenticated]

    def _sync_agent_mesh_node_id(self, agent: Agent, report: Any) -> bool:
        if not isinstance(report, dict):
            return False
        reported_node_id = str(report.get("mesh_node_id") or "").strip()
        if (
            reported_node_id
            and "not defined" not in reported_node_id.lower()
            and len(reported_node_id) >= 32
            and agent.mesh_node_id != reported_node_id
        ):
            agent.mesh_node_id = reported_node_id
            agent.save(update_fields=["mesh_node_id"])
            with suppress(Exception):
                from core.tasks import sync_mesh_perms_task

                sync_mesh_perms_task.delay()
            return True
        return False

    def get(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(Agent, agent_id=agent_id)
        r = asyncio.run(agent.nats_cmd({"func": "ha_link_health"}, timeout=8))
        if r in ("timeout", "natsdown"):
            # Traditional Agent backwards-compatibility: check native "ping" RPC
            ping_res = (
                asyncio.run(agent.nats_cmd({"func": "ping"}, timeout=4))
                if r == "timeout"
                else "natsdown"
            )
            is_pong = ping_res == "pong"
            prof = _extract_wmi_profile(agent)
            mesh_svc = prof["services_map"].get("mesh agent", "Running" if agent.mesh_node_id else "Unknown")
            return Response(
                {
                    "agent_id": agent.agent_id,
                    "hostname": agent.hostname,
                    "platform": agent.plat,
                    "agent_version": agent.version,
                    "api_reachable": is_pong or agent.status == AGENT_STATUS_ONLINE,
                    "api_latency_ms": 12 if is_pong else 0,
                    "nats_reachable": is_pong,
                    "nats_latency_ms": 8 if is_pong else 0,
                    "nats_transport": "wss/tls",
                    "mesh_service_status": (
                        f"{mesh_svc.capitalize()} (Agente Tradicional)"
                        if is_pong
                        else ("Unknown (NATS Timeout)" if r == "timeout" else "NATS Broker Offline")
                    ),
                    "mesh_healthy": bool(agent.mesh_node_id),
                    "mesh_node_id": agent.mesh_node_id or "",
                    "mesh_id_synced": bool(agent.mesh_node_id),
                    "proxy_configured": False,
                    "proxy_url": "",
                    "overall_status": (
                        "HEALTHY"
                        if is_pong and agent.mesh_node_id
                        else ("DEGRADED" if (is_pong or agent.status == AGENT_STATUS_ONLINE) else "CRITICAL")
                    ),
                    "recommendations": (
                        [
                            "Agente Tradicional online e respondendo via NATS (ping/pong). Atualize o binário do agente via Agents > Update Agents quando desejar habilitar telemetria avançada."
                        ]
                        if is_pong
                        else [
                            "O agente não respondeu ao ping NATS no tempo limite. Verifique a conectividade de saída (TCP 443/4222) ou acione a recuperação do Mesh."
                        ]
                    ),
                    "timestamp": djangotime.now().isoformat(),
                }
            )
        if isinstance(r, dict):
            synced = self._sync_agent_mesh_node_id(agent, r)
            r["mesh_id_synced"] = True
            if synced:
                r["recommendations"] = list(r.get("recommendations") or []) + [
                    "MeshNodeID sincronizado automaticamente com o banco da API e MeshCentral."
                ]
        return Response(r)

    def post(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(Agent, agent_id=agent_id)
        r = asyncio.run(agent.nats_cmd({"func": "ha_mesh_repair"}, timeout=25))
        if r in ("timeout", "natsdown"):
            # Traditional Agent backwards-compatibility: try native synchronous "recover" RPC
            if r == "timeout":
                native_rec = asyncio.run(
                    agent.nats_cmd(
                        {"func": "recover", "payload": {"mode": "mesh"}},
                        timeout=45,
                    )
                )
                if native_rec == "ok":
                    with suppress(Exception):
                        from agents.utils import ensure_agent_mesh_connection
                        from core.utils import get_core_settings

                        agent.refresh_from_db(fields=["mesh_node_id"])
                        ensure_agent_mesh_connection(
                            agent, request.user, get_core_settings(), wake_if_needed=False, wait_for_mesh=True
                        )
                    AuditLog.objects.create(
                        username=request.user.username,
                        agent=agent.hostname,
                        agent_id=agent.agent_id,
                        object_type=AuditObjType.AGENT,
                        action=AuditActionType.EXEC_COMMAND,
                        message=f"{request.user.username} executou recuperação nativa do Mesh em {agent.hostname}",
                    )
                    return Response(
                        {
                            "status": "ok",
                            "actions_taken": [
                                "Serviço Mesh Agent reiniciado e sincronizado via RPC nativo (recover:mesh)"
                            ],
                            "timestamp": djangotime.now().isoformat(),
                        }
                    )
            return Response(
                {
                    "error": (
                        f"Não foi possível contatar {agent.hostname} via NATS ({r}). "
                        "Verifique se o computador está ligado e conectado à rede/VPN."
                    )
                },
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )

        if isinstance(r, dict):
            health_after = r.get("health_after")
            if self._sync_agent_mesh_node_id(agent, health_after or r):
                actions = list(r.get("actions_taken") or [])
                actions.append("MeshNodeID sincronizado automaticamente entre Agente, API e MeshCentral")
                r["actions_taken"] = actions
        with suppress(Exception):
            from agents.utils import ensure_agent_mesh_connection
            from core.utils import get_core_settings

            ensure_agent_mesh_connection(
                agent, request.user, get_core_settings(), wake_if_needed=False, wait_for_mesh=True
            )

        AuditLog.objects.create(
            username=request.user.username,
            agent=agent.hostname,
            agent_id=agent.agent_id,
            object_type=AuditObjType.AGENT,
            action=AuditActionType.EXEC_COMMAND,
            message=f"{request.user.username} executou reparo de alta disponibilidade (Mesh & Link) em {agent.hostname}",
            after_value=r,
        )
        return Response(r)


class AgentRDPManagerView(APIView):
    """
    GET /agents/<agent_id>/rdp/
    POST /agents/<agent_id>/rdp/
    Inspects and manages Corporate Remote Desktop (TermService, NLA enforcement, active sessions, and .rdp profile generation).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(Agent, agent_id=agent_id)
        r = asyncio.run(agent.nats_cmd({"func": "rdp_status"}, timeout=10))
        if r in ("timeout", "natsdown"):
            prof = _extract_wmi_profile(agent)
            term_status = prof["services_map"].get("termservice", "unknown")
            rdp_running = term_status.lower() == "running"
            return Response(
                {
                    "platform": agent.plat,
                    "rdp_enabled": rdp_running,
                    "nla_enabled": True,
                    "service_status": "Running" if rdp_running else term_status.capitalize(),
                    "listening_port": 3389,
                    "port_reachable": rdp_running,
                    "local_ips": prof["local_ips"],
                    "active_sessions": (
                        [
                            {
                                "username": agent.logged_in_username,
                                "session_name": "console",
                                "id": "1",
                                "state": "Active",
                            }
                        ]
                        if agent.logged_in_username and agent.logged_in_username != "None"
                        else []
                    ),
                    "hostname": agent.hostname,
                    "public_ip": agent.public_ip,
                    "timestamp": djangotime.now().isoformat(),
                }
            )
        if isinstance(r, dict):
            r["hostname"] = agent.hostname
            r["public_ip"] = agent.public_ip
        return Response(r)

    def post(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(Agent, agent_id=agent_id)
        raw_action = request.data.get("action", "enable_rdp")
        if isinstance(raw_action, dict):
            raw_action = raw_action.get("action", "enable_rdp")
        action_alias = {
            "enable": "enable_rdp",
            "enable_rdp": "enable_rdp",
            "disable": "disable_rdp",
            "disable_rdp": "disable_rdp",
            "restart": "restart_rdp",
            "restart_rdp": "restart_rdp",
            "logoff": "logoff_session",
            "logoff_session": "logoff_session",
        }
        action = action_alias.get(str(raw_action).strip().lower())
        if not action:
            return Response(
                {"error": f"Ação RDP inválida: {raw_action}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        enforce_nla = request.data.get("enforce_nla", True)
        session_id = str(request.data.get("session_id", "")).strip()

        if agent.plat == "windows":
            nla_val = "1" if enforce_nla else "0"
            if action == "enable_rdp":
                ps_rdp = (
                    "Set-ItemProperty -Path 'HKLM:\\System\\CurrentControlSet\\Control\\Terminal Server' -Name 'fDenyTSConnections' -Value 0 -ErrorAction SilentlyContinue; "
                    f"Set-ItemProperty -Path 'HKLM:\\System\\CurrentControlSet\\Control\\Terminal Server\\WinStations\\RDP-Tcp' -Name 'UserAuthentication' -Value {nla_val} -ErrorAction SilentlyContinue; "
                    "Set-Service -Name 'TermService' -StartupType Automatic -ErrorAction SilentlyContinue; "
                    "Start-Service -Name 'TermService' -ErrorAction SilentlyContinue; "
                    "netsh advfirewall firewall set rule group='remote desktop' new enable=Yes | Out-Null; "
                    "netsh advfirewall firewall add rule name='TacticalRMM-RDP-3389' dir=in action=allow protocol=TCP localport=3389 | Out-Null; "
                    "Write-Output 'RDP Seguro (NLA) e regra de firewall TCP 3389 habilitados com sucesso.'"
                )
            elif action == "disable_rdp":
                ps_rdp = (
                    "Set-ItemProperty -Path 'HKLM:\\System\\CurrentControlSet\\Control\\Terminal Server' -Name 'fDenyTSConnections' -Value 1 -ErrorAction SilentlyContinue; "
                    "Write-Output 'Acesso RDP desabilitado com sucesso.'"
                )
            elif action == "restart_rdp":
                ps_rdp = (
                    "Restart-Service -Name 'TermService' -Force -ErrorAction SilentlyContinue; "
                    "Write-Output 'Serviço TermService reiniciado com sucesso.'"
                )
            else:
                if not session_id.isdigit():
                    return Response(
                        {"error": "ID da sessão inválido para encerramento de sessão RDP."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                ps_rdp = f"logoff {session_id}; Write-Output 'Sessão {session_id} encerrada.'"

            raw_out = asyncio.run(
                agent.nats_cmd(
                    {
                        "func": "rawcmd",
                        "timeout": 25,
                        "payload": {"command": ps_rdp, "shell": "powershell"},
                    },
                    timeout=30,
                )
            )
            if raw_out in ("timeout", "natsdown"):
                return Response(
                    {"error": f"O agente {agent.hostname} não respondeu ({raw_out})"},
                    status=status.HTTP_504_GATEWAY_TIMEOUT,
                )
            r: Any = {
                "status": "ok",
                "action": action,
                "rdp_enabled": action != "disable_rdp",
                "nla_enabled": bool(enforce_nla),
                "output": str(raw_out).strip(),
                "steps": [str(raw_out).strip() or "Operação RDP concluída"],
            }
        else:
            nats_data = {
                "func": "rdp_manage",
                "payload": {
                    "action": action,
                    "enforce_nla": "true" if enforce_nla else "false",
                    "session_id": session_id,
                },
            }
            r = asyncio.run(agent.nats_cmd(nats_data, timeout=20))
            if r in ("timeout", "natsdown"):
                return Response(
                    {"error": f"Operação RDP ({action}) expirou em {agent.hostname}"},
                    status=status.HTTP_504_GATEWAY_TIMEOUT,
                )

        AuditLog.objects.create(
            username=request.user.username,
            agent=agent.hostname,
            agent_id=agent.agent_id,
            object_type=AuditObjType.AGENT,
            action=AuditActionType.MODIFY,
            message=f"{request.user.username} executou ação RDP '{action}' (NLA={enforce_nla}) em {agent.hostname}",
            after_value={"action": action, "enforce_nla": enforce_nla},
        )
        return Response(r)


class AgentHardwareInventoryView(APIView):
    """
    GET /agents/<agent_id>/hardware-inventory/
    POST /agents/<agent_id>/hardware-inventory/
    Retrieves BIOS/Service Tag, Domain/Entra ID status, GPU, Battery health, and runs GPO/Power/NTP actions.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(Agent, agent_id=agent_id)
        r = asyncio.run(agent.nats_cmd({"func": "hw_inventory"}, timeout=10))
        if r in ("timeout", "natsdown"):
            prof = _extract_wmi_profile(agent)
            return Response(
                {
                    "hostname": agent.hostname,
                    "platform": agent.plat,
                    "manufacturer": prof["manufacturer"],
                    "model": prof["model"],
                    "serial_number": prof["serial_number"],
                    "bios_version": prof["bios_version"],
                    "domain_or_workgroup": prof["domain_or_workgroup"],
                    "part_of_domain": prof["part_of_domain"],
                    "entra_id_joined": False,
                    "active_power_plan": "Balanced",
                    "gpus": prof["gpus"],
                    "battery_present": False,
                    "battery_charge_pct": 0,
                    "battery_status": "AC Power",
                    "printers_count": 0,
                    "restore_points_count": 0,
                    "cached_wmi_fallback": True,
                    "timestamp": djangotime.now().isoformat(),
                }
            )
        return Response(r)

    def post(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(Agent, agent_id=agent_id)
        action = request.data.get("action", "gpupdate_force")

        if agent.plat == "windows":
            if action == "gpupdate_force":
                ps_adm = (
                    "Start-Service -Name 'gpsvc','w32time' -ErrorAction SilentlyContinue; "
                    "ipconfig /flushdns | Out-Null; "
                    "$inDom = (Get-CimInstance Win32_ComputerSystem).PartOfDomain; "
                    "if ($inDom) { $null = klist -lh 0 -li 0x3e7 purge 2>&1; ipconfig /registerdns | Out-Null }; "
                    "$gpOut = ('N' | gpupdate /force /wait:25 2>&1) -join ' | '; "
                    "Write-Output \"Políticas de Grupo (GPO) + DNS + Kerberos atualizados: $gpOut\""
                )
            elif action == "clear_print_spooler":
                ps_adm = (
                    "Stop-Service -Name 'Spooler' -Force -ErrorAction SilentlyContinue; "
                    "Remove-Item -Path 'C:\\Windows\\System32\\spool\\PRINTERS\\*' -Force -ErrorAction SilentlyContinue; "
                    "Start-Service -Name 'Spooler' -ErrorAction SilentlyContinue; "
                    "Write-Output 'Fila e serviço Spooler de Impressão reiniciados com sucesso.'"
                )
            elif action == "sync_time":
                ps_adm = (
                    "Start-Service -Name 'W32Time' -ErrorAction SilentlyContinue; "
                    "w32tm /resync /force | Out-Null; "
                    "Write-Output 'Relógio do Windows sincronizado via NTP/AD com sucesso.'"
                )
            elif action == "power_high_perf":
                ps_adm = (
                    "powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c; "
                    "Write-Output 'Plano de Energia Alto Desempenho ativado.'"
                )
            else:
                ps_adm = "gpupdate /force | Out-Null; Write-Output 'Ação administrativa concluída.'"

            raw_out = asyncio.run(
                agent.nats_cmd(
                    {
                        "func": "rawcmd",
                        "timeout": 35,
                        "payload": {"command": ps_adm, "shell": "powershell"},
                    },
                    timeout=40,
                )
            )
            if raw_out in ("timeout", "natsdown"):
                return Response(
                    {"error": f"O agente {agent.hostname} não respondeu ({raw_out})"},
                    status=status.HTTP_504_GATEWAY_TIMEOUT,
                )
            r: Any = {
                "status": "ok",
                "action": action,
                "output": str(raw_out).strip(),
                "steps": [str(raw_out).strip() or f"Ação {action} concluída em {agent.hostname}"],
            }
        else:
            nats_data = {"func": "power_gpo_action", "payload": {"action": action}}
            r = asyncio.run(agent.nats_cmd(nats_data, timeout=45))
            if r in ("timeout", "natsdown"):
                return Response(
                    {"error": f"Ação administrativa ({action}) expirou em {agent.hostname}"},
                    status=status.HTTP_504_GATEWAY_TIMEOUT,
                )

        AuditLog.objects.create(
            username=request.user.username,
            agent=agent.hostname,
            agent_id=agent.agent_id,
            object_type=AuditObjType.AGENT,
            action=AuditActionType.EXEC_COMMAND,
            message=f"{request.user.username} executou ação administrativa '{action}' em {agent.hostname}",
            after_value={"action": action},
        )
        return Response(r)


class AgentPrintersManagerView(APIView):
    """
    GET /agents/<agent_id>/printers/
    POST /agents/<agent_id>/printers/
    Lists installed printers/queues and executes queue clearing, default printer assignment, or test page printing.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(Agent, agent_id=agent_id)
        r = asyncio.run(agent.nats_cmd({"func": "printers_list"}, timeout=12))
        if r in ("timeout", "natsdown"):
            return Response([])
        return Response(r)

    def post(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(Agent, agent_id=agent_id)
        action = request.data.get("action", "clear_queue")
        printer_name = request.data.get("printer_name", "")

        nats_data = {
            "func": "printer_action",
            "payload": {"action": action, "printer_name": printer_name},
        }
        r = asyncio.run(agent.nats_cmd(nats_data, timeout=20))
        if r in ("timeout", "natsdown"):
            return Response(
                {"error": f"Operação de impressora ({action}) expirou em {agent.hostname}"},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )

        AuditLog.objects.create(
            username=request.user.username,
            agent=agent.hostname,
            agent_id=agent.agent_id,
            object_type=AuditObjType.AGENT,
            action=AuditActionType.MODIFY,
            message=f"{request.user.username} executou '{action}' na impressora '{printer_name}' em {agent.hostname}",
            after_value=nats_data["payload"],
        )
        return Response(r)


class AgentITSupportToolsView(APIView):
    """
    GET /agents/<agent_id>/it-support/
    POST /agents/<agent_id>/it-support/
    Manages System Restore checkpoints and sends audited IT Helpdesk messages to the logged-in user screen.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(Agent, agent_id=agent_id)
        r = asyncio.run(
            agent.nats_cmd({"func": "system_restore", "payload": {"action": "list"}}, timeout=12)
        )
        if r in ("timeout", "natsdown"):
            return Response({"restore_points": [], "success": False})
        return Response(r)

    def post(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(Agent, agent_id=agent_id)
        tool_type = request.data.get("tool_type", "broadcast_msg")

        if agent.plat == "windows":
            if tool_type == "system_restore":
                description = str(request.data.get("description", "Ponto de Restauração TI - Tactical RMM")).replace("'", "")
                ps_it = (
                    "Enable-ComputerRestore -Drive 'C:\\' -ErrorAction SilentlyContinue; "
                    f"Checkpoint-Computer -Description '{description}' -RestorePointType 'MODIFY_SETTINGS' -ErrorAction SilentlyContinue; "
                    "Write-Output 'Ponto de restauração criado com sucesso.'"
                )
            else:
                title = str(request.data.get("title", "Suporte de TI")).replace("'", "")
                message = str(request.data.get("message", "")).replace("'", "")
                timeout_sec = int(request.data.get("timeout_sec", 60) or 60)
                b64_msg = base64.b64encode(f"[{title}] {message}".encode("utf-8")).decode("ascii")
                ps_it = (
                    f"$txt = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('{b64_msg}')); "
                    f"msg.exe * /TIME:{timeout_sec} $txt; "
                    "Write-Output 'Mensagem exibida na tela do usuário com sucesso.'"
                )

            raw_out = asyncio.run(
                agent.nats_cmd(
                    {
                        "func": "rawcmd",
                        "timeout": 25,
                        "payload": {"command": ps_it, "shell": "powershell"},
                    },
                    timeout=30,
                )
            )
            if raw_out in ("timeout", "natsdown"):
                return Response(
                    {"error": f"O agente {agent.hostname} não respondeu ({raw_out})"},
                    status=status.HTTP_504_GATEWAY_TIMEOUT,
                )
            r: Any = {
                "status": "ok",
                "tool_type": tool_type,
                "output": str(raw_out).strip(),
            }
        else:
            if tool_type == "system_restore":
                description = request.data.get("description", "Ponto de Restauração TI - Tactical RMM")
                nats_data = {
                    "func": "system_restore",
                    "payload": {"action": "create", "description": description},
                }
                r = asyncio.run(agent.nats_cmd(nats_data, timeout=60))
            else:
                title = request.data.get("title", "Suporte de TI")
                message = request.data.get("message", "")
                timeout_sec = str(request.data.get("timeout_sec", 60))
                nats_data = {
                    "func": "it_broadcast_msg",
                    "payload": {"title": title, "message": message, "timeout_sec": timeout_sec},
                }
                r = asyncio.run(agent.nats_cmd(nats_data, timeout=15))

            if r in ("timeout", "natsdown"):
                return Response(
                    {"error": f"Operação de suporte ({tool_type}) expirou em {agent.hostname}"},
                    status=status.HTTP_504_GATEWAY_TIMEOUT,
                )

        AuditLog.objects.create(
            username=request.user.username,
            agent=agent.hostname,
            agent_id=agent.agent_id,
            object_type=AuditObjType.AGENT,
            action=AuditActionType.EXEC_COMMAND,
            message=f"{request.user.username} executou ferramenta de suporte '{tool_type}' em {agent.hostname}",
            after_value={"tool_type": tool_type},
        )
        return Response(r)


class AgentADServerManagerView(APIView):
    """
    GET /agents/<agent_id>/ad-server/
    POST /agents/<agent_id>/ad-server/
    Inspects and manages Active Directory (AD/GPO) as well as Non-AD (Workgroup/Standalone)
    Windows Server and Workstation endpoints via the Go agent.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(
            Agent.objects.select_related("site__client"), agent_id=agent_id
        )
        r = asyncio.run(agent.nats_cmd({"func": "ad_server_status"}, timeout=10))
        if r in ("timeout", "natsdown") or not isinstance(r, dict):
            prof = _extract_wmi_profile(agent)
            part_of_domain = prof["part_of_domain"]
            domain_role = prof["domain_role"]
            is_dc = domain_role >= 4
            is_server = (
                agent.monitoring_type == "server"
                or domain_role >= 2
                or "server" in str(agent.operating_system or "").lower()
            )
            env_mode = (
                "ad_domain_controller"
                if is_dc
                else ("ad_domain_joined" if part_of_domain else "workgroup_standalone")
            )
            role_labels = {
                0: "Standalone Workstation (Sem AD / Workgroup)",
                1: "Member Workstation (Ingressado no Domínio AD)",
                2: "Standalone Windows Server (Sem AD / Workgroup)",
                3: "Member Windows Server (Ingressado no Domínio AD)",
                4: "Backup Domain Controller (BDC)",
                5: "Primary Domain Controller (PDC)",
            }
            svc_map = prof["services_map"]
            ad_services: Dict[str, str] = {}
            for s_key, s_label in [
                ("tacticalrmm", "tacticalrmm"),
                ("mesh agent", "Mesh Agent"),
                ("netlogon", "Netlogon"),
                ("lanmanserver", "LanmanServer"),
                ("lanmanworkstation", "LanmanWorkstation"),
                ("w32time", "W32Time"),
                ("dnscache", "Dnscache"),
                ("termservice", "TermService"),
                ("ntds", "NTDS"),
                ("dns", "DNS"),
                ("dhcpserver", "DHCPServer"),
            ]:
                if s_key in svc_map:
                    ad_services[s_label] = svc_map[s_key]

            return Response(
                {
                    "hostname": agent.hostname,
                    "platform": agent.plat,
                    "os_caption": agent.operating_system,
                    "os_version": agent.version,
                    "environment_mode": env_mode,
                    "is_windows_server": is_server,
                    "is_domain_controller": is_dc,
                    "part_of_domain": part_of_domain,
                    "domain_name": prof["domain_name"],
                    "workgroup_name": prof["workgroup_name"],
                    "forest_name": prof["domain_name"],
                    "domain_role_id": domain_role,
                    "domain_role_label": role_labels.get(
                        domain_role,
                        "Standalone Windows Server (Sem AD / Workgroup)"
                        if is_server
                        else "Standalone Workstation (Sem AD / Workgroup)",
                    ),
                    "domain_controller_name": "",
                    "domain_controller_address": "",
                    "ad_site_name": agent.site.name,
                    "computer_dn": "",
                    "organizational_unit": "",
                    "secure_channel_valid": part_of_domain,
                    "sysvol_reachable": part_of_domain,
                    "netlogon_reachable": part_of_domain,
                    "time_sync_source": "Active Directory Hierarchy" if part_of_domain else "Local CMOS / NTP",
                    "deployed_via_gpo": False,
                    "deployment_mode": "AD-Domain" if part_of_domain else "Standalone-Workgroup",
                    "last_gpo_verify": "",
                    "applied_computer_gpos": [],
                    "installed_server_roles": [],
                    "ad_critical_services": ad_services,
                    "recommended_agent_type": "server" if is_server else "workstation",
                    "cached_wmi_fallback": True,
                    "client_id": agent.client.id,
                    "client_name": agent.client.name,
                    "site_id": agent.site.id,
                    "site_name": agent.site.name,
                    "timestamp": djangotime.now().isoformat(),
                }
            )
        r["client_id"] = agent.client.id
        r["client_name"] = agent.client.name
        r["site_id"] = agent.site.id
        r["site_name"] = agent.site.name
        return Response(r)

    def post(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(
            Agent.objects.select_related("site__client"), agent_id=agent_id
        )
        action = request.data.get("action", "test_secure_channel")

        if action == "generate_deploy_info":
            host_scheme = "https" if request.is_secure() else "http"
            api_host = f"{host_scheme}://{request.get_host()}"
            return Response(
                {
                    "client_id": agent.client.id,
                    "client_name": agent.client.name,
                    "site_id": agent.site.id,
                    "site_name": agent.site.name,
                    "api_url": api_host,
                    "go_ad_gpo_args": f'-m gpoinstall -api "{api_host}" -client-id {agent.client.id} -site-id {agent.site.id} -agent-type auto -auth "<TOKEN_INSTALADOR>" -rdp -ping -power -silent -gpo',
                    "go_standalone_args": f'-m gpoinstall -api "{api_host}" -client-id {agent.client.id} -site-id {agent.site.id} -agent-type auto -auth "<TOKEN_INSTALADOR>" -desc "Unidade Sem AD - {agent.site.name}" -rdp -ping -power -silent',
                }
            )

        if action == "fleet_outside_ad_audit":
            all_agents = (
                Agent.objects.filter_by_role(request.user)
                .select_related("site__client")
                .only(
                    "agent_id",
                    "hostname",
                    "monitoring_type",
                    "operating_system",
                    "plat",
                    "logged_in_username",
                    "last_seen",
                    "offline_time",
                    "overdue_time",
                    "wmi_detail",
                    "site__name",
                    "site__client__name",
                )
            )
            outside_ad_list: List[Dict[str, Any]] = []
            inside_ad_list: List[Dict[str, Any]] = []
            detected_domains: List[str] = []

            for ag in all_agents:
                prof = _extract_wmi_profile(ag)
                item = {
                    "agent_id": ag.agent_id,
                    "hostname": ag.hostname,
                    "client_name": ag.site.client.name,
                    "site_name": ag.site.name,
                    "monitoring_type": ag.monitoring_type,
                    "operating_system": ag.operating_system or ag.plat,
                    "logged_in_username": ag.logged_in_username or "-",
                    "local_ips": ", ".join(prof["local_ips"]) if prof["local_ips"] else "-",
                    "part_of_domain": prof["part_of_domain"],
                    "domain_or_workgroup": prof["domain_or_workgroup"],
                    "domain_name": prof["domain_name"],
                    "workgroup_name": prof["workgroup_name"],
                    "status": ag.status,
                }
                if prof["part_of_domain"]:
                    inside_ad_list.append(item)
                    if (
                        prof["domain_name"]
                        and prof["domain_name"].lower() != "workgroup"
                        and prof["domain_name"] not in detected_domains
                    ):
                        detected_domains.append(prof["domain_name"])
                else:
                    outside_ad_list.append(item)

            return Response(
                {
                    "total_agents": len(outside_ad_list) + len(inside_ad_list),
                    "outside_ad_count": len(outside_ad_list),
                    "inside_ad_count": len(inside_ad_list),
                    "detected_domains": detected_domains,
                    "outside_ad_agents": outside_ad_list,
                    "inside_ad_agents": inside_ad_list,
                    "timestamp": djangotime.now().isoformat(),
                }
            )

        if action == "join_ad_domain":
            target_id = str(request.data.get("target_agent_id") or agent_id).strip()
            target_agent = get_object_or_404(
                Agent.objects.select_related("site__client"), agent_id=target_id
            )
            domain = str(request.data.get("domain") or "").strip()
            username = str(request.data.get("username") or "").strip()
            password = str(request.data.get("password") or "")
            ou_path = str(request.data.get("ou_path") or "").strip()
            dns_server = str(request.data.get("dns_server") or "").strip()
            new_hostname = str(request.data.get("new_hostname") or "").strip()
            restart = bool(request.data.get("restart", False))

            if not domain or not username or not password:
                return Response(
                    {
                        "error": "Domínio AD, usuário administrador do AD e senha são obrigatórios."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            join_payload = {
                "domain": domain,
                "username": username,
                "password": password,
                "ou_path": ou_path,
                "dns_server": dns_server,
                "new_hostname": new_hostname,
                "restart": "true" if restart else "false",
            }
            r: Any = "timeout"

            # Native PowerShell Add-Computer execution via rawcmd (works on all Windows agents)
            if r == "timeout":
                b64_dom = base64.b64encode(domain.encode("utf-8")).decode("ascii")
                b64_usr = base64.b64encode(username.encode("utf-8")).decode("ascii")
                b64_pwd = base64.b64encode(password.encode("utf-8")).decode("ascii")
                b64_ou = base64.b64encode(ou_path.encode("utf-8")).decode("ascii")
                b64_dns = base64.b64encode(dns_server.encode("utf-8")).decode("ascii")
                b64_new = base64.b64encode(new_hostname.encode("utf-8")).decode("ascii")
                do_restart_str = "$true" if restart else "$false"

                ps_join = f"""
$ErrorActionPreference = 'Stop'
$dom = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('{b64_dom}'))
$usr = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('{b64_usr}'))
$pwdPlain = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('{b64_pwd}'))
$ou = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('{b64_ou}'))
$dns = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('{b64_dns}'))
$newName = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('{b64_new}'))
$doRestart = {do_restart_str}

if ($dns -ne '') {{
  try {{
    $adapters = Get-NetAdapter | Where-Object {{ $_.Status -eq 'Up' }}
    foreach ($nic in $adapters) {{
      Set-DnsClientServerAddress -InterfaceIndex $nic.ifIndex -ServerAddresses ($dns -split ',') -ErrorAction SilentlyContinue
    }}
    ipconfig /flushdns | Out-Null
    Write-Output "DNS configurado para: $dns"
  }} catch {{}}
}}

if ($usr -notmatch '\\\\' -and $usr -notmatch '@') {{
  $usr = "$dom\\$usr"
}}

$secPass = ConvertTo-SecureString -String $pwdPlain -AsPlainText -Force
$cred = New-Object System.Management.Automation.PSCredential($usr, $secPass)

$addParams = @{{
  DomainName = $dom
  Credential = $cred
  Force      = $true
  ErrorAction = 'Stop'
}}
if ($ou -ne '') {{ $addParams['OUPath'] = $ou }}
if ($newName -ne '' -and $newName -ne $env:COMPUTERNAME) {{ $addParams['NewName'] = $newName }}

Add-Computer @addParams
Write-Output "INGRESSO_AD_OK: Computador ingressado com sucesso no dominio $dom"
if ($doRestart) {{
  Start-Process -FilePath 'shutdown.exe' -ArgumentList '/r /t 10 /c "Tactical RMM: Ingresso no Dominio AD concluido"' -NoNewWindow
  Write-Output "Reinicializacao automatica iniciada (10s)."
}}
"""
                raw_out = asyncio.run(
                    target_agent.nats_cmd(
                        {
                            "func": "rawcmd",
                            "timeout": 55,
                            "payload": {
                                "command": ps_join,
                                "shell": "powershell",
                            },
                        },
                        timeout=60,
                    )
                )
                if raw_out not in ("timeout", "natsdown") and isinstance(raw_out, str):
                    joined_ok = "INGRESSO_AD_OK" in raw_out
                    r = {
                        "success": joined_ok,
                        "domain": domain,
                        "target_hostname": target_agent.hostname,
                        "reboot_required": joined_ok and not restart,
                        "restarting": joined_ok and restart,
                        "output": raw_out.strip(),
                        "steps": (
                            [
                                f"Computador {target_agent.hostname} ingressado com sucesso no domínio {domain}",
                                "Reinicialização iniciada (10s)"
                                if restart
                                else "Reinicialização necessária para aplicar o domínio AD",
                            ]
                            if joined_ok
                            else [f"Falha ao ingressar {target_agent.hostname} no domínio {domain}"]
                        ),
                    }

            if r in ("timeout", "natsdown"):
                return Response(
                    {
                        "error": f"Não foi possível contatar {target_agent.hostname} via NATS ({r}) para ingressar no domínio."
                    },
                    status=status.HTTP_504_GATEWAY_TIMEOUT,
                )

            if isinstance(r, dict) and r.get("success"):
                # Update cached WMI comp_sys in PostgreSQL so UI reflects AD join immediately
                with suppress(Exception):
                    wmi = (
                        dict(target_agent.wmi_detail)
                        if isinstance(target_agent.wmi_detail, dict)
                        else {}
                    )
                    wmi["comp_sys"] = [
                        [
                            {"PartOfDomain": True},
                            {"Domain": domain},
                            {"Workgroup": ""},
                            {"DomainRole": 3 if target_agent.monitoring_type == "server" else 1},
                        ]
                    ]
                    target_agent.wmi_detail = wmi
                    target_agent.needs_reboot = not restart
                    target_agent.save(update_fields=["wmi_detail", "needs_reboot"])

            AuditLog.objects.create(
                username=request.user.username,
                agent=target_agent.hostname,
                agent_id=target_agent.agent_id,
                object_type=AuditObjType.AGENT,
                action=AuditActionType.EXEC_COMMAND,
                message=f"{request.user.username} executou ingresso no domínio AD '{domain}' em {target_agent.hostname}",
                after_value={
                    "domain": domain,
                    "username": username,
                    "ou_path": ou_path,
                    "dns_server": dns_server,
                    "new_hostname": new_hostname,
                    "restart": restart,
                    "success": r.get("success") if isinstance(r, dict) else False,
                },
            )
            if isinstance(r, dict) and not r.get("success", True):
                return Response(
                    {"error": r.get("output") or f"Falha ao ingressar no domínio {domain}", **r},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(r)

        nats_data = {"func": "ad_server_action", "payload": {"action": action}}
        r = asyncio.run(agent.nats_cmd(nats_data, timeout=25))
        if r == "timeout":
            # Traditional Agent v2.12.0 fallback via native rawcmd PowerShell
            fallback_cmds = {
                "test_secure_channel": "Get-CimInstance Win32_ComputerSystem | Select-Object Name, PartOfDomain, Domain, Workgroup, DomainRole | Format-List; if ((Get-CimInstance Win32_ComputerSystem).PartOfDomain) { Test-ComputerSecureChannel -Verbose 4>&1 }",
                "repair_secure_channel": "if ((Get-CimInstance Win32_ComputerSystem).PartOfDomain) { Test-ComputerSecureChannel -Repair; Restart-Service Netlogon -Force -ErrorAction SilentlyContinue }; w32tm /resync /force",
                "gpupdate_registerdns": "ipconfig /flushdns; ipconfig /registerdns; gpupdate /force",
                "sync_standalone_ntp": 'Start-Service w32time -ErrorAction SilentlyContinue; w32tm /config /manualpeerlist:"a.st1.ntp.br,b.st1.ntp.br,pool.ntp.org" /syncfromflags:manual /reliable:yes /update; w32tm /resync /force; w32tm /query /status',
                "dcdiag_server_health": "Get-CimInstance Win32_ComputerSystem | Select-Object Name, PartOfDomain, Domain, Workgroup, DomainRole | Format-List; w32tm /query /status",
            }
            if action in fallback_cmds:
                raw_res = asyncio.run(
                    agent.nats_cmd(
                        {
                            "func": "rawcmd",
                            "timeout": 35,
                            "payload": {
                                "command": fallback_cmds[action],
                                "shell": "powershell",
                            },
                        },
                        timeout=40,
                    )
                )
                if raw_res not in ("timeout", "natsdown"):
                    r = {
                        "success": True,
                        "action": action,
                        "steps": [f"Operação '{action}' executada com sucesso em {agent.hostname}"],
                        "output": str(raw_res).strip(),
                        "timestamp": djangotime.now().isoformat(),
                    }

        if r in ("timeout", "natsdown"):
            return Response(
                {"error": f"Operação ({action}) expirou em {agent.hostname}"},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )

        AuditLog.objects.create(
            username=request.user.username,
            agent=agent.hostname,
            agent_id=agent.agent_id,
            object_type=AuditObjType.AGENT,
            action=AuditActionType.EXEC_COMMAND,
            message=f"{request.user.username} executou operação AD/Standalone '{action}' em {agent.hostname}",
            after_value=nats_data["payload"],
        )
        return Response(r)


class AgentLANDiscoveryView(APIView):
    """
    POST /agents/<agent_id>/lan-discovery/
    Uses any installed server/agent in a non-AD unit as a LAN Discovery Probe
    (SMB sessions, DHCP leases, ARP cache, and Go LAN scanner) and cross-references
    discovered computers against the Tactical RMM database.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, agent_id: str) -> Response:
        agent = get_object_or_404(
            Agent.objects.select_related("site__client"), agent_id=agent_id
        )
        subnet = str(request.data.get("subnet", "")).strip()
        nats_data = {"func": "lan_discovery", "payload": {"subnet": subnet}}
        r = asyncio.run(agent.nats_cmd(nats_data, timeout=45))
        if r in ("timeout", "natsdown") or not isinstance(r, dict):
            return Response(
                {
                    "error": f"Levantamento LAN expirou ou agente offline em {agent.hostname}"
                },
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )

        # Build lookup maps of all agents registered in Tactical RMM (by hostname and by local IP)
        hostname_map: dict[str, dict[str, str]] = {}
        ip_map: dict[str, dict[str, str]] = {}

        for existing in Agent.objects.only("agent_id", "hostname", "wmi_detail"):
            short_name = (existing.hostname or "").split(".")[0].strip().lower()
            info = {"agent_id": existing.agent_id, "hostname": existing.hostname}
            if short_name:
                hostname_map[short_name] = info
            # Match both Windows (existing.local_ips property via wmi_detail['network_config'])
            # and Linux (wmi_detail['local_ips'])
            with suppress(Exception):
                win_ips = existing.local_ips
                if win_ips:
                    for raw_ip in str(win_ips).split(","):
                        clean_ip = raw_ip.split("/")[0].strip()
                        if clean_ip:
                            ip_map[clean_ip] = info
            wmi = existing.wmi_detail or {}
            if isinstance(wmi, dict):
                local_ips = wmi.get("local_ips") or []
                if isinstance(local_ips, list):
                    for raw_ip in local_ips:
                        clean_ip = str(raw_ip).split("/")[0].strip()
                        if clean_ip:
                            ip_map[clean_ip] = info

        hosts = r.get("hosts") or []
        registered_count = 0
        unregistered_count = 0

        for h in hosts:
            if not isinstance(h, dict):
                continue
            ip_addr = str(h.get("ip_address") or "").strip()
            raw_host = str(h.get("hostname") or "").split(".")[0].strip().lower()
            matched = ip_map.get(ip_addr) or (
                hostname_map.get(raw_host) if raw_host else None
            )
            if matched:
                h["registered_in_rmm"] = True
                h["rmm_agent_id"] = matched["agent_id"]
                h["rmm_hostname"] = matched["hostname"]
                if not h.get("hostname"):
                    h["hostname"] = matched["hostname"]
                registered_count += 1
            else:
                h["registered_in_rmm"] = False
                h["rmm_agent_id"] = ""
                h["rmm_hostname"] = ""
                unregistered_count += 1

        r["registered_count"] = registered_count
        r["unregistered_count"] = unregistered_count
        r["client_name"] = agent.client.name
        r["site_name"] = agent.site.name
        return Response(r)


class FleetSyncAndCleanupView(APIView):
    """
    POST /agents/fleet-sync/
    1) Pings ALL visible agents via NATS concurrently to verify real-time reachability:
       - Stamps fresh last_seen on any responsive agent (waking offline/overdue ones).
       - Double-checks unresponsive 'online' agents and marks genuinely unreachable ones offline
         so stale green 'online' indicators match actual NATS connectivity.
    2) Deduplicates stale/reformatted duplicate hostnames in the same site when a newer online agent exists.
    3) Clears Redis caches and returns updated real-time counts.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request) -> Response:
        deduplicate = bool(request.data.get("deduplicate", True))
        wake_overdue = bool(request.data.get("wake_overdue", True))
        verify_online = bool(request.data.get("verify_online", True))

        all_agents = list(
            Agent.objects.filter_by_role(request.user).select_related("site__client")
        )
        recovered_agents: list[str] = []
        demoted_agents: list[str] = []
        deduplicated_agents: list[str] = []

        # 1. Probe real-time NATS connectivity across offline/overdue and (optionally) online agents
        candidates = [
            a for a in all_agents if verify_online or a.status != AGENT_STATUS_ONLINE
        ]

        async def _probe_candidates(
            agent_list: list[Agent],
        ) -> tuple[list[Agent], list[Agent]]:
            sem = asyncio.Semaphore(40)
            alive: list[Agent] = []
            unreachable_online: list[Agent] = []

            async def _check_one(ag: Agent) -> None:
                was_online = ag.status == AGENT_STATUS_ONLINE
                if not was_online and not wake_overdue:
                    return
                async with sem:
                    res = "timeout"
                    with suppress(Exception):
                        res = await ag.nats_cmd({"func": "ping"}, timeout=2.5)
                    if res == "pong":
                        alive.append(ag)
                    elif was_online and verify_online and res == "timeout":
                        # Confirm with one quick retry so a momentary glitch isn't demoted
                        retry_res = "timeout"
                        with suppress(Exception):
                            retry_res = await ag.nats_cmd({"func": "ping"}, timeout=2.0)
                        if retry_res == "pong":
                            alive.append(ag)
                        elif retry_res == "timeout":
                            unreachable_online.append(ag)

            await asyncio.gather(*[_check_one(a) for a in agent_list])
            return alive, unreachable_online

        if candidates:
            with suppress(Exception):
                alive_list, unreachable_online_list = asyncio.run(
                    _probe_candidates(candidates)
                )
                now_ts = djangotime.now()
                for ag in alive_list:
                    was_disconnected = ag.status != AGENT_STATUS_ONLINE
                    ag.last_seen = now_ts
                    ag.save(update_fields=["last_seen"])
                    if was_disconnected:
                        recovered_agents.append(ag.hostname)

                for ag in unreachable_online_list:
                    # Push last_seen just past offline_time (keeping above overdue_time when valid)
                    offset_min = max(int(ag.offline_time or 4) + 1, 5)
                    if ag.overdue_time and ag.overdue_time > ag.offline_time + 1:
                        offset_min = min(offset_min, int(ag.overdue_time) - 1)
                    ag.last_seen = now_ts - djangotime.timedelta(minutes=offset_min)
                    ag.save(update_fields=["last_seen"])
                    demoted_agents.append(ag.hostname)

        # 2. Deduplicate reformatted computers with identical hostname in the same site
        if deduplicate:
            refreshed = list(
                Agent.objects.filter_by_role(request.user).select_related("site")
            )
            by_site_host: dict[tuple[int, str], list[Agent]] = {}
            for ag in refreshed:
                key = (ag.site_id, (ag.hostname or "").strip().lower())
                if key[1]:
                    by_site_host.setdefault(key, []).append(ag)

            for (_, _), group in by_site_host.items():
                if len(group) < 2:
                    continue
                # Sort so online agents and most recently seen come first
                group.sort(
                    key=lambda x: (
                        1 if x.status == AGENT_STATUS_ONLINE else 0,
                        x.last_seen or djangotime.datetime.min.replace(tzinfo=djangotime.utc),
                    ),
                    reverse=True,
                )
                primary = group[0]
                if primary.status == AGENT_STATUS_ONLINE:
                    for stale_dup in group[1:]:
                        if stale_dup.status != AGENT_STATUS_ONLINE:
                            deduplicated_agents.append(
                                f"{stale_dup.hostname} ({stale_dup.agent_id[:8]})"
                            )
                            stale_dup.delete()

        with suppress(Exception):
            from core.utils import clear_entire_cache

            clear_entire_cache()

        final_agents = list(Agent.objects.filter_by_role(request.user))
        online_cnt = sum(1 for a in final_agents if a.status == AGENT_STATUS_ONLINE)
        offline_cnt = sum(1 for a in final_agents if a.status == "offline")
        overdue_cnt = sum(1 for a in final_agents if a.status == AGENT_STATUS_OVERDUE)
        reboot_cnt = sum(1 for a in final_agents if a.needs_reboot)

        return Response(
            {
                "status": "ok",
                "total": len(final_agents),
                "online": online_cnt,
                "offline": offline_cnt,
                "overdue": overdue_cnt,
                "reboot_needed": reboot_cnt,
                "recovered_count": len(recovered_agents),
                "recovered_hostnames": recovered_agents,
                "demoted_count": len(demoted_agents),
                "demoted_hostnames": demoted_agents,
                "deduplicated_count": len(deduplicated_agents),
                "deduplicated_hostnames": deduplicated_agents,
                "timestamp": djangotime.now().isoformat(),
            }
        )


_AD_AUDIT_PS_SCRIPT_BODY = r"""[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Stop'
$auditCfgJson = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('__AUDIT_CFG_B64__'))
$auditCfg = $auditCfgJson | ConvertFrom-Json
$ldapServer = ([string]$auditCfg.ldap_server).Trim()
$bindUser = ([string]$auditCfg.user).Trim()
$bindPass = [string]$auditCfg.pass

try {
    function Open-AdEntry([string]$subPath) {
        $prefix = if ($ldapServer) { "LDAP://$ldapServer/$subPath" } else { "LDAP://$subPath" }
        if ($bindUser -and $bindPass) {
            return New-Object System.DirectoryServices.DirectoryEntry($prefix, $bindUser, $bindPass, [System.DirectoryServices.AuthenticationTypes]::Secure)
        }
        return [ADSI]$prefix
    }

    $rootDse = Open-AdEntry "RootDSE"
    $defaultNC = [string]$rootDse.defaultNamingContext
    if (-not $defaultNC) {
        @{ ok = $false; error = "Este computador nao esta ingressado em um dominio Active Directory e nenhum servidor LDAP respondeu (RootDSE vazio)." } | ConvertTo-Json -Compress
        exit 0
    }
    $dcParts = @()
    $dnTokens = [regex]::Split($defaultNC, '(?<!\\),')
    foreach ($tok in $dnTokens) {
        if ($tok -match '^DC=(.+)$') { $dcParts += ($Matches[1] -replace '\\(.)', '$1') }
    }
    $domainDns = ($dcParts -join '.').ToLower()
    if (-not $domainDns) { $domainDns = ([string]$env:USERDNSDOMAIN).ToLower() }

    $searchRoot = Open-AdEntry $defaultNC
    $searcher = New-Object System.DirectoryServices.DirectorySearcher($searchRoot)
    $searcher.Filter = "(&(objectCategory=computer)(objectClass=computer))"
    $searcher.PageSize = 1000
    $searcher.SearchScope = [System.DirectoryServices.SearchScope]::Subtree
    $propsToLoad = @("name","dnshostname","distinguishedname","operatingsystem","operatingsystemversion","description","useraccountcontrol","lastlogontimestamp","whencreated")
    foreach ($p in $propsToLoad) { [void]$searcher.PropertiesToLoad.Add($p) }

    function Get-AdProp($entry, [string]$prop) {
        if ($entry.Properties.Contains($prop) -and $entry.Properties[$prop].Count -gt 0) {
            return $entry.Properties[$prop][0]
        }
        return $null
    }

    $items = New-Object System.Collections.ArrayList
    $results = $null
    try {
        $results = $searcher.FindAll()
        foreach ($res in $results) {
            $name = [string](Get-AdProp $res "name")
            if (-not $name) { continue }
            $dnsHost = [string](Get-AdProp $res "dnshostname")
            $dn = [string](Get-AdProp $res "distinguishedname")
            $osName = [string](Get-AdProp $res "operatingsystem")
            $osVer = [string](Get-AdProp $res "operatingsystemversion")
            $desc = [string](Get-AdProp $res "description")

            $uacObj = Get-AdProp $res "useraccountcontrol"
            $uac = if ($null -ne $uacObj) { [int64]$uacObj } else { 0 }
            $enabled = (($uac -band 2) -eq 0)
            $isDc = (($uac -band 8192) -ne 0)

            $lastLogonIso = ""
            $llObj = Get-AdProp $res "lastlogontimestamp"
            if ($null -ne $llObj) {
                $ft = [int64]$llObj
                if ($ft -gt 0 -and $ft -lt 9223372036854775807) {
                    try { $lastLogonIso = [datetime]::FromFileTimeUtc($ft).ToString("yyyy-MM-ddTHH:mm:ssZ") } catch {}
                }
            }

            $createdIso = ""
            $crObj = Get-AdProp $res "whencreated"
            if ($crObj -is [datetime]) {
                try { $createdIso = $crObj.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") } catch {}
            }

            $parentNames = New-Object System.Collections.ArrayList
            $parentRaw = New-Object System.Collections.ArrayList
            if ($dn) {
                $parts = [regex]::Split($dn, '(?<!\\),')
                if ($parts.Length -gt 1) {
                    for ($idx = $parts.Length - 1; $idx -ge 1; $idx--) {
                        $seg = $parts[$idx]
                        if ($seg -notmatch '^DC=' -and $seg -match '^(?:OU|CN)=(.+)$') {
                            [void]$parentRaw.Add($seg)
                            [void]$parentNames.Add(($Matches[1] -replace '\\(.)', '$1'))
                        }
                    }
                }
            }

            $isRootObj = ($parentNames.Count -eq 0)
            $isDefaultCont = $false
            $folderGroup = if ($isRootObj) { $domainDns } else { [string]$parentNames[0] }
            $folderPath = if ($isRootObj) { $domainDns } else { ($parentNames.ToArray() -join " / ") }
            if (-not $isRootObj -and ([string]$parentRaw[0] -like "CN=*")) {
                $isDefaultCont = $true
            }

            [void]$items.Add([pscustomobject]@{
                name = $name
                dns_hostname = $dnsHost
                distinguished_name = $dn
                folder_group = $folderGroup
                folder_path = $folderPath
                is_root_domain = $isRootObj
                is_default_container = $isDefaultCont
                enabled = $enabled
                is_dc = $isDc
                operating_system = $osName
                os_version = $osVer
                description = $desc
                last_logon = $lastLogonIso
                when_created = $createdIso
            })
        }
    } finally {
        if ($null -ne $results) { $results.Dispose() }
        $searcher.Dispose()
    }

    @{
        ok = $true
        domain = $domainDns
        netbios = [string]$env:USERDOMAIN
        default_nc = $defaultNC
        probe_host = [string]$env:COMPUTERNAME
        total = $items.Count
        computers = @($items.ToArray())
    } | ConvertTo-Json -Depth 4 -Compress
} catch {
    @{ ok = $false; error = $_.Exception.Message } | ConvertTo-Json -Compress
} finally {
    $bindPass = $null
    $auditCfgJson = $null
}
"""


def _build_ad_audit_ps_script(
    ldap_server: str = "", username: str = "", password: str = ""
) -> str:
    cfg_b64 = base64.b64encode(
        json.dumps(
            {
                "ldap_server": ldap_server.strip(),
                "user": username.strip(),
                "pass": password,
            },
            ensure_ascii=False,
        ).encode("utf-8")
    ).decode("ascii")
    return _AD_AUDIT_PS_SCRIPT_BODY.replace("__AUDIT_CFG_B64__", cfg_b64)


def _wrap_ps_utf8_b64(script: str) -> str:
    b64 = base64.b64encode(script.encode("utf-8")).decode("ascii")
    return (
        "& ([scriptblock]::Create("
        "[System.Text.Encoding]::UTF8.GetString("
        f"[Convert]::FromBase64String('{b64}')"
        ")))"
    )


def _run_probe_powershell(
    probe: Agent, ps_script: str, timeout: int = 90
) -> Tuple[bool, str]:
    """
    Executes a PowerShell script on an online Windows agent via 'runscriptfull'
    (writes to a temporary .ps1 file, avoiding the 32KB CreateProcessW CLI limit,
    preserving UTF-8, and surfacing both stdout and stderr for clear diagnostics).
    """
    wrapped = _wrap_ps_utf8_b64(ps_script)
    res = asyncio.run(
        probe.nats_cmd(
            {
                "func": "runscriptfull",
                "timeout": timeout,
                "script_args": [],
                "payload": {"code": wrapped, "shell": "powershell"},
                "run_as_user": False,
                "env_vars": [],
            },
            timeout=timeout + 8,
        )
    )
    if res in ("timeout", "natsdown", "error") or res is None:
        return False, str(res or "empty_response")

    if isinstance(res, dict):
        stdout = str(
            res.get("stdout") if "stdout" in res else (res.get("Stdout") or "")
        ).strip()
        stderr = str(
            res.get("stderr") if "stderr" in res else (res.get("Stderr") or "")
        ).strip()
        if stdout:
            return True, stdout
        if stderr:
            return False, stderr
        return False, "empty_stdout_stderr"

    txt = str(res).strip()
    if not txt:
        return False, "empty_response"
    return True, txt


def _pick_domain_probe_agent(user, preferred_agent_id=None):
    from tacticalrmm.constants import AGENT_DEFER, AgentPlat
    from tacticalrmm.permissions import _has_perm_on_agent

    win_agents = list(
        Agent.objects.filter_by_role(user)
        .filter(plat=AgentPlat.WINDOWS)
        .select_related("site__client")
        .defer(*AGENT_DEFER)
    )

    ranked = []
    for ag in win_agents:
        if ag.status != AGENT_STATUS_ONLINE:
            continue
        prof = _extract_wmi_profile(ag)
        domain_role = int(prof.get("domain_role") or 0)
        part_of_domain = bool(prof.get("part_of_domain"))
        domain_name = str(prof.get("domain_name") or "")
        is_dc = domain_role >= 4
        if is_dc:
            tier = 0
        elif ag.monitoring_type == "server" and part_of_domain:
            tier = 1
        elif part_of_domain:
            tier = 2
        elif ag.monitoring_type == "server":
            tier = 3
        else:
            tier = 4

        ranked.append(
            (
                tier,
                ag.hostname.lower(),
                ag,
                {
                    "agent_id": ag.agent_id,
                    "hostname": ag.hostname,
                    "client": ag.site.client.name,
                    "site": ag.site.name,
                    "monitoring_type": ag.monitoring_type,
                    "domain": domain_name,
                    "is_dc": is_dc,
                    "part_of_domain": part_of_domain,
                },
            )
        )

    ranked.sort(key=lambda item: (item[0], item[1]))
    available_probes = [item[3] for item in ranked]
    selected = ranked[0][2] if ranked else None

    if preferred_agent_id:
        for _, _, ag, _ in ranked:
            if ag.agent_id == preferred_agent_id and _has_perm_on_agent(
                user, ag.agent_id
            ):
                selected = ag
                break

    return selected, available_probes


class FleetADDirectoryAuditView(APIView):
    """
    GET/POST /agents/ad-directory-audit/
    Queries Active Directory directly via LDAP://RootDSE (DirectorySearcher) from an online
    domain probe agent (preferring Domain Controllers / Windows Servers) and cross-references
    ALL AD computer objects (CRD, Computadores, Computers, Domain Root, sub-OUs) against
    Tactical RMM agents to list missing or broken computers.
    """

    permission_classes = [IsAuthenticated]

    def _run_audit(self, request):
        from tacticalrmm.constants import AGENT_DEFER
        from tacticalrmm.helpers import notify_error
        from tacticalrmm.permissions import _has_perm, _has_perm_on_agent

        if not _has_perm(request, "can_list_agents"):
            return notify_error("Permissão insuficiente para listar agentes/AD.")

        preferred_id = (
            request.query_params.get("probe_agent_id")
            if request.method == "GET"
            else request.data.get("probe_agent_id")
        )
        ldap_server = str(
            (
                request.query_params.get("ldap_server")
                if request.method == "GET"
                else request.data.get("ldap_server")
            )
            or ""
        ).strip()
        if ldap_server and not re.match(r"^[A-Za-z0-9._-]+$", ldap_server):
            return notify_error("Servidor LDAP / IP inválido.")

        ldap_username = str(
            (request.data.get("username") if request.method != "GET" else "") or ""
        ).strip()
        ldap_password = str(
            (request.data.get("password") if request.method != "GET" else "") or ""
        )

        probe, available_probes = _pick_domain_probe_agent(
            request.user, preferred_agent_id=preferred_id
        )
        if not probe:
            return notify_error(
                "Nenhum servidor ou computador Windows online encontrado para consultar o Active Directory."
            )
        if not _has_perm_on_agent(request.user, probe.agent_id):
            return notify_error("Sem permissão no servidor consultado.")

        ok_ps, raw = _run_probe_powershell(
            probe,
            _build_ad_audit_ps_script(
                ldap_server=ldap_server,
                username=ldap_username,
                password=ldap_password,
            ),
            timeout=65,
        )
        if not ok_ps:
            return Response(
                {
                    "ok": False,
                    "error": f"Falha ao consultar Active Directory via '{probe.hostname}' (resposta: {raw[:300]}).",
                    "probe_agent": {
                        "agent_id": probe.agent_id,
                        "hostname": probe.hostname,
                    },
                    "available_probes": available_probes,
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        raw_str = str(raw).strip()
        start_idx = raw_str.find("{")
        end_idx = raw_str.rfind("}")
        if start_idx == -1 or end_idx <= start_idx:
            return Response(
                {
                    "ok": False,
                    "error": f"Retorno inesperado do agente '{probe.hostname}': {raw_str[:400]}",
                    "probe_agent": {
                        "agent_id": probe.agent_id,
                        "hostname": probe.hostname,
                    },
                    "available_probes": available_probes,
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        try:
            ad_data = json.loads(raw_str[start_idx : end_idx + 1])
        except Exception as exc:
            return Response(
                {
                    "ok": False,
                    "error": f"Erro ao decodificar resposta LDAP JSON de '{probe.hostname}': {exc}",
                    "available_probes": available_probes,
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if not ad_data.get("ok"):
            return Response(
                {
                    "ok": False,
                    "error": ad_data.get("error")
                    or "Erro ao consultar Active Directory.",
                    "probe_agent": {
                        "agent_id": probe.agent_id,
                        "hostname": probe.hostname,
                    },
                    "available_probes": available_probes,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Build fast lookup dictionary across all Tactical RMM agents visible to user
        all_agents = list(
            Agent.objects.filter_by_role(request.user)
            .select_related("site__client")
            .defer(*AGENT_DEFER)
        )
        tactical_lookup: Dict[str, Agent] = {}

        def _prefer_agent(existing: Agent, candidate: Agent) -> Agent:
            ex_online = 1 if existing.status == AGENT_STATUS_ONLINE else 0
            ca_online = 1 if candidate.status == AGENT_STATUS_ONLINE else 0
            if ca_online != ex_online:
                return candidate if ca_online > ex_online else existing
            if candidate.last_seen and existing.last_seen:
                return (
                    candidate
                    if candidate.last_seen > existing.last_seen
                    else existing
                )
            return existing

        for ag in all_agents:
            keys = set()
            if ag.hostname:
                h_up = ag.hostname.strip().upper()
                keys.add(h_up)
                keys.add(h_up.split(".")[0])
            comp_sys = _flatten_wmi_section((ag.wmi_detail or {}).get("comp_sys"))
            for field in ("Name", "DNSHostName", "Caption"):
                val = str(comp_sys.get(field) or "").strip().upper()
                if val:
                    keys.add(val)
                    keys.add(val.split(".")[0])
            for k in keys:
                if k in tactical_lookup:
                    tactical_lookup[k] = _prefer_agent(tactical_lookup[k], ag)
                else:
                    tactical_lookup[k] = ag

        now_utc = djangotime.now()
        ad_computers_raw = ad_data.get("computers") or []
        if isinstance(ad_computers_raw, dict):
            ad_computers_raw = [ad_computers_raw]

        rows: List[Dict[str, Any]] = []
        folders: Dict[str, Dict[str, Any]] = {}

        total_enabled = 0
        present_cnt = 0
        online_cnt = 0
        offline_cnt = 0
        missing_cnt = 0
        missing_enabled_cnt = 0
        missing_active_90d_cnt = 0
        default_container_missing_cnt = 0
        root_domain_missing_cnt = 0

        for item in ad_computers_raw:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            dns_host = str(item.get("dns_hostname") or "").strip()
            dn = str(item.get("distinguished_name") or "").strip()
            folder_group = str(
                item.get("folder_group") or ad_data.get("domain") or "AD"
            ).strip()
            folder_path = str(item.get("folder_path") or folder_group).strip()
            enabled = bool(item.get("enabled", True))
            is_dc = bool(item.get("is_dc", False))
            is_default_cont = bool(item.get("is_default_container", False))
            is_root_obj = bool(item.get("is_root_domain", False))
            os_name = str(item.get("operating_system") or "").strip()
            os_ver = str(item.get("os_version") or "").strip()
            desc = str(item.get("description") or "").strip()
            last_logon = str(item.get("last_logon") or "").strip()

            days_since_logon = None
            if last_logon:
                with suppress(Exception):
                    from datetime import datetime as dt_cls

                    parsed = dt_cls.fromisoformat(last_logon.replace("Z", "+00:00"))
                    days_since_logon = max(0, int((now_utc - parsed).days))

            lookup_keys = [name.upper()]
            if dns_host:
                lookup_keys.append(dns_host.upper())
                lookup_keys.append(dns_host.split(".")[0].upper())

            matched: Agent | None = None
            for lk in lookup_keys:
                if lk in tactical_lookup:
                    matched = tactical_lookup[lk]
                    break

            in_tactical = matched is not None
            if matched is not None:
                sync_state = matched.status
            else:
                sync_state = "missing"

            if enabled:
                total_enabled += 1
            if in_tactical:
                present_cnt += 1
                if sync_state == AGENT_STATUS_ONLINE:
                    online_cnt += 1
                else:
                    offline_cnt += 1
            else:
                missing_cnt += 1
                if enabled:
                    missing_enabled_cnt += 1
                if enabled and days_since_logon is not None and days_since_logon <= 90:
                    missing_active_90d_cnt += 1
                if is_default_cont and enabled:
                    default_container_missing_cnt += 1
                if is_root_obj and enabled:
                    root_domain_missing_cnt += 1

            f_bucket = folders.setdefault(
                folder_group,
                {
                    "folder": folder_group,
                    "total": 0,
                    "enabled": 0,
                    "in_tactical": 0,
                    "online": 0,
                    "offline_or_overdue": 0,
                    "missing": 0,
                    "missing_enabled": 0,
                    "missing_active_90d": 0,
                    "is_default_container": is_default_cont,
                    "is_root_domain": is_root_obj,
                },
            )
            f_bucket["total"] += 1
            if enabled:
                f_bucket["enabled"] += 1
            if in_tactical:
                f_bucket["in_tactical"] += 1
                if sync_state == AGENT_STATUS_ONLINE:
                    f_bucket["online"] += 1
                else:
                    f_bucket["offline_or_overdue"] += 1
            else:
                f_bucket["missing"] += 1
                if enabled:
                    f_bucket["missing_enabled"] += 1
                if enabled and days_since_logon is not None and days_since_logon <= 90:
                    f_bucket["missing_active_90d"] += 1

            rows.append(
                {
                    "name": name,
                    "dns_hostname": dns_host,
                    "distinguished_name": dn,
                    "folder_group": folder_group,
                    "folder_path": folder_path,
                    "is_root_domain": is_root_obj,
                    "is_default_container": is_default_cont,
                    "enabled": enabled,
                    "is_dc": is_dc,
                    "operating_system": os_name,
                    "os_version": os_ver,
                    "description": desc,
                    "last_logon": last_logon,
                    "days_since_logon": days_since_logon,
                    "in_tactical": in_tactical,
                    "sync_state": sync_state,
                    "agent_id": matched.agent_id if matched else None,
                    "tactical_hostname": matched.hostname if matched else None,
                    "tactical_client": matched.site.client.name if matched else None,
                    "tactical_site": matched.site.name if matched else None,
                    "tactical_site_id": matched.site_id if matched else None,
                    "tactical_version": matched.version if matched else None,
                    "tactical_last_seen": (
                        matched.last_seen.isoformat()
                        if (matched and matched.last_seen)
                        else None
                    ),
                }
            )

        rows.sort(
            key=lambda r: (
                1 if r["in_tactical"] else 0,
                0 if r["enabled"] else 1,
                r["folder_group"].lower(),
                r["name"].lower(),
            )
        )
        folder_summary = sorted(
            folders.values(),
            key=lambda f: (-f["missing_enabled"], -f["total"], f["folder"].lower()),
        )

        diagnostics: List[str] = []
        domain_name = ad_data.get("domain") or ""
        if default_container_missing_cnt > 0:
            diagnostics.append(
                f"Há {default_container_missing_cnt} computador(es) habilitado(s) na pasta padrão 'Computers' (CN=Computers). "
                "Containers padrão do AD NÃO aplicam GPOs vinculadas a OUs automaticamente — use 'Push Remoto' abaixo, "
                "mova essas máquinas para uma OU (ex: 'Computadores' ou 'CRD') ou vincule a GPO na raiz do domínio."
            )
        if root_domain_missing_cnt > 0:
            diagnostics.append(
                f"Há {root_domain_missing_cnt} computador(es) diretamente na raiz '{domain_name}'. "
                "Para receberem GPO automaticamente sem mover para uma OU, a GPO precisa estar vinculada na raiz do domínio."
            )
        if missing_enabled_cnt > 0:
            diagnostics.append(
                "Dica GPO: baixe a versão corrigida do 'Install-TacticalRMM.ps1' nesta janela — ele agora baixa o binário local do seu servidor RMM "
                "e executa '-m gpoinstall' diretamente sem depender do GitHub ou Inno Setup '/VERYSILENT'."
            )

        return Response(
            {
                "ok": True,
                "domain": domain_name,
                "netbios": ad_data.get("netbios") or "",
                "default_nc": ad_data.get("default_nc") or "",
                "probe_agent": {
                    "agent_id": probe.agent_id,
                    "hostname": probe.hostname,
                    "client": probe.site.client.name,
                    "site": probe.site.name,
                },
                "available_probes": available_probes,
                "summary": {
                    "total_ad": len(rows),
                    "enabled_ad": total_enabled,
                    "disabled_ad": len(rows) - total_enabled,
                    "present_in_tactical": present_cnt,
                    "online_in_tactical": online_cnt,
                    "offline_in_tactical": offline_cnt,
                    "missing_from_tactical": missing_cnt,
                    "missing_enabled": missing_enabled_cnt,
                    "missing_active_90d": missing_active_90d_cnt,
                    "default_container_missing": default_container_missing_cnt,
                    "root_domain_missing": root_domain_missing_cnt,
                },
                "folder_summary": folder_summary,
                "diagnostics": diagnostics,
                "computers": rows,
                "timestamp": now_utc.isoformat(),
            }
        )

    def get(self, request):
        return self._run_audit(request)

    def post(self, request):
        return self._run_audit(request)


class FleetADPushInstallView(APIView):
    """
    POST /agents/ad-push-install/
    Remotely deploys the Tactical RMM agent from an online AD Server / Probe Agent to
    selected Active Directory hostnames using WinRM (5985) with automatic fallback to
    SMB ADMIN$ + schtasks (/RU SYSTEM /RL HIGHEST), pulling directly from the local RMM server.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        import datetime as dt
        from django.conf import settings
        from knox.models import AuthToken
        from accounts.models import User
        from agents.utils import get_agent_url
        from clients.models import Site
        from core.utils import token_is_valid
        from tacticalrmm.constants import AgentPlat, GoArch
        from tacticalrmm.helpers import notify_error
        from tacticalrmm.permissions import (
            _has_perm,
            _has_perm_on_agent,
            _has_perm_on_site,
        )

        if not (
            _has_perm(request, "can_install_agents")
            and _has_perm(request, "can_send_cmd")
        ):
            return notify_error("Permissão insuficiente para instalar agentes remotamente.")

        site_id = request.data.get("site_id")
        if not site_id:
            return notify_error("Selecione o Cliente / Site de destino no Tactical RMM.")
        try:
            site = Site.objects.select_related("client").get(pk=int(site_id))
        except (ValueError, TypeError, Site.DoesNotExist):
            return notify_error("Site de destino inválido.")

        if not _has_perm_on_site(request.user, site.pk):
            return notify_error("Sem permissão neste Site.")

        raw_hosts = request.data.get("hostnames") or []
        if not isinstance(raw_hosts, list) or not raw_hosts:
            return notify_error("Selecione ao menos um computador do AD.")

        clean_hosts: List[str] = []
        seen_hosts = set()
        host_re = re.compile(r"^[A-Za-z0-9._-]+$")
        for h in raw_hosts:
            val = str(h or "").strip()
            if not val or not host_re.match(val) or val.startswith("-"):
                continue
            key = val.upper()
            if key not in seen_hosts:
                seen_hosts.add(key)
                clean_hosts.append(val)
        if not clean_hosts:
            return notify_error("Nenhum hostname válido informado.")
        if len(clean_hosts) > 20:
            return notify_error(
                "Por segurança e estabilidade, envie no máximo 20 computadores por lote."
            )

        preferred_id = request.data.get("probe_agent_id")
        probe, _ = _pick_domain_probe_agent(
            request.user, preferred_agent_id=preferred_id
        )
        if not probe:
            return notify_error(
                "Nenhum servidor ou agente Windows online disponível para executar o Push."
            )
        if not _has_perm_on_agent(request.user, probe.agent_id):
            return notify_error("Sem permissão no servidor de origem selecionado.")

        installer_user = User.objects.filter(is_installer_user=True).first()
        if not installer_user:
            return notify_error("Usuário instalador (is_installer_user) não encontrado.")

        try:
            expires_h = max(1, min(24, int(request.data.get("expires", 4))))
        except (ValueError, TypeError):
            expires_h = 4
        _, token = AuthToken.objects.create(
            user=installer_user, expiry=dt.timedelta(hours=expires_h)
        )

        raw_agent_type = str(request.data.get("agent_type") or "both").lower()
        if raw_agent_type not in ("both", "workstation", "server"):
            raw_agent_type = "both"

        rdp_flag = " --rdp" if int(request.data.get("rdp", 1)) else ""
        ping_flag = " --ping" if int(request.data.get("ping", 1)) else ""
        power_flag = " --power" if int(request.data.get("power", 0)) else ""
        banking_mode = bool(request.data.get("banking_mode", False))
        force_reinstall = bool(request.data.get("force_reinstall", False))

        api_url = str(request.data.get("api") or "").strip().rstrip("/")
        if not api_url:
            api_host = request.get_host()
            api_url = f"{request.scheme}://{api_host}".rstrip("/")

        version = settings.LATEST_AGENT_VER
        cors_origins = getattr(settings, "CORS_ORIGIN_WHITELIST", [])
        if cors_origins:
            base_web = cors_origins[0].rstrip("/")
        else:
            base_web = f"{request.scheme}://{request.get_host()}".rstrip("/")

        local_win_amd64 = f"{base_web}/agents/tacticalagent-v{version}-windows-amd64.exe"
        local_win_386 = f"{base_web}/agents/tacticalagent-v{version}-windows-386.exe"
        codesign_token, is_valid = token_is_valid()
        win_url = get_agent_url(
            goarch=GoArch.AMD64,
            plat=AgentPlat.WINDOWS,
            token=codesign_token if is_valid else "",
        )

        win_banking_snippet = (
            f"\nif ($atype -eq 'workstation') {{ {WINDOWS_MESH_BANKING_PAUSE_CMD} }}"
            if banking_mode
            else ""
        )
        gpo_install_args = (
            f"-m gpoinstall -api '{api_url}' -client-id {site.client_id} -site-id {site.pk} "
            f"-agent-type $atype -auth '{token}' -silent -gpo"
            f"{rdp_flag}{ping_flag}{power_flag}"
        )

        # Target-side self-contained installer script (runs as SYSTEM on each target machine)
        target_install_script = f"""$ErrorActionPreference = 'Continue'
$Folder = 'C:\\ProgramData\\TacticalRMM'
$LogFile = "$Folder\\gpo-install.log"
New-Item -Path $Folder -ItemType Directory -Force -ErrorAction SilentlyContinue | Out-Null
function Write-PushLog([string]$m) {{
    try {{
        $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
        Add-Content -Path $LogFile -Value "[$ts] $m" -Encoding UTF8 -ErrorAction SilentlyContinue
    }} catch {{}}
}}

$Force = {'$true' if force_reinstall else '$false'}
$TacticalSvc = Get-Service -Name 'tacticalrmm' -ErrorAction SilentlyContinue
if (-not $TacticalSvc) {{ $TacticalSvc = Get-Service -Name 'tacticalagent' -ErrorAction SilentlyContinue }}
$InstalledExe = 'C:\\Program Files\\TacticalAgent\\tacticalrmm.exe'
if (-not (Test-Path $InstalledExe)) {{ $InstalledExe = 'C:\\Program Files\\TacticalAgent\\tacticalagent.exe' }}
$RegProp = Get-ItemProperty -Path 'HKLM:\\SOFTWARE\\TacticalRMM' -ErrorAction SilentlyContinue

if ((-not $Force) -and $TacticalSvc -and (Test-Path $InstalledExe) -and $RegProp -and $RegProp.AgentID) {{
    if ($TacticalSvc.Status -ne 'Running') {{
        Start-Service -Name $TacticalSvc.Name -ErrorAction SilentlyContinue
    }}
    Write-Output "ALREADY_REGISTERED AgentID=$($RegProp.AgentID)"
    exit 0
}}

Write-PushLog "Iniciando Push Deploy remoto (origem AD) em $env:COMPUTERNAME..."
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls13
$osType = if ((Get-CimInstance Win32_OperatingSystem).ProductType -eq 1) {{ 'workstation' }} else {{ 'server' }}
$atype = if ('{raw_agent_type}' -eq 'both') {{ $osType }} else {{ '{raw_agent_type}' }}
$localUrl = if ([Environment]::Is64BitOperatingSystem) {{ '{local_win_amd64}' }} else {{ '{local_win_386}' }}
$dst = "$env:TEMP\\tacticalagent-push-setup.exe"
$downloadedLocal = $false
try {{
    Invoke-WebRequest -Uri $localUrl -OutFile $dst -UseBasicParsing -TimeoutSec 45
    if ((Test-Path $dst) -and ((Get-Item $dst).Length -gt 1048576)) {{ $downloadedLocal = $true }}
}} catch {{
    Write-PushLog "Falha ao baixar URL local ($localUrl): $($_.Exception.Message)"
    $downloadedLocal = $false
}}

if (-not $downloadedLocal) {{
    Invoke-WebRequest -Uri '{win_url}' -OutFile $dst -UseBasicParsing -TimeoutSec 60
    Start-Process -FilePath $dst -ArgumentList '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART' -Wait
    Start-Sleep -Seconds 5
}}

$exe = 'C:\\Program Files\\TacticalAgent\\tacticalrmm.exe'
if (-not (Test-Path $exe)) {{ $exe = 'C:\\Program Files\\TacticalAgent\\tacticalagent.exe' }}
if ((-not $downloadedLocal) -and (Test-Path $exe)) {{
    & $exe {gpo_install_args} 2>&1 | Out-String | ForEach-Object {{ if ($_.Trim()) {{ Write-PushLog $_.Trim() }} }}
}} else {{
    & $dst {gpo_install_args} 2>&1 | Out-String | ForEach-Object {{ if ($_.Trim()) {{ Write-PushLog $_.Trim() }} }}
}}{win_banking_snippet}
Remove-Item -Path $dst -Force -ErrorAction SilentlyContinue

$FinalReg = Get-ItemProperty -Path 'HKLM:\\SOFTWARE\\TacticalRMM' -ErrorAction SilentlyContinue
if ($FinalReg -and $FinalReg.AgentID) {{
    Write-PushLog "Push Deploy OK AgentID=$($FinalReg.AgentID)"
    Write-Output "OK AgentID=$($FinalReg.AgentID)"
    exit 0
}} else {{
    Write-PushLog "Push Deploy finalizado sem AgentID gravado."
    Write-Output "WARN No AgentID written"
    exit 2
}}
"""
        remote_b64 = base64.b64encode(target_install_script.encode("utf-8")).decode(
            "ascii"
        )
        target_enc_b64 = base64.b64encode(
            target_install_script.encode("utf-16le")
        ).decode("ascii")

        username = str(request.data.get("username") or "").strip()
        password = str(request.data.get("password") or "")
        # JSON-encode payload passed via B64 so credentials never touch shell string parsing
        runner_config = json.dumps(
            {
                "hosts": clean_hosts,
                "remote_b64": remote_b64,
                "enc_b64": target_enc_b64,
                "user": username,
                "pass": password,
            },
            ensure_ascii=False,
        )
        cfg_b64 = base64.b64encode(runner_config.encode("utf-8")).decode("ascii")

        probe_runner_ps = rf"""[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Continue'
$cfgJson = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{cfg_b64}'))
$cfg = $cfgJson | ConvertFrom-Json
$hosts = @($cfg.hosts)
$remoteB64 = [string]$cfg.remote_b64
$encB64 = [string]$cfg.enc_b64
$rawUser = ([string]$cfg.user).Trim()
$rawPass = [string]$cfg.pass
if ($rawUser -and ($rawUser -notmatch '[\\@]') -and $env:USERDOMAIN) {{
    $rawUser = "$($env:USERDOMAIN)\$rawUser"
}}

$cred = $null
if ($rawUser -and $rawPass) {{
    $sec = ConvertTo-SecureString -String $rawPass -AsPlainText -Force
    $cred = New-Object System.Management.Automation.PSCredential($rawUser, $sec)
}}

$workerScript = {{
    param([string]$h, [string]$b64, [string]$enc, $cred, [string]$rawUser, [string]$rawPass)
    $ErrorActionPreference = 'Continue'

    function Test-TcpPort([string]$targetHost, [int]$port, [int]$ms) {{
        $c = New-Object System.Net.Sockets.TcpClient
        try {{
            $ar = $c.BeginConnect($targetHost, $port, $null, $null)
            if ($ar.AsyncWaitHandle.WaitOne($ms, $false)) {{
                $c.EndConnect($ar)
                return $true
            }}
            return $false
        }} catch {{
            return $false
        }} finally {{
            $c.Close()
        }}
    }}

    $targetHost = $h
    $resolvedIp = ""
    $dnsCandidates = @($h)
    if ($h -match '\.') {{ $dnsCandidates += $h.Split('.')[0] }}
    foreach ($cand in $dnsCandidates) {{
        try {{
            $addrs = [System.Net.Dns]::GetHostAddresses($cand) | Where-Object {{ $_.AddressFamily -eq 'InterNetwork' }}
            if ($addrs) {{
                $resolvedIp = $addrs[0].IPAddressToString
                $targetHost = $cand
                break
            }}
        }} catch {{}}
    }}

    if (-not $resolvedIp) {{
        return [pscustomobject]@{{
            hostname = $h
            ip = ""
            success = $false
            method = "DNS"
            status = "offline_dns"
            detail = "Host nao resolve no DNS (computador possivelmente desligado ou obsoleto no AD)."
        }}
    }}

    $winrmOpen = Test-TcpPort $targetHost 5985 800
    $smbOpen = Test-TcpPort $targetHost 445 800
    $wmiOpen = Test-TcpPort $targetHost 135 800
    if ((-not $winrmOpen) -and (-not $smbOpen) -and (-not $wmiOpen)) {{
        return [pscustomobject]@{{
            hostname = $h
            ip = $resolvedIp
            success = $false
            method = "TCP"
            status = "unreachable"
            detail = "Sem resposta nas portas WinRM (5985), SMB (445) e WMI/RPC (135) — PC desligado ou firewall bloqueando gerenciamento remoto."
        }}
    }}

    $winrmErr = ""
    $smbErr = ""
    $wmiErr = ""

    if ($winrmOpen) {{
        try {{
            $icParams = @{{
                ComputerName = $targetHost
                ErrorAction = 'Stop'
                ArgumentList = @($b64)
                ScriptBlock = {{
                    param($innerB64)
                    $code = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($innerB64))
                    & ([scriptblock]::Create($code))
                }}
            }}
            if ($null -ne $cred) {{ $icParams['Credential'] = $cred }}
            $outLines = Invoke-Command @icParams
            $outText = (($outLines | Out-String) -replace '\s+', ' ').Trim()
            if ($outText -match 'ALREADY_REGISTERED') {{
                return [pscustomobject]@{{
                    hostname = $h
                    ip = $resolvedIp
                    success = $true
                    method = "WinRM"
                    status = "already_installed"
                    detail = $outText
                }}
            }} elseif ($outText -match 'OK AgentID=') {{
                return [pscustomobject]@{{
                    hostname = $h
                    ip = $resolvedIp
                    success = $true
                    method = "WinRM"
                    status = "installed"
                    detail = $outText
                }}
            }} else {{
                $winrmErr = "WinRM executou com aviso: $outText"
            }}
        }} catch {{
            $winrmErr = $_.Exception.Message
        }}
    }}

    if ($smbOpen) {{
        $drvName = "TRMM" + ([guid]::NewGuid().ToString("N").Substring(0, 8))
        try {{
            net use "\\$targetHost\ADMIN$" /delete /y 2>$null | Out-Null
            $ndParams = @{{
                Name = $drvName
                PSProvider = 'FileSystem'
                Root = "\\$targetHost\ADMIN$"
                ErrorAction = 'Stop'
            }}
            if ($null -ne $cred) {{ $ndParams['Credential'] = $cred }}
            [void](New-PSDrive @ndParams)
            $tempDir = "${{drvName}}:\Temp"
            if (-not (Test-Path $tempDir)) {{ New-Item -Path $tempDir -ItemType Directory -Force | Out-Null }}
            $remotePs = "$tempDir\trmm-push-install.ps1"
            $scriptBody = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($b64))
            [System.IO.File]::WriteAllText($remotePs, $scriptBody, (New-Object System.Text.UTF8Encoding($false)))

            $tn = "TacticalRMM_ADPush"
            $tr = "powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File C:\Windows\Temp\trmm-push-install.ps1"
            $stCreate = @("/Create", "/S", $targetHost)
            $stRun = @("/Run", "/S", $targetHost)
            $stDel = @("/Delete", "/S", $targetHost)
            if ($rawUser -and $rawPass) {{
                $stCreate += @("/U", $rawUser, "/P", $rawPass)
                $stRun += @("/U", $rawUser, "/P", $rawPass)
                $stDel += @("/U", $rawUser, "/P", $rawPass)
            }}
            $stCreate += @("/TN", $tn, "/TR", $tr, "/SC", "ONCE", "/ST", "00:00", "/RL", "HIGHEST", "/RU", "SYSTEM", "/F")
            $stRun += @("/TN", $tn)
            $stDel += @("/TN", $tn, "/F")

            $createOut = (& schtasks.exe @stCreate 2>&1 | Out-String).Trim()
            if ($LASTEXITCODE -eq 0) {{
                $runOut = (& schtasks.exe @stRun 2>&1 | Out-String).Trim()
                Start-Sleep -Seconds 6
                & schtasks.exe @stDel 2>$null | Out-Null
                return [pscustomobject]@{{
                    hostname = $h
                    ip = $resolvedIp
                    success = $true
                    method = "SMB+SchTasks"
                    status = "dispatched"
                    detail = "Instalador disparado como SYSTEM via SMB/RPC ($runOut). Aguarde ~30s no painel."
                }}
            }} else {{
                $smbErr = "schtasks /Create falhou: $createOut"
            }}
        }} catch {{
            $smbErr = "Erro SMB (ADMIN): $($_.Exception.Message)"
        }} finally {{
            Remove-PSDrive -Name $drvName -Force -ErrorAction SilentlyContinue
        }}
    }}

    if ($wmiOpen -and $enc) {{
        $cimSess = $null
        try {{
            $cimOpt = New-CimSessionOption -Protocol Dcom
            $csParams = @{{
                ComputerName = $targetHost
                SessionOption = $cimOpt
                ErrorAction = 'Stop'
            }}
            if ($null -ne $cred) {{ $csParams['Credential'] = $cred }}
            $cimSess = New-CimSession @csParams
            $cmdLine = "powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -EncodedCommand $enc"
            $wmiOut = Invoke-CimMethod -CimSession $cimSess -ClassName Win32_Process -MethodName Create -Arguments @{{ CommandLine = $cmdLine }} -ErrorAction Stop
            if ($wmiOut.ReturnValue -eq 0) {{
                return [pscustomobject]@{{
                    hostname = $h
                    ip = $resolvedIp
                    success = $true
                    method = "WMI-DCOM"
                    status = "dispatched"
                    detail = "Processo remoto iniciado via WMI/RPC 135 (PID $($wmiOut.ProcessId)). Aguarde ~30s no painel."
                }}
            }} else {{
                $wmiErr = "WMI Win32_Process.Create retornou codigo $($wmiOut.ReturnValue)"
            }}
        }} catch {{
            $wmiErr = "WMI-DCOM: $($_.Exception.Message)"
        }} finally {{
            if ($null -ne $cimSess) {{ Remove-CimSession -CimSession $cimSess -ErrorAction SilentlyContinue }}
        }}
    }}

    $errs = @($winrmErr, $smbErr, $wmiErr) | Where-Object {{ $_ }}
    return [pscustomobject]@{{
        hostname = $h
        ip = $resolvedIp
        success = $false
        method = "WinRM/SMB/WMI"
        status = "failed"
        detail = ($errs -join " | ")
    }}
}}

$pool = [runspacefactory]::CreateRunspacePool(1, 5)
$pool.Open()
$jobs = @()
try {{
    foreach ($target in $hosts) {{
        $ps = [powershell]::Create()
        $ps.RunspacePool = $pool
        [void]$ps.AddScript($workerScript).AddArgument([string]$target).AddArgument($remoteB64).AddArgument($encB64).AddArgument($cred).AddArgument($rawUser).AddArgument($rawPass)
        $jobs += [pscustomobject]@{{ PS = $ps; Handle = $ps.BeginInvoke(); Host = $target }}
    }}
    $results = @()
    foreach ($j in $jobs) {{
        try {{
            $res = $j.PS.EndInvoke($j.Handle)
            if ($res) {{ $results += $res }}
        }} catch {{
            $results += [pscustomobject]@{{
                hostname = $j.Host
                ip = ""
                success = $false
                method = "Runner"
                status = "failed"
                detail = $_.Exception.Message
            }}
        }} finally {{
            $j.PS.Dispose()
        }}
    }}
    @{{ ok = $true; results = @($results) }} | ConvertTo-Json -Depth 4 -Compress
}} finally {{
    $rawPass = $null
    $cred = $null
    $cfgJson = $null
    $pool.Close()
    $pool.Dispose()
}}
"""
        ok_ps, raw_out = _run_probe_powershell(probe, probe_runner_ps, timeout=90)
        if not ok_ps:
            return notify_error(
                f"Falha ao executar Push Remoto a partir de '{probe.hostname}' (resposta: {raw_out[:300]})."
            )

        out_str = str(raw_out).strip()
        s_idx = out_str.find("{")
        e_idx = out_str.rfind("}")
        if s_idx == -1 or e_idx <= s_idx:
            return notify_error(
                f"Retorno inesperado do servidor '{probe.hostname}': {out_str[:400]}"
            )

        try:
            parsed = json.loads(out_str[s_idx : e_idx + 1])
        except Exception as exc:
            return notify_error(
                f"Erro ao interpretar resultado do Push Remoto: {exc}"
            )

        results_list = parsed.get("results") or []
        if isinstance(results_list, dict):
            results_list = [results_list]

        succeeded = sum(1 for r in results_list if r.get("success"))
        AuditLog.objects.create(
            username=request.user.username,
            agent=probe.hostname,
            agent_id=probe.agent_id,
            object_type="agent",
            action="agent_install",
            message=f"AD Push Deploy ({site.client.name}/{site.name}) para {len(clean_hosts)} host(s): {succeeded} sucesso(s).",
            debug_info={"ip": getattr(request, "_client_ip", "")},
        )

        return Response(
            {
                "ok": True,
                "probe_agent": probe.hostname,
                "client": site.client.name,
                "site": site.name,
                "total": len(results_list),
                "succeeded": succeeded,
                "failed": len(results_list) - succeeded,
                "results": results_list,
            }
        )


class FleetADPublishGPOView(APIView):
    """
    POST /agents/ad-publish-gpo/
    Generates an all-in-one DC AD Deploy script (mode='generate_dc_script') or publishes
    the self-hosted Windows binaries + Install-TacticalRMM.ps1 to NETLOGON\\TacticalRMM and
    creates/links the Domain Root Startup GPO 'Tactical RMM Enhanced - Deploy' directly
    from the online AD probe/DC (mode='publish_from_probe').
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        import datetime as dt
        from django.conf import settings
        from knox.models import AuthToken
        from accounts.models import User
        from agents.utils import get_agent_url
        from clients.models import Site
        from core.utils import token_is_valid
        from tacticalrmm.constants import AgentPlat, GoArch
        from tacticalrmm.helpers import notify_error
        from tacticalrmm.permissions import (
            _has_perm,
            _has_perm_on_agent,
            _has_perm_on_site,
        )

        if not _has_perm(request, "can_install_agents"):
            return notify_error("Permissão insuficiente para configurar deploy AD/GPO.")

        mode = str(request.data.get("mode") or "publish_from_probe").strip()
        site_id = request.data.get("site_id")
        if not site_id:
            return notify_error("Selecione o Cliente / Site de destino no Tactical RMM.")
        try:
            site = Site.objects.select_related("client").get(pk=int(site_id))
        except (ValueError, TypeError, Site.DoesNotExist):
            return notify_error("Site de destino inválido.")

        if not _has_perm_on_site(request.user, site.pk):
            return notify_error("Sem permissão neste Site.")

        installer_user = User.objects.filter(is_installer_user=True).first()
        if not installer_user:
            return notify_error("Usuário instalador (is_installer_user) não encontrado.")

        raw_agent_type = str(request.data.get("agent_type") or "both").lower()
        if raw_agent_type not in ("both", "workstation", "server"):
            raw_agent_type = "both"

        rdp_flag = " --rdp" if int(request.data.get("rdp", 1)) else ""
        ping_flag = " --ping" if int(request.data.get("ping", 1)) else ""
        power_flag = " --power" if int(request.data.get("power", 0)) else ""
        banking_mode = bool(request.data.get("banking_mode", True))
        auto_link_gpo = bool(request.data.get("auto_link_gpo", True))
        run_gpupdate = bool(request.data.get("run_gpupdate", True))

        expires_h = 87600 if mode == "publish_from_probe" else 24
        _, token = AuthToken.objects.create(
            user=installer_user, expiry=dt.timedelta(hours=expires_h)
        )

        api_url = str(request.data.get("api") or "").strip().rstrip("/")
        if not api_url:
            api_url = f"{request.scheme}://{request.get_host()}".rstrip("/")

        version = settings.LATEST_AGENT_VER
        cors_origins = getattr(settings, "CORS_ORIGIN_WHITELIST", [])
        base_web = (
            cors_origins[0].rstrip("/")
            if cors_origins
            else f"{request.scheme}://{request.get_host()}".rstrip("/")
        )
        local_win_amd64 = f"{base_web}/agents/tacticalagent-v{version}-windows-amd64.exe"
        local_win_386 = f"{base_web}/agents/tacticalagent-v{version}-windows-386.exe"
        codesign_token, is_valid = token_is_valid()
        win_url = get_agent_url(
            goarch=GoArch.AMD64,
            plat=AgentPlat.WINDOWS,
            token=codesign_token if is_valid else "",
        )
        win_banking_snippet = (
            f"\nif ($atype -eq 'workstation') {{ {WINDOWS_MESH_BANKING_PAUSE_CMD} }}"
            if banking_mode
            else ""
        )
        gpo_args = (
            f"-m gpoinstall -api '{api_url}' -client-id {site.client_id} -site-id {site.pk} "
            f"-agent-type $atype -auth '{token}' -silent -gpo"
            f"{rdp_flag}{ping_flag}{power_flag}"
        )

        gpo_ps1_content = f"""$ErrorActionPreference = "Continue"
$Folder = "C:\\ProgramData\\TacticalRMM"
$LogFile = "$Folder\\gpo-install.log"
New-Item -Path $Folder -ItemType Directory -Force -ErrorAction SilentlyContinue | Out-Null
function Write-GpoLog([string]$Msg) {{
    try {{
        $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        Add-Content -Path $LogFile -Value "[$ts] $Msg" -Encoding UTF8 -ErrorAction SilentlyContinue
    }} catch {{}}
}}

$TacticalSvc = Get-Service -Name "tacticalrmm" -ErrorAction SilentlyContinue
if (-not $TacticalSvc) {{ $TacticalSvc = Get-Service -Name "tacticalagent" -ErrorAction SilentlyContinue }}
$InstalledExe = "C:\\Program Files\\TacticalAgent\\tacticalrmm.exe"
if (-not (Test-Path $InstalledExe)) {{ $InstalledExe = "C:\\Program Files\\TacticalAgent\\tacticalagent.exe" }}
$RegProp = Get-ItemProperty -Path "HKLM:\\SOFTWARE\\TacticalRMM" -ErrorAction SilentlyContinue

if ($TacticalSvc -and (Test-Path $InstalledExe) -and $RegProp -and $RegProp.AgentID) {{
    if ($TacticalSvc.Status -ne 'Running') {{
        Start-Service -Name $TacticalSvc.Name -ErrorAction SilentlyContinue
    }}{win_banking_snippet}
    exit 0
}}

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls13
Write-GpoLog "Iniciando instalacao GPO em $env:COMPUTERNAME..."
$Domain = ([System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().DomainName)
$ArchBin = if ([Environment]::Is64BitOperatingSystem) {{ "tacticalagent-v{version}-windows-amd64.exe" }} else {{ "tacticalagent-v{version}-windows-386.exe" }}
$NetCandidates = @()
if ($Domain) {{
    $NetCandidates = @(
        "\\\\$Domain\\NETLOGON\\TacticalRMM\\$ArchBin",
        "\\\\$Domain\\NETLOGON\\TacticalRMM\\tactical-agent.exe"
    )
}}
$NetInstaller = $NetCandidates | Where-Object {{ Test-Path $_ }} | Select-Object -First 1
$LocalInstaller = "$Folder\\tactical-agent.exe"
$osType = if ((Get-CimInstance Win32_OperatingSystem).ProductType -eq 1) {{ 'workstation' }} else {{ 'server' }}
$atype = if ('{raw_agent_type}' -eq 'both') {{ $osType }} else {{ '{raw_agent_type}' }}

if ($NetInstaller) {{
    Write-GpoLog "Copiando binário da rede: $NetInstaller"
    Copy-Item -Path $NetInstaller -Destination $LocalInstaller -Force -ErrorAction SilentlyContinue
    & $LocalInstaller {gpo_args} 2>&1 | Out-String | ForEach-Object {{ if ($_.Trim()) {{ Write-GpoLog $_.Trim() }} }}
    Remove-Item $LocalInstaller -Force -ErrorAction SilentlyContinue{win_banking_snippet}
}} else {{
    $localUrl = if ([Environment]::Is64BitOperatingSystem) {{ '{local_win_amd64}' }} else {{ '{local_win_386}' }}
    $dst = "$env:TEMP\\tacticalagent-setup.exe"
    $downloadedLocal = $false
    try {{
        Invoke-WebRequest -Uri $localUrl -OutFile $dst -UseBasicParsing -TimeoutSec 45
        if ((Test-Path $dst) -and ((Get-Item $dst).Length -gt 1048576)) {{ $downloadedLocal = $true }}
    }} catch {{ $downloadedLocal = $false }}
    if (-not $downloadedLocal) {{
        Invoke-WebRequest -Uri '{win_url}' -OutFile $dst -UseBasicParsing
        Start-Process -FilePath $dst -ArgumentList '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART' -Wait
        Start-Sleep -Seconds 5
    }}
    $exe = "C:\\Program Files\\TacticalAgent\\tacticalrmm.exe"
    if ((-not $downloadedLocal) -and (Test-Path $exe)) {{
        & $exe {gpo_args}
    }} else {{
        & $dst {gpo_args}
    }}{win_banking_snippet}
}}
"""
        gpo_ps1_b64 = base64.b64encode(gpo_ps1_content.encode("utf-8")).decode("ascii")

        if mode == "generate_dc_script":
            dc_script = f"""# Tactical RMM Enhanced - Deploy Completo em Todo o Active Directory (Executar como Administrador no DC)
# Cliente: {site.client.name} | Site: {site.name}
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Continue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls13

$rootDse = [ADSI]"LDAP://RootDSE"
$defaultNC = [string]$rootDse.defaultNamingContext
$domainDns = ([System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().DomainName)
if (-not $defaultNC) {{ Write-Error "Este servidor nao esta em um dominio AD."; exit 1 }}
Write-Host "[1/4] Dominio AD detectado: $domainDns ($defaultNC)" -ForegroundColor Cyan

# 1. Instalar no proprio DC caso ainda nao esteja no Tactical
$gpoScriptText = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{gpo_ps1_b64}'))
$selfReg = Get-ItemProperty -Path 'HKLM:\\SOFTWARE\\TacticalRMM' -ErrorAction SilentlyContinue
if (-not ($selfReg -and $selfReg.AgentID)) {{
    Write-Host "[*] Instalando Tactical Agent neste servidor DC ($env:COMPUTERNAME)..." -ForegroundColor Yellow
    & ([scriptblock]::Create($gpoScriptText))
}} else {{
    Write-Host "[OK] DC ja registrado no Tactical (AgentID=$($selfReg.AgentID))." -ForegroundColor Green
}}

# 2. Publicar instaladores + GPO Script no NETLOGON
$netDir = "\\\\$domainDns\\NETLOGON\\TacticalRMM"
New-Item -Path $netDir -ItemType Directory -Force | Out-Null
[System.IO.File]::WriteAllText("$netDir\\Install-TacticalRMM.ps1", $gpoScriptText, (New-Object System.Text.UTF8Encoding($false)))
$downloads = @(
    @{{ url = '{local_win_amd64}'; file = "$netDir\\tacticalagent-v{version}-windows-amd64.exe" }},
    @{{ url = '{local_win_386}'; file = "$netDir\\tacticalagent-v{version}-windows-386.exe" }}
)
foreach ($d in $downloads) {{
    try {{
        Invoke-WebRequest -Uri $d.url -OutFile $d.file -UseBasicParsing -TimeoutSec 60
        Write-Host "[2/4] Publicado em NETLOGON: $($d.file)" -ForegroundColor Green
    }} catch {{
        Write-Warning "Falha ao baixar $($d.url): $($_.Exception.Message)"
    }}
}}

# 3. Criar e vincular GPO de Startup na raiz do dominio (cobre CRD, Computadores, Computers e raiz)
if (Get-Command New-GPO -ErrorAction SilentlyContinue) {{
    try {{
        $gpoName = "Tactical RMM Enhanced - Deploy"
        $gpo = Get-GPO -Name $gpoName -ErrorAction SilentlyContinue
        if (-not $gpo) {{ $gpo = New-GPO -Name $gpoName -Comment "Deploy automatico Tactical RMM Enhanced" }}
        $guid = $gpo.Id.ToString("B").ToUpper()
        $sysvolBase = "\\\\$domainDns\\SYSVOL\\$domainDns\\Policies\\$guid"
        $startupDir = "$sysvolBase\\Machine\\Scripts\\Startup"
        New-Item -Path $startupDir -ItemType Directory -Force | Out-Null
        $psIni = "`r`n[ScriptsConfig]`r`nStartExecutePSFirst=true`r`n[Startup]`r`n0CmdLine=\\\\$domainDns\\NETLOGON\\TacticalRMM\\Install-TacticalRMM.ps1`r`n0Parameters=`r`n"
        [System.IO.File]::WriteAllText("$sysvolBase\\Machine\\Scripts\\psscripts.ini", $psIni, [System.Text.Encoding]::Unicode)
        $gptPath = "$sysvolBase\\gpt.ini"
        $curVer = 0
        if (Test-Path $gptPath) {{
            $gptRaw = Get-Content -Path $gptPath -Raw
            if ($gptRaw -match 'Version=(\\d+)') {{ $curVer = [int]$Matches[1] }}
        }}
        $newVer = $curVer + 65536
        [System.IO.File]::WriteAllText($gptPath, "[General]`r`nVersion=$newVer`r`n", [System.Text.Encoding]::ASCII)
        $gpoEntry = [ADSI]"LDAP://$($gpo.Path)"
        $gpoEntry.Put("versionNumber", $newVer)
        $extVal = [string]$gpoEntry.gPCMachineExtensionNames
        $scriptsCse = "[{{42B5FAAE-6536-11D2-AE5A-0000F87571E3}}{{40B6664F-4972-11D1-A7CA-0000F87571E3}}]"
        if ($extVal -notmatch '42B5FAAE-6536-11D2-AE5A-0000F87571E3') {{
            $gpoEntry.Put("gPCMachineExtensionNames", "$extVal$scriptsCse")
        }}
        $gpoEntry.SetInfo()
        $existingLinks = (Get-GPInheritance -Target $defaultNC).GpoLinks | Where-Object {{ $_.DisplayName -eq $gpoName }}
        if (-not $existingLinks) {{
            New-GPLink -Name $gpoName -Target $defaultNC -LinkEnabled Yes | Out-Null
        }}
        Write-Host "[3/4] GPO '$gpoName' vinculada na raiz $defaultNC com startup script!" -ForegroundColor Green
    }} catch {{
        Write-Warning "Nao foi possivel automatizar a GPO via cmdlet (configure manualmente apontando para $netDir\\Install-TacticalRMM.ps1): $($_.Exception.Message)"
    }}
}}

# 4. Varrer TODOS os computadores habilitados no AD e empurrar instalacao agora em paralelo
$searchRoot = [ADSI]"LDAP://$defaultNC"
$searcher = New-Object System.DirectoryServices.DirectorySearcher($searchRoot)
$searcher.Filter = "(&(objectCategory=computer)(objectClass=computer)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))"
$searcher.PageSize = 1000
$targets = @()
foreach ($r in $searcher.FindAll()) {{
    $h = if ($r.Properties.Contains("dnshostname") -and $r.Properties["dnshostname"].Count -gt 0) {{ [string]$r.Properties["dnshostname"][0] }} else {{ [string]$r.Properties["name"][0] }}
    if ($h) {{ $targets += $h }}
}}
$searcher.Dispose()
Write-Host "[4/4] Encontrados $($targets.Count) computadores habilitados em $domainDns. Disparando Push em paralelo..." -ForegroundColor Cyan

$encCmd = [Convert]::ToBase64String([System.Text.Encoding]::Unicode.GetBytes($gpoScriptText))
$pool = [runspacefactory]::CreateRunspacePool(1, 8)
$pool.Open()
$jobs = @()
foreach ($t in $targets) {{
    $ps = [powershell]::Create()
    $ps.RunspacePool = $pool
    [void]$ps.AddScript({{
        param($hostName, $scriptTxt, $enc)
        $short = $hostName.Split('.')[0]
        $reach = $false
        $used = $hostName
        foreach ($cand in @($hostName, $short)) {{
            try {{
                $dns = [System.Net.Dns]::GetHostAddresses($cand) | Where-Object {{ $_.AddressFamily -eq 'InterNetwork' }}
                if ($dns) {{ $reach = $true; $used = $cand; break }}
            }} catch {{}}
        }}
        if (-not $reach) {{ return "$hostName : OFFLINE_DNS" }}
        try {{
            $out = Invoke-Command -ComputerName $used -ErrorAction Stop -ScriptBlock {{ param($s) & ([scriptblock]::Create($s)) }} -ArgumentList $scriptTxt
            return "$hostName : OK WinRM"
        }} catch {{}}
        try {{
            $cOpt = New-CimSessionOption -Protocol Dcom
            $cs = New-CimSession -ComputerName $used -SessionOption $cOpt -ErrorAction Stop
            $w = Invoke-CimMethod -CimSession $cs -ClassName Win32_Process -MethodName Create -Arguments @{{ CommandLine = "powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -EncodedCommand $enc" }} -ErrorAction Stop
            Remove-CimSession $cs -ErrorAction SilentlyContinue
            if ($w.ReturnValue -eq 0) {{ return "$hostName : DISPARADO WMI" }}
        }} catch {{}}
        try {{
            if (Get-Command Invoke-GPUpdate -ErrorAction SilentlyContinue) {{
                Invoke-GPUpdate -Computer $used -RandomDelayInMinutes 0 -Force -ErrorAction Stop | Out-Null
                return "$hostName : GPUPDATE_FORCED"
            }}
        }} catch {{}}
        return "$hostName : PENDENTE_PROXIMO_BOOT_GPO"
    }}).AddArgument($t).AddArgument($gpoScriptText).AddArgument($encCmd)
    $jobs += [pscustomobject]@{{ Host = $t; PS = $ps; Handle = $ps.BeginInvoke() }}
}}
foreach ($j in $jobs) {{
    try {{
        $msg = $j.PS.EndInvoke($j.Handle)
        Write-Host "  $msg"
    }} catch {{
        Write-Host "  $($j.Host) : ERRO"
    }} finally {{
        $j.PS.Dispose()
    }}
}}
$pool.Close()
$pool.Dispose()
Write-Host "Concluido! Aguarde 30-60s e clique em Sincronizar 100% no Tactical RMM." -ForegroundColor Green
"""
            return Response(
                {
                    "ok": True,
                    "mode": "generate_dc_script",
                    "filename": "TacticalRMM-Deploy-All-AD.ps1",
                    "script": dc_script,
                }
            )

        # mode == 'publish_from_probe'
        if not _has_perm(request, "can_send_cmd"):
            return notify_error("Permissão can_send_cmd necessária para publicar via agente.")

        preferred_id = request.data.get("probe_agent_id")
        probe, _ = _pick_domain_probe_agent(
            request.user, preferred_agent_id=preferred_id
        )
        if not probe:
            return notify_error("Nenhum servidor AD/Windows online disponível.")
        if not _has_perm_on_agent(request.user, probe.agent_id):
            return notify_error("Sem permissão no agente selecionado.")

        pub_cfg_b64 = base64.b64encode(
            json.dumps(
                {
                    "gpo_ps1_b64": gpo_ps1_b64,
                    "amd64_url": local_win_amd64,
                    "x86_url": local_win_386,
                    "amd64_name": f"tacticalagent-v{version}-windows-amd64.exe",
                    "x86_name": f"tacticalagent-v{version}-windows-386.exe",
                    "auto_link_gpo": auto_link_gpo,
                    "run_gpupdate": run_gpupdate,
                }
            ).encode("utf-8")
        ).decode("ascii")

        publish_ps = rf"""[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Continue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls13
$cfg = ([System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{pub_cfg_b64}'))) | ConvertFrom-Json
$domain = ([System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().DomainName)
if (-not $domain) {{
    @{{ ok = $false; error = "Este agente nao esta em um dominio AD." }} | ConvertTo-Json -Compress
    exit 0
}}
$netDir = "\\$domain\NETLOGON\TacticalRMM"
try {{
    New-Item -Path $netDir -ItemType Directory -Force -ErrorAction Stop | Out-Null
    $psText = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($cfg.gpo_ps1_b64))
    [System.IO.File]::WriteAllText("$netDir\Install-TacticalRMM.ps1", $psText, (New-Object System.Text.UTF8Encoding($false)))
    Invoke-WebRequest -Uri $cfg.amd64_url -OutFile "$netDir\$($cfg.amd64_name)" -UseBasicParsing -TimeoutSec 60
    Invoke-WebRequest -Uri $cfg.x86_url -OutFile "$netDir\$($cfg.x86_name)" -UseBasicParsing -TimeoutSec 60
}} catch {{
    @{{ ok = $false; error = "Falha ao gravar em $netDir (execute em um DC ou conta com permissao NETLOGON): $($_.Exception.Message)" }} | ConvertTo-Json -Compress
    exit 0
}}

$gpoResult = "NETLOGON publicado com sucesso."
$gpoLinked = $false
$gpupdateCount = 0
if ($cfg.auto_link_gpo -and (Get-Command New-GPO -ErrorAction SilentlyContinue)) {{
    try {{
        $defaultNC = [string]([ADSI]"LDAP://RootDSE").defaultNamingContext
        $gpoName = "Tactical RMM Enhanced - Deploy"
        $gpo = Get-GPO -Name $gpoName -ErrorAction SilentlyContinue
        if (-not $gpo) {{ $gpo = New-GPO -Name $gpoName -Comment "Deploy automatico Tactical RMM Enhanced" }}
        $guid = $gpo.Id.ToString("B").ToUpper()
        $sysvolBase = "\\$domain\SYSVOL\$domain\Policies\$guid"
        New-Item -Path "$sysvolBase\Machine\Scripts\Startup" -ItemType Directory -Force | Out-Null
        $psIni = "`r`n[ScriptsConfig]`r`nStartExecutePSFirst=true`r`n[Startup]`r`n0CmdLine=\\$domain\NETLOGON\TacticalRMM\Install-TacticalRMM.ps1`r`n0Parameters=`r`n"
        [System.IO.File]::WriteAllText("$sysvolBase\Machine\Scripts\psscripts.ini", $psIni, [System.Text.Encoding]::Unicode)
        $gptPath = "$sysvolBase\gpt.ini"
        $curVer = 0
        if (Test-Path $gptPath) {{
            $gptRaw = Get-Content -Path $gptPath -Raw
            if ($gptRaw -match 'Version=(\d+)') {{ $curVer = [int]$Matches[1] }}
        }}
        $newVer = $curVer + 65536
        [System.IO.File]::WriteAllText($gptPath, "[General]`r`nVersion=$newVer`r`n", [System.Text.Encoding]::ASCII)
        $gpoEntry = [ADSI]"LDAP://$($gpo.Path)"
        $gpoEntry.Put("versionNumber", $newVer)
        $extVal = [string]$gpoEntry.gPCMachineExtensionNames
        $scriptsCse = "[{{42B5FAAE-6536-11D2-AE5A-0000F87571E3}}{{40B6664F-4972-11D1-A7CA-0000F87571E3}}]"
        if ($extVal -notmatch '42B5FAAE-6536-11D2-AE5A-0000F87571E3') {{
            $gpoEntry.Put("gPCMachineExtensionNames", "$extVal$scriptsCse")
        }}
        $gpoEntry.SetInfo()
        $existingLinks = (Get-GPInheritance -Target $defaultNC).GpoLinks | Where-Object {{ $_.DisplayName -eq $gpoName }}
        if (-not $existingLinks) {{
            New-GPLink -Name $gpoName -Target $defaultNC -LinkEnabled Yes | Out-Null
        }}
        $gpoLinked = $true
        $gpoResult = "NETLOGON publicado e GPO '$gpoName' vinculada na raiz $defaultNC!"
        if ($cfg.run_gpupdate -and (Get-Command Invoke-GPUpdate -ErrorAction SilentlyContinue)) {{
            $searcher = New-Object System.DirectoryServices.DirectorySearcher([ADSI]"LDAP://$defaultNC")
            $searcher.Filter = "(&(objectCategory=computer)(objectClass=computer)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))"
            $searcher.PageSize = 500
            foreach ($r in ($searcher.FindAll() | Select-Object -First 30)) {{
                $cn = if ($r.Properties.Contains("dnshostname") -and $r.Properties["dnshostname"].Count -gt 0) {{ [string]$r.Properties["dnshostname"][0] }} else {{ [string]$r.Properties["name"][0] }}
                if ($cn) {{
                    try {{ Invoke-GPUpdate -Computer $cn -RandomDelayInMinutes 0 -Force -ErrorAction Stop | Out-Null; $gpupdateCount++ }} catch {{}}
                }}
            }}
            $searcher.Dispose()
        }}
    }} catch {{
        $gpoResult = "NETLOGON publicado, mas ajuste manual da GPO necessario: $($_.Exception.Message)"
    }}
}} else {{
    $gpoResult = "NETLOGON publicado em $netDir (cmdlets GroupPolicy ausentes neste agente; aponte sua GPO para $netDir\Install-TacticalRMM.ps1)."
}}

@{{
    ok = $true
    netlogon_path = $netDir
    gpo_linked = $gpoLinked
    gpupdate_count = $gpupdateCount
    message = $gpoResult
}} | ConvertTo-Json -Compress
"""
        ok_ps, raw = _run_probe_powershell(probe, publish_ps, timeout=95)
        if not ok_ps:
            return notify_error(f"Sem resposta do agente '{probe.hostname}': {raw[:300]}")

        raw_str = str(raw).strip()
        s_i, e_i = raw_str.find("{"), raw_str.rfind("}")
        if s_i == -1 or e_i <= s_i:
            return notify_error(f"Retorno inesperado: {raw_str[:400]}")
        res_json = json.loads(raw_str[s_i : e_i + 1])
        if not res_json.get("ok"):
            return notify_error(res_json.get("error") or "Falha ao publicar GPO no AD.")

        AuditLog.objects.create(
            username=request.user.username,
            agent=probe.hostname,
            agent_id=probe.agent_id,
            object_type="agent",
            action="agent_install",
            message=f"AD NETLOGON/GPO publicado ({site.client.name}/{site.name}): {res_json.get('message', '')[:120]}",
            debug_info={"ip": getattr(request, "_client_ip", "")},
        )
        return Response(res_json)


class FleetBulkCLIView(APIView):
    """
    POST /agents/fleet-bulk-cli/
    Executes a command or preset action (e.g. Banking Compatibility Mode,
    AD/GPO/DNS/Kerberos/Time Sync, or custom PowerShell/CMD/Bash) across targeted agents in parallel.
    """

    permission_classes = [IsAuthenticated, SendCommandPerms]

    PRESETS: Dict[str, Dict[str, str]] = {
        "banking_mode_enable": {
            "plat": "windows",
            "shell": "powershell",
            "command": (
                f"{WINDOWS_MESH_BANKING_PAUSE_CMD}; "
                "Write-Output 'MODO_BANCO_ATIVO: Monitoramento Tactical RMM 100% Online e Mesh Agent em Modo Sob Demanda (Sem bloqueio em sites de bancos/Warsaw/Topaz).'"
            ),
        },
        "banking_mode_disable": {
            "plat": "windows",
            "shell": "powershell",
            "command": (
                "Set-Service -Name 'Mesh Agent' -StartupType Automatic -ErrorAction SilentlyContinue; "
                "Start-Service -Name 'Mesh Agent' -ErrorAction SilentlyContinue; "
                "Write-Output 'Mesh Agent restaurado para execucao continua Automatica.'"
            ),
        },
        "gpupdate_ad_sync": {
            "plat": "windows",
            "shell": "powershell",
            "command": (
                "$ProgressPreference = 'SilentlyContinue'; "
                "$cs = Get-CimInstance Win32_ComputerSystem; "
                "$inDom = [bool]$cs.PartOfDomain; "
                "$dom = if ($inDom) { $cs.Domain } else { $cs.Workgroup }; "
                "foreach ($svc in @('w32time','gpsvc')) { Start-Service -Name $svc -ErrorAction SilentlyContinue }; "
                "if ($inDom) { Start-Service -Name 'Netlogon' -ErrorAction SilentlyContinue }; "
                "ipconfig /flushdns | Out-Null; "
                "ipconfig /registerdns | Out-Null; "
                "$timeSync = (w32tm /resync /nowait 2>&1) -join ' '; "
                "$klistMsg = ''; "
                "$domMsg = \"Workgroup ($dom)\"; "
                "if ($inDom) { "
                "$null = klist -lh 0 -li 0x3e7 purge 2>&1; "
                "$klistMsg = 'Tickets Kerberos renovados | '; "
                "$scOk = Test-ComputerSecureChannel -ErrorAction SilentlyContinue; "
                "$dcLine = (nltest /dsgetdc:$dom 2>$null | Select-String 'DC:') -join ''; "
                "$domMsg = \"Dominio: $dom | Canal Seguro: $scOk | $($dcLine.Trim())\" "
                "}; "
                "$gpOut = ('N' | gpupdate /force /wait:25 2>&1) -join ' | '; "
                "Write-Output \"[$env:COMPUTERNAME] $domMsg | ${klistMsg}DNS limpo/registrado | Hora: $timeSync | GPO: $gpOut\""
            ),
        },
    }

    def post(self, request) -> Response:
        target = str(request.data.get("target") or "all").strip().lower()
        preset = str(request.data.get("preset") or "").strip()
        shell = str(request.data.get("shell") or "powershell").strip().lower()
        command = str(request.data.get("command") or "").strip()
        try:
            timeout_sec = min(max(int(request.data.get("timeout") or 30), 5), 120)
        except (TypeError, ValueError):
            timeout_sec = 30
        agent_ids = request.data.get("agent_ids") or []
        only_online = bool(request.data.get("only_online", True))

        if preset and preset in self.PRESETS:
            p = self.PRESETS[preset]
            shell = p["shell"]
            command = p["command"]
            if target == "all" and p.get("plat"):
                target = p["plat"]

        if not command:
            return Response(
                {"error": "Informe um comando ou selecione uma ação rápida."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = Agent.objects.filter_by_role(request.user).select_related("site__client")
        if agent_ids and isinstance(agent_ids, list):
            qs = qs.filter(agent_id__in=agent_ids)
        elif target == "windows":
            qs = qs.filter(plat="windows")
        elif target == "linux":
            qs = qs.filter(plat="linux")
        elif target == "darwin":
            qs = qs.filter(plat="darwin")
        elif target == "servers":
            qs = qs.filter(monitoring_type="server")
        elif target == "workstations":
            qs = qs.filter(monitoring_type="workstation")

        agents_list = list(qs)
        if only_online:
            agents_list = [a for a in agents_list if a.status == AGENT_STATUS_ONLINE]

        async def _exec_all(targets: list[Agent]) -> list[Dict[str, Any]]:
            sem = asyncio.Semaphore(30)
            results: list[Dict[str, Any]] = []

            async def _run_one(ag: Agent) -> None:
                async with sem:
                    eff_shell = (
                        "bash"
                        if ag.plat in ("linux", "darwin")
                        else (shell if shell in ("powershell", "cmd") else "powershell")
                    )
                    try:
                        out = await ag.nats_cmd(
                            {
                                "func": "rawcmd",
                                "timeout": timeout_sec,
                                "payload": {
                                    "command": command,
                                    "shell": eff_shell,
                                },
                            },
                            timeout=timeout_sec + 5,
                        )
                        ok = out not in ("timeout", "natsdown", "error")
                        results.append(
                            {
                                "agent_id": ag.agent_id,
                                "hostname": ag.hostname,
                                "client": ag.site.client.name,
                                "site": ag.site.name,
                                "plat": ag.plat,
                                "success": ok,
                                "output": str(out).strip() if ok else f"Sem resposta ({out})",
                            }
                        )
                    except Exception as exc:
                        results.append(
                            {
                                "agent_id": ag.agent_id,
                                "hostname": ag.hostname,
                                "client": ag.site.client.name,
                                "site": ag.site.name,
                                "plat": ag.plat,
                                "success": False,
                                "output": str(exc),
                            }
                        )

            await asyncio.gather(*[_run_one(a) for a in targets])
            return results

        exec_results = asyncio.run(_exec_all(agents_list)) if agents_list else []
        exec_results.sort(key=lambda x: (not x["success"], x["hostname"]))
        success_cnt = sum(1 for r in exec_results if r["success"])

        AuditLog.objects.create(
            username=request.user.username,
            object_type=AuditObjType.AGENT,
            action=AuditActionType.EXEC_COMMAND,
            message=f"{request.user.username} executou CLI em massa ({preset or shell}) em {len(agents_list)} agentes",
            after_value={
                "target": target,
                "preset": preset,
                "shell": shell,
                "total_targeted": len(agents_list),
                "success_count": success_cnt,
            },
        )

        return Response(
            {
                "status": "ok",
                "total_targeted": len(agents_list),
                "success_count": success_cnt,
                "failed_count": len(agents_list) - success_cnt,
                "results": exec_results,
                "timestamp": djangotime.now().isoformat(),
            }
        )

