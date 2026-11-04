# Tactical RMM Enhanced (REA Edition)

Plataforma completa de **Remote Monitoring & Management (RMM)** unificada, modelada e expandida via engenharia reversa estruturada (**REA — Reverse Engineer Anything**), consolidando:

1. **`api/`** — Backend em **Django + Django REST Framework + Django Channels (WebSockets) + Celery**
2. **`web/`** — Dashboard Administrativa em **Vue 3 + Quasar Framework + TypeScript + Xterm.js**
3. **`rmmagent/`** — Agente Multiplataforma (Windows, Linux, macOS) em **Go (Golang)** com comunicação em tempo real via **NATS + MessagePack**
4. **`natsapi/`** — Microserviço de alta performance em **Go** para ingestão de check-ins NATS direto no PostgreSQL
5. **`docs/`** — Dossiê completo de Engenharia Reversa REA ([`docs/REA_REVERSE_ENGINEERING_DOSSIER.md`](docs/REA_REVERSE_ENGINEERING_DOSSIER.md)) e Ledger de Evidências ([`docs/rea_evidence_ledger.json`](docs/rea_evidence_ledger.json))

---

## Novas Ferramentas e Funções Adicionadas

### 1. Agente Go (`rmmagent/agent/`) — +18 Novos Comandos RPC via NATS
- **Telemetria Ao Vivo & S.M.A.R.T. (`telemetry.go`)**:
  - `telemetry_snapshot`: Uso de CPU por núcleo/thread, RAM (Total/Usada/Livre), métricas de partições de disco, tráfego de rede (TX/RX bytes e pacotes), contagem de processos e uptime.
  - `smart_health`: Diagnóstico físico S.M.A.R.T. de discos (modelo, número de série, tipo de mídia SSD/NVMe/HDD e status de saúde).
- **Centro de Segurança, EDR & Firewall (`security_edr.go`)**:
  - `security_audit`: Cálculo de **Security Score (0–100)** com verificação de Antivírus/Windows Defender, Proteção em Tempo Real, Firewall, Criptografia de Disco (BitLocker/LUKS), UAC, RDP, protocolo SMBv1, processos suspeitos, portas críticas expostas e grupo de Administradores locais.
  - `firewall_status` & `firewall_rule`: Inspeção dos perfis Domain/Private/Public e criação/remoção/bloqueio instantâneo de portas TCP/UDP no Firewall do host.
  - `startup_items`, `local_users`, `bitlocker_status`: Auditoria completa de persistência (Autoruns), contas de usuários locais e criptografia de volume.
- **Ferramentas Avançadas de Rede (`network_tools.go`)**:
  - `netconnections`: Mapeamento em tempo real de conexões TCP/UDP ativas e portas em escuta (`LISTEN`) correlacionadas com PID e nome do processo.
  - `portscan`: Scanner de portas TCP concorrente (64 workers) com detecção de serviço e latência em milissegundos.
  - `netdiag`: Diagnóstico completo de conectividade (latência de resolução DNS, ICMP Ping, teste de alcance TCP/80 e TCP/443, IPs locais e IP público).
- **Motor Autônomo de Auto-Remediação / Self-Healing (`self_healing.go`)**:
  - `self_heal`: Auto-remediação inteligente (`full`, `disk`, `services`, `network`, `winupdate`, `memory`) que reinicia serviços automáticos parados, repara a fila do Windows Update (`wuauserv`, `bits`, `cryptsvc`), limpa caches e otimiza memória.
  - `disk_cleanup`: Limpeza profunda de diretórios temporários (`%TEMP%`, `C:\Windows\Temp`, `SoftwareDistribution\Download`, `/var/tmp`) retornando o total de arquivos removidos e bytes liberados.
  - `trim_memory` & `reset_network`: Otimização de Working Set de RAM e reset de pilha de rede (Flush DNS, limpeza de tabela ARP e reset de Winsock).
- **Gerenciador Nativo Winget & Patch de Terceiros (`winget_manager.go`)**:
  - `winget_list`, `winget_install`, `winget_upgrade`: Integração nativa com **Windows Package Manager (`winget`)** e `apt` (Linux) para listar pacotes desatualizados, instalar softwares silenciosamente por ID e atualizar todos os aplicativos em 1 clique.

### 2. Backend API (`api/tacticalrmm/`)
- **Novos Endpoints REST em [`api/tacticalrmm/agents/views_enhanced.py`](api/tacticalrmm/agents/views_enhanced.py)**:
  - `GET /agents/executive-summary/` — KPIs globais da frota (Fleet Health Score, % de Disponibilidade, % de Conformidade de Patches, Alertas Críticos/Avisos e Checks com falha).
  - `GET /agents/<agent_id>/telemetry/` — Telemetria em tempo real via NATS (com fallback resiliente para cache do banco).
  - `GET|POST /agents/<agent_id>/security-audit/` — Auditoria de Segurança/EDR, Autoruns, Usuários Locais e BitLocker.
  - `GET|POST /agents/<agent_id>/firewall/` — Gerenciamento remoto de regras e perfis de Firewall auditado no `AuditLog`.
  - `GET|POST /agents/<agent_id>/network/` — Conexões ativas, Port Scanner e NetDiag.
  - `POST /agents/<agent_id>/self-heal/` — Disparo auditado de rotinas de Self-Healing e limpeza profunda de disco.
  - `GET|POST /agents/<agent_id>/winget/` — Gerenciamento de pacotes via Winget/APT.
  - `POST /agents/<agent_id>/ai-diagnostics/` — Assistente de Diagnóstico de Causa Raiz (IA/Heurística) com geração automática de Playbooks de remediação.
- **Novos Tipos de Checks (`api/tacticalrmm/tacticalrmm/constants.py` & `checks/models.py`)**:
  - `port_check` (Disponibilidade de Porta TCP/UDP)
  - `ssl_cert` (Expiração de Certificado SSL/TLS)
  - `process_check` (Saúde e consumo de Processo)
  - `security_posture` (Postura de Segurança do Endpoint)
  - `smart_disk` (Saúde física S.M.A.R.T. do disco)
  - Flag `auto_remediate` adicionada ao modelo `Check`.

### 3. Dashboard Web (`web/src/`)
- **Barra Executiva de KPIs da Frota ([`ExecutiveKPIBar.vue`](web/src/components/dashboard/ExecutiveKPIBar.vue))**: Integrada no topo da `DashboardView.vue`.
- **4 Novas Abas de Gerenciamento em [`SubTableTabs.vue`](web/src/components/SubTableTabs.vue) e [`RemoteBackground.vue`](web/src/views/RemoteBackground.vue)**:
  - **Live Telemetry ([`TelemetryTab.vue`](web/src/components/agents/TelemetryTab.vue))**
  - **Security & EDR ([`SecurityEDRTab.vue`](web/src/components/agents/SecurityEDRTab.vue))**
  - **Network & Ports ([`NetworkToolsTab.vue`](web/src/components/agents/NetworkToolsTab.vue))**
  - **Self-Heal & AI ([`SelfHealWingetTab.vue`](web/src/components/agents/SelfHealWingetTab.vue))**
- **Menu de Contexto Rápido Aprimorado ([`AgentActionMenu.vue`](web/src/components/agents/AgentActionMenu.vue))**: Submenu *Self-Heal & Winget* com ações de 1 clique direto na tabela de agentes.
