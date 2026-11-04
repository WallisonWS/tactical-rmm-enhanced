<template>
  <div v-if="!selectedAgent" class="q-pa-sm">{{ t("common.noAgentSelected") }}</div>
  <div v-else class="q-pa-sm">
    <q-bar dense style="background-color: transparent">
      <q-btn
        dense
        flat
        icon="lan"
        :label="t('net.activeConns')"
        no-caps
        :loading="loadingConns"
        @click="loadConnections"
      />
      <q-input
        v-model="diagTarget"
        dense
        outlined
        :label="t('net.targetHost')"
        style="width: 180px"
        class="q-ml-sm"
      />
      <q-btn
        dense
        unelevated
        color="primary"
        icon="network_check"
        :label="t('net.runDiag')"
        no-caps
        class="q-ml-xs"
        :loading="loadingDiag"
        @click="execNetDiag"
      />
      <q-btn
        dense
        unelevated
        color="secondary"
        icon="radar"
        :label="t('net.portScan')"
        no-caps
        class="q-ml-xs"
        :loading="loadingScan"
        @click="execPortScan"
      />
      <q-space />
      <q-input
        v-model="filterText"
        dense
        outlined
        clearable
        :placeholder="t('net.filterPlaceholder')"
        style="width: 240px"
      />
    </q-bar>
    <q-separator class="q-my-xs" />

    <div class="row q-col-gutter-md q-mt-xs">
      <!-- Active Sockets Table -->
      <div class="col-12 col-md-7">
        <q-table
          dense
          flat
          bordered
          :title="t('net.tableTitle')"
          :rows="connections"
          :columns="columns"
          :filter="filterText"
          row-key="local_port"
          :pagination="{ rowsPerPage: 10 }"
          :loading="loadingConns"
        />
      </div>

      <!-- Diagnostics & Port Scanner Output -->
      <div class="col-12 col-md-5">
        <q-card flat bordered class="q-mb-sm" v-if="diagResult">
          <q-card-section class="q-pa-sm">
            <div class="text-subtitle2 text-weight-bold">
              Network Diagnostics: {{ diagResult.target }}
            </div>
            <div class="row q-gutter-xs q-my-xs">
              <q-badge :color="diagResult.ping_success ? 'positive' : 'negative'">
                ICMP Ping: {{ diagResult.ping_success ? "OK" : "Failed" }}
              </q-badge>
              <q-badge color="info">
                DNS: {{ diagResult.dns_latency_ms }} ms
              </q-badge>
              <q-badge :color="diagResult.tcp_80_reachable ? 'positive' : 'grey'">
                TCP/80: {{ diagResult.tcp_80_reachable ? "Open" : "Closed" }}
              </q-badge>
              <q-badge :color="diagResult.tcp_443_reachable ? 'positive' : 'grey'">
                TCP/443: {{ diagResult.tcp_443_reachable ? "Open" : "Closed" }}
              </q-badge>
            </div>
            <div class="text-caption">
              <b>Public IP:</b> {{ diagResult.public_ip }} &bull;
              <b>LAN IPs:</b> {{ (diagResult.local_ips || []).join(", ") }}
            </div>
          </q-card-section>
        </q-card>

        <q-card flat bordered v-if="scanResult">
          <q-card-section class="q-pa-sm">
            <div class="text-subtitle2 text-weight-bold">
              Port Scan: {{ scanResult.host }} ({{ scanResult.open_ports.length }} open of {{ scanResult.scanned_count }} scanned in {{ scanResult.duration_ms }} ms)
            </div>
            <q-list dense separator class="q-mt-xs">
              <q-item v-for="p in scanResult.open_ports" :key="p.port">
                <q-item-section>
                  <q-item-label class="text-weight-bold">
                    {{ p.protocol }} / {{ p.port }} ({{ p.service }})
                  </q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-badge color="positive">{{ p.latency_ms }} ms</q-badge>
                </q-item-section>
              </q-item>
            </q-list>
          </q-card-section>
        </q-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from "vue";
import { useStore } from "vuex";
import {
  fetchAgentNetConnections,
  runAgentNetDiag,
  runAgentPortScan,
  type NetConnectionInfo,
  type NetDiagReport,
  type PortScanResult,
} from "@/api/enhanced";
import { notifyError } from "@/utils/notify";
import { useI18n } from "@/i18n";

const { t } = useI18n();
const store = useStore();
const selectedAgent = computed(() => store.state.selectedRow);

const loadingConns = ref(false);
const loadingDiag = ref(false);
const loadingScan = ref(false);
const filterText = ref("");
const diagTarget = ref("1.1.1.1");
const connections = ref<NetConnectionInfo[]>([]);
const diagResult = ref<NetDiagReport | null>(null);
const scanResult = ref<PortScanResult | null>(null);

const columns = [
  { name: "protocol", label: "Proto", field: "protocol", align: "left" as const, sortable: true },
  { name: "local_addr", label: "Local Address", field: "local_addr", align: "left" as const, sortable: true },
  { name: "local_port", label: "Port", field: "local_port", align: "left" as const, sortable: true },
  { name: "remote_addr", label: "Remote Address", field: "remote_addr", align: "left" as const, sortable: true },
  { name: "state", label: "State", field: "state", align: "left" as const, sortable: true },
  { name: "pid", label: "PID", field: "pid", align: "left" as const, sortable: true },
  { name: "process", label: "Process", field: "process", align: "left" as const, sortable: true },
];

async function loadConnections() {
  if (!selectedAgent.value) return;
  loadingConns.value = true;
  try {
    connections.value = await fetchAgentNetConnections(selectedAgent.value);
  } catch (e: any) {
    notifyError(e?.response?.data?.error || "Failed to load active connections");
  } finally {
    loadingConns.value = false;
  }
}

async function execNetDiag() {
  if (!selectedAgent.value) return;
  loadingDiag.value = true;
  try {
    diagResult.value = await runAgentNetDiag(selectedAgent.value, diagTarget.value);
  } catch (e: any) {
    notifyError(e?.response?.data?.error || "Failed to run network diagnostics");
  } finally {
    loadingDiag.value = false;
  }
}

async function execPortScan() {
  if (!selectedAgent.value) return;
  loadingScan.value = true;
  try {
    scanResult.value = await runAgentPortScan(selectedAgent.value, diagTarget.value);
  } catch (e: any) {
    notifyError(e?.response?.data?.error || "Failed to run port scan");
  } finally {
    loadingScan.value = false;
  }
}

watch(selectedAgent, () => {
  connections.value = [];
  diagResult.value = null;
  scanResult.value = null;
  if (selectedAgent.value) loadConnections();
});

onMounted(() => {
  if (selectedAgent.value) loadConnections();
});
</script>
