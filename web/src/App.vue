<template>
  <router-view />
</template>

<script>
import { initSiteTranslator } from "@/i18n";

export default {
  name: "App",
  mounted() {
    initSiteTranslator();
  },
};
</script>

<style lang="sass">
body
  overflow-y: hidden

a
  color: #1976D2

.tbl-sticky
  thead tr th
    position: sticky
    z-index: 1
  thead tr:first-child th
    top: 0

.tabs-tbl-sticky

  thead tr th
    position: sticky
    z-index: 1
  thead tr:first-child th
    top: 0

.remote-bg-tbl-sticky
  max-height: 70vh

  thead tr th
    position: sticky
    z-index: 1
  thead tr:first-child th
    top: 0

.audit-mgr-tbl-sticky
  max-height: 75vh

  thead tr th
    position: sticky
    z-index: 1
  thead tr:first-child th
    top: 0

.settings-tbl-sticky
  max-height: 60vh

  thead tr th
    position: sticky
    z-index: 1
  thead tr:first-child th
    top: 0

.agents-tbl-sticky
  thead tr th
    position: sticky
    z-index: 1
  thead tr:first-child th
    top: 0

.table-bgcolor
  .q-table__top,
  .q-table__bottom,
  thead tr:first-child th
    background-color: #f5f4f2
    font-weight: 600
  tbody tr:hover
    background-color: rgba(25, 118, 210, 0.08)

.table-bgcolor-dark
  .q-table__top,
  .q-table__bottom,
  thead tr:first-child th
    background-color: #181b20
    font-weight: 600
  tbody tr:hover
    background-color: rgba(25, 118, 210, 0.16)

.bg-dark
  background-color: --q-page-dark

.bg-light
  background-color: #ffffff

.highlight
  background-color: #c9e6ff !important
  box-shadow: inset 3px 0 0 #1976D2

.highlight-dark
  background-color: #263244 !important
  box-shadow: inset 3px 0 0 #42a5f5

.action-completed
  background-color: $positive

.agent-offline
  background: gray !important

.agent-overdue
  background: red !important

.min-width
  min-width: 0px !important

.q-bar
  height: auto !important
  min-height: 32px
  flex-wrap: wrap
  row-gap: 4px
  padding-top: 3px
  padding-bottom: 3px

.q-btn__content
  flex-wrap: nowrap !important
  white-space: nowrap !important

.trmm-subtabs
  .q-tab__content
    flex-wrap: nowrap !important
    white-space: nowrap !important
</style>
