<template>
  <q-layout view="hHh Lpr lff">
    <q-header elevated class="bg-primary text-white">
      <q-toolbar>
        <q-toolbar-title>
          <router-link to="/" class="text-white" style="text-decoration: none; cursor: pointer">
            WishDeck
          </router-link>
        </q-toolbar-title>
        <q-btn
          flat
          round
          dense
          :icon="darkIcon"
          @click="cycleDark"
        >
          <q-tooltip>{{ $t('theme.toggle') }}</q-tooltip>
        </q-btn>
        <q-btn v-if="auth.isAuthenticated && auth.isAdmin" flat :label="$t('menu.users')" to="/users" />
        <q-btn v-if="auth.isAuthenticated&& auth.isAdmin" flat :label="$t('menu.settings')" to="/settings" />
        <q-btn v-if="auth.isAuthenticated" flat :label="$t('menu.logout')" @click="onLogout" />
        <q-btn v-else flat :label="$t('menu.login')" to="/login" />
      </q-toolbar>
    </q-header>

    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup>
import { computed } from 'vue';
import { Dark } from 'quasar';
import { useAuthStore } from 'stores/auth';
import { useRouter } from 'vue-router';
import { getDarkMode, setDarkMode } from 'boot/dark';

const auth = useAuthStore();
const router = useRouter();

const order = ['auto', 'light', 'dark'];
const darkIcon = computed(() => {
  const m = getDarkMode();
  if (m === 'light') return 'light_mode';
  if (m === 'dark') return 'dark_mode';
  return 'contrast';
});

function cycleDark() {
  const current = getDarkMode();
  const next = order[(order.indexOf(current) + 1) % order.length];
  setDarkMode(next);
}

async function onLogout() {
  await auth.logout();
  router.push('/login');
}
</script>
