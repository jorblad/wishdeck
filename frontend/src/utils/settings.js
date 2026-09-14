/**
 * Pure helpers for the Settings UI. Kept framework-free so they can be unit
 * tested with Vitest and reused by SettingsPage.vue.
 */

export const SECRET_KEYS = ['OIDC_CLIENT_SECRET', 'SECRET_KEY'];

export function isSecret(setting) {
  return SECRET_KEYS.includes(setting.key);
}

function humanize(key) {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function inferType(value) {
  if (typeof value === 'boolean') return 'bool';
  if (typeof value === 'number') return 'int';
  return 'text';
}

/**
 * Guard the UI against a backend that omits display metadata. Derives
 * `type`, `group`, `label` and `help` from the raw API row when missing so the
 * settings form always renders.
 */
export function normalizeSettings(list) {
  return (list || []).map((s) => ({
    ...s,
    type: s.type || inferType(s.value),
    group: s.group || 'general',
    label: s.label || humanize(s.key),
    help: s.help ?? null,
  }));
}

/**
 * A setting is locked (rendered disabled) when it is managed by an environment
 * variable, the user lacks admin rights, or the key is non-editable.
 */
export function isLocked(setting, isAdmin) {
  return setting.is_env_overridden || !isAdmin || !setting.editable;
}

export function groupNames(settings) {
  return [...new Set(settings.map((s) => s.group))];
}

export function settingsByGroup(settings, group) {
  return settings.filter((s) => s.group === group);
}

export function hasEnvOverrides(settings) {
  return settings.some((s) => s.is_env_overridden);
}

/**
 * Build the payload for PUT /settings: only editable, non-env-overridden keys
 * whose value actually changed.
 */
export function collectChanges(settings, form, original) {
  const values = {};
  for (const s of settings) {
    if (s.is_env_overridden || !s.editable) continue;
    if (form[s.key] !== original[s.key]) values[s.key] = form[s.key];
  }
  return values;
}
