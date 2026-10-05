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

  // Optional Umami session recordings: /recorder.js served from the same
  // Umami origin as the main script. Gated behind an admin toggle so it is
  // opt-in and privacy-friendly.
  const recordingEnabled = store.settings?.UMAMI_RECORDING_ENABLED;
  if (recordingEnabled && src && id && !document.getElementById('umami-recorder')) {
    const base = src
      .replace(/\/script\.js(\?.*)?$/i, '')
      .replace(/\/recorder\.js(\?.*)?$/i, '')
      .replace(/\/+$/, '');
    const recorderSrc = `${base}/recorder.js`;
    const r = document.createElement('script');
    r.defer = true;
    r.src = recorderSrc;
    r.setAttribute('data-website-id', id);
    r.id = 'umami-recorder';
    document.head.appendChild(r);
  }
});
