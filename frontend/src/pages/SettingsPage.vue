<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <q-btn
        flat
        round
        dense
        icon="arrow_back"
        :aria-label="t('back')"
        @click="goBack"
      />
      <div class="text-h5">{{ t('settings.title') }}</div>
      <q-space />
      <q-btn
        :label="t('settings.save')"
        color="primary"
        icon="save"
        :loading="saving"
        :disable="!hasChanges || !isAdmin"
        @click="save"
      />
    </div>

    <div v-if="loading" class="text-center q-pa-xl"><q-spinner size="40px" /></div>

    <q-banner
      v-else-if="loadError"
      class="bg-red-1 text-negative q-mb-md rounded-borders"
    >
      {{ t('settings.loadError', { error: loadError }) }}
    </q-banner>

    <template v-else>
    <q-banner v-if="!isAdmin" class="bg-amber-1 text-amber-10 q-mb-md rounded-borders">
      {{ t('settings.readOnlyHint') }}
    </q-banner>

    <q-banner v-if="!anyEnvOverrides" class="bg-blue-1 text-blue-10 q-mb-md rounded-borders">
      {{ t('settings.noEnvOverrides') }}
    </q-banner>

    <!-- Grouped settings -->
    <div v-for="group in groups" :key="group" class="q-mb-lg">
      <div class="text-subtitle1 text-weight-medium text-capitalize q-mb-sm">
        {{ t(`settings.groups.${group}`) }}
      </div>

      <q-card flat bordered>
        <q-list separator>
          <q-item v-for="s in settingsByGroup(settings, group)" :key="s.key">
            <q-item-section>
              <div class="row items-center q-gutter-xs">
                <span class="text-body2 text-weight-medium">{{ t('settings.labels.' + s.key, s.label) }}</span>
                <q-badge
                  v-if="s.is_env_overridden"
                  color="deep-purple"
                  label="ENV"
                  class="cursor-pointer"
                >
                  <q-tooltip>{{ t('settings.managedViaEnv') }}</q-tooltip>
                </q-badge>
              </div>
              <div v-if="s.help" class="text-caption text-grey-7">{{ t('settings.help.' + s.key, s.help) }}</div>
            </q-item-section>

            <q-item-section side style="min-width: 280px">
              <!-- Boolean -->
              <q-toggle
                v-if="s.type === 'bool'"
                v-model="form[s.key]"
                :disable="isLocked(s, isAdmin)"
                :color="s.is_env_overridden ? 'grey-6' : 'primary'"
                :label="form[s.key] ? t('common.on') : t('common.off')"
              />
              <!-- Integer -->
              <q-input
                v-else-if="s.type === 'int'"
                v-model.number="form[s.key]"
                type="number"
                dense
                outlined
                :disable="isLocked(s, isAdmin)"
                :class="{ 'env-locked': s.is_env_overridden }"
              />
              <!-- Select (visibility / locale) -->
              <q-select
                v-else-if="s.key === 'DEFAULT_VISIBILITY'"
                v-model="form[s.key]"
                :options="visibilityOptions"
                dense
                outlined
                emit-value
                map-options
                :disable="isLocked(s, isAdmin)"
                :class="{ 'env-locked': s.is_env_overridden }"
              />
              <q-select
                v-else-if="s.key === 'DEFAULT_LOCALE'"
                v-model="form[s.key]"
                :options="localeOptions"
                dense
                outlined
                emit-value
                map-options
                :disable="isLocked(s, isAdmin)"
                :class="{ 'env-locked': s.is_env_overridden }"
              />
              <!-- Secret text -->
              <q-input
                v-else-if="isSecret(s)"
                v-model="form[s.key]"
                type="password"
                dense
                outlined
                :disable="isLocked(s, isAdmin)"
                :class="{ 'env-locked': s.is_env_overridden }"
              />
              <!-- Plain text -->
              <q-input
                v-else
                v-model="form[s.key]"
                dense
                outlined
                :disable="isLocked(s, isAdmin)"
                :class="{ 'env-locked': s.is_env_overridden }"
              />
            </q-item-section>
          </q-item>
        </q-list>
      </q-card>
    </div>
    </template>
  </q-page>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { api } from 'boot/axios';
import { useAuthStore } from 'stores/auth';
import {
  collectChanges,
  groupNames,
  hasEnvOverrides,
  isLocked,
  isSecret,
  normalizeSettings,
  settingsByGroup,
} from 'src/utils/settings';

const { t } = useI18n();
const $q = useQuasar();
const router = useRouter();
const auth = useAuthStore();

const settings = ref([]);
const form = reactive({});
const saving = ref(false);
const loading = ref(false);
const loadError = ref('');
const original = ref({});

const isAdmin = computed(() => auth.isAdmin);

const groups = computed(() => groupNames(settings.value));
const hasChanges = computed(() =>
  Object.keys(collectChanges(settings.value, form, original.value)).length > 0
);
const anyEnvOverrides = computed(() => hasEnvOverrides(settings.value));

const visibilityOptions = [
  { label: 'Private', value: 'private' },
  { label: 'Unlisted', value: 'unlisted' },
  { label: 'Public', value: 'public' },
];
const localeOptions = [
  { label: 'English', value: 'en' },
  { label: 'Svenska', value: 'sv' },
];

function goBack() {
  if (window.history.length > 1) router.back();
  else router.push('/');
}

async function load() {
  loading.value = true;
  loadError.value = '';
  try {
    const { data } = await api.get('/settings');
    settings.value = normalizeSettings(data.settings);
    for (const s of settings.value) {
      form[s.key] = s.value;
      original.value[s.key] = s.value;
    }
  } catch (e) {
    loadError.value = e.response?.data?.detail || e.message || 'request failed';
  } finally {
    loading.value = false;
  }
}

async function save() {
  saving.value = true;
  try {
    const values = collectChanges(settings.value, form, original.value);
    if (!Object.keys(values).length) {
      saving.value = false;
      return;
    }
    const { data } = await api.put('/settings', { values });
    settings.value = data.settings;
    for (const s of settings.value) {
      form[s.key] = s.value;
      original.value[s.key] = s.value;
    }
    $q.notify({ type: 'positive', message: t('settings.saved') });
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Error' });
  } finally {
    saving.value = false;
  }
}

onMounted(load);
</script>

<style scoped>
.env-locked :deep(.q-field__control) {
  background: #f0f0f0;
  color: #9e9e9e;
}
</style>
