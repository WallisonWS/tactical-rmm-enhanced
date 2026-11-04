<template>
  <div class="q-pa-md">
    <div v-if="!selectedAgentId" class="text-grey text-center q-pa-lg">
      Selecione um agente para gerenciar a Alta Disponibilidade (Agent ↔ API ↔ Mesh) e o Acesso RDP Corporativo.
    </div>

    <div v-else>
      <!-- Top Action Bar -->
      <div class="row items-center justify-between q-mb-md">
        <div>
          <div class="text-subtitle1 text-weight-bold flex items-center">
            <q-icon name="desktop_windows" color="primary" size="sm" class="q-mr-sm" />
            {{ t("rdpha.title") }}
          </div>
          <div class="text-caption text-grey">
            {{ t("rdpha.subtitle") }}
          </div>
        </div>
        <div class="row q-gutter-sm">
          <q-btn
            dense
            color="primary"
            icon="sync"
            :label="t('rdpha.refresh')"
            :loading="loading"
            @click="loadAll"
          />
          <q-btn
            dense
            color="deep-orange"
            icon="build_circle"
            :label="t('rdpha.repairLink')"
            :loading="repairing"
            @click="onRepairLink"
          />
        </div>
      </div>

      <!-- High Availability (Agent <-> API <-> NATS <-> Mesh) Cards -->
      <div class="row q-col-gutter-md q-mb-md" v-if="haHealth">
        <!-- Agent <-> API HTTPS -->
        <div class="col-12 col-md-4">
          <q-card flat bordered>
            <q-card-section class="row items-center justify-between">
              <div>
                <div class="text-caption text-grey">{{ t("rdpha.apiChannel") }}</div>
                <div
                  class="text-subtitle1 text-weight-bold"
                  :class="haHealth.api_reachable ? 'text-positive' : 'text-negative'"
                >
                  {{ haHealth.api_reachable ? t("rdpha.reachable") : t("rdpha.unreachable") }}
                </div>
                <div class="text-caption">
                  {{ t("rdpha.latency") }}: <b>{{ haHealth.api_latency_ms }} ms</b>
                  <span v-if="haHealth.proxy_configured" class="q-ml-xs text-info">
                    (Proxy: {{ haHealth.proxy_url }})
                  </span>
                </div>
              </div>
              <q-icon
                :name="haHealth.api_reachable ? 'cloud_done' : 'cloud_off'"
                :color="haHealth.api_reachable ? 'positive' : 'negative'"
                size="md"
              />
            </q-card-section>
          </q-card>
        </div>

        <!-- Agent <-> NATS RPC -->
        <div class="col-12 col-md-4">
          <q-card flat bordered>
            <q-card-section class="row items-center justify-between">
              <div>
                <div class="text-caption text-grey">{{ t("rdpha.natsChannel") }}</div>
                <div
                  class="text-subtitle1 text-weight-bold"
                  :class="haHealth.nats_reachable ? 'text-positive' : 'text-negative'"
                >
                  {{ haHealth.nats_reachable ? t("rdpha.reachable") : t("rdpha.unreachable") }}
                </div>
                <div class="text-caption">
                  {{ t("rdpha.latency") }}: <b>{{ haHealth.nats_latency_ms }} ms</b>
                  <span v-if="haHealth.nats_transport" class="q-ml-xs text-grey">
                    ({{ haHealth.nats_transport }})
                  </span>
                </div>
              </div>
              <q-icon
                :name="haHealth.nats_reachable ? 'bolt' : 'warning'"
                :color="haHealth.nats_reachable ? 'positive' : 'negative'"
                size="md"
              />
            </q-card-section>
          </q-card>
        </div>

        <!-- MeshCentral Service -->
        <div class="col-12 col-md-4">
          <q-card flat bordered>
            <q-card-section class="row items-center justify-between">
              <div>
                <div class="text-caption text-grey">{{ t("rdpha.meshChannel") }}</div>
                <div
                  class="text-subtitle1 text-weight-bold"
                  :class="haHealth.mesh_healthy ? 'text-positive' : 'text-warning'"
                >
                  {{ haHealth.mesh_service_status }}
                </div>
                <div class="text-caption">
                  Status Global: <q-badge :color="haHealth.overall_status === 'HEALTHY' ? 'positive' : 'warning'">{{ haHealth.overall_status }}</q-badge>
                  <q-badge v-if="haHealth.mesh_id_synced || haHealth.mesh_node_id" color="teal" class="q-ml-xs">
                    NodeID Synced
                  </q-badge>
                </div>
              </div>
              <q-icon
                :name="haHealth.mesh_healthy ? 'verified_user' : 'report_problem'"
                :color="haHealth.mesh_healthy ? 'positive' : 'warning'"
                size="md"
              />
            </q-card-section>
          </q-card>
        </div>
      </div>

      <!-- Corporate RDP Control Panel -->
      <q-card flat bordered class="q-mb-md" v-if="rdpStatus">
        <q-card-section>
          <div class="row items-center justify-between q-mb-sm">
            <div class="text-subtitle2 text-weight-bold flex items-center">
              <q-icon name="computer" color="primary" class="q-mr-xs" />
              {{ t("rdpha.rdpSection") }}
            </div>
            <div class="row q-gutter-sm">
              <q-btn
                dense
                color="positive"
                icon="lock"
                :label="t('rdpha.enableRdp')"
                :loading="rdpActionLoading"
                @click="onManageRDP('enable_rdp', true)"
              />
              <q-btn
                dense
                color="negative"
                outline
                icon="block"
                :label="t('rdpha.disableRdp')"
                :loading="rdpActionLoading"
                @click="onManageRDP('disable_rdp', true)"
              />
              <q-btn
                dense
                color="secondary"
                outline
                icon="restart_alt"
                :label="t('rdpha.restartRdp')"
                :loading="rdpActionLoading"
                @click="onManageRDP('restart_rdp', true)"
              />
              <q-btn
                dense
                color="primary"
                icon="download"
                :label="t('rdpha.downloadRdp')"
                @click="onDownloadRDP"
              />
              <q-btn
                dense
                color="indigo"
                icon="screen_share"
                :label="t('rdpha.openTakeControl')"
                @click="onOpenTakeControl"
              />
            </div>
          </div>

          <q-separator class="q-my-sm" />

          <div class="row q-col-gutter-md items-center">
            <div class="col-6 col-md-3">
              <div class="text-caption text-grey">{{ t("rdpha.rdpStatus") }}</div>
              <q-chip
                dense
                :color="rdpStatus.rdp_enabled ? 'positive' : 'grey-7'"
                text-color="white"
                :icon="rdpStatus.rdp_enabled ? 'check_circle' : 'cancel'"
              >
                {{ rdpStatus.rdp_enabled ? t("rdpha.enabled") : t("rdpha.disabled") }}
                ({{ rdpStatus.service_status }})
              </q-chip>
            </div>
            <div class="col-6 col-md-3">
              <div class="text-caption text-grey">{{ t("rdpha.nlaStatus") }}</div>
              <q-chip
                dense
                :color="rdpStatus.nla_enabled ? 'teal' : 'orange'"
                text-color="white"
                icon="security"
              >
                {{ rdpStatus.nla_enabled ? "NLA Ativo (CredSSP)" : "NLA Inativo" }}
              </q-chip>
            </div>
            <div class="col-6 col-md-3">
              <div class="text-caption text-grey">{{ t("rdpha.rdpPort") }}</div>
              <div class="text-body2 text-weight-bold">
                TCP {{ rdpStatus.listening_port }}
                <q-badge :color="rdpStatus.port_reachable ? 'positive' : 'warning'" class="q-ml-xs">
                  {{ rdpStatus.port_reachable ? "Listening" : "Closed" }}
                </q-badge>
              </div>
            </div>
            <div class="col-6 col-md-3">
              <q-select
                v-model="selectedTargetIP"
                :options="availableIPs"
                dense
                outlined
                label="IP / Host para Conexão .RDP"
              />
            </div>
          </div>
        </q-card-section>
      </q-card>

      <!-- Active User Sessions Table -->
      <q-card flat bordered v-if="rdpStatus">
        <q-card-section class="q-pa-sm">
          <div class="text-subtitle2 q-px-sm q-pt-xs q-mb-xs">
            {{ t("rdpha.activeSessions") }}
          </div>
          <q-table
            dense
            flat
            :rows="rdpStatus.active_sessions || []"
            :columns="sessionColumns"
            row-key="id"
            :pagination="{ rowsPerPage: 10 }"
            no-data-label="Nenhuma sessão interativa ativa no momento"
          >
            <template v-slot:body-cell-actions="props">
              <q-td :props="props">
                <q-btn
                  dense
                  flat
                  size="sm"
                  color="negative"
                  icon="logout"
                  :label="t('rdpha.logoff')"
                  @click="onManageRDP('logoff_session', true, props.row.id)"
                />
              </q-td>
            </template>
          </q-table>
        </q-card-section>
      </q-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from "vue";
import { useStore } from "vuex";
import { useRouter } from "vue-router";
import { useI18n } from "@/i18n";
import {
  fetchAgentHALinkHealth,
  repairAgentHALink,
  fetchAgentRDPStatus,
  manageAgentRDP,
  downloadNativeRDPFile,
  type HALinkHealthReport,
  type CorporateRDPStatus,
} from "@/api/enhanced";
import { notifySuccess, notifyError } from "@/utils/notify";

const props = defineProps<{
  agentId?: string;
}>();

const store = useStore();
const router = useRouter();
const { t } = useI18n();

const selectedAgentId = computed<string>(
  () => props.agentId || store.state.selectedRow || "",
);

const loading = ref(false);
const repairing = ref(false);
const rdpActionLoading = ref(false);
const haHealth = ref<HALinkHealthReport | null>(null);
const rdpStatus = ref<CorporateRDPStatus | null>(null);
const selectedTargetIP = ref("");

const availableIPs = computed<string[]>(() => {
  const list: string[] = [];
  if (rdpStatus.value?.local_ips?.length) {
    list.push(...rdpStatus.value.local_ips);
  }
  if (rdpStatus.value?.hostname && !list.includes(rdpStatus.value.hostname)) {
    list.push(rdpStatus.value.hostname);
  }
  if (rdpStatus.value?.public_ip && !list.includes(rdpStatus.value.public_ip)) {
    list.push(rdpStatus.value.public_ip);
  }
  return list.length ? list : ["127.0.0.1"];
});

const sessionColumns = computed(() => [
  { name: "session_name", label: t("rdpha.sessionName"), field: "session_name", align: "left" as const },
  { name: "username", label: t("rdpha.username"), field: "username", align: "left" as const },
  { name: "id", label: t("rdpha.sessionId"), field: "id", align: "left" as const },
  { name: "state", label: t("rdpha.state"), field: "state", align: "left" as const },
  { name: "actions", label: t("rdpha.actions"), field: "actions", align: "right" as const },
]);

async function loadAll() {
  if (!selectedAgentId.value) return;
  loading.value = true;
  try {
    const [ha, rdp] = await Promise.all([
      fetchAgentHALinkHealth(selectedAgentId.value),
      fetchAgentRDPStatus(selectedAgentId.value),
    ]);
    haHealth.value = ha;
    rdpStatus.value = rdp;
    if (!selectedTargetIP.value && availableIPs.value.length > 0) {
      selectedTargetIP.value = availableIPs.value[0];
    }
  } catch (e: any) {
    notifyError(e?.response?.data?.error || "Falha ao consultar status HA/RDP do agente");
  } finally {
    loading.value = false;
  }
}

async function onRepairLink() {
  if (!selectedAgentId.value) return;
  repairing.value = true;
  try {
    const res = await repairAgentHALink(selectedAgentId.value);
    if (res?.health_after) {
      haHealth.value = res.health_after;
    }
    notifySuccess("Serviço Mesh e conectividade do agente ressincronizados com sucesso!");
  } catch (e: any) {
    notifyError(e?.response?.data?.error || "Erro ao reparar conectividade do agente");
  } finally {
    repairing.value = false;
  }
}

async function onManageRDP(
  action: "enable_rdp" | "disable_rdp" | "restart_rdp" | "logoff_session",
  enforceNLA = true,
  sessionId = "",
) {
  if (!selectedAgentId.value) return;
  rdpActionLoading.value = true;
  try {
    const res = await manageAgentRDP(selectedAgentId.value, action, enforceNLA, sessionId);
    if (res?.rdp_status) {
      rdpStatus.value = res.rdp_status;
    } else {
      await loadAll();
    }
    notifySuccess(`Operação RDP (${action}) concluída com sucesso!`);
  } catch (e: any) {
    notifyError(e?.response?.data?.error || `Falha ao executar ação RDP: ${action}`);
  } finally {
    rdpActionLoading.value = false;
  }
}

function onDownloadRDP() {
  const host = selectedTargetIP.value || availableIPs.value[0] || "127.0.0.1";
  const port = rdpStatus.value?.listening_port || 3389;
  const hostname = rdpStatus.value?.hostname || haHealth.value?.hostname || host;
  downloadNativeRDPFile(hostname, host, port);
  notifySuccess(`Arquivo ${hostname}.rdp gerado para conexão remota!`);
}

function onOpenTakeControl() {
  if (!selectedAgentId.value) return;
  const url = router.resolve({
    name: "TakeControl",
    params: { pk: selectedAgentId.value },
  }).href;
  window.open(url, "", "scrollbars=no,location=no,status=no,toolbar=no,menubar=no,width=1600,height=900");
}

watch(selectedAgentId, (newVal) => {
  if (newVal) {
    selectedTargetIP.value = "";
    loadAll();
  }
});

onMounted(() => {
  if (selectedAgentId.value) {
    loadAll();
  }
});
</script>
