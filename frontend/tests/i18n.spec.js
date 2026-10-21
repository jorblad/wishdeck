import { describe, expect, it } from 'vitest';
import en from 'src/i18n/en';
import sv from 'src/i18n/sv';

describe('navigation and login translations', () => {
  const keys = (value, prefix = '') => Object.entries(value).flatMap(([key, entry]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    return entry && typeof entry === 'object' ? keys(entry, path) : [path];
  });

  it('keeps the English and Swedish catalogs in sync', () => {
    expect(keys(sv).sort()).toEqual(keys(en).sort());
  });

  it('provides translated drawer titles and SSO labels in both locales', () => {
    expect(en.menu.title).toBe('Menu');
    expect(sv.menu.title).toBe('Meny');
    expect(en.login.continueWith).toBe('Continue with {provider}');
    expect(sv.login.continueWith).toBe('Fortsätt med {provider}');
    expect(en.login.oidcStartFailed).toBeTruthy();
    expect(sv.login.oidcStartFailed).toBeTruthy();
    expect(sv.item.quantityLabel).toBe('Antal');
    expect(sv.index.filter.all).toBe('Alla');
  });
});
