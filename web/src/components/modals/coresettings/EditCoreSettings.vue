<template>
  <q-card style="min-width: 68vw; max-width: 92vw; max-height: 92vh">
    <q-splitter v-model="splitterModel">
      <template v-slot:before>
        <q-tabs dense v-model="tab" vertical class="text-primary">
          <q-tab name="general" label="Geral" />
          <q-tab name="themes" label="Temas & Paletas" />
          <q-tab name="emailalerts" label="Alertas por E-mail" />
          <q-tab name="smsalerts" label="Alertas por SMS" />
          <q-tab name="meshcentral" label="MeshCentral" />
          <q-tab name="customfields" label="Campos Personalizados" />
          <q-tab name="keystore" label="Cofre de Chaves" />
          <q-tab name="urlactions" label="Ações de URL" />
          <q-tab name="webhooks" label="Web Hooks" />
          <q-tab name="retention" label="Retenção de Dados" />
          <q-tab name="apikeys" label="Chaves de API" />
          <q-tab name="sso" label="Single Sign-On (SSO)" />
          <q-tab name="schedules" label="Agendamentos" />
          <q-tab name="openai" label="Inteligência Artificial (IA)" />
        </q-tabs>
      </template>
      <template v-slot:after>
        <q-form @submit.prevent="editSettings" @validation-error="onValidationError">
          <q-card-section class="row items-center q-py-sm">
            <div class="text-h6">Configurações Globais</div>
            <q-space />
            <q-btn icon="close" flat round dense v-close-popup />
          </q-card-section>
          <q-scroll-area
            :thumb-style="thumbStyle"
            style="height: 68vh; max-height: calc(92vh - 136px); min-height: 360px"
          >
            <q-tab-panels
              v-model="tab"
              animated
              class="q-pb-md"
              transition-prev="jump-up"
              transition-next="jump-up"
            >
              <!-- general -->
              <q-tab-panel name="general">
                <div class="text-subtitle2">Configurações Gerais</div>
                <q-separator />
                <q-card-section class="row">
                  <q-checkbox
                    v-model="settings.agent_auto_update"
                    label="Habilitar atualização automática dos agentes"
                  >
                    <q-tooltip> Executa automaticamente a cada hora </q-tooltip>
                  </q-checkbox>
                </q-card-section>
                <q-card-section class="row">
                  <q-checkbox
                    v-model="settings.enable_server_scripts"
                    label="Habilitar execução de scripts no servidor (Server-Side Scripts)"
                  />
                </q-card-section>
                <q-card-section class="row">
                  <q-checkbox
                    v-model="settings.enable_server_webterminal"
                    label="Habilitar Terminal Web do Servidor e CLI em Massa (>_)"
                  />
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-4">Fuso horário padrão dos agentes:</div>
                  <div class="col-2"></div>
                  <tactical-dropdown
                    filterable
                    outlined
                    dense
                    options-dense
                    v-model="settings.default_time_zone"
                    :options="allTimezones"
                    class="col-6"
                  />
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-4">Formato de data padrão:</div>
                  <div class="col-2"></div>
                  <q-input
                    outlined
                    dense
                    v-model="settings.date_format"
                    class="col-6"
                  >
                    <template v-slot:after>
                      <q-btn
                        round
                        dense
                        flat
                        size="sm"
                        icon="info"
                        @click="
                          openURL(
                            'https://quasar.dev/quasar-utils/date-utils#format-for-display',
                          )
                        "
                      >
                        <q-tooltip>Ver opções de formatação</q-tooltip>
                      </q-btn>
                    </template>
                  </q-input>
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-4">Política padrão para Servidores:</div>
                  <div class="col-2"></div>
                  <q-select
                    clearable
                    map-options
                    emit-value
                    outlined
                    dense
                    options-dense
                    v-model="settings.server_policy"
                    :options="policies"
                    class="col-6"
                  />
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-4">Política padrão para Estações de Trabalho:</div>
                  <div class="col-2"></div>
                  <q-select
                    clearable
                    map-options
                    emit-value
                    outlined
                    dense
                    options-dense
                    v-model="settings.workstation_policy"
                    :options="policies"
                    class="col-6"
                  />
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-4">Modelo de alerta padrão:</div>
                  <div class="col-2"></div>
                  <q-select
                    clearable
                    map-options
                    emit-value
                    outlined
                    dense
                    options-dense
                    v-model="settings.alert_template"
                    :options="alertTemplateOptions"
                    class="col-6"
                  />
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-4 flex items-center">
                    Receber notificações em:
                  </div>
                  <div class="col-2"></div>
                  <q-checkbox
                    dense
                    v-model="settings.notify_on_info_alerts"
                    class="col-3"
                    label="Alertas Informativos"
                  />
                  <q-checkbox
                    dense
                    v-model="settings.notify_on_warning_alerts"
                    class="col-3"
                    label="Alertas de Aviso"
                  />
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-4">Nível de Depuração do Agente:</div>
                  <div class="col-2"></div>
                  <q-select
                    emit-value
                    map-options
                    outlined
                    dense
                    options-dense
                    v-model="settings.agent_debug_level"
                    :options="logLevelOptions"
                    class="col-6"
                  />
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-4">
                    Limpar falhas de agentes sem resposta após (dias):
                  </div>
                  <div class="col-2"></div>
                  <q-input
                    hint="Definir como 0 desativa esta função"
                    outlined
                    dense
                    type="number"
                    v-model.number="settings.clear_faults_days"
                    class="col-6"
                    :rules="[(val) => (val !== null && val !== '' && Number(val) >= 0) || 'Mínimo é 0']"
                  />
                </q-card-section>
                <q-card-section class="row items-start content-between">
                  <div class="col-6">Experiência do Terminal</div>
                  <div class="col-6">
                    <q-option-group
                      class="q-gutter-lg"
                      v-model="settings.terminal_mode"
                      :options="terminalModeOptions"
                      type="radio"
                      inline
                      dense
                    />
                  </div>
                </q-card-section>
                <q-card-section class="row items-start content-between">
                  <div class="col-6">Experiência do Gerenciador de Arquivos</div>
                  <div class="col-6">
                    <q-option-group
                      class="q-gutter-lg"
                      v-model="settings.file_browser_mode"
                      :options="fileBrowserModeOptions"
                      type="radio"
                      inline
                      dense
                    />
                  </div>
                </q-card-section>
                <q-card-section class="row items-start content-between">
                  <div class="col-6">Terminal Padrão do Windows</div>
                  <div class="col-6">
                    <q-option-group
                      class="q-gutter-lg"
                      v-model="settings.default_shell_windows"
                      :options="windowsShellOptions"
                      type="radio"
                      inline
                      dense
                    />
                    <q-input
                      v-if="settings.default_shell_windows === 'custom'"
                      v-model="settings.default_shell_windows_custom"
                      class="q-mt-md"
                      dense
                      outlined
                      placeholder="Informe o caminho do shell personalizado"
                      bottom-slots
                    >
                      <template v-slot:hint>
                        <span style="font-size: 1.2em">
                          Ex.: C:\Program Files\PowerShell\7\pwsh.exe
                        </span>
                      </template>
                    </q-input>
                  </div>
                </q-card-section>
                <q-card-section class="row items-start content-between">
                  <div class="col-6">Terminal Padrão do Linux</div>
                  <div class="col-6">
                    <q-option-group
                      class="q-gutter-lg"
                      v-model="settings.default_shell_linux"
                      :options="linuxShellOptions"
                      type="radio"
                      inline
                      dense
                    />
                    <q-input
                      v-if="settings.default_shell_linux === 'custom'"
                      v-model="settings.default_shell_linux_custom"
                      class="q-mt-md"
                      dense
                      outlined
                      placeholder="Informe o caminho do shell (ex.: /usr/bin/fish)"
                    />
                  </div>
                </q-card-section>
                <q-card-section class="row items-start content-between">
                  <div class="col-6">Terminal Padrão do macOS</div>
                  <div class="col-6">
                    <q-option-group
                      class="q-gutter-lg"
                      v-model="settings.default_shell_darwin"
                      :options="darwinShellOptions"
                      type="radio"
                      inline
                      dense
                    />
                    <q-input
                      v-if="settings.default_shell_darwin === 'custom'"
                      v-model="settings.default_shell_darwin_custom"
                      class="q-mt-md"
                      dense
                      outlined
                      placeholder="Informe o caminho do shell (ex.: /bin/zsh)"
                    />
                  </div>
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-4">Redefinir Política de Patches nos Agentes:</div>
                  <div class="col-2"></div>
                  <q-btn
                    color="negative"
                    label="Redefinir"
                    @click="showResetPatchPolicy"
                  />
                </q-card-section>
              </q-tab-panel>
              <!-- email alerts -->
              <q-tab-panel name="emailalerts">
                <div class="text-subtitle2 row">
                  <div>Email Alert Routing</div>
                  <q-space />
                  <div>
                    <q-btn
                      size="sm"
                      color="grey-5"
                      icon="fas fa-plus"
                      text-color="black"
                      label="Add emails"
                      @click="toggleAddEmail"
                    />
                  </div>
                </div>
                <q-separator />
                <q-card-section class="row">
                  <div class="col-3">Recipients</div>
                  <div class="col-4"></div>
                  <div class="col-5">
                    <q-list
                      dense
                      v-if="
                        ready && settings.email_alert_recipients.length !== 0
                      "
                    >
                      <q-item
                        v-for="email in settings.email_alert_recipients"
                        :key="email"
                        clickable
                        v-ripple
                        @click="removeEmail(email)"
                      >
                        <q-item-section>
                          <q-item-label>{{ email }}</q-item-label>
                        </q-item-section>
                        <q-item-section side>
                          <q-icon name="delete" color="red" />
                        </q-item-section>
                      </q-item>
                    </q-list>
                    <q-list v-else>
                      <q-item-section>
                        <q-item-label>No recipients</q-item-label>
                      </q-item-section>
                    </q-list>
                  </div>
                </q-card-section>
                <!-- smtp -->
                <div class="text-subtitle2">Configurações SMTP</div>
                <q-separator />
                <q-card-section class="row">
                  <div class="col-2">E-mail remetente:</div>
                  <div class="col-4"></div>
                  <q-input
                    outlined
                    dense
                    v-model="settings.smtp_from_email"
                    class="col-6 q-pa-none"
                    :rules="[(val) => !val || isValidEmail(val) || 'E-mail inválido']"
                  />
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-2">Nome remetente:</div>
                  <div class="col-4"></div>
                  <q-input
                    outlined
                    dense
                    v-model="settings.smtp_from_name"
                    class="col-6 q-pa-none"
                  />
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-2">Servidor (Host):</div>
                  <div class="col-4"></div>
                  <q-input
                    outlined
                    dense
                    v-model="settings.smtp_host"
                    class="col-6 q-pa-none"
                  />
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-2">Porta:</div>
                  <div class="col-4"></div>
                  <q-input
                    dense
                    v-model.number="settings.smtp_port"
                    type="number"
                    filled
                    class="q-pa-none"
                    :rules="[
                      (val) => !val || (Number(val) > 0 && Number(val) <= 65535) || 'Porta inválida',
                    ]"
                  />
                </q-card-section>
                <q-card-section class="row">
                  <q-checkbox
                    v-model="settings.smtp_requires_auth"
                    label="My Server Requires Authentication"
                    class="q-pa-none"
                  />
                </q-card-section>
                <q-card-section
                  class="row"
                  v-show="settings.smtp_requires_auth"
                >
                  <div class="col-2">Username:</div>
                  <div class="col-4"></div>
                  <q-input
                    outlined
                    dense
                    v-model="settings.smtp_host_user"
                    class="col-6 q-pa-none"
                  />
                </q-card-section>
                <q-card-section
                  class="row"
                  v-show="settings.smtp_requires_auth"
                >
                  <div class="col-2">Password:</div>
                  <div class="col-4"></div>
                  <q-input
                    outlined
                    dense
                    class="col-6 q-pa-none"
                    v-model="settings.smtp_host_password"
                    :type="isPwd ? 'password' : 'text'"
                  >
                    <template v-slot:append>
                      <q-icon
                        :name="isPwd ? 'visibility_off' : 'visibility'"
                        class="cursor-pointer"
                        @click="isPwd = !isPwd"
                      />
                    </template>
                  </q-input>
                </q-card-section>
              </q-tab-panel>
              <!-- twilio sms alerts -->
              <q-tab-panel name="smsalerts">
                <div class="text-subtitle2 row">
                  <div>SMS Alert Routing</div>
                  <q-space />
                  <div>
                    <q-btn
                      size="sm"
                      color="grey-5"
                      icon="fas fa-plus"
                      text-color="black"
                      label="Add numbers"
                      @click="toggleAddSMSNumber"
                    />
                  </div>
                </div>
                <q-separator />
                <q-card-section class="row">
                  <div class="col-3">Recipients</div>
                  <div class="col-4"></div>
                  <div class="col-5">
                    <q-list
                      dense
                      v-if="ready && settings.sms_alert_recipients.length !== 0"
                    >
                      <q-item
                        v-for="num in settings.sms_alert_recipients"
                        :key="num"
                        clickable
                        v-ripple
                        @click="removeSMSNumber(num)"
                      >
                        <q-item-section>
                          <q-item-label>{{ num }}</q-item-label>
                        </q-item-section>
                        <q-item-section side>
                          <q-icon name="delete" color="red" />
                        </q-item-section>
                      </q-item>
                    </q-list>
                    <q-list v-else>
                      <q-item-section>
                        <q-item-label>No recipients</q-item-label>
                      </q-item-section>
                    </q-list>
                  </div>
                </q-card-section>
                <!-- smtp -->
                <div class="text-subtitle2">Twilio Settings</div>
                <q-separator />
                <q-card-section class="row">
                  <div class="col-3">Twilio Number:</div>
                  <div class="col-3"></div>
                  <q-input
                    outlined
                    dense
                    v-model="settings.twilio_number"
                    class="col-6 q-pa-none"
                    placeholder="+12131231234"
                  />
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-3">Twilio Account SID:</div>
                  <div class="col-3"></div>
                  <q-input
                    outlined
                    dense
                    v-model="settings.twilio_account_sid"
                    class="col-6 q-pa-none"
                  />
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-3">Twilio Auth Token:</div>
                  <div class="col-3"></div>
                  <q-input
                    outlined
                    dense
                    v-model="settings.twilio_auth_token"
                    class="col-6 q-pa-none"
                  />
                </q-card-section>
              </q-tab-panel>
              <!-- meshcentral -->
              <q-tab-panel name="meshcentral">
                <div class="text-subtitle2">Configurações MeshCentral</div>
                <q-separator />
                <q-card-section class="row" v-if="!hosted">
                  <div class="col-4">Usuário Mesh:</div>
                  <div class="col-2"></div>
                  <q-input
                    dense
                    outlined
                    v-model="settings.mesh_username"
                    class="col-6"
                    :rules="[
                      (val) =>
                        !val ||
                        !/[A-Z]/.test(String(val)) ||
                        'O usuário deve ser todo em minúsculas',
                    ]"
                  />
                </q-card-section>
                <q-card-section class="row" v-if="!hosted">
                  <div class="col-4">Mesh Site:</div>
                  <div class="col-2"></div>
                  <q-input
                    dense
                    outlined
                    v-model="settings.mesh_site"
                    class="col-6"
                  />
                </q-card-section>
                <q-card-section class="row" v-if="!hosted">
                  <div class="col-4">Mesh Token:</div>
                  <div class="col-2"></div>
                  <q-input
                    dense
                    outlined
                    v-model="settings.mesh_token"
                    class="col-6"
                  />
                </q-card-section>
                <q-card-section class="row" v-if="!hosted">
                  <div class="col-4">Mesh Device Group Name:</div>
                  <div class="col-2"></div>
                  <q-input
                    dense
                    outlined
                    v-model="settings.mesh_device_group"
                    class="col-6"
                  />
                </q-card-section>
                <q-card-section class="row" v-if="!hosted">
                  <div class="col-4 flex items-center">
                    Sync Mesh Perms with TRMM:
                    <q-icon
                      right
                      name="ion-information-circle-outline"
                      size="sm"
                      class="cursor-pointer"
                    >
                      <q-tooltip class="text-caption">
                        It is recommended to keep this option enabled;
                        otherwise, all TRMM users will have full permissions in
                        MeshCentral regardless of their permissions in TRMM.
                      </q-tooltip>
                    </q-icon>
                  </div>
                  <div class="col-2"></div>
                  <q-checkbox
                    dense
                    :model-value="settings.sync_mesh_with_trmm"
                    @update:model-value="confirmSyncChange"
                    class="col-6"
                  />
                </q-card-section>

                <q-card-section class="row items-center">
                  <div class="col-4 flex items-center">
                    Company Name:
                    <q-icon
                      name="ion-information-circle-outline"
                      size="sm"
                      class="q-ml-sm cursor-pointer"
                    >
                      <q-tooltip class="text-caption">
                        Adding your company name here will append it to the
                        user's full name that appears when doing a remote
                        control session, for example: 'John Doe - Amidaware
                        Inc.'
                      </q-tooltip>
                    </q-icon>
                  </div>

                  <div class="col-2"></div>

                  <q-input
                    dense
                    outlined
                    v-model="settings.mesh_company_name"
                    class="col-6"
                  >
                  </q-input>
                </q-card-section>
              </q-tab-panel>

              <!-- custom fields -->
              <q-tab-panel name="customfields">
                <CustomFields />
              </q-tab-panel>

              <!-- key store -->
              <q-tab-panel name="keystore">
                <KeyStoreTable />
              </q-tab-panel>

              <!-- url actions -->
              <q-tab-panel name="urlactions">
                <URLActionsTable type="web" />
              </q-tab-panel>

              <!-- web hooks -->
              <q-tab-panel name="webhooks">
                <URLActionsTable type="rest" />
              </q-tab-panel>

              <!-- retention -->
              <q-tab-panel name="retention">
                <q-card-section class="row">
                  <div class="col-4">Histórico de Verificações (dias):</div>
                  <div class="col-2"></div>
                  <q-input
                    dense
                    outlined
                    type="number"
                    v-model.number="settings.check_history_prune_days"
                    :rules="[(val) => (val !== null && val !== '' && Number(val) >= 0) || 'Mínimo é 0']"
                    class="col-6"
                    hint="Definir como 0 desativa esta função"
                  />
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-4">Alertas Resolvidos (dias):</div>
                  <div class="col-2"></div>
                  <q-input
                    dense
                    outlined
                    type="number"
                    v-model.number="settings.resolved_alerts_prune_days"
                    :rules="[(val) => (val !== null && val !== '' && Number(val) >= 0) || 'Mínimo é 0']"
                    class="col-6"
                    hint="Definir como 0 desativa esta função"
                  />
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-4">Histórico de Agentes (dias):</div>
                  <div class="col-2"></div>
                  <q-input
                    dense
                    outlined
                    type="number"
                    v-model.number="settings.agent_history_prune_days"
                    :rules="[(val) => (val !== null && val !== '' && Number(val) >= 0) || 'Mínimo é 0']"
                    class="col-6"
                    hint="Definir como 0 desativa esta função"
                  />
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-4">Logs de Depuração (dias):</div>
                  <div class="col-2"></div>
                  <q-input
                    dense
                    outlined
                    type="number"
                    v-model.number="settings.debug_log_prune_days"
                    :rules="[(val) => (val !== null && val !== '' && Number(val) >= 0) || 'Mínimo é 0']"
                    class="col-6"
                    hint="Definir como 0 desativa esta função"
                  />
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-4">Logs de Auditoria (dias):</div>
                  <div class="col-2"></div>
                  <q-input
                    dense
                    outlined
                    type="number"
                    v-model.number="settings.audit_log_prune_days"
                    :rules="[(val) => (val !== null && val !== '' && Number(val) >= 0) || 'Mínimo é 0']"
                    class="col-6"
                    hint="Definir como 0 desativa esta função"
                  />
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-4">Histórico de Relatórios (dias):</div>
                  <div class="col-2"></div>
                  <q-input
                    dense
                    outlined
                    type="number"
                    v-model.number="settings.report_history_prune_days"
                    :rules="[(val) => (val !== null && val !== '' && Number(val) >= 0) || 'Mínimo é 0']"
                    class="col-6"
                    hint="Definir como 0 desativa esta função"
                  />
                </q-card-section>
              </q-tab-panel>

              <q-tab-panel name="apikeys">
                <APIKeysTable />
              </q-tab-panel>

              <!-- sso integration -->
              <q-tab-panel name="sso">
                <SSOProvidersTable />
              </q-tab-panel>

              <!-- themes & palettes -->
              <q-tab-panel name="themes">
                <div class="text-subtitle2 q-mb-xs">Temas &amp; Paletas de Cores</div>
                <q-separator class="q-mb-md" />
                <div class="row q-col-gutter-md">
                  <div
                    v-for="pal in themePalettes"
                    :key="pal.id"
                    class="col-12 col-md-6"
                  >
                    <q-card
                      bordered
                      flat
                      class="cursor-pointer q-pa-sm"
                      :style="{
                        borderColor: activePalette === pal.id ? pal.primary : 'rgba(255,255,255,0.18)',
                        borderWidth: activePalette === pal.id ? '2px' : '1px',
                      }"
                      @click="choosePalette(pal.id)"
                    >
                      <div class="row items-center justify-between q-mb-xs">
                        <div class="text-weight-bold">{{ pal.name }}</div>
                        <q-badge v-if="activePalette === pal.id" color="positive">
                          Ativo
                        </q-badge>
                      </div>
                      <div
                        class="row no-wrap"
                        style="height: 36px; border-radius: 8px; overflow: hidden; border: 1px solid rgba(255,255,255,0.15)"
                      >
                        <div
                          v-for="(hex, i) in pal.swatches"
                          :key="i"
                          :style="{ backgroundColor: hex, flex: 1 }"
                          class="column justify-end items-center q-pb-xs"
                        >
                          <span
                            style="font-size: 9px; font-family: monospace; background: rgba(0,0,0,0.55); color: #fff; padding: 1px 3px; border-radius: 3px"
                          >
                            {{ hex }}
                          </span>
                        </div>
                      </div>
                    </q-card>
                  </div>
                </div>
              </q-tab-panel>

              <!-- schedules -->
              <q-tab-panel name="schedules">
                <ScheduleTable />
              </q-tab-panel>

              <!-- Open AI -->
              <q-tab-panel name="openai">
                <div class="text-subtitle2">Inteligência Artificial (OpenAI / LLM)</div>
                <q-separator />
                <q-card-section class="row">
                  <div class="col-4">Chave de API (API Key):</div>
                  <div class="col-2"></div>
                  <q-input
                    dense
                    outlined
                    v-model="settings.open_ai_token"
                    class="col-6"
                  />
                </q-card-section>
                <q-card-section class="row">
                  <div class="col-4">Modelo de IA:</div>
                  <div class="col-2"></div>
                  <q-input
                    dense
                    outlined
                    v-model="settings.open_ai_model"
                    class="col-6"
                  />
                </q-card-section>
              </q-tab-panel>
            </q-tab-panels>
          </q-scroll-area>
          <q-card-section class="row items-center">
            <q-btn
              v-show="
                tab === 'general' ||
                tab === 'emailalerts' ||
                tab === 'smsalerts' ||
                tab === 'meshcentral' ||
                tab === 'retention' ||
                tab === 'openai'
              "
              label="Salvar"
              color="primary"
              type="submit"
            />
            <q-btn
              v-show="tab === 'emailalerts'"
              label="Salvar e Testar E-mail"
              color="primary"
              type="submit"
              class="q-ml-md"
              @click="emailTest = true"
            />
            <q-btn
              v-show="tab === 'smsalerts'"
              label="Salvar e Testar SMS"
              color="primary"
              type="submit"
              class="q-ml-md"
              @click="smsTest = true"
            />
          </q-card-section>
        </q-form>
      </template>
    </q-splitter>
  </q-card>
</template>

<script>
import { openURL } from "quasar";
import mixins from "@/mixins/mixins";
import ResetPatchPolicy from "@/components/modals/coresettings/ResetPatchPolicy.vue";
import CustomFields from "@/components/modals/coresettings/CustomFields.vue";
import KeyStoreTable from "@/components/modals/coresettings/KeyStoreTable.vue";
import URLActionsTable from "@/components/modals/coresettings/URLActionsTable.vue";
import APIKeysTable from "@/components/core/APIKeysTable.vue";
import SSOProvidersTable from "@/ee/sso/components/SSOProvidersTable.vue";
import TacticalDropdown from "@/components/ui/TacticalDropdown.vue";
import ScheduleTable from "@/core/settings/components/ScheduleTable.vue";
import { THEME_PALETTES, currentPaletteId, applyThemePalette } from "@/utils/themePalettes";

export default {
  name: "EditCoreSettings",
  emits: ["close"],
  components: {
    CustomFields,
    KeyStoreTable,
    URLActionsTable,
    APIKeysTable,
    SSOProvidersTable,
    TacticalDropdown,
    ScheduleTable,
  },
  mixins: [mixins],
  data() {
    return {
      themePalettes: THEME_PALETTES,
      ready: false,
      policies: [],
      settings: {},
      email: null,
      tab: "general",
      splitterModel: 20,
      isPwd: true,
      allTimezones: [],
      emailTest: false,
      smsTest: false,
      thumbStyle: {
        right: "2px",
        borderRadius: "5px",
        backgroundColor: "#027be3",
        width: "5px",
        opacity: 0.75,
      },
      alertTemplateOptions: [],
      logLevelOptions: [
        { label: "Info", value: "info" },
        { label: "Warning", value: "warning" },
        { label: "Error", value: "error" },
        { label: "Critical", value: "critical" },
      ],
    };
  },
  computed: {
    activePalette() {
      return currentPaletteId.value;
    },
    hosted() {
      return false;
    },
    terminalModeOptions() {
      return [
        { label: "Usar novo terminal", value: "new" },
        { label: "Usar terminal clássico", value: "legacy" },
      ];
    },
    fileBrowserModeOptions() {
      return [
        { label: "Usar novo gerenciador de arquivos", value: "new" },
        { label: "Usar gerenciador clássico", value: "legacy" },
      ];
    },
    windowsShellOptions() {
      return [
        { label: "CMD", value: "cmd" },
        { label: "PowerShell", value: "powershell" },
        { label: "Custom", value: "custom" },
      ];
    },
    linuxShellOptions() {
      return [
        { label: "Bash", value: "bash" },
        { label: "Custom", value: "custom" },
      ];
    },
    darwinShellOptions() {
      return [
        { label: "Bash", value: "bash" },
        { label: "Custom", value: "custom" },
      ];
    },
  },
  watch: {
    tab(newTab, oldTab) {
      if (oldTab === "sso") {
        this.getCoreSettings();
      }
    },
  },
  methods: {
    choosePalette(id) {
      applyThemePalette(id);
      this.notifySuccess("Paleta de cores aplicada com sucesso!");
    },
    openURL(url) {
      openURL(url);
    },
    getCoreSettings() {
      this.$axios.get("/core/settings/").then((r) => {
        const data = r.data || {};
        data.email_alert_recipients = Array.isArray(data.email_alert_recipients)
          ? data.email_alert_recipients
          : [];
        data.sms_alert_recipients = Array.isArray(data.sms_alert_recipients)
          ? data.sms_alert_recipients
          : [];
        if (!data.open_ai_model) data.open_ai_model = "gpt-4o-mini";
        this.settings = data;
        this.allTimezones = Object.freeze(data.all_timezones || []);
        this.ready = true;
      });
    },
    getPolicies() {
      this.$q.loading.show();
      this.$axios
        .get("/automation/policies/")
        .then((r) => {
          this.policies = r.data.map((policy) => ({
            label: policy.name,
            value: policy.id,
          }));
          this.$q.loading.hide();
        })
        .catch(() => {
          this.$q.loading.hide();
        });
    },
    getAlertTemplates() {
      this.$axios.get("alerts/templates/").then((r) => {
        this.alertTemplateOptions = r.data.map((template) => ({
          label: template.name,
          value: template.id,
        }));
      });
    },
    confirmSyncChange(newValue) {
      this.$q
        .dialog({
          title: "Are you sure?",
          message:
            "This operation may take several minutes to complete in the background and can be very CPU/disk intensive, depending on your hardware and number of agents. Please allow time for the sync to fully complete.",
          ok: { label: "Yes", color: "primary" },
          cancel: { label: "No", color: "negative" },
        })
        .onOk(() => {
          this.settings.sync_mesh_with_trmm = newValue;
        });
    },
    showResetPatchPolicy() {
      this.$q.dialog({
        component: ResetPatchPolicy,
      });
    },
    toggleAddEmail() {
      this.$q
        .dialog({
          title: "Add email",
          prompt: {
            model: "",
            isValid: (val) => this.isValidEmail(val),
            type: "email",
          },
          cancel: true,
          ok: { label: "Add", color: "primary" },
          persistent: false,
        })
        .onOk((data) => {
          this.settings.email_alert_recipients.push(data);
        });
    },
    toggleAddSMSNumber() {
      this.$q
        .dialog({
          title: "Add number",
          message:
            "Use E.164 format: must have the <b>+</b> symbol and <span class='text-red'>country code</span>, followed by the <span class='text-green'>phone number</span> e.g. <b>+<span class='text-red'>1</span><span class='text-green'>2131231234</span></b>",
          prompt: {
            model: "",
          },
          html: true,
          cancel: true,
          ok: { label: "Add", color: "primary" },
          persistent: false,
        })
        .onOk((data) => {
          this.settings.sms_alert_recipients.push(data);
        });
    },
    removeEmail(email) {
      const removed = this.settings.email_alert_recipients.filter(
        (k) => k !== email,
      );
      this.settings.email_alert_recipients = removed;
    },
    removeSMSNumber(num) {
      const removed = this.settings.sms_alert_recipients.filter(
        (k) => k !== num,
      );
      this.settings.sms_alert_recipients = removed;
    },
    onValidationError() {
      this.emailTest = false;
      this.smsTest = false;
      this.notifyError("Verifique os campos obrigatórios ou inválidos antes de salvar.");
    },
    editSettings() {
      this.$q.loading.show();
      const payload = { ...this.settings };
      delete payload.all_timezones;
      const intFields = [
        "clear_faults_days",
        "smtp_port",
        "check_history_prune_days",
        "resolved_alerts_prune_days",
        "agent_history_prune_days",
        "debug_log_prune_days",
        "audit_log_prune_days",
        "report_history_prune_days",
      ];
      for (const key of intFields) {
        if (payload[key] === "" || payload[key] === null || payload[key] === undefined) {
          payload[key] = key === "smtp_port" ? 25 : 0;
        } else {
          payload[key] = Number(payload[key]);
        }
      }
      this.$axios
        .put("/core/settings/", payload)
        .then(() => {
          this.$q.loading.hide();
          if (this.emailTest) {
            this.$q.loading.show({ message: "Enviando e-mail de teste..." });
            this.$axios
              .post("/core/emailtest/")
              .then((r) => {
                this.emailTest = false;
                this.$q.loading.hide();
                this.getCoreSettings();
                this.notifySuccess(r.data, 3000);
              })
              .catch(() => {
                this.emailTest = false;
                this.$q.loading.hide();
              });
          } else if (this.smsTest) {
            this.$q.loading.show({ message: "Enviando SMS de teste..." });
            this.$axios
              .post("/core/smstest/")
              .then((r) => {
                this.smsTest = false;
                this.$q.loading.hide();
                this.getCoreSettings();
                this.notifySuccess(r.data, 3000);
              })
              .catch(() => {
                this.smsTest = false;
                this.$q.loading.hide();
              });
          } else {
            this.$emit("close");
            this.$store.dispatch("getDashInfo", false);
            this.notifySuccess("Configurações salvas com sucesso!");
          }
        })
        .catch((err) => {
          this.emailTest = false;
          this.smsTest = false;
          this.$q.loading.hide();
          const detail = err?.response?.data;
          if (detail && typeof detail === "object") {
            const firstMsg = Object.entries(detail)
              .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(", ") : v}`)
              .join(" | ");
            if (firstMsg) this.notifyError(firstMsg);
          }
        });
    },
  },
  mounted() {
    this.getCoreSettings();
    this.getPolicies();
    this.getAlertTemplates();
  },
};
</script>
