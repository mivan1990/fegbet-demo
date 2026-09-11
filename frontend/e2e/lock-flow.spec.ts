import { test, expect } from '@playwright/test'
import {
  adminToken,
  createBettableMatch,
  registerViaUi,
  rescheduleMatch,
  saveTicket,
  uniqueEmail,
} from './helpers'

test('biletul se blochează după startul meciului', async ({ page, request }) => {
  const token = await adminToken(request)
  const match = await createBettableMatch(request, token, { minutesFromNow: 180 })

  await registerViaUi(page, { email: uniqueEmail('lock'), displayName: 'Lock Testescu' })

  await page.goto(`/meci/${match.id}`)
  await page.getByRole('button', { name: /Da \+/ }).click()
  await saveTicket(page)
  await expect(page.getByText('Biletul e băgat. Baftă!')).toBeVisible()

  // Adminul mută ora în trecut → meciul „a început".
  await rescheduleMatch(request, token, match.id, new Date(Date.now() - 60_000))

  await page.goto(`/meci/${match.id}`)
  await expect(page.getByText('Meciul a început.')).toBeVisible()
  await expect(
    page.getByRole('button', { name: /BAG BILETUL|ACTUALIZEAZĂ BILETUL/ }),
  ).toHaveCount(0)
  // Selecția rămâne vizibilă, read-only.
  await expect(page.getByText('Ambele marchează: Da')).toBeVisible()
})
