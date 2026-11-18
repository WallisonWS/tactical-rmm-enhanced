<template>
  <q-card
    style="width: 1180px; max-width: 96vw; max-height: 92vh; overflow: hidden"
    class="column no-wrap trmm-cli-modal"
  >
    <!-- Executive Gradient Header -->
    <div
      class="row items-center justify-between q-px-md q-py-sm text-white trmm-cli-header"
      style="flex: 0 0 auto"
    >
      <div class="row items-center no-wrap q-gutter-x-sm">
        <div class="trmm-cli-header-icon">
          <q-icon name="terminal" size="20px" color="cyan-3" />
        </div>
        <div>
          <div class="text-subtitle1 text-weight-bold" style="line-height: 1.2">
            Central CLI — Execução em Massa na Frota
          </div>
          <div class="text-caption text-blue-grey-3" style="font-size: 11px">
            Execução paralela em tempo real via NATS RPC &bull; Windows, Linux &amp; macOS
          </div>
        </div>
      </div>

      <div class="row items-center q-gutter-x-xs">
        <q-btn
          dense
          unelevated
          no-caps
          icon="dns"
          icon-right="open_in_new"
          label="Terminal Linux (/webterm)"
          class="q-px-sm trmm-cli-webterm-btn"
          @click="launchServerWebTerm"
        >
          <q-tooltip>Abre o terminal SSH/Web direto do servidor Tactical RMM</q-tooltip>
        </q-btn>
        <q-btn dense flat round icon="close" color="white" v-close-popup />
      </div>
    </div>

    <!-- Scrollable Modal Body -->
    <div
      class="col q-pa-md"
      style="flex: 1 1 auto; min-height: 0; overflow-y: auto; overscroll-behavior: contain"
    >
      <!-- Section 1: Quick 1-Click Fleet Actions -->
      <div class="row items-center justify-between q-mb-sm">
        <div class="row items-center q-gutter-x-xs">
          <q-icon name="bolt" color="amber-5" size="18px" />
          <span class="text-subtitle2 text-weight-bold">
            Ações Rápidas de 1 Clique (Frota Online)
          </span>
        </div>
        <q-badge
          outline
          :color="$q.dark.isActive ? 'blue-grey-4' : 'blue-grey-7'"
          class="text-caption"
        >
          Execução paralela segura em segundo plano
        </q-badge>
      </div>

      <div class="row q-col-gutter-md q-mb-md">
        <!-- Card 1: Banking Mode -->
        <div class="col-12 col-md-4">
          <q-card
            flat
            bordered
            class="full-height column justify-between q-pa-md trmm-cli-card trmm-cli-card--teal"
          >
            <div>
              <div class="row items-center no-wrap q-gutter-x-sm q-mb-sm">
                <div class="trmm-cli-icon-circle trmm-cli-icon-circle--teal">
                  <q-icon name="account_balance" size="20px" color="teal-3" />
                </div>
                <div class="col">
                  <div class="text-subtitle2 text-weight-bold" style="line-height: 1.2">
                    Modo Banco (Pausar Mesh)
                  </div>
                  <div class="text-caption text-teal-4" style="font-size: 11px">
                    Compatibilidade Warsaw / Topaz
                  </div>
                </div>
              </div>
              <div class="text-caption trmm-cli-desc">
                Coloca apenas o <b>Mesh Agent</b> em modo Sob Demanda nas estações Windows para evitar bloqueios em internet banking. O <b>Tactical RMM segue 100% online</b> e o Mesh religa sozinho ao abrir Controle Remoto.
              </div>
            </div>

            <div class="row items-center justify-between q-mt-md q-pt-xs">
              <q-badge outline color="teal-5" style="font-size: 10px">
                Estações Windows
              </q-badge>
              <q-btn
                dense
                unelevated
                no-caps
                color="teal-7"
                icon="verified_user"
                label="Ativar Modo Banco"
                class="q-px-sm trmm-cli-card-btn"
                :loading="runningPreset === 'banking_mode_enable'"
                @click="executePreset('banking_mode_enable', 'workstations')"
              />
            </div>
          </q-card>
        </div>

        <!-- Card 2: GPO / AD Sync -->
        <div class="col-12 col-md-4">
          <q-card
            flat
            bordered
            class="full-height column justify-between q-pa-md trmm-cli-card trmm-cli-card--indigo"
          >
            <div>
              <div class="row items-center no-wrap q-gutter-x-sm q-mb-sm">
                <div class="trmm-cli-icon-circle trmm-cli-icon-circle--indigo">
                  <q-icon name="hub" size="20px" color="indigo-3" />
                </div>
                <div class="col">
                  <div class="text-subtitle2 text-weight-bold" style="line-height: 1.2">
                    Sincronizar GPO / AD &amp; DNS
                  </div>
                  <div class="text-caption text-indigo-3" style="font-size: 11px">
                    Kerberos • DNS • Canal Seguro
                  </div>
                </div>
              </div>
              <div class="text-caption trmm-cli-desc">
                Sincroniza relógio (<code>w32tm</code>), renova tickets <b>Kerberos</b> (<code>klist purge</code>), limpa e registra <b>DNS</b>, valida o Canal Seguro com o DC e aplica <code>gpupdate /force</code> sem travar.
              </div>
            </div>

            <div class="row items-center justify-between q-mt-md q-pt-xs">
              <q-badge outline color="indigo-4" style="font-size: 10px">
                Frota Windows
              </q-badge>
              <q-btn
                dense
                unelevated
                no-caps
                color="indigo-6"
                icon="sync"
                label="Sincronizar AD"
                class="q-px-sm trmm-cli-card-btn"
                :loading="runningPreset === 'gpupdate_ad_sync'"
                @click="executePreset('gpupdate_ad_sync', 'windows', 45)"
              />
            </div>
          </q-card>
        </div>

        <!-- Card 3: Restore Continuous Mesh -->
        <div class="col-12 col-md-4">
          <q-card
            flat
            bordered
            class="full-height column justify-between q-pa-md trmm-cli-card trmm-cli-card--sky"
          >
            <div>
              <div class="row items-center no-wrap q-gutter-x-sm q-mb-sm">
                <div class="trmm-cli-icon-circle trmm-cli-icon-circle--sky">
                  <q-icon name="published_with_changes" size="20px" color="light-blue-3" />
                </div>
                <div class="col">
                  <div class="text-subtitle2 text-weight-bold" style="line-height: 1.2">
                    Restaurar Mesh Contínuo
                  </div>
                  <div class="text-caption text-light-blue-3" style="font-size: 11px">
                    Inicialização Automática 24/7
                  </div>
                </div>
              </div>
              <div class="text-caption trmm-cli-desc">
                Reconfigura o serviço <b>Mesh Agent</b> para inicialização <b>Automática contínua</b> em segundo plano. Recomendado para servidores ou estações que não utilizam sistemas bancários com Warsaw/Topaz.
              </div>
            </div>

            <div class="row items-center justify-between q-mt-md q-pt-xs">
              <q-badge outline color="light-blue-4" style="font-size: 10px">
                Servidores / Windows
              </q-badge>
              <q-btn
                dense
                outline
                no-caps
                color="light-blue-4"
                icon="autorenew"
                label="Restaurar Contínuo"
                class="q-px-sm trmm-cli-card-btn"
                :loading="runningPreset === 'banking_mode_disable'"
                @click="executePreset('banking_mode_disable', 'windows')"
              />
            </div>
          </q-card>
        </div>
      </div>

      <q-separator class="q-my-md" />

      <!-- Section 2: Interactive Fleet Command Console -->
      <div class="row items-center justify-between wrap q-mb-sm q-gutter-y-xs">
        <div class="row items-center q-gutter-x-xs">
          <q-icon name="code" color="primary" size="18px" />
          <span class="text-subtitle2 text-weight-bold">
            Console de Comando Personalizado
          </span>
        </div>

        <!-- 1-Click Useful Command Snippets -->
        <div class="row items-center wrap q-gutter-xs">
          <span class="text-caption text-grey-5">Modelos prontos:</span>
          <q-btn
            v-for="snip in commandSnippets"
            :key="snip.label"
            dense
            flat
            no-caps
            size="xs"
            :icon="snip.icon"
            :label="snip.label"
            class="trmm-snippet-btn"
            @click="applySnippet(snip)"
          />
        </div>
      </div>

      <div class="row q-col-gutter-sm items-center q-mb-sm">
        <div class="col-12 col-md-4">
          <q-select
            v-model="target"
            :options="targetOptions"
            emit-value
            map-options
            outlined
            dense
            label="Alvo da Execução"
          >
            <template v-slot:prepend>
              <q-icon name="devices" color="primary" size="18px" />
            </template>
          </q-select>
        </div>
        <div class="col-12 col-md-4">
          <q-select
            v-model="shell"
            :options="shellOptions"
            emit-value
            map-options
            outlined
            dense
            label="Interpretador / Shell"
          >
            <template v-slot:prepend>
              <q-icon name="terminal" color="teal-5" size="18px" />
            </template>
          </q-select>
        </div>
        <div class="col-6 col-md-2">
          <q-input
            v-model.number="timeoutSec"
            type="number"
            outlined
            dense
            label="Timeout (seg)"
          >
            <template v-slot:prepend>
              <q-icon name="timer" color="amber-6" size="18px" />
            </template>
          </q-input>
        </div>
        <div class="col-6 col-md-2 row no-wrap q-gutter-xs">
          <q-btn
            unelevated
            no-caps
            color="primary"
            icon="play_arrow"
            label="Executar"
            class="col trmm-cli-run-btn"
            :loading="loading"
            @click="executeCustomCommand"
          />
          <q-btn
            flat
            dense
            icon="delete_sweep"
            color="grey-5"
            @click="command = ''"
          >
            <q-tooltip>Limpar comando</q-tooltip>
          </q-btn>
        </div>
      </div>

      <!-- Dark IDE Terminal Input Box -->
      <div class="trmm-terminal-shell" data-no-translate="true">
        <div class="row items-center justify-between q-px-sm q-py-xs trmm-terminal-topbar">
          <div class="row items-center q-gutter-x-xs">
            <span class="trmm-term-dot trmm-term-dot--red" />
            <span class="trmm-term-dot trmm-term-dot--yellow" />
            <span class="trmm-term-dot trmm-term-dot--green" />
            <span class="text-caption text-cyan-3 q-ml-sm text-weight-bold" style="font-family: monospace">
              {{ terminalPrompt }}
            </span>
          </div>
          <span class="text-caption text-grey-5" style="font-size: 11px">
            Ctrl + Enter para executar
          </span>
        </div>
        <q-input
          v-model="command"
          type="textarea"
          borderless
          dark
          autogrow
          class="q-px-sm q-pb-xs"
          :input-style="{
            minHeight: '115px',
            fontFamily: 'Consolas, JetBrains Mono, monospace',
            fontSize: '13px',
            color: '#e2e8f0',
            lineHeight: '1.45',
          }"
          placeholder="Ex: Get-Service tacticalrmm, 'Mesh Agent' | Select-Object Name, Status, StartType"
          @keydown.ctrl.enter.prevent="executeCustomCommand"
        />
      </div>

      <!-- Execution Results Section -->
      <div v-if="lastResponse" class="q-mt-md">
        <div class="row items-center justify-between wrap q-mb-xs q-gutter-y-xs">
          <div class="row items-center q-gutter-x-xs">
            <q-icon name="receipt_long" color="primary" size="18px" />
            <span class="text-subtitle2 text-weight-bold">Resultado da Execução:</span>
            <q-badge color="primary" class="q-px-sm">
              Total: {{ lastResponse.total_targeted }}
            </q-badge>
            <q-badge color="positive" class="q-px-sm">
              Sucesso: {{ lastResponse.success_count }}
            </q-badge>
            <q-badge v-if="lastResponse.failed_count > 0" color="negative" class="q-px-sm">
              Falha / Timeout: {{ lastResponse.failed_count }}
            </q-badge>
          </div>
          <div class="row items-center q-gutter-x-xs">
            <q-btn
              dense
              outline
              no-caps
              color="teal-4"
              icon="download"
              label="Exportar Saída (.CSV)"
              class="q-px-sm"
              @click="exportResultsCsv"
            />
            <q-input
              v-model="resultFilter"
              dense
              outlined
              clearable
              placeholder="Filtrar computador ou saída..."
              style="width: 240px"
            >
              <template v-slot:prepend>
                <q-icon name="search" size="xs" />
              </template>
            </q-input>
          </div>
        </div>

        <q-table
          dense
          flat
          bordered
          :rows="filteredResults"
          :columns="columns"
          row-key="agent_id"
          v-model:pagination="resultsPagination"
          :rows-per-page-options="[15, 30, 50, 0]"
          style="max-height: 36vh"
        >
          <template v-slot:body-cell-status="props">
            <q-td :props="props">
              <q-badge
                :color="props.row.success ? 'positive' : 'negative'"
                class="q-px-sm text-weight-bold"
              >
                {{ props.row.success ? "OK" : "Erro" }}
              </q-badge>
            </q-td>
          </template>
          <template v-slot:body-cell-output="props">
            <q-td
              :props="props"
              data-no-translate="true"
              style="white-space: pre-wrap; font-family: Consolas, monospace; font-size: 12px"
            >
              {{ props.row.output }}
            </q-td>
          </template>
        </q-table>
      </div>
    </div>
  </q-card>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { useQuasar } from "quasar";
import { runFleetBulkCLI, type FleetBulkCLIResponse } from "@/api/enhanced";
import { openWebTerminal } from "@/api/core";
import { notifyError, notifySuccess } from "@/utils/notify";

const $q = useQuasar();

const target = ref("windows");
const shell = ref("powershell");
const timeoutSec = ref(35);
const command = ref("");
const loading = ref(false);
const runningPreset = ref("");
const resultFilter = ref("");
const lastResponse = ref<FleetBulkCLIResponse | null>(null);
const resultsPagination = ref({
  rowsPerPage: 15,
  sortBy: "hostname",
  descending: false,
});

const targetOptions = [
  { label: "Todos os Computadores Online (Windows + Linux + macOS)", value: "all" },
  { label: "Todos os Computadores Windows (Estações + Servidores)", value: "windows" },
  { label: "Apenas Estações de Trabalho (Workstations)", value: "workstations" },
  { label: "Apenas Servidores (Servers)", value: "servers" },
  { label: "Apenas Máquinas Linux", value: "linux" },
  { label: "Apenas Máquinas macOS", value: "darwin" },
];

const shellOptions = [
  { label: "PowerShell (Windows)", value: "powershell" },
  { label: "Prompt de Comando CMD (Windows)", value: "cmd" },
  { label: "Bash / Shell (Linux & macOS)", value: "bash" },
];

const commandSnippets = [
  {
    label: "Serviços RMM/Mesh",
    icon: "miscellaneous_services",
    shell: "powershell",
    target: "windows",
    cmd: "Get-Service tacticalrmm, 'Mesh Agent' -ErrorAction SilentlyContinue | Select-Object Name, Status, StartType | Format-Table -AutoSize",
  },
  {
    label: "IP & Gateway",
    icon: "lan",
    shell: "powershell",
    target: "windows",
    cmd: "Get-NetIPConfiguration | Select-Object InterfaceAlias, IPv4Address, IPv4DefaultGateway | Format-Table -AutoSize",
  },
  {
    label: "Uptime & Boot",
    icon: "schedule",
    shell: "powershell",
    target: "windows",
    cmd: "$os = Get-CimInstance Win32_OperatingSystem; \"Boot: $($os.LastBootUpTime) | Uptime: $([math]::Round(((Get-Date)-$os.LastBootUpTime).TotalHours,1))h\"",
  },
  {
    label: "Espaço em Disco",
    icon: "storage",
    shell: "powershell",
    target: "windows",
    cmd: "Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' | Select-Object DeviceID, @{N='TotalGB';E={[math]::Round($_.Size/1GB,1)}}, @{N='LivreGB';E={[math]::Round($_.FreeSpace/1GB,1)}} | Format-Table -AutoSize",
  },
  {
    label: "Limpar Spooler",
    icon: "print",
    shell: "powershell",
    target: "windows",
    cmd: "Stop-Service Spooler -Force; Remove-Item 'C:\\Windows\\System32\\spool\\PRINTERS\\*' -Force -ErrorAction SilentlyContinue; Start-Service Spooler; 'Spooler reiniciado com sucesso'",
  },
];

const terminalPrompt = computed(() => {
  if (shell.value === "cmd") return "C:\\Windows\\system32>";
  if (shell.value === "bash") return "root@fleet:~#";
  return "PS C:\\Fleet>";
});

const columns = [
  { name: "hostname", label: "Computador", field: "hostname", align: "left" as const, sortable: true },
  { name: "site", label: "Unidade / Site", field: "site", align: "left" as const, sortable: true },
  { name: "plat", label: "SO", field: "plat", align: "left" as const, sortable: true },
  { name: "status", label: "Status", field: "success", align: "left" as const, sortable: true },
  { name: "output", label: "Saída / Resposta", field: "output", align: "left" as const },
];

const filteredResults = computed(() => {
  const list = lastResponse.value?.results || [];
  const q = resultFilter.value.trim().toLowerCase();
  if (!q) return list;
  return list.filter(
    (r) =>
      r.hostname.toLowerCase().includes(q) ||
      r.site.toLowerCase().includes(q) ||
      r.output.toLowerCase().includes(q),
  );
});

function applySnippet(snip: { shell: string; target: string; cmd: string }) {
  shell.value = snip.shell;
  target.value = snip.target;
  command.value = snip.cmd;
}

function extractApiError(err: unknown, fallback: string): string {
  const maybeErr = err as { response?: { data?: { error?: string } } } | null;
  return maybeErr?.response?.data?.error || fallback;
}

async function executePreset(presetKey: string, defaultTarget: string, minTimeout?: number) {
  runningPreset.value = presetKey;
  loading.value = true;
  const effectiveTimeout = minTimeout ? Math.max(timeoutSec.value, minTimeout) : timeoutSec.value;
  try {
    const res = await runFleetBulkCLI({
      preset: presetKey,
      target: defaultTarget,
      timeout: effectiveTimeout,
      only_online: true,
    });
    lastResponse.value = res;
    notifySuccess(
      `Ação executada com sucesso em ${res.success_count} de ${res.total_targeted} máquinas!`,
    );
  } catch (e: unknown) {
    notifyError(extractApiError(e, "Erro ao executar ação na frota."));
  } finally {
    runningPreset.value = "";
    loading.value = false;
  }
}

async function executeCustomCommand() {
  if (!command.value.trim()) {
    notifyError("Digite ou cole um comando para executar.");
    return;
  }
  loading.value = true;
  try {
    const res = await runFleetBulkCLI({
      target: target.value,
      shell: shell.value,
      command: command.value,
      timeout: timeoutSec.value,
      only_online: true,
    });
    lastResponse.value = res;
    notifySuccess(
      `Comando concluído em ${res.success_count} de ${res.total_targeted} máquinas!`,
    );
  } catch (e: unknown) {
    notifyError(extractApiError(e, "Erro ao executar comando na frota."));
  } finally {
    loading.value = false;
  }
}

function exportResultsCsv() {
  if (!filteredResults.value.length) return;
  const esc = (v: unknown) => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const lines = [["Computador", "Unidade", "SO", "Status", "Saida"].map(esc).join(";")];
  for (const r of filteredResults.value) {
    lines.push([r.hostname, r.site, r.plat, r.success ? "OK" : "Erro", r.output].map(esc).join(";"));
  }
  const blob = new Blob(["\uFEFF" + lines.join("\r\n")], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `central-cli-resultado-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

function launchServerWebTerm() {
  openWebTerminal();
}
</script>

<style scoped>
.trmm-cli-header {
  background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 60%, #0f4c5c 100%);
  border-bottom: 1px solid rgba(56, 189, 248, 0.22);
}

.trmm-cli-header-icon {
  width: 36px;
  height: 36px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(56, 189, 248, 0.14);
  border: 1px solid rgba(56, 189, 248, 0.35);
}

.trmm-cli-webterm-btn {
  background: rgba(15, 23, 42, 0.65);
  border: 1px solid rgba(148, 163, 184, 0.35);
  border-radius: 7px;
  font-size: 12px;
  font-weight: 600;
}
.trmm-cli-webterm-btn:hover {
  background: rgba(30, 41, 59, 0.9);
  border-color: rgba(56, 189, 248, 0.5);
}

.trmm-cli-card {
  border-radius: 10px;
  transition: border-color 0.18s ease, transform 0.15s ease;
}
.trmm-cli-card:hover {
  transform: translateY(-1px);
}
.trmm-cli-card--teal:hover {
  border-color: rgba(45, 212, 191, 0.55);
}
.trmm-cli-card--indigo:hover {
  border-color: rgba(129, 140, 248, 0.55);
}
.trmm-cli-card--sky:hover {
  border-color: rgba(56, 189, 248, 0.55);
}

.trmm-cli-icon-circle {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.trmm-cli-icon-circle--teal {
  background: rgba(13, 148, 136, 0.18);
  border: 1px solid rgba(45, 212, 191, 0.32);
}
.trmm-cli-icon-circle--indigo {
  background: rgba(79, 70, 229, 0.18);
  border: 1px solid rgba(129, 140, 248, 0.32);
}
.trmm-cli-icon-circle--sky {
  background: rgba(2, 132, 199, 0.18);
  border: 1px solid rgba(56, 189, 248, 0.32);
}

.trmm-cli-desc {
  line-height: 1.45;
  opacity: 0.88;
}

.trmm-cli-card-btn {
  border-radius: 7px;
  font-size: 12px;
  font-weight: 600;
}

.trmm-snippet-btn {
  border-radius: 6px;
  border: 1px solid rgba(148, 163, 184, 0.26);
  background: rgba(148, 163, 184, 0.08);
  padding: 2px 8px;
  font-size: 11px;
}
.trmm-snippet-btn:hover {
  border-color: rgba(56, 189, 248, 0.5);
  background: rgba(56, 189, 248, 0.14);
}

.trmm-cli-run-btn {
  border-radius: 7px;
  font-weight: 600;
  height: 40px;
}

.trmm-terminal-shell {
  background: #0b111b;
  border: 1px solid rgba(56, 189, 248, 0.25);
  border-radius: 10px;
  overflow: hidden;
  box-shadow: inset 0 1px 4px rgba(0, 0, 0, 0.45);
}

.trmm-terminal-topbar {
  background: #111927;
  border-bottom: 1px solid rgba(148, 163, 184, 0.16);
}

.trmm-term-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  display: inline-block;
}
.trmm-term-dot--red {
  background: #ef4444;
}
.trmm-term-dot--yellow {
  background: #f59e0b;
}
.trmm-term-dot--green {
  background: #22c55e;
}
</style>
