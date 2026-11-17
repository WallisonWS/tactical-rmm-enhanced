<template>
  <q-card flat square class="full-width" data-no-translate="true">
    <q-bar v-if="modal" class="bg-primary text-white">
      <q-btn @click="search" class="q-mr-sm" dense flat icon="refresh">
        <q-tooltip>Atualizar Auditoria</q-tooltip>
      </q-btn>
      <q-icon name="travel_explore" size="sm" class="q-mr-xs" />
      <div class="text-weight-bold">Auditoria Completa do Sistema (Audit Manager)</div>
      <q-space />
      <q-btn dense flat icon="close" v-close-popup>
        <q-tooltip>Fechar</q-tooltip>
      </q-btn>
    </q-bar>
    <q-table
      @request="onRequest"
      :rows="auditLogs"
      :columns="columns"
      class="tabs-tbl-sticky trmm-fill-table"
      :table-class="{
        'table-bgcolor': !$q.dark.isActive,
        'table-bgcolor-dark': $q.dark.isActive,
      }"
      :style="
        tabHeight
          ? { height: tabHeight }
          : { height: modal ? 'calc(100vh - 34px)' : `${$q.screen.height - 33}px` }
      "
      row-key="id"
      dense
      flat
      binary-state-sort
      v-model:pagination="pagination"
      :rows-per-page-options="[25, 50, 100, 500, 1000]"
      :no-data-label="tableNoDataText"
      @row-click="openAuditDetail"
      virtual-scroll
      :virtual-scroll-item-size="28"
      :loading="loading"
    >
      <template v-slot:top>
        <div class="row items-center wrap full-width q-gutter-xs q-pa-xs">
          <q-btn
            dense
            flat
            round
            color="primary"
            @click="search"
            icon="refresh"
          >
            <q-tooltip>Atualizar registros de auditoria</q-tooltip>
          </q-btn>
          <q-option-group
            v-if="!agent"
            inline
            dense
            v-model="filterType"
            :options="filterTypeOptions"
            color="primary"
          />
          <tactical-dropdown
            v-if="filterType === 'agents' && !agent"
            style="width: 190px"
            v-model="agentFilter"
            :options="agentOptions"
            label="Computadores"
            clearable
            mapOptions
            multiple
            outlined
            filterable
          />
          <tactical-dropdown
            v-if="filterType === 'clients' && !agent"
            style="width: 190px"
            v-model="clientFilter"
            :options="clientOptions"
            label="Clientes"
            clearable
            multiple
            outlined
            mapOptions
            filterable
          />
          <tactical-dropdown
            style="width: 170px"
            v-model="userFilter"
            :options="userOptions"
            label="Usuários"
            clearable
            outlined
            multiple
          />
          <tactical-dropdown
            style="width: 190px"
            v-model="actionFilter"
            :options="actionOptions"
            label="Ação"
            clearable
            outlined
            multiple
            mapOptions
          />
          <tactical-dropdown
            style="width: 175px"
            v-if="!agent"
            v-model="objectFilter"
            :options="objectOptions"
            label="Objeto / Módulo"
            clearable
            outlined
            multiple
            mapOptions
          />
          <tactical-dropdown
            style="width: 175px"
            v-model="timeFilter"
            :options="timeOptions"
            label="Período"
            outlined
            mapOptions
          />
          <q-input
            v-model="searchText"
            dense
            outlined
            clearable
            style="min-width: 210px; flex: 1 1 210px; max-width: 300px"
            placeholder="Pesquisar mensagem, comando, IP..."
            @keyup.enter="search"
            @clear="search"
          >
            <template v-slot:prepend>
              <q-icon name="search" size="xs" color="primary" />
            </template>
          </q-input>
          <q-btn
            unelevated
            no-caps
            dense
            color="primary"
            icon="search"
            label="Buscar"
            class="q-px-sm"
            @click="search"
          />
          <q-btn
            v-if="hasActiveFilters"
            outline
            no-caps
            dense
            color="grey"
            icon="clear_all"
            label="Limpar"
            class="q-px-sm"
            @click="resetFilters"
          />
          <q-space />
          <export-table-btn :data="auditLogs" :columns="columns" />
        </div>
      </template>

      <template v-slot:no-data>
        <div class="full-width row items-center justify-center q-pa-md q-gutter-sm">
          <q-icon name="info_outline" size="sm" color="info" />
          <span class="text-body2">{{ tableNoDataText }}</span>
          <q-btn
            v-if="timeFilter !== 0"
            outline
            dense
            no-caps
            color="primary"
            label="Carregar Todo o Histórico"
            @click="loadAllHistory"
          />
        </div>
      </template>

      <template v-slot:body-cell-action="props">
        <q-td :props="props">
          <q-badge
            :color="formatActionColor(props.row.action)"
            :label="formatActionLabel(props.row.action)"
          />
        </q-td>
      </template>
      <template v-slot:body-cell-client="props">
        <q-td :props="props">
          <span v-if="props.value">{{ props.value.client_name }}</span>
          <span v-else class="text-grey-6">-</span>
        </q-td>
      </template>
      <template v-slot:body-cell-site="props">
        <q-td :props="props">
          <span v-if="props.value">{{ props.value.name }}</span>
          <span v-else class="text-grey-6">-</span>
        </q-td>
      </template>
      <template v-slot:body-cell-entry_time="props">
        <q-td :props="props">
          {{ formatDate(props.value) }}
        </q-td>
      </template>
      <template v-slot:body-cell-details="props">
        <q-td :props="props">
          <q-btn
            dense
            flat
            round
            size="xs"
            color="primary"
            icon="visibility"
            @click.stop="openAuditDetail($event, props.row)"
          >
            <q-tooltip>Ver detalhes (Before / After / IP)</q-tooltip>
          </q-btn>
        </q-td>
      </template>
    </q-table>
  </q-card>
</template>

<script>
// composition imports
import { ref, computed, watch, onMounted } from "vue";
import { useStore } from "vuex";
import { useClientDropdown } from "@/composables/clients";
import { useAgentDropdown } from "@/composables/agents";
import { useUserDropdown } from "@/composables/accounts";
import { useQuasar } from "quasar";
import { fetchAuditLog } from "@/api/logs";
import { formatTableColumnText } from "@/utils/format";

// ui imported
import AuditLogDetailModal from "@/components/logs/AuditLogDetailModal.vue";
import ExportTableBtn from "@/components/ui/ExportTableBtn.vue";
import TacticalDropdown from "@/components/ui/TacticalDropdown.vue";

const ACTION_LABELS = {
  add: "Criação / Adição",
  modify: "Alteração / Edição",
  delete: "Exclusão / Remoção",
  execute_command: "Comando Executado",
  execute_script: "Script Executado",
  remote_session: "Sessão Remota",
  file_transfer: "Transferência de Arquivo",
  url_action: "Ação de URL",
  agent_install: "Instalação de Agente",
  bulk_action: "Ação em Massa",
  failed_login: "Falha de Login",
  login: "Login Realizado",
  task_run: "Execução de Tarefa",
};

// static data
const columns = [
  {
    name: "entry_time",
    label: "Data/Hora",
    field: "entry_time",
    align: "left",
    sortable: true,
  },
  {
    name: "username",
    label: "Usuário",
    field: "username",
    align: "left",
    sortable: true,
  },
  {
    name: "agent",
    label: "Computador",
    field: "agent",
    align: "left",
    sortable: true,
  },
  {
    name: "client",
    label: "Cliente",
    field: "site",
    align: "left",
    sortable: true,
  },
  { name: "site", label: "Unidade / Site", field: "site", align: "left", sortable: true },
  {
    name: "action",
    label: "Ação",
    field: "action",
    align: "left",
    sortable: true,
  },
  {
    name: "object_type",
    label: "Objeto",
    field: "object_type",
    align: "left",
    sortable: true,
    format: (val) => formatTableColumnText(val),
  },
  {
    name: "message",
    label: "Descrição / Evento",
    field: "message",
    align: "left",
    sortable: true,
  },
  {
    name: "client_ip",
    label: "IP Origem",
    field: "ip_address",
    align: "left",
    sortable: true,
  },
  {
    name: "details",
    label: "Detalhes",
    field: "id",
    align: "center",
    sortable: false,
  },
];

const agentActionOptions = [
  { value: "remote_session", label: "Sessão Remota (Controle)" },
  { value: "execute_command", label: "Comando Executado" },
  { value: "execute_script", label: "Script Executado" },
  { value: "file_transfer", label: "Transferência de Arquivo" },
  { value: "add", label: "Criação / Adição" },
  { value: "modify", label: "Alteração / Edição" },
  { value: "url_action", label: "Ação de URL" },
  { value: "agent_install", label: "Instalação de Agente" },
  { value: "task_run", label: "Execução de Tarefa" },
  { value: "delete", label: "Exclusão / Remoção" },
];

const actionOptions = [
  { value: "bulk_action", label: "Ações em Massa" },
  { value: "login", label: "Login Realizado" },
  { value: "failed_login", label: "Falha de Login" },
];

const objectOptions = [
  { value: "agent", label: "Agente / Computador" },
  { value: "automatedtask", label: "Tarefa Automática" },
  { value: "bulk", label: "Ações em Massa" },
  { value: "coresettings", label: "Configurações Globais" },
  { value: "check", label: "Verificação (Check)" },
  { value: "client", label: "Cliente" },
  { value: "policy", label: "Política" },
  { value: "site", label: "Unidade / Site" },
  { value: "script", label: "Script" },
  { value: "user", label: "Usuário" },
  { value: "winupdatepolicy", label: "Política de Updates" },
  { value: "alerttemplate", label: "Modelo de Alerta" },
  { value: "role", label: "Perfil / Função (Role)" },
  { value: "urlaction", label: "Ação de URL" },
  { value: "keystore", label: "Cofre de Chaves" },
  { value: "customfield", label: "Campo Personalizado" },
  { value: "schedule", label: "Agendamento" },
  { value: "reportschedule", label: "Relatório Agendado" },
];

const timeOptions = [
  { value: 1, label: "Últimas 24 horas" },
  { value: 7, label: "Últimos 7 dias" },
  { value: 30, label: "Últimos 30 dias" },
  { value: 90, label: "Últimos 3 meses" },
  { value: 180, label: "Últimos 6 meses" },
  { value: 365, label: "Último 1 ano" },
  { value: 0, label: "Todo o Histórico" },
];

const filterTypeOptions = [
  {
    label: "Por Clientes",
    value: "clients",
  },
  {
    label: "Por Computadores",
    value: "agents",
  },
];

export default {
  name: "AuditManager",
  components: { TacticalDropdown, ExportTableBtn },
  props: {
    agent: String,
    tabHeight: String,
    modal: {
      type: Boolean,
      default: false,
    },
  },
  setup(props) {
    // setup vuex
    const store = useStore();
    const formatDate = computed(() => store.getters.formatDate);
    const dash_positive_color = computed(() => store.state.dash_positive_color);
    const dash_negative_color = computed(() => store.state.dash_negative_color);
    const dash_warning_color = computed(() => store.state.dash_warning_color);

    // setup dropdowns
    const { clientOptions, getClientOptions } = useClientDropdown();
    const { agentOptions, getAgentOptions } = useAgentDropdown();
    const { userOptions, getUserOptions } = useUserDropdown();

    // setup main audit log functionality
    const auditLogs = ref([]);
    const agentFilter = ref(null);
    const userFilter = ref(null);
    const actionFilter = ref(null);
    const clientFilter = ref(null);
    const objectFilter = ref(null);
    const timeFilter = ref(30);
    const searchText = ref("");
    const filterType = ref("clients");
    const loading = ref(false);
    const searched = ref(false);

    const pagination = ref({
      rowsPerPage: 50,
      rowsNumber: null,
      sortBy: "entry_time",
      descending: true,
      page: 1,
    });

    const hasActiveFilters = computed(() => {
      return Boolean(
        (userFilter.value && userFilter.value.length > 0) ||
          (actionFilter.value && actionFilter.value.length > 0) ||
          (objectFilter.value && objectFilter.value.length > 0) ||
          (!props.agent && agentFilter.value && agentFilter.value.length > 0) ||
          (clientFilter.value && clientFilter.value.length > 0) ||
          (searchText.value && searchText.value.trim().length > 0) ||
          timeFilter.value !== 30,
      );
    });

    async function search() {
      loading.value = true;
      searched.value = true;

      const data = {
        pagination: pagination.value,
      };

      if (agentFilter.value && agentFilter.value.length > 0)
        data["agentFilter"] = agentFilter.value;
      else if (clientFilter.value && clientFilter.value.length > 0)
        data["clientFilter"] = clientFilter.value;
      if (userFilter.value && userFilter.value.length > 0)
        data["userFilter"] = userFilter.value;
      if (timeFilter.value) data["timeFilter"] = timeFilter.value;
      if (actionFilter.value && actionFilter.value.length > 0)
        data["actionFilter"] = actionFilter.value;
      if (objectFilter.value && objectFilter.value.length > 0)
        data["objectFilter"] = objectFilter.value;
      if (searchText.value && searchText.value.trim())
        data["search"] = searchText.value.trim();

      try {
        const { audit_logs, total } = await fetchAuditLog(data);
        auditLogs.value = audit_logs;
        pagination.value.rowsNumber = total;
      } catch (e) {}

      loading.value = false;
    }

    function resetFilters() {
      userFilter.value = null;
      actionFilter.value = null;
      objectFilter.value = null;
      clientFilter.value = null;
      if (!props.agent) agentFilter.value = null;
      searchText.value = "";
      timeFilter.value = 30;
      pagination.value.page = 1;
      search();
    }

    function loadAllHistory() {
      timeFilter.value = 0;
      pagination.value.page = 1;
      search();
    }

    function onRequest(data) {
      const { page, rowsPerPage, sortBy, descending } = data.pagination;

      pagination.value.page = page;
      pagination.value.rowsPerPage = rowsPerPage;
      pagination.value.sortBy = sortBy;
      pagination.value.descending = descending;

      search();
    }

    // audit detail modal
    const { dialog } = useQuasar();
    function openAuditDetail(evt, log) {
      dialog({
        component: AuditLogDetailModal,
        componentProps: {
          log,
        },
      });
    }

    function formatActionLabel(action) {
      const key = String(action || "").toLowerCase();
      return ACTION_LABELS[key] || formatTableColumnText(action);
    }

    function formatActionColor(action) {
      switch (String(action || "").toLowerCase()) {
        case "modify":
          return dash_warning_color.value;
        case "add":
        case "agent_install":
        case "file_transfer":
        case "login":
          return dash_positive_color.value;
        case "delete":
        case "failed_login":
          return dash_negative_color.value;
        case "remote_session":
          return "teal-7";
        case "execute_command":
        case "execute_script":
          return "indigo-6";
        default:
          return "primary";
      }
    }

    // watchers
    watch(filterType, () => {
      agentFilter.value = null;
      clientFilter.value = null;
    });

    if (props.agent) {
      agentFilter.value = [props.agent];
      watch([userFilter, actionFilter, timeFilter], () => {
        pagination.value.page = 1;
        search();
      });
      watch(
        () => props.agent,
        (newValue) => {
          if (newValue) {
            agentFilter.value = [props.agent];
            pagination.value.page = 1;
            search();
          }
        },
      );
    } else {
      watch([agentFilter, clientFilter, userFilter, actionFilter, objectFilter, timeFilter], () => {
        pagination.value.page = 1;
        search();
      });
    }

    // vue component hooks
    onMounted(() => {
      if (!props.agent) {
        getClientOptions();
        getAgentOptions();
      }
      getUserOptions(true);
      search();
    });

    return {
      auditLogs,
      agentFilter,
      userFilter,
      actionFilter,
      clientFilter,
      objectFilter,
      timeFilter,
      searchText,
      filterType,
      loading,
      searched,
      hasActiveFilters,
      pagination,
      userOptions,
      clientOptions,
      agentOptions,
      columns,
      actionOptions: props.agent
        ? [...agentActionOptions]
        : [...agentActionOptions, ...actionOptions],
      objectOptions,
      timeOptions,
      filterTypeOptions,
      tableNoDataText: computed(() =>
        searched.value
          ? "Nenhum evento de auditoria encontrado para os filtros e período selecionados."
          : "Carregando registros de auditoria...",
      ),
      search,
      resetFilters,
      loadAllHistory,
      onRequest,
      openAuditDetail,
      formatActionLabel,
      formatActionColor,
      formatDate,
    };
  },
};
</script>
