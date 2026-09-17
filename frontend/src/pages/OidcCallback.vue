<template>
  <q-layout view="hHh lpR fFf">
    <q-page-container>
      <q-page class="q-pa-md flex flex-center">
        <q-card style="width: 380px; max-width: 90vw">
          <q-card-section class="text-center">
            <q-spinner color="primary" size="2em" v-if="status === 'pending'" />
            <q-icon name="error" color="negative" size="2em" v-else />
            <div class="text-h6 q-mt-sm">{{ title }}</div>
            <div class="text-caption q-mt-xs" v-if="message">{{ message }}</div>
            <q-btn
              v-if="status === 'error'"
              class="q-mt-md"
              color="primary"
              :label="t('login.backToLogin')"
              to="/login"
            />
          </q-card-section>
        </q-card>
      </q-page>
    </q-page-container>
  </q-layout>
</template>

<script setup>
import { onMounted, ref, computed } from 'vue';
import { useRoute } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useQuasar } from 'quasar';
import { api } from 'boot/axios';

const { t } = useI18n();
const $q = useQuasar();
const route = useRoute();

const status = ref('pending'); // 'pending' | 'error'
const message = ref('');

const title = computed(() =>
  status.value === 'error' ? t('error.generic') : t('login.signingIn'),
);

onMounted(async () => {
  // Providers return the code/state/error as query parameters on the callback
  // URL. The router query is the canonical source; we also check the raw search
  // string as a fallback for unusual redirect patterns.
  const search = new URLSearchParams(window.location.search);
  const get = (k) => route.query[k] || search.get(k) || null;
  const code = get('code');
  const state = get('state');
  const error = get('error');
  const errorDescription = get('error_description');

  if (error) {
    status.value = 'error';
    message.value = errorDescription || error;
    return;
  }
  if (!code) {
    status.value = 'error';
    message.value = 'Missing authorization code';
    return;
  }

  const savedState = sessionStorage.getItem('oidc_state');
  if (state && savedState && state !== savedState) {
    status.value = 'error';
    message.value = 'Invalid OIDC state';
    return;
  }
  sessionStorage.removeItem('oidc_state');

  const redirectUri = `${window.location.origin}/oidc/callback`;
  try {
    await api.post('/auth/oidc/callback', { code, redirect_uri: redirectUri });
    // Force a full-page navigation so the freshly set auth cookie is used by
    // the next app boot. This avoids router/service-worker timing issues that
    // can cause a client-side replace('/') to land back on the login page.
    window.location.href = '/';
  } catch (e) {
    status.value = 'error';
    message.value = e?.response?.data?.detail || 'OIDC login failed';
  }
});
</script>
