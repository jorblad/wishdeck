/**
 * Dark mode initialisation.
 *
 * Default behaviour follows the client's operating-system / browser preference
 * via Quasar's "auto" mode. An explicit choice made with the header toggle is
 * persisted in localStorage and restored on the next visit.
 */
import { Dark } from 'quasar';

const STORAGE_KEY = 'wishdeck.dark';

export default function initDarkMode() {
  const saved = localStorage.getItem(STORAGE_KEY);
  // 'auto' (or no saved value) honours prefers-color-scheme.
  if (saved === 'dark') {
    Dark.set(true);
  } else if (saved === 'light') {
    Dark.set(false);
  } else {
    Dark.set('auto');
  }
}

export function getDarkMode() {
  return localStorage.getItem(STORAGE_KEY) || 'auto';
}

export function setDarkMode(mode) {
  // mode: 'auto' | 'light' | 'dark'
  localStorage.setItem(STORAGE_KEY, mode);
  if (mode === 'auto') Dark.set('auto');
  else Dark.set(mode === 'dark');
}
