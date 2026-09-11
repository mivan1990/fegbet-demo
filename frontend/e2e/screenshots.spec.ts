import path from 'node:path'
import { test } from '@playwright/test'
import { adminToken, createBettableMatch, loginViaUi } from './helpers'

const SHOT_DIR = path.join('e2e', '__screenshots__')

/**
 * PLAN_SONNET.md Faza 7: screenshot-uri la 375px / 1440px pentru paginile-cheie.
 * Rulează pe ambele proiecte; fișierele poartă numele proiectului.
 */
test('screenshot-uri pagini-cheie', async ({ page, request }, testInfo) => {
  const token = await adminToken(request)
  const match = await createBettableMatch(request, token, { opponent: 'Contabilitate FC' })

  // Autentificat ca admin — vedem UI-ul real, nu stările „intră în cont".
  await loginViaUi(page, 'admin@mariusivan.ro', 'admin12345')

  const shot = async (name: string) => {
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(500)
    await page.screenshot({
      path: path.join(SHOT_DIR, `${testInfo.project.name}-${name}.png`),
      fullPage: true,
    })
  }

  await page.goto('/')
  await shot('home')
  await page.goto(`/meci/${match.id}`)
  await shot('meci')
  await page.goto('/grupe')
  await shot('grupe')
  await page.goto('/clasament')
  await shot('clasament')
  await page.goto('/bracket')
  await shot('bracket')
  await page.goto('/admin/meciuri')
  await shot('admin-meciuri')
  await page.goto('/admin/grupe')
  await shot('admin-grupe')
  await page.goto('/admin/loguri')
  await shot('admin-loguri')
})
