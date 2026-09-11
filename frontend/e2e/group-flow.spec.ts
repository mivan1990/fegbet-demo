import { test, expect } from '@playwright/test'
import {
  adminToken,
  createGroupAdditive,
  createTeam,
  finalizeGroup,
  registerViaUi,
  rescheduleMatch,
  settleGroupWithClearRanking,
  uniqueEmail,
  uniqueGroupName,
  uniqueSuffix,
} from './helpers'

/**
 * Fiecare rulare a testului ăsta își creează propriile echipe, propria grupă
 * (nume unic) și propriul user (email unic) — complet independentă de orice altă
 * rulare, a ei însăși sau a altui spec de grupe, pe aceeași bază de test.
 *
 * Grupa se creează prin ruta ADITIVĂ `createGroupAdditive`
 * (`POST /api/admin/groups`, services/groups.py `create_group`), care nu șterge
 * nimic — spre deosebire de `generate_groups` (reset global, folosit de
 * `admin-groups-flow.spec.ts` pentru fluxul real de admin), asta nu se lovește de
 * refuzul global al lui `generate_groups` cât timp există undeva meciuri de grupă
 * validate sau pronosticuri plasate — exact ce lasă în urmă `admin-groups-flow.spec.ts`
 * și rulările anterioare ale acestui test pe aceeași bază SQLite. De-asta testul
 * trece indiferent de ordinea specurilor de grupe și de câte ori a mai rulat.
 */
test('înregistrare → pronostic pe grupă → admin validează → finalizează → userul vede ștampila și punctele', async ({
  page,
  request,
}) => {
  const token = await adminToken(request)

  const t1 = await createTeam(request, token, 'Grupa Flow Echipa1')
  const t2 = await createTeam(request, token, 'Grupa Flow Echipa2')
  const t3 = await createTeam(request, token, 'Grupa Flow Echipa3')
  const t4 = await createTeam(request, token, 'Grupa Flow Echipa4')
  const teamIds: [number, number, number, number] = [t1.id, t2.id, t3.id, t4.id]

  const group = await createGroupAdditive(request, token, uniqueGroupName(), teamIds)
  expect(group.matches).toHaveLength(6)
  expect(group.qualifiers_count).toBe(2)

  // Programează toate meciurile grupei în viitor, ca să accepte pronosticuri.
  const when = new Date(Date.now() + 180 * 60_000)
  for (const m of group.matches) {
    await rescheduleMatch(request, token, m.id, when)
  }

  const email = uniqueEmail('grupa')
  const displayName = `Grupa Testescu ${uniqueSuffix()}`
  await registerViaUi(page, { email, displayName, password: 'parolabuna1' })

  await page.goto('/grupe')
  // Mobil (`Grupe.tsx`: `md:hidden`, prag 768px) arată un singur card, ales din tab-uri —
  // trebuie apăsat tab-ul grupei noastre explicit. Verificăm viewport-ul, nu
  // `locator.count()`: cu mai multe grupe pe bază (A, B din admin-groups-flow.spec.ts +
  // altele), grupa asta aproape sigur NU e cea activă implicit (prima din listă), iar
  // `count()` nu așteaptă încărcarea listei — poate întoarce 0 din cauza unei curse cu
  // fetch-ul, sărind peste click chiar dacă butonul chiar există. `.click()` reîncearcă
  // singur până apare.
  const isMobile = (page.viewportSize()?.width ?? 1440) < 768
  if (isMobile) {
    await page.getByRole('button', { name: `Grupa ${group.name}` }).click()
  }
  await expect(page.getByRole('heading', { name: `Grupa ${group.name}` })).toBeVisible()

  // Votează exact 2 echipe (qualifiers_count implicit = 2): t1 și t2 vor ieși din
  // grupă (vezi `settleGroupWithClearRanking`: t1 neînvinsă, t2 pe doi).
  await page.getByRole('button', { name: t1.name }).click()
  await page.getByRole('button', { name: t2.name }).click()
  await page.getByRole('button', { name: 'Salvează pronosticul' }).click()
  await expect(page.getByText('Pronostic salvat. Baftă!')).toBeVisible()

  // Admin validează cele 6 meciuri, fără egaluri — t1 neînvins, t2 pe doi, fără
  // ambiguitate (clasament t1 9p, t2 6p, t3 3p, t4 0p).
  await settleGroupWithClearRanking(request, token, group, teamIds)

  // Finalizare automată.
  await finalizeGroup(request, token, group.id)

  await page.goto('/grupe')
  if (isMobile) {
    await page.getByRole('button', { name: `Grupa ${group.name}` }).click()
  }
  await expect(page.getByTestId('stamp').first()).toContainText('CÂȘTIGAT')
  await expect(page.getByText('+2p').first()).toBeAttached()

  // Punctele intră în clasamentul general (bilete + grupe, PLAN_GRUPE.md 5.6) — scopat
  // la rândul ACESTUI user (nume unic per rulare), ca alte rulări ale aceluiași test
  // pe aceeași bază să nu producă mai multe potriviri pentru același text.
  await page.goto('/clasament')
  const nameCell = page.getByText(displayName).first()
  const rowContainer = nameCell.locator('xpath=..')
  await expect(rowContainer).toContainText('din care 4 p. din grupe')
})
