import { boot } from 'quasar/wrappers';
import { usePublicSettingsStore } from 'stores/publicSettings';

// Inject the Umami analytics script when configured via public settings
// (UMAMI_SRC + UMAMI_ID). Public settings are loaded by the publicSettings
// boot, which runs before this one, so the values are available here.
export default boot(() => {
  const store = usePublicSettingsStore();
  const src = store.settings?.UMAMI_SRC;
  const id = store.settings?.UMAMI_ID;
  if (src && id && !document.getElementById('umami-analytics')) {
    const s = document.createElement('script');
    s.async = true;
    s.src = src;
    s.setAttribute('data-website-id', id);
    s.id = 'umami-analytics';
    document.head.appendChild(s);
  }
});
