import { defineConfig, devices } from '@playwright/test'

/**
 * PLAN_SONNET.md Faza 7: două proiecte — `desktop` (1440×900) și `mobile`
 * (iPhone 13, 390×844). Cele 3 fluxuri rulează pe ambele.
 *
 * webServer pornește backend-ul pe 8110 (DB de test separată, ștearsă la fiecare
 * pornire) și frontend-ul pe 5174, ca să nu se calce cu serverele de development.
 */
const BACKEND_PORT = 8110
const FRONTEND_PORT = 5174

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  timeout: 30_000,
  expect: { timeout: 7_000 },

  use: {
    baseURL: `http://localhost:${FRONTEND_PORT}`,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  projects: [
    {
      name: 'desktop',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } },
    },
    {
      name: 'mobile',
      use: { ...devices['iPhone 13'] },
    },
  ],

  webServer: [
    {
      command:
        'sh -c "rm -f fegbet-e2e.db fegbet-e2e.db-shm fegbet-e2e.db-wal && ' +
        `.venv/bin/python -m uvicorn main:app --port ${BACKEND_PORT} --log-config log_config.json"`,
      cwd: '../backend',
      port: BACKEND_PORT,
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
      env: {
        DATABASE_URL: 'sqlite:///./fegbet-e2e.db',
        JWT_SECRET: 'e2e-secret-cheie-suficient-de-lunga-0123456789abcd',
        ALLOWED_EMAIL_DOMAIN: '@mariusivan.ro',
        ADMIN_EMAILS: 'admin@mariusivan.ro',
        ADMIN_PASSWORD: 'admin12345',
        APP_NAME: 'FEG BET (e2e)',
        CORS_ORIGINS: '',
        RATE_LIMIT_ENABLED: 'false',
        // Doar aici — NICIODATĂ pe server (INSTALARE_SERVER.md). Înregistrează
        // POST /api/e2e/reset-groups, folosită de admin-groups-flow.spec.ts ca să
        // decupleze specurile de grupe de ordinea lor de rulare (vezi helpers.ts
        // `resetAllGroupsForTests`). Ruta însăși mai verifică o dată că
        // DATABASE_URL conține „e2e" — motiv suplimentar să nu redenumești fișierul.
        E2E_TEST_MODE: '1',
      },
    },
    {
      command: `npm run dev -- --port ${FRONTEND_PORT} --strictPort`,
      port: FRONTEND_PORT,
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
      env: { VITE_API_TARGET: `http://localhost:${BACKEND_PORT}` },
    },
  ],
})
