<template>
  <div v-if="!selectedAgent" class="q-pa-sm">No agent selected</div>
  <div v-else class="q-pa-sm">
    <div class="row q-col-gutter-md">
      <!-- Autonomous Self-Healing & System Optimization -->
      <div class="col-12 col-md-4">
        <q-card flat bordered>
          <q-card-section>
            <div class="text-subtitle2 text-weight-bold q-mb-sm">
              1-Click Self-Healing &amp; System Repair
            </div>
            <div class="column q-gutter-xs">
              <q-btn
                unelevated
                color="primary"
                icon="auto_fix_high"
                label="Run Full Autonomous Self-Heal"
                no-caps
                :loading="healing"
                @click="execSelfHeal('self_heal', 'full')"
              />
              <q-btn
                outline
                color="secondary"
                icon="cleaning_services"
                label="Deep Disk Cleanup (Temp &amp; Update Cache)"
                no-caps
                :loading="healing"
                @click="execSelfHeal('disk_cleanup', 'disk')"
              />
              <q-btn
                outline
                color="positive"
                icon="miscellaneous_services"
                label="Auto-Restart Stopped Automatic Services"
                no-caps
                :loading="healing"
                @click="execSelfHeal('self_heal', 'services')"
              />
              <q-btn
                outline
                color="warning"
                icon="build_circle"
                label="Repair Windows Update (wuauserv/bits)"
                no-caps
                :loading="healing"
                @click="execSelfHeal('self_heal', 'winupdate')"
              />
              <q-btn
                outline
                color="info"
                icon="memory"
                label="Optimize &amp; Trim Memory Working Set"
                no-caps
                :loading="healing"
                @click="execSelfHeal('trim_memory', 'memory')"
              />
            </div>

            <div v-if="healOutput" class="q-mt-sm">
              <q-banner dense rounded class="bg-grey-9 text-white text-caption">
                <div class="text-weight-bold">Last Self-Heal Output:</div>
                <pre class="q-ma-none" style="white-space: pre-wrap">{{ JSON.stringify(healOutput, null, 2) }}</pre>
              </q-banner>
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- Winget Package & Patch Manager -->
      <div class="col-12 col-md-4">
        <q-card flat bordered>
          <q-card-section>
            <div class="row items-center justify-between q-mb-sm">
              <span class="text-subtitle2 text-weight-bold">Winget Package Manager</span>
              <div class="row q-gutter-xs">
                <q-btn
                  dense
                  flat
                  icon="refresh"
                  label="Scan Updates"
                  no-caps
                  :loading="loadingWinget"
                  @click="loadWinget"
                />
                <q-btn
                  dense
                  unelevated
                  color="positive"
                  icon="system_update_alt"
                  label="Upgrade All"
                  no-caps
                  :loading="loadingWinget"
                  @click="upgradePackage('all')"
                />
              </div>
            </div>

            <div class="row q-col-gutter-xs q-mb-sm">
              <div class="col-8">
                <q-input
                  v-model="pkgIdInput"
                  dense
                  outlined
                  placeholder="Winget ID (e.g. 7zip.7zip, Mozilla.Firefox)"
                />
              </div>
              <div class="col-4">
                <q-btn
                  dense
                  unelevated
                  color="primary"
                  label="Install Silent"
                  no-caps
                  class="full-width full-height"
                  :loading="loadingWinget"
                  @click="installPackage"
                />
              </div>
            </div>

            <q-list dense bordered separator style="max-height: 220px" class="scroll">
              <q-item v-for="pkg in upgradablePkgs" :key="pkg.id">
                <q-item-section>
                  <q-item-label class="text-weight-bold">{{ pkg.name }}</q-item-label>
                  <q-item-label caption>
                    {{ pkg.id }}: {{ pkg.installed_version }} &rarr; {{ pkg.available_version }}
                  </q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-btn
                    dense
                    flat
                    color="primary"
                    icon="upgrade"
                    @click="upgradePackage(pkg.id)"
                  />
                </q-item-section>
              </q-item>
              <q-item v-if="!upgradablePkgs.length">
                <q-item-section class="text-caption text-grey">
                  Click "Scan Updates" to list outdated third-party software via Winget/APT.
                </q-item-section>
              </q-item>
            </q-list>
          </q-card-section>
        </q-card>
      </div>

      <!-- AI Diagnostics & Root-Cause Playbooks -->
      <div class="col-12 col-md-4">
        <q-card flat bordered>
          <q-card-section>
            <div class="row items-center justify-between q-mb-sm">
              <span class="text-subtitle2 text-weight-bold">AI Root-Cause Assistant</span>
              <q-btn
                dense
                unelevated
                color="deep-purple"
                icon="psychology"
                label="Analyze Endpoint"
                no-caps
                :loading="loadingAI"
                @click="execAIDiagnostics"
              />
            </div>

            <div v-if="aiReport">
              <div class="row items-center justify-between q-mb-xs">
                <span class="text-caption">Endpoint Health Score:</span>
                <q-badge :color="aiReport.health_score >= 80 ? 'positive' : 'warning'">
                  {{ aiReport.health_score }} / 100
                </q-badge>
              </div>
              <q-list dense bordered separator>
                <q-item v-for="(f, idx) in aiReport.findings" :key="idx">
                  <q-item-section>
                    <q-item-label class="text-weight-bold">
                      [{{ f.category }}] {{ f.title }}
                    </q-item-label>
                    <q-item-label caption>{{ f.detail }}</q-item-label>
                  </q-item-section>
                </q-item>
              </q-list>

              <div v-if="aiReport.remediation_playbooks?.length" class="q-mt-sm">
                <div class="text-caption text-weight-bold q-mb-xs">
                  Suggested Auto-Remediation Playbooks
                </div>
                <q-chip
                  v-for="(pb, idx) in aiReport.remediation_playbooks"
                  :key="idx"
                  clickable
                  color="primary"
                  text-color="white"
                  icon="play_arrow"
                  @click="execSelfHeal('self_heal', pb.mode || 'full')"
                >
                  {{ pb.name }}
                </q-chip>
              </div>
            </div>
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
  triggerAgentSelfHeal,
  fetchAgentWingetPackages,
  runAgentWingetOperation,
  runAgentAIDiagnostics,
} from "@/api/enhanced";
import { notifySuccess, notifyError } from "@/utils/notify";

const store = useStore();
const selectedAgent = computed(() => store.state.selectedRow);

const healing = ref(false);
const loadingWinget = ref(false);
const loadingAI = ref(false);
const healOutput = ref<any>(null);
const upgradablePkgs = ref<any[]>([]);
const pkgIdInput = ref("");
const aiReport = ref<any>(null);

async function execSelfHeal(
  action: "self_heal" | "disk_cleanup" | "trim_memory" | "reset_network",
  mode: "full" | "disk" | "services" | "network" | "winupdate" | "memory",
) {
  if (!selectedAgent.value) return;
  healing.value = true;
  try {
    healOutput.value = await triggerAgentSelfHeal(selectedAgent.value, action, mode);
    notifySuccess(`Self-healing action (${action}) completed`);
  } catch (e: any) {
    notifyError(e?.response?.data?.error || "Self-healing failed");
  } finally {
    healing.value = false;
  }
}

async function loadWinget() {
  if (!selectedAgent.value) return;
  loadingWinget.value = true;
  try {
    const res = await fetchAgentWingetPackages(selectedAgent.value);
    upgradablePkgs.value = res.upgradable || [];
  } catch (e: any) {
    notifyError(e?.response?.data?.error || "Winget scan failed");
  } finally {
    loadingWinget.value = false;
  }
}

async function installPackage() {
  if (!selectedAgent.value || !pkgIdInput.value.trim()) return;
  loadingWinget.value = true;
  try {
    await runAgentWingetOperation(selectedAgent.value, "install", pkgIdInput.value.trim());
    notifySuccess(`Installed ${pkgIdInput.value}`);
    pkgIdInput.value = "";
  } catch (e: any) {
    notifyError(e?.response?.data?.error || "Winget install failed");
  } finally {
    loadingWinget.value = false;
  }
}

async function upgradePackage(pkgId: string) {
  if (!selectedAgent.value) return;
  loadingWinget.value = true;
  try {
    await runAgentWingetOperation(selectedAgent.value, "upgrade", pkgId);
    notifySuccess(`Upgraded ${pkgId}`);
    await loadWinget();
  } catch (e: any) {
    notifyError(e?.response?.data?.error || "Winget upgrade failed");
  } finally {
    loadingWinget.value = false;
  }
}

async function execAIDiagnostics() {
  if (!selectedAgent.value) return;
  loadingAI.value = true;
  try {
    aiReport.value = await runAgentAIDiagnostics(selectedAgent.value);
  } catch (e: any) {
    notifyError(e?.response?.data?.error || "Failed to run AI diagnostics");
  } finally {
    loadingAI.value = false;
  }
}

watch(selectedAgent, () => {
  healOutput.value = null;
  upgradablePkgs.value = [];
  aiReport.value = null;
  if (selectedAgent.value) execAIDiagnostics();
});

onMounted(() => {
  if (selectedAgent.value) execAIDiagnostics();
});
</script>
