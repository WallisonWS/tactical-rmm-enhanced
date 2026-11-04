#!/usr/bin/env bash

SCRIPT_VERSION="200-enhanced"
SCRIPT_URL="https://raw.githubusercontent.com/WallisonWS/tactical-rmm-enhanced/main/install.sh"
ENHANCED_REPO_URL="https://github.com/WallisonWS/tactical-rmm-enhanced.git"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPTS_DIR='/opt/trmm-community-scripts'
PYTHON_VER='3.12.13'
GO_VER='1.23.4'
SETTINGS_FILE='/rmm/api/tacticalrmm/tacticalrmm/settings.py'
local_settings='/rmm/api/tacticalrmm/tacticalrmm/local_settings.py'
SCRIPT_SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Detect OS Family & Package Manager (Debian, Ubuntu, Fedora / RHEL)
if [ ! -f /etc/os-release ]; then
  echo -ne "${RED}ERROR: /etc/os-release not found. Unsupported operating system.${NC}\n"
  exit 1
fi

. /etc/os-release
osname=$(echo "${ID}" | tr '[A-Z]' '[a-z]')
oslike=$(echo "${ID_LIKE}" | tr '[A-Z]' '[a-z]')
fullrelno="${VERSION_ID}"
relno=$(echo "${VERSION_ID}" | cut -d. -f1)
codename="${VERSION_CODENAME}"

PKG_MGR=""
OS_FAMILY=""
WEB_USER="www-data"
WEB_GROUP="www-data"
REDIS_SVC="redis-server.service"

if [[ "$osname" == "debian" ]] || [[ "$oslike" == *"debian"* && "$osname" != "ubuntu" ]]; then
  PKG_MGR="apt"
  OS_FAMILY="debian"
  osname="debian"
elif [[ "$osname" == "ubuntu" ]] || [[ "$oslike" == *"ubuntu"* ]]; then
  PKG_MGR="apt"
  OS_FAMILY="ubuntu"
  osname="ubuntu"
elif [[ "$osname" == "fedora" ]] || [[ "$osname" == "rhel" ]] || [[ "$osname" == "rocky" ]] || [[ "$osname" == "almalinux" ]] || [[ "$oslike" == *"fedora"* ]] || [[ "$oslike" == *"rhel"* ]]; then
  PKG_MGR="dnf"
  OS_FAMILY="fedora"
  WEB_USER="nginx"
  WEB_GROUP="nginx"
  REDIS_SVC="redis.service"
else
  echo -ne "${RED}ERROR: Unsupported distribution (${ID}). Supported OS: Ubuntu (20.04/22.04/24.04/26.04+), Debian (11/12/13+), Fedora (38/39/40/41/42+) & RHEL/Rocky/AlmaLinux.${NC}\n"
  exit 1
fi

printf >&2 "${GREEN}Detected OS: ${PRETTY_NAME} [Family: ${OS_FAMILY} | Package Manager: ${PKG_MGR}]${NC}\n"

if [[ "$PKG_MGR" == "apt" ]]; then
  export DEBIAN_FRONTEND=noninteractive
  sudo apt update
  sudo apt install -y curl wget jq lsb-release ca-certificates openssl gnupg tar git
  if [ -z "$codename" ] && command -v lsb_release >/dev/null 2>&1; then
    codename=$(lsb_release -sc)
  fi
elif [[ "$PKG_MGR" == "dnf" ]]; then
  sudo dnf install -y curl wget jq ca-certificates openssl gnupg2 tar git policycoreutils
  sudo groupadd -f www-data
fi

virt_type=$(systemd-detect-virt)
if [[ "$virt_type" == "lxc" ]] && [[ $* != *--allow-lxc* ]]; then
  echo -ne "${RED}LXC is not supported by default, use a VM or pass --allow-lxc.${NC}\n"
  exit 1
fi

if [ -d /rmm/api/tacticalrmm ] && [[ $* != *--force* ]]; then
  echo -ne "${RED}ERROR: Existing trmm installation found. The install script must be run on a clean server (or pass --force).${NC}\n"
  exit 1
fi

arch=$(uname -m)
if [[ "$arch" != "x86_64" ]] && [[ "$arch" != "aarch64" ]]; then
  echo -ne "${RED}ERROR: Only x86_64 and aarch64 is supported, not ${arch}${NC}\n"
  exit 1
fi

memTotal=$(grep -i memtotal /proc/meminfo | awk '{print $2}')
if [[ $memTotal -lt 3627528 ]] && [[ $* != *--skip-ram-check* ]]; then
  echo -ne "${RED}ERROR: A minimum of 4GB of RAM is required (pass --skip-ram-check for test VMs).${NC}\n"
  exit 1
fi

not_supported() {
  echo -ne "${RED}ERROR: Supported Linux distributions are Debian (11/12/13+), Ubuntu (20.04/22.04/24.04/26.04+), and Fedora (38/39/40/41/42+).${NC}\n"
}

if [[ "$OS_FAMILY" == "debian" ]]; then
  if [[ "$relno" -lt 11 ]]; then
    not_supported
    exit 1
  fi
elif [[ "$OS_FAMILY" == "ubuntu" ]]; then
  if [[ "$relno" -lt 20 ]]; then
    not_supported
    exit 1
  fi
elif [[ "$OS_FAMILY" == "fedora" ]]; then
  if [[ "$osname" == "fedora" && "$relno" -lt 36 ]]; then
    not_supported
    exit 1
  fi
fi

if [[ "$PKG_MGR" == "apt" ]] && dpkg -l | grep -qi turnkey; then
  echo -ne "${RED}Turnkey linux is not supported. Please use the official Debian/Ubuntu/Fedora ISO.${NC}\n"
  exit 1
fi

if ps aux | grep -v grep | grep -qi webmin; then
  echo -ne "${RED}Webmin running, should not be installed. Please use the official Debian/Ubuntu/Fedora ISO.${NC}\n"
  exit 1
fi

if [ $EUID -eq 0 ] && [[ $* != *--allow-root* ]]; then
  echo -ne "${RED}Do NOT run this script as root. Run as a standard sudo user (or pass --allow-root). Exiting.${NC}\n"
  exit 1
fi

if [[ "$LANG" != *".UTF-8"* ]] && [[ "$LANG" != *".utf8"* ]]; then
  printf >&2 "\n${YELLOW}Configuring UTF-8 system locale automatically...${NC}\n"
  if [[ "$PKG_MGR" == "apt" ]]; then
    sudo apt install -y locales
    sudo sed -i 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen 2>/dev/null || true
    sudo locale-gen en_US.UTF-8 || true
    sudo localectl set-locale LANG=en_US.UTF-8 || true
  elif [[ "$PKG_MGR" == "dnf" ]]; then
    sudo dnf install -y glibc-langpack-en glibc-langpack-pt || true
    sudo localectl set-locale LANG=en_US.UTF-8 || true
  fi
  export LANG=en_US.UTF-8
  export LC_ALL=en_US.UTF-8
fi

if [ "$arch" = "x86_64" ]; then
  pgarch='amd64'
else
  pgarch='arm64'
fi

# prevents logging issues with some VPS providers like Vultr if this is a freshly provisioned instance that hasn't been rebooted yet
sudo systemctl restart systemd-journald.service

DJANGO_SEKRET=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 80 | head -n 1)
ADMINURL=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 70 | head -n 1)
MESHPASSWD=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 25 | head -n 1)
pgusername=$(cat /dev/urandom | tr -dc 'a-z' | fold -w 8 | head -n 1)
pgpw=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 20 | head -n 1)
meshusername=$(cat /dev/urandom | tr -dc 'a-z' | fold -w 8 | head -n 1)
MESHPGUSER=$(cat /dev/urandom | tr -dc 'a-z' | fold -w 8 | head -n 1)
MESHPGPWD=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 20 | head -n 1)

cls() {
  printf "\033c"
}

print_green() {
  printf >&2 "${GREEN}%0.s-${NC}" {1..80}
  printf >&2 "\n"
  printf >&2 "${GREEN}${1}${NC}\n"
  printf >&2 "${GREEN}%0.s-${NC}" {1..80}
  printf >&2 "\n"
}

print_error() {
  printf >&2 "${RED}${1}${NC}\n"
}

print_yellow() {
  printf >&2 "${YELLOW}${1}${NC}\n"
}

cls

fetch_key() {
  if ! curl -fsSL "$1" | sudo tee "$2" >/dev/null; then
    print_error "ERROR: failed to download signing key from $1"
    exit 1
  fi
  if ! grep -q "BEGIN PGP PUBLIC KEY BLOCK" "$2"; then
    print_error "ERROR: $1 did not return an armored PGP key"
    exit 1
  fi
  sudo chmod 644 "$2"
}

while [[ $rmmdomain != *[.]*[.]* ]]; do
  echo -ne "${YELLOW}Enter the subdomain for the backend (e.g. api.example.com)${NC}: "
  read rmmdomain
done

while [[ $frontenddomain != *[.]*[.]* ]]; do
  echo -ne "${YELLOW}Enter the subdomain for the frontend (e.g. rmm.example.com)${NC}: "
  read frontenddomain
done

while [[ $meshdomain != *[.]*[.]* ]]; do
  echo -ne "${YELLOW}Enter the subdomain for meshcentral (e.g. mesh.example.com)${NC}: "
  read meshdomain
done

echo -ne "${YELLOW}Enter the root domain (e.g. example.com or example.co.uk)${NC}: "
read rootdomain

while [[ $letsemail != *[@]*[.]* ]]; do
  echo -ne "${YELLOW}Enter a valid email address for django and meshcentral${NC}: "
  read letsemail
done

byocert=false
if [[ $* == *--use-own-cert* ]]; then
  byocert=true
fi

if [[ "$byocert" = true ]]; then
  while true; do

    print_yellow "Please enter the full path to your fullchain.pem file:"
    read -r fullchain_path
    print_yellow "Please enter the full path to your privkey.pem file:"
    read -r privkey_path

    if [[ ! -f "$fullchain_path" || ! -f "$privkey_path" ]]; then
      print_error "One or both files do not exist. Please try again."
      continue
    fi

    openssl x509 -in "$fullchain_path" -noout >/dev/null
    if [[ $? -ne 0 ]]; then
      print_error "ERROR: The provided file is not a valid certificate."
      exit 1
    fi

    break
  done
fi

if grep -q manage_etc_hosts /etc/hosts; then
  sudo sed -i '/manage_etc_hosts: true/d' /etc/cloud/cloud.cfg >/dev/null
  echo -e "\nmanage_etc_hosts: false" | sudo tee --append /etc/cloud/cloud.cfg >/dev/null
fi

CHECK_HOSTS=$(grep 127.0.1.1 /etc/hosts | grep "$rmmdomain" | grep "$meshdomain" | grep "$frontenddomain")
HAS_11=$(grep 127.0.1.1 /etc/hosts)

if ! [[ $CHECK_HOSTS ]]; then
  print_green 'Adding subdomains to hosts file'
  if [[ $HAS_11 ]]; then
    sudo sed -i "/127.0.1.1/s/$/ ${rmmdomain} ${frontenddomain} ${meshdomain}/" /etc/hosts
  else
    echo "127.0.1.1 ${rmmdomain} ${frontenddomain} ${meshdomain}" | sudo tee --append /etc/hosts >/dev/null
  fi
fi

BEHIND_NAT=false
IPV4=$(ip -4 addr | sed -ne 's|^.* inet \([^/]*\)/.* scope global.*$|\1|p' | head -1)
if echo "$IPV4" | grep -qE '^(10\.|172\.1[6789]\.|172\.2[0-9]\.|172\.3[01]\.|192\.168)'; then
  BEHIND_NAT=true
fi

insecure=false
if [[ $* == *--insecure* ]]; then
  insecure=true
fi

if [[ "$insecure" = true ]]; then
  print_green 'Generating self-signed cert'
  certdir='/etc/ssl/tactical'
  sudo mkdir -p $certdir
  sudo chown ${USER}:${USER} $certdir
  sudo chmod 770 $certdir
  CERT_PRIV_KEY=${certdir}/key.pem
  CERT_PUB_KEY=${certdir}/cert.pem
  openssl req -x509 -newkey rsa:4096 -sha256 -days 3650 \
    -nodes -keyout ${CERT_PRIV_KEY} -out ${CERT_PUB_KEY} -subj "/CN=${rootdomain}" \
    -addext "subjectAltName=DNS:${rootdomain},DNS:*.${rootdomain}"

elif [[ "$byocert" = true ]]; then
  CERT_PRIV_KEY=$privkey_path
  CERT_PUB_KEY=$fullchain_path
  sudo chown ${USER}:${USER} $CERT_PRIV_KEY $CERT_PUB_KEY
else
  if [[ "$PKG_MGR" == "apt" ]]; then
    sudo apt install -y certbot
  elif [[ "$PKG_MGR" == "dnf" ]]; then
    sudo dnf install -y certbot
  fi
  print_green 'Getting wildcard cert'

  sudo certbot certonly --manual -d *.${rootdomain} --agree-tos --preferred-challenges dns -m ${letsemail} --no-eff-email
  while [[ $? -ne 0 ]]; do
    sudo certbot certonly --manual -d *.${rootdomain} --agree-tos --preferred-challenges dns -m ${letsemail} --no-eff-email
  done
  CERT_PRIV_KEY=/etc/letsencrypt/live/${rootdomain}/privkey.pem
  CERT_PUB_KEY=/etc/letsencrypt/live/${rootdomain}/fullchain.pem
  sudo chown ${USER}:${USER} -R /etc/letsencrypt
fi

print_green "Installing Nginx (${OS_FAMILY})"

if [[ "$PKG_MGR" == "apt" ]]; then
  sudo mkdir -p /etc/apt/keyrings
  fetch_key https://nginx.org/keys/nginx_signing.key /etc/apt/keyrings/nginx.asc

  nginxrepo="$(
    cat <<EOF
Types: deb
URIs: https://nginx.org/packages/${osname}
Suites: ${codename}
Components: nginx
Signed-By: /etc/apt/keyrings/nginx.asc
EOF
  )"
  echo "${nginxrepo}" | sudo tee /etc/apt/sources.list.d/nginx.sources >/dev/null
  printf 'Package: *\nPin: origin nginx.org\nPin: release o=nginx\nPin-Priority: 900\n' | sudo tee /etc/apt/preferences.d/99nginx >/dev/null

  if ! sudo apt update || ! sudo apt install -y nginx; then
    print_yellow "Official nginx.org repo not available for ${codename}, falling back to distribution nginx package..."
    sudo rm -f /etc/apt/sources.list.d/nginx.sources /etc/apt/preferences.d/99nginx
    sudo apt update
    sudo apt install -y nginx
  fi
  NGINX_MODULES_INCLUDE="include /etc/nginx/modules-enabled/*.conf;"
elif [[ "$PKG_MGR" == "dnf" ]]; then
  sudo dnf install -y nginx
  sudo usermod -aG www-data nginx 2>/dev/null || true
  sudo usermod -aG nginx ${USER} 2>/dev/null || true
  NGINX_MODULES_INCLUDE="include /usr/share/nginx/modules/*.conf;"
fi

sudo systemctl stop nginx

nginxdefaultconf='/etc/nginx/nginx.conf'

nginxconf="$(
  cat <<EOF
worker_rlimit_nofile 1000000;
user ${WEB_USER};
worker_processes auto;
pid /run/nginx.pid;
${NGINX_MODULES_INCLUDE}

events {
        worker_connections 4096;
}

http {
        sendfile on;
        tcp_nopush on;
        types_hash_max_size 2048;
        server_names_hash_bucket_size 256;
        include /etc/nginx/mime.types;
        default_type application/octet-stream;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_prefer_server_ciphers on;
        access_log /var/log/nginx/access.log;
        error_log /var/log/nginx/error.log;
        gzip on;
        include /etc/nginx/conf.d/*.conf;
        include /etc/nginx/sites-enabled/*;
}
EOF
)"
echo "${nginxconf}" | sudo tee $nginxdefaultconf >/dev/null

for i in sites-available sites-enabled; do
  sudo mkdir -p /etc/nginx/$i
done

print_green 'Installing NodeJS'

NODE_MAJOR=24
if [[ "$PKG_MGR" == "apt" ]]; then
  fetch_key https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key /etc/apt/keyrings/nodesource.asc

  noderepo="$(
    cat <<EOF
Types: deb
URIs: https://deb.nodesource.com/node_${NODE_MAJOR}.x
Suites: nodistro
Components: main
Signed-By: /etc/apt/keyrings/nodesource.asc
EOF
  )"
  echo "${noderepo}" | sudo tee /etc/apt/sources.list.d/nodesource.sources >/dev/null

  sudo apt update
  sudo apt install -y gcc g++ make
  sudo apt install -y nodejs
  sudo npm install -g npm
elif [[ "$PKG_MGR" == "dnf" ]]; then
  sudo dnf install -y gcc gcc-c++ make
  sudo dnf install -y https://rpm.nodesource.com/pub_${NODE_MAJOR}.x/nodistro/repo/nodesource-release-nodistro-1.noarch.rpm || true
  sudo dnf install -y nodejs npm
  sudo npm install -g npm || true
fi

print_green "Installing Python ${PYTHON_VER}"

if [[ "$PKG_MGR" == "apt" ]]; then
  sudo apt install -y build-essential zlib1g-dev libncurses-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev libsqlite3-dev libbz2-dev
elif [[ "$PKG_MGR" == "dnf" ]]; then
  sudo dnf install -y gcc gcc-c++ make zlib-devel ncurses-devel gdbm-devel nss-devel openssl-devel readline-devel libffi-devel sqlite-devel bzip2-devel xz-devel libpq-devel python3-devel
fi

if command -v python3.12 >/dev/null 2>&1; then
  print_green "Found system Python 3.12 ($(python3.12 --version))"
  if [[ "$PKG_MGR" == "apt" ]]; then
    sudo apt install -y python3.12-venv python3.12-dev || true
  elif [[ "$PKG_MGR" == "dnf" ]]; then
    sudo dnf install -y python3.12 python3.12-devel || true
  fi
else
  numprocs=$(nproc)
  cd ~
  wget https://www.python.org/ftp/python/${PYTHON_VER}/Python-${PYTHON_VER}.tgz
  tar -xf Python-${PYTHON_VER}.tgz
  cd Python-${PYTHON_VER}
  ./configure --enable-optimizations
  make -j $numprocs
  sudo make altinstall
  cd ~
  sudo rm -rf Python-${PYTHON_VER} Python-${PYTHON_VER}.tgz
fi

print_green 'Installing redis and git'
if [[ "$PKG_MGR" == "apt" ]]; then
  sudo apt install -y redis git
  sudo systemctl enable --now redis-server.service || sudo systemctl enable --now redis.service || true
elif [[ "$PKG_MGR" == "dnf" ]]; then
  sudo dnf install -y redis git
  sudo systemctl enable --now redis.service
fi

print_green "Installing PostgreSQL (${OS_FAMILY})"

if [[ "$PKG_MGR" == "apt" ]]; then
  fetch_key https://www.postgresql.org/media/keys/ACCC4CF8.asc /etc/apt/keyrings/postgresql.asc

  pgrepo="$(
    cat <<EOF
Types: deb
URIs: https://apt.postgresql.org/pub/repos/apt
Suites: ${codename}-pgdg
Components: main
Architectures: ${pgarch}
Signed-By: /etc/apt/keyrings/postgresql.asc
EOF
  )"
  echo "${pgrepo}" | sudo tee /etc/apt/sources.list.d/pgdg.sources >/dev/null

  sudo apt update
  if ! sudo apt install -y postgresql-18; then
    print_yellow "postgresql-18 not found in PGDG for ${codename}, installing latest available PostgreSQL..."
    sudo apt install -y postgresql-17 || sudo apt install -y postgresql-16 || sudo apt install -y postgresql
  fi
  sleep 2
  sudo systemctl enable --now postgresql
elif [[ "$PKG_MGR" == "dnf" ]]; then
  sudo dnf install -y postgresql-server postgresql-contrib
  if [ ! -f /var/lib/pgsql/data/PG_VERSION ]; then
    sudo postgresql-setup --initdb
  fi
  # Ensure local TCP password authentication (md5/scram-sha-256) is allowed on Fedora/RHEL
  if [ -f /var/lib/pgsql/data/pg_hba.conf ]; then
    sudo sed -i 's/^\(host\s\+all\s\+all\s\+127\.0\.0\.1\/32\s\+\)ident/\1scram-sha-256/g' /var/lib/pgsql/data/pg_hba.conf
    sudo sed -i 's/^\(host\s\+all\s\+all\s\+::1\/128\s\+\)ident/\1scram-sha-256/g' /var/lib/pgsql/data/pg_hba.conf
  fi
  sudo systemctl enable --now postgresql
fi

until pg_isready >/dev/null 2>&1; do
  echo -ne "${GREEN}Waiting for PostgreSQL to be ready${NC}\n"
  sleep 3
done

print_green 'Creating database for trmm'

sudo -iu postgres psql -c "CREATE DATABASE tacticalrmm"
sudo -iu postgres psql -c "CREATE USER ${pgusername} WITH PASSWORD '${pgpw}'"
sudo -iu postgres psql -c "ALTER ROLE ${pgusername} SET client_encoding TO 'utf8'"
sudo -iu postgres psql -c "ALTER ROLE ${pgusername} SET default_transaction_isolation TO 'read committed'"
sudo -iu postgres psql -c "ALTER ROLE ${pgusername} SET timezone TO 'UTC'"
sudo -iu postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE tacticalrmm TO ${pgusername}"
sudo -iu postgres psql -c "ALTER DATABASE tacticalrmm OWNER TO ${pgusername}"
sudo -iu postgres psql -c "GRANT USAGE, CREATE ON SCHEMA PUBLIC TO ${pgusername}"

print_green 'Creating database for meshcentral'

sudo -iu postgres psql -c "CREATE DATABASE meshcentral"
sudo -iu postgres psql -c "CREATE USER ${MESHPGUSER} WITH PASSWORD '${MESHPGPWD}'"
sudo -iu postgres psql -c "ALTER ROLE ${MESHPGUSER} SET client_encoding TO 'utf8'"
sudo -iu postgres psql -c "ALTER ROLE ${MESHPGUSER} SET default_transaction_isolation TO 'read committed'"
sudo -iu postgres psql -c "ALTER ROLE ${MESHPGUSER} SET timezone TO 'UTC'"
sudo -iu postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE meshcentral TO ${MESHPGUSER}"
sudo -iu postgres psql -c "ALTER DATABASE meshcentral OWNER TO ${MESHPGUSER}"
sudo -iu postgres psql -c "GRANT USAGE, CREATE ON SCHEMA PUBLIC TO ${MESHPGUSER}"

print_green 'Cloning Tactical RMM Enhanced repository'

sudo mkdir -p /rmm
sudo chown ${USER}:${USER} /rmm
sudo mkdir -p /var/log/celery
sudo chown ${USER}:${USER} /var/log/celery

if [ -d "${SCRIPT_SOURCE_DIR}/api/tacticalrmm" ] && [ -d "${SCRIPT_SOURCE_DIR}/web" ]; then
  print_green "Copying Tactical RMM Enhanced from local checkout (${SCRIPT_SOURCE_DIR})..."
  cp -a "${SCRIPT_SOURCE_DIR}/." /rmm/
else
  git clone "${ENHANCED_REPO_URL}" /rmm/
fi
cd /rmm
git config user.email "admin@example.com"
git config user.name "Bob"

sudo mkdir -p ${SCRIPTS_DIR}
sudo chown ${USER}:${USER} ${SCRIPTS_DIR}
git clone https://github.com/amidaware/community-scripts.git ${SCRIPTS_DIR}/
cd ${SCRIPTS_DIR}
git config user.email "admin@example.com"
git config user.name "Bob"
git checkout main

print_green 'Downloading NATS'

if [ "$arch" = "x86_64" ]; then
  natsarch='amd64'
else
  natsarch='arm64'
fi

NATS_SERVER_VER=$(grep "^NATS_SERVER_VER" "$SETTINGS_FILE" | awk -F'[= "]' '{print $5}')
nats_tmp=$(mktemp -d -t nats-XXXXXXXXXX)
wget https://github.com/nats-io/nats-server/releases/download/v${NATS_SERVER_VER}/nats-server-v${NATS_SERVER_VER}-linux-${natsarch}.tar.gz -P ${nats_tmp}
tar -xzf ${nats_tmp}/nats-server-v${NATS_SERVER_VER}-linux-${natsarch}.tar.gz -C ${nats_tmp}
sudo mv ${nats_tmp}/nats-server-v${NATS_SERVER_VER}-linux-${natsarch}/nats-server /usr/local/bin/
sudo chmod +x /usr/local/bin/nats-server
sudo chown ${USER}:${USER} /usr/local/bin/nats-server
rm -rf ${nats_tmp}

print_green 'Installing MeshCentral'

MESH_VER=$(grep "^MESH_VER" "$SETTINGS_FILE" | awk -F'[= "]' '{print $5}')

sudo mkdir -p /meshcentral/meshcentral-data
sudo chown ${USER}:${USER} -R /meshcentral
cd /meshcentral
sudo chown ${USER}:${USER} -R /meshcentral

mesh_pkg="$(
  cat <<EOF
{
  "dependencies": {
    "archiver": "7.0.1",
    "meshcentral": "${MESH_VER}",
    "otplib": "13.4.1",
    "pg": "8.16.3"
  }
}
EOF
)"
echo "${mesh_pkg}" >/meshcentral/package.json

meshcfg="$(
  cat <<EOF
{
  "settings": {
    "cert": "${meshdomain}",
    "WANonly": true,
    "minify": 1,
    "port": 4430,
    "aliasPort": 443,
    "redirPort": 800,
    "allowLoginToken": true,
    "allowFraming": true,
    "agentPing": 35,
    "allowHighQualityDesktop": true,
    "tlsOffload": "127.0.0.1",
    "agentCoreDump": false,
    "compression": false,
    "wsCompression": false,
    "agentWsCompression": false,
    "maxInvalidLogin": { "time": 5, "count": 5, "coolofftime": 30 },
	"autoBackup": false,
    "postgres": {
      "user": "${MESHPGUSER}",
      "password": "${MESHPGPWD}",
      "port": "5432",
      "host": "localhost"
    }
  },
  "domains": {
    "": {
      "title": "Tactical RMM",
      "title2": "Tactical RMM",
      "newAccounts": false,
      "certUrl": "https://${meshdomain}:443/",
      "geoLocation": true,
      "cookieIpCheck": false,
      "mstsc": true
    }
  }
}
EOF
)"
echo "${meshcfg}" >/meshcentral/meshcentral-data/config.json

npm install

localvars="$(
  cat <<EOF
SECRET_KEY = "${DJANGO_SEKRET}"

DEBUG = False

ALLOWED_HOSTS = ['${rmmdomain}']

ADMIN_URL = "${ADMINURL}/"

CORS_ORIGIN_WHITELIST = [
    "https://${frontenddomain}"
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'tacticalrmm',
        'USER': '${pgusername}',
        'PASSWORD': '${pgpw}',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

MESH_USERNAME = "${meshusername}"
MESH_SITE = "https://${meshdomain}"
ADMIN_ENABLED = True
EOF
)"
echo "${localvars}" >$local_settings

if [[ "$insecure" = true ]]; then
  echo "TRMM_INSECURE = True" | tee --append $local_settings >/dev/null
fi

if [[ "$byocert" = true ]] || [[ "$insecure" = true ]]; then
  owncerts="$(
    cat <<EOF
CERT_FILE = "${CERT_PUB_KEY}"
KEY_FILE = "${CERT_PRIV_KEY}"
EOF
  )"
  echo "${owncerts}" | tee --append $local_settings >/dev/null
fi

if [ "$arch" = "x86_64" ]; then
  natsapi='nats-api'
else
  natsapi='nats-api-arm64'
fi

sudo cp /rmm/natsapi/bin/${natsapi} /usr/local/bin/nats-api
sudo chown ${USER}:${USER} /usr/local/bin/nats-api
sudo chmod +x /usr/local/bin/nats-api

print_green 'Installing the backend'

# for weasyprint
if [[ "$PKG_MGR" == "apt" ]]; then
  if [[ "$osname" == "debian" ]]; then
    sudo apt install -y libpango-1.0-0 libpangoft2-1.0-0 || true
  elif [[ "$osname" == "ubuntu" ]]; then
    sudo apt install -y libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0 || true
  fi
  if ! dpkg -l | grep -q "^ii  libharfbuzz-subset0" && apt-cache show libharfbuzz-subset0 >/dev/null 2>&1; then
    sudo apt install -y libharfbuzz-subset0
  fi
elif [[ "$PKG_MGR" == "dnf" ]]; then
  sudo dnf install -y pango harfbuzz cairo gobject-introspection gd || true
fi

SETUPTOOLS_VER=$(grep "^SETUPTOOLS_VER" "$SETTINGS_FILE" | awk -F'[= "]' '{print $5}')
WHEEL_VER=$(grep "^WHEEL_VER" "$SETTINGS_FILE" | awk -F'[= "]' '{print $5}')

sudo mkdir -p /opt/tactical/reporting/assets
sudo mkdir -p /opt/tactical/reporting/schemas
sudo chown -R ${USER}:${USER} /opt/tactical

cd /rmm/api
python3.12 -m venv env
source /rmm/api/env/bin/activate
cd /rmm/api/tacticalrmm
pip install --no-cache-dir pip==25.1
pip install --no-cache-dir setuptools==${SETUPTOOLS_VER} wheel==${WHEEL_VER}
pip install --no-cache-dir -r /rmm/api/tacticalrmm/requirements.txt
python manage.py migrate
python manage.py generate_json_schemas
python manage.py collectstatic --no-input
python manage.py create_natsapi_conf
python manage.py create_uwsgi_conf
python manage.py load_chocos
python manage.py load_community_scripts
WEB_VERSION=$(python manage.py get_config webversion)
WEBTAR_URL=$(python manage.py get_webtar_url)
printf >&2 "${YELLOW}%0.s*${NC}" {1..80}
printf >&2 "\n"
printf >&2 "${YELLOW}Please create your login for the RMM website${NC}\n"
printf >&2 "${YELLOW}%0.s*${NC}" {1..80}
printf >&2 "\n"
echo -ne "Username: "
read djangousername
python manage.py createsuperuser --username ${djangousername} --email ${letsemail}
python manage.py create_installer_user
RANDBASE=$(python manage.py generate_totp)
cls
python manage.py generate_barcode ${RANDBASE} ${djangousername} ${frontenddomain}
deactivate
read -n 1 -s -r -p "Press any key to continue..."

rmmservice="$(
  cat <<EOF
[Unit]
Description=tacticalrmm uwsgi daemon
After=network.target postgresql.service

[Service]
User=${USER}
Group=${WEB_GROUP}
WorkingDirectory=/rmm/api/tacticalrmm
Environment="PATH=/rmm/api/env/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/rmm/api/env/bin/uwsgi --ini app.ini
Restart=always
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF
)"
echo "${rmmservice}" | sudo tee /etc/systemd/system/rmm.service >/dev/null

uviservice="$(
  cat <<EOF
[Unit]
Description=uvicorn daemon v1
After=network.target

[Service]
User=${USER}
Group=${WEB_GROUP}
WorkingDirectory=/rmm/api/tacticalrmm
Environment="PATH=/rmm/api/env/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/rmm/api/env/bin/uvicorn --uds /rmm/daphne.sock --forwarded-allow-ips='*' tacticalrmm.asgi:application
ExecStartPre=rm -f /rmm/daphne.sock
ExecStartPre=rm -f /rmm/daphne.sock.lock
Restart=always
RestartSec=3s

[Install]
WantedBy=multi-user.target
EOF
)"
echo "${uviservice}" | sudo tee /etc/systemd/system/daphne.service >/dev/null

natsservice="$(
  cat <<EOF
[Unit]
Description=NATS Server
After=network.target

[Service]
PrivateTmp=true
Type=simple
ExecStart=/usr/local/bin/nats-server -c /rmm/api/tacticalrmm/nats-rmm.conf
ExecReload=/usr/bin/kill -s HUP \$MAINPID
ExecStop=/usr/bin/kill -s SIGINT \$MAINPID
User=${USER}
Group=${USER}
Restart=always
RestartSec=5s
LimitNOFILE=1000000

[Install]
WantedBy=multi-user.target
EOF
)"
echo "${natsservice}" | sudo tee /etc/systemd/system/nats.service >/dev/null

natsapi="$(
  cat <<EOF
[Unit]
Description=TacticalRMM Nats Api v1
After=nats.service

[Service]
Type=simple
ExecStart=/usr/local/bin/nats-api
User=${USER}
Group=${USER}
Restart=always
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF
)"
echo "${natsapi}" | sudo tee /etc/systemd/system/nats-api.service >/dev/null

nginxrmm="$(
  cat <<EOF
server_tokens off;

upstream tacticalrmm {
    server unix:////rmm/api/tacticalrmm/tacticalrmm.sock;
}

map \$http_user_agent \$ignore_ua {
    "~python-requests.*" 0;
    "~go-resty.*" 0;
    default 1;
}

server {
    listen 80;
    listen [::]:80;
    server_name ${rmmdomain};
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl reuseport;
    listen [::]:443 ssl;
    server_name ${rmmdomain};
    client_max_body_size 300M;
    access_log /rmm/api/tacticalrmm/tacticalrmm/private/log/access.log combined if=\$ignore_ua;
    error_log /rmm/api/tacticalrmm/tacticalrmm/private/log/error.log;
    ssl_certificate ${CERT_PUB_KEY};
    ssl_certificate_key ${CERT_PRIV_KEY};
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers EECDH+AESGCM:EDH+AESGCM;
    ssl_ecdh_curve secp384r1;
    add_header X-Content-Type-Options nosniff;
    
    location /static/ {
        root /rmm/api/tacticalrmm;
        add_header "Access-Control-Allow-Origin" "https://${frontenddomain}";
    }

    location /private/ {
        internal;
        add_header "Access-Control-Allow-Origin" "https://${frontenddomain}";
        alias /rmm/api/tacticalrmm/tacticalrmm/private/;
    }

    location /assets/ {
        internal;
        add_header "Access-Control-Allow-Origin" "https://${frontenddomain}";
        alias /opt/tactical/reporting/assets/;
    }

    location ~ ^/ws/ {
        proxy_pass http://unix:/rmm/daphne.sock;

        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";

        proxy_redirect     off;
        proxy_set_header   Host \$host;
        proxy_set_header   X-Real-IP \$remote_addr;
        proxy_set_header   X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Host \$server_name;
    }

    location ~ ^/natsws {
        proxy_pass http://127.0.0.1:9235;
        proxy_http_version 1.1;

        proxy_set_header Host \$host;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header X-Forwarded-Host \$host:\$server_port;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location / {
        uwsgi_pass  tacticalrmm;
        include     /etc/nginx/uwsgi_params;
        uwsgi_read_timeout 300s;
        uwsgi_ignore_client_abort on;
    }
}
EOF
)"
echo "${nginxrmm}" | sudo tee /etc/nginx/sites-available/rmm.conf >/dev/null

nginxmesh="$(
  cat <<EOF
server {
  listen 80;
  listen [::]:80;
  server_name ${meshdomain};
  return 301 https://\$server_name\$request_uri;
}

server {

    listen 443 ssl;
    listen [::]:443 ssl;
    proxy_send_timeout 330s;
    proxy_read_timeout 330s;
    server_name ${meshdomain};
    ssl_certificate ${CERT_PUB_KEY};
    ssl_certificate_key ${CERT_PRIV_KEY};

    ssl_session_cache shared:WEBSSL:10m;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers EECDH+AESGCM:EDH+AESGCM;
    ssl_ecdh_curve secp384r1;
    add_header X-Content-Type-Options nosniff;

    location / {
        proxy_pass http://127.0.0.1:4430/;
        proxy_http_version 1.1;

        proxy_set_header Host \$host;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header X-Forwarded-Host \$host:\$server_port;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
)"
echo "${nginxmesh}" | sudo tee /etc/nginx/sites-available/meshcentral.conf >/dev/null

sudo ln -sf /etc/nginx/sites-available/rmm.conf /etc/nginx/sites-enabled/rmm.conf
sudo ln -sf /etc/nginx/sites-available/meshcentral.conf /etc/nginx/sites-enabled/meshcentral.conf

sudo mkdir -p /etc/conf.d

celeryservice="$(
  cat <<EOF
[Unit]
Description=Celery Service V3
After=network.target ${REDIS_SVC} postgresql.service
BindsTo=${REDIS_SVC}

[Service]
Type=forking
User=${USER}
Group=${USER}
EnvironmentFile=/etc/conf.d/celery.conf
WorkingDirectory=/rmm/api/tacticalrmm
ExecStart=/bin/sh -c '\${CELERY_BIN} -A \$CELERY_APP multi start \$CELERYD_NODES --pidfile=\${CELERYD_PID_FILE} --logfile=\${CELERYD_LOG_FILE} --loglevel="\${CELERYD_LOG_LEVEL}" \$CELERYD_OPTS'
ExecStop=/bin/sh -c '\${CELERY_BIN} multi stopwait \$CELERYD_NODES --pidfile=\${CELERYD_PID_FILE} --loglevel="\${CELERYD_LOG_LEVEL}"'
ExecReload=/bin/sh -c '\${CELERY_BIN} -A \$CELERY_APP multi restart \$CELERYD_NODES --pidfile=\${CELERYD_PID_FILE} --logfile=\${CELERYD_LOG_FILE} --loglevel="\${CELERYD_LOG_LEVEL}" \$CELERYD_OPTS'
Restart=always
RestartSec=15s
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target ${REDIS_SVC}
EOF
)"
echo "${celeryservice}" | sudo tee /etc/systemd/system/celery.service >/dev/null

celeryconf="$(
  cat <<EOF
CELERYD_NODES="w1"

CELERY_BIN="/rmm/api/env/bin/celery"

CELERY_APP="tacticalrmm"

CELERYD_MULTI="multi"

CELERYD_OPTS="--time-limit=14400 --soft-time-limit=14100 --autoscale=10,4"

CELERYD_PID_FILE="/rmm/api/tacticalrmm/%n.pid"
CELERYD_LOG_FILE="/var/log/celery/%n%I.log"
CELERYD_LOG_LEVEL="ERROR"

CELERYBEAT_PID_FILE="/rmm/api/tacticalrmm/beat.pid"
CELERYBEAT_LOG_FILE="/var/log/celery/beat.log"
EOF
)"
echo "${celeryconf}" | sudo tee /etc/conf.d/celery.conf >/dev/null

celerybeatservice="$(
  cat <<EOF
[Unit]
Description=Celery Beat Service V5
After=network.target ${REDIS_SVC} postgresql.service
BindsTo=${REDIS_SVC}

[Service]
Type=simple
User=${USER}
Group=${USER}
EnvironmentFile=/etc/conf.d/celery.conf
WorkingDirectory=/rmm/api/tacticalrmm
ExecStart=/bin/sh -c '\${CELERY_BIN} -A \${CELERY_APP} beat --pidfile=\${CELERYBEAT_PID_FILE} --logfile=\${CELERYBEAT_LOG_FILE} --loglevel=\${CELERYD_LOG_LEVEL}'
ExecStartPre=rm -f /rmm/api/tacticalrmm/beat.pid
ExecStartPre=rm -f /rmm/api/tacticalrmm/celerybeat-schedule
Restart=always
RestartSec=10s
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target ${REDIS_SVC}
EOF
)"
echo "${celerybeatservice}" | sudo tee /etc/systemd/system/celerybeat.service >/dev/null

sudo chown ${USER}:${USER} -R /etc/conf.d/

meshservice="$(
  cat <<EOF
[Unit]
Description=MeshCentral Server
After=network.target postgresql.service nginx.service
[Service]
Type=simple
LimitNOFILE=1000000
ExecStart=/usr/bin/node node_modules/meshcentral
Environment=NODE_ENV=production
WorkingDirectory=/meshcentral
User=${USER}
Group=${USER}
Restart=always
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF
)"
echo "${meshservice}" | sudo tee /etc/systemd/system/meshcentral.service >/dev/null

sudo systemctl daemon-reload

if [ -d ~/.npm ]; then
  sudo chown -R $USER:$USER ~/.npm
fi

if [ -d ~/.config ]; then
  sudo chown -R $USER:$USER ~/.config
fi

print_green 'Building & Installing Tactical RMM Enhanced Frontend (PT-BR / EN-US / ES-ES)'

sudo mkdir -p /var/www/rmm/dist
if [ -d /rmm/web ] && [ -f /rmm/web/package.json ]; then
  cd /rmm/web
  npm install --legacy-peer-deps || npm install
  npm run build
  sudo cp -a /rmm/web/dist/. /var/www/rmm/dist/
else
  webtar="trmm-web-v${WEB_VERSION}.tar.gz"
  wget -q ${WEBTAR_URL} -O /tmp/${webtar}
  sudo tar -xzf /tmp/${webtar} -C /var/www/rmm
  rm -f /tmp/${webtar}
fi
echo "window._env_ = {PROD_URL: \"https://${rmmdomain}\"}" | sudo tee /var/www/rmm/dist/env-config.js >/dev/null

# Compile Enhanced Go Agents (Windows & Linux) so endpoints can download directly from this RMM server
if [ -d /rmm/rmmagent ]; then
  print_green 'Compiling Enhanced Go Agents for Windows (amd64/386) and Linux (amd64/arm64)'
  if ! command -v go >/dev/null 2>&1; then
    go_tmp=$(mktemp -d -t go-XXXXXXXXXX)
    wget -q "https://go.dev/dl/go${GO_VER}.linux-${natsarch}.tar.gz" -P "${go_tmp}" && \
      sudo rm -rf /usr/local/go && \
      sudo tar -C /usr/local -xzf "${go_tmp}/go${GO_VER}.linux-${natsarch}.tar.gz"
    rm -rf "${go_tmp}"
    export PATH="/usr/local/go/bin:${PATH}"
  fi
  if command -v go >/dev/null 2>&1; then
    sudo mkdir -p /var/www/rmm/dist/agents
    sudo chown -R ${USER}:${USER} /var/www/rmm/dist/agents
    cd /rmm/rmmagent
    AGENT_VER=$(grep "^LATEST_AGENT_VER" "$SETTINGS_FILE" | awk -F'[= "]' '{print $5}')
    CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags="-s -w" -o "/var/www/rmm/dist/agents/tacticalagent-v${AGENT_VER}-linux-amd64" . || true
    CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build -ldflags="-s -w" -o "/var/www/rmm/dist/agents/tacticalagent-v${AGENT_VER}-linux-arm64" . || true
    CGO_ENABLED=0 GOOS=windows GOARCH=amd64 go build -ldflags="-s -w" -o "/var/www/rmm/dist/agents/tacticalagent-v${AGENT_VER}-windows-amd64.exe" . || true
    CGO_ENABLED=0 GOOS=windows GOARCH=386 go build -ldflags="-s -w" -o "/var/www/rmm/dist/agents/tacticalagent-v${AGENT_VER}-windows-386.exe" . || true
  fi
fi

sudo chown ${WEB_USER}:${WEB_GROUP} -R /var/www/rmm/dist

# Configure Fedora / RHEL Firewalld & SELinux permissions if active
if [[ "$OS_FAMILY" == "fedora" ]]; then
  if systemctl is-active --quiet firewalld; then
    print_green 'Configuring Firewalld for HTTP/HTTPS on Fedora/RHEL'
    sudo firewall-cmd --permanent --add-service=http >/dev/null 2>&1 || true
    sudo firewall-cmd --permanent --add-service=https >/dev/null 2>&1 || true
    sudo firewall-cmd --reload >/dev/null 2>&1 || true
  fi
  if command -v setsebool >/dev/null 2>&1; then
    sudo setsebool -P httpd_can_network_connect 1 >/dev/null 2>&1 || true
  fi
  sudo chmod o+x /rmm /rmm/api /rmm/api/tacticalrmm 2>/dev/null || true
fi

nginxfrontend="$(
  cat <<EOF
server {
    server_name ${frontenddomain};
    charset utf-8;
    location / {
        root /var/www/rmm/dist;
        try_files \$uri \$uri/ /index.html;
        add_header Cache-Control "no-store, no-cache, must-revalidate";
        add_header Pragma "no-cache";
    }
    error_log  /var/log/nginx/frontend-error.log;
    access_log /var/log/nginx/frontend-access.log;

    listen 443 ssl;
    listen [::]:443 ssl;
    ssl_certificate ${CERT_PUB_KEY};
    ssl_certificate_key ${CERT_PRIV_KEY};
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers EECDH+AESGCM:EDH+AESGCM;
    ssl_ecdh_curve secp384r1;
    add_header X-Content-Type-Options nosniff;
}

server {
    if (\$host = ${frontenddomain}) {
        return 301 https://\$host\$request_uri;
    }

    listen 80;
    listen [::]:80;
    server_name ${frontenddomain};
    return 404;
}
EOF
)"
echo "${nginxfrontend}" | sudo tee /etc/nginx/sites-available/frontend.conf >/dev/null

sudo ln -sf /etc/nginx/sites-available/frontend.conf /etc/nginx/sites-enabled/frontend.conf

print_green 'Enabling Services'

for i in rmm.service daphne.service celery.service celerybeat.service nginx; do
  sudo systemctl enable ${i}
  sudo systemctl stop ${i}
  sudo systemctl start ${i}
done
sleep 5
sudo systemctl enable meshcentral

print_green 'Starting meshcentral and waiting for it to be ready'

sudo systemctl restart meshcentral

sleep 3

# The first time we start meshcentral, it will need some time to generate certs and install plugins.
# This will take anywhere from a few seconds to a few minutes depending on the server's hardware
# We will know it's ready once the last line of the systemd service stdout is 'MeshCentral HTTP server running on port.....'
while ! [[ $CHECK_MESH_READY ]]; do
  CHECK_MESH_READY=$(sudo journalctl -u meshcentral.service -b --no-pager | grep "MeshCentral HTTP server running on port")
  echo -ne "${GREEN}Mesh Central not ready yet...${NC}\n"
  sleep 5
done

print_green 'Generating meshcentral login token key'

MESHTOKENKEY=$(node /meshcentral/node_modules/meshcentral --logintokenkey)

meshtoken="$(
  cat <<EOF
MESH_TOKEN_KEY = "${MESHTOKENKEY}"
EOF
)"
echo "${meshtoken}" | tee --append $local_settings >/dev/null

print_green 'Creating meshcentral account and group'

sudo systemctl stop meshcentral
sleep 1
cd /meshcentral

node node_modules/meshcentral --createaccount ${meshusername} --pass ${MESHPASSWD} --email ${letsemail}
sleep 1
node node_modules/meshcentral --adminaccount ${meshusername}

sudo systemctl start meshcentral
sleep 5

while ! [[ $CHECK_MESH_READY2 ]]; do
  CHECK_MESH_READY2=$(sudo journalctl -u meshcentral.service -b --no-pager | grep "MeshCentral HTTP server running on port")
  echo -ne "${GREEN}Mesh Central not ready yet...${NC}\n"
  sleep 5
done

node node_modules/meshcentral/meshctrl.js --url wss://${meshdomain}:443 --loginuser ${meshusername} --loginpass ${MESHPASSWD} AddDeviceGroup --name TacticalRMM
sleep 1

sudo systemctl enable nats.service
cd /rmm/api/tacticalrmm
source /rmm/api/env/bin/activate
python manage.py initial_db_setup
python manage.py reload_nats
python manage.py sync_mesh_with_trmm
deactivate
sudo systemctl start nats.service

sleep 1
sudo systemctl enable nats-api.service
sudo systemctl start nats-api.service

## disable django admin
sed -i 's/ADMIN_ENABLED = True/ADMIN_ENABLED = False/g' $local_settings

print_green 'Restarting services'
for i in rmm.service daphne.service celery.service celerybeat.service; do
  sudo systemctl stop ${i}
  sudo systemctl start ${i}
done

printf >&2 "${YELLOW}%0.s*${NC}" {1..80}
printf >&2 "\n\n"
printf >&2 "${YELLOW}Installation complete!${NC}\n\n"
printf >&2 "${YELLOW}Access your rmm at: ${GREEN}https://${frontenddomain}${NC}\n\n"
printf >&2 "${YELLOW}MeshCentral username: ${GREEN}${meshusername}${NC}\n"
printf >&2 "${YELLOW}MeshCentral password: ${GREEN}${MESHPASSWD}${NC}\n\n"

if [ "$BEHIND_NAT" = true ]; then
  echo -ne "${YELLOW}Read below if your router does NOT support Hairpin NAT${NC}\n\n"
  echo -ne "${GREEN}If you will be accessing the web interface of the RMM from the same LAN as this server,${NC}\n"
  echo -ne "${GREEN}you'll need to make sure your 3 subdomains resolve to ${IPV4}${NC}\n"
  echo -ne "${GREEN}This also applies to any agents that will be on the same local network as the rmm.${NC}\n"
  echo -ne "${GREEN}You'll also need to setup port forwarding in your router on port 443${NC}\n\n"
fi

printf >&2 "${YELLOW}%0.s*${NC}" {1..80}
printf >&2 "\n"
