<template>
  <q-card style="min-width: 72vw; max-width: 88vw" data-no-translate="true">
    <q-bar class="bg-primary text-white">
      <q-icon name="cloud_download" size="sm" class="q-mr-xs" />
      <div class="text-weight-bold">
        {{
          info.plat === "universal_all"
            ? "Central de Implantação Multi-OS (Windows + Linux + macOS)"
            : `Instruções de Instalação (${info.plat ? info.plat.toUpperCase() : ""})`
        }}
      </div>
      <q-space />
      <q-btn v-close-popup flat round dense icon="close" />
    </q-bar>

    <!-- MODO UNIVERSAL MULTI-OS (WINDOWS + LINUX + MACOS) -->
    <q-card-section v-if="info.plat === 'universal_all'">
      <div class="row items-center justify-between q-mb-sm">
        <div class="text-subtitle2">
          Token Único Multi-Plataforma válido por <strong>{{ info.expires }} horas</strong>
          <q-badge color="positive" class="q-ml-xs">Windows 10/11/Server</q-badge>
          <q-badge color="info" class="q-ml-xs">Linux Ubuntu/Debian/Fedora/RHEL</q-badge>
          <q-badge color="purple" class="q-ml-xs">macOS Intel &amp; Apple Silicon</q-badge>
        </div>
      </div>

      <q-tabs
        v-model="osTab"
        dense
        class="text-grey"
        active-color="primary"
        indicator-color="primary"
        align="left"
      >
        <q-tab name="windows" icon="mdi-microsoft-windows" label="1. Windows (EXE + GPO AD)" />
        <q-tab name="linux" icon="mdi-linux" label="2. Linux Universal (.sh)" />
        <q-tab name="macos" icon="mdi-apple" label="3. macOS (Intel & M-Series)" />
      </q-tabs>
      <q-separator />

      <q-tab-panels v-model="osTab" animated>
        <!-- ABA WINDOWS -->
        <q-tab-panel name="windows" class="q-px-none">
          <div class="row q-gutter-sm q-mb-md">
            <q-btn
              color="primary"
              icon="download"
              label="Baixar Executável Windows (.EXE)"
              :loading="downloadingExe"
              @click="downloadGeneratedWindowsExe"
            />
            <q-btn
              color="teal-7"
              icon="domain"
              label="Baixar Script GPO AD (Install-TacticalRMM.ps1)"
              @click="downloadTextFile('Install-TacticalRMM.ps1', info.data.windows.ad_gpo_script)"
            />
            <q-btn
              color="indigo-7"
              icon="terminal"
              label="Baixar Instalador PowerShell (.ps1)"
              @click="downloadTextFile('install-tactical-windows.ps1', info.data.windows.ps_oneliner)"
            />
          </div>

          <div class="text-weight-bold q-mb-xs">
            Comando PowerShell de 1 Linha (Auto-detecta Estação vs. Windows Server):
          </div>
          <q-field outlined dense>
            <template v-slot:control>
              <code style="word-break: break-all; font-size: 12px">{{ info.data.windows.ps_oneliner }}</code>
            </template>
          </q-field>
          <q-btn
            size="sm"
            flat
            dense
            color="primary"
            icon="content_copy"
            label="Copiar Comando PowerShell"
            @click="copyValueToClip(info.data.windows.ps_oneliner)"
            class="q-mt-xs"
          />
        </q-tab-panel>

        <!-- ABA LINUX -->
        <q-tab-panel name="linux" class="q-px-none">
          <div class="row q-gutter-sm q-mb-md">
            <q-btn
              color="primary"
              icon="download"
              label="Baixar Script Linux Universal (install-tactical-linux.sh)"
              @click="downloadTextFile('install-tactical-linux.sh', '#!/usr/bin/env bash\n' + info.data.linux.cmd + '\n')"
            />
          </div>

          <div class="text-weight-bold q-mb-xs">
            Comando Terminal Linux (Auto-detecta Ubuntu / Debian / Fedora / RHEL e x86_64 / ARM64):
          </div>
          <q-field outlined dense>
            <template v-slot:control>
              <code style="word-break: break-all; font-size: 12px">{{ info.data.linux.cmd }}</code>
            </template>
          </q-field>
          <q-btn
            size="sm"
            flat
            dense
            color="primary"
            icon="content_copy"
            label="Copiar Comando Linux"
            @click="copyValueToClip(info.data.linux.cmd)"
            class="q-mt-xs"
          />
        </q-tab-panel>

        <!-- ABA MACOS -->
        <q-tab-panel name="macos" class="q-px-none">
          <div class="row q-gutter-sm q-mb-md">
            <q-btn
              color="primary"
              icon="download"
              label="Baixar Script macOS Universal (install-tactical-macos.sh)"
              @click="downloadTextFile('install-tactical-macos.sh', '#!/usr/bin/env bash\n' + info.data.macos.cmd + '\n')"
            />
          </div>

          <div class="text-weight-bold q-mb-xs">
            Comando Terminal macOS (Auto-detecta Intel 64-bit e Apple Silicon M1/M2/M3/M4):
          </div>
          <q-field outlined dense>
            <template v-slot:control>
              <code style="word-break: break-all; font-size: 12px">{{ info.data.macos.cmd }}</code>
            </template>
          </q-field>
          <q-btn
            size="sm"
            flat
            dense
            color="primary"
            icon="content_copy"
            label="Copiar Comando macOS"
            @click="copyValueToClip(info.data.macos.cmd)"
            class="q-mt-xs"
          />
        </q-tab-panel>
      </q-tab-panels>
    </q-card-section>

    <!-- MODO INDIVIDUAL PADRÃO -->
    <q-card-section v-else>
      <p v-if="info.plat === 'windows'" class="text-subtitle1">
        Execute o comando abaixo no Prompt de Comando ou PowerShell como Administrador:
      </p>
      <p v-else-if="info.plat === 'linux'" class="text-subtitle1">
        Execute o comando abaixo como root (sudo) na máquina <strong>Ubuntu, Debian ou Fedora</strong>:
      </p>
      <p v-else-if="info.plat === 'darwin'" class="text-subtitle1">
        Execute o comando abaixo no Terminal do macOS:
      </p>
      <p>
        <q-field outlined :color="$q.dark.isActive ? 'white' : 'black'">
          <code>{{ info.data.cmd }}</code>
        </q-field>
        <q-btn
          size="md"
          flat
          dense
          icon="content_copy"
          label="Copiar comando"
          @click="copyValueToClip(info.data.cmd)"
          class="q-mt-xs"
        />
      </p>
      <br />
      <p v-if="info.plat === 'windows' || info.plat === 'linux'">
        Nota: O token de autenticação acima é válido por {{ info.expires }} horas.
      </p>
      <q-btn
        v-if="info.plat === 'windows' || info.plat === 'linux'"
        type="a"
        :href="info.data.url"
        color="primary"
        icon="download"
        label="Baixar Binário do Agente"
      />
    </q-card-section>
  </q-card>
</template>

<script>
import { ref } from "vue";
import axios from "axios";
import mixins from "@/mixins/mixins";
import { notifySuccess, notifyError } from "@/utils/notify";
import { copyToClipboard } from "quasar";

export default {
  name: "AgentDownload",
  mixins: [mixins],
  props: ["info"],
  setup(props) {
    const osTab = ref("windows");
    const downloadingExe = ref(false);

    function copyValueToClip(val) {
      copyToClipboard(val).then(() => {
        notifySuccess("Copiado para a área de transferência!");
      });
    }

    function downloadTextFile(filename, content) {
      const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
      const link = document.createElement("a");
      link.href = window.URL.createObjectURL(blob);
      link.download = filename;
      link.click();
      notifySuccess(`Arquivo ${filename} baixado com sucesso!`);
    }

    async function downloadGeneratedWindowsExe() {
      if (!props.info?.exeRequestData) return;
      downloadingExe.value = true;
      try {
        const r = await axios.post("/agents/installer/", props.info.exeRequestData, {
          responseType: "blob",
        });
        const blob = new Blob([r.data], {
          type: "application/vnd.microsoft.portable-executable",
        });
        const link = document.createElement("a");
        link.href = window.URL.createObjectURL(blob);
        link.download = props.info.fileName || "tactical-agent.exe";
        link.click();
        notifySuccess("Executável Windows (.exe) baixado com sucesso!");
      } catch (e) {
        notifyError("Falha ao gerar o executável Windows.");
      } finally {
        downloadingExe.value = false;
      }
    }

    return {
      osTab,
      downloadingExe,
      copyValueToClip,
      downloadTextFile,
      downloadGeneratedWindowsExe,
    };
  },
};
</script>
