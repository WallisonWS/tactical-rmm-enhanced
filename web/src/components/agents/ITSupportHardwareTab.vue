<template>
  <div class="q-pa-md">
    <div v-if="!selectedAgentId" class="text-grey text-center q-pa-lg">
      Selecione um agente para acessar a Central de Suporte TI, Inventário de Hardware, Impressoras e GPO.
    </div>

    <div v-else>
      <!-- Top Header & 1-Click Corporate Admin Actions -->
      <div class="row items-center justify-between q-mb-md">
        <div>
          <div class="text-subtitle1 text-weight-bold flex items-center">
            <q-icon name="support_agent" color="primary" size="sm" class="q-mr-sm" />
            {{ t("itsupport.title") }}
          </div>
          <div class="text-caption text-grey">
            {{ t("itsupport.subtitle") }}
          </div>
        </div>
        <div class="row q-gutter-xs">
          <q-btn
            dense
            color="primary"
            icon="refresh"
            :label="t('itsupport.refresh')"
            :loading="loading"
            @click="loadAll"
          />
          <q-btn
            dense
            color="indigo"
            icon="policy"
            :label="t('itsupport.gpupdate')"
            :loading="adminActionLoading"
            @click="onAdminAction('gpupdate_force')"
          />
          <q-btn
            dense
            color="teal"
            icon="schedule"
            :label="t('itsupport.syncTime')"
            :loading="adminActionLoading"
            @click="onAdminAction('sync_time')"
          />
          <q-btn
            dense
            color="amber-9"
            icon="bolt"
            :label="t('itsupport.highPerf')"
            :loading="adminActionLoading"
            @click="onAdminAction('high_performance_power')"
          />
          <q-btn
            dense
            color="deep-orange"
            icon="print_disabled"
            :label="t('itsupport.clearSpooler')"
            :loading="adminActionLoading"
            @click="onAdminAction('clear_print_spooler')"
          />
        </div>
      </div>

      <!-- Hardware, BIOS, Service Tag, Domain & Battery Cards -->
      <div class="row q-col-gutter-md q-mb-md" v-if="hwInventory">
        <div class="col-12 col-md-3">
          <q-card flat bordered class="full-height">
            <q-card-section class="q-pa-sm">
              <div class="text-caption text-grey">Fabricante / Modelo</div>
              <div class="text-subtitle2 text-weight-bold">
                {{ hwInventory.manufacturer || "N/A" }} — {{ hwInventory.model || "N/A" }}
              </div>
              <div class="text-caption q-mt-xs">
                Service Tag / Serial: <q-badge color="primary">{{ hwInventory.serial_number || "N/A" }}</q-badge>
              </div>
              <div class="text-caption text-grey">
                BIOS: {{ hwInventory.bios_version || "N/A" }}
              </div>
            </q-card-section>
          </q-card>
        </div>

        <div class="col-12 col-md-3">
          <q-card flat bordered class="full-height">
            <q-card-section class="q-pa-sm">
              <div class="text-caption text-grey">Domínio AD / Entra ID (Azure AD)</div>
              <div class="text-subtitle2 text-weight-bold">
                {{ hwInventory.domain_or_workgroup || "WORKGROUP" }}
              </div>
              <div class="row q-gutter-xs q-mt-xs">
                <q-badge :color="hwInventory.part_of_domain ? 'positive' : 'grey-7'">
                  {{ hwInventory.part_of_domain ? "Active Directory Joined" : "Workgroup" }}
                </q-badge>
                <q-badge :color="hwInventory.entra_id_joined ? 'info' : 'grey-7'">
                  {{ hwInventory.entra_id_joined ? "Entra ID / AzureAD" : "Local Auth" }}
                </q-badge>
              </div>
            </q-card-section>
          </q-card>
        </div>

        <div class="col-12 col-md-3">
          <q-card flat bordered class="full-height">
            <q-card-section class="q-pa-sm">
              <div class="text-caption text-grey">GPU &amp; Plano de Energia</div>
              <div class="text-body2 text-weight-bold ellipsis">
                {{ hwInventory.gpus?.length ? hwInventory.gpus.join(", ") : "Standard Display Adapter" }}
              </div>
              <div class="text-caption text-grey q-mt-xs ellipsis">
                {{ hwInventory.active_power_plan || "Balanced" }}
              </div>
            </q-card-section>
          </q-card>
        </div>

        <div class="col-12 col-md-3">
          <q-card flat bordered class="full-height">
            <q-card-section class="q-pa-sm">
              <div class="text-caption text-grey">Energia / Bateria &amp; Periféricos</div>
              <div class="text-subtitle2 text-weight-bold">
                <span v-if="hwInventory.battery_present">
                  🔋 {{ hwInventory.battery_charge_pct }}% ({{ hwInventory.battery_status }})
                </span>
                <span v-else>🔌 Desktop / Tomada AC</span>
              </div>
              <div class="text-caption text-grey q-mt-xs">
                Impressoras: <b>{{ printers.length }}</b> &bull; Pontos de Restauração: <b>{{ restorePoints.length }}</b>
              </div>
            </q-card-section>
          </q-card>
        </div>
      </div>

      <!-- Active Directory (GPO) & Non-AD (Workgroup / Standalone Windows Server) Section -->
      <q-card flat bordered class="q-mb-md" v-if="adProfile">
        <q-card-section class="q-pa-sm">
          <div class="row items-center justify-between q-mb-sm">
            <div class="row items-center q-gutter-xs">
              <q-icon name="domain" color="primary" size="sm" />
              <span class="text-subtitle2 text-weight-bold">
                Compatibilidade Híbrida (Golang): Active Directory (GPO) &amp; Unidades Sem AD (Workgroup / Windows Server)
              </span>
              <q-badge :color="adProfile.part_of_domain ? 'positive' : 'blue-grey-7'">
                {{ adProfile.part_of_domain ? `Com AD: ${adProfile.domain_name}` : `Unidade Sem AD (${adProfile.workgroup_name || "WORKGROUP"})` }}
              </q-badge>
              <q-badge :color="adProfile.is_windows_server ? 'deep-purple' : 'teal'">
                {{ adProfile.domain_role_label }}
              </q-badge>
            </div>

            <div class="row q-gutter-xs">
              <q-btn
                dense
                outline
                size="sm"
                color="primary"
                icon="verified_user"
                label="Testar Canal AD / Status Local"
                :loading="adActionLoading"
                @click="onADAction('test_secure_channel')"
              />
              <q-btn
                dense
                outline
                size="sm"
                color="positive"
                icon="build_circle"
                label="Reparar Trust AD / W32Time"
                :loading="adActionLoading"
                @click="onADAction('repair_secure_channel')"
              />
              <q-btn
                dense
                outline
                size="sm"
                color="indigo"
                icon="sync"
                label="GPO / LGPO + DNS"
                :loading="adActionLoading"
                @click="onADAction('gpupdate_registerdns')"
              />
              <q-btn
                dense
                outline
                size="sm"
                color="teal"
                icon="access_time"
                label="NTP Unidade Sem AD"
                :loading="adActionLoading"
                @click="onADAction('sync_standalone_ntp')"
              />
              <q-btn
                dense
                outline
                size="sm"
                color="deep-purple"
                icon="dns"
                label="Diag Windows Server"
                :loading="adActionLoading"
                @click="onADAction('dcdiag_server_health')"
              />
              <q-btn
                dense
                color="secondary"
                size="sm"
                icon="terminal"
                label="Modo Instalação GPO / Sem AD"
                :loading="adActionLoading"
                @click="onADAction('generate_deploy_info')"
              />
            </div>
          </div>

          <div class="row q-col-gutter-sm">
            <div class="col-12 col-md-4">
              <div class="text-caption text-grey">Controlador de Domínio / Grupo de Trabalho</div>
              <div class="text-body2 text-weight-medium" v-if="adProfile.part_of_domain">
                DC: {{ adProfile.domain_controller_name || "Auto" }}
                <span v-if="adProfile.domain_controller_address">({{ adProfile.domain_controller_address }})</span>
              </div>
              <div class="text-body2 text-weight-medium" v-else>
                Workgroup: {{ adProfile.workgroup_name || "WORKGROUP" }} (Modo Standalone)
              </div>
              <div class="text-caption text-grey">
                OU / Local: {{ adProfile.organizational_unit || adProfile.site_name || "Padrão" }}
              </div>
            </div>

            <div class="col-12 col-md-4">
              <div class="text-caption text-grey">Saúde de Domínio / Sincronismo de Horário</div>
              <div class="row q-gutter-xs q-mt-xs">
                <q-badge v-if="adProfile.part_of_domain" :color="adProfile.secure_channel_valid ? 'positive' : 'negative'">
                  Trust AD: {{ adProfile.secure_channel_valid ? "OK" : "Verificar" }}
                </q-badge>
                <q-badge v-if="adProfile.part_of_domain" :color="adProfile.sysvol_reachable ? 'positive' : 'warning'">
                  SYSVOL: {{ adProfile.sysvol_reachable ? "OK" : "Indisponível" }}
                </q-badge>
                <q-badge color="blue-grey">
                  NTP: {{ adProfile.time_sync_source || "Local" }}
                </q-badge>
              </div>
            </div>

            <div class="col-12 col-md-4">
              <div class="text-caption text-grey">GPOs Aplicadas / Roles Windows Server</div>
              <div class="text-caption">
                <span v-if="adProfile.installed_server_roles?.length">
                  Roles Server: <b>{{ adProfile.installed_server_roles.join(", ") }}</b>
                </span>
                <span v-else-if="adProfile.applied_computer_gpos?.length">
                  GPOs ({{ adProfile.applied_computer_gpos.length }}): {{ adProfile.applied_computer_gpos.slice(0, 3).join(", ") }}
                </span>
                <span v-else>
                  Tipo Recomendado Go: <b>{{ adProfile.recommended_agent_type }}</b> ({{ adProfile.deployment_mode || "Padrão" }})
                </span>
              </div>
            </div>
          </div>

          <div v-if="deployInfo" class="q-mt-sm q-pa-sm bg-grey-10 text-white rounded-borders">
            <div class="text-caption text-weight-bold text-amber q-mb-xs">
              Parâmetros Nativos do Agente em Golang ({{ deployInfo.client_name }} / {{ deployInfo.site_name }}):
            </div>
            <div class="text-caption font-monospace q-mb-xs">
              <b>Unidades COM Active Directory (GPO):</b> tacticalagent.exe {{ deployInfo.go_ad_gpo_args }}
            </div>
            <div class="text-caption font-monospace">
              <b>Unidades SEM Active Directory (Standalone / Workgroup):</b> tacticalagent.exe {{ deployInfo.go_standalone_args }}
            </div>
          </div>

          <div v-if="adActionOutput" class="q-mt-sm q-pa-sm bg-blue-grey-10 text-white rounded-borders">
            <pre class="q-ma-none text-caption" style="white-space: pre-wrap">{{ adActionOutput }}</pre>
          </div>
        </q-card-section>
      </q-card>

      <!-- LAN Computer Discovery for Non-AD Units (Levantamento de Computadores via Servidor Local) -->
      <q-card flat bordered class="q-mb-md">
        <q-card-section class="q-pa-sm">
          <div class="row items-center justify-between q-mb-sm">
            <div>
              <div class="text-subtitle2 text-weight-bold flex items-center">
                <q-icon name="radar" color="teal" size="sm" class="q-mr-xs" />
                Levantamento de Computadores da Unidade (Via Servidor Local / Sem AD)
              </div>
              <div class="text-caption text-grey">
                Usa o agente Go instalado no servidor da unidade para descobrir todas as máquinas na rede local (Sessões SMB/ pastas compartilhadas, DHCP Leases, Tabela ARP e Scanner LAN Go) e comparar quem já tem o Tactical RMM instalado.
              </div>
            </div>

            <div class="row items-center q-gutter-xs">
              <q-input
                v-model="customDiscoverySubnet"
                dense
                outlined
                placeholder="Sub-rede opcional (ex: 192.168.1.0)"
                style="min-width: 220px"
              />
              <q-btn
                dense
                color="teal"
                icon="travel_explore"
                label="Executar Levantamento da Unidade"
                :loading="lanDiscoveryLoading"
                @click="onRunLANDiscovery"
              />
            </div>
          </div>

          <div v-if="lanDiscoveryReport" class="row q-gutter-sm q-mb-sm items-center">
            <q-badge color="primary" class="q-pa-xs">
              Sub-redes: {{ lanDiscoveryReport.local_subnets?.join(", ") || "Auto" }}
            </q-badge>
            <q-badge color="blue-grey-8" class="q-pa-xs">
              Total na Rede: {{ lanDiscoveryReport.total_found }}
            </q-badge>
            <q-badge color="teal-8" class="q-pa-xs">
              Computadores Identificados: {{ lanDiscoveryReport.computers_count }}
            </q-badge>
            <q-badge color="positive" class="q-pa-xs">
              Já Cadastrados no RMM: {{ lanDiscoveryReport.registered_count || 0 }}
            </q-badge>
            <q-badge color="warning" text-color="black" class="q-pa-xs">
              Faltando Instalar Agente: {{ lanDiscoveryReport.unregistered_count || 0 }}
            </q-badge>
          </div>

          <q-table
            v-if="lanDiscoveryReport"
            dense
            flat
            :rows="lanDiscoveryReport.hosts || []"
            :columns="lanDiscoveryColumns"
            row-key="ip_address"
            :pagination="{ rowsPerPage: 10 }"
            no-data-label="Nenhum host encontrado na sub-rede"
          >
            <template v-slot:body-cell-rmm_status="props">
              <q-td :props="props">
                <q-badge v-if="props.row.registered_in_rmm" color="positive">
                  Instalado ({{ props.row.rmm_hostname || "Ativo" }})
                </q-badge>
                <q-badge v-else color="warning" text-color="black">
                  Pendente no RMM
                </q-badge>
              </q-td>
            </template>
            <template v-slot:body-cell-discovery_source="props">
              <q-td :props="props">
                {{ (props.row.discovery_source || []).join(" + ") }}
              </q-td>
            </template>
            <template v-slot:body-cell-open_services="props">
              <q-td :props="props">
                {{ (props.row.open_services || []).join(", ") || "-" }}
              </q-td>
            </template>
          </q-table>
        </q-card-section>
      </q-card>

      <!-- On-Screen IT Helpdesk Broadcast & System Restore Checkpoint Row -->
      <div class="row q-col-gutter-md q-mb-md">
        <!-- IT Helpdesk Broadcast -->
        <div class="col-12 col-md-6">
          <q-card flat bordered class="full-height">
            <q-card-section class="q-pa-sm">
              <div class="text-subtitle2 text-weight-bold flex items-center q-mb-xs">
                <q-icon name="campaign" color="primary" class="q-mr-xs" />
                {{ t("itsupport.msgSection") }}
              </div>
              <div class="row q-col-gutter-sm items-center">
                <div class="col-12 col-sm-4">
                  <q-input
                    v-model="msgTitle"
                    dense
                    outlined
                    :label="t('itsupport.msgTitle')"
                  />
                </div>
                <div class="col-12 col-sm-5">
                  <q-input
                    v-model="msgBody"
                    dense
                    outlined
                    :label="t('itsupport.msgBody')"
                    @keyup.enter="onSendBroadcast"
                  />
                </div>
                <div class="col-12 col-sm-3">
                  <q-btn
                    dense
                     color="primary"
                    icon="send"
                    class="full-width"
                    :label="t('itsupport.sendMsg')"
                    :loading="sendingMsg"
                    @click="onSendBroadcast"
                  />
                </div>
              </div>
            </q-card-section>
          </q-card>
        </div>

        <!-- System Restore Checkpoint Creator -->
        <div class="col-12 col-md-6">
          <q-card flat bordered class="full-height">
            <q-card-section class="q-pa-sm">
              <div class="text-subtitle2 text-weight-bold flex items-center q-mb-xs">
                <q-icon name="restore" color="positive" class="q-mr-xs" />
                {{ t("itsupport.restoreSection") }}
              </div>
              <div class="row q-col-gutter-sm items-center">
                <div class="col-12 col-sm-8">
                  <q-input
                    v-model="restoreDescription"
                    dense
                    outlined
                    label="Descrição do Ponto de Restauração (Antes da Manutenção)"
                  />
                </div>
                <div class="col-12 col-sm-4">
                  <q-btn
                    dense
                    color="positive"
                    icon="add_task"
                    class="full-width"
                    :label="t('itsupport.createRestore')"
                    :loading="creatingRestore"
                    @click="onCreateRestorePoint"
                  />
                </div>
              </div>
            </q-card-section>
          </q-card>
        </div>
      </div>

      <!-- Printers & Print Queue Table -->
      <q-card flat bordered class="q-mb-md">
        <q-card-section class="q-pa-sm">
          <div class="text-subtitle2 text-weight-bold flex items-center q-mb-xs">
            <q-icon name="print" color="primary" class="q-mr-xs" />
            {{ t("itsupport.printersSection") }}
          </div>
          <q-table
            dense
            flat
            :rows="printers"
            :columns="printerColumns"
            row-key="name"
            :pagination="{ rowsPerPage: 8 }"
            no-data-label="Nenhuma impressora detectada neste computador"
          >
            <template v-slot:body-cell-actions="props">
              <q-td :props="props" class="q-gutter-xs">
                <q-btn
                  dense
                  flat
                  size="sm"
                  color="primary"
                  icon="star"
                  label="Definir Padrão"
                  @click="onPrinterAction('set_default', props.row.name)"
                />
                <q-btn
                  dense
                  flat
                  size="sm"
                  color="warning"
                  icon="cleaning_services"
                  label="Limpar Fila"
                  @click="onPrinterAction('clear_queue', props.row.name)"
                />
                <q-btn
                  dense
                  flat
                  size="sm"
                  color="teal"
                  icon="description"
                  label="Página Teste"
                  @click="onPrinterAction('test_page', props.row.name)"
                />
              </q-td>
            </template>
          </q-table>
        </q-card-section>
      </q-card>

      <!-- System Restore Points List -->
      <q-card flat bordered v-if="restorePoints.length > 0">
        <q-card-section class="q-pa-sm">
          <div class="text-subtitle2 text-weight-bold q-mb-xs">
            Histórico de Pontos de Restauração do Windows
          </div>
          <q-table
            dense
            flat
            :rows="restorePoints"
            :columns="restoreColumns"
            row-key="sequence_number"
            :pagination="{ rowsPerPage: 5 }"
          />
        </q-card-section>
      </q-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from "vue";
import { useStore } from "vuex";
import { useI18n } from "@/i18n";
import {
  fetchAgentHardwareInventory,
  runAgentAdminAction,
  fetchAgentPrinters,
  runAgentPrinterAction,
  fetchAgentRestorePoints,
  createAgentRestorePoint,
  sendAgentITSupportMessage,
  fetchAgentADServerStatus,
  runAgentADServerAction,
  runAgentLANDiscovery,
  type HardwareDomainInventory,
  type PrinterInfo,
  type RestorePointInfo,
  type WindowsServerADProfile,
  type UnitLANDiscoveryReport,
} from "@/api/enhanced";
import { notifySuccess, notifyError } from "@/utils/notify";

const props = defineProps<{
  agentId?: string;
}>();

const store = useStore();
const { t } = useI18n();

const selectedAgentId = computed<string>(
  () => props.agentId || store.state.selectedRow || "",
);

const loading = ref(false);
const adminActionLoading = ref(false);
const adActionLoading = ref(false);
const sendingMsg = ref(false);
const creatingRestore = ref(false);

const hwInventory = ref<HardwareDomainInventory | null>(null);
const adProfile = ref<WindowsServerADProfile | null>(null);
const adActionOutput = ref("");
const deployInfo = ref<any | null>(null);
const lanDiscoveryLoading = ref(false);
const customDiscoverySubnet = ref("");
const lanDiscoveryReport = ref<UnitLANDiscoveryReport | null>(null);
const printers = ref<PrinterInfo[]>([]);
const restorePoints = ref<RestorePointInfo[]>([]);

const lanDiscoveryColumns = [
  { name: "ip_address", label: "Endereço IP", field: "ip_address", align: "left" as const, sortable: true },
  { name: "hostname", label: "Hostname / Nome na Rede", field: "hostname", align: "left" as const, sortable: true },
  { name: "estimated_type", label: "Tipo Identificado", field: "estimated_type", align: "left" as const, sortable: true },
  { name: "smb_user", label: "Usuário Conectado (SMB)", field: "smb_user", align: "left" as const },
  { name: "mac_address", label: "Endereço MAC", field: "mac_address", align: "left" as const },
  { name: "discovery_source", label: "Origem da Descoberta", field: "discovery_source", align: "left" as const },
  { name: "open_services", label: "Serviços Detectados", field: "open_services", align: "left" as const },
  { name: "rmm_status", label: "Status no Tactical RMM", field: "registered_in_rmm", align: "center" as const, sortable: true },
];

const msgTitle = ref("Suporte de TI");
const msgBody = ref("Olá! A equipe de TI está realizando uma manutenção rápida no seu computador.");
const restoreDescription = ref("Checkpoint Preventivo Suporte TI");

const printerColumns = [
  { name: "name", label: "Impressora", field: "name", align: "left" as const, sortable: true },
  { name: "driver_name", label: "Driver", field: "driver_name", align: "left" as const },
  { name: "port_name", label: "Porta / IP", field: "port_name", align: "left" as const },
  { name: "printer_status", label: "Status", field: "printer_status", align: "left" as const },
  { name: "job_count", label: "Documentos na Fila", field: "job_count", align: "center" as const },
  { name: "actions", label: "Ações de Suporte", field: "actions", align: "right" as const },
];

const restoreColumns = [
  { name: "sequence_number", label: "Seq #", field: "sequence_number", align: "left" as const },
  { name: "description", label: "Descrição", field: "description", align: "left" as const },
  { name: "creation_time", label: "Data de Criação", field: "creation_time", align: "left" as const },
  { name: "event_type", label: "Tipo", field: "event_type", align: "left" as const },
];

async function loadAll() {
  if (!selectedAgentId.value) return;
  loading.value = true;
  try {
    const [hw, prn, rp, ad] = await Promise.all([
      fetchAgentHardwareInventory(selectedAgentId.value),
      fetchAgentPrinters(selectedAgentId.value),
      fetchAgentRestorePoints(selectedAgentId.value),
      fetchAgentADServerStatus(selectedAgentId.value),
    ]);
    hwInventory.value = hw;
    printers.value = Array.isArray(prn) ? prn : [];
    restorePoints.value = rp?.restore_points || [];
    adProfile.value = ad;
  } catch (e: any) {
    notifyError(e?.response?.data?.error || "Falha ao carregar dados de suporte e hardware");
  } finally {
    loading.value = false;
  }
}

async function onADAction(
  action:
    | "test_secure_channel"
    | "repair_secure_channel"
    | "gpupdate_registerdns"
    | "sync_standalone_ntp"
    | "dcdiag_server_health"
    | "generate_deploy_info",
) {
  if (!selectedAgentId.value) return;
  adActionLoading.value = true;
  try {
    const res = await runAgentADServerAction(selectedAgentId.value, action);
    if (action === "generate_deploy_info") {
      deployInfo.value = res;
      notifySuccess("Parâmetros de instalação Golang (AD GPO e Unidade Sem AD) gerados!");
      return;
    }
    if (res?.ad_profile) {
      adProfile.value = res.ad_profile;
    }
    adActionOutput.value = res?.output || (res?.steps || []).join("\n");
    notifySuccess(res?.steps?.[0] || `Operação (${action}) executada com sucesso!`);
  } catch (e: any) {
    notifyError(e?.response?.data?.error || `Erro ao executar ${action}`);
  } finally {
    adActionLoading.value = false;
  }
}

async function onRunLANDiscovery() {
  if (!selectedAgentId.value) return;
  lanDiscoveryLoading.value = true;
  try {
    const res = await runAgentLANDiscovery(
      selectedAgentId.value,
      customDiscoverySubnet.value.trim(),
    );
    lanDiscoveryReport.value = res;
    notifySuccess(
      `Levantamento concluído: ${res.total_found} dispositivos encontrados (${res.unregistered_count || 0} pendentes no RMM).`,
    );
  } catch (e: any) {
    notifyError(
      e?.response?.data?.error || "Falha ao executar levantamento LAN na unidade",
    );
  } finally {
    lanDiscoveryLoading.value = false;
  }
}

async function onAdminAction(
  action: "gpupdate_force" | "high_performance_power" | "sync_time" | "clear_print_spooler",
) {
  if (!selectedAgentId.value) return;
  adminActionLoading.value = true;
  try {
    const res = await runAgentAdminAction(selectedAgentId.value, action);
    notifySuccess(res?.steps?.[0] || `Ação (${action}) concluída com sucesso!`);
    await loadAll();
  } catch (e: any) {
    notifyError(e?.response?.data?.error || `Erro ao executar ${action}`);
  } finally {
    adminActionLoading.value = false;
  }
}

async function onPrinterAction(
  action: "clear_queue" | "set_default" | "test_page",
  printerName: string,
) {
  if (!selectedAgentId.value) return;
  try {
    const res = await runAgentPrinterAction(selectedAgentId.value, action, printerName);
    if (Array.isArray(res?.printers)) {
      printers.value = res.printers;
    }
    notifySuccess(res?.message || `Ação '${action}' aplicada em ${printerName}`);
  } catch (e: any) {
    notifyError(e?.response?.data?.error || "Erro ao gerenciar impressora");
  }
}

async function onSendBroadcast() {
  if (!selectedAgentId.value || !msgBody.value.trim()) return;
  sendingMsg.value = true;
  try {
    await sendAgentITSupportMessage(selectedAgentId.value, msgTitle.value, msgBody.value, 60);
    notifySuccess("Mensagem exibida na tela do usuário com sucesso!");
  } catch (e: any) {
    notifyError(e?.response?.data?.error || "Falha ao enviar mensagem para a tela do usuário");
  } finally {
    sendingMsg.value = false;
  }
}

async function onCreateRestorePoint() {
  if (!selectedAgentId.value) return;
  creatingRestore.value = true;
  try {
    const res = await createAgentRestorePoint(
      selectedAgentId.value,
      restoreDescription.value || "Checkpoint Preventivo Suporte TI",
    );
    if (Array.isArray(res?.restore_points)) {
      restorePoints.value = res.restore_points;
    }
    notifySuccess(res?.message || "Ponto de Restauração criado com sucesso!");
  } catch (e: any) {
    notifyError(e?.response?.data?.error || "Falha ao criar Ponto de Restauração");
  } finally {
    creatingRestore.value = false;
  }
}

watch(selectedAgentId, (newVal) => {
  if (newVal) {
    loadAll();
  }
});

onMounted(() => {
  if (selectedAgentId.value) {
    loadAll();
  }
});
</script>
