<template>
  <q-card style="min-width: 78vw; max-width: 92vw" data-no-translate="true">
    <q-bar class="bg-primary text-white">
      <q-icon name="terminal" size="sm" class="q-mr-xs" />
      <div class="text-weight-bold">
        Central CLI — Execução em Massa na Frota (Windows / Linux / macOS) &amp; Terminal do Servidor
      </div>
      <q-space />
      <q-btn
        dense
        flat
        no-caps
        icon="open_in_new"
        label="Abrir Terminal Linux do Servidor (/webterm)"
        class="bg-dark text-white q-px-sm q-mr-sm"
        @click="launchServerWebTerm"
      />
      <q-btn dense flat icon="close" v-close-popup />
    </q-bar>

    <q-card-section class="q-pb-xs">
      <div class="text-subtitle2 q-mb-xs text-weight-bold">
        Ações Rápidas de 1 Clique (Executar em Toda a Frota Online):
      </div>
      <div class="row q-col-gutter-sm">
        <div class="col-12 col-md-4">
          <q-card flat bordered class="full-height column justify-between q-pa-sm">
            <div>
              <q-btn
                unelevated
                no-caps
                color="teal-7"
                icon="account_balance"
                label="Modo Banco (Pausar Mesh)"
                class="full-width"
                :loading="runningPreset === 'banking_mode_enable'"
                @click="executePreset('banking_mode_enable', 'workstations')"
              >
                <q-tooltip max-width="340px">
                  Coloca o serviço Mesh Agent das estações Windows em modo Sob Demanda (Manual). Os sites de banco param de acusar bloqueio (Warsaw/Topaz/GBPlugin) e o monitoramento Tactical RMM segue 100% online.
                </q-tooltip>
              </q-btn>
              <div class="text-caption q-mt-xs" style="line-height: 1.35">
                Pausa apenas o controle remoto <b>Mesh Agent</b> (Sob Demanda) nas estações Windows para não bloquear internet banking (<b>Warsaw / Topaz</b>). O <b>Tactical RMM continua 100% online</b> e o Mesh religa sozinho ao clicar em Controle Remoto.
              </div>
            </div>
            <div class="q-mt-xs">
              <q-badge outline color="teal-5">Alvo: Estações de Trabalho Windows</q-badge>
            </div>
          </q-card>
        </div>

        <div class="col-12 col-md-4">
          <q-card flat bordered class="full-height column justify-between q-pa-sm">
            <div>
              <q-btn
                unelevated
                no-caps
                color="indigo-7"
                icon="sync"
                label="Sincronizar GPO / AD e DNS"
                class="full-width"
                :loading="runningPreset === 'gpupdate_ad_sync'"
                @click="executePreset('gpupdate_ad_sync', 'windows', 45)"
              >
                <q-tooltip max-width="340px">
                  Executa sincronização completa de Active Directory sem travar aguardando logoff: inicia W32Time/Netlogon/GPSVC, renova tickets Kerberos, limpa/registra DNS, testa Canal Seguro e aplica gpupdate /force.
                </q-tooltip>
              </q-btn>
              <div class="text-caption q-mt-xs" style="line-height: 1.35">
                Sincroniza relógio (<code>w32tm</code>), renova tickets <b>Kerberos</b> da máquina (<code>klist purge</code>), limpa e registra <b>DNS</b> (<code>flushdns</code> / <code>registerdns</code>), valida o <b>Canal Seguro</b> com o DC e força <code>gpupdate /force</code> sem travar.
              </div>
            </div>
            <div class="q-mt-xs">
              <q-badge outline color="indigo-4">Alvo: Todos os Computadores Windows</q-badge>
            </div>
          </q-card>
        </div>

        <div class="col-12 col-md-4">
          <q-card flat bordered class="full-height column justify-between q-pa-sm">
            <div>
              <q-btn
                outline
                no-caps
                color="primary"
                icon="autorenew"
                label="Restaurar Mesh Contínuo"
                class="full-width"
                :loading="runningPreset === 'banking_mode_disable'"
                @click="executePreset('banking_mode_disable', 'windows')"
              >
                <q-tooltip max-width="340px">
                  Reconfigura o serviço Mesh Agent para inicialização Automática contínua em todas as máquinas Windows online.
                </q-tooltip>
              </q-btn>
              <div class="text-caption q-mt-xs" style="line-height: 1.35">
                Restaura o serviço <b>Mesh Agent</b> para inicialização <b>Automática contínua</b> em segundo plano. Use somente em servidores ou máquinas que não acessem sistemas bancários com proteção Warsaw/Topaz.
              </div>
            </div>
            <div class="q-mt-xs">
              <q-badge outline color="primary">Alvo: Todos os Computadores Windows</q-badge>
            </div>
          </q-card>
        </div>
      </div>
    </q-card-section>

    <q-separator class="q-my-xs" />

    <q-card-section class="q-pt-xs">
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
          />
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
          />
        </div>
        <div class="col-12 col-md-2">
          <q-input
            v-model.number="timeoutSec"
            type="number"
            outlined
            dense
            label="Timeout (seg)"
          />
        </div>
        <div class="col-12 col-md-2">
          <q-btn
            unelevated
            no-caps
            color="primary"
            icon="play_arrow"
            label="Executar CLI"
            class="full-width"
            :loading="loading"
            @click="executeCustomCommand"
          />
        </div>
      </div>

      <q-input
        v-model="command"
        type="textarea"
        outlined
        autogrow
        :input-style="{ minHeight: '110px', fontFamily: 'monospace', fontSize: '13px' }"
        label="Digite ou cole seu comando / script de múltiplas linhas (PowerShell, CMD ou Bash Linux/macOS)"
        placeholder="Ex: Get-Service tacticalrmm, 'Mesh Agent' | Select-Object Name, Status, StartType"
      />
    </q-card-section>

    <q-card-section v-if="lastResponse" class="q-pt-none">
      <div class="row items-center justify-between q-mb-xs">
        <div class="text-subtitle2 text-weight-bold">
          Resultado da Execução:
          <q-badge color="primary" class="q-ml-xs">
            Total: {{ lastResponse.total_targeted }}
          </q-badge>
          <q-badge color="positive" class="q-ml-xs">
            Sucesso: {{ lastResponse.success_count }}
          </q-badge>
          <q-badge v-if="lastResponse.failed_count > 0" color="negative" class="q-ml-xs">
            Falha/Timeout: {{ lastResponse.failed_count }}
          </q-badge>
        </div>
        <q-input
          v-model="resultFilter"
          dense
          outlined
          placeholder="Filtrar computador ou saída..."
          style="width: 260px"
        >
          <template v-slot:prepend>
            <q-icon name="search" size="xs" />
          </template>
        </q-input>
      </div>

      <q-table
        dense
        flat
        bordered
        :rows="filteredResults"
        :columns="columns"
        row-key="agent_id"
        :pagination="{ rowsPerPage: 15 }"
        style="max-height: 36vh"
      >
        <template v-slot:body-cell-status="props">
          <q-td :props="props">
            <q-badge :color="props.row.success ? 'positive' : 'negative'">
              {{ props.row.success ? "OK" : "Erro" }}
            </q-badge>
          </q-td>
        </template>
        <template v-slot:body-cell-output="props">
          <q-td :props="props" style="white-space: pre-wrap; font-family: monospace; font-size: 12px">
            {{ props.row.output }}
          </q-td>
        </template>
      </q-table>
    </q-card-section>
  </q-card>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { runFleetBulkCLI, type FleetBulkCLIResponse } from "@/api/enhanced";
import { openWebTerminal } from "@/api/core";
import { notifyError, notifySuccess } from "@/utils/notify";

const target = ref("windows");
const shell = ref("powershell");
const timeoutSec = ref(35);
const command = ref("");
const loading = ref(false);
const runningPreset = ref("");
const resultFilter = ref("");
const lastResponse = ref<FleetBulkCLIResponse | null>(null);

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

function launchServerWebTerm() {
  openWebTerminal();
}
</script>
