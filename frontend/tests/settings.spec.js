import { describe, it, expect } from 'vitest';
import {
  collectChanges,
  groupNames,
  hasEnvOverrides,
  isLocked,
  isSecret,
  settingsByGroup,
} from 'src/utils/settings';

const sample = [
  { key: 'ALLOW_PUBLIC_CLAIMS', group: 'features', is_env_overridden: true, editable: true, value: true },
  { key: 'DEFAULT_VISIBILITY', group: 'features', is_env_overridden: false, editable: true, value: 'private' },
  { key: 'OIDC_ENABLED', group: 'auth', is_env_overridden: false, editable: true, value: false },
  { key: 'SECRET_KEY', group: 'general', is_env_overridden: false, editable: false, value: 'x' },
];

describe('settings util', () => {
  it('flags env-overridden settings as locked regardless of admin', () => {
    expect(isLocked(sample[0], true)).toBe(true);
    expect(isLocked(sample[0], false)).toBe(true);
  });

  it('locks non-editable keys and non-admins', () => {
    expect(isLocked(sample[3], true)).toBe(true); // non-editable
    expect(isLocked(sample[2], false)).toBe(true); // non-admin
    expect(isLocked(sample[2], true)).toBe(false); // editable + admin
  });

  it('groups and detects env overrides', () => {
    expect(groupNames(sample).sort()).toEqual(['auth', 'features', 'general']);
    expect(settingsByGroup(sample, 'features')).toHaveLength(2);
    expect(hasEnvOverrides(sample)).toBe(true);
    expect(hasEnvOverrides(sample.filter((s) => !s.is_env_overridden))).toBe(false);
  });

  it('collectChanges excludes env-overridden and unchanged keys', () => {
    const form = { ALLOW_PUBLIC_CLAIMS: true, DEFAULT_VISIBILITY: 'public', OIDC_ENABLED: false };
    const original = { ALLOW_PUBLIC_CLAIMS: true, DEFAULT_VISIBILITY: 'private', OIDC_ENABLED: false };
    const changes = collectChanges(sample, form, original);
    expect(changes).toEqual({ DEFAULT_VISIBILITY: 'public' }); // env + unchanged dropped
  });

  it('identifies secret keys', () => {
    expect(isSecret({ key: 'OIDC_CLIENT_SECRET' })).toBe(true);
    expect(isSecret({ key: 'DEFAULT_LOCALE' })).toBe(false);
  });
});
