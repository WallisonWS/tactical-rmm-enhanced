<template>
  <q-card style="width: 1220px; max-width: 97vw; max-height: 93vh" class="column no-wrap">
    <q-bar class="bg-indigo-10 text-white">
      <q-icon name="account_tree" class="q-mr-xs" />
      <div class="text-weight-medium">
        Auditoria Active Directory × Tactical RMM (Computadores Faltantes por Pasta / OU)
      </div>
      <q-space />
      <q-btn dense flat icon="close" v-close-popup @click="$emit('close')" />
    </q-bar>

    <!-- Probe Selector + Quick Actions -->
    <q-card-section class="q-py-sm q-px-md bg-grey-10 text-white border-bottom">
      <div class="row items-center q-col-gutter-sm">
        <div class="col-12 col-md-4">
          <q-select
            v-model="selectedProbeId"
            dense
            outlined
            dark
            emit-value
            map-options
            :options="probeOptions"
            label="Servidor / Agente para consultar o AD (LDAP)"
            @update:model-value="loadAudit"
          />
        </div>

        <div class="col-12 col-md-8 row items-center justify-end q-gutter-xs">
          <q-chip v-if="report" dense color="blue-grey-9" text-color="white" icon="dns">
            Domínio: {{ report.domain || "-" }} ({{ report.default_nc || "-" }})
          </q-chip>
          <q-btn
            dense
            unelevated
            color="primary"
            icon="refresh"
            label="Consultar AD Agora"
            :loading="loading"
            @click="loadAudit()"
          />
          <q-btn
            dense
            outline
            color="amber-4"
            icon="hub"
            :label="showLdapOverride ? 'Ocultar DC LDAP' : 'Conectar via IP do DC'"
            @click="showLdapOverride = !showLdapOverride"
          >
            <q-tooltip>
              Opcional: informe IP/FQDN do Controlador de Domínio + credencial caso o agente consultado esteja fora do AD
            </q-tooltip>
          </q-btn>
          <q-btn
            dense
            outline
            color="deep-purple-3"
            icon="publish"
            label="Publicar GPO no AD"
            :loading="publishingGpo"
            :disable="!selectedClient || !selectedSite || !selectedProbeId"
            @click="onPublishGpoFromProbe"
          >
            <q-tooltip>
              Publica binários + Install-TacticalRMM.ps1 no NETLOGON e cria/vincula a GPO na raiz do domínio para capturar máquinas desligadas e CN=Computers
            </q-tooltip>
          </q-btn>
          <q-btn
            dense
            outline
            color="orange-4"
            icon="terminal"
            label="Script Completo DC (.ps1)"
            :loading="downloadingDcScript"
            :disable="!selectedClient || !selectedSite"
            @click="onDownloadAllInOneDcScript"
          >
            <q-tooltip>
              Baixa script único para rodar como Admin direto no Controlador de Domínio: instala no DC, varre TODO o AD, faz Push paralelo e cria/vincula GPO na raiz
            </q-tooltip>
          </q-btn>
          <q-btn
            dense
            outline
            color="light-blue-4"
            icon="policy"
            label="GPO (.ps1)"
            :loading="downloadingGpo"
            :disable="!selectedClient || !selectedSite"
            @click="downloadFixedGpoScript"
          >
            <q-tooltip>
              Gera Install-TacticalRMM.ps1 corrigido para baixar diretamente do seu servidor RMM (-m gpoinstall) com log local
            </q-tooltip>
          </q-btn>
          <q-btn
            dense
            outline
            color="teal-3"
            icon="download"
            label="CSV"
            :disable="!filteredRows.length"
            @click="exportCsv"
          />
        </div>
      </div>

      <!-- Optional Direct DC / LDAP Override -->
      <div v-if="showLdapOverride" class="row items-center q-col-gutter-sm q-mt-xs">
        <div class="col-12 col-sm-4">
          <q-input
            v-model="ldapServer"
            dense
            outlined
            dark
            label="IP ou FQDN do Controlador AD (Opcional)"
            placeholder="Ex: 10.0.0.10"
          />
        </div>
        <div class="col-6 col-sm-3">
          <q-input
            v-model="pushUsername"
            dense
            outlined
            dark
            label="Usuário AD (em memória)"
            placeholder="DOMINIO\\Administrator"
          />
        </div>
        <div class="col-6 col-sm-3">
          <q-input
            v-model="pushPassword"
            dense
            outlined
            dark
            :type="showPassword ? 'text' : 'password'"
            label="Senha AD (em memória)"
          />
        </div>
        <div class="col-12 col-sm-2">
          <q-btn
            unelevated
            color="amber-8"
            icon="search"
            label="Consultar DC"
            class="full-width"
            :loading="loading"
            @click="loadAudit()"
          />
        </div>
      </div>
    </q-card-section>

    <q-card-section class="col scroll q-pa-md">
      <!-- Error Banner -->
      <q-banner v-if="errorMsg" rounded class="bg-negative text-white q-mb-md">
        <template v-slot:avatar>
          <q-icon name="error_outline" />
        </template>
        <div class="text-weight-medium">{{ errorMsg }}</div>
        <div class="text-caption q-mt-xs">
          Selecione acima um servidor AD online, preencha "Conectar via IP do DC", ou escolha o Cliente/Site abaixo e clique em "Script Completo DC (.ps1)" para rodar diretamente no Controlador de Domínio e puxar todas as máquinas:
        </div>
        <div class="row q-col-gutter-sm q-mt-sm">
          <div class="col-12 col-sm-5">
            <q-select
              v-model="selectedClient"
              dense
              outlined
              dark
              :options="clientOptions"
              label="Cliente de Destino"
              @update:model-value="onClientChanged"
            />
          </div>
          <div class="col-12 col-sm-5">
            <q-select
              v-model="selectedSite"
              dense
              outlined
              dark
              :options="siteOptions"
              label="Site de Destino"
            />
          </div>
        </div>
      </q-banner>

      <!-- Initial Loading Skeleton -->
      <div v-if="loading && !report" class="q-pa-xl text-center">
        <q-spinner-gears size="48px" color="primary" />
        <div class="text-subtitle2 q-mt-md">
          Consultando árvore completa do Active Directory (RootDSE / OUs / Computers / CN)...
        </div>
      </div>

      <template v-if="report">
        <!-- Summary KPI Strip -->
        <div class="row q-col-gutter-sm q-mb-sm">
          <div class="col-6 col-sm-4 col-md">
            <q-card flat bordered class="q-pa-xs text-center">
              <div class="text-caption text-grey">Total no AD</div>
              <div class="text-h6 text-weight-bold">{{ report.summary.total_ad }}</div>
            </q-card>
          </div>
          <div class="col-6 col-sm-4 col-md">
            <q-card flat bordered class="q-pa-xs text-center">
              <div class="text-caption text-grey">Habilitados AD</div>
              <div class="text-h6 text-weight-bold text-info">{{ report.summary.enabled_ad }}</div>
            </q-card>
          </div>
          <div class="col-6 col-sm-4 col-md">
            <q-card flat bordered class="q-pa-xs text-center">
              <div class="text-caption text-grey">No Tactical (Online)</div>
              <div class="text-h6 text-weight-bold text-positive">
                {{ report.summary.online_in_tactical }}
              </div>
            </q-card>
          </div>
          <div class="col-6 col-sm-4 col-md">
            <q-card flat bordered class="q-pa-xs text-center">
              <div class="text-caption text-grey">No Tactical (Offline)</div>
              <div class="text-h6 text-weight-bold text-warning">
                {{ report.summary.offline_in_tactical }}
              </div>
            </q-card>
          </div>
          <div class="col-6 col-sm-4 col-md">
            <q-card flat bordered class="q-pa-xs text-center">
              <div class="text-caption text-negative">Faltando no Tactical</div>
              <div class="text-h6 text-weight-bold text-negative">
                {{ report.summary.missing_enabled }}
              </div>
            </q-card>
          </div>
          <div class="col-6 col-sm-4 col-md">
            <q-card flat bordered class="q-pa-xs text-center">
              <div class="text-caption text-grey">Ativos (≤90d) Faltando</div>
              <div class="text-h6 text-weight-bold text-deep-orange">
                {{ report.summary.missing_active_90d }}
              </div>
            </q-card>
          </div>
        </div>

        <!-- AD Diagnostics Warnings -->
        <q-banner
          v-for="(diag, idx) in report.diagnostics || []"
          :key="idx"
          dense
          rounded
          class="bg-amber-10 text-white q-mb-xs"
        >
          <template v-slot:avatar>
            <q-icon name="info" />
          </template>
          <span class="text-caption">{{ diag }}</span>
        </q-banner>

        <!-- AD Folder Chips (OUs, Containers, Domain Root) -->
        <div class="q-mt-sm q-mb-sm">
          <div class="text-caption text-grey q-mb-xs">
            Pastas / OUs encontradas no AD ({{ report.folder_summary.length }}) — clique para filtrar:
          </div>
          <div class="row items-center wrap q-gutter-xs">
            <q-chip
              clickable
              dense
              :color="selectedFolder === '__ALL__' ? 'primary' : 'grey-8'"
              text-color="white"
              @click="selectedFolder = '__ALL__'"
            >
              Todas as Pastas ({{ report.summary.total_ad }})
            </q-chip>
            <q-chip
              v-for="f in report.folder_summary"
              :key="f.folder"
              clickable
              dense
              :color="selectedFolder === f.folder ? 'indigo-7' : f.missing_enabled > 0 ? 'deep-orange-9' : 'grey-8'"
              text-color="white"
              :icon="f.is_root_domain ? 'public' : f.is_default_container ? 'inventory_2' : 'folder'"
              @click="selectedFolder = selectedFolder === f.folder ? '__ALL__' : f.folder"
            >
              {{ f.folder }}: {{ f.missing_enabled }} falt. / {{ f.total }} total
              <q-tooltip>
                Pasta: {{ f.folder }} | Faltando (habilitados): {{ f.missing_enabled }} | Presentes no Tactical: {{ f.in_tactical }} (Online: {{ f.online }}, Offline: {{ f.offline_or_overdue }})
                <span v-if="f.is_default_container"> | Container padrão CN=Computers (GPO de OU não se aplica aqui)</span>
                <span v-if="f.is_root_domain"> | Objetos diretamente na raiz do domínio</span>
              </q-tooltip>
            </q-chip>
          </div>
        </div>

        <!-- Filter Controls -->
        <div class="row items-center q-col-gutter-sm q-mb-sm">
          <div class="col-12 col-md-4">
            <q-btn-toggle
              v-model="statusFilter"
              dense
              no-caps
              spread
              unelevated
              toggle-color="primary"
              :options="[
                { label: `Faltando (${countMissingFilteredFolder})`, value: 'missing' },
                { label: `Offline/Vencido`, value: 'offline' },
                { label: `Todos (${report.computers.length})`, value: 'all' },
              ]"
            />
          </div>
          <div class="col-12 col-md-4 row items-center q-gutter-sm">
            <q-checkbox v-model="onlyEnabled" dense label="Somente habilitados no AD" />
            <q-checkbox v-model="onlyActive90d" dense label="Ativos ≤ 90 dias" />
          </div>
          <div class="col-12 col-md-4 row items-center justify-end q-gutter-xs">
            <q-btn
              v-if="allMissingFilteredRows.length"
              dense
              unelevated
              color="deep-orange"
              icon="done_all"
              :label="`Puxar TODOS Faltantes (${allMissingFilteredRows.length})`"
              :loading="pushLoading"
              :disable="!selectedSite"
              @click="runPushInstall(allMissingFilteredRows, false)"
            >
              <q-tooltip>
                Envia instalação automática (WinRM + SMB/SchTasks + WMI DCOM) em lotes para TODOS os {{ allMissingFilteredRows.length }} computadores faltantes desta lista
              </q-tooltip>
            </q-btn>
          </div>
        </div>
        <div class="row q-mb-sm">
          <div class="col-12">
            <q-input
              v-model="search"
              dense
              outlined
              clearable
              placeholder="Buscar computador, pasta/OU, SO ou descrição..."
            >
              <template v-slot:prepend>
                <q-icon name="search" />
              </template>
            </q-input>
          </div>
        </div>

        <!-- Computers Table -->
        <q-table
          dense
          flat
          bordered
          row-key="distinguished_name"
          selection="multiple"
          v-model:selected="selectedRows"
          :rows="filteredRows"
          :columns="columns"
          :pagination="{ rowsPerPage: 15, sortBy: 'name', descending: false }"
          no-data-label="Nenhum computador encontrado com os filtros atuais."
        >
          <template v-slot:body-cell-name="props">
            <q-td :props="props">
              <div class="text-weight-bold">
                {{ props.row.name }}
                <q-badge v-if="props.row.is_dc" color="purple-7" class="q-ml-xs">DC</q-badge>
                <q-badge v-if="!props.row.enabled" color="grey-7" class="q-ml-xs">Desativado</q-badge>
              </div>
              <div class="text-caption text-grey-5" v-if="props.row.dns_hostname">
                {{ props.row.dns_hostname }}
              </div>
            </q-td>
          </template>

          <template v-slot:body-cell-folder_path="props">
            <q-td :props="props">
              <div>{{ props.row.folder_path }}</div>
              <q-badge
                v-if="props.row.is_default_container"
                color="amber-9"
                text-color="black"
                class="q-mt-xs"
              >
                Container CN (sem herança GPO OU)
              </q-badge>
              <q-badge
                v-else-if="props.row.is_root_domain"
                color="blue-grey-7"
                class="q-mt-xs"
              >
                Raiz do Domínio
              </q-badge>
            </q-td>
          </template>

          <template v-slot:body-cell-sync_state="props">
            <q-td :props="props">
              <q-badge v-if="props.row.sync_state === 'missing'" color="negative">
                Faltando no Tactical
              </q-badge>
              <q-badge v-else-if="props.row.sync_state === 'online'" color="positive">
                Online ({{ props.row.tactical_site || "Tactical" }})
              </q-badge>
              <q-badge v-else color="warning" text-color="black">
                {{ props.row.sync_state === "overdue" ? "Vencido" : "Offline" }} ({{ props.row.tactical_site || "Tactical" }})
              </q-badge>
            </q-td>
          </template>

          <template v-slot:body-cell-last_logon="props">
            <q-td :props="props">
              <span v-if="props.row.last_logon">
                {{ props.row.last_logon.slice(0, 10) }}
                <span v-if="props.row.days_since_logon !== null" class="text-caption text-grey-5">
                  ({{ props.row.days_since_logon }}d)
                </span>
              </span>
              <span v-else class="text-grey-6">Nunca / N/D</span>
            </q-td>
          </template>

          <template v-slot:body-cell-actions="props">
            <q-td :props="props" class="text-right">
              <q-btn
                dense
                size="sm"
                unelevated
                :color="props.row.in_tactical ? 'blue-grey-7' : 'deep-orange'"
                icon="install_desktop"
                :label="props.row.in_tactical ? 'Reparar' : 'Push'"
                :loading="pushLoading"
                :disable="!selectedSite"
                @click="runPushInstall([props.row], props.row.in_tactical)"
              />
            </q-td>
          </template>
        </q-table>

        <!-- Push Deploy Target Config Card -->
        <q-card flat bordered class="q-mt-md">
          <q-card-section class="q-pa-sm">
            <div class="text-subtitle2 text-weight-bold flex items-center q-mb-xs">
              <q-icon name="rocket_launch" color="deep-orange" class="q-mr-xs" />
              Instalação Remota via AD Push (WinRM 5985 + Fallback SMB/RPC ADMIN$ + schtasks SYSTEM)
            </div>
            <div class="row q-col-gutter-sm items-center">
              <div class="col-12 col-sm-6 col-md-3">
                <q-select
                  v-model="selectedClient"
                  dense
                  outlined
                  :options="clientOptions"
                  label="Cliente de Destino"
                  @update:model-value="onClientChanged"
                />
              </div>
              <div class="col-12 col-sm-6 col-md-3">
                <q-select
                  v-model="selectedSite"
                  dense
                  outlined
                  :options="siteOptions"
                  label="Site de Destino"
                />
              </div>
              <div class="col-6 col-md-2">
                <q-select
                  v-model="agentType"
                  dense
                  outlined
                  emit-value
                  map-options
                  :options="[
                    { label: 'Auto (PC/Server)', value: 'both' },
                    { label: 'Workstation', value: 'workstation' },
                    { label: 'Server', value: 'server' },
                  ]"
                  label="Tipo de Agente"
                />
              </div>
              <div class="col-6 col-md-2">
                <q-input
                  v-model="pushUsername"
                  dense
                  outlined
                  label="Admin AD (Opcional)"
                  placeholder="DOMINIO\\Administrator"
                />
              </div>
              <div class="col-12 col-md-2">
                <q-input
                  v-model="pushPassword"
                  dense
                  outlined
                  :type="showPassword ? 'text' : 'password'"
                  label="Senha (em memória)"
                >
                  <template v-slot:append>
                    <q-icon
                      :name="showPassword ? 'visibility_off' : 'visibility'"
                      class="cursor-pointer"
                      @click="showPassword = !showPassword"
                    />
                  </template>
                </q-input>
              </div>
            </div>

            <div class="row items-center justify-between q-mt-sm wrap q-gutter-xs">
              <div class="row items-center wrap q-gutter-sm">
                <q-checkbox v-model="bankingMode" dense label="Modo Banco em Estações (Pausar Mesh)" />
                <q-checkbox v-model="enableRdp" dense label="Habilitar RDP" />
                <q-checkbox v-model="enablePing" dense label="Habilitar Ping" />
                <q-checkbox v-model="forceReinstall" dense label="Forçar reinstalação se já existir" />
                <span class="text-caption text-grey-5">
                  * Credenciais transitam somente em memória no Push e nunca são gravadas no banco.
                </span>
              </div>
              <div class="row q-gutter-xs">
                <q-btn
                  outline
                  color="amber-9"
                  icon="select_all"
                  :label="`Selecionar Faltantes (${allMissingFilteredRows.length})`"
                  :disable="!allMissingFilteredRows.length || pushLoading"
                  @click="selectAllMissing"
                />
                <q-btn
                  unelevated
                  color="deep-orange"
                  icon="install_desktop"
                  :label="`Push nos Selecionados (${selectedRows.length})`"
                  :loading="pushLoading"
                  :disable="!selectedRows.length || !selectedSite"
                  @click="runPushInstall(selectedRows, forceReinstall)"
                />
              </div>
            </div>

            <div v-if="pushProgressMsg" class="text-caption text-amber q-mt-xs">
              {{ pushProgressMsg }}
            </div>
          </q-card-section>
        </q-card>

        <!-- Push Deploy Results Table -->
        <q-card v-if="pushResults.length" flat bordered class="q-mt-sm">
          <q-card-section class="q-pa-sm">
            <div class="text-subtitle2 text-weight-bold q-mb-xs">
              Resultado do Último Push Remoto ({{ pushSucceeded }} sucesso / {{ pushResults.length }} enviados)
            </div>
            <q-table
              dense
              flat
              bordered
              row-key="hostname"
              :rows="pushResults"
              :columns="pushResultColumns"
              :pagination="{ rowsPerPage: 10 }"
            >
              <template v-slot:body-cell-success="props">
                <q-td :props="props">
                  <q-badge :color="props.row.success ? 'positive' : 'negative'">
                    {{ props.row.status }}
                  </q-badge>
                </q-td>
              </template>
            </q-table>
          </q-card-section>
        </q-card>
      </template>
    </q-card-section>
  </q-card>
</template>

<script setup lang="ts">
import axios from "axios";
import { ref, computed, onMounted } from "vue";
import { useStore } from "vuex";
import { getBaseUrl } from "@/boot/axios";
import {
  fetchADDirectoryAudit,
  pushInstallADComputers,
  publishADGPO,
  type ADDirectoryAuditReport,
  type ADDirectoryComputer,
  type ADPushInstallResultItem,
} from "@/api/enhanced";
import { notifySuccess, notifyError } from "@/utils/notify";

const props = defineProps<{
  initialProbeAgentId?: string;
}>();

defineEmits<{
  (e: "close"): void;
}>();

const store = useStore();

const loading = ref(false);
const errorMsg = ref("");
const report = ref<ADDirectoryAuditReport | null>(null);
const selectedProbeId = ref<string>(props.initialProbeAgentId || "");

const selectedFolder = ref<string>("__ALL__");
const statusFilter = ref<"missing" | "offline" | "all">("missing");
const onlyEnabled = ref(true);
const onlyActive90d = ref(false);
const search = ref("");
const selectedRows = ref<ADDirectoryComputer[]>([]);

const clientOptions = ref<{ label: string; value: number; sites: { label: string; value: number }[] }[]>([]);
const selectedClient = ref<{ label: string; value: number; sites: { label: string; value: number }[] } | null>(null);
const selectedSite = ref<{ label: string; value: number } | null>(null);
const agentType = ref<"both" | "workstation" | "server">("both");
const pushUsername = ref("");
const pushPassword = ref("");
const ldapServer = ref("");
const showLdapOverride = ref(false);
const showPassword = ref(false);
const bankingMode = ref(true);
const enableRdp = ref(true);
const enablePing = ref(true);
const forceReinstall = ref(false);

const downloadingGpo = ref(false);
const publishingGpo = ref(false);
const downloadingDcScript = ref(false);
const pushLoading = ref(false);
const pushProgressMsg = ref("");
const pushResults = ref<ADPushInstallResultItem[]>([]);

const probeOptions = computed(() => {
  const list = report.value?.available_probes || [];
  return list.map((p) => ({
    label: `${p.hostname} (${p.is_dc ? "DC AD" : p.monitoring_type === "server" ? "Server" : "PC"} - ${p.client}/${p.site})`,
    value: p.agent_id,
  }));
});

const siteOptions = computed(() => selectedClient.value?.sites || []);

const countMissingFilteredFolder = computed(() => {
  const list = report.value?.computers || [];
  return list.filter((c) => {
    if (selectedFolder.value !== "__ALL__" && c.folder_group !== selectedFolder.value) return false;
    if (onlyEnabled.value && !c.enabled) return false;
    return !c.in_tactical;
  }).length;
});

const filteredRows = computed(() => {
  const rows = report.value?.computers || [];
  const q = search.value.trim().toLowerCase();
  return rows.filter((r) => {
    if (selectedFolder.value !== "__ALL__" && r.folder_group !== selectedFolder.value) return false;
    if (onlyEnabled.value && !r.enabled) return false;
    if (onlyActive90d.value && (r.days_since_logon === null || r.days_since_logon > 90)) return false;
    if (statusFilter.value === "missing" && r.in_tactical) return false;
    if (statusFilter.value === "offline" && (!r.in_tactical || r.sync_state === "online")) return false;
    if (q) {
      const hay = `${r.name} ${r.dns_hostname} ${r.folder_path} ${r.operating_system} ${r.description}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
});

const allMissingFilteredRows = computed(() =>
  filteredRows.value.filter((r) => !r.in_tactical && r.enabled),
);

const pushSucceeded = computed(() => pushResults.value.filter((r) => r.success).length);

const columns = [
  { name: "name", label: "Computador no AD", field: "name", align: "left" as const, sortable: true },
  { name: "folder_path", label: "Pasta / OU no AD", field: "folder_path", align: "left" as const, sortable: true },
  { name: "sync_state", label: "Status no Tactical", field: "sync_state", align: "left" as const, sortable: true },
  { name: "operating_system", label: "Sistema Operacional", field: "operating_system", align: "left" as const, sortable: true },
  { name: "description", label: "Descrição", field: "description", align: "left" as const, sortable: true },
  { name: "last_logon", label: "Último Logon AD", field: "last_logon", align: "left" as const, sortable: true },
  { name: "actions", label: "Ação", field: "name", align: "right" as const },
];

const pushResultColumns = [
  { name: "hostname", label: "Computador", field: "hostname", align: "left" as const, sortable: true },
  { name: "ip", label: "IP", field: "ip", align: "left" as const },
  { name: "method", label: "Método", field: "method", align: "left" as const },
  { name: "success", label: "Resultado", field: "status", align: "left" as const },
  { name: "detail", label: "Detalhe", field: "detail", align: "left" as const },
];

interface RawSiteDto {
  id: number;
  name: string;
}

interface RawClientDto {
  id: number;
  name: string;
  sites?: RawSiteDto[];
}

function extractApiError(err: unknown, fallback: string): string {
  const resData = (err as { response?: { data?: unknown } })?.response?.data;
  if (typeof resData === "string" && resData.trim()) return resData;
  const nested = (resData as { error?: unknown } | undefined)?.error;
  if (typeof nested === "string" && nested.trim()) return nested;
  return fallback;
}

async function loadClients() {
  try {
    const { data } = await axios.get<RawClientDto[]>("/clients/");
    const mapped = (data || []).map((c) => ({
      label: c.name,
      value: c.id,
      sites: (c.sites || []).map((s) => ({ label: s.name, value: s.id })),
    }));
    clientOptions.value = mapped;
    if (mapped.length) {
      selectedClient.value = mapped[0];
      selectedSite.value = mapped[0].sites[0] || null;
    }
  } catch {
    // Non-fatal if user lacks client list permission
  }
}

function onClientChanged() {
  selectedSite.value = siteOptions.value[0] || null;
}

function selectAllMissing() {
  selectedRows.value = [...allMissingFilteredRows.value];
}

async function loadAudit(probeId?: string) {
  loading.value = true;
  errorMsg.value = "";
  try {
    const idToUse = typeof probeId === "string" ? probeId : selectedProbeId.value;
    const res = await fetchADDirectoryAudit({
      probeAgentId: idToUse || undefined,
      ldapServer: ldapServer.value.trim() || undefined,
      username: pushUsername.value.trim() || undefined,
      password: pushPassword.value || undefined,
    });
    report.value = res;
    if (res.probe_agent?.agent_id) {
      selectedProbeId.value = res.probe_agent.agent_id;
    }
    selectedRows.value = [];
  } catch (e: unknown) {
    const data = (e as { response?: { data?: Partial<ADDirectoryAuditReport> } })?.response?.data;
    if (data?.available_probes && !report.value) {
      report.value = {
        ok: false,
        domain: "",
        netbios: "",
        default_nc: "",
        probe_agent: data.probe_agent || { agent_id: "", hostname: "", client: "", site: "" },
        available_probes: data.available_probes,
        summary: {
          total_ad: 0,
          enabled_ad: 0,
          disabled_ad: 0,
          present_in_tactical: 0,
          online_in_tactical: 0,
          offline_in_tactical: 0,
          missing_from_tactical: 0,
          missing_enabled: 0,
          missing_active_90d: 0,
          default_container_missing: 0,
          root_domain_missing: 0,
        },
        folder_summary: [],
        diagnostics: [],
        computers: [],
        timestamp: "",
      };
    }
    errorMsg.value = extractApiError(e, "Falha ao consultar o Active Directory.");
  } finally {
    loading.value = false;
  }
}

async function downloadFixedGpoScript() {
  if (!selectedClient.value || !selectedSite.value) return;
  downloadingGpo.value = true;
  try {
    const { data } = await axios.post("/agents/installer/", {
      installMethod: "universal_bundle",
      plat: "universal_all",
      client: selectedClient.value.value,
      site: selectedSite.value.value,
      expires: 87600,
      agenttype: agentType.value,
      power: 0,
      rdp: enableRdp.value ? 1 : 0,
      ping: enablePing.value ? 1 : 0,
      banking_safe: bankingMode.value,
      goarch: "amd64",
      api: getBaseUrl(),
      fileName: "Install-TacticalRMM.ps1",
    });
    const scriptText = data?.ad_gpo_script;
    if (!scriptText) {
      notifyError("Backend não retornou o script GPO.");
      return;
    }
    const blob = new Blob([scriptText], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "Install-TacticalRMM.ps1";
    link.click();
    URL.revokeObjectURL(url);
    notifySuccess("GPO Install-TacticalRMM.ps1 (corrigido) baixada!");
  } catch (e: unknown) {
    notifyError(extractApiError(e, "Erro ao gerar script GPO corrigido."));
  } finally {
    downloadingGpo.value = false;
  }
}

async function onPublishGpoFromProbe() {
  if (!selectedSite.value || !selectedProbeId.value) return;
  publishingGpo.value = true;
  try {
    const res = await publishADGPO({
      mode: "publish_from_probe",
      site_id: selectedSite.value.value,
      probe_agent_id: selectedProbeId.value,
      agent_type: agentType.value,
      rdp: enableRdp.value ? 1 : 0,
      ping: enablePing.value ? 1 : 0,
      banking_mode: bankingMode.value,
      auto_link_gpo: true,
      run_gpupdate: true,
      api: getBaseUrl(),
    });
    notifySuccess(res.message || "GPO e binários publicados no AD/NETLOGON!");
  } catch (e: unknown) {
    notifyError(extractApiError(e, "Erro ao publicar GPO/NETLOGON no AD."));
  } finally {
    publishingGpo.value = false;
  }
}

async function onDownloadAllInOneDcScript() {
  if (!selectedSite.value) return;
  downloadingDcScript.value = true;
  try {
    const res = await publishADGPO({
      mode: "generate_dc_script",
      site_id: selectedSite.value.value,
      agent_type: agentType.value,
      rdp: enableRdp.value ? 1 : 0,
      ping: enablePing.value ? 1 : 0,
      banking_mode: bankingMode.value,
      api: getBaseUrl(),
    });
    if (!res.script) {
      notifyError("Backend não retornou o script completo.");
      return;
    }
    const blob = new Blob([res.script], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = res.filename || "TacticalRMM-Deploy-All-AD.ps1";
    link.click();
    URL.revokeObjectURL(url);
    notifySuccess("Script TacticalRMM-Deploy-All-AD.ps1 baixado! Execute como Admin no DC.");
  } catch (e: unknown) {
    notifyError(extractApiError(e, "Erro ao gerar script completo para o DC."));
  } finally {
    downloadingDcScript.value = false;
  }
}

async function runPushInstall(targets: ADDirectoryComputer[], force = false) {
  if (!selectedSite.value || !targets.length) return;
  pushLoading.value = true;
  pushProgressMsg.value = "";
  pushResults.value = [];

  const allHostnames = targets.map((t) => t.dns_hostname || t.name).filter(Boolean);
  const batchSize = 15;
  try {
    for (let i = 0; i < allHostnames.length; i += batchSize) {
      const batch = allHostnames.slice(i, i + batchSize);
      const batchNum = Math.floor(i / batchSize) + 1;
      const totalBatches = Math.ceil(allHostnames.length / batchSize);
      pushProgressMsg.value = `Executando Push Remoto (lote ${batchNum}/${totalBatches}, ${batch.length} computador(es))...`;
      const res = await pushInstallADComputers({
        hostnames: batch,
        site_id: selectedSite.value.value,
        probe_agent_id: selectedProbeId.value || undefined,
        agent_type: agentType.value,
        rdp: enableRdp.value ? 1 : 0,
        ping: enablePing.value ? 1 : 0,
        power: 0,
        banking_mode: bankingMode.value,
        force_reinstall: force,
        username: pushUsername.value || undefined,
        password: pushPassword.value || undefined,
        api: getBaseUrl(),
      });
      pushResults.value = [...pushResults.value, ...(res.results || [])];
    }

    const okCnt = pushResults.value.filter((r) => r.success).length;
    notifySuccess(
      `Push concluído: ${okCnt} de ${pushResults.value.length} comando(s) aceito(s). Novos agentes aparecerão no painel em ~30s.`,
    );
    await store.dispatch("refreshDashboard");
  } catch (e: unknown) {
    notifyError(extractApiError(e, "Falha ao executar Push Remoto."));
  } finally {
    pushLoading.value = false;
    pushProgressMsg.value = "";
  }
}

function exportCsv() {
  const esc = (v: unknown) => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const headers = [
    "Hostname_AD",
    "DNS_Hostname",
    "Pasta_Grupo",
    "Caminho_OU",
    "Status_Tactical",
    "Habilitado_AD",
    "Sistema_Operacional",
    "Descricao",
    "Ultimo_Logon_AD",
    "Site_Tactical",
  ];
  const lines = [headers.join(";")];
  for (const r of filteredRows.value) {
    lines.push(
      [
        esc(r.name),
        esc(r.dns_hostname),
        esc(r.folder_group),
        esc(r.folder_path),
        esc(r.sync_state),
        esc(r.enabled ? "Sim" : "Não"),
        esc(r.operating_system),
        esc(r.description),
        esc(r.last_logon),
        esc(r.tactical_site || ""),
      ].join(";"),
    );
  }
  const blob = new Blob(["\uFEFF" + lines.join("\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `auditoria-ad-tactical-${report.value?.domain || "dominio"}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

onMounted(async () => {
  await Promise.all([loadClients(), loadAudit()]);
});
</script>
