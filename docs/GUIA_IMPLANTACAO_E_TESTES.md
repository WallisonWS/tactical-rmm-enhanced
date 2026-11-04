# Guia Rápido de Testes e Implantação — Tactical RMM Enhanced

Este guia reúne o passo a passo para você testar o **Dashboard Web (Português / Inglês / Espanhol)**, a **API Backend Django** e o **Agente Go (`rmmagent`)**.

---

## 1. Testando o Dashboard Web (Interface Vue 3 + Quasar + Multi-Idiomas)

Para visualizar e testar a interface gráfica, o seletor de idiomas (`🇧🇷 PT` / `🇺🇸 EN` / `🇪🇸 ES`), a barra de KPIs executivos e as 6 novas abas:

```powershell
cd C:\Users\wallison.araujo\.gemini\antigravity\scratch\tactical-rmm-enhanced\web
npm install
npm run serve
```

- Na barra superior direita (`MainLayout.vue`), clique no botão com ícone de tradução (`🇧🇷 PT`) para alternar instantaneamente entre:
  - **🇧🇷 Português (Brasil)** *(padrão inicial)*
  - **🇺🇸 English (US)**
  - **🇪🇸 Español**
- Verifique no painel inferior (`SubTableTabs.vue`) e na janela `RemoteBackground` as 6 novas abas:
  1. **Telemetria ao Vivo** (`TelemetryTab.vue`)
  2. **Segurança & EDR** (`SecurityEDRTab.vue`)
  3. **Rede & Portas** (`NetworkToolsTab.vue`)
  4. **Auto-Cura & IA** (`SelfHealWingetTab.vue`)
  5. **RDP & Link HA** (`RDPHAConnectivityTab.vue`)
  6. **Suporte TI & Hardware** (`ITSupportHardwareTab.vue`)

---

## 2. Subindo o Ambiente Completo com Docker Compose (Desenvolvimento/Homologação)

Para subir o ecossistema completo (API Django + PostgreSQL + Redis + MeshCentral + NATS + Frontend) em containers isolados:

```powershell
cd C:\Users\wallison.araujo\.gemini\antigravity\scratch\tactical-rmm-enhanced
cp .env.example .env
docker compose -f docker-compose.dev.yml up -d --build
```

---

## 3. Compilando o Agente Go (`rmmagent`) com os 28 Novos Handlers NATS RPC

Quando tiver o Go (`>= 1.22`) instalado no ambiente de build:

```powershell
cd C:\Users\wallison.araujo\.gemini\antigravity\scratch\tactical-rmm-enhanced\rmmagent

# Compilar para Windows 64-bit
$env:GOOS="windows"; $env:GOARCH="amd64"
go build -o tacticalagent.exe .

# Testar os novos modos de diagnóstico direto via CLI
.\tacticalagent.exe -m telemetry
.\tacticalagent.exe -m securityaudit
.\tacticalagent.exe -m netdiag
.\tacticalagent.exe -m selfheal
```
