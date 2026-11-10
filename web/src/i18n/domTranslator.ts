import { watch, type Ref } from "vue";
import type { SupportedLocale } from "./index";

const originalTextMap = new WeakMap<Text, string>();
const originalAttrMap = new WeakMap<Element, Record<string, string>>();

const SKIP_TAGS = new Set([
  "SCRIPT",
  "STYLE",
  "NOSCRIPT",
  "CODE",
  "PRE",
  "TEXTAREA",
  "SVG",
  "PATH",
]);

function shouldSkipElement(el: Element | null): boolean {
  if (!el) return true;
  if (SKIP_TAGS.has(el.tagName)) return true;
  if (
    el.closest(
      ".monaco-editor, .xterm, pre, code, [data-no-translate='true']",
    )
  ) {
    return true;
  }
  if (el.classList.contains("q-icon") || el.classList.contains("material-icons")) {
    return true;
  }
  return false;
}

/**
 * Exact phrase dictionary: maps source strings (English from upstream Tactical RMM
 * or Portuguese from Enhanced components) to [pt-BR, en-US, es-ES].
 */
const EXACT_PHRASES: Array<[string, string, string]> = [
  // Common & Global Actions
  ["No agent selected", "Nenhum agente selecionado", "Ningún agente seleccionado"],
  ["No Agents", "Nenhum Agente", "Sin Agentes"],
  ["No Clients", "Nenhum Cliente", "Sin Clientes"],
  ["No checks", "Nenhuma verificação", "Sin verificaciones"],
  ["No tasks", "Nenhuma tarefa", "Sin tareas"],
  ["No notes", "Nenhuma nota", "Sin notas"],
  ["No Windows Updates", "Nenhuma atualização do Windows", "Sin actualizaciones de Windows"],
  ["No data available", "Nenhum dado disponível", "Sin datos disponibles"],
  ["No results", "Sem resultados", "Sin resultados"],
  ["Records per page:", "Registros por página:", "Registros por página:"],
  ["Only supported for Windows agents at this time", "Suportado apenas para agentes Windows no momento", "Solo compatible con agentes Windows por el momento"],
  ["Refresh", "Atualizar", "Actualizar"],
  ["Close", "Fechar", "Cerrar"],
  ["Cancel", "Cancelar", "Cancelar"],
  ["Save", "Salvar", "Guardar"],
  ["Submit", "Enviar", "Enviar"],
  ["Add", "Adicionar", "Añadir"],
  ["New", "Novo", "Nuevo"],
  ["Edit", "Editar", "Editar"],
  ["Delete", "Excluir", "Eliminar"],
  ["Remove", "Remover", "Quitar"],
  ["Search", "Pesquisar", "Buscar"],
  ["Apply", "Aplicar", "Aplicar"],
  ["Clear", "Limpar", "Limpiar"],
  ["Yes", "Sim", "Sí"],
  ["No", "Não", "No"],
  ["Actions", "Ações", "Acciones"],
  ["Status", "Status", "Estado"],
  ["Name", "Nome", "Nombre"],
  ["Description", "Descrição", "Descripción"],
  ["Type", "Tipo", "Tipo"],
  ["Version", "Versão", "Versión"],
  ["Size", "Tamanho", "Tamaño"],
  ["Date", "Data", "Fecha"],
  ["Time", "Data/Hora", "Fecha/Hora"],
  ["User", "Usuário", "Usuario"],
  ["Username", "Usuário", "Usuario"],
  ["Password", "Senha", "Contraseña"],
  ["Login", "Entrar", "Iniciar Sesión"],
  ["Log in with SSO", "Entrar com SSO", "Iniciar sesión con SSO"],
  ["Two-Factor Token", "Código de Dois Fatores (2FA)", "Código de Dos Factores (2FA)"],
  ["This field is required", "Este campo é obrigatório", "Este campo es obligatorio"],

  // Summary Tab & Hardware Details
  ["Hardware Details", "Detalhes do Hardware", "Detalles del Hardware"],
  ["Checks Status", "Status das Verificações", "Estado de Verificaciones"],
  ["Custom Fields", "Campos Personalizados", "Campos Personalizados"],
  ["Disks", "Discos", "Discos"],
  ["Popout", "Abrir em Janela", "Abrir en Ventana"],
  ["Take Control", "Controle Remoto", "Control Remoto"],
  ["Maintenance Mode", "Modo de Manutenção", "Modo de Mantenimiento"],
  ["Enable Maintenance Mode", "Ativar Modo de Manutenção", "Activar Modo de Mantenimiento"],
  ["Disable Maintenance Mode", "Desativar Modo de Manutenção", "Desactivar Modo de Mantenimiento"],
  ["unknown make/model", "Fabricante/Modelo padrão", "Fabricante/Modelo estándar"],
  ["Agent online", "Agente online", "Agente en línea"],
  ["Agent offline", "Agente offline", "Agente desconectado"],
  ["Agent overdue", "Agente atrasado (Overdue)", "Agente retrasado (Overdue)"],
  ["Reboot required", "Reinicialização necessária", "Reinicio requerido"],
  ["Checks Status", "Status de Verificações", "Estado de Verificaciones"],
  ["Patches Pending", "Patches Pendentes", "Parches Pendientes"],
  ["Pending Actions", "Ações Pendentes", "Acciones Pendientes"],
  ["Agent Status", "Status do Agente", "Estado del Agente"],
  ["Reboot", "Reiniciar", "Reiniciar"],

  // Client/Site Context Menu & FileBar
  ["Add Site", "Adicionar Unidade / Site", "Añadir Sitio / Sede"],
  ["Add Client", "Adicionar Cliente", "Añadir Cliente"],
  ["Install Agent", "Instalar Agente", "Instalar Agente"],
  ["Assign Automation Policy", "Atribuir Política de Automação", "Asignar Política de Automatización"],
  ["Assign Alert Template", "Atribuir Modelo de Alerta", "Asignar Plantilla de Alerta"],
  ["Run URL Action", "Executar Ação de URL", "Ejecutar Acción URL"],
  ["Run Checks", "Executar Verificações", "Ejecutar Verificaciones"],
  ["Reporting", "Relatórios", "Informes"],
  ["Reporting Manager", "Gerenciador de Relatórios", "Gestor de Informes"],
  ["Documentation", "Documentação", "Documentación"],
  ["GitHub Repo", "Repositório GitHub", "Repositorio GitHub"],
  ["Bug Report", "Reportar Problema", "Reportar Error"],
  ["Feature Request", "Solicitar Funcionalidade", "Solicitar Función"],
  ["Join Discord", "Comunidade Discord", "Comunidad Discord"],

  // Checks Tab
  ["Disk Space Check", "Verificação de Espaço em Disco", "Verificación de Espacio en Disco"],
  ["Ping Check", "Verificação de Ping", "Verificación de Ping"],
  ["CPU Load Check", "Verificação de Uso de CPU", "Verificación de Carga de CPU"],
  ["Memory Check", "Verificação de Memória RAM", "Verificación de Memoria RAM"],
  ["Windows Service Check", "Verificação de Serviço Windows", "Verificación de Servicio Windows"],
  ["Script Check", "Verificação por Script", "Verificación por Script"],
  ["Event Log Check", "Verificação de Log de Eventos", "Verificación de Registro de Eventos"],
  ["Run Checks Now", "Executar Verificações Agora", "Ejecutar Verificaciones Ahora"],
  ["Reset All Checks Status", "Resetar Status das Verificações", "Restablecer Estado de Verificaciones"],
  ["Reset Check Status", "Resetar Status da Verificação", "Restablecer Estado de Verificación"],
  ["SMS Alert", "Alerta por SMS", "Alerta por SMS"],
  ["Email Alert", "Alerta por E-mail", "Alerta por Correo"],
  ["Dashboard Alert", "Alerta no Painel", "Alerta en el Panel"],
  ["Assigned To", "Atribuído a", "Asignado a"],
  ["Last Run", "Última Execução", "Última Ejecución"],
  ["More Info", "Mais Informações", "Más Información"],

  // Tasks Tab
  ["Add Task", "Adicionar Tarefa", "Añadir Tarea"],
  ["Run task now", "Executar tarefa agora", "Ejecutar tarea ahora"],
  ["Enabled", "Ativado", "Habilitado"],
  ["Collector Task", "Tarefa Coletora", "Tarea Colectora"],
  ["Sync Status", "Status de Sincronismo", "Estado de Sincronización"],
  ["Schedule", "Agendamento", "Programación"],
  ["Last Run Status", "Status da Última Execução", "Estado de Última Ejecución"],

  // Windows Updates / Patches Tab
  ["Run Update Scan", "Verificar Atualizações Agora", "Buscar Actualizaciones Ahora"],
  ["Install Approved Updates", "Instalar Atualizações Aprovadas", "Instalar Actualizaciones Aprobadas"],
  ["Inherit", "Herdar Política", "Heredar Política"],
  ["Approve", "Aprovar", "Aprobar"],
  ["Ignore", "Ignorar", "Ignorar"],
  ["Do Nothing", "Não Fazer Nada", "No Hacer Nada"],
  ["Installed", "Instalado", "Instalado"],
  ["Pending", "Pendente", "Pendiente"],
  ["Severity", "Severidade", "Severidad"],
  ["Title", "Título", "Título"],
  ["More Info URL", "URL de Informações", "URL de Información"],
  ["Installed On", "Instalado em", "Instalado el"],

  // Software Tab
  ["Install Software", "Instalar Software", "Instalar Software"],
  ["Uninstall", "Desinstalar", "Desinstalar"],
  ["Publisher", "Fabricante / Editor", "Editor / Fabricante"],

  // History, Notes, Assets, Debug, Audit Tabs
  ["Action", "Ação", "Acción"],
  ["Script/Command", "Script / Comando", "Script / Comando"],
  ["Initiated By", "Iniciado Por", "Iniciado Por"],
  ["Output", "Saída / Resultado", "Salida / Resultado"],
  ["Add Note", "Adicionar Nota", "Añadir Nota"],
  ["Note", "Nota", "Nota"],
  ["Operating System", "Sistema Operacional", "Sistema Operativo"],
  ["Memory", "Memória RAM", "Memoria RAM"],
  ["Bios", "BIOS", "BIOS"],
  ["Computer System", "Sistema do Computador", "Sistema del Equipo"],
  ["Motherboard", "Placa-Mãe", "Placa Base"],
  ["Computer System Product", "Produto do Sistema", "Producto del Sistema"],
  ["Network Config", "Configuração de Rede", "Configuración de Red"],
  ["Graphics", "Placa de Vídeo", "Gráficos"],
  ["Monitors", "Monitores", "Monitores"],
  ["Network Adapters", "Adaptadores de Rede", "Adaptadores de Red"],

  // Modals & Managers (Global Settings, Clients, Scripts, Automation, Alerts, Remote Background)
  ["Clients Manager", "Gerenciador de Clientes", "Gestor de Clientes"],
  ["Script Manager", "Gerenciador de Scripts", "Gestor de Scripts"],
  ["Automation Manager", "Gerenciador de Automação", "Gestor de Automatización"],
  ["Alerts Manager", "Gerenciador de Alertas", "Gestor de Alertas"],
  ["Permissions Manager", "Gerenciador de Permissões", "Gestor de Permisos"],
  ["User Administration", "Administração de Usuários", "Administración de Usuarios"],
  ["Global Settings", "Configurações Globais", "Configuración Global"],
  ["Server Maintenance", "Manutenção do Servidor", "Mantenimiento del Servidor"],
  ["Manage Deployments", "Gerenciar Implantações", "Gestionar Despliegues"],
  ["Update Agents", "Atualizar Agentes", "Actualizar Agentes"],
  ["Send Command", "Enviar Comando", "Enviar Comando"],
  ["Run Script", "Executar Script", "Ejecutar Script"],
  ["Agent Recovery", "Recuperação do Agente", "Recuperación del Agente"],
  ["Remote Background", "Segundo Plano Remoto", "Segundo Plano Remoto"],
  ["Terminal", "Terminal", "Terminal"],
  ["Services", "Serviços", "Servicios"],
  ["Processes", "Processos", "Procesos"],
  ["Event Log", "Visualizador de Eventos", "Visor de Eventos"],
  ["File Browser", "Gerenciador de Arquivos", "Explorador de Archivos"],
  ["User Preferences", "Preferências do Usuário", "Preferencias del Usuario"],
  ["General", "Geral", "General"],
  ["Key Store", "Cofre de Chaves", "Almacén de Claves"],
  ["URL Actions", "Ações de URL", "Acciones URL"],
  ["MeshCentral", "MeshCentral", "MeshCentral"],
  ["Email Alerts", "Alertas por E-mail", "Alertas por Correo"],
  ["SMS Alerts", "Alertas por SMS", "Alertas por SMS"],

  // Enhanced Context Menu & Sub-tabs (Portuguese -> English / Spanish)
  ["Full Autonomous Self-Heal", "Auto-Cura Completa Autônoma", "Auto-Curación Completa Autónoma"],
  ["Deep Disk Cleanup", "Limpeza Profunda de Disco", "Limpieza Profunda de Disco"],
  ["Restart Stopped Services", "Reiniciar Serviços Parados", "Reiniciar Servicios Detenidos"],
  ["Winget Upgrade All Software", "Atualizar Softwares (Winget)", "Actualizar Software (Winget)"],
  ["Reparar Link & Mesh (HA)", "Repair Link & Mesh (HA)", "Reparar Enlace y Mesh (HA)"],
  ["Habilitar RDP Seguro (NLA)", "Enable Secure RDP (NLA)", "Habilitar RDP Seguro (NLA)"],
  ["Baixar Conexão .RDP (1-Clique)", "Download .RDP Connection (1-Click)", "Descargar Conexión .RDP (1-Clic)"],
  ["Forçar GPO (gpupdate /force)", "Force GPO (gpupdate /force)", "Forzar GPO (gpupdate /force)"],
  ["Resetar Spooler de Impressão", "Reset Print Spooler", "Reiniciar Spooler de Impresión"],
  ["Enviar Aviso TI na Tela", "Send On-Screen IT Notice", "Enviar Aviso TI en Pantalla"],
  ["Active Directory (GPO) & Unidades Sem AD (Workgroup / Windows Server)", "Active Directory (GPO) & Non-AD Units (Workgroup / Windows Server)", "Active Directory (GPO) y Unidades Sin AD (Workgroup / Windows Server)"],
  ["Levantamento de Computadores na Rede da Unidade (Sem AD / via Servidor Local)", "Unit LAN Computer Discovery (Non-AD / via Local Server)", "Levantamiento de Equipos en la Red de la Unidad (Sin AD / vía Servidor Local)"],
  ["Escanear Rede da Unidade", "Scan Unit Network", "Escanear Red de la Unidad"],
  ["Gerar Script GPO & Sem AD", "Generate GPO & Non-AD Script", "Generar Script GPO y Sin AD"],
  ["Testar Canal / Status", "Test Channel / Status", "Probar Canal / Estado"],
  ["Reparar Netlogon / Hora", "Repair Netlogon / Time", "Reparar Netlogon / Hora"],
  ["Sincronizar NTP (Sem AD)", "Sync NTP (Non-AD)", "Sincronizar NTP (Sin AD)"],
  ["Diagnóstico Server / AD", "Server / AD Diagnostics", "Diagnóstico Servidor / AD"],
];

// Build fast lookup maps for each target locale
const lookupMaps: Record<SupportedLocale, Map<string, string>> = {
  "pt-BR": new Map(),
  "en-US": new Map(),
  "es-ES": new Map(),
};

for (const [enText, ptText, esText] of EXACT_PHRASES) {
  // Note: some entries in EXACT_PHRASES have PT in col 0 and EN in col 1 (the last 13 items)
  const isPtSource = [
    "Reparar Link & Mesh (HA)",
    "Habilitar RDP Seguro (NLA)",
    "Baixar Conexão .RDP (1-Clique)",
    "Forçar GPO (gpupdate /force)",
    "Resetar Spooler de Impressão",
    "Enviar Aviso TI na Tela",
    "Active Directory (GPO) & Unidades Sem AD (Workgroup / Windows Server)",
    "Levantamento de Computadores na Rede da Unidade (Sem AD / via Servidor Local)",
    "Escanear Rede da Unidade",
    "Gerar Script GPO & Sem AD",
    "Testar Canal / Status",
    "Reparar Netlogon / Hora",
    "Sincronizar NTP (Sem AD)",
    "Diagnóstico Server / AD",
  ].includes(enText);

  const actualPt = isPtSource ? enText : ptText;
  const actualEn = isPtSource ? ptText : enText;
  const actualEs = esText;

  for (const key of [actualEn, actualPt, actualEs]) {
    lookupMaps["pt-BR"].set(key, actualPt);
    lookupMaps["en-US"].set(key, actualEn);
    lookupMaps["es-ES"].set(key, actualEs);
  }
}

function translateDynamicPatterns(raw: string, locale: SupportedLocale): string | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;

  // 1. Exact phrase match
  const exact = lookupMaps[locale].get(trimmed);
  if (exact) {
    return raw.replace(trimmed, exact);
  }

  // 2. Relative boot / last seen time: "7 hours ago", "22 days ago", "1 months ago", "5 minutes ago"
  const relMatch = trimmed.match(/^(\d+)\s+(second|seconds|minute|minutes|hour|hours|day|days|month|months|year|years)\s+ago$/i);
  if (relMatch) {
    const num = relMatch[1];
    const unit = relMatch[2].toLowerCase();
    if (locale === "en-US") return raw;
    const unitMapPt: Record<string, string> = {
      second: "segundo",
      seconds: "segundos",
      minute: "minuto",
      minutes: "minutos",
      hour: "hora",
      hours: "horas",
      day: "dia",
      days: "dias",
      month: "mês",
      months: "meses",
      year: "ano",
      years: "anos",
    };
    const unitMapEs: Record<string, string> = {
      second: "segundo",
      seconds: "segundos",
      minute: "minuto",
      minutes: "minutos",
      hour: "hora",
      hours: "horas",
      day: "día",
      days: "días",
      month: "mes",
      months: "meses",
      year: "año",
      years: "años",
    };
    if (locale === "pt-BR") {
      return `há ${num} ${unitMapPt[unit] || unit}`;
    }
    if (locale === "es-ES") {
      return `hace ${num} ${unitMapEs[unit] || unit}`;
    }
  }

  // 3. Disks free space: "378.4 GB free of 474.5 GB"
  const diskMatch = trimmed.match(/^([\d.,]+\s*[A-Za-z]+)\s+free\s+of\s+([\d.,]+\s*[A-Za-z]+)$/i);
  if (diskMatch) {
    if (locale === "pt-BR") return `${diskMatch[1]} livres de ${diskMatch[2]}`;
    if (locale === "es-ES") return `${diskMatch[1]} libres de ${diskMatch[2]}`;
    return `${diskMatch[1]} free of ${diskMatch[2]}`;
  }

  // 4. Pagination counter: "1-95 of 95"
  const pageMatch = trimmed.match(/^(\d+-\d+)\s+of\s+(\d+)$/i);
  if (pageMatch) {
    if (locale === "pt-BR" || locale === "es-ES") {
      return `${pageMatch[1]} de ${pageMatch[2]}`;
    }
    return `${pageMatch[1]} of ${pageMatch[2]}`;
  }

  // 5. Checks status chips: "3 checks passing", "1 checks failing"
  const checksMatch = trimmed.match(/^(\d+)\s+checks\s+(passing|failing|warning|info)$/i);
  if (checksMatch) {
    const num = checksMatch[1];
    const st = checksMatch[2].toLowerCase();
    if (locale === "pt-BR") {
      const mapPt: Record<string, string> = {
        passing: "verificações aprovadas",
        failing: "verificações falhando",
        warning: "verificações em alerta",
        info: "verificações informativas",
      };
      return `${num} ${mapPt[st] || st}`;
    }
    if (locale === "es-ES") {
      const mapEs: Record<string, string> = {
        passing: "verificaciones aprobadas",
        failing: "verificaciones fallando",
        warning: "verificaciones en alerta",
        info: "verificaciones informativas",
      };
      return `${num} ${mapEs[st] || st}`;
    }
  }

  // 6. Public IP / LAN IP prefixes
  if (trimmed.startsWith("Public IP:")) {
    const val = trimmed.slice("Public IP:".length);
    if (locale === "pt-BR") return `IP Público:${val}`;
    if (locale === "es-ES") return `IP Pública:${val}`;
  }
  if (trimmed.startsWith("LAN IP:")) {
    const val = trimmed.slice("LAN IP:".length);
    if (locale === "pt-BR") return `IP Local (LAN):${val}`;
    if (locale === "es-ES") return `IP Local (LAN):${val}`;
  }

  return null;
}

let isApplying = false;

export function translateDomSubtree(root: Node, locale: SupportedLocale) {
  if (typeof document === "undefined" || !root || isApplying) return;
  isApplying = true;
  try {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    let node = walker.nextNode() as Text | null;
    while (node) {
      const parent = node.parentElement;
      if (parent && !shouldSkipElement(parent)) {
        if (!originalTextMap.has(node)) {
          originalTextMap.set(node, node.nodeValue || "");
        }
        const orig = originalTextMap.get(node) || "";
        const translated = translateDynamicPatterns(orig, locale);
        const targetVal = translated !== null ? translated : orig;
        if (node.nodeValue !== targetVal) {
          node.nodeValue = targetVal;
        }
      }
      node = walker.nextNode() as Text | null;
    }

    if (root instanceof Element || root instanceof Document) {
      const elems = (root as Element).querySelectorAll
        ? (root as Element).querySelectorAll("[placeholder], [title], [aria-label]")
        : [];
      elems.forEach((el) => {
        if (shouldSkipElement(el)) return;
        let saved = originalAttrMap.get(el);
        if (!saved) {
          saved = {};
          for (const attr of ["placeholder", "title", "aria-label"]) {
            const val = el.getAttribute(attr);
            if (val) saved[attr] = val;
          }
          originalAttrMap.set(el, saved);
        }
        for (const [attr, origVal] of Object.entries(saved)) {
          const translated = translateDynamicPatterns(origVal, locale);
          const targetVal = translated !== null ? translated : origVal;
          if (el.getAttribute(attr) !== targetVal) {
            el.setAttribute(attr, targetVal);
          }
        }
      });
    }
  } finally {
    isApplying = false;
  }
}

let observerInstalled = false;

export function installSiteWideTranslator(currentLocale: Ref<SupportedLocale>) {
  if (typeof window === "undefined" || typeof document === "undefined" || observerInstalled) {
    return;
  }
  observerInstalled = true;

  const runFullPass = () => {
    if (document.body) {
      translateDomSubtree(document.body, currentLocale.value);
    }
  };

  watch(
    currentLocale,
    () => {
      runFullPass();
    },
    { immediate: true },
  );

  let rafId: number | null = null;
  const observer = new MutationObserver(() => {
    if (isApplying) return;
    if (rafId !== null) cancelAnimationFrame(rafId);
    rafId = requestAnimationFrame(() => {
      rafId = null;
      runFullPass();
    });
  });

  if (document.body) {
    observer.observe(document.body, {
      childList: true,
      subtree: true,
      characterData: false,
    });
    runFullPass();
  } else {
    window.addEventListener("DOMContentLoaded", () => {
      if (document.body) {
        observer.observe(document.body, {
          childList: true,
          subtree: true,
          characterData: false,
        });
        runFullPass();
      }
    });
  }
}
