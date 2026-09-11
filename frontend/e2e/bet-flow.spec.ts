import { test, expect } from '@playwright/test'
import { adminToken, createBettableMatch, registerViaUi, saveTicket, uniqueEmail } from './helpers'

test('register → pariere → editare bilet', async ({ page, request }) => {
  const token = await adminToken(request)
  const match = await createBettableMatch(request, token)

  await registerViaUi(page, { email: uniqueEmail('bet'), displayName: 'Betul Testescu' })

  await page.goto(`/meci/${match.id}`)

  // O selecție = un tap.
  await page.getByRole('button', { name: /Egal/ }).click()
  await saveTicket(page)
  await expect(page.getByText('Biletul e băgat. Baftă!')).toBeVisible()

  // Reîncărcare: selecția rămâne pre-bifată.
  await page.reload()
  await expect(page.getByRole('button', { name: /Egal/ })).toHaveAttribute('aria-pressed', 'true')

  // Adaugă o a doua selecție și salvează din nou.
  await page.getByRole('button', { name: /Da \+/ }).click()
  await saveTicket(page)
  await expect(page.getByText('Bilet actualizat', { exact: false })).toBeVisible()

  // Biletul are ambele selecții.
  await page.goto('/biletele-mele')
  await expect(page.getByText('Câștigător: Egal')).toBeVisible()
  await expect(page.getByText('Ambele marchează: Da')).toBeVisible()
})

test('al doilea tap pe același chip deselectează', async ({ page, request }) => {
  const token = await adminToken(request)
  const match = await createBettableMatch(request, token)
  await registerViaUi(page, { email: uniqueEmail('toggle') })

  await page.goto(`/meci/${match.id}`)
  const chip = page.getByRole('button', { name: /Egal/ })
  await chip.click()
  await expect(chip).toHaveAttribute('aria-pressed', 'true')
  await chip.click()
  await expect(chip).toHaveAttribute('aria-pressed', 'false')
})
