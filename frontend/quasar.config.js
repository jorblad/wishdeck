/*
 * Quasar App Vite Configuration
 * See https://v2.quasar.dev/quasar-cli-vite/quasar-config-js
 */
const API_PROXY_TARGET = process.env.API_PROXY_TARGET || 'http://localhost:8000';
module.exports = function (ctx) {
  return {
      boot: ['pinia', 'i18n', 'axios', 'dark'],
    css: [],
    extras: ['material-icons'],
    framework: {
      config: {},
      plugins: ['Notify', 'Dialog', 'Loading', 'Dark'],
    },
    build: {
      target: { browser: ['es2022', 'firefox115', 'chrome115', 'safari13'] },
      vueRouterMode: 'history',
      publicPath: '/',
      // @quasar/app-vite v3 dropped the auto-aliases for src subfolders
      // (stores/components/pages/boot/layouts/router/assets). Re-add them so
      // the existing `import ... from 'stores/auth'`-style imports keep working.
      alias: {
        stores: ctx.appPaths.srcDir + '/stores',
        components: ctx.appPaths.srcDir + '/components',
        pages: ctx.appPaths.srcDir + '/pages',
        layouts: ctx.appPaths.srcDir + '/layouts',
        boot: ctx.appPaths.srcDir + '/boot',
        router: ctx.appPaths.srcDir + '/router',
        assets: ctx.appPaths.srcDir + '/assets',
        src: ctx.appPaths.srcDir,
      },
    },
    devServer: {
      port: 9000,
      open: false,
      proxy: {
        // In Docker the backend is reachable as `backend:8000`; on the host it is `localhost:8000`.
        // Override with API_PROXY_TARGET when running the dev server inside the container.
        '/api': {
          target: API_PROXY_TARGET,
          changeOrigin: true,
        },
        '/docs': {
          target: API_PROXY_TARGET,
          changeOrigin: true,
        },
        '/redoc': {
          target: API_PROXY_TARGET,
          changeOrigin: true,
        },
        '/openapi.json': {
          target: API_PROXY_TARGET,
          changeOrigin: true,
        },
      },
    },
    pwa: {
      workboxMode: 'GenerateSW',
      workboxOptions: {
        skipWaiting: true,
        clientsClaim: true,
        navigateFallback: 'index.html',
      },
      manifest: {
        name: 'WishDeck',
        short_name: 'WishDeck',
        description: 'Multi-tenant collaborative wishlists',
        display: 'standalone',
        orientation: 'portrait',
        background_color: '#ffffff',
        theme_color: '#1976d2',
      },
    },
  };
};
