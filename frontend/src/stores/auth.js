import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { api } from 'boot/axios';

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null);
  const isAdmin = computed(() => user.value?.role === 'admin');
  const isAuthenticated = computed(() => !!user.value);

  async function fetchMe() {
    try {
      const { data } = await api.get('/auth/me');
      user.value = data;
    } catch {
      user.value = null;
    }
    return user.value;
  }

  function logout() {
    return api.post('/auth/logout').finally(() => {
      user.value = null;
    });
  }

  return { user, isAdmin, isAuthenticated, fetchMe, logout };
});
