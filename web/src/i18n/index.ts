import { ref, computed } from "vue";

export type SupportedLocale = "pt-BR" | "en-US" | "es-ES";

export interface LocaleOption {
  code: SupportedLocale;
  label: string;
  shortLabel: string;
  flag: string;
}

export const SUPPORTED_LOCALES: LocaleOption[] = [
  { code: "pt-BR", label: "Português (Brasil)", shortLabel: "PT", flag: "🇧🇷" },
  { code: "en-US", label: "English (US)", shortLabel: "EN", flag: "🇺🇸" },
  { code: "es-ES", label: "Español", shortLabel: "ES", flag: "🇪🇸" },
];

const STORAGE_KEY = "trmm_locale";

function getInitialLocale(): SupportedLocale {
  if (typeof window !== "undefined" && window.localStorage) {
    const saved = window.localStorage.getItem(STORAGE_KEY) as SupportedLocale | null;
    if (saved && ["pt-BR", "en-US", "es-ES"].includes(saved)) {
      return saved;
    }
  }
  return "pt-BR";
}

const currentLocale = ref<SupportedLocale>(getInitialLocale());

const messages: Record<SupportedLocale, Record<string, string>> = {
  "pt-BR": {
    // Top Header & Navigation
    "nav.backToDashboard": "Voltar ao Painel",
    "nav.agentCount": "Total de Agentes",
    "nav.servers": "Servidores",
    "nav.workstations": "Estações de Trabalho",
    "nav.total": "Total",
    "nav.offline": "Offline",
    "nav.preferences": "Preferências",
    "nav.account": "Conta",
    "nav.resetPassword": "Redefinir Senha",
    "nav.reset2fa": "Redefinir 2FA",
    "nav.logout": "Sair",
    "nav.language": "Idioma da Interface",
    "nav.allClients": "Todos os Clientes",

    // FileBar Menus
    "filebar.file": "Arquivo",
    "filebar.add": "Adicionar",
    "filebar.client": "Cliente",
    "filebar.site": "Unidade / Site",
    "filebar.auditLog": "Log de Auditoria",
    "filebar.debugLog": "Log de Depuração",
    "filebar.view": "Exibir",
    "filebar.pendingActions": "Ações Pendentes",
    "filebar.agents": "Agentes",
    "filebar.installAgent": "Instalar Agente",
    "filebar.manageDeployments": "Gerenciar Implantações",
    "filebar.updateAgents": "Atualizar Agentes",
    "filebar.settings": "Configurações",
    "filebar.clientsManager": "Gerenciador de Clientes",
    "filebar.scriptManager": "Gerenciador de Scripts",
    "filebar.automationManager": "Gerenciador de Automação",
    "filebar.alertsManager": "Gerenciador de Alertas",
    "filebar.permissionsManager": "Gerenciador de Permissões",
    "filebar.userAdmin": "Administração de Usuários",
    "filebar.globalSettings": "Configurações Globais",
    "filebar.codeSigning": "Assinatura de Código",
    "filebar.tools": "Ferramentas",
    "filebar.bulkCommand": "Comando em Massa",
    "filebar.bulkScript": "Script em Massa",
    "filebar.bulkPatch": "Patches em Massa",
    "filebar.serverMaintenance": "Manutenção do Servidor",
    "filebar.clearCache": "Limpar Cache",
    "filebar.recoverAllAgents": "Recuperar Todos os Agentes",
    "filebar.reporting": "Relatórios",
    "filebar.help": "Ajuda",

    // Executive KPI Bar
    "kpi.fleetHealth": "Saúde Global da Frota",
    "kpi.onlineAgents": "Agentes Online",
    "kpi.availability": "Disponibilidade",
    "kpi.patchCompliance": "Conformidade de Patches",
    "kpi.pendingAgents": "agentes com pendências",
    "kpi.activeAlerts": "Alertas & Falhas",
    "kpi.critical": "críticos",
    "kpi.warnings": "avisos",
    "kpi.failingChecks": "checks falhando",
    "kpi.pendingReboots": "Reinicializações Pendentes",
    "kpi.inMaintenance": "em manutenção",
    "kpi.refreshKpis": "Atualizar KPIs",

    // SubTableTabs
    "tabs.summary": "Resumo",
    "tabs.telemetry": "Telemetria ao Vivo",
    "tabs.security": "Segurança & EDR",
    "tabs.network": "Rede & Portas",
    "tabs.selfheal": "Auto-Cura & IA",
    "tabs.rdpHa": "RDP & Link HA",
    "tabs.checks": "Verificações",
    "tabs.tasks": "Tarefas",
    "tabs.patches": "Patches",
    "tabs.software": "Softwares",
    "tabs.history": "Histórico",
    "tabs.notes": "Notas",
    "tabs.assets": "Ativos",
    "tabs.debug": "Depuração",
    "tabs.audit": "Auditoria",

    // RDP & High-Availability Tab
    "rdpha.title": "Alta Disponibilidade (Agent ↔ API ↔ Mesh) & Acesso RDP Corporativo",
    "rdpha.subtitle": "Monitoramento contínuo de resiliência de comunicação de produção e controle seguro de Área de Trabalho Remota",
    "rdpha.refresh": "Validar Conectividade & RDP",
    "rdpha.repairLink": "Reparar / Ressincronizar Mesh & Link",
    "rdpha.apiChannel": "Canal Agent ↔ API (HTTPS)",
    "rdpha.natsChannel": "Canal Agent ↔ NATS (RPC)",
    "rdpha.meshChannel": "Serviço MeshCentral (Controle Remoto)",
    "rdpha.reachable": "Conectado (100% Operacional)",
    "rdpha.unreachable": "Degradado / Sem Resposta",
    "rdpha.latency": "Latência",
    "rdpha.rdpSection": "Gerenciador de Conexão RDP Corporativa",
    "rdpha.rdpStatus": "Status do RDP",
    "rdpha.nlaStatus": "Segurança NLA (CredSSP)",
    "rdpha.rdpPort": "Porta de Escuta",
    "rdpha.enabled": "Habilitado",
    "rdpha.disabled": "Desabilitado",
    "rdpha.enableRdp": "Habilitar RDP Seguro (NLA)",
    "rdpha.disableRdp": "Desabilitar RDP",
    "rdpha.restartRdp": "Reiniciar TermService",
    "rdpha.downloadRdp": "Baixar Arquivo .RDP (1-Clique)",
    "rdpha.openTakeControl": "Abrir Controle Remoto (Mesh)",
    "rdpha.activeSessions": "Sessões de Usuários no Computador (qwinsta)",
    "rdpha.sessionName": "Sessão",
    "rdpha.username": "Usuário",
    "rdpha.sessionId": "ID",
    "rdpha.state": "Estado",
    "rdpha.actions": "Ações",
    "rdpha.logoff": "Encerrar Sessão",
  },
  "en-US": {
    // Top Header & Navigation
    "nav.backToDashboard": "Back to Dashboard",
    "nav.agentCount": "Agent Count",
    "nav.servers": "Servers",
    "nav.workstations": "Workstations",
    "nav.total": "Total",
    "nav.offline": "Offline",
    "nav.preferences": "Preferences",
    "nav.account": "Account",
    "nav.resetPassword": "Reset Password",
    "nav.reset2fa": "Reset 2FA",
    "nav.logout": "Logout",
    "nav.language": "Interface Language",
    "nav.allClients": "All Clients",

    // FileBar Menus
    "filebar.file": "File",
    "filebar.add": "Add",
    "filebar.client": "Client",
    "filebar.site": "Site",
    "filebar.auditLog": "Audit Log",
    "filebar.debugLog": "Debug Log",
    "filebar.view": "View",
    "filebar.pendingActions": "Pending Actions",
    "filebar.agents": "Agents",
    "filebar.installAgent": "Install Agent",
    "filebar.manageDeployments": "Manage Deployments",
    "filebar.updateAgents": "Update Agents",
    "filebar.settings": "Settings",
    "filebar.clientsManager": "Clients Manager",
    "filebar.scriptManager": "Script Manager",
    "filebar.automationManager": "Automation Manager",
    "filebar.alertsManager": "Alerts Manager",
    "filebar.permissionsManager": "Permissions Manager",
    "filebar.userAdmin": "User Administration",
    "filebar.globalSettings": "Global Settings",
    "filebar.codeSigning": "Code Signing",
    "filebar.tools": "Tools",
    "filebar.bulkCommand": "Bulk Command",
    "filebar.bulkScript": "Bulk Script",
    "filebar.bulkPatch": "Bulk Patch Management",
    "filebar.serverMaintenance": "Server Maintenance",
    "filebar.clearCache": "Clear Cache",
    "filebar.recoverAllAgents": "Recover All Agents",
    "filebar.reporting": "Reporting",
    "filebar.help": "Help",

    // Executive KPI Bar
    "kpi.fleetHealth": "Global Fleet Health",
    "kpi.onlineAgents": "Online Agents",
    "kpi.availability": "Availability",
    "kpi.patchCompliance": "Patch Compliance",
    "kpi.pendingAgents": "agents with pending patches",
    "kpi.activeAlerts": "Active Alerts & Checks",
    "kpi.critical": "critical",
    "kpi.warnings": "warnings",
    "kpi.failingChecks": "failing checks",
    "kpi.pendingReboots": "Pending Reboots",
    "kpi.inMaintenance": "in maintenance",
    "kpi.refreshKpis": "Refresh KPIs",

    // SubTableTabs
    "tabs.summary": "Summary",
    "tabs.telemetry": "Live Telemetry",
    "tabs.security": "Security & EDR",
    "tabs.network": "Network & Ports",
    "tabs.selfheal": "Self-Heal & AI",
    "tabs.rdpHa": "RDP & HA Link",
    "tabs.checks": "Checks",
    "tabs.tasks": "Tasks",
    "tabs.patches": "Patches",
    "tabs.software": "Software",
    "tabs.history": "History",
    "tabs.notes": "Notes",
    "tabs.assets": "Assets",
    "tabs.debug": "Debug",
    "tabs.audit": "Audit",

    // RDP & High-Availability Tab
    "rdpha.title": "High Availability (Agent ↔ API ↔ Mesh) & Corporate RDP Manager",
    "rdpha.subtitle": "Continuous production link resilience monitoring and secure Remote Desktop administration",
    "rdpha.refresh": "Validate Link & RDP",
    "rdpha.repairLink": "Repair / Resync Mesh & Link",
    "rdpha.apiChannel": "Agent ↔ API Channel (HTTPS)",
    "rdpha.natsChannel": "Agent ↔ NATS Channel (RPC)",
    "rdpha.meshChannel": "MeshCentral Service (Remote Control)",
    "rdpha.reachable": "Connected (100% Operational)",
    "rdpha.unreachable": "Degraded / Unresponsive",
    "rdpha.latency": "Latency",
    "rdpha.rdpSection": "Corporate Remote Desktop (RDP) Manager",
    "rdpha.rdpStatus": "RDP Status",
    "rdpha.nlaStatus": "NLA Security (CredSSP)",
    "rdpha.rdpPort": "Listening Port",
    "rdpha.enabled": "Enabled",
    "rdpha.disabled": "Disabled",
    "rdpha.enableRdp": "Enable Secure RDP (NLA)",
    "rdpha.disableRdp": "Disable RDP",
    "rdpha.restartRdp": "Restart TermService",
    "rdpha.downloadRdp": "Download .RDP File (1-Click)",
    "rdpha.openTakeControl": "Open Take Control (Mesh)",
    "rdpha.activeSessions": "Active Computer User Sessions (qwinsta)",
    "rdpha.sessionName": "Session",
    "rdpha.username": "Username",
    "rdpha.sessionId": "ID",
    "rdpha.state": "State",
    "rdpha.actions": "Actions",
    "rdpha.logoff": "Logoff Session",
  },
  "es-ES": {
    // Top Header & Navigation
    "nav.backToDashboard": "Volver al Panel",
    "nav.agentCount": "Total de Agentes",
    "nav.servers": "Servidores",
    "nav.workstations": "Estaciones de Trabajo",
    "nav.total": "Total",
    "nav.offline": "Desconectados",
    "nav.preferences": "Preferencias",
    "nav.account": "Cuenta",
    "nav.resetPassword": "Restablecer Contraseña",
    "nav.reset2fa": "Restablecer 2FA",
    "nav.logout": "Cerrar Sesión",
    "nav.language": "Idioma de la Interfaz",
    "nav.allClients": "Todos los Clientes",

    // FileBar Menus
    "filebar.file": "Archivo",
    "filebar.add": "Añadir",
    "filebar.client": "Cliente",
    "filebar.site": "Sitio / Sede",
    "filebar.auditLog": "Registro de Auditoría",
    "filebar.debugLog": "Registro de Depuración",
    "filebar.view": "Ver",
    "filebar.pendingActions": "Acciones Pendientes",
    "filebar.agents": "Agentes",
    "filebar.installAgent": "Instalar Agente",
    "filebar.manageDeployments": "Gestionar Despliegues",
    "filebar.updateAgents": "Actualizar Agentes",
    "filebar.settings": "Configuración",
    "filebar.clientsManager": "Gestor de Clientes",
    "filebar.scriptManager": "Gestor de Scripts",
    "filebar.automationManager": "Gestor de Automatización",
    "filebar.alertsManager": "Gestor de Alertas",
    "filebar.permissionsManager": "Gestor de Permisos",
    "filebar.userAdmin": "Administración de Usuarios",
    "filebar.globalSettings": "Configuración Global",
    "filebar.codeSigning": "Firma de Código",
    "filebar.tools": "Herramientas",
    "filebar.bulkCommand": "Comando Masivo",
    "filebar.bulkScript": "Script Masivo",
    "filebar.bulkPatch": "Parches Masivos",
    "filebar.serverMaintenance": "Mantenimiento del Servidor",
    "filebar.clearCache": "Limpiar Caché",
    "filebar.recoverAllAgents": "Recuperar Todos los Agentes",
    "filebar.reporting": "Informes",
    "filebar.help": "Ayuda",

    // Executive KPI Bar
    "kpi.fleetHealth": "Salud Global de la Flota",
    "kpi.onlineAgents": "Agentes en Línea",
    "kpi.availability": "Disponibilidad",
    "kpi.patchCompliance": "Cumplimiento de Parches",
    "kpi.pendingAgents": "agentes con parches pendientes",
    "kpi.activeAlerts": "Alertas y Fallos Activos",
    "kpi.critical": "críticos",
    "kpi.warnings": "advertencias",
    "kpi.failingChecks": "chequeos fallidos",
    "kpi.pendingReboots": "Reinicios Pendientes",
    "kpi.inMaintenance": "en mantenimiento",
    "kpi.refreshKpis": "Actualizar KPIs",

    // SubTableTabs
    "tabs.summary": "Resumen",
    "tabs.telemetry": "Telemetría en Vivo",
    "tabs.security": "Seguridad y EDR",
    "tabs.network": "Red y Puertos",
    "tabs.selfheal": "Auto-Curación e IA",
    "tabs.rdpHa": "RDP y Enlace HA",
    "tabs.checks": "Chequeos",
    "tabs.tasks": "Tareas",
    "tabs.patches": "Parches",
    "tabs.software": "Software",
    "tabs.history": "Historial",
    "tabs.notes": "Notas",
    "tabs.assets": "Activos",
    "tabs.debug": "Depuración",
    "tabs.audit": "Auditoría",

    // RDP & High-Availability Tab
    "rdpha.title": "Alta Disponibilidad (Agent ↔ API ↔ Mesh) y Gestor RDP Corporativo",
    "rdpha.subtitle": "Monitoreo continuo de resiliencia de comunicación en producción y control seguro de Escritorio Remoto",
    "rdpha.refresh": "Validar Enlace y RDP",
    "rdpha.repairLink": "Reparar / Resincronizar Mesh y Enlace",
    "rdpha.apiChannel": "Canal Agent ↔ API (HTTPS)",
    "rdpha.natsChannel": "Canal Agent ↔ NATS (RPC)",
    "rdpha.meshChannel": "Servicio MeshCentral (Control Remoto)",
    "rdpha.reachable": "Conectado (100% Operativo)",
    "rdpha.unreachable": "Degradado / Sin Respuesta",
    "rdpha.latency": "Latencia",
    "rdpha.rdpSection": "Gestor de Escritorio Remoto Corporativo (RDP)",
    "rdpha.rdpStatus": "Estado de RDP",
    "rdpha.nlaStatus": "Seguridad NLA (CredSSP)",
    "rdpha.rdpPort": "Puerto de Escucha",
    "rdpha.enabled": "Habilitado",
    "rdpha.disabled": "Deshabilitado",
    "rdpha.enableRdp": "Habilitar RDP Seguro (NLA)",
    "rdpha.disableRdp": "Deshabilitar RDP",
    "rdpha.restartRdp": "Reiniciar TermService",
    "rdpha.downloadRdp": "Descargar Archivo .RDP (1-Clic)",
    "rdpha.openTakeControl": "Abrir Control Remoto (Mesh)",
    "rdpha.activeSessions": "Sesiones de Usuario Activas (qwinsta)",
    "rdpha.sessionName": "Sesión",
    "rdpha.username": "Usuario",
    "rdpha.sessionId": "ID",
    "rdpha.state": "Estado",
    "rdpha.actions": "Acciones",
    "rdpha.logoff": "Cerrar Sesión",
  },
};

export function setLocale(locale: SupportedLocale) {
  currentLocale.value = locale;
  if (typeof window !== "undefined" && window.localStorage) {
    window.localStorage.setItem(STORAGE_KEY, locale);
  }
}

export function t(key: string, fallback?: string): string {
  const dict = messages[currentLocale.value] || messages["pt-BR"];
  return dict[key] || messages["en-US"][key] || fallback || key;
}

export function useI18n() {
  const activeLocaleOption = computed(
    () => SUPPORTED_LOCALES.find((l) => l.code === currentLocale.value) || SUPPORTED_LOCALES[0],
  );

  return {
    locale: currentLocale,
    locales: SUPPORTED_LOCALES,
    activeLocaleOption,
    setLocale,
    t,
  };
}
