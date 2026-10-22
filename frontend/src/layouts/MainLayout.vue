<template>
  <q-layout view="hHh Lpr lff">
    <q-header elevated class="bg-primary text-white">
      <q-toolbar>
        <q-btn
          v-if="$q.screen.lt.md"
          flat
          dense
          round
          icon="menu"
          :aria-label="$t('menu.title')"
          @click="drawer = !drawer"
        />
        <q-toolbar-title>
          <router-link to="/" class="text-white" style="text-decoration: none; cursor: pointer">
            WishDeck
          </router-link>
        </q-toolbar-title>
        <template v-if="$q.screen.gt.sm">
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
          <q-btn v-if="auth.isAuthenticated" flat :label="$t('menu.profile')" to="/profile" />
          <q-btn
            v-if="auth.isAuthenticated && publicSettings.featureGiftExchange"
            flat
            :label="$t('giftExchange.title')"
            to="/gift-exchange"
          />
          <q-btn v-if="auth.isAuthenticated&& auth.isAdmin" flat :label="$t('menu.settings')" to="/settings" />
          <q-btn v-if="auth.isAuthenticated" flat :label="$t('menu.logout')" @click="onLogout" />
          <q-btn v-else flat :label="$t('menu.login')" to="/login" />
        </template>
      </q-toolbar>
    </q-header>

    <q-drawer
      v-model="drawer"
      side="left"
      bordered
      :breakpoint="0"
      class="bg-primary text-white"
    >
      <q-list>
        <q-item-label header class="text-white">{{ $t('menu.title') }}</q-item-label>

        <q-item clickable to="/" @click="drawer = false">
          <q-item-section avatar><q-icon name="home" /></q-item-section>
          <q-item-section>{{ $t('menu.overview') }}</q-item-section>
        </q-item>
        <q-item v-if="auth.isAuthenticated && auth.isAdmin" clickable to="/users" @click="drawer = false">
          <q-item-section avatar><q-icon name="people" /></q-item-section>
          <q-item-section>{{ $t('menu.users') }}</q-item-section>
        </q-item>
        <q-item v-if="auth.isAuthenticated" clickable to="/profile" @click="drawer = false">
          <q-item-section avatar><q-icon name="person" /></q-item-section>
          <q-item-section>{{ $t('menu.profile') }}</q-item-section>
        </q-item>
        <q-item
          v-if="auth.isAuthenticated && publicSettings.featureGiftExchange"
          clickable
          to="/gift-exchange"
          @click="drawer = false"
        >
          <q-item-section avatar><q-icon name="card_giftcard" /></q-item-section>
          <q-item-section>{{ $t('giftExchange.title') }}</q-item-section>
        </q-item>
        <q-item v-if="auth.isAuthenticated && auth.isAdmin" clickable to="/settings" @click="drawer = false">
          <q-item-section avatar><q-icon name="settings" /></q-item-section>
          <q-item-section>{{ $t('menu.settings') }}</q-item-section>
        </q-item>
        <q-item v-if="auth.isAuthenticated" clickable @click="onLogout">
          <q-item-section avatar><q-icon name="logout" /></q-item-section>
          <q-item-section>{{ $t('menu.logout') }}</q-item-section>
        </q-item>
        <q-item v-else clickable to="/login" @click="drawer = false">
          <q-item-section avatar><q-icon name="login" /></q-item-section>
          <q-item-section>{{ $t('menu.login') }}</q-item-section>
        </q-item>

        <q-separator dark class="q-my-sm" />

        <q-item clickable v-close-popup @click="cycleDark">
          <q-item-section avatar><q-icon :name="darkIcon" /></q-item-section>
          <q-item-section>{{ $t('theme.toggle') }}</q-item-section>
        </q-item>
      </q-list>
    </q-drawer>

    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup>
import { computed, ref } from 'vue';
import { useQuasar } from 'quasar';
import { useAuthStore } from 'stores/auth';
import { usePublicSettingsStore } from 'stores/publicSettings';
import { useRouter } from 'vue-router';
import { getDarkMode, setDarkMode } from 'boot/dark';

const $q = useQuasar();
const auth = useAuthStore();
const publicSettings = usePublicSettingsStore();
const router = useRouter();
const drawer = ref(false);

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
  drawer.value = false;
  await auth.logout();
  router.push('/login');
}
</script>

<!--
  Quasar colors an active q-item with `var(--q-primary)`. Since the drawer
  itself uses `bg-primary`, the active item's text/icon would become the same
  color as the background and render invisible. Force the active item to stay
  white (readable on the primary band in both light and dark themes) and give
  it a subtle highlight so the current page is easy to spot.
-->
<style scoped>
.q-drawer .q-item.q-router-link--active,
.q-drawer .q-item.q-item--active {
  color: #fff;
  background: rgba(255, 255, 255, 0.12);
}
</style>
