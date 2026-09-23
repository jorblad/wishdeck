const routes = [
  {
    path: '/',
    component: () => import('layouts/MainLayout.vue'),
    children: [
      { path: '', name: 'home', component: () => import('pages/IndexPage.vue'), meta: { requiresAuth: true } },
      {
        path: 'settings',
        name: 'settings',
        component: () => import('pages/SettingsPage.vue'),
        meta: { requiresAuth: true, requiresAdmin: true },
      },
      {
        path: 'users',
        name: 'users',
        component: () => import('pages/UsersPage.vue'),
        meta: { requiresAuth: true, requiresAdmin: true },
      },
      {
        path: 'wishlists/:slug',
        name: 'public-wishlist',
        component: () => import('pages/WishlistPage.vue'),
      },
      {
        path: 'wishlists/owner/:id',
        name: 'owner-wishlist',
        component: () => import('pages/WishlistPage.vue'),
        meta: { requiresAuth: true },
      },
      {
        path: 'add',
        name: 'add-from-extension',
        component: () => import('pages/AddFromExtensionPage.vue'),
        meta: { requiresAuth: true },
      },
    ],
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('pages/LoginPage.vue'),
  },
  {
    path: '/oidc/callback',
    name: 'oidc-callback',
    component: () => import('pages/OidcCallback.vue'),
  },
  { path: '/:catchAll(.*)*', component: () => import('pages/ErrorNotFound.vue') },
];

export default routes;
