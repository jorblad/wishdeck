import { boot } from 'quasar/wrappers';
import { createI18n } from 'vue-i18n';
import { watch } from 'vue';
import { Quasar } from 'quasar';

import en from 'src/i18n/en';
import sv from 'src/i18n/sv';
import langEn from 'quasar/lang/en-US';
import langSv from 'quasar/lang/sv';
import { api } from 'boot/axios';

function applyQuasarLang(locale) {
  Quasar.lang.set(locale === 'sv' ? langSv : langEn);
}

/**
 * Default locale priority:
 *   1. explicit user choice stored in localStorage (highest)
 *   2. server DEFAULT_LOCALE (which itself resolves ENV > UI/DB > built-in)
 *   3. built-in fallback 'en'
 * The server value is fetched from the public config endpoint on boot.
 */
const STORAGE_KEY = 'wishdeck.locale';

function storedLocale() {
  return localStorage.getItem(STORAGE_KEY);
}

export const i18n = createI18n({
  legacy: false,
  locale: storedLocale() || 'en',
  fallbackLocale: 'en',
  messages: { en, sv },
});

export default boot(async ({ app }) => {
  app.use(i18n);

  applyQuasarLang(i18n.global.locale.value);
  watch(
    () => i18n.global.locale.value,
    (locale) => applyQuasarLang(locale),
  );

  const stored = storedLocale();
  if (stored) return; // user override always wins

  try {
    const { data } = await api.get('/settings/public');
    const serverLocale = data?.DEFAULT_LOCALE;
    if (serverLocale) {
      i18n.global.locale.value = serverLocale;
    }
  } catch {
    // Backend unavailable / not ready — keep the built-in fallback.
  }
});
