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
      <div class="text-h5">{{ t('settings.profileTitle') }}</div>
    </div>

    <q-card flat bordered class="q-mb-lg" style="max-width: 520px">
      <q-card-section>
        <div class="text-subtitle1 text-weight-medium q-mb-sm">
          {{ t('settings.profileTitle') }}
        </div>
        <div class="row q-col-gutter-md items-end">
          <div class="col-12 col-sm-8">
            <q-input
              v-model="profileName"
              :label="t('login.fullName')"
              dense
              outlined
              :disable="profileSaving"
            />
          </div>
          <div class="col-auto">
            <q-btn
              :label="t('settings.save')"
              color="primary"
              icon="save"
              :loading="profileSaving"
              :disable="!profileChanged"
              @click="saveProfile"
            />
          </div>
        </div>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup>
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { api } from 'boot/axios';
import { useAuthStore } from 'stores/auth';

const { t } = useI18n();
const $q = useQuasar();
const router = useRouter();
const auth = useAuthStore();

const profileName = ref(auth.user?.full_name || '');
const profileSaving = ref(false);
const profileChanged = computed(
  () => (profileName.value || '') !== (auth.user?.full_name || '')
);

async function saveProfile() {
  profileSaving.value = true;
  try {
    await api.put('/auth/me', { full_name: profileName.value || null });
    await auth.fetchMe();
    profileName.value = auth.user?.full_name || '';
    $q.notify({ type: 'positive', message: t('settings.profileSaved') });
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Error' });
  } finally {
    profileSaving.value = false;
  }
}

function goBack() {
  if (window.history.length > 1) router.back();
  else router.push('/');
}
</script>
