import { boot } from 'quasar/wrappers';
import { usePublicSettingsStore } from 'stores/publicSettings';

// Fetch public settings (incl. feature flags) once at startup so the UI can
// show/hide opt-in modules like Gift Exchange.
export default boot(async () => {
  const store = usePublicSettingsStore();
  await store.load();
});
