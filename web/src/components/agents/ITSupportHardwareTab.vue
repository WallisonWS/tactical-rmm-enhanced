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
  type HardwareDomainInventory,
  type PrinterInfo,
  type RestorePointInfo,
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
const sendingMsg = ref(false);
const creatingRestore = ref(false);

const hwInventory = ref<HardwareDomainInventory | null>(null);
const printers = ref<PrinterInfo[]>([]);
const restorePoints = ref<RestorePointInfo[]>([]);

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
    const [hw, prn, rp] = await Promise.all([
      fetchAgentHardwareInventory(selectedAgentId.value),
      fetchAgentPrinters(selectedAgentId.value),
      fetchAgentRestorePoints(selectedAgentId.value),
    ]);
    hwInventory.value = hw;
    printers.value = Array.isArray(prn) ? prn : [];
    restorePoints.value = rp?.restore_points || [];
  } catch (e: any) {
    notifyError(e?.response?.data?.error || "Falha ao carregar dados de suporte e hardware");
  } finally {
    loading.value = false;
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
