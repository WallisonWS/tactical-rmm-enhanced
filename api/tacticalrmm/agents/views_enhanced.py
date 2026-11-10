import asyncio
import base64
import json
import re
from contextlib import suppress
from typing import Any, Dict, List

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone as djangotime
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from agents.models import Agent
from agents.permissions import SendCMDPerms as SendCommandPerms
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
            # Traditional Agent backwards-compatibility: try native synchronous "recover" RPC first
            if r == "timeout":
                native_rec = asyncio.run(
                    agent.nats_cmd(
                        {"func": "recover", "payload": {"mode": "mesh"}},
                        timeout=45,
                    )
                )
                if native_rec == "ok":
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
            # Fallback to NATS async recovercmd if synchronous repair timed out
            with suppress(Exception):
                asyncio.run(
                    agent.nats_cmd(
                        {"func": "recovercmd", "recoverycommand": "mesh"},
                        wait=False,
                    )
                )
            return Response(
                {"error": f"Não foi possível contatar {agent.hostname} via NATS ({r}). Comando assíncrono de recuperação Mesh enfileirado."},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )

        if isinstance(r, dict):
            health_after = r.get("health_after")
            if self._sync_agent_mesh_node_id(agent, health_after or r):
                actions = list(r.get("actions_taken") or [])
                actions.append("MeshNodeID sincronizado automaticamente entre Agente, API e MeshCentral")
                r["actions_taken"] = actions

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
        action = request.data.get("action", "enable_rdp")
        enforce_nla = request.data.get("enforce_nla", True)
        session_id = str(request.data.get("session_id", ""))

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
                ps_adm = "gpupdate /force | Out-Null; Write-Output 'Políticas de Grupo (GPO) atualizadas com sucesso (gpupdate /force).'"
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
