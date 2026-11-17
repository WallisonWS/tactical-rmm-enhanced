<template>
  <div class="q-video relative-position" :style="{ height: `${$q.screen.height - 26}px` }">
    <iframe
      v-if="vnc"
      :key="iframeKey"
      :src="vnc"
      allow="clipboard-read; clipboard-write"
      allowfullscreen
      frameborder="0"
    ></iframe>
    <div v-else-if="errorMessage" class="column flex-center fit q-pa-lg text-center">
      <q-icon name="cloud_off" size="48px" color="negative" class="q-mb-md" />
      <div class="text-h6 q-mb-xs">Não foi possível iniciar o WebVNC</div>
      <div class="text-body2 text-grey-6 q-mb-md" style="max-width: 540px">
        {{ errorMessage }}
      </div>
      <q-btn color="primary" icon="refresh" label="Tentar Novamente" no-caps @click="getVNCUrl" />
    </div>
    <div v-else class="column flex-center fit">
      <q-spinner color="primary" size="40px" class="q-mb-sm" />
      <div class="text-caption text-grey">Verificando conectividade do Mesh Agent e WebVNC...</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRoute } from "vue-router";
import { useMeta } from "quasar";
import axios from "axios";

const { params } = useRoute();
const vnc = ref("");
const errorMessage = ref("");
const iframeKey = ref(0);

async function getVNCUrl() {
  vnc.value = "";
  errorMessage.value = "";
  try {
    const { data } = await axios.get(`/agents/${params.agent_id}/${params.port}/webvnc/`);
    vnc.value = data.vnc;
    iframeKey.value += 1;
    useMeta({
      title: `${data.hostname} - ${data.client} - ${data.site} | VNC`,
    });
  } catch (e: unknown) {
    const err = e as { response?: { data?: string | { error?: string; detail?: string } } };
    const payload = err?.response?.data;
    if (typeof payload === "string" && payload.trim()) {
      errorMessage.value = payload;
    } else if (payload && typeof payload === "object") {
      errorMessage.value = payload.error || payload.detail || "Agente ou Mesh Agent desconectado.";
    } else {
      errorMessage.value = "Falha ao contatar o agente ou MeshCentral.";
    }
  }
}

onMounted(() => {
  getVNCUrl();
});
</script>
