# Guia Completo de Implantação e Testes — Tactical RMM Enhanced (Multi-Distro & Multi-OS)

Este guia reúne o passo a passo para instalar e testar o **Servidor** e os **Agentes** do **Tactical RMM Enhanced** em **Ubuntu**, **Debian**, **Fedora** e **Windows**, além do **Dashboard Web (Português / Inglês / Espanhol)**.

---

## 1. Instalação do Servidor no Linux (Ubuntu, Debian e Fedora)

Diferente do Tactical RMM original (que bloqueava a instalação apenas para Debian 13), o nosso `install.sh` possui detecção automática de distribuição (`/etc/os-release`) e suporta nativamente:
- **Ubuntu:** `20.04 LTS`, `22.04 LTS`, `24.04 LTS`, `26.04+` (e derivados como Linux Mint / Pop!_OS) via `apt`
- **Debian:** `11 (Bullseye)`, `12 (Bookworm)`, `13 (Trixie)+` via `apt`
- **Fedora / Enterprise Linux:** `Fedora 38 / 39 / 40 / 41 / 42+`, `RHEL`, `Rocky Linux` e `AlmaLinux` via `dnf` (incluindo configuração automática de `firewalld`, `SELinux`, `postgresql-server` e `redis.service`)

### Comandos para instalar o Servidor (Ubuntu / Debian / Fedora):
```bash
git clone https://github.com/WallisonWS/tactical-rmm-enhanced.git
cd tactical-rmm-enhanced
chmod +x install.sh update.sh
./install.sh
```
> **Dica para Laboratório / Homologação (Sem Domínio Público ou com Certificado Autoassinado):**
> ```bash
> ./install.sh --insecure --skip-ram-check
> ```
> Durante a instalação, o script compila automaticamente o **Frontend Vue 3 Multi-Idioma (PT/EN/ES)** em `/var/www/rmm/dist` e compila os binários do **Agente Go (`rmmagent`)** para **Windows (`amd64`/`386`)** e **Linux (`amd64`/`arm64`)** em `/var/www/rmm/dist/agents/`.

---

## 2. Instalação no Windows (Windows 10 / 11 & Windows Server 2016/2019/2022/2025)

No Windows, utilize o instalador PowerShell `install-windows.ps1` na raiz do repositório:

```powershell
cd C:\Users\wallison.araujo\.gemini\antigravity\scratch\tactical-rmm-enhanced

# Modo Interativo (Menu com 3 opções: Servidor Nativo, Servidor Docker ou Agente Endpoint)
.\install-windows.ps1

# Ou diretamente por parâmetro:
.\install-windows.ps1 -Mode ServerNative
.\install-windows.ps1 -Mode ServerDocker
.\install-windows.ps1 -Mode Agent -ApiUrl "https://api.seudominio.com" -ClientId 1 -SiteId 1 -AuthToken "SEU_TOKEN" -EnableRDP -EnablePing
```

---

## 3. Instalação de Agentes nos Computadores (Windows e Linux: Ubuntu, Debian e Fedora)

Pelo Painel Web (**Agentes > Instalar Agente** / **Agents > Install Agent**):
1. Escolha o **Sistema Operacional**:
   - **Windows (10 / 11 / Server):**
     - **PowerShell (`.ps1`):** Baixa o script automatizado (funciona inclusive com certificado autoassinado `--insecure` e configura auto-recuperação do serviço `sc.exe failure`).
     - **Standard EXE / Manual:** Exibe o comando completo para Prompt de Comando (Admin).
     - **Generated EXE:** Gera o instalador `.exe` customizado.
   - **Linux (Ubuntu / Debian / Fedora):**
     - **Não exige mais assinatura paga (Code Signing) da Amidaware!**
     - Selecione a distribuição desejada:
       - **Universal (Auto-Detectar Ubuntu / Debian / Fedora)**
       - **Ubuntu (20.04 / 22.04 / 24.04 / 26.04 — APT)**
       - **Debian (11 / 12 / 13 — APT)**
       - **Fedora / RHEL / Rocky (38 / 39 / 40 / 41 / 42 — DNF + SELinux)**
     - Funciona tanto em **Servidores SSH (Headless)** quanto em **Desktops com Interface Gráfica (X11 / Wayland)**.
     - Se o binário pré-compilado não estiver acessível na URL primária, o script `agent_linux.sh` compila automaticamente o agente Go localmente na máquina Linux!

---

## 4. Testando o Dashboard Web Rapidamente

```powershell
cd C:\Users\wallison.araujo\.gemini\antigravity\scratch\tactical-rmm-enhanced\web
npm install --legacy-peer-deps
npm run dev
```

- Na barra superior direita (`MainLayout.vue`), clique no botão de idioma (`🇧🇷 PT` / `🇺🇸 EN` / `🇪🇸 ES`) para alternar instantaneamente entre **Português**, **Inglês** e **Espanhol**.
- Verifique as **6 novas abas Enterprise**:
  1. **Telemetria ao Vivo** (`TelemetryTab.vue`)
  2. **Segurança & EDR** (`SecurityEDRTab.vue` — suporta Windows Defender Firewall, Ubuntu/Debian `ufw` e Fedora `firewalld`)
  3. **Rede & Portas** (`NetworkToolsTab.vue`)
  4. **Auto-Cura & IA** (`SelfHealWingetTab.vue` — suporta Windows `winget`, Ubuntu/Debian `apt` e Fedora `dnf`)
  5. **RDP & Link HA** (`RDPHAConnectivityTab.vue`)
  6. **Suporte TI & Hardware** (`ITSupportHardwareTab.vue`)
