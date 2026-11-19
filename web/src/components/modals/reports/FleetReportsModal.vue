<template>
  <q-card
    class="trmm-reports-card"
    :class="$q.dark.isActive ? 'trmm-reports-card--dark text-white' : 'trmm-reports-card--light text-dark'"
  >
    <!-- Executive Gradient Header -->
    <div class="trmm-rep-header row items-center justify-between wrap q-px-md q-py-sm">
      <div class="row items-center no-wrap" style="gap: 10px; min-width: 240px">
        <div class="trmm-rep-hdr-badge">
          <q-icon name="assessment" size="22px" color="white" />
        </div>
        <div>
          <div class="text-subtitle1 text-weight-bold text-white" style="line-height: 1.2">
            Central de Relatórios Corporativos &amp; Auditoria de TI
          </div>
          <div class="text-caption" style="color: rgba(226, 232, 240, 0.8); line-height: 1.2">
            {{ activeReportMeta.label }} &bull; Escopo: {{ scopeLabel }}
          </div>
        </div>
      </div>

      <div class="row items-center wrap" style="gap: 8px">
        <q-btn
          dense
          flat
          no-caps
          icon="refresh"
          label="Atualizar"
          color="white"
          class="trmm-rep-hdr-btn"
          :loading="loading"
          @click="loadReportData(true)"
        >
          <q-tooltip>Recarregar dados em tempo real (sem cache)</q-tooltip>
        </q-btn>

        <q-btn
          dense
          unelevated
          no-caps
          color="teal-6"
          text-color="white"
          icon="download"
          :label="`Exportar Excel (${exportRowCount})`"
          class="q-px-sm"
          style="border-radius: 7px"
          :disable="exportRowCount === 0"
          @click="exportCSV"
        />

        <q-btn
          dense
          unelevated
          no-caps
          color="indigo-5"
          text-color="white"
          icon="print"
          :label="`Imprimir / PDF (${exportRowCount})`"
          class="q-px-sm"
          style="border-radius: 7px"
          :disable="exportRowCount === 0"
          @click="printReport"
        />

        <q-btn dense flat round icon="close" color="white" @click="$emit('close')">
          <q-tooltip>Fechar</q-tooltip>
        </q-btn>
      </div>
    </div>

    <!-- Filters & Quick Unit Pills -->
    <div
      class="trmm-rep-filters q-px-md q-pt-sm q-pb-sm"
      :class="$q.dark.isActive ? 'trmm-rep-filters--dark' : 'trmm-rep-filters--light'"
    >
      <!-- Quick Unit Scope Pills -->
      <div class="row items-center wrap q-mb-sm" style="gap: 6px">
        <span class="text-caption text-weight-bold text-grey-5 q-mr-xs">Empresas / Unidades:</span>
        <q-btn
          dense
          no-caps
          unelevated
          size="sm"
          class="trmm-unit-pill"
          :class="{ 'trmm-unit-pill--active': selectedClient === 'Todos' && selectedSite === 'Todos' }"
          @click="selectUnitScope('Todos', 'Todos')"
        >
          <span>Todas</span>
          <span class="trmm-unit-pill-cnt">{{ allRows.length }}</span>
        </q-btn>
        <q-btn
          v-for="u in unitQuickPills"
          :key="u.key"
          dense
          no-caps
          unelevated
          size="sm"
          class="trmm-unit-pill"
          :class="{ 'trmm-unit-pill--active': selectedClient === u.client && selectedSite === u.site }"
          @click="selectUnitScope(u.client, u.site)"
        >
          <q-icon name="apartment" size="13px" class="q-mr-xs" :color="selectedClient === u.client && selectedSite === u.site ? 'white' : getEntityBadgeColor(u.client)" />
          <span>{{ u.client }} / {{ u.site }}</span>
          <span class="trmm-unit-pill-cnt">{{ u.count }}</span>
        </q-btn>
      </div>

      <!-- Filter Controls Row -->
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
              <q-icon :name="activeReportMeta.icon" color="primary" size="18px" />
            </template>
          </q-select>
        </div>

        <div class="col-6 col-md-2">
          <q-select
            v-model="selectedClient"
            :options="clientOptions"
            dense
            outlined
            label="Empresa / Cliente"
            @update:model-value="selectedSite = 'Todos'"
          />
        </div>

        <div class="col-6 col-md-2">
          <q-select
            v-model="selectedSite"
            :options="siteOptions"
            dense
            outlined
            label="Unidade / Filial"
          />
        </div>

        <div v-if="selectedReportType !== 'unit_summary'" class="col-6 col-md-2">
          <q-select
            v-model="selectedStatus"
            :options="statusOptions"
            emit-value
            map-options
            dense
            outlined
            label="Monitoramento / Status"
          />
        </div>

        <div :class="selectedReportType === 'unit_summary' ? 'col-12 col-md-5' : 'col-6 col-md-3'">
          <q-input
            v-model="searchQuery"
            dense
            outlined
            clearable
            :label="
              selectedReportType === 'unit_summary'
                ? 'Filtrar empresa ou unidade...'
                : 'Buscar patrimônio, hostname, IP, modelo, setor...'
            "
          >
            <template v-slot:prepend>
              <q-icon name="search" color="primary" size="18px" />
            </template>
          </q-input>
        </div>
      </div>

      <!-- Context-Specific Accuracy Banner & Toggle for AD Reports -->
      <div
        v-if="selectedReportType === 'ad_compliance' || selectedReportType === 'outside_ad'"
        class="row items-center justify-between wrap q-mt-xs q-px-sm q-py-xs trmm-accuracy-bar"
        :class="$q.dark.isActive ? 'trmm-accuracy-bar--dark' : 'trmm-accuracy-bar--light'"
      >
        <div class="row items-center no-wrap text-caption" style="gap: 6px">
          <q-icon name="verified" size="16px" color="teal-4" />
          <span>
            Precisão AD: roteadores, switches, impressoras, CFTV e equipamentos médicos são excluídos automaticamente deste relatório (apenas estações/servidores Windows).
          </span>
        </div>
        <q-toggle
          v-model="includeAgentlessPcsInAd"
          dense
          size="sm"
          color="amber-7"
          label="Incluir Estações LAN sem Agente (Workgroup)"
          class="text-caption"
        />
      </div>

      <!-- Precision KPI Summary Strip -->
      <div class="row q-col-gutter-xs q-mt-xs">
        <div class="col-6 col-sm-4 col-md-2">
          <div class="trmm-kpi-mini" :class="$q.dark.isActive ? 'trmm-kpi-mini--dark' : 'trmm-kpi-mini--light'">
            <div class="trmm-kpi-mini-lbl">Total no Escopo</div>
            <div class="row items-baseline justify-between">
              <span class="trmm-kpi-mini-val text-primary">{{ kpiStats.total }}</span>
              <span class="text-caption text-grey-5">{{ kpiStats.withAgent }} c/ agente</span>
            </div>
          </div>
        </div>

        <div class="col-6 col-sm-4 col-md-2">
          <div class="trmm-kpi-mini" :class="$q.dark.isActive ? 'trmm-kpi-mini--dark' : 'trmm-kpi-mini--light'">
            <div class="trmm-kpi-mini-lbl">Agentes Monitorados</div>
            <div class="row items-center" style="gap: 6px">
              <span class="trmm-kpi-mini-val text-positive">{{ kpiStats.online }}</span>
              <span class="text-caption text-grey-5">on</span>
              <span class="text-caption text-warning text-weight-bold">{{ kpiStats.offline }} off</span>
              <span v-if="kpiStats.overdue > 0" class="text-caption text-deep-orange text-weight-bold">{{ kpiStats.overdue }} venc</span>
            </div>
          </div>
        </div>

        <div class="col-6 col-sm-4 col-md-2">
          <div class="trmm-kpi-mini" :class="$q.dark.isActive ? 'trmm-kpi-mini--dark' : 'trmm-kpi-mini--light'">
            <div class="trmm-kpi-mini-lbl">Sem Agente / Rede &amp; Clín.</div>
            <div class="row items-baseline justify-between">
              <span class="trmm-kpi-mini-val text-cyan-4">{{ kpiStats.agentless }}</span>
              <span class="text-caption text-grey-5">{{ kpiStats.networkAndMedical }} rede/clín.</span>
            </div>
          </div>
        </div>

        <div class="col-6 col-sm-4 col-md-2">
          <div class="trmm-kpi-mini" :class="$q.dark.isActive ? 'trmm-kpi-mini--dark' : 'trmm-kpi-mini--light'">
            <div class="trmm-kpi-mini-lbl">Active Directory (PCs)</div>
            <div class="row items-center" style="gap: 8px">
              <span class="trmm-kpi-mini-val text-teal-4">{{ kpiStats.inAd }}</span>
              <span class="text-caption text-grey-5">AD</span>
              <span class="text-caption text-amber-5 text-weight-bold">{{ kpiStats.outsideAd }} fora</span>
            </div>
          </div>
        </div>

        <div class="col-6 col-sm-4 col-md-2">
          <div class="trmm-kpi-mini" :class="$q.dark.isActive ? 'trmm-kpi-mini--dark' : 'trmm-kpi-mini--light'">
            <div class="trmm-kpi-mini-lbl">Patches / Reboot</div>
            <div class="row items-center" style="gap: 8px">
              <span class="trmm-kpi-mini-val text-light-blue-4">{{ kpiStats.patchesPending }}</span>
              <span class="text-caption text-grey-5">patch</span>
              <span class="text-caption text-orange-4 text-weight-bold">{{ kpiStats.rebootNeeded }} reb</span>
            </div>
          </div>
        </div>

        <div class="col-6 col-sm-4 col-md-2">
          <div class="trmm-kpi-mini" :class="$q.dark.isActive ? 'trmm-kpi-mini--dark' : 'trmm-kpi-mini--light'">
            <div class="trmm-kpi-mini-lbl">Com Nº Patrimônio</div>
            <div class="row items-baseline justify-between">
              <span class="trmm-kpi-mini-val text-emerald-4" style="color: #34d399">{{ kpiStats.withPatrimonio }}</span>
              <span class="text-caption text-grey-5">{{ kpiStats.patrimonioPct }}%</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <q-separator />

    <!-- Report Table Container (Single-Layer Sticky Scroll) -->
    <div class="col q-pa-sm overflow-hidden" style="flex: 1 1 0%; min-height: 0; display: flex; flex-direction: column">
      <!-- Mode A: Executive Per-Unit Summary Table -->
      <q-table
        v-if="selectedReportType === 'unit_summary'"
        :rows="unitSummaryRows"
        :columns="unitSummaryColumns"
        row-key="key"
        dense
        flat
        bordered
        :loading="loading"
        :pagination="{ rowsPerPage: 0 }"
        :rows-per-page-options="[0]"
        hide-bottom
        class="trmm-fill-table trmm-rep-table"
        :table-class="$q.dark.isActive ? 'table-bgcolor-dark' : 'table-bgcolor'"
      >
        <template v-slot:body-cell-client_name="props">
          <q-td :props="props">
            <q-badge
              v-if="!props.row.isTotal"
              :color="getEntityBadgeColor(props.row.client_name)"
              text-color="white"
              class="text-weight-bold q-px-sm"
            >
              {{ props.row.client_name }}
            </q-badge>
            <strong v-else class="text-primary">{{ props.row.client_name }}</strong>
          </q-td>
        </template>

        <template v-slot:body-cell-site_name="props">
          <q-td :props="props">
            <q-badge
              v-if="!props.row.isTotal"
              outline
              :color="getEntityBadgeColor(props.row.site_name)"
              class="text-weight-bold q-px-sm"
            >
              {{ props.row.site_name }}
            </q-badge>
            <strong v-else>{{ props.row.site_name }}</strong>
          </q-td>
        </template>

        <template v-slot:body-cell-total="props">
          <q-td :props="props">
            <strong :class="props.row.isTotal ? 'text-primary text-subtitle2' : ''">
              {{ props.row.total }}
            </strong>
          </q-td>
        </template>

        <template v-slot:body-cell-online="props">
          <q-td :props="props">
            <span class="text-positive text-weight-bold">{{ props.row.online }}</span>
          </q-td>
        </template>

        <template v-slot:body-cell-offline_overdue="props">
          <q-td :props="props">
            <span :class="props.row.offline_overdue > 0 ? 'text-warning text-weight-bold' : 'text-grey-6'">
              {{ props.row.offline_overdue }}
            </span>
          </q-td>
        </template>

        <template v-slot:body-cell-outside_ad="props">
          <q-td :props="props">
            <span :class="props.row.outside_ad > 0 ? 'text-amber-5 text-weight-bold' : 'text-grey-6'">
              {{ props.row.outside_ad }}
            </span>
          </q-td>
        </template>

        <template v-slot:body-cell-patrimonio_pct="props">
          <q-td :props="props">
            <q-badge
              rounded
              :color="props.row.patrimonio_pct >= 80 ? 'positive' : props.row.patrimonio_pct > 0 ? 'amber-8' : 'grey-8'"
              text-color="white"
            >
              {{ props.row.with_patrimonio }} / {{ props.row.total }} ({{ props.row.patrimonio_pct }}%)
            </q-badge>
          </q-td>
        </template>
      </q-table>

      <!-- Mode B: Precision Asset / Compliance Detail Table -->
      <q-table
        v-else
        :rows="filteredRows"
        :columns="columns"
        row-key="row_key"
        dense
        flat
        bordered
        :loading="loading"
        :pagination="{ rowsPerPage: 50, sortBy: 'hostname' }"
        :rows-per-page-options="[25, 50, 100, 0]"
        binary-state-sort
        no-data-label="Nenhum equipamento encontrado para este relatório e filtro."
        class="trmm-fill-table trmm-rep-table"
        :table-class="$q.dark.isActive ? 'table-bgcolor-dark' : 'table-bgcolor'"
      >
        <template v-slot:body-cell-patrimonio="props">
          <q-td :props="props">
            <q-badge v-if="props.row.patrimonio" color="teal-7" text-color="white" class="text-weight-bold">
              {{ props.row.patrimonio }}
            </q-badge>
            <span v-else class="text-caption text-grey-6">—</span>
          </q-td>
        </template>

        <template v-slot:body-cell-client_name="props">
          <q-td :props="props">
            <div class="row items-center no-wrap" style="gap: 4px">
              <q-badge
                :color="getEntityBadgeColor(props.row.client_name)"
                text-color="white"
                class="text-weight-bold"
              >
                {{ props.row.client_name }}
              </q-badge>
              <q-badge
                outline
                :color="getEntityBadgeColor(props.row.site_name)"
                class="text-weight-bold"
              >
                {{ props.row.site_name }}
              </q-badge>
            </div>
          </q-td>
        </template>

        <template v-slot:body-cell-category="props">
          <q-td :props="props">
            <q-badge
              :color="categoryColor(props.row.category)"
              text-color="white"
              style="border-radius: 5px; font-size: 11px"
            >
              {{ props.row.category_label }}
            </q-badge>
          </q-td>
        </template>

        <template v-slot:body-cell-monitor_status="props">
          <q-td :props="props">
            <q-badge
              v-if="props.row.monitor_status === 'online'"
              color="positive"
              text-color="white"
              label="Online"
            />
            <q-badge
              v-else-if="props.row.monitor_status === 'overdue'"
              color="deep-orange"
              text-color="white"
              label="Vencido"
            />
            <q-badge
              v-else-if="props.row.monitor_status === 'offline'"
              color="warning"
              text-color="black"
              label="Offline"
            />
            <q-badge
              v-else
              color="blue-grey-7"
              text-color="white"
              label="Inventário LAN"
            />
          </q-td>
        </template>

        <template v-slot:body-cell-ad_status="props">
          <q-td :props="props">
            <q-badge
              v-if="props.row.ad_state === 'in_ad'"
              color="teal-7"
              text-color="white"
              :label="`No AD (${props.row.domain_name})`"
            />
            <q-badge
              v-else-if="props.row.ad_state === 'outside_ad'"
              color="amber-9"
              text-color="white"
              :label="`Fora do AD (${props.row.domain_name})`"
            />
            <q-badge
              v-else-if="props.row.ad_state === 'outside_ad_lan'"
              color="orange-9"
              text-color="white"
              label="Workgroup (Sem Agente)"
            />
            <q-badge
              v-else-if="props.row.ad_state === 'unknown'"
              color="grey-7"
              text-color="white"
              label="Não Verificado"
            />
            <span v-else class="text-caption text-grey-6">N/A</span>
          </q-td>
        </template>

        <template v-slot:body-cell-has_patches_pending="props">
          <q-td :props="props">
            <q-badge
              v-if="props.row.has_patches_pending === true"
              color="primary"
              text-color="white"
              label="Pendente"
            />
            <q-badge
              v-else-if="props.row.has_patches_pending === false"
              color="positive"
              outline
              label="Em Dia"
            />
            <span v-else class="text-caption text-grey-6">N/A</span>
          </q-td>
        </template>

        <template v-slot:body-cell-needs_reboot="props">
          <q-td :props="props">
            <q-badge
              v-if="props.row.needs_reboot === true"
              color="orange-9"
              text-color="white"
              label="Sim (Pendente)"
            />
            <q-badge
              v-else-if="props.row.needs_reboot === false"
              color="grey-7"
              outline
              label="Não"
            />
            <span v-else class="text-caption text-grey-6">N/A</span>
          </q-td>
        </template>

        <template v-slot:body-cell-version="props">
          <q-td :props="props">
            <span v-if="props.row.has_agent" class="text-caption">v{{ props.row.version }}</span>
            <span v-else class="text-caption text-grey-6">Sem Agente</span>
          </q-td>
        </template>
      </q-table>
    </div>
  </q-card>
</template>

<script>
import { ref, computed, watch, onMounted } from "vue";
import axios from "axios";
import {
  fetchFleetExecutiveSummary,
  fleetDomainMap,
  fetchInventoryAssets,
  getEntityBadgeColor,
} from "@/api/enhanced";
import { notifySuccess, notifyError } from "@/utils/notify";

const CATEGORY_LABELS = {
  ativo_monitorado: "Agente Tactical",
  estacao_sem_agente: "Estação Sem Agente",
  ativo_rede: "Ativo de Rede",
  passivo_rede: "Passivo de Rede",
  equipamento_medico: "Equipamento Médico",
  impressora_periferico: "Impressora / CFTV",
};

const CATEGORY_COLORS = {
  ativo_monitorado: "primary",
  estacao_sem_agente: "amber-9",
  ativo_rede: "teal-7",
  passivo_rede: "indigo-6",
  equipamento_medico: "deep-purple-6",
  impressora_periferico: "cyan-8",
};

function formatDateTimePt(isoVal) {
  if (!isoVal) return "—";
  const d = new Date(isoVal);
  if (Number.isNaN(d.getTime())) return String(isoVal);
  return d.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function cleanMakeModel(manuf, model, fallback) {
  const m1 = String(manuf || "").trim();
  const m2 = String(model || "").trim();
  if (m1 || m2) {
    if (m1 && m2 && m2.toLowerCase().startsWith(m1.toLowerCase())) {
      return m2;
    }
    return `${m1} ${m2}`.trim();
  }
  const fb = String(fallback || "").trim();
  if (!fb || fb.toLowerCase() === "unknown make/model") return "—";
  return fb;
}

function cleanSerial(val) {
  const s = String(val || "").trim();
  if (!s || s.toLowerCase() === "n/a" || s.toLowerCase() === "unknown" || s.toLowerCase() === "to be filled by o.e.m.") {
    return "—";
  }
  return s;
}

export default {
  name: "FleetReportsModal",
  props: {
    initialReportType: {
      type: String,
      default: "all",
    },
    initialClient: {
      type: String,
      default: "Todos",
    },
    initialSite: {
      type: String,
      default: "Todos",
    },
  },
  emits: ["close"],
  setup(props) {
    const loading = ref(false);
    const allRows = ref([]);
    const selectedReportType = ref(props.initialReportType || "all");
    const selectedClient = ref(props.initialClient || "Todos");
    const selectedSite = ref(props.initialSite || "Todos");
    const selectedStatus = ref("all");
    const searchQuery = ref("");
    const includeAgentlessPcsInAd = ref(true);

    watch(
      () => props.initialReportType,
      (val) => {
        if (val) selectedReportType.value = val;
      },
    );

    const reportTypeOptions = [
      { label: "1. Inventário Geral da Frota (Completo)", value: "all", icon: "assessment" },
      { label: "2. Resumo Executivo por Empresa & Unidade", value: "unit_summary", icon: "apartment" },
      { label: "3. Conformidade Active Directory (AD vs. Workgroup)", value: "ad_compliance", icon: "domain" },
      { label: "4. Computadores Fora do Domínio AD (Workgroup)", value: "outside_ad", icon: "domain_disabled" },
      { label: "5. Patches Pendentes & Reinicialização Necessária", value: "patches_reboot", icon: "system_update_alt" },
      { label: "6. Saúde & Alertas (Checks com Falha / Vencidos)", value: "health_checks", icon: "health_and_safety" },
      { label: "7. Agentes Offline / Vencidos (Monitorados)", value: "offline_audit", icon: "cloud_off" },
    ];

    const statusOptions = [
      { label: "Todos os Status", value: "all" },
      { label: "Com Agente — Online", value: "online" },
      { label: "Com Agente — Offline", value: "offline" },
      { label: "Com Agente — Vencidos (Overdue)", value: "overdue" },
      { label: "Com Agente — Todos Monitorados", value: "with_agent" },
      { label: "Sem Agente (Inventário LAN / Rede / Clínico)", value: "agentless" },
    ];

    const activeReportMeta = computed(
      () =>
        reportTypeOptions.find((o) => o.value === selectedReportType.value) ||
        reportTypeOptions[0],
    );

    const columns = [
      { name: "patrimonio", label: "Patrimônio", field: "patrimonio", sortable: true, align: "left" },
      { name: "hostname", label: "Equipamento / Hostname", field: "hostname", sortable: true, align: "left" },
      { name: "client_name", label: "Empresa / Unidade", field: "client_name", sortable: true, align: "left" },
      { name: "category", label: "Classificação", field: "category_label", sortable: true, align: "left" },
      { name: "sector_location", label: "Setor / Local", field: "sector_location", sortable: true, align: "left" },
      { name: "monitor_status", label: "Status", field: "monitor_status_label", sortable: true, align: "left" },
      { name: "ad_status", label: "Active Directory", field: "ad_label", sortable: true, align: "left" },
      { name: "logged_username", label: "Usuário", field: "logged_username", sortable: true, align: "left" },
      { name: "operating_system", label: "SO / Função Clínica", field: "operating_system", sortable: true, align: "left" },
      { name: "local_ips", label: "IP Local (LAN)", field: "local_ips", sortable: true, align: "left" },
      { name: "make_model", label: "Fabricante / Modelo", field: "make_model", sortable: true, align: "left" },
      { name: "serial_number", label: "Nº de Série", field: "serial_number", sortable: true, align: "left" },
      { name: "has_patches_pending", label: "Patches", field: "patches_label", sortable: true, align: "center" },
      { name: "needs_reboot", label: "Reboot", field: "reboot_label", sortable: true, align: "center" },
      { name: "version", label: "Agente", field: "version", sortable: true, align: "left" },
      { name: "last_seen_formatted", label: "Última Resposta", field: "last_seen_formatted", sortable: true, align: "left" },
    ];

    const unitSummaryColumns = [
      { name: "client_name", label: "Empresa / Cliente", field: "client_name", sortable: true, align: "left" },
      { name: "site_name", label: "Unidade / Filial", field: "site_name", sortable: true, align: "left" },
      { name: "total", label: "Total", field: "total", sortable: true, align: "right" },
      { name: "with_agent", label: "Com Agente", field: "with_agent", sortable: true, align: "right" },
      { name: "online", label: "Online", field: "online", sortable: true, align: "right" },
      { name: "offline_overdue", label: "Off / Venc.", field: "offline_overdue", sortable: true, align: "right" },
      { name: "agentless", label: "Sem Agente", field: "agentless", sortable: true, align: "right" },
      { name: "network", label: "Rede", field: "network", sortable: true, align: "right" },
      { name: "medical", label: "Médicos", field: "medical", sortable: true, align: "right" },
      { name: "printers", label: "Impr./CFTV", field: "printers", sortable: true, align: "right" },
      { name: "in_ad", label: "No AD", field: "in_ad", sortable: true, align: "right" },
      { name: "outside_ad", label: "Fora AD (PCs)", field: "outside_ad", sortable: true, align: "right" },
      { name: "patches_pending", label: "Patches", field: "patches_pending", sortable: true, align: "right" },
      { name: "reboot_needed", label: "Reboot", field: "reboot_needed", sortable: true, align: "right" },
      { name: "patrimonio_pct", label: "Patrimônio", field: "patrimonio_pct", sortable: true, align: "center" },
    ];

    function categoryColor(cat) {
      return CATEGORY_COLORS[cat] || "blue-grey-7";
    }

    function selectUnitScope(client, site) {
      selectedClient.value = client;
      selectedSite.value = site;
    }

    async function loadReportData(force = false) {
      loading.value = true;
      try {
        const [, agentsRes, invRes] = await Promise.all([
          fetchFleetExecutiveSummary(force).catch(() => null),
          axios.get("/agents/"),
          fetchInventoryAssets().catch(() => null),
        ]);

        const invByAgent = {};
        const standaloneAssets = [];
        if (invRes && Array.isArray(invRes.items)) {
          for (const item of invRes.items) {
            if (item.agent_id) {
              invByAgent[item.agent_id] = item;
            } else {
              standaloneAssets.push(item);
            }
          }
        }

        const agentsList = Array.isArray(agentsRes?.data) ? agentsRes.data : [];
        const domainMap = fleetDomainMap.value || {};
        const merged = [];

        for (const a of agentsList) {
          const inv = invByAgent[a.agent_id] || null;
          const rawVer = String(a.version || "").trim();
          const hasAgent = inv
            ? Boolean(inv.has_agent)
            : rawVer !== "" && rawVer !== "0.1.0";

          const category =
            inv?.category || (hasAgent ? "ativo_monitorado" : "estacao_sem_agente");
          const categoryLabel =
            inv?.category_label || CATEGORY_LABELS[category] || category;

          const monitorStatus = hasAgent ? a.status || "offline" : "agentless";
          const monitorStatusLabel =
            monitorStatus === "online"
              ? "Online"
              : monitorStatus === "overdue"
                ? "Vencido"
                : monitorStatus === "offline"
                  ? "Offline"
                  : "Inventário LAN";

          const platLower = String(a.plat || "windows").toLowerCase();
          const isWindowsComputer =
            (category === "ativo_monitorado" || category === "estacao_sem_agente") &&
            platLower === "windows";

          const dInfo = domainMap[a.agent_id] || null;
          let adState = "na";
          let domainName = "—";
          let adLabel = "N/A";

          if (isWindowsComputer) {
            if (hasAgent) {
              if (dInfo && typeof dInfo.part_of_domain === "boolean") {
                if (dInfo.part_of_domain) {
                  adState = "in_ad";
                  domainName = dInfo.domain || "AD";
                  adLabel = `No AD (${domainName})`;
                } else {
                  adState = "outside_ad";
                  domainName = dInfo.domain || "WORKGROUP";
                  adLabel = `Fora do AD (${domainName})`;
                }
              } else {
                adState = "unknown";
                domainName = "—";
                adLabel = "Não Verificado";
              }
            } else {
              adState = "outside_ad_lan";
              domainName = "WORKGROUP";
              adLabel = "Workgroup (Sem Agente)";
            }
          }

          const patchesPending = hasAgent ? Boolean(a.has_patches_pending) : null;
          const needsReboot = hasAgent ? Boolean(a.needs_reboot) : null;
          const hasFailingChecks = hasAgent ? Boolean(a.checks?.has_failing_checks) : false;

          const makeModel = cleanMakeModel(
            inv?.manufacturer,
            inv?.model_name,
            a.make_model,
          );
          const osDisplay = hasAgent
            ? a.operating_system || inv?.operating_system || "—"
            : inv?.operating_system || inv?.asset_subtype || "Dispositivo LAN";
          const localIp = (inv?.ip_address || a.local_ips || "").trim() || "—";
          const serialNum = cleanSerial(inv?.serial_number || a.serial_number);
          const loggedUser = hasAgent
            ? (a.logged_username && a.logged_username !== "-" ? a.logged_username : "—")
            : "—";

          merged.push({
            row_key: `agent:${a.agent_id}`,
            agent_id: a.agent_id,
            has_agent: hasAgent,
            hostname: a.hostname || inv?.name || "—",
            client_name: a.client_name || inv?.client_name || "—",
            site_name: a.site_name || inv?.site_name || "—",
            category,
            category_label: categoryLabel,
            patrimonio: (inv?.patrimonio || "").trim(),
            sector_location: (inv?.sector_location || "").trim() || "—",
            responsible: (inv?.responsible || "").trim(),
            monitor_status: monitorStatus,
            monitor_status_label: monitorStatusLabel,
            ad_state: adState,
            domain_name: domainName,
            ad_label: adLabel,
            is_windows_computer: isWindowsComputer,
            logged_username: loggedUser,
            operating_system: osDisplay,
            local_ips: localIp,
            public_ip: hasAgent ? a.public_ip || "—" : "—",
            make_model: makeModel,
            serial_number: serialNum,
            has_patches_pending: patchesPending,
            patches_label:
              patchesPending === true ? "Pendente" : patchesPending === false ? "Em Dia" : "N/A",
            needs_reboot: needsReboot,
            reboot_label:
              needsReboot === true ? "Sim (Pendente)" : needsReboot === false ? "Não" : "N/A",
            has_failing_checks: hasFailingChecks,
            failing_checks_count: hasAgent ? Number(a.checks?.failing || 0) : 0,
            version: hasAgent ? rawVer : "",
            last_seen: hasAgent ? a.last_seen || "" : "",
            last_seen_formatted: hasAgent ? formatDateTimePt(a.last_seen) : "—",
            notes: (inv?.notes || "").trim(),
          });
        }

        // Also include standalone manual/passive inventory items so counts match Inventory 100%
        for (const item of standaloneAssets) {
          const category = item.category || "passivo_rede";
          const isLanPc = category === "estacao_sem_agente";
          merged.push({
            row_key: item.row_key || `asset:${item.asset_id}`,
            agent_id: null,
            has_agent: false,
            hostname: item.name || "—",
            client_name: item.client_name || "—",
            site_name: item.site_name || "—",
            category,
            category_label: item.category_label || CATEGORY_LABELS[category] || category,
            patrimonio: (item.patrimonio || "").trim(),
            sector_location: (item.sector_location || "").trim() || "—",
            responsible: (item.responsible || "").trim(),
            monitor_status: "agentless",
            monitor_status_label: "Inventário LAN",
            ad_state: isLanPc ? "outside_ad_lan" : "na",
            domain_name: isLanPc ? "WORKGROUP" : "—",
            ad_label: isLanPc ? "Workgroup (Sem Agente)" : "N/A",
            is_windows_computer: isLanPc,
            logged_username: "—",
            operating_system: item.operating_system || item.asset_subtype || "—",
            local_ips: (item.ip_address || "").trim() || "—",
            public_ip: "—",
            make_model: cleanMakeModel(item.manufacturer, item.model_name, ""),
            serial_number: cleanSerial(item.serial_number),
            has_patches_pending: null,
            patches_label: "N/A",
            needs_reboot: null,
            reboot_label: "N/A",
            has_failing_checks: false,
            failing_checks_count: 0,
            version: "",
            last_seen: "",
            last_seen_formatted: "—",
            notes: (item.notes || "").trim(),
          });
        }

        allRows.value = merged;
      } catch (e) {
        notifyError("Erro ao carregar dados para o relatório.");
      } finally {
        loading.value = false;
      }
    }

    const clientOptions = computed(() => {
      const set = new Set(allRows.value.map((a) => a.client_name).filter((v) => v && v !== "—"));
      return ["Todos", ...Array.from(set).sort((a, b) => a.localeCompare(b))];
    });

    const siteOptions = computed(() => {
      const list =
        selectedClient.value === "Todos"
          ? allRows.value
          : allRows.value.filter((a) => a.client_name === selectedClient.value);
      const set = new Set(list.map((a) => a.site_name).filter((v) => v && v !== "—"));
      return ["Todos", ...Array.from(set).sort((a, b) => a.localeCompare(b))];
    });

    const unitQuickPills = computed(() => {
      const counts = new Map();
      for (const r of allRows.value) {
        const key = `${r.client_name}||${r.site_name}`;
        if (!counts.has(key)) {
          counts.set(key, { key, client: r.client_name, site: r.site_name, count: 0 });
        }
        counts.get(key).count += 1;
      }
      return Array.from(counts.values()).sort((a, b) =>
        `${a.client}/${a.site}`.localeCompare(`${b.client}/${b.site}`),
      );
    });

    const scopeLabel = computed(() => {
      if (selectedClient.value !== "Todos" && selectedSite.value !== "Todos") {
        return `${selectedClient.value} / ${selectedSite.value}`;
      }
      if (selectedClient.value !== "Todos") {
        return `${selectedClient.value} (Todas as Unidades)`;
      }
      if (selectedSite.value !== "Todos") {
        return `Unidade: ${selectedSite.value}`;
      }
      return "Todas as Empresas e Unidades";
    });

    const unitScopedRows = computed(() => {
      return allRows.value.filter((row) => {
        if (selectedClient.value !== "Todos" && row.client_name !== selectedClient.value) {
          return false;
        }
        if (selectedSite.value !== "Todos" && row.site_name !== selectedSite.value) {
          return false;
        }
        return true;
      });
    });

    const filteredRows = computed(() => {
      const q = (searchQuery.value || "").trim().toLowerCase();
      return unitScopedRows.value.filter((row) => {
        if (selectedStatus.value === "with_agent") {
          if (!row.has_agent) return false;
        } else if (selectedStatus.value !== "all" && row.monitor_status !== selectedStatus.value) {
          return false;
        }

        if (selectedReportType.value === "ad_compliance") {
          if (!row.is_windows_computer) return false;
          if (!includeAgentlessPcsInAd.value && !row.has_agent) return false;
        } else if (selectedReportType.value === "outside_ad") {
          if (!row.is_windows_computer) return false;
          if (includeAgentlessPcsInAd.value) {
            if (row.ad_state !== "outside_ad" && row.ad_state !== "outside_ad_lan") return false;
          } else if (row.ad_state !== "outside_ad") {
            return false;
          }
        } else if (selectedReportType.value === "patches_reboot") {
          if (!row.has_agent) return false;
          if (!row.has_patches_pending && !row.needs_reboot) return false;
        } else if (selectedReportType.value === "health_checks") {
          if (!row.has_agent) return false;
          if (!row.has_failing_checks && row.monitor_status !== "overdue") return false;
        } else if (selectedReportType.value === "offline_audit") {
          if (!row.has_agent) return false;
          if (row.monitor_status !== "offline" && row.monitor_status !== "overdue") return false;
        }

        if (q) {
          const hay = [
            row.hostname,
            row.client_name,
            row.site_name,
            row.category_label,
            row.logged_username,
            row.operating_system,
            row.local_ips,
            row.public_ip,
            row.domain_name,
            row.ad_label,
            row.make_model,
            row.serial_number,
            row.patrimonio,
            row.sector_location,
            row.notes,
          ]
            .filter(Boolean)
            .join(" ")
            .toLowerCase();
          if (!hay.includes(q)) return false;
        }
        return true;
      });
    });

    const unitSummaryRows = computed(() => {
      const q = (searchQuery.value || "").trim().toLowerCase();
      const map = new Map();

      for (const r of unitScopedRows.value) {
        if (q) {
          const unitText = `${r.client_name} ${r.site_name}`.toLowerCase();
          if (!unitText.includes(q)) continue;
        }
        const key = `${r.client_name}||${r.site_name}`;
        if (!map.has(key)) {
          map.set(key, {
            key,
            client_name: r.client_name,
            site_name: r.site_name,
            total: 0,
            with_agent: 0,
            online: 0,
            offline: 0,
            overdue: 0,
            offline_overdue: 0,
            agentless: 0,
            network: 0,
            medical: 0,
            printers: 0,
            in_ad: 0,
            outside_ad: 0,
            patches_pending: 0,
            reboot_needed: 0,
            with_patrimonio: 0,
            patrimonio_pct: 0,
            isTotal: false,
          });
        }
        const g = map.get(key);
        g.total += 1;
        if (r.has_agent) {
          g.with_agent += 1;
          if (r.monitor_status === "online") g.online += 1;
          else if (r.monitor_status === "overdue") {
            g.overdue += 1;
            g.offline_overdue += 1;
          } else {
            g.offline += 1;
            g.offline_overdue += 1;
          }
          if (r.has_patches_pending) g.patches_pending += 1;
          if (r.needs_reboot) g.reboot_needed += 1;
        } else {
          g.agentless += 1;
        }
        if (r.category === "ativo_rede" || r.category === "passivo_rede") g.network += 1;
        if (r.category === "equipamento_medico") g.medical += 1;
        if (r.category === "impressora_periferico") g.printers += 1;
        if (r.ad_state === "in_ad") g.in_ad += 1;
        if (r.ad_state === "outside_ad" || r.ad_state === "outside_ad_lan") g.outside_ad += 1;
        if (r.patrimonio) g.with_patrimonio += 1;
      }

      const list = Array.from(map.values())
        .map((g) => ({
          ...g,
          patrimonio_pct: g.total > 0 ? Math.round((g.with_patrimonio / g.total) * 100) : 0,
        }))
        .sort((a, b) =>
          `${a.client_name}/${a.site_name}`.localeCompare(`${b.client_name}/${b.site_name}`),
        );

      if (list.length > 1) {
        const totals = list.reduce(
          (acc, g) => ({
            ...acc,
            total: acc.total + g.total,
            with_agent: acc.with_agent + g.with_agent,
            online: acc.online + g.online,
            offline: acc.offline + g.offline,
            overdue: acc.overdue + g.overdue,
            offline_overdue: acc.offline_overdue + g.offline_overdue,
            agentless: acc.agentless + g.agentless,
            network: acc.network + g.network,
            medical: acc.medical + g.medical,
            printers: acc.printers + g.printers,
            in_ad: acc.in_ad + g.in_ad,
            outside_ad: acc.outside_ad + g.outside_ad,
            patches_pending: acc.patches_pending + g.patches_pending,
            reboot_needed: acc.reboot_needed + g.reboot_needed,
            with_patrimonio: acc.with_patrimonio + g.with_patrimonio,
          }),
          {
            key: "__total__",
            client_name: "TOTAL GERAL",
            site_name: `${list.length} unidades`,
            total: 0,
            with_agent: 0,
            online: 0,
            offline: 0,
            overdue: 0,
            offline_overdue: 0,
            agentless: 0,
            network: 0,
            medical: 0,
            printers: 0,
            in_ad: 0,
            outside_ad: 0,
            patches_pending: 0,
            reboot_needed: 0,
            with_patrimonio: 0,
            patrimonio_pct: 0,
            isTotal: true,
          },
        );
        totals.patrimonio_pct =
          totals.total > 0 ? Math.round((totals.with_patrimonio / totals.total) * 100) : 0;
        list.push(totals);
      }
      return list;
    });

    const kpiStats = computed(() => {
      let source = filteredRows.value;
      if (selectedReportType.value === "unit_summary") {
        const q = (searchQuery.value || "").trim().toLowerCase();
        source = q
          ? unitScopedRows.value.filter((r) =>
              `${r.client_name} ${r.site_name}`.toLowerCase().includes(q),
            )
          : unitScopedRows.value;
      }
      let withAgent = 0;
      let online = 0;
      let offline = 0;
      let overdue = 0;
      let agentless = 0;
      let networkAndMedical = 0;
      let inAd = 0;
      let outsideAd = 0;
      let patchesPending = 0;
      let rebootNeeded = 0;
      let withPatrimonio = 0;

      for (const r of source) {
        if (r.has_agent) {
          withAgent += 1;
          if (r.monitor_status === "online") online += 1;
          else if (r.monitor_status === "overdue") overdue += 1;
          else offline += 1;
          if (r.has_patches_pending) patchesPending += 1;
          if (r.needs_reboot) rebootNeeded += 1;
        } else {
          agentless += 1;
        }
        if (
          r.category === "ativo_rede" ||
          r.category === "passivo_rede" ||
          r.category === "equipamento_medico"
        ) {
          networkAndMedical += 1;
        }
        if (r.ad_state === "in_ad") inAd += 1;
        if (r.ad_state === "outside_ad" || r.ad_state === "outside_ad_lan") outsideAd += 1;
        if (r.patrimonio) withPatrimonio += 1;
      }

      const total = source.length;
      return {
        total,
        withAgent,
        online,
        offline,
        overdue,
        agentless,
        networkAndMedical,
        inAd,
        outsideAd,
        patchesPending,
        rebootNeeded,
        withPatrimonio,
        patrimonioPct: total > 0 ? Math.round((withPatrimonio / total) * 100) : 0,
      };
    });

    const exportRowCount = computed(() =>
      selectedReportType.value === "unit_summary"
        ? unitSummaryRows.value.filter((r) => !r.isTotal).length
        : filteredRows.value.length,
    );

    function buildScopeSlug() {
      const raw =
        selectedClient.value !== "Todos" && selectedSite.value !== "Todos"
          ? `${selectedClient.value}-${selectedSite.value}`
          : selectedClient.value !== "Todos"
            ? selectedClient.value
            : selectedSite.value !== "Todos"
              ? selectedSite.value
              : "Geral";
      return raw
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/[^a-zA-Z0-9_-]+/g, "-");
    }

    function exportCSV() {
      const escapeCell = (val) => `"${String(val ?? "").replace(/"/g, '""')}"`;
      let lines = [];

      if (selectedReportType.value === "unit_summary") {
        const headers = [
          "Empresa/Cliente",
          "Unidade/Filial",
          "Total Equipamentos",
          "Com Agente Tactical",
          "Online",
          "Offline",
          "Vencidos (Overdue)",
          "Sem Agente (LAN/Manual)",
          "Ativos/Passivos Rede",
          "Equipamentos Medicos",
          "Impressoras/CFTV",
          "No Dominio AD (PCs)",
          "Fora do AD (PCs)",
          "Patches Pendentes",
          "Reboot Pendente",
          "Com Patrimonio",
          "% Patrimonio",
        ];
        lines = [headers.map(escapeCell).join(";")];
        for (const g of unitSummaryRows.value) {
          lines.push(
            [
              g.client_name,
              g.site_name,
              g.total,
              g.with_agent,
              g.online,
              g.offline,
              g.overdue,
              g.agentless,
              g.network,
              g.medical,
              g.printers,
              g.in_ad,
              g.outside_ad,
              g.patches_pending,
              g.reboot_needed,
              g.with_patrimonio,
              `${g.patrimonio_pct}%`,
            ]
              .map(escapeCell)
              .join(";"),
          );
        }
      } else {
        const headers = [
          "Patrimonio",
          "Equipamento/Hostname",
          "Empresa/Cliente",
          "Unidade/Site",
          "Classificacao",
          "Setor/Localizacao",
          "Monitoramento/Status",
          "Active Directory",
          "Dominio/Workgroup",
          "Usuario Logado",
          "SO / Funcao Clinica",
          "IP Local (LAN)",
          "IP Publico",
          "Fabricante/Modelo",
          "Numero de Serie",
          "Patches",
          "Reboot",
          "Agente",
          "Ultima Resposta",
        ];
        lines = [headers.map(escapeCell).join(";")];
        for (const r of filteredRows.value) {
          lines.push(
            [
              r.patrimonio || "-",
              r.hostname,
              r.client_name,
              r.site_name,
              r.category_label,
              r.sector_location || "-",
              r.monitor_status_label,
              r.ad_label,
              r.domain_name || "-",
              r.logged_username || "-",
              r.operating_system || "-",
              r.local_ips || "-",
              r.public_ip || "-",
              r.make_model || "-",
              r.serial_number || "-",
              r.patches_label,
              r.reboot_label,
              r.has_agent ? `v${r.version}` : "Sem Agente",
              r.last_seen_formatted || "-",
            ]
              .map(escapeCell)
              .join(";"),
          );
        }
      }

      const csvContent = "\uFEFF" + lines.join("\r\n");
      const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      const dateStr = new Date().toISOString().slice(0, 10);
      a.href = url;
      a.download = `relatorio-${buildScopeSlug()}-${selectedReportType.value}-${dateStr}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      notifySuccess(`Relatório exportado (${exportRowCount.value} registro(s) — ${scopeLabel.value})!`);
    }

    function printReport() {
      const escHtml = (val) =>
        String(val ?? "")
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;")
          .replace(/"/g, "&quot;");

      const reportTitle = activeReportMeta.value.label;
      const nowStr = new Date().toLocaleString("pt-BR");

      let tableHeadHtml = "";
      let tableBodyHtml = "";

      if (selectedReportType.value === "unit_summary") {
        tableHeadHtml = `
          <tr>
            <th>Empresa</th>
            <th>Unidade</th>
            <th>Total</th>
            <th>Com Agente</th>
            <th>Online</th>
            <th>Off/Venc.</th>
            <th>Sem Agente</th>
            <th>Rede</th>
            <th>Médicos</th>
            <th>Impr./CFTV</th>
            <th>No AD</th>
            <th>Fora AD</th>
            <th>Patches</th>
            <th>Reboot</th>
            <th>Patrimônio</th>
          </tr>`;
        tableBodyHtml = unitSummaryRows.value
          .map(
            (g) => `
          <tr${g.isTotal ? ' style="font-weight:700;background:#e2e8f0;"' : ""}>
            <td><strong>${escHtml(g.client_name)}</strong></td>
            <td>${escHtml(g.site_name)}</td>
            <td style="text-align:right"><strong>${g.total}</strong></td>
            <td style="text-align:right">${g.with_agent}</td>
            <td style="text-align:right">${g.online}</td>
            <td style="text-align:right">${g.offline_overdue}</td>
            <td style="text-align:right">${g.agentless}</td>
            <td style="text-align:right">${g.network}</td>
            <td style="text-align:right">${g.medical}</td>
            <td style="text-align:right">${g.printers}</td>
            <td style="text-align:right">${g.in_ad}</td>
            <td style="text-align:right">${g.outside_ad}</td>
            <td style="text-align:right">${g.patches_pending}</td>
            <td style="text-align:right">${g.reboot_needed}</td>
            <td style="text-align:center">${g.with_patrimonio}/${g.total} (${g.patrimonio_pct}%)</td>
          </tr>`,
          )
          .join("");
      } else {
        tableHeadHtml = `
          <tr>
            <th>Patrimônio</th>
            <th>Equipamento</th>
            <th>Empresa / Unidade</th>
            <th>Classificação</th>
            <th>Status</th>
            <th>Active Directory</th>
            <th>SO / Função</th>
            <th>IP Local</th>
            <th>Fabricante / Modelo</th>
            <th>Patches / Reboot</th>
          </tr>`;
        tableBodyHtml = filteredRows.value
          .map(
            (r) => `
          <tr>
            <td>${escHtml(r.patrimonio || "—")}</td>
            <td><strong>${escHtml(r.hostname)}</strong>${r.sector_location && r.sector_location !== "—" ? `<br><span style="color:#64748b;font-size:9px">${escHtml(r.sector_location)}</span>` : ""}</td>
            <td>${escHtml(r.client_name)} / ${escHtml(r.site_name)}</td>
            <td>${escHtml(r.category_label)}</td>
            <td>${escHtml(r.monitor_status_label)}</td>
            <td>${escHtml(r.ad_label)}</td>
            <td>${escHtml(r.operating_system)}</td>
            <td>${escHtml(r.local_ips)}</td>
            <td>${escHtml(r.make_model)}</td>
            <td>${escHtml(r.patches_label)} / ${escHtml(r.reboot_label)}</td>
          </tr>`,
          )
          .join("");
      }

      const win = window.open("", "_blank");
      if (!win) {
        notifyError("Permita pop-ups no navegador para imprimir/salvar PDF.");
        return;
      }

      const k = kpiStats.value;
      win.document.write(`
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
          <meta charset="utf-8" />
          <title>${escHtml(reportTitle)} — ${escHtml(scopeLabel.value)}</title>
          <style>
            @page { size: landscape; margin: 10mm; }
            body { font-family: "Segoe UI", Arial, sans-serif; margin: 14px; color: #0f172a; }
            .hdr { display: flex; justify-content: space-between; align-items: flex-end; border-bottom: 2px solid #0f4c5c; padding-bottom: 8px; margin-bottom: 10px; }
            h1 { font-size: 16px; margin: 0 0 3px; color: #0f4c5c; }
            .meta { font-size: 10.5px; color: #475569; }
            .kpis { display: grid; grid-template-columns: repeat(6, 1fr); gap: 8px; margin-bottom: 12px; font-size: 10.5px; }
            .kpi { padding: 6px 8px; border: 1px solid #cbd5e1; border-radius: 6px; background: #f8fafc; }
            .kpi-lbl { font-size: 9px; text-transform: uppercase; color: #64748b; font-weight: 700; }
            .kpi-val { font-size: 13px; font-weight: 700; color: #0f172a; margin-top: 2px; }
            table { width: 100%; border-collapse: collapse; font-size: 9.5px; }
            thead { display: table-header-group; }
            tr { page-break-inside: avoid; }
            th, td { border: 1px solid #cbd5e1; padding: 4px 6px; text-align: left; vertical-align: top; }
            th { background: #0f4c5c; color: #fff; font-weight: 600; }
            tr:nth-child(even) { background: #f8fafc; }
            .footer { margin-top: 10px; font-size: 9px; color: #64748b; text-align: right; }
            @media print { body { margin: 0; } }
          </style>
        </head>
        <body>
          <div class="hdr">
            <div>
              <h1>Tactical RMM Enhanced — ${escHtml(reportTitle)}</h1>
              <div class="meta"><strong>Escopo:</strong> ${escHtml(scopeLabel.value)} &bull; <strong>Gerado em:</strong> ${escHtml(nowStr)}</div>
            </div>
            <div class="meta" style="text-align:right"><strong>Registros Exatos:</strong> ${exportRowCount.value}</div>
          </div>
          <div class="kpis">
            <div class="kpi"><div class="kpi-lbl">Total no Escopo</div><div class="kpi-val">${k.total}</div></div>
            <div class="kpi"><div class="kpi-lbl">Agentes Online / Off</div><div class="kpi-val">${k.online} on / ${k.offline + k.overdue} off</div></div>
            <div class="kpi"><div class="kpi-lbl">Sem Agente / Rede</div><div class="kpi-val">${k.agentless}</div></div>
            <div class="kpi"><div class="kpi-lbl">AD / Fora do AD (PCs)</div><div class="kpi-val">${k.inAd} AD / ${k.outsideAd} fora</div></div>
            <div class="kpi"><div class="kpi-lbl">Patches / Reboot</div><div class="kpi-val">${k.patchesPending} / ${k.rebootNeeded}</div></div>
            <div class="kpi"><div class="kpi-lbl">Com Patrimônio</div><div class="kpi-val">${k.withPatrimonio} (${k.patrimonioPct}%)</div></div>
          </div>
          <table>
            <thead>${tableHeadHtml}</thead>
            <tbody>${tableBodyHtml}</tbody>
          </table>
          <div class="footer">Relatório oficial gerado pelo Tactical RMM Enhanced em ${escHtml(nowStr)}</div>
          <script>window.onload = function() { window.print(); };<\/script>
        </body>
        </html>
      `);
      win.document.close();
    }

    onMounted(() => {
      loadReportData(true);
    });

    return {
      loading,
      allRows,
      selectedReportType,
      selectedClient,
      selectedSite,
      selectedStatus,
      searchQuery,
      includeAgentlessPcsInAd,
      reportTypeOptions,
      statusOptions,
      activeReportMeta,
      clientOptions,
      siteOptions,
      unitQuickPills,
      scopeLabel,
      columns,
      unitSummaryColumns,
      filteredRows,
      unitSummaryRows,
      kpiStats,
      exportRowCount,
      categoryColor,
      getEntityBadgeColor,
      selectUnitScope,
      loadReportData,
      exportCSV,
      printReport,
    };
  },
};
</script>

<style scoped>
.trmm-reports-card {
  height: 100vh;
  max-height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.trmm-reports-card--dark {
  background: #0f141d;
}

.trmm-reports-card--light {
  background: #f8fafc;
}

.trmm-rep-header {
  flex: 0 0 auto;
  background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 55%, #0f4c5c 100%);
  border-bottom: 1px solid rgba(148, 163, 184, 0.2);
  gap: 8px 12px;
}

.trmm-rep-hdr-badge {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.22);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.trmm-rep-hdr-btn {
  border-radius: 7px;
  background: rgba(255, 255, 255, 0.1);
  padding: 2px 10px;
}

.trmm-rep-hdr-btn:hover {
  background: rgba(255, 255, 255, 0.2);
}

.trmm-rep-filters {
  flex: 0 0 auto;
}

.trmm-rep-filters--dark {
  background: rgba(15, 23, 42, 0.5);
}

.trmm-rep-filters--light {
  background: #ffffff;
}

.trmm-unit-pill {
  border-radius: 999px !important;
  padding: 2px 10px !important;
  min-height: 26px !important;
  font-size: 11.5px !important;
  font-weight: 500;
  border: 1px solid rgba(148, 163, 184, 0.25);
  background: rgba(148, 163, 184, 0.1);
}

.trmm-unit-pill--active {
  background: var(--q-primary, #1976d2) !important;
  border-color: var(--q-primary, #1976d2) !important;
  color: #ffffff !important;
  font-weight: 600;
}

.trmm-unit-pill-cnt {
  margin-left: 6px;
  padding: 0 6px;
  border-radius: 999px;
  font-size: 10.5px;
  font-weight: 700;
  background: rgba(0, 0, 0, 0.22);
}

body.body--light .trmm-unit-pill:not(.trmm-unit-pill--active) .trmm-unit-pill-cnt {
  background: rgba(15, 23, 42, 0.1);
  color: #0f172a;
}

.trmm-accuracy-bar {
  border-radius: 8px;
  border: 1px solid rgba(45, 212, 191, 0.25);
  gap: 8px;
}

.trmm-accuracy-bar--dark {
  background: rgba(13, 148, 136, 0.12);
}

.trmm-accuracy-bar--light {
  background: rgba(13, 148, 136, 0.08);
}

.trmm-kpi-mini {
  padding: 6px 10px;
  border-radius: 9px;
  border: 1px solid rgba(148, 163, 184, 0.16);
}

.trmm-kpi-mini--dark {
  background: rgba(20, 26, 36, 0.85);
}

.trmm-kpi-mini--light {
  background: #f8fafc;
  border-color: rgba(15, 23, 42, 0.1);
}

.trmm-kpi-mini-lbl {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #94a3b8;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

body.body--light .trmm-kpi-mini-lbl {
  color: #64748b;
}

.trmm-kpi-mini-val {
  font-size: 18px;
  font-weight: 800;
  line-height: 1.25;
}

.trmm-rep-table :deep(thead tr th) {
  position: sticky;
  top: 0;
  z-index: 2;
}
</style>
