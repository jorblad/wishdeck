import { boot } from 'quasar/wrappers';
import axios from 'axios';

// Empty API_BASE means "same-origin" — the request goes through the dev (Vite)
// or production (nginx) proxy for /api, avoiding cross-origin credential issues.
const API_BASE = process.env.API_BASE || '';
const baseURL = API_BASE ? `${API_BASE}/api/v1` : '/api/v1';

const api = axios.create({
  baseURL,
  withCredentials: true, // send/receive HTTP-only JWT cookie
  headers: { 'Content-Type': 'application/json' },
});

export default boot(({ app }) => {
  app.config.globalProperties.$api = api;
});

export { api, API_BASE };
