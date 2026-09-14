<template>
  <q-layout view="hHh lpR fFf">
    <q-page-container>
      <q-page class="q-pa-md flex flex-center">
        <q-card style="width: 380px; max-width: 90vw">
          <q-card-section>
            <div class="text-h6">Sign in</div>
          </q-card-section>

          <q-card-section>
            <q-form @submit.prevent="mode === 'login' ? localLogin() : localRegister()">
              <q-input v-model="email" label="Email" type="email" autofocus />
              <q-input v-if="mode === 'register'" v-model="fullName" label="Full name" class="q-mt-sm" />
              <q-input
                v-if="mode === 'register'"
                v-model="username"
                label="Username (optional)"
                class="q-mt-sm"
              />
              <q-input v-model="password" label="Password" type="password" class="q-mt-sm" />
              <q-btn
                type="submit"
                color="primary"
                class="full-width q-mt-md"
                :label="mode === 'login' ? 'Login' : 'Create account'"
                :loading="loading"
              />
            </q-form>

            <div class="text-center q-mt-sm">
              <q-btn
                flat
                dense
                :label="mode === 'login' ? 'Create an account' : 'Have an account? Sign in'"
                @click="mode = mode === 'login' ? 'register' : 'login'"
              />
            </div>

            <template v-if="oidc.enabled">
              <q-separator class="q-my-md" />
              <q-btn
                outline
                color="secondary"
                class="full-width"
                :label="`Continue with ${oidc.name || 'SSO'}`"
                @click="startOidc"
              />
            </template>
          </q-card-section>
        </q-card>
      </q-page>
    </q-page-container>
  </q-layout>
</template>

<script setup>
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { api } from 'boot/axios';
import { useAuthStore } from 'stores/auth';

const router = useRouter();
const auth = useAuthStore();
const mode = ref('login');
const email = ref('');
const password = ref('');
const fullName = ref('');
const username = ref('');
const loading = ref(false);
const oidc = ref({ enabled: false, name: '', issuer_url: '' });

onMounted(async () => {
  try {
    const { data } = await api.get('/auth/oidc/config');
    oidc.value = data;
  } catch {
    oidc.value = { enabled: false, name: '', issuer_url: '' };
  }
});

async function afterAuth() {
  await auth.fetchMe();
  router.push('/');
}

async function localLogin() {
  loading.value = true;
  try {
    await api.post('/auth/login', { username: email.value, password: password.value });
    await afterAuth();
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
}

async function localRegister() {
  loading.value = true;
  try {
    await api.post('/auth/register', {
      email: email.value,
      password: password.value,
      full_name: fullName.value || null,
      username: username.value || null,
    });
    await localLogin(); // first user is promoted to admin automatically
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
}

function startOidc() {
  const issuer = oidc.value.issuer_url;
  const redirect = `${window.location.origin}/#/oidc/callback`;
  window.location.href =
    `${issuer}/protocol/openid-connect/auth?response_type=code&client_id=wishdeck` +
    `&redirect_uri=${encodeURIComponent(redirect)}&scope=openid%20email%20profile`;
}
</script>
