import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { api } from 'boot/axios';

// Holds the public (non-sensitive) server settings, including the
// ENABLE_GIFT_EXCHANGE feature flag used to show/hide the module.
export const usePublicSettingsStore = defineStore('publicSettings', () => {
  const settings = ref({});
  const loaded = ref(false);

  async function load() {
    try {
      const { data } = await api.get('/settings/public');
      settings.value = data || {};
    } catch {
      settings.value = {};
    }
    loaded.value = true;
  }

  const featureGiftExchange = computed(
    () => String(settings.value?.ENABLE_GIFT_EXCHANGE) === 'true',
  );

  return { settings, loaded, load, featureGiftExchange };
});
