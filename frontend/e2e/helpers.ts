import { expect, type APIRequestContext, type Page } from '@playwright/test'

export const API = 'http://localhost:8110/api'

function authHeaders(token: string) {
  return { Authorization: `Bearer ${token}` }
}

let seq = 0
export function uniqueEmail(prefix = 'e2e'): string {
  seq += 1
  return `${prefix}-${Date.now()}-${seq}@mariusivan.ro`
}

/** Token unic (fără caractere speciale) — pentru nume afișate/grupe unice per rulare. */
export function uniqueSuffix(): string {
  seq += 1
  return `${Date.now()}${seq}`
}

export async function adminToken(request: APIRequestContext): Promise<string> {
  const r = await request.post(`${API}/auth/login`, {
    data: { email: 'admin@mariusivan.ro', password: 'admin12345' },
  })
  expect(r.ok(), await r.text()).toBeTruthy()
  return (await r.json()).access_token
}

export interface CreatedMatch {
  id: number
  home_team_id: number
  away_team_id: number
}

/** Creează un meci FEG-vs-advers programat în viitor și deschis la pariere. */
export async function createBettableMatch(
  request: APIRequestContext,
  token: string,
  { minutesFromNow = 180, opponent }: { minutesFromNow?: number; opponent?: string } = {},
): Promise<CreatedMatch> {
  const teams = await (await request.get(`${API}/teams`)).json()
  const feg = teams.find((t: { is_feg: boolean }) => t.is_feg)
  expect(feg, 'echipa FEG lipsește din seed').toBeTruthy()

  const suffix = opponent ? ` ${seq}` : ` ${Date.now().toString(36)}${seq}`
  const opp = await request.post(`${API}/admin/teams`, {
    headers: authHeaders(token),
    data: { name: `${opponent ?? 'Adversarii'}${suffix}` },
  })
  const oppTeam = await opp.json()

  const created = await request.post(`${API}/admin/matches`, {
    headers: authHeaders(token),
    data: {
      round_no: 1,
      bracket_position: (Date.now() % 100000) + seq,
      stage_label: 'Sferturi',
      home_team_id: feg.id,
      away_team_id: oppTeam.id,
    },
  })
  expect(created.ok(), await created.text()).toBeTruthy()
  const match = await created.json()

  const when = new Date(Date.now() + minutesFromNow * 60_000).toISOString()
  const sched = await request.put(`${API}/admin/matches/${match.id}/schedule`, {
    headers: authHeaders(token),
    data: { scheduled_at: when },
  })
  expect(sched.ok(), await sched.text()).toBeTruthy()

  return { id: match.id, home_team_id: feg.id, away_team_id: oppTeam.id }
}

export interface CreatedTeam {
  id: number
  name: string
}

/** Creează o echipă activă, ne-FEG, cu nume unic. */
export async function createTeam(
  request: APIRequestContext,
  token: string,
  namePrefix: string,
): Promise<CreatedTeam> {
  seq += 1
  const r = await request.post(`${API}/admin/teams`, {
    headers: authHeaders(token),
    data: { name: `${namePrefix} ${Date.now().toString(36)}${seq}` },
  })
  expect(r.ok(), await r.text()).toBeTruthy()
  return r.json()
}

export interface GeneratedGroup {
  id: number
  name: string
  qualifiers_count: number
  is_finalized: boolean
  is_locked: boolean
  teams: { id: number; name: string }[]
  standings: { team_id: number; team: { id: number; name: string }; rank: number; points: number }[]
  qualified: { id: number; name: string }[]
  matches: {
    id: number
    round_no: number
    is_settled: boolean
    home_team: { id: number }
    away_team: { id: number }
  }[]
}

/**
 * Nume de grupă unic (1-2 caractere — limita din `GroupSpecIn`/`Group.name`), ca
 * `createGroupAdditive` să nu se lovească de un nume deja folosit de o rulare
 * anterioară pe aceeași bază de test.
 */
export function uniqueGroupName(): string {
  seq += 1
  return `${Date.now().toString(36)}${seq}`.slice(-2).toUpperCase()
}

/**
 * Adaugă O SINGURĂ grupă nouă, fără să atingă vreo grupă existentă
 * (`POST /api/admin/groups`, services/groups.py `create_group`) — spre deosebire de
 * `POST /admin/groups/generate` (reset global, folosit o singură dată la începutul
 * turneului, vezi `admin-groups-flow.spec.ts`). Fiindcă e aditivă, nu se lovește de
 * refuzul global al lui `generate_groups` cât timp există undeva meciuri de grupă
 * validate sau pronosticuri plasate — de asta o folosesc specurile care au nevoie
 * de propria lor grupă fixture, indiferent de ordine sau de ce a lăsat în urmă alt
 * spec de grupe pe aceeași bază.
 */
export async function createGroupAdditive(
  request: APIRequestContext,
  token: string,
  name: string,
  teamIds: number[],
): Promise<GeneratedGroup> {
  const r = await request.post(`${API}/admin/groups`, {
    headers: authHeaders(token),
    data: { name, team_ids: teamIds },
  })
  expect(r.ok(), await r.text()).toBeTruthy()
  return r.json()
}

/**
 * Caută o grupă existentă după nume, printre grupele admin. Folosit de
 * `admin-groups-flow.spec.ts` ca să detecteze dacă propria ei grupă fixture ('A')
 * a mai fost generată într-o rulare anterioară pe aceeași bază de test (proiectul
 * mobil rulează aceleași specuri a doua oară, pe aceeași bază) — ca să nu încerce
 * s-o regenereze (`generate_groups` e un reset global, o singură dată per bază).
 */
export async function findGroupByName(
  request: APIRequestContext,
  token: string,
  name: string,
): Promise<GeneratedGroup | null> {
  const r = await request.get(`${API}/admin/groups`, { headers: authHeaders(token) })
  expect(r.ok(), await r.text()).toBeTruthy()
  const groups: GeneratedGroup[] = await r.json()
  return groups.find((g) => g.name === name) ?? null
}

/** Toate grupele admin (nefiltrate) — folosit pentru verificarea „toate finalizate?". */
export async function listAdminGroups(
  request: APIRequestContext,
  token: string,
): Promise<GeneratedGroup[]> {
  const r = await request.get(`${API}/admin/groups`, { headers: authHeaders(token) })
  expect(r.ok(), await r.text()).toBeTruthy()
  return r.json()
}

/**
 * Șterge NECONDIȚIONAT tot domeniul grupelor din baza de test — `POST
 * /api/e2e/reset-groups` (routers/e2e.py), înregistrată în backend DOAR cu
 * `E2E_TEST_MODE=1` (vezi env-ul serverului backend din `playwright.config.ts`) și
 * refuzată dacă `DATABASE_URL` nu conține „e2e". NU există în afara suitei de test —
 * vezi backend/tests/test_e2e_route.py.
 *
 * Folosită STRICT de `admin-groups-flow.spec.ts`, chiar înainte de singurul ei apel
 * la fluxul real, distructiv, „Generează grupe" (`generate_groups`) — ca să-i
 * garanteze o bază curată indiferent ce a lăsat în urmă alt spec de grupe pe aceeași
 * bază SQLite (`generate_groups` refuză global dacă există undeva un meci de grupă
 * validat sau un pronostic plasat, indiferent cine l-a creat).
 */
export async function resetAllGroupsForTests(request: APIRequestContext, token: string): Promise<void> {
  const r = await request.post(`${API}/e2e/reset-groups`, { headers: authHeaders(token) })
  expect(r.ok(), await r.text()).toBeTruthy()
}

/**
 * Rezultate fără ambiguitate de departajare pentru un round-robin de 4 echipe:
 * t1 neînvinsă (9p), t2 a doua (6p), t3 a treia (3p), t4 ultima (0p) — același
 * tipar folosit în `test_group_finalize.py::_clear_win_scorelines`.
 */
function clearWinScoreline(
  homeId: number,
  awayId: number,
  [t1, t2, t3, t4]: [number, number, number, number],
): { home_score: number; away_score: number } {
  const table = new Map<string, [number, number]>([
    [`${t1}-${t4}`, [3, 0]],
    [`${t2}-${t3}`, [2, 0]],
    [`${t4}-${t3}`, [1, 2]], // t3 câștigă
    [`${t1}-${t2}`, [2, 1]], // t1 câștigă
    [`${t2}-${t4}`, [3, 1]], // t2 câștigă
    [`${t3}-${t1}`, [0, 1]], // t1 câștigă
  ])
  const [home_score, away_score] = table.get(`${homeId}-${awayId}`)!
  return { home_score, away_score }
}

/** Validează cele 6 meciuri ale unei grupe cu rezultate clare (fără egalitate la depart.). */
export async function settleGroupWithClearRanking(
  request: APIRequestContext,
  token: string,
  group: GeneratedGroup,
  teamIds: [number, number, number, number],
): Promise<void> {
  for (const m of group.matches) {
    const score = clearWinScoreline(m.home_team.id, m.away_team.id, teamIds)
    await settleMatch(request, token, m.id, score)
  }
}

export async function finalizeGroup(
  request: APIRequestContext,
  token: string,
  groupId: number,
  teamIds?: number[],
): Promise<void> {
  const r = await request.post(`${API}/admin/groups/${groupId}/finalize`, {
    headers: authHeaders(token),
    data: teamIds ? { team_ids: teamIds } : {},
  })
  expect(r.ok(), await r.text()).toBeTruthy()
}

export async function rescheduleMatch(
  request: APIRequestContext,
  token: string,
  matchId: number,
  when: Date,
): Promise<void> {
  const r = await request.put(`${API}/admin/matches/${matchId}/schedule`, {
    headers: authHeaders(token),
    data: { scheduled_at: when.toISOString() },
  })
  expect(r.ok(), await r.text()).toBeTruthy()
}

export async function settleMatch(
  request: APIRequestContext,
  token: string,
  matchId: number,
  body: { home_score: number; away_score: number },
): Promise<void> {
  const r = await request.post(`${API}/admin/matches/${matchId}/settle`, {
    headers: authHeaders(token),
    data: body,
  })
  expect(r.ok(), await r.text()).toBeTruthy()
}

async function submitAuthForm(
  page: Page,
  fields: { email: string; displayName?: string; password: string },
  buttonName: string,
): Promise<void> {
  // pressSequentially (taste reale) — `.fill()` nu propagă mereu în starea React
  // înainte de submit, iar validarea zod respinge un câmp „gol".
  const emailBox = page.getByLabel('Email')
  await emailBox.click()
  await emailBox.pressSequentially(fields.email, { delay: 15 })
  if (fields.displayName) {
    await page.getByLabel('Nume afișat').click()
    await page.getByLabel('Nume afișat').pressSequentially(fields.displayName, { delay: 15 })
  }
  const pwBox = page.getByLabel('Parolă')
  await pwBox.click()
  await pwBox.pressSequentially(fields.password, { delay: 15 })

  await expect(emailBox).toHaveValue(fields.email)
  await expect(pwBox).toHaveValue(fields.password)

  // Submit prin Enter din câmpul de parolă — mai fiabil decât click pe buton
  // când validarea zod rulează pe blur.
  await pwBox.press('Enter')
  await page.waitForURL(/\/$/, { timeout: 10_000 }).catch(async () => {
    // fallback: click explicit pe buton
    await page.getByRole('button', { name: buttonName }).click()
    await page.waitForURL(/\/$/, { timeout: 10_000 })
  })
}

/** Înregistrare prin UI. Rămâne autentificat după. */
export async function registerViaUi(
  page: Page,
  { email, displayName, password = 'parolabuna1' }: { email: string; displayName?: string; password?: string },
): Promise<void> {
  await page.goto('/inregistrare')
  await submitAuthForm(page, { email, displayName, password }, 'Îmi fac cont')
}

export async function loginViaUi(
  page: Page,
  email: string,
  password = 'parolabuna1',
): Promise<void> {
  await page.goto('/login')
  await submitAuthForm(page, { email, password }, 'Intru')
}

const SAVE_RE = /BAG BILETUL|ACTUALIZEAZĂ BILETUL/

/** Salvează biletul curent — gestionează bara + bottom-sheet pe mobil. */
export async function saveTicket(page: Page): Promise<void> {
  const width = page.viewportSize()?.width ?? 1440
  if (width < 1024) {
    await page.getByRole('button', { name: 'Vezi biletul' }).click()
    const sheet = page.getByRole('dialog', { name: 'Biletul tău' })
    await sheet.getByRole('button', { name: SAVE_RE }).click()
  } else {
    await page.getByRole('button', { name: SAVE_RE }).click()
  }
}
