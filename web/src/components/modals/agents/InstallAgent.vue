<template>
  <q-card style="min-width: 48vw; max-width: 65vw">
    <q-card-section class="row items-center q-pb-sm">
      <q-card-actions align="left">
        <div class="text-h6">{{ t("installAgent.title") }}</div>
      </q-card-actions>
      <q-space />
      <q-card-actions align="right">
        <q-btn v-close-popup flat round dense icon="close" />
      </q-card-actions>
    </q-card-section>
    <q-card-section class="q-pt-none">
      <q-form @submit.prevent="addAgent">
        <div class="row q-col-gutter-sm q-px-md q-mb-sm">
          <div class="col-12 col-md-6">
            <q-select
              outlined
              dense
              options-dense
              :label="t('installAgent.client')"
              v-model="client"
              :options="client_options"
              @update:model-value="site = sites[0]"
            />
          </div>
          <div class="col-12 col-md-6">
            <q-select
              dense
              options-dense
              outlined
              :label="t('installAgent.site')"
              v-model="site"
              :options="sites"
            />
          </div>
        </div>

        <q-card-section class="q-py-xs">
          <div class="text-subtitle2 q-mb-xs">{{ t("installAgent.osLabel") }}</div>
          <div class="q-gutter-sm">
            <q-radio
              v-model="agentOS"
              val="universal_all"
              color="positive"
              class="text-weight-bold"
              label="Todos os Sistemas Operacionais (Universal: Windows + Linux + macOS)"
              @update:model-value="
                installMethod = 'universal_bundle';
                agenttype = 'both';
                goarch = GOARCH_AMD64;
              "
            />
            <q-radio
              v-model="agentOS"
              val="windows"
              label="Windows (10 / 11 / Server)"
              @update:model-value="
                installMethod = 'exe';
                goarch = GOARCH_AMD64;
              "
            />
            <q-radio
              v-model="agentOS"
              val="linux"
              label="Linux (Ubuntu / Debian / Fedora)"
              @update:model-value="
                installMethod = 'bash';
                goarch = GOARCH_AMD64;
              "
            />
            <q-radio
              v-model="agentOS"
              val="darwin"
              label="macOS (Intel / Apple Silicon)"
              @update:model-value="
                installMethod = 'mac';
                goarch = GOARCH_AMD64;
              "
            />
          </div>
        </q-card-section>

        <q-card-section v-show="agentOS === 'linux'" class="q-py-xs">
          <div class="text-subtitle2 q-mb-xs">{{ t("installAgent.linuxDistroLabel") }}</div>
          <div class="column q-gutter-xs">
            <q-radio
              v-model="linuxDistro"
              val="universal"
              :label="t('installAgent.distroUniversal')"
            />
            <q-radio
              v-model="linuxDistro"
              val="ubuntu"
              :label="t('installAgent.distroUbuntu')"
            />
            <q-radio
              v-model="linuxDistro"
              val="debian"
              :label="t('installAgent.distroDebian')"
            />
            <q-radio
              v-model="linuxDistro"
              val="fedora"
              :label="t('installAgent.distroFedora')"
            />
          </div>
        </q-card-section>

        <q-card-section class="q-py-xs">
          <div class="text-subtitle2 q-mb-xs">{{ t("installAgent.agentType") }}</div>
          <div class="q-gutter-sm">
            <q-radio
              v-model="agenttype"
              val="both"
              color="positive"
              label="Ambos (Auto-Detectar Servidor / Estação de Trabalho)"
            />
            <q-radio
              v-model="agenttype"
              val="workstation"
              :label="t('installAgent.workstation')"
            />
            <q-radio
              v-model="agenttype"
              val="server"
              :label="t('installAgent.server')"
              @update:model-value="power = false"
            />
          </div>
        </q-card-section>

        <q-card-section class="q-py-xs">
          <div class="row items-center q-gutter-sm">
            <q-input
              v-model.number="expires"
              dense
              type="number"
              filled
              :label="t('installAgent.tokenExpire')"
              style="max-width: 220px"
              stack-label
            />
            <q-chip
              clickable
              dense
              :color="expires === 24 ? 'primary' : 'grey-8'"
              text-color="white"
              @click="expires = 24"
            >
              24h
            </q-chip>
            <q-chip
              clickable
              dense
              :color="expires === 720 ? 'primary' : 'grey-8'"
              text-color="white"
              @click="expires = 720"
            >
              30 Dias (720h)
            </q-chip>
            <q-chip
              clickable
              dense
              :color="expires === 87600 ? 'positive' : 'grey-8'"
              text-color="white"
              icon="verified"
              @click="expires = 87600"
            >
              10 Anos / Permanente AD (87600h)
            </q-chip>
          </div>
        </q-card-section>

        <q-card-section v-show="agentOS === 'windows' || agentOS === 'universal_all'" class="q-py-xs">
          <div class="q-gutter-sm">
            <q-checkbox v-model="rdp" dense :label="t('installAgent.enableRdp')" />
            <q-checkbox v-model="ping" dense :label="t('installAgent.enablePing')">
              <q-tooltip>
                Enable ICMP echo requests in the local firewall
              </q-tooltip>
            </q-checkbox>
            <q-checkbox
              v-model="power"
              dense
              v-show="agenttype !== 'server'"
              :label="t('installAgent.disableSleep')"
            />
            <q-checkbox
              v-model="bankingSafe"
              dense
              color="teal-7"
              v-show="agenttype !== 'server'"
              label="Modo Compatibilidade Bancária (Estações: Mesh Sob Demanda)"
            >
              <q-tooltip>
                Configura o Mesh Agent como Manual nas Estações Windows para não conflitar nem bloquear acesso a sites de bancos (Warsaw / Topaz / GBPlugin), ligando apenas sob demanda ao assumir controle remoto.
              </q-tooltip>
            </q-checkbox>
          </div>
        </q-card-section>

        <q-card-section v-show="agentOS !== 'universal_all'" class="q-py-xs">
          <div class="text-subtitle2 q-mb-xs">{{ t("installAgent.arch") }}</div>
          <div class="q-gutter-sm">
            <q-radio
              v-model="goarch"
              :val="GOARCH_AMD64"
              label="64 bit (x86_64 / amd64)"
              v-show="agentOS === 'windows' || agentOS === 'linux'"
            />
            <q-radio
              v-model="goarch"
              :val="GOARCH_AMD64"
              label="Intel 64 bit"
              v-show="agentOS === 'darwin'"
            />
            <q-radio
              v-model="goarch"
              :val="GOARCH_i386"
              label="32 bit (i386)"
              v-show="agentOS !== 'darwin'"
            />
            <q-radio
              v-model="goarch"
              :val="GOARCH_ARM64"
              label="ARM 64 bit (aarch64)"
              v-show="agentOS === 'linux'"
            />
            <q-radio
              v-model="goarch"
              :val="GOARCH_ARM64"
              label="Apple Silicon (M-Series)"
              v-show="agentOS === 'darwin'"
            />
            <q-radio
              v-model="goarch"
              :val="GOARCH_ARM32"
              label="ARM 32 bit"
              v-show="agentOS === 'linux'"
            />
          </div>
        </q-card-section>

        <q-card-section v-show="agentOS !== 'universal_all'" class="q-py-xs">
          <div class="text-subtitle2 q-mb-xs">{{ t("installAgent.method") }}</div>
          <div class="q-gutter-sm">
            <q-radio
              v-model="installMethod"
              val="exe"
              v-show="agentOS === 'windows'"
              label="Generated EXE"
            />
            <q-radio
              v-model="installMethod"
              val="powershell"
              v-show="agentOS === 'windows'"
              label="PowerShell (.ps1)"
            />
            <q-radio
              v-model="installMethod"
              val="manual"
              v-show="agentOS === 'windows'"
              label="Standard EXE / Manual"
            />
            <q-radio
              v-model="installMethod"
              val="bash"
              v-show="agentOS === 'linux'"
              :label="t('installAgent.linuxScript')"
            />
            <q-radio
              v-model="installMethod"
              val="linux_manual"
              v-show="agentOS === 'linux'"
              :label="t('installAgent.linuxManual')"
            />
          </div>
        </q-card-section>

        <q-card-actions align="left" class="q-pt-md">
          <q-btn
            :label="installButtonText"
            color="primary"
            icon="download"
            type="submit"
            unelevated
          />
        </q-card-actions>
      </q-form>
    </q-card-section>
    <q-dialog v-model="showAgentDownload">
      <AgentDownload :info="info" @close="showAgentDownload = false" />
    </q-dialog>
  </q-card>
</template>

<script>
import mixins from "@/mixins/mixins";
import AgentDownload from "@/components/modals/agents/AgentDownload.vue";
import { getBaseUrl } from "@/boot/axios";
import { t } from "@/i18n";
import {
  GOARCH_AMD64,
  GOARCH_i386,
  GOARCH_ARM64,
  GOARCH_ARM32,
} from "@/constants/constants";

export default {
  name: "InstallAgent",
  mixins: [mixins],
  components: { AgentDownload },
  props: {
    sitepk: Number,
  },
  data() {
    return {
      GOARCH_AMD64: GOARCH_AMD64,
      GOARCH_i386: GOARCH_i386,
      GOARCH_ARM64: GOARCH_ARM64,
      GOARCH_ARM32: GOARCH_ARM32,
      client_options: [],
      client: null,
      site: null,
      agenttype: "both",
      expires: 87600,
      power: false,
      rdp: true,
      ping: true,
      bankingSafe: true,
      showAgentDownload: false,
      info: {},
      installMethod: "universal_bundle",
      goarch: GOARCH_AMD64,
      agentOS: "universal_all",
      linuxDistro: "universal",
    };
  },
  methods: {
    t,
    getClients() {
      this.$q.loading.show();
      this.$axios
        .get("/clients/")
        .then((r) => {
          this.client_options = this.formatClientOptions(r.data);
          if (this.sitepk !== undefined && this.sitepk !== null) {
            this.client_options.forEach((client) => {
              let site = client.sites.find((site) => site.id === this.sitepk);

              if (site !== undefined) {
                this.client = client;
                this.site = { value: site.id, label: site.name };
              }
            });
          } else {
            this.client = this.client_options[0];
            this.site = this.sites[0];
          }
          this.$q.loading.hide();
        })
        .catch(() => {
          this.$q.loading.hide();
        });
    },
    addAgent() {
      const api = getBaseUrl();
      const clientStripped = this.client.label
        .replace(/\s/g, "")
        .toLowerCase()
        .replace(/([^a-zA-Z0-9]+)/g, "");
      const siteStripped = this.site.label
        .replace(/\s/g, "")
        .toLowerCase()
        .replace(/([^a-zA-Z0-9]+)/g, "");

      const effType = this.agenttype === "both" ? "workstation" : this.agenttype;
      const fileName = `trmm-${clientStripped}-${siteStripped}-${effType}-${this.goarch}.exe`;

      const data = {
        installMethod: this.agentOS === "universal_all" ? "universal_bundle" : this.installMethod,
        client: this.client.value,
        site: this.site.value,
        expires: this.expires,
        agenttype: this.agenttype,
        power: this.power ? 1 : 0,
        rdp: this.rdp ? 1 : 0,
        ping: this.ping ? 1 : 0,
        banking_safe: this.bankingSafe,
        goarch: this.goarch,
        api,
        fileName,
        plat: this.agentOS,
        distro: this.linuxDistro,
      };

      if (this.agentOS === "universal_all" || this.installMethod === "universal_bundle") {
        this.$q.loading.show({ message: "Gerando pacote universal Multi-OS (Windows + Linux + macOS)..." });
        this.$axios
          .post("/agents/installer/", data)
          .then((r) => {
            this.$q.loading.hide();
            this.info = {
              expires: this.expires,
              data: r.data,
              goarch: this.goarch,
              plat: "universal_all",
              distro: this.linuxDistro,
              exeRequestData: {
                ...data,
                plat: "windows",
                installMethod: "exe",
                agenttype: effType,
                fileName,
              },
              fileName,
            };
            this.showAgentDownload = true;
          })
          .catch(() => {
            this.$q.loading.hide();
          });
        return;
      }

      if (
        this.installMethod === "manual" ||
        this.installMethod === "mac" ||
        this.installMethod === "linux_manual"
      ) {
        this.$axios.post("/agents/installer/", data).then((r) => {
          this.info = {
            expires: this.expires,
            data: r.data,
            goarch: this.goarch,
            plat: this.agentOS,
            distro: this.linuxDistro,
          };
          this.showAgentDownload = true;
        });
      } else if (this.installMethod === "exe") {
        this.$q.loading.show({ message: "Gerando executável (.exe)..." });
        this.$axios
          .post("/agents/installer/", data, { responseType: "blob" })
          .then((r) => {
            this.$q.loading.hide();
            const blob = new Blob([r.data], {
              type: "application/vnd.microsoft.portable-executable",
            });
            let link = document.createElement("a");
            link.href = window.URL.createObjectURL(blob);
            link.download = fileName;
            link.click();
            this.showDLMessage();
          })
          .catch(() => {
            this.$q.loading.hide();
          });
      } else if (
        this.installMethod === "powershell" ||
        this.installMethod === "bash"
      ) {
        this.$q.loading.show();
        let ext = this.installMethod === "powershell" ? "ps1" : "sh";
        let distroTag =
          this.installMethod === "bash" ? `-${this.linuxDistro}` : "";
        const scriptName = `rmm-${clientStripped}-${siteStripped}-${effType}${distroTag}.${ext}`;
        this.$axios
          .post("/agents/installer/", data, { responseType: "blob" })
          .then(({ data }) => {
            this.$q.loading.hide();
            const blob = new Blob([data], { type: "text/plain" });
            let link = document.createElement("a");
            link.href = window.URL.createObjectURL(blob);
            link.download = scriptName;
            link.click();
            if (this.installMethod === "powershell") this.showDLMessage();
          })
          .catch(() => {
            this.$q.loading.hide();
          });
      }
    },
    showDLMessage() {
      this.$q.dialog({
        message: `Instalador para ${this.client.label} - ${this.site.label} baixado com sucesso (válido por ${this.expires} horas).`,
      });
    },
  },
  computed: {
    sites() {
      return !!this.client ? this.formatSiteOptions(this.client.sites) : [];
    },
    installButtonText() {
      if (this.agentOS === "universal_all") {
        return "GERAR PACOTE UNIVERSAL MULTI-OS (WINDOWS + LINUX + MACOS)";
      }
      switch (this.installMethod) {
        case "exe":
          return this.t("installAgent.btnExe");
        case "powershell":
          return this.t("installAgent.btnPs1");
        case "manual":
        case "linux_manual":
        case "mac":
          return this.t("installAgent.btnManual");
        case "bash":
          return this.t("installAgent.btnBash");
      }
      return this.t("installAgent.btnManual");
    },
  },
  mounted() {
    this.getClients();
  },
};
</script>
