import { route } from 'quasar/wrappers';
import { createRouter, createMemoryHistory, createWebHistory } from 'vue-router';
import { useAuthStore } from 'stores/auth';

import routes from './routes';

export default route(function () {
  const createHistory = import.meta.env.SSR ? createMemoryHistory : createWebHistory;

  const router = createRouter({
    scrollBehavior: () => ({ left: 0, top: 0 }),
    routes,
    history: createHistory(import.meta.env.BASE_URL),
  });

  router.beforeEach(async (to) => {
    const auth = useAuthStore();
    // If already authenticated and heading to login, skip it.
    if (to.name === 'login' && auth.isAuthenticated) {
      return { name: 'home' };
    }
    if (to.meta.requiresAuth && !auth.isAuthenticated) {
      if (!auth.user) {
        try {
          await auth.fetchMe();
        } catch {
          return { name: 'login' };
        }
      }
      if (!auth.isAuthenticated) {
        return { name: 'login', query: { redirect: to.fullPath } };
      }
    }
    if (to.meta.requiresAdmin && !auth.isAdmin) {
      return { name: 'home' };
    }
    return true;
  });

  return router;
});
