#!/usr/bin/env bash
# Tactical RMM Enhanced — Multi-Distro Linux Agent Installer
# Supports: Ubuntu (20.04/22.04/24.04/26.04+), Debian (11/12/13+), Fedora (38/39/40/41/42+), RHEL/Rocky/AlmaLinux, Arch, openSUSE
# Works on both Headless Server (SSH) and Desktop GUI (X11 / Wayland) environments.

if [ $EUID -ne 0 ]; then
    echo "ERROR: Must be run as root (use: sudo bash $0)"
    exit 1
fi

HAS_SYSTEMD=$(ps --no-headers -o comm 1 2>/dev/null)
if [ "${HAS_SYSTEMD}" != 'systemd' ]; then
    echo "ERROR: This install script requires systemd."
    exit 1
fi

DEBUG=0
INSECURE=0
NOMESH=0
TARGET_DISTRO="auto"

agentDL='agentDLChange'
meshDL='meshDLChange'

apiURL='apiURLChange'
token='tokenChange'
clientID='clientIDChange'
siteID='siteIDChange'
agentType='agentTypeChange'
targetDistro='distroChange'
proxy=''

agentBinPath='/usr/local/bin'
binName='tacticalagent'
agentBin="${agentBinPath}/${binName}"
agentConf='/etc/tacticalagent'
agentSvcName='tacticalagent.service'
agentSysD="/etc/systemd/system/${agentSvcName}"
agentDir='/opt/tacticalagent'
meshDir='/opt/tacticalmesh'
meshSystemBin="${meshDir}/meshagent"
meshSvcName='meshagent.service'
meshSysD="/lib/systemd/system/${meshSvcName}"
ENHANCED_REPO_URL="https://github.com/WallisonWS/tactical-rmm-enhanced.git"

deb=(ubuntu debian raspbian kali linuxmint pop zorin elementary)
rhe=(fedora rocky almalinux centos rhel amzn ol)

distroID="linux"
distroIDLIKE=""
if [ -f /etc/os-release ]; then
    distroID=$(
        . /etc/os-release
        echo "${ID}" | tr '[A-Z]' '[a-z]'
    )
    distroIDLIKE=$(
        . /etc/os-release
        echo "${ID_LIKE}" | tr '[A-Z]' '[a-z]'
    )
fi

ensure_dependencies() {
    if [[ " ${deb[*]} " =~ " ${distroID} " ]] || [[ "${distroIDLIKE}" == *"debian"* ]] || [[ "${distroIDLIKE}" == *"ubuntu"* ]]; then
        export DEBIAN_FRONTEND=noninteractive
        if ! command -v wget >/dev/null 2>&1 || ! command -v curl >/dev/null 2>&1; then
            apt-get update -qq >/dev/null 2>&1
            apt-get install -y -qq curl wget ca-certificates tar locales >/dev/null 2>&1
        fi
    elif [[ " ${rhe[*]} " =~ " ${distroID} " ]] || [[ "${distroIDLIKE}" == *"fedora"* ]] || [[ "${distroIDLIKE}" == *"rhel"* ]]; then
        if ! command -v wget >/dev/null 2>&1 || ! command -v curl >/dev/null 2>&1; then
            dnf install -y -q curl wget ca-certificates tar policycoreutils glibc-langpack-en >/dev/null 2>&1 || \
            yum install -y -q curl wget ca-certificates tar policycoreutils >/dev/null 2>&1
        fi
    fi
}

set_locale_deb() {
    locale-gen "en_US.UTF-8" >/dev/null 2>&1 || true
    localectl set-locale LANG=en_US.UTF-8 >/dev/null 2>&1 || true
    [ -f /etc/default/locale ] && . /etc/default/locale
}

set_locale_rhel() {
    localedef -c -i en_US -f UTF-8 en_US.UTF-8 >/dev/null 2>&1 || true
    localectl set-locale LANG=en_US.UTF-8 >/dev/null 2>&1 || true
    [ -f /etc/locale.conf ] && . /etc/locale.conf
}

configure_selinux_fedora() {
    if command -v chcon >/dev/null 2>&1; then
        [ -f "${agentBin}" ] && chcon -t bin_t "${agentBin}" >/dev/null 2>&1 || true
        [ -f "${meshSystemBin}" ] && chcon -t bin_t "${meshSystemBin}" >/dev/null 2>&1 || true
    fi
    if command -v restorecon >/dev/null 2>&1; then
        [ -f "${agentBin}" ] && restorecon -F "${agentBin}" >/dev/null 2>&1 || true
        [ -f "${ agentSysD }" ] && restorecon -F "${agentSysD}" >/dev/null 2>&1 || true
    fi
}

RemoveOldAgent() {
    if [ -f "${agentSysD}" ]; then
        systemctl disable ${agentSvcName} >/dev/null 2>&1
        systemctl stop ${agentSvcName} >/dev/null 2>&1
        rm -f "${agentSysD}"
        systemctl daemon-reload
    fi

    if [ -f "${agentConf}" ]; then
        rm -f "${agentConf}"
    fi

    if [ -f "${agentBin}" ]; then
        rm -f "${agentBin}"
    fi

    if [ -d "${agentDir}" ]; then
        rm -rf "${agentDir}"
    fi
}

InstallMesh() {
    if [[ " ${deb[*]} " =~ " ${distroID} " ]] || [[ "${distroIDLIKE}" == *"debian"* ]] || [[ "${distroIDLIKE}" == *"ubuntu"* ]]; then
        set_locale_deb
    else
        set_locale_rhel
    fi

    meshTmpDir='/root/meshtemp'
    mkdir -p $meshTmpDir

    meshTmpBin="${meshTmpDir}/meshagent"
    wget --no-check-certificate -q -O ${meshTmpBin} "${meshDL}" || curl -fsSLk "${meshDL}" -o ${meshTmpBin}
    if [ -s "${meshTmpBin}" ]; then
        chmod +x ${meshTmpBin}
        mkdir -p ${meshDir}
        # Run meshagent installer in isolated headless environment even if a desktop GUI session is active
        env -u DISPLAY -u WAYLAND_DISPLAY LC_ALL=en_US.UTF-8 LANGUAGE=en_US XAUTHORITY=foo DISPLAY=bar ${meshTmpBin} -install --installPath=${meshDir}
        sleep 1
        configure_selinux_fedora
    else
        echo "WARNING: MeshAgent download skipped or unavailable; continuing with Tactical Agent installation."
    fi
    rm -rf ${meshTmpDir}
}

RemoveMesh() {
    if [ -f "${meshSystemBin}" ]; then
        env -u DISPLAY -u WAYLAND_DISPLAY XAUTHORITY=foo DISPLAY=bar ${meshSystemBin} -uninstall >/dev/null 2>&1
        sleep 1
    fi

    for unitPath in "${meshSysD}" "/etc/systemd/system/${meshSvcName}" "/usr/lib/systemd/system/${meshSvcName}"; do
        if [ -f "${unitPath}" ]; then
            systemctl stop ${meshSvcName} >/dev/null 2>&1
            systemctl disable ${meshSvcName} >/dev/null 2>&1
            rm -f "${unitPath}"
        fi
    done

    rm -rf ${meshDir}
    systemctl daemon-reload
}

CompileAgentFallback() {
    echo "Prebuilt binary not reachable at primary URL; compiling Enhanced Linux Agent locally for ${distroID}..."
    if ! command -v go >/dev/null 2>&1; then
        if [[ " ${deb[*]} " =~ " ${distroID} " ]] || [[ "${distroIDLIKE}" == *"debian"* ]] || [[ "${distroIDLIKE}" == *"ubuntu"* ]]; then
            apt-get update -qq && apt-get install -y -qq git golang-go
        elif [[ " ${rhe[*]} " =~ " ${distroID} " ]] || [[ "${distroIDLIKE}" == *"fedora"* ]] || [[ "${distroIDLIKE}" == *"rhel"* ]]; then
            dnf install -y -q git golang || yum install -y -q git golang
        fi
    fi
    buildTmp=$(mktemp -d -t trmm-agent-build-XXXXXX)
    if git clone --depth 1 "${ENHANCED_REPO_URL}" "${buildTmp}" >/dev/null 2>&1; then
        cd "${buildTmp}/rmmagent" && CGO_ENABLED=0 go build -ldflags="-s -w" -o "${agentBin}" .
    fi
    rm -rf "${buildTmp}"
}

Uninstall() {
    RemoveMesh
    RemoveOldAgent
}

if [ $# -ne 0 ] && [[ $1 =~ ^(uninstall|-uninstall|--uninstall)$ ]]; then
    Uninstall
    rm -f "$0"
    exit 0
fi

while [[ "$#" -gt 0 ]]; do
    case $1 in
    -debug | --debug | debug) DEBUG=1 ;;
    -insecure | --insecure | insecure) INSECURE=1 ;;
    -nomesh | --nomesh | nomesh) NOMESH=1 ;;
    -distro | --distro)
        shift
        TARGET_DISTRO="$1"
        ;;
    *)
        echo "ERROR: Unknown parameter: $1"
        exit 1
        ;;
    esac
    shift
done

echo "=================================================================="
echo " Tactical RMM Enhanced — Linux Agent Installer (${distroID})"
echo " Supported: Ubuntu | Debian | Fedora / RHEL / Rocky / AlmaLinux"
echo "=================================================================="

ensure_dependencies
RemoveOldAgent

if [ ! -d "${agentBinPath}" ]; then
    mkdir -p ${agentBinPath}
fi

echo "Downloading Tactical RMM Enhanced Agent..."
if ! wget --no-check-certificate -q -O "${agentBin}" "${agentDL}" && ! curl -fsSLk "${agentDL}" -o "${agentBin}"; then
    CompileAgentFallback
fi

if [ ! -s "${agentBin}" ]; then
    CompileAgentFallback
fi

if [ ! -s "${agentBin}" ]; then
    echo "ERROR: Unable to download or compile tactical agent binary."
    exit 1
fi

chmod +x "${agentBin}"
configure_selinux_fedora

if [[ $NOMESH -eq 1 ]]; then
    echo "Skipping mesh install"
else
    if [ -f "${meshSystemBin}" ]; then
        RemoveMesh
    fi
    echo "Downloading and installing MeshCentral Agent..."
    InstallMesh
fi

INSTALL_CMD="${agentBin} -m install -api ${apiURL} -client-id ${clientID} -site-id ${siteID} -agent-type ${agentType} -auth ${token}"

if [[ $DEBUG -eq 1 ]]; then
    INSTALL_CMD+=" --log debug"
fi

if [[ $INSECURE -eq 1 ]]; then
    INSTALL_CMD+=" --insecure"
fi

if [ "${proxy}" != '' ]; then
    INSTALL_CMD+=" --proxy ${proxy}"
fi

eval "${INSTALL_CMD}"

tacticalsvc="$(
    cat <<EOF
[Unit]
Description=Tactical RMM Enhanced Linux Agent (${distroID})
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=${agentBin} -m svc
User=root
Group=root
Restart=always
RestartSec=5s
LimitNOFILE=1000000
KillMode=process

[Install]
WantedBy=multi-user.target
EOF
)"
echo "${tacticalsvc}" | tee ${agentSysD} >/dev/null
configure_selinux_fedora

systemctl daemon-reload
systemctl enable ${agentSvcName}
systemctl start ${agentSvcName}
echo "Tactical RMM Enhanced Linux Agent successfully installed and started on ${distroID}!"
