<template>
  <q-btn
    dense
    flat
    no-caps
    icon="palette"
    class="q-mr-xs trmm-theme-btn"
    data-no-translate="true"
  >
    <q-tooltip :delay="350">Temas &amp; Paletas de Cores</q-tooltip>
    <q-menu
      style="min-width: 310px; max-width: 350px; border-radius: 10px"
    >
      <q-list dense class="q-py-xs">
        <q-item-label header class="text-weight-bold row items-center q-py-sm">
          <q-icon name="palette" color="primary" size="sm" class="q-mr-xs" />
          <span>Temas &amp; Paletas de Cores</span>
        </q-item-label>

        <q-separator />

        <q-item-label caption class="q-px-md q-pt-sm q-pb-xs text-uppercase text-weight-bold" style="font-size: 10px; letter-spacing: 0.6px; opacity: 0.7">
          Temas Escuros
        </q-item-label>

        <q-item
          v-for="pal in darkPalettes"
          :key="pal.id"
          clickable
          v-ripple
          v-close-popup
          @click="selectPalette(pal.id)"
          class="q-mx-xs q-my-xs rounded-borders theme-card-item"
          :class="{ 'theme-card-active': currentPaletteId === pal.id }"
        >
          <q-item-section>
            <q-item-label class="text-weight-bold row items-center justify-between" style="font-size: 13px">
              <span>{{ pal.name }}</span>
              <q-icon
                v-if="currentPaletteId === pal.id"
                name="check_circle"
                color="positive"
                size="xs"
              />
            </q-item-label>
            <div class="row no-wrap q-mt-xs theme-swatch-bar">
              <div
                v-for="(hex, idx) in pal.swatches"
                :key="idx"
                :style="{ backgroundColor: hex, flex: 1 }"
                :title="hex"
              />
            </div>
            <q-item-label caption class="q-mt-xs" style="font-size: 11px; opacity: 0.78">
              {{ pal.subtitle }}
            </q-item-label>
          </q-item-section>
        </q-item>

        <q-separator class="q-my-xs" />

        <q-item-label caption class="q-px-md q-pt-xs q-pb-xs text-uppercase text-weight-bold" style="font-size: 10px; letter-spacing: 0.6px; opacity: 0.7">
          Tema Claro
        </q-item-label>

        <q-item
          v-for="pal in lightPalettes"
          :key="pal.id"
          clickable
          v-ripple
          v-close-popup
          @click="selectPalette(pal.id)"
          class="q-mx-xs q-my-xs rounded-borders theme-card-item"
          :class="{ 'theme-card-active': currentPaletteId === pal.id }"
        >
          <q-item-section>
            <q-item-label class="text-weight-bold row items-center justify-between" style="font-size: 13px">
              <span>{{ pal.name }}</span>
              <q-icon
                v-if="currentPaletteId === pal.id"
                name="check_circle"
                color="positive"
                size="xs"
              />
            </q-item-label>
            <div class="row no-wrap q-mt-xs theme-swatch-bar">
              <div
                v-for="(hex, idx) in pal.swatches"
                :key="idx"
                :style="{ backgroundColor: hex, flex: 1 }"
                :title="hex"
              />
            </div>
            <q-item-label caption class="q-mt-xs" style="font-size: 11px; opacity: 0.78">
              {{ pal.subtitle }}
            </q-item-label>
          </q-item-section>
        </q-item>
      </q-list>
    </q-menu>
  </q-btn>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { THEME_PALETTES, currentPaletteId, applyThemePalette } from "@/utils/themePalettes";
import { notifySuccess } from "@/utils/notify";

const darkPalettes = computed(() => THEME_PALETTES.filter((p) => p.group === "dark"));
const lightPalettes = computed(() => THEME_PALETTES.filter((p) => p.group === "light"));

function selectPalette(id: string) {
  applyThemePalette(id);
  const found = THEME_PALETTES.find((p) => p.id === id);
  if (found) {
    notifySuccess(`Tema aplicado: ${found.name}`);
  }
}
</script>

<style scoped>
.trmm-theme-btn {
  border-radius: 7px;
  padding: 2px 7px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  background: rgba(255, 255, 255, 0.06);
  transition: all 0.15s ease;
}
.trmm-theme-btn:hover {
  background: rgba(255, 255, 255, 0.14);
  border-color: rgba(255, 255, 255, 0.32);
}
.theme-card-item {
  border: 1px solid rgba(148, 163, 184, 0.16);
  transition: border-color 0.15s ease, background-color 0.15s ease;
}
.theme-card-item:hover {
  border-color: rgba(56, 189, 248, 0.45);
}
.theme-card-active {
  border-color: var(--q-primary, #1976d2);
  background: rgba(25, 118, 210, 0.14);
}
.theme-swatch-bar {
  border-radius: 6px;
  overflow: hidden;
  height: 16px;
  border: 1px solid rgba(148, 163, 184, 0.28);
}
</style>
