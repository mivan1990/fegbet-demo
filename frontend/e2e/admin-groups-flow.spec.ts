import { test, expect } from '@playwright/test'
import {
  adminToken,
  createTeam,
  findGroupByName,
  listAdminGroups,
  loginViaUi,
  resetAllGroupsForTests,
  settleGroupWithClearRanking,
} from './helpers'

/**
 * Testul ăsta apasă efectiv, prin interfață, ca admin, fluxul real de generare de
 * grupe (`GroupGenerateModal` → `POST /admin/groups/generate`, reset global) +
 * `FinalizeGroupModal` + starea butonului „generează bracket din grupe" —
 * `group-flow.spec.ts` nu le atinge (își creează fixture-ul prin ruta ADITIVĂ
 * `POST /api/admin/groups`, care nu trece deloc prin `GroupGenerateModal`).
 *
 * `generate_groups` e un reset GLOBAL, o singură dată per bază: refuză să
 * (re)genereze dacă există undeva un meci de grupă validat sau un pronostic plasat —
 * indiferent cine l-a creat, pe orice grupă. Ca testul ăsta să treacă indiferent de
 * ordinea specurilor (alt spec de grupe poate fi rulat înaintea lui pe aceeași bază
 * SQLite de test), chemăm `resetAllGroupsForTests` chiar înainte de singurul apel
 * real la fluxul distructiv — ruta există DOAR în suita de test
 * (`E2E_TEST_MODE=1`, vezi `playwright.config.ts` și `backend/routers/e2e.py`).
 *
 * Idempotent pe aceeași bază: prima rulare resetează + generează + validează +
 * finalizează prin UI; rulările următoare (proiectul mobile) găsesc grupa A deja
 * finalizată și doar re-verifică starea (apăsând totuși „Re-finalizează", ca să
 * exercităm modalul și pe rulările ulterioare, nu doar pe prima — și fără reset, ca
 * să nu șteargă fixture-urile create între timp de alte specuri de grupe).
 */
const GROUP_A = 'A'
const GROUP_B = 'B'
const ADMIN_EMAIL = 'admin@mariusivan.ro'
const ADMIN_PASSWORD = 'admin12345'

test('admin: generează grupe din UI, validează meciurile, finalizează și verifică butonul de bracket', async ({
  page,
  request,
}) => {
  const token = await adminToken(request)
  await loginViaUi(page, ADMIN_EMAIL, ADMIN_PASSWORD)

  let groupA = await findGroupByName(request, token, GROUP_A)

  if (!groupA) {
    // ---- prima rulare pe această bază: bază curată garantată, apoi generează A + B prin UI ----
    await resetAllGroupsForTests(request, token)

    const a = [
      await createTeam(request, token, 'Admin Grupe A Echipa1'),
      await createTeam(request, token, 'Admin Grupe A Echipa2'),
      await createTeam(request, token, 'Admin Grupe A Echipa3'),
      await createTeam(request, token, 'Admin Grupe A Echipa4'),
    ]
    const b = [
      await createTeam(request, token, 'Admin Grupe B Echipa1'),
      await createTeam(request, token, 'Admin Grupe B Echipa2'),
      await createTeam(request, token, 'Admin Grupe B Echipa3'),
      await createTeam(request, token, 'Admin Grupe B Echipa4'),
    ]

    await page.goto('/admin/grupe')
    await page.getByRole('button', { name: 'Generează grupe' }).click()
    const genModal = page.getByRole('dialog', { name: 'Generează grupe' })
    await expect(genModal).toBeVisible()

    // Tab-ul activ implicit e 'A' — alegem cele 4 echipe direct.
    for (const t of a) {
      await genModal.getByRole('button', { name: t.name }).click()
    }
    // Trecem pe tab-ul 'B' și alegem echipele ei.
    await genModal.getByRole('button', { name: new RegExp(`^${GROUP_B} \\(`) }).click()
    for (const t of b) {
      await genModal.getByRole('button', { name: t.name }).click()
    }

    await genModal.getByRole('button', { name: /Generează \(2 grupe\)/ }).click()
    await expect(page.getByText('Grupe generate.')).toBeVisible()

    groupA = await findGroupByName(request, token, GROUP_A)
    expect(groupA, 'grupa A nu a apărut după generare — reset-ul de mai sus n-a garantat o bază curată').toBeTruthy()

    // Confirmă prin interfața publică (/grupe) că apar cele 6 meciuri ale grupei A.
    // Mobil (`Grupe.tsx`: `md:hidden`, prag 768px) arată un card, ales din tab-uri —
    // verificăm viewport-ul, nu `locator.count()` (care nu așteaptă fetch-ul listei de
    // grupe și poate întoarce 0 dintr-o cursă, sărind peste click chiar dacă butonul
    // există); `.click()` reîncearcă singur până apare.
    await page.goto('/grupe')
    const isMobile = (page.viewportSize()?.width ?? 1440) < 768
    if (isMobile) {
      await page.getByRole('button', { name: `Grupa ${GROUP_A}` }).click()
    }
    await expect(page.getByRole('heading', { name: `Grupa ${GROUP_A}`, exact: true })).toBeVisible()
    await expect(page.getByRole('article').filter({ hasText: `Grupa ${GROUP_A} ·` })).toHaveCount(6)

    // Validează cele 6 meciuri — aici folosim API-ul, nu e ce testăm în pasul ăsta.
    await settleGroupWithClearRanking(
      request,
      token,
      groupA!,
      a.map((t) => t.id) as [number, number, number, number],
    )
  }

  const targetName = groupA!.name

  // Stare proaspătă (poate s-a schimbat mai sus).
  groupA = (await findGroupByName(request, token, targetName))!

  await page.goto('/admin/grupe')
  const card = page
    .locator('section')
    .filter({ has: page.getByRole('heading', { name: `Grupa ${targetName}`, exact: true }) })
  await expect(card).toBeVisible()

  if (!groupA.is_finalized) {
    // Clasamentul afișat pe pagina de admin, înainte de finalizare.
    const ranked = [...groupA.standings].sort((x, y) => x.rank - y.rank)
    await expect(card.locator('tr', { hasText: ranked[0].team.name })).toContainText(
      String(ranked[0].points),
    )

    await card.getByRole('button', { name: 'Finalizează', exact: true }).click()
    const finalizeModal = page.getByRole('dialog', { name: `Finalizează grupa ${targetName}` })
    await expect(finalizeModal).toBeVisible()
    await expect(
      finalizeModal.getByText(`Se califică primele ${groupA.qualifiers_count} din clasament`),
    ).toBeVisible()
    await finalizeModal.getByRole('button', { name: 'Finalizează' }).click()
    await expect(page.getByText(`Grupa ${targetName} a fost finalizată.`)).toBeVisible()
  } else {
    // Rulare ulterioară: grupa e deja finalizată — re-finalizăm (PLAN_GRUPE.md 5.5
    // permite explicit re-finalizarea, fără să adune puncte peste cele vechi), ca să
    // exercităm modalul și pe rulările următoare, nu doar pe prima.
    await card.getByRole('button', { name: 'Re-finalizează' }).click()
    const finalizeModal = page.getByRole('dialog', { name: `Finalizează grupa ${targetName}` })
    await expect(finalizeModal).toBeVisible()
    await finalizeModal.getByRole('button', { name: 'Finalizează' }).click()
    await expect(page.getByText(`Grupa ${targetName} a fost finalizată.`)).toBeVisible()
  }

  await expect(card.getByText('Finalizată')).toBeVisible()
  const freshA = (await findGroupByName(request, token, targetName))!
  const qualifiedNames = freshA.qualified.map((t) => t.name)
  await expect(card.getByText(`Calificate: ${qualifiedNames.join(', ')}`)).toBeVisible()

  // ---- „generează bracket din grupe" — buton activ doar dacă TOATE grupele sunt
  // finalizate (AdminGroups.tsx: disabled={!allFinalized}). Grupa B rămâne mereu
  // deschisă (nimic n-o finalizează), deci în mod normal butonul e dezactivat — dar
  // verificăm starea reală în loc s-o presupunem, ca testul să rămână corect și dacă
  // se schimbă ce alte grupe există pe bază.
  const allGroups = await listAdminGroups(request, token)
  const allFinalized = allGroups.length > 0 && allGroups.every((g) => g.is_finalized)
  const bracketBtn = page.getByRole('button', { name: 'Generează bracket din grupe' })
  await expect(bracketBtn).toBeVisible()
  if (allFinalized) {
    await expect(bracketBtn).toBeEnabled()
  } else {
    await expect(bracketBtn).toBeDisabled()
  }
})
