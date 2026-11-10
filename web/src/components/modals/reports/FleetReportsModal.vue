<template>
  <q-card class="bg-dark text-white" style="min-height: 100vh; display: flex; flex-direction: column">
    <!-- Top Header -->
    <q-bar class="bg-primary text-white q-py-md">
      <q-icon name="assessment" size="sm" class="q-mr-sm" />
      <div class="text-subtitle1 text-weight-bold">
        Central de Relatórios Corporativos &amp; Inventário de TI
      </div>
      <q-space />
      <q-btn
        dense
        flat
        icon="refresh"
        label="Atualizar Dados"
        no-caps
        class="q-mr-sm"
        :loading="loading"
        @click="loadReportData"
      />
      <q-btn
        dense
        unelevated
        color="positive"
        icon="download"
        label="Exportar Excel (.CSV)"
        no-caps
        class="q-mr-sm q-px-sm"
        @click="exportCSV"
      />
      <q-btn
        dense
        unelevated
        color="indigo-6"
        icon="print"
        label="Imprimir / Salvar PDF"
        no-caps
        class="q-mr-md q-px-sm"
        @click="printReport"
      />
      <q-btn dense flat icon="close" @click="$emit('close')">
        <q-tooltip>Fechar</q-tooltip>
      </q-btn>
    </q-bar>

    <!-- Report Type Selector & Filters -->
    <q-card-section class="q-pb-sm">
      <div class="row q-col-gutter-sm items-center">
        <div class="col-12 col-md-3">
          <q-select
            v-model="selectedReportType"
            :options="reportTypeOptions"
            emit-value
            map-options
            dense
            outlined
            label="Tipo de Relatório"
          >
            <template v-slot:prepend>
              <q-icon name="description" color="primary" />
            </template>
          </q-select>
        </div>

        <div class="col-6 col-md-2">
          <q-select
            v-model="selectedClient"
            :options="clientOptions"
            dense
            outlined
            label="Cliente"
          />
        </div>

        <div class="col-6 col-md-2">
          <q-select
            v-model="selectedSite"
            :options="siteOptions"
            dense
            outlined
            label="Unidade / Site"
          />
        </div>

        <div class="col-6 col-md-2">
          <q-select
            v-model="selectedStatus"
            :options="statusOptions"
            emit-value
            map-options
            dense
            outlined
            label="Status do Computador"
          />
        </div>

        <div class="col-6 col-md-3">
          <q-input
            v-model="searchQuery"
            dense
            outlined
            clearable
            label="Pesquisar computador, usuário, IP, domínio..."
          >
            <template v-slot:prepend>
              <q-icon name="search" color="primary" />
            </template>
          </q-input>
        </div>
      </div>

      <!-- Summary KPI Chips -->
      <div class="row q-gutter-sm q-mt-xs items-center">
        <q-chip color="primary" text-color="white" icon="devices" dense>
          Total no Filtro: <strong class="q-ml-xs">{{ filteredRows.length }}</strong>
        </q-chip>
        <q-chip color="positive" text-color="white" icon="check_circle" dense>
          Online: <strong class="q-ml-xs">{{ summaryCounts.online }}</strong>
        </q-chip>
        <q-chip color="warning" text-color="black" icon="cloud_off" dense>
          Offline: <strong class="q-ml-xs">{{ summaryCounts.offline }}</strong>
        </q-chip>
        <q-chip color="deep-orange" text-color="white" icon="schedule" dense>
          Vencidos (Overdue): <strong class="q-ml-xs">{{ summaryCounts.overdue }}</strong>
        </q-chip>
        <q-chip color="teal-7" text-color="white" icon="domain" dense>
          No Domínio AD: <strong class="q-ml-xs">{{ summaryCounts.inAd }}</strong>
        </q-chip>
        <q-chip color="amber-9" text-color="white" icon="domain_disabled" dense>
          Fora do AD: <strong class="q-ml-xs">{{ summaryCounts.outsideAd }}</strong>
        </q-chip>
        <q-chip color="orange-9" text-color="white" icon="restart_alt" dense>
          Reboot Pendente: <strong class="q-ml-xs">{{ summaryCounts.rebootNeeded }}</strong>
        </q-chip>
      </div>
    </q-card-section>

    <q-separator dark />

    <!-- Report Data Table -->
    <q-card-section class="col q-pa-sm" style="overflow: auto">
      <q-table
        :rows="filteredRows"
        :columns="columns"
        row-key="agent_id"
        dense
        flat
        bordered
        :loading="loading"
        :pagination="{ rowsPerPage: 50, sortBy: 'hostname' }"
        :rows-per-page-options="[25, 50, 100, 0]"
        binary-state-sort
      >
        <template v-slot:body-cell-status="props">
          <q-td :props="props">
            <q-badge
              :color="
                props.row.status === 'online'
                  ? 'positive'
                  : props.row.status === 'overdue'
                    ? 'deep-orange'
                    : 'warning'
              "
              :label="
                props.row.status === 'online'
                  ? 'Online'
                  : props.row.status === 'overdue'
                    ? 'Vencido'
                    : 'Offline'
              "
            />
          </q-td>
        </template>

        <template v-slot:body-cell-ad_status="props">
          <q-td :props="props">
            <q-badge
              :color="props.row.part_of_domain ? 'teal-7' : 'amber-9'"
              :label="
                props.row.part_of_domain
                  ? `No AD (${props.row.domain_name || 'Domínio'})`
                  : `Fora do AD (${props.row.domain_name || 'WORKGROUP'})`
              "
            />
          </q-td>
        </template>

        <template v-slot:body-cell-needs_reboot="props">
          <q-td :props="props">
            <q-badge
              :color="props.row.needs_reboot ? 'orange-9' : 'grey-8'"
              :label="props.row.needs_reboot ? 'Sim (Pendente)' : 'Não'"
            />
          </q-td>
        </template>

        <template v-slot:body-cell-has_patches_pending="props">
          <q-td :props="props">
            <q-badge
              :color="props.row.has_patches_pending ? 'primary' : 'grey-8'"
              :label="props.row.has_patches_pending ? 'Pendente' : 'Em Dia'"
            />
          </q-td>
        </template>
      </q-table>
    </q-card-section>
  </q-card>
</template>

<script>
import { ref, computed, onMounted } from "vue";
import axios from "axios";
import { fetchFleetExecutiveSummary, fleetDomainMap } from "@/api/enhanced";
import { notifySuccess, notifyError } from "@/utils/notify";

export default {
  name: "FleetReportsModal",
  props: {
    initialReportType: {
      type: String,
      default: "all",
    },
  },
  emits: ["close"],
  setup(props) {
    const loading = ref(false);
    const agents = ref([]);
    const selectedReportType = ref(props.initialReportType || "all");
    const selectedClient = ref("Todos");
    const selectedSite = ref("Todos");
    const selectedStatus = ref("all");
    const searchQuery = ref("");

    const reportTypeOptions = [
      { label: "1. Inventário Geral da Frota (Completo)", value: "all" },
      { label: "2. Conformidade Active Directory (No AD vs. Fora do AD)", value: "ad_compliance" },
      { label: "3. Computadores Fora do Domínio AD (Workgroup)", value: "outside_ad" },
      { label: "4. Patches Pendentes & Reinicialização Necessária", value: "patches_reboot" },
      { label: "5. Saúde & Alertas (Verificações com Falha)", value: "health_checks" },
      { label: "6. Computadores Offline / Vencidos", value: "offline_audit" },
    ];

    const statusOptions = [
      { label: "Todos os Status", value: "all" },
      { label: "Apenas Online", value: "online" },
      { label: "Apenas Offline", value: "offline" },
      { label: "Apenas Vencidos (Overdue)", value: "overdue" },
    ];

    const columns = [
      { name: "hostname", label: "Computador (Hostname)", field: "hostname", sortable: true, align: "left" },
      { name: "client_name", label: "Cliente", field: "client_name", sortable: true, align: "left" },
      { name: "site_name", label: "Unidade / Site", field: "site_name", sortable: true, align: "left" },
      { name: "status", label: "Status", field: "status", sortable: true, align: "left" },
      { name: "logged_username", label: "Usuário Logado", field: "logged_username", sortable: true, align: "left" },
      { name: "ad_status", label: "Active Directory / Domínio", field: "domain_name", sortable: true, align: "left" },
      { name: "operating_system", label: "Sistema Operacional", field: "operating_system", sortable: true, align: "left" },
      { name: "local_ips", label: "IP Local (LAN)", field: "local_ips", sortable: true, align: "left" },
      { name: "public_ip", label: "IP Público", field: "public_ip", sortable: true, align: "left" },
      { name: "make_model", label: "Fabricante / Modelo", field: "make_model", sortable: true, align: "left" },
      { name: "serial_number", label: "Nº de Série / Service Tag", field: "serial_number", sortable: true, align: "left" },
      { name: "has_patches_pending", label: "Patches", field: "has_patches_pending", sortable: true, align: "center" },
      { name: "needs_reboot", label: "Reboot", field: "needs_reboot", sortable: true, align: "center" },
      { name: "version", label: "Agente", field: "version", sortable: true, align: "left" },
      { name: "last_seen", label: "Última Resposta", field: "last_seen", sortable: true, align: "left" },
    ];

    async function loadReportData() {
      loading.value = true;
      try {
        await fetchFleetExecutiveSummary().catch(() => {});
        const { data } = await axios.get("/agents/");
        const domainMap = fleetDomainMap.value || {};
        agents.value = (Array.isArray(data) ? data : []).map((a) => {
          const dInfo = domainMap[a.agent_id] || null;
          const partOfDomain = dInfo ? Boolean(dInfo.part_of_domain) : true;
          const domainName = dInfo?.domain || (partOfDomain ? "Domínio" : "WORKGROUP");
          return {
            ...a,
            part_of_domain: partOfDomain,
            domain_name: domainName,
          };
        });
      } catch (e) {
        notifyError("Erro ao carregar dados para o relatório.");
      } finally {
        loading.value = false;
      }
    }

    const clientOptions = computed(() => {
      const set = new Set(agents.value.map((a) => a.client_name).filter(Boolean));
      return ["Todos", ...Array.from(set).sort()];
    });

    const siteOptions = computed(() => {
      const list =
        selectedClient.value === "Todos"
          ? agents.value
          : agents.value.filter((a) => a.client_name === selectedClient.value);
      const set = new Set(list.map((a) => a.site_name).filter(Boolean));
      return ["Todos", ...Array.from(set).sort()];
    });

    const filteredRows = computed(() => {
      const q = (searchQuery.value || "").trim().toLowerCase();
      return agents.value.filter((row) => {
        if (selectedClient.value !== "Todos" && row.client_name !== selectedClient.value) {
          return false;
        }
        if (selectedSite.value !== "Todos" && row.site_name !== selectedSite.value) {
          return false;
        }
        if (selectedStatus.value !== "all" && row.status !== selectedStatus.value) {
          return false;
        }
        if (selectedReportType.value === "outside_ad" && row.part_of_domain !== false) {
          return false;
        }
        if (
          selectedReportType.value === "patches_reboot" &&
          !row.has_patches_pending &&
          !row.needs_reboot
        ) {
          return false;
        }
        if (
          selectedReportType.value === "health_checks" &&
          !row.checks?.has_failing_checks &&
          row.status !== "overdue"
        ) {
          return false;
        }
        if (
          selectedReportType.value === "offline_audit" &&
          row.status === "online"
        ) {
          return false;
        }
        if (q) {
          const hay = [
            row.hostname,
            row.client_name,
            row.site_name,
            row.logged_username,
            row.operating_system,
            row.local_ips,
            row.public_ip,
            row.domain_name,
            row.make_model,
            row.serial_number,
          ]
            .filter(Boolean)
            .join(" ")
            .toLowerCase();
          if (!hay.includes(q)) return false;
        }
        return true;
      });
    });

    const summaryCounts = computed(() => {
      const rows = filteredRows.value;
      return {
        online: rows.filter((r) => r.status === "online").length,
        offline: rows.filter((r) => r.status === "offline").length,
        overdue: rows.filter((r) => r.status === "overdue").length,
        inAd: rows.filter((r) => r.part_of_domain === true).length,
        outsideAd: rows.filter((r) => r.part_of_domain === false).length,
        rebootNeeded: rows.filter((r) => Boolean(r.needs_reboot)).length,
      };
    });

    function exportCSV() {
      const headers = [
        "Hostname",
        "Cliente",
        "Unidade/Site",
        "Status",
        "Usuario Logado",
        "No Dominio AD",
        "Dominio/Workgroup",
        "Sistema Operacional",
        "IP Local",
        "IP Publico",
        "Fabricante/Modelo",
        "Numero de Serie",
        "Patches Pendentes",
        "Reboot Pendente",
        "Versao Agente",
        "Ultima Resposta",
      ];
      const escapeCell = (val) => {
        const s = String(val ?? "").replace(/"/g, '""');
        return `"${s}"`;
      };
      const lines = [headers.map(escapeCell).join(";")];
      for (const r of filteredRows.value) {
        lines.push(
          [
            r.hostname,
            r.client_name,
            r.site_name,
            r.status === "online" ? "Online" : r.status === "overdue" ? "Vencido" : "Offline",
            r.logged_username || "-",
            r.part_of_domain ? "Sim" : "Nao (Fora do AD)",
            r.domain_name || "-",
            r.operating_system || "-",
            r.local_ips || "-",
            r.public_ip || "-",
            r.make_model || "-",
            r.serial_number || "-",
            r.has_patches_pending ? "Sim" : "Nao",
            r.needs_reboot ? "Sim" : "Nao",
            r.version || "-",
            r.last_seen || "-",
          ]
            .map(escapeCell)
            .join(";"),
        );
      }
      const csvContent = "\uFEFF" + lines.join("\r\n");
      const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      const dateStr = new Date().toISOString().slice(0, 10);
      a.href = url;
      a.download = `relatorio-tacticalrmm-${selectedReportType.value}-${dateStr}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      notifySuccess(`Relatório exportado (${filteredRows.value.length} computadores)!`);
    }

    function printReport() {
      const reportTitle =
        reportTypeOptions.find((o) => o.value === selectedReportType.value)?.label ||
        "Relatório da Frota";
      const nowStr = new Date().toLocaleString("pt-BR");
      const rowsHtml = filteredRows.value
        .map(
          (r) => `
          <tr>
            <td><strong>${r.hostname || ""}</strong></td>
            <td>${r.client_name || ""} / ${r.site_name || ""}</td>
            <td>${r.status === "online" ? "Online" : r.status === "overdue" ? "Vencido" : "Offline"}</td>
            <td>${r.logged_username || "-"}</td>
            <td>${r.part_of_domain ? "No AD (" + (r.domain_name || "") + ")" : "Fora do AD (" + (r.domain_name || "WORKGROUP") + ")"}</td>
            <td>${r.operating_system || "-"}</td>
            <td>${r.local_ips || "-"}</td>
            <td>${r.make_model || "-"}</td>
            <td>${r.needs_reboot ? "Sim" : "Não"}</td>
          </tr>`,
        )
        .join("");

      const win = window.open("", "_blank");
      if (!win) {
        notifyError("Permita pop-ups no navegador para imprimir/salvar PDF.");
        return;
      }
      win.document.write(`
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
          <meta charset="utf-8" />
          <title>${reportTitle}</title>
          <style>
            body { font-family: Arial, sans-serif; margin: 20px; color: #111; }
            h1 { font-size: 18px; margin-bottom: 4px; }
            .meta { font-size: 12px; color: #444; margin-bottom: 12px; }
            .kpis { display: flex; gap: 12px; margin-bottom: 14px; font-size: 12px; }
            .kpi { padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px; background: #f8f9fa; }
            table { width: 100%; border-collapse: collapse; font-size: 11px; }
            th, td { border: 1px solid #ccc; padding: 5px 6px; text-align: left; }
            th { background: #eaecef; }
          </style>
        </head>
        <body>
          <h1>Tactical RMM — ${reportTitle}</h1>
          <div class="meta">Gerado em: ${nowStr} | Total de computadores: ${filteredRows.value.length}</div>
          <div class="kpis">
            <div class="kpi"><strong>Online:</strong> ${summaryCounts.value.online}</div>
            <div class="kpi"><strong>Offline:</strong> ${summaryCounts.value.offline}</div>
            <div class="kpi"><strong>Vencidos:</strong> ${summaryCounts.value.overdue}</div>
            <div class="kpi"><strong>No Domínio AD:</strong> ${summaryCounts.value.inAd}</div>
            <div class="kpi"><strong>Fora do AD:</strong> ${summaryCounts.value.outsideAd}</div>
            <div class="kpi"><strong>Reboot Pendente:</strong> ${summaryCounts.value.rebootNeeded}</div>
          </div>
          <table>
            <thead>
              <tr>
                <th>Computador</th>
                <th>Cliente / Unidade</th>
                <th>Status</th>
                <th>Usuário</th>
                <th>Status AD</th>
                <th>Sistema Operacional</th>
                <th>IP Local</th>
                <th>Modelo</th>
                <th>Reboot</th>
              </tr>
            </thead>
            <tbody>${rowsHtml}</tbody>
          </table>
          <script>window.onload = function() { window.print(); };<\/script>
        </body>
        </html>
      `);
      win.document.close();
    }

    onMounted(() => {
      loadReportData();
    });

    return {
      loading,
      selectedReportType,
      selectedClient,
      selectedSite,
      selectedStatus,
      searchQuery,
      reportTypeOptions,
      clientOptions,
      siteOptions,
      statusOptions,
      columns,
      filteredRows,
      summaryCounts,
      loadReportData,
      exportCSV,
      printReport,
    };
  },
};
</script>
