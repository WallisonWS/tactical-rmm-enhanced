import asyncio
import copy
import re
import threading
import urllib.parse
from io import StringIO
from pathlib import Path
from typing import Optional, Tuple

from django.conf import settings
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from packaging import version as pyver
from rest_framework.response import Response

from checks.models import CheckResult
from core.utils import get_core_settings, get_mesh_device_id, get_mesh_ws_url
from tacticalrmm.constants import (
    AGENT_DEFER,
    AgentPlat,
    AlertSeverity,
    CheckStatus,
    CheckType,
    FILE_BROWSER_MAX_ARCHIVE_PATHS,
    FILE_BROWSER_MAX_DELETE_PATHS,
    FILE_BROWSER_MAX_NAME_FILTER_LEN,
    MeshAgentIdent,
)
from tacticalrmm.helpers import notify_error


def get_agent_url(*, goarch: str, plat: str, token: str = "") -> str:
    ver = settings.LATEST_AGENT_VER
    if token:
        params = {
            "version": ver,
            "arch": goarch,
            "token": token,
            "plat": plat,
            "api": settings.ALLOWED_HOSTS[0],
        }
        return settings.AGENTS_URL + urllib.parse.urlencode(params)

    if plat == AgentPlat.WINDOWS:
        return f"https://github.com/amidaware/rmmagent/releases/download/v{ver}/tacticalagent-v{ver}-{plat}-{goarch}.exe"

    # For Linux (Ubuntu / Debian / Fedora) & macOS without commercial code-signing token,
    # point to the RMM frontend's locally hosted agent binaries (/agents/) with automatic source compile fallback in agent_linux.sh
    cors_origins = getattr(settings, "CORS_ORIGIN_WHITELIST", [])
    base_web = cors_origins[0] if cors_origins else f"https://{settings.ALLOWED_HOSTS[0]}"
    return f"{base_web.rstrip('/')}/agents/tacticalagent-v{ver}-{plat}-{goarch}"


def generate_linux_install(
    client: str,
    site: str,
    agent_type: str,
    arch: str,
    token: str,
    api: str,
    download_url: str,
    distro: str = "universal",
) -> FileResponse:
    match arch:
        case "amd64":
            arch_id = MeshAgentIdent.LINUX64
        case "386":
            arch_id = MeshAgentIdent.LINUX32
        case "arm64":
            arch_id = MeshAgentIdent.LINUX_ARM_64
        case "arm":
            arch_id = MeshAgentIdent.LINUX_ARM_HF
        case _:
            arch_id = "not_found"

    core = get_core_settings()

    try:
        uri = get_mesh_ws_url()
        mesh_id = asyncio.run(get_mesh_device_id(uri, core.mesh_device_group))
        mesh_dl = (
            f"{core.mesh_site}/meshagents?id={mesh_id}&installflags=2&meshinstall={arch_id}"
        )
    except Exception:
        mesh_dl = ""

    text = Path(settings.LINUX_AGENT_SCRIPT).read_text(encoding="utf-8")

    replace = {
        "agentDLChange": download_url,
        "meshDLChange": mesh_dl,
        "clientIDChange": client,
        "siteIDChange": site,
        "agentTypeChange": agent_type,
        "tokenChange": token,
        "apiURLChange": api,
        "distroChange": distro,
    }

    for i, j in replace.items():
        text = text.replace(i, j)

    text = text.replace("\r\n", "\n") + "\n"
    with StringIO(text) as fp:
        return FileResponse(
            fp.read(), as_attachment=True, filename=f"linux_{distro}_agent_install.sh"
        )


def get_validated_agent(agent_id, min_version="2.10.0"):
    from .models import Agent

    agent = get_object_or_404(Agent.objects.defer(*AGENT_DEFER), agent_id=agent_id)

    if pyver.parse(agent.version) < pyver.parse(min_version):
        return notify_error(
            f"This feature requires agent version {min_version} or higher."
        )

    return agent


_nats_notify_loop: Optional[asyncio.AbstractEventLoop] = None
_nats_notify_thread: Optional[threading.Thread] = None
_nats_notify_lock = threading.Lock()


def _ensure_nats_notify_loop() -> asyncio.AbstractEventLoop:
    global _nats_notify_loop, _nats_notify_thread
    with _nats_notify_lock:
        if _nats_notify_loop is None:
            loop = asyncio.new_event_loop()

            def _run() -> None:
                asyncio.set_event_loop(loop)
                loop.run_forever()

            _nats_notify_thread = threading.Thread(
                target=_run, daemon=True, name="nats-notify"
            )
            _nats_notify_thread.start()
            _nats_notify_loop = loop
    return _nats_notify_loop


_NATS_UNAVAILABLE = ("timeout", "natsdown")
NATS_UNAVAILABLE_MESSAGE = "Unable to contact the agent"
NATS_FAILED_PREFIX = "NATS communication failed"


def _nats_unavailable_error(result) -> Optional[Response]:
    if result in _NATS_UNAVAILABLE:
        return notify_error(NATS_UNAVAILABLE_MESSAGE)
    return None


def send_nats_notification(agent, func: str, payload: dict) -> Optional[Response]:
    loop = _ensure_nats_notify_loop()
    data = {"func": func, "payload": payload}
    try:
        future = asyncio.run_coroutine_threadsafe(
            agent.nats_cmd(data, wait=False),
            loop,
        )
        result = future.result(timeout=10)
    except Exception as e:
        return notify_error(f"{NATS_FAILED_PREFIX}: {str(e)}")
    return _nats_unavailable_error(result)


def send_nats_command(
    agent, func: str, payload: dict, timeout: int = 60, *, prefix_error: bool = True
):
    try:
        data = {"func": func, "payload": payload}
        response = asyncio.run(agent.nats_cmd(data, timeout=timeout))
    except Exception as e:
        return notify_error(f"{NATS_FAILED_PREFIX}: {str(e)}")

    unavailable = _nats_unavailable_error(response)
    if unavailable is not None:
        return unavailable

    if isinstance(response, dict) and "error" in response:
        err = str(response["error"])
        if prefix_error:
            return notify_error(f"{func.replace('_', ' ').title()} failed: {err}")
        return notify_error(err)

    return response


def strip_relation_caches_for_cache(instances: list, keep: tuple = ("script",)) -> list:
    # returns shallow copies of model instances safe to pickle into redis cache
    # this was found when a server was using an insane amount of RAM for redis cache, after debugging found it was due to adding many agents in policy exclusions
    # checks/tasks that were being cached were carrying select_related/prefetch graphs with them (check -> policy -> excluded_agents -> full agent rows with wmi_detail etc.)
    # causing massive cache keys (25 or so MB each instead of a few KB)
    # only relations in "keep", like check.script for the check runner, are kept, cuz these are needed by consumers of the cached values
    cleaned = []
    for instance in instances:
        obj = copy.copy(instance)
        obj._state = copy.copy(instance._state)
        obj._state.fields_cache = {
            field: value
            for field, value in instance._state.fields_cache.items()
            if field in keep
        }
        obj._prefetched_objects_cache = {}
        # results are attached per agent at runtime, never valid to cache
        obj.__dict__.pop("check_result", None)
        obj.__dict__.pop("task_result", None)
        cleaned.append(obj)
    return cleaned


def calculate_agent_checks(agent) -> dict:
    total, passing, failing, warning, info = 0, 0, 0, 0, 0

    for check in agent.get_checks_with_policies(exclude_overridden=True):
        total += 1
        if (
            not hasattr(check.check_result, "status")
            or isinstance(check.check_result, CheckResult)
            and check.check_result.status == CheckStatus.PASSING
        ):
            passing += 1
        elif (
            isinstance(check.check_result, CheckResult)
            and check.check_result.status == CheckStatus.FAILING
        ):
            alert_severity = (
                check.check_result.alert_severity
                if check.check_type
                in (
                    CheckType.MEMORY,
                    CheckType.CPU_LOAD,
                    CheckType.DISK_SPACE,
                    CheckType.SCRIPT,
                )
                else check.alert_severity
            )
            if alert_severity == AlertSeverity.ERROR:
                failing += 1
            elif alert_severity == AlertSeverity.WARNING:
                warning += 1
            elif alert_severity == AlertSeverity.INFO:
                info += 1

    ret = {
        "total": total,
        "passing": passing,
        "failing": failing,
        "warning": warning,
        "info": info,
        "has_failing_checks": failing > 0 or warning > 0,
    }
    return ret


def is_windows_path(s: str) -> bool:
    s = (s or "").strip()
    if not s:
        return False
    if any(x in s for x in ('"', "'", "\n", "\r", "&", "|", ";")):
        return False
    if not re.match(r"^(?:[a-zA-Z]:\\|\\\\)", s):
        return False
    if not s.lower().endswith(".exe"):
        return False
    return True


def is_posix_abs_path(s: str) -> bool:
    s = (s or "").strip()
    if not s:
        return False
    if any(x in s for x in ('"', "'", "\n", "\r", "&", "|", ";")):
        return False
    return s.startswith("/")


_INVALID_FILENAME_CHARS = frozenset('<>:"/\\|?*\x00')
_WINDOWS_RESERVED_NAMES = frozenset(
    ["CON", "PRN", "AUX", "NUL"]
    + [f"COM{i}" for i in range(10)]
    + [f"LPT{i}" for i in range(10)]
)
_WINDOWS_ABS_PATH_RE = re.compile(r"^(?:[a-zA-Z]:\\|\\\\[^\\]+\\[^\\]+)")
_PATH_CONTROL_CHARS = ("\n", "\r", "\x00")


def _path_has_traversal(path: str, plat: str = "") -> bool:
    value = (path or "").strip()
    if plat == "windows":
        parts = re.split(r"[\\/]+", value)
    else:
        parts = value.split("/")
    return ".." in parts


def validate_fs_name(
    raw_name,
    field: str = "name",
    *,
    ban_trailing_space_or_period: bool = True,
    ban_windows_reserved: bool = False,
) -> Optional[str]:
    """
    Validate a single filesystem name segment (mkdir / rename / upload filename).
    """
    if raw_name is None or not str(raw_name).strip():
        return f"{field} is required"

    if ban_trailing_space_or_period:
        name = str(raw_name)
        if name.endswith(" ") or name.endswith("."):
            return f"{field} cannot end with a space or a period"
        trimmed = name.strip()
    else:
        trimmed = str(raw_name).strip()

    if trimmed in (".", ".."):
        return f"{field} is invalid"
    if len(trimmed) > 255:
        return f"{field} is too long"
    if any(ch in _INVALID_FILENAME_CHARS for ch in trimmed):
        return f"{field} contains invalid characters"
    if (
        ban_windows_reserved
        and trimmed.split(".")[0].rstrip(" ").upper() in _WINDOWS_RESERVED_NAMES
    ):
        return f"{field} is reserved by Windows (CON, PRN, AUX, NUL, COM1–9, LPT1–9)"
    return None


def validate_file_browser_name(
    raw_name, field: str = "name", plat: Optional[str] = None
) -> Optional[str]:
    windows = plat in (None, AgentPlat.WINDOWS)
    return validate_fs_name(
        raw_name,
        field=field,
        ban_trailing_space_or_period=windows,
        ban_windows_reserved=windows,
    )


def validate_file_transfer_filename(
    filename: str,
    *,
    ban_trailing_space_or_period: bool = True,
    ban_windows_reserved: bool = False,
) -> Optional[str]:
    return validate_fs_name(
        filename,
        field="filename",
        ban_trailing_space_or_period=ban_trailing_space_or_period,
        ban_windows_reserved=ban_windows_reserved,
    )


def validate_absolute_agent_path(
    path: str,
    plat: str,
    *,
    field: str = "path",
    normalize: bool = False,
) -> Optional[str]:
    """
    Shared absolute path checks for File Browser and file transfer.
    """
    value = (
        normalize_file_browser_path(path, plat) if normalize else (path or "").strip()
    )
    if not value:
        return f"{field} is required"

    if any(x in value for x in _PATH_CONTROL_CHARS):
        return f"{field} contains invalid characters"
    if _path_has_traversal(value, plat):
        return f"{field} must not contain path traversal"

    if plat == "windows":
        if not _WINDOWS_ABS_PATH_RE.match(value):
            return f"{field} must be an absolute Windows path"
        return None

    if not value.startswith("/"):
        return f"{field} must be an absolute path"
    return None


def validate_file_transfer_destination_path(path: str, plat: str) -> Optional[str]:
    return validate_absolute_agent_path(
        path,
        plat,
        field="destination_path",
        normalize=False,
    )


def validate_file_transfer_source_path(path: str, plat: str) -> Optional[str]:
    """Validate a download source path (same rules as destination, clearer field)."""
    return validate_absolute_agent_path(
        path,
        plat,
        field="source_path",
        normalize=False,
    )


def resolve_upload_destination_path(
    destination_path: str, filename: str, plat: str
) -> str:
    destination_path = destination_path.strip()
    filename = filename.strip()
    sep = "\\" if plat == "windows" else "/"

    basename = re.split(r"[\\/]+", destination_path.rstrip("\\/"))[-1]
    if basename.lower() == filename.lower():
        return destination_path

    base = destination_path.rstrip("\\/")
    return f"{base}{sep}{filename}"


def derive_archive_download_filename(
    paths: list[str], requested: str | None = None
) -> str:
    name = str(requested or "").strip()
    if name:
        if not name.lower().endswith(".zip"):
            name = f"{name}.zip"
        return name

    if len(paths) == 1:
        base = re.split(r"[\\/]+", paths[0].rstrip("\\/"))[-1] or "download"
        if not base.lower().endswith(".zip"):
            base = f"{base}.zip"
        return base

    return "download.zip"


_UPLOAD_CONTENT_RANGE_RE = re.compile(
    r"^bytes (\d+)-(\d+)/(\d+|\*)$",
    re.IGNORECASE,
)


def parse_upload_content_range(
    header: str, total_size: int
) -> tuple[Optional[tuple[int, int]], Optional[str]]:
    value = (header or "").strip()
    if not value:
        return None, "Content-Range header is required"

    match = _UPLOAD_CONTENT_RANGE_RE.match(value)
    if not match:
        return None, "Invalid Content-Range header"

    try:
        start = int(match.group(1))
        end = int(match.group(2))
        total_raw = match.group(3)
        range_total = total_size if total_raw == "*" else int(total_raw)
    except ValueError:
        return None, "Invalid Content-Range header"

    if range_total != total_size:
        return None, "Content-Range total does not match session total_size"
    if start < 0 or end < start:
        return None, "Invalid Content-Range byte range"
    if end >= total_size:
        return None, "Content-Range exceeds file size"

    return (start, end), None


def canonical_file_browser_path(
    path: str, plat: str
) -> Tuple[Optional[str], Optional[str]]:
    value = normalize_file_browser_path(path, plat)
    err = validate_absolute_agent_path(
        value,
        plat,
        field="path",
        normalize=False,
    )
    if err:
        return None, err
    return value, None


def validate_file_browser_path(path: str, plat: str) -> Optional[str]:
    _value, err = canonical_file_browser_path(path, plat)
    return err


def sanitize_file_browser_name_filter(raw) -> Tuple[Optional[str], Optional[str]]:
    """
    Light sanitization for files_list name substring filter.
    """
    if raw is None:
        return None, None
    value = str(raw).strip()
    if not value:
        return None, None
    if any(ch in value for ch in ("\n", "\r", "\x00")):
        return None, "filter contains invalid characters"
    if len(value) > FILE_BROWSER_MAX_NAME_FILTER_LEN:
        return (
            None,
            f"filter must be at most {FILE_BROWSER_MAX_NAME_FILTER_LEN} characters",
        )
    return value, None


def normalize_file_browser_path(path: str, plat: str) -> str:
    value = (path or "").strip()
    if not value:
        return value

    if plat == "windows":
        value = value.replace("/", "\\")
        if re.match(r"^[A-Za-z]:\\*$", value):
            return value if value.endswith("\\") else f"{value}\\"
        return value

    if value != "/":
        value = value.rstrip("/")
    return value or "/"


def normalize_file_browser_items(raw_items) -> list:
    if not isinstance(raw_items, list):
        return []

    items = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            continue

        item_type = raw.get("type")
        if item_type not in ("file", "folder"):
            continue

        name = (raw.get("name") or "").strip()
        path = (raw.get("path") or "").strip()
        if not name or not path:
            continue

        item = {
            "id": str(raw.get("id") or path),
            "name": name,
            "path": path,
            "type": item_type,
            "size": str(raw.get("size") or "0"),
            "modified": raw.get("modified") or "",
            "created": raw.get("created") or "",
            "accessed": raw.get("accessed") or "",
            "hidden": bool(raw.get("hidden", False)),
            "system": bool(raw.get("system", False)),
            "readonly": bool(raw.get("readonly", False)),
        }
        extension = raw.get("extension")
        if extension:
            item["extension"] = str(extension)
        items.append(item)

    return items


def normalize_file_browser_item(raw) -> Optional[dict]:
    items = normalize_file_browser_items([raw] if raw is not None else [])
    return items[0] if items else None


def normalize_file_browser_properties(raw) -> Optional[dict]:
    """Normalize a files_properties agent response, including folder summary fields."""
    item = normalize_file_browser_item(raw)
    if not item or not isinstance(raw, dict):
        return item

    location = (raw.get("location") or "").strip()
    if location:
        item["location"] = location

    if item["type"] == "folder":
        try:
            item["file_count"] = max(0, int(raw.get("file_count", 0)))
        except (TypeError, ValueError):
            item["file_count"] = 0
        try:
            item["folder_count"] = max(0, int(raw.get("folder_count", 0)))
        except (TypeError, ValueError):
            item["folder_count"] = 0
        item["summary_truncated"] = bool(raw.get("summary_truncated", False))

    return item


def canonical_file_browser_paths(
    paths, plat: str
) -> Tuple[Optional[list], Optional[str]]:
    if not isinstance(paths, list) or not paths:
        return None, "paths is required"
    if len(paths) > FILE_BROWSER_MAX_DELETE_PATHS:
        return None, f"paths must not exceed {FILE_BROWSER_MAX_DELETE_PATHS} items"

    canonical: list[str] = []
    for path in paths:
        if not isinstance(path, str) or not path.strip():
            return None, "paths must be non-empty strings"
        value, path_err = canonical_file_browser_path(path, plat)
        if path_err:
            return None, path_err
        canonical.append(value)
    return canonical, None


def collect_file_transfer_paths(
    paths,
    plat: str,
    *,
    max_paths: int = FILE_BROWSER_MAX_ARCHIVE_PATHS,
    max_exceeded_message: Optional[str] = None,
) -> Tuple[Optional[list], Optional[str]]:
    """
    Validate and collect absolute paths for archive download.
    """
    if not isinstance(paths, list) or not paths:
        return None, "paths must be a non-empty array"

    if len(paths) > max_paths:
        if max_exceeded_message:
            return None, max_exceeded_message
        return None, f"paths must not exceed {max_paths} items"

    validated: list[str] = []
    for raw_path in paths:
        path = str(raw_path or "").strip()
        if not path:
            continue
        path_err = validate_absolute_agent_path(
            path,
            plat,
            field="path",
            normalize=False,
        )
        if path_err:
            return None, path_err
        validated.append(path)

    if not validated:
        return None, "paths must contain at least one valid absolute path"
    return validated, None


def normalize_file_browser_delete_results(raw_results) -> list:
    if not isinstance(raw_results, list):
        return []

    results = []
    for raw in raw_results:
        if not isinstance(raw, dict):
            continue

        path = (raw.get("path") or "").strip()
        if not path:
            continue

        entry = {
            "path": path,
            "success": bool(raw.get("success", False)),
        }
        if raw.get("error"):
            entry["error"] = str(raw["error"])
        results.append(entry)
    return results


WINDOWS_MESH_BANKING_PAUSE_CMD = (
    "Set-Service -Name 'tacticalrmm' -StartupType Automatic -ErrorAction SilentlyContinue; "
    "Start-Service -Name 'tacticalrmm' -ErrorAction SilentlyContinue; "
    "Set-Service -Name 'Mesh Agent' -StartupType Manual -ErrorAction SilentlyContinue; "
    "sc.exe stop 'Mesh Agent' 2>&1 | Out-Null; "
    "Start-Sleep -Milliseconds 1000; "
    "Stop-Process -Name 'MeshAgent*' -Force -ErrorAction SilentlyContinue"
)

_WINDOWS_MESH_WAKE_CMD = (
    "$svc = Get-Service -Name 'Mesh Agent' -ErrorAction SilentlyContinue; "
    "if ($svc) { "
    "  $wmiSvc = Get-CimInstance Win32_Service -Filter \"Name='Mesh Agent'\" -ErrorAction SilentlyContinue; "
    "  if ($wmiSvc -and $wmiSvc.StartMode -eq 'Disabled') { "
    "    $ptype = (Get-CimInstance Win32_OperatingSystem -ErrorAction SilentlyContinue).ProductType; "
    "    $stype = if ($ptype -eq 1) { 'Manual' } else { 'Automatic' }; "
    "    Set-Service -Name 'Mesh Agent' -StartupType $stype -ErrorAction SilentlyContinue "
    "  }; "
    "  if ($svc.Status -ne 'Running') { "
    "    if ($svc.Status -eq 'StopPending' -or $svc.Status -eq 'PausePending' -or $svc.Status -eq 'StartPending') { "
    "      if ($wmiSvc -and $wmiSvc.ProcessId -gt 0) { Stop-Process -Id $wmiSvc.ProcessId -Force -ErrorAction SilentlyContinue }; "
    "      Stop-Process -Name 'MeshAgent*' -Force -ErrorAction SilentlyContinue; "
    "      for ($i = 0; $i -lt 8; $i++) { "
    "        Start-Sleep -Milliseconds 400; "
    "        $svc = Get-Service -Name 'Mesh Agent' -ErrorAction SilentlyContinue; "
    "        if (-not $svc -or $svc.Status -eq 'Stopped') { break } "
    "      } "
    "    }; "
    "    Start-Service -Name 'Mesh Agent' -ErrorAction SilentlyContinue; "
    "    for ($i = 0; $i -lt 6; $i++) { "
    "      $svc = Get-Service -Name 'Mesh Agent' -ErrorAction SilentlyContinue; "
    "      if (-not $svc -or $svc.Status -eq 'Running') { break }; "
    "      Start-Sleep -Milliseconds 400 "
    "    }; "
    "    if ($svc -and $svc.Status -ne 'Running') { "
    "      Stop-Process -Name 'MeshAgent*' -Force -ErrorAction SilentlyContinue; "
    "      Start-Sleep -Milliseconds 900; "
    "      Start-Service -Name 'Mesh Agent' -ErrorAction SilentlyContinue; "
    "      Start-Sleep -Milliseconds 700; "
    "      $svc = Get-Service -Name 'Mesh Agent' -ErrorAction SilentlyContinue "
    "    } "
    "  } "
    "}; "
    "$exe = $null; "
    "$regDir = (Get-ItemProperty 'HKLM:\\SOFTWARE\\TacticalRMM' -ErrorAction SilentlyContinue).MeshDir; "
    "$cands = @(); "
    "if ($regDir) { $cands += (Join-Path $regDir 'MeshAgent.exe') }; "
    "$cands += (Join-Path $env:ProgramFiles 'Mesh Agent\\MeshAgent.exe'); "
    "if (${env:ProgramFiles(x86)}) { $cands += (Join-Path ${env:ProgramFiles(x86)} 'Mesh Agent\\MeshAgent.exe') }; "
    "foreach ($c in $cands) { if ($c -and (Test-Path $c)) { $exe = $c; break } }; "
    "$nid = ''; "
    "if ($exe) { $nid = ((& $exe -nodeid 2>$null) | Out-String).Trim() }; "
    "Write-Output ('SVC:' + $(if ($svc) { $svc.Status } else { 'Missing' }) + '|BIN:' + ([bool]$exe) + '|NODEID:' + $nid)"
)

_LINUX_MESH_WAKE_CMD = (
    "if command -v systemctl >/dev/null 2>&1; then "
    "  systemctl unmask meshagent.service >/dev/null 2>&1 || true; "
    "  systemctl enable meshagent.service >/dev/null 2>&1 || true; "
    "  systemctl start meshagent.service >/dev/null 2>&1 || systemctl restart meshagent.service >/dev/null 2>&1 || true; "
    "  svc=$(systemctl is-active meshagent.service 2>/dev/null || echo inactive); "
    "else svc=unknown; fi; "
    "exe=''; "
    "for p in /usr/local/mesh_services/meshagent/meshagent /opt/tacticalmesh/meshagent; do "
    "  if [ -x \"$p\" ]; then exe=\"$p\"; break; fi; "
    "done; "
    "nid=''; "
    "if [ -n \"$exe\" ]; then nid=$(\"$exe\" -nodeid 2>/dev/null | tr -d '\\r\\n '); fi; "
    "bin_ok=False; [ -n \"$exe\" ] && bin_ok=True; "
    "echo \"SVC:${svc}|BIN:${bin_ok}|NODEID:${nid}\""
)

_DARWIN_MESH_WAKE_CMD = (
    "launchctl kickstart -k system/meshagent >/dev/null 2>&1 || true; "
    "exe=''; "
    "for p in /opt/tacticalmesh/meshagent /usr/local/mesh_services/meshagent/meshagent; do "
    "  if [ -x \"$p\" ]; then exe=\"$p\"; break; fi; "
    "done; "
    "nid=''; "
    "if [ -n \"$exe\" ]; then nid=$(\"$exe\" -nodeid 2>/dev/null | tr -d '\\r\\n '); fi; "
    "bin_ok=False; [ -n \"$exe\" ] && bin_ok=True; "
    "if pgrep -fi meshagent >/dev/null 2>&1; then svc=Running; else svc=Stopped; fi; "
    "echo \"SVC:${svc}|BIN:${bin_ok}|NODEID:${nid}\""
)


def _parse_mesh_wake_output(raw_out: object) -> dict:
    info = {"svc": "Unknown", "bin_exists": None, "node_id": ""}
    if not isinstance(raw_out, str):
        return info
    for line in raw_out.splitlines():
        if "SVC:" in line and "NODEID:" in line:
            for part in line.strip().split("|"):
                if part.startswith("SVC:"):
                    info["svc"] = part[4:].strip() or "Unknown"
                elif part.startswith("BIN:"):
                    val = part[4:].strip().lower()
                    info["bin_exists"] = val in ("true", "1", "yes")
                elif part.startswith("NODEID:"):
                    nid = part[7:].strip()
                    if nid and "not defined" not in nid.lower() and "error" not in nid.lower() and len(nid) >= 32:
                        info["node_id"] = nid
            break
    return info


def _nats_ping_with_retry(agent, timeouts: tuple[float, ...] = (3.0, 4.5)) -> str:
    """Ping agent over NATS with retry to tolerate transient Windows/network jitter."""
    last_res = "timeout"
    for timeout_s in timeouts:
        try:
            res = asyncio.run(agent.nats_cmd({"func": "ping"}, timeout=timeout_s))
        except Exception:
            res = "timeout"
        if res in ("pong", "natsdown"):
            return str(res)
        last_res = str(res or "timeout")
    return last_res


def ensure_agent_mesh_connection(
    agent,
    user,
    core,
    *,
    wake_if_needed: bool = True,
    wait_for_mesh: bool = True,
) -> dict:
    """
    Verify live connectivity between NATS, Mesh Agent on the endpoint, and MeshCentral.
    Wakes paused/stopped Mesh services across Windows/Linux/macOS, repairs stale
    mesh_node_id references, grants user permissions synchronously, and polls MeshCentral
    briefly until connected so Take Control / Remote Background / WebVNC avoid blank
    'Desconectado' sessions.
    """
    from contextlib import suppress
    from django.utils import timezone as djangotime
    from core.mesh_utils import (
        build_mesh_display_name,
        get_mesh_node_live_state,
        poll_mesh_node_connected,
    )
    from core.utils import make_alpha_numeric
    from tacticalrmm.constants import AGENT_STATUS_OFFLINE, AGENT_STATUS_ONLINE, AGENT_STATUS_OVERDUE
    from tacticalrmm.helpers import make_random_password

    db_status = agent.status
    result: dict = {
        "db_status": db_status,
        "live_status": db_status,
        "nats_online": False,
        "nats_broker_down": False,
        "mesh_reachable": False,
        "mesh_node_found": False,
        "mesh_connected": False,
        "mesh_service_status": "Unknown",
        "mesh_binary_exists": None,
        "mesh_node_synced": False,
        "rights_synced": False,
        "needs_recovery": False,
        "diagnostic_reason": "",
    }

    if getattr(settings, "DEMO", False):
        return result

    sync_user = bool(getattr(core, "sync_mesh_with_trmm", False) and user is not None and getattr(user, "mesh_user_id", None))
    mesh_user_id = getattr(user, "mesh_user_id", None) if sync_user else None
    mesh_username = getattr(user, "mesh_username", None) if sync_user else None
    mesh_display_name = ""
    mesh_email = ""
    if sync_user:
        mesh_display_name = build_mesh_display_name(
            first_name=getattr(user, "first_name", ""),
            last_name=getattr(user, "last_name", ""),
            company_name=getattr(core, "mesh_company_name", ""),
        )
        rand1 = make_random_password(len=6)
        rand2 = make_random_password(len=5)
        email_prefix = make_alpha_numeric(getattr(user, "username", "user"))
        mesh_email = f"{email_prefix}.{rand1}@tacticalrmm-do-not-change-{rand2}.local"

    uri = ""
    with suppress(Exception):
        uri = get_mesh_ws_url()

    # 1. Fast query to MeshCentral first (<50ms when local WS is up)
    mesh_state: dict = {}
    if uri and agent.hex_mesh_node_id != "error":
        with suppress(Exception):
            mesh_state = get_mesh_node_live_state(
                uri,
                agent.hex_mesh_node_id,
                mesh_user_id=mesh_user_id,
                mesh_username=mesh_username,
                mesh_display_name=mesh_display_name,
                mesh_email=mesh_email,
                sync_user=sync_user,
            )

    result["mesh_reachable"] = bool(mesh_state.get("mesh_reachable"))
    result["mesh_node_found"] = bool(mesh_state.get("node_found"))
    result["mesh_connected"] = bool(mesh_state.get("mesh_connected"))
    result["rights_synced"] = bool(mesh_state.get("rights_synced"))

    # If MeshCentral already confirms active connection, perform a single quick NATS ping for accurate status
    if result["mesh_connected"] and result["mesh_node_found"]:
        ping_res = _nats_ping_with_retry(agent, timeouts=(2.5,))
        if ping_res == "pong":
            result["nats_online"] = True
            result["live_status"] = AGENT_STATUS_ONLINE
            with suppress(Exception):
                agent.last_seen = djangotime.now()
                agent.save(update_fields=["last_seen"])
        elif ping_res == "natsdown":
            result["nats_broker_down"] = True
        else:
            result["nats_online"] = False
        if result["nats_online"]:
            result["mesh_service_status"] = "Running"
        else:
            result["mesh_service_status"] = "Running (NATS Offline)"
            result["diagnostic_reason"] = (
                "Mesh Agent está conectado ao MeshCentral, porém o agente Tactical não respondeu via NATS."
            )
        return result

    # 2. Mesh is not connected yet (or unknown/node missing). Verify real-time NATS reachability with retry.
    ping_res = _nats_ping_with_retry(agent, timeouts=(3.0, 4.5))

    if ping_res == "natsdown":
        result["nats_broker_down"] = True
        result["nats_online"] = False
        return result

    if ping_res != "pong":
        result["nats_online"] = False
        if db_status == AGENT_STATUS_ONLINE:
            result["live_status"] = AGENT_STATUS_OFFLINE
        elif db_status == AGENT_STATUS_OVERDUE:
            result["live_status"] = AGENT_STATUS_OVERDUE
        result["diagnostic_reason"] = (
            f"O computador {agent.hostname} constava como '{db_status}' no histórico, porém não respondeu "
            "ao ping NATS em tempo real. Pode estar desligado, sem internet/VPN ou com o serviço Tactical Agent parado."
        )
        return result

    # NATS responded pong! Stamp fresh last_seen immediately.
    result["nats_online"] = True
    result["live_status"] = AGENT_STATUS_ONLINE
    agent.last_seen = djangotime.now()
    agent.save(update_fields=["last_seen"])

    # 3. Wake Mesh service cleanly across Windows/Linux/macOS & fetch real endpoint NodeID
    if wake_if_needed:
        if agent.plat == AgentPlat.WINDOWS:
            cmd_text, shell_name = _WINDOWS_MESH_WAKE_CMD, "powershell"
        elif agent.plat == AgentPlat.DARWIN:
            cmd_text, shell_name = _DARWIN_MESH_WAKE_CMD, "bash"
        else:
            cmd_text, shell_name = _LINUX_MESH_WAKE_CMD, "bash"

        wake_raw = None
        with suppress(Exception):
            wake_raw = asyncio.run(
                agent.nats_cmd(
                    {
                        "func": "rawcmd",
                        "timeout": 14,
                        "payload": {"command": cmd_text, "shell": shell_name},
                    },
                    timeout=15,
                )
            )

        parsed = _parse_mesh_wake_output(wake_raw)
        result["mesh_service_status"] = parsed["svc"]
        result["mesh_binary_exists"] = parsed["bin_exists"]

        live_node_id = parsed["node_id"]
        if live_node_id and agent.mesh_node_id != live_node_id:
            agent.mesh_node_id = live_node_id
            agent.save(update_fields=["mesh_node_id"])
            result["mesh_node_synced"] = True

    # Wait briefly for MeshAgent -> MeshCentral WebSocket handshake and sync user rights
    if wait_for_mesh and uri and agent.hex_mesh_node_id != "error":
        with suppress(Exception):
            polled = poll_mesh_node_connected(
                uri,
                agent.hex_mesh_node_id,
                mesh_user_id=mesh_user_id,
                mesh_username=mesh_username,
                mesh_display_name=mesh_display_name,
                mesh_email=mesh_email,
                sync_user=sync_user,
                max_wait_s=8.5,
                poll_interval_s=0.75,
            )
            result["mesh_reachable"] = bool(polled.get("mesh_reachable"))
            result["mesh_node_found"] = bool(polled.get("node_found"))
            result["mesh_connected"] = bool(polled.get("mesh_connected"))
            if polled.get("rights_synced"):
                result["rights_synced"] = True

    if result["mesh_reachable"] and not result["mesh_connected"]:
        svc_low = str(result["mesh_service_status"] or "").lower()
        bin_missing = result["mesh_binary_exists"] is False
        node_missing = not result["mesh_node_found"] or agent.hex_mesh_node_id == "error"
        result["needs_recovery"] = bool(
            bin_missing
            or node_missing
            or svc_low in ("missing", "stopped", "stoppending", "startpending", "paused", "inactive", "failed")
        )

        if bin_missing:
            result["diagnostic_reason"] = (
                "Agente Tactical online via NATS, mas o executável do Mesh Agent não foi encontrado no computador. "
                "Clique em 'Recuperar Conexão' para reinstalar automaticamente."
            )
        elif node_missing:
            result["diagnostic_reason"] = (
                "Agente Tactical online via NATS, mas o NodeID do Mesh Agent está ausente ou não registrado no MeshCentral. "
                "Clique em 'Recuperar Conexão' para reparar e ressincronizar o vínculo."
            )
        else:
            result["diagnostic_reason"] = (
                f"Agente Tactical online via NATS (Serviço Mesh: {result['mesh_service_status']}), "
                "porém o Mesh Agent ainda não concluiu conexão com o MeshCentral. "
                "Verifique bloqueios de antivírus/firewall para MeshAgent ou execute 'Recuperar Conexão'."
            )

    return result
