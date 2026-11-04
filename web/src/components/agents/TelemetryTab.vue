<template>
  <div v-if="!selectedAgent" class="q-pa-sm">{{ t("common.noAgentSelected") }}</div>
  <div v-else class="q-pa-sm">
    <q-bar dense style="background-color: transparent">
      <q-btn
        dense
        flat
        icon="refresh"
        :label="t('tel.refresh')"
        no-caps
        :loading="loading"
        @click="loadTelemetry"
      />
      <q-space />
      <q-badge v-if="telemetry?.cached_fallback" color="warning" text-color="black">
        Cached Fallback Mode
      </q-badge>
      <span v-if="telemetry?.timestamp" class="text-caption text-grey q-ml-sm">
        {{ telemetry.timestamp }}
      </span>
    </q-bar>
    <q-separator class="q-my-xs" />

    <div v-if="telemetry" class="row q-col-gutter-md q-mt-xs">
      <!-- CPU & RAM Gauges -->
      <div class="col-12 col-md-4">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-subtitle2 text-weight-bold q-mb-sm">
              {{ t("tel.cpuRamTitle") }}
            </div>
            <div class="row items-center justify-around q-my-sm">
              <div class="text-center">
                <q-circular-progress
                  show-value
                  font-size="14px"
                  :value="telemetry.cpu_load_percent || 0"
                  size="80px"
                  :thickness="0.22"
                  :color="barColor(telemetry.cpu_load_percent || 0)"
                  track-color="grey-8"
                >
                  {{ telemetry.cpu_load_percent || 0 }}%
                </q-circular-progress>
                <div class="text-caption q-mt-xs">
                  CPU ({{ telemetry.cpu_cores_logical || 1 }} Threads)
                </div>
              </div>

              <div class="text-center">
                <q-circular-progress
                  show-value
                  font-size="14px"
                  :value="telemetry.ram_used_percent || 0"
                  size="80px"
                  :thickness="0.22"
                  :color="barColor(telemetry.ram_used_percent || 0)"
                  track-color="grey-8"
                >
                  {{ telemetry.ram_used_percent || 0 }}%
                </q-circular-progress>
                <div class="text-caption q-mt-xs">
                  RAM ({{ telemetry.ram_used_mb || 0 }} / {{ telemetry.ram_total_mb || 0 }} MB)
                </div>
              </div>
            </div>

            <div v-if="telemetry.cpu_per_core?.length" class="q-mt-md">
              <div class="text-caption text-grey q-mb-xs">{{ t("tel.perCore") }}</div>
              <div
                v-for="(pct, idx) in telemetry.cpu_per_core"
                :key="idx"
                class="q-mb-xs"
              >
                <div class="row justify-between text-caption">
                  <span>Core #{{ idx }}</span>
                  <span>{{ pct }}%</span>
                </div>
                <q-linear-progress
                  rounded
                  size="8px"
                  :value="pct / 100"
                  :color="barColor(pct)"
                />
              </div>
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- Disk Telemetry & S.M.A.R.T. Health -->
      <div class="col-12 col-md-4">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-subtitle2 text-weight-bold q-mb-sm">
              {{ t("tel.storageSmart") }}
            </div>
            <div
              v-for="d in telemetry.disk_metrics || []"
              :key="d.mountpoint"
              class="q-mb-sm"
            >
              <div class="row justify-between text-caption">
                <span class="text-weight-bold">{{ d.mountpoint }} ({{ d.fstype }})</span>
                <span>{{ d.used_gb }} GB / {{ d.total_gb }} GB ({{ d.used_percent }}%)</span>
              </div>
              <q-linear-progress
                rounded
                size="12px"
                :value="d.used_percent / 100"
                :color="barColor(d.used_percent)"
                class="q-my-xs"
              />
            </div>

            <q-separator class="q-my-sm" />
            <div class="text-caption text-weight-bold q-mb-xs">
              {{ t("tel.smartStatus") }}
            </div>
            <q-list dense bordered separator v-if="telemetry.smart_health?.length">
              <q-item v-for="(s, i) in telemetry.smart_health" :key="i">
                <q-item-section>
                  <q-item-label>{{ s.model }}</q-item-label>
                  <q-item-label caption>
                    Media: {{ s.media_type || "Disk" }} &bull; SN: {{ s.serial_number || "N/A" }}
                  </q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-badge
                    :color="s.status === 'Healthy' ? 'positive' : 'warning'"
                    :label="s.status || 'Unknown'"
                  />
                </q-item-section>
              </q-item>
            </q-list>
            <div v-else class="text-caption text-grey">
              S.M.A.R.T. OK
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- Network I/O & Runtime Metrics -->
      <div class="col-12 col-md-4">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-subtitle2 text-weight-bold q-mb-sm">
              {{ t("tel.netRuntime") }}
            </div>
            <q-list dense separator>
              <q-item>
                <q-item-section avatar>
                  <q-icon name="cloud_upload" color="primary" />
                </q-item-section>
                <q-item-section>{{ t("tel.bytesSent") }}</q-item-section>
                <q-item-section side>
                  {{ formatBytes(telemetry.net_bytes_sent || 0) }}
                </q-item-section>
              </q-item>
              <q-item>
                <q-item-section avatar>
                  <q-icon name="cloud_download" color="secondary" />
                </q-item-section>
                <q-item-section>{{ t("tel.bytesRecv") }}</q-item-section>
                <q-item-section side>
                  {{ formatBytes(telemetry.net_bytes_recv || 0) }}
                </q-item-section>
              </q-item>
              <q-item>
                <q-item-section avatar>
                  <q-icon name="apps" color="info" />
                </q-item-section>
                <q-item-section>{{ t("tel.activeProcesses") }}</q-item-section>
                <q-item-section side>
                  {{ telemetry.process_count || 0 }}
                </q-item-section>
              </q-item>
              <q-item>
                <q-item-section avatar>
                  <q-icon name="schedule" color="positive" />
                </q-item-section>
                <q-item-section>{{ t("tel.systemUptime") }}</q-item-section>
                <q-item-section side>
                  {{ formatUptime(telemetry.uptime_seconds || 0) }}
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
import { fetchAgentLiveTelemetry, type LiveTelemetrySnapshot } from "@/api/enhanced";
import { useI18n } from "@/i18n";

const { t } = useI18n();
const store = useStore();
const selectedAgent = computed(() => store.state.selectedRow);
const loading = ref(false);
const telemetry = ref<LiveTelemetrySnapshot | null>(null);

function barColor(pct: number): string {
  if (pct >= 90) return "negative";
  if (pct >= 75) return "warning";
  return "positive";
}

function formatBytes(bytes: number): string {
  if (!bytes || bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const idx = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / Math.pow(1024, idx)).toFixed(2)} ${units[idx]}`;
}

function formatUptime(sec: number): string {
  if (!sec || sec <= 0) return "N/A";
  const days = Math.floor(sec / 86400);
  const hours = Math.floor((sec % 86400) / 3600);
  const mins = Math.floor((sec % 3600) / 60);
  return `${days}d ${hours}h ${mins}m`;
}

async function loadTelemetry() {
  if (!selectedAgent.value) return;
  loading.value = true;
  try {
    telemetry.value = await fetchAgentLiveTelemetry(selectedAgent.value);
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
}

watch(selectedAgent, () => {
  loadTelemetry();
});

onMounted(() => {
  if (selectedAgent.value) loadTelemetry();
});
</script>
