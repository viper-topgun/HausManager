import { writable } from 'svelte/store';
import { browser } from '$app/environment';

/** JWT string or null */
export const authToken = writable(browser ? localStorage.getItem('hm_token') : null);

/** { username, role, display_name } or null */
export const currentUser = writable(null);

// Keep localStorage in sync with the store
authToken.subscribe((token) => {
  if (!browser) return;
  if (token) {
    localStorage.setItem('hm_token', token);
  } else {
    localStorage.removeItem('hm_token');
    currentUser.set(null);
  }
});

export function logout() {
  authToken.set(null);
  currentUser.set(null);
}
