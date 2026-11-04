<template>
  <q-btn
    dense
    flat
    no-caps
    class="q-mr-sm"
    icon="translate"
    :label="`${activeLocaleOption.flag} ${activeLocaleOption.shortLabel}`"
  >
    <q-tooltip :delay="400">{{ t("nav.language") }}</q-tooltip>
    <q-menu auto-close>
      <q-list dense style="min-width: 190px">
        <q-item-label header class="text-caption text-weight-bold">
          {{ t("nav.language") }}
        </q-item-label>
        <q-item
          v-for="opt in locales"
          :key="opt.code"
          clickable
          v-close-popup
          :active="locale === opt.code"
          active-class="bg-primary text-white"
          @click="selectLanguage(opt.code)"
        >
          <q-item-section avatar style="min-width: 30px">
            <span style="font-size: 16px">{{ opt.flag }}</span>
          </q-item-section>
          <q-item-section>
            <q-item-label>{{ opt.label }}</q-item-label>
          </q-item-section>
          <q-item-section side v-if="locale === opt.code">
            <q-icon name="check" size="xs" color="white" />
          </q-item-section>
        </q-item>
      </q-list>
    </q-menu>
  </q-btn>
</template>

<script setup lang="ts">
import { useI18n, type SupportedLocale } from "@/i18n";
import { notifySuccess } from "@/utils/notify";

const { locale, locales, activeLocaleOption, setLocale, t } = useI18n();

function selectLanguage(code: SupportedLocale) {
  setLocale(code);
  const chosen = locales.find((l) => l.code === code);
  if (chosen) {
    notifySuccess(`${chosen.flag} ${chosen.label}`);
  }
}
</script>
