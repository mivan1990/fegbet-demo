import { test, expect } from '@playwright/test'
import {
  adminToken,
  createBettableMatch,
  registerViaUi,
  saveTicket,
  settleMatch,
  uniqueEmail,
} from './helpers'

test('admin validează meci → userul vede ștampila și punctele', async ({ page, request }) => {
  const token = await adminToken(request)
  const match = await createBettableMatch(request, token)

  await registerViaUi(page, { email: uniqueEmail('settle'), displayName: 'Câștig Testescu' })

  await page.goto(`/meci/${match.id}`)
  await page.getByRole('button', { name: /Da \+/ }).click() // BTTS: Da
  await saveTicket(page)
  await expect(page.getByText('Biletul e băgat. Baftă!')).toBeVisible()

  // Admin decontează 2–1 → ambele echipe au marcat → selecția e corectă.
  await settleMatch(request, token, match.id, { home_score: 2, away_score: 1 })

  await page.goto(`/meci/${match.id}`)
  await expect(page.getByText('Scor final')).toBeVisible()
  await expect(page.getByText(/2\s*[–-]\s*1/)).toBeVisible()

  // Ștampila CÂȘTIGAT + punctele acordate.
  await expect(page.getByTestId('stamp')).toContainText('CÂȘTIGAT')

  await page.goto('/biletele-mele')
  await expect(page.getByTestId('stamp')).toContainText('CÂȘTIGAT')
  await expect(page.getByText('+2p').first()).toBeVisible()
})
