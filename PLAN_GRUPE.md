# Faza 9 — Grupe (A/B/C/D) + pronostic „cine merge mai departe" la nivel de grupă

Extinde `PLAN_SONNET.md`. Unde cele două se contrazic, **acest document are prioritate**
pentru tot ce ține de grupe; restul rămâne neschimbat.

## 1. Ce se schimbă, pe scurt

Turneul devine **grupe + knockout**:

- **16 echipe → 4 grupe (A, B, C, D) × 4 echipe**, fiecare grupă în sistem
  **fiecare-cu-fiecare** (6 meciuri/grupă, **24 de meciuri de grupă** în total).
- Din fiecare grupă se califică **primele 2** → **8 echipe** → bracket-ul existent
  (sferturi → semifinale → finală). Numărul de calificate e **configurabil per grupă**
  (`Group.qualifiers_count`, default 2) — organizatorul a spus explicit că s-ar putea
  schimba.
- Piața **`QUALIFY` („Cine merge mai departe") dispare de pe meciurile de grupă.**
  În locul ei apare un **pronostic la nivel de grupă**: userul votează *ce echipe ies
  din grupă*. Citat de la organizator: „Cine merge mai departe: asta aș vrea să îl facem
  la nivel de grupe, să voteze ce echipe merg mai departe".
- Meciurile de grupă **pot fi egale fără penalty-uri** (azi decontarea le refuză).
- Calificarea în bracket se face **automat** din clasamentul grupei, **cu suprascriere
  manuală de admin** când departajarea e ambiguă.

## 2. Ce NU se schimbă

- Piața `QUALIFY` rămâne exact cum e pe meciurile din **bracket**.
- Piața `SCORER` rămâne doar la meciurile FEG — **inclusiv la meciurile de grupă ale FEG**.
- `WINNER` (cu `DRAW`), `TOTAL_GOALS`, `BTTS` rămân disponibile pe toate meciurile.
- Un bilet e tot per meci, cu maxim o selecție per piață.
- Motorul de punctaj rămâne pur (`services/scoring.py`, fără DB).
- Tot textul vizibil e în română, cu diacritice.

---

## 3. Model de date

### 3.1 Tabel nou: `groups`

| Coloană | Tip | Note |
|---|---|---|
| `id` | int PK | |
| `name` | String(2), unique | „A", „B", „C", „D" |
| `sort_order` | int, not null | 1..4, pentru afișare |
| `qualifiers_count` | int, not null, default 2 | câte echipe ies din grupă |
| `created_at` / `updated_at` | UtcDateTime | via `TimestampMixin` |

### 3.2 Tabel nou: `group_qualifiers`

Sursa de adevăr pentru „cine a ieșit din grupă". Se scrie la **finalizarea grupei**
(automat sau cu suprascriere de admin). Nu se recalculează la fiecare citire — ca
decontarea să fie deterministă și auditabilă.

| Coloană | Tip | Note |
|---|---|---|
| `id` | int PK | |
| `group_id` | FK groups.id, index | |
| `team_id` | FK teams.id | |
| `rank` | int | 1..`qualifiers_count` (1 = câștigătoarea grupei) |
| `created_at` | UtcDateTime | |

Constrângeri: `unique(group_id, rank)`, `unique(group_id, team_id)`.

### 3.3 Tabele noi: `group_predictions` + `group_prediction_picks`

Pronosticul „ce echipe ies din grupa X". **Ordinea nu contează** — userul votează un
*set* de echipe, nu locul 1 și locul 2.

`group_predictions`:

| Coloană | Tip | Note |
|---|---|---|
| `id` | int PK | |
| `user_id` | FK users.id, index | |
| `group_id` | FK groups.id, index | |
| `status` | String(8), default „OPEN" | OPEN / SETTLED / VOID |
| `total_points` | int, nullable | |
| `created_at` / `updated_at` | UtcDateTime | |

Constrângere: `unique(user_id, group_id)` (`uq_group_prediction_user_group`).

`group_prediction_picks`:

| Coloană | Tip | Note |
|---|---|---|
| `id` | int PK | |
| `prediction_id` | FK group_predictions.id **ondelete CASCADE**, index | |
| `team_id` | FK teams.id | |
| `is_correct` | bool, nullable | |
| `points_awarded` | int, nullable | |
| `created_at` | UtcDateTime | |

Constrângere: `unique(prediction_id, team_id)`.

### 3.4 Coloane noi pe tabele existente

> ⚠️ **Migrarea** (`database._migrate`) face `ALTER TABLE ADD COLUMN` pe tabelele
> existente. SQLite **refuză** o coloană `NOT NULL` fără default. Deci orice coloană
> nouă pe un tabel existent e ori `nullable=True`, ori are `server_default`.

- `teams.group_id` → `ForeignKey("groups.id")`, **nullable**, index.
- `matches.phase` → `String(10)`, `nullable=False`, **`server_default="KNOCKOUT"`**,
  index. Valori: `"GROUP"` / `"KNOCKOUT"`. Meciurile existente devin automat
  `KNOCKOUT` → comportamentul actual rămâne identic.
- `matches.group_id` → `ForeignKey("groups.id")`, **nullable**, index.

### 3.5 Semantica câmpurilor `Match` pentru meciurile de grupă

| Câmp | Valoare la un meci de grupă |
|---|---|
| `phase` | `"GROUP"` |
| `group_id` | grupa |
| `round_no` | **etapa** 1..3 |
| `bracket_position` | ordinea în etapă (0, 1) |
| `stage_label` | `"Grupa A · etapa 1"` |
| `next_match_id` / `next_slot` | **NULL** — nu există avansare din meci |
| `winner_team_id` | NULL la egal |
| `penalties_home` / `penalties_away` | **întotdeauna NULL** |

---

## 4. Setări noi de punctaj

În `seed.DEFAULT_SETTINGS` și `scoring.DEFAULT_POINTS`:

| Cheie | Default | Ce înseamnă |
|---|---|---|
| `pts.group.qualify` | `2` | puncte **per echipă ghicită corect** în pronosticul de grupă |
| `pts.group.perfect` | `0` | bonus dacă **toate** echipele din pronostic sunt corecte (0 = dezactivat) |

Se editează din `/admin/setari` ca restul. Regula existentă se păstrează: **o schimbare
de punctaj nu rescrie retroactiv pronosticurile deja decontate**, se aplică doar
decontărilor următoare. Apar automat în `GET /api/settings/points` (endpoint-ul
iterează `DEFAULT_POINTS`).

---

## 5. Reguli de business

### 5.1 Disponibilitatea piețelor

`services/scoring.market_available()` primește un parametru nou:

```python
def market_available(market: str, *, has_feg: bool, both_teams_set: bool, is_group: bool = False) -> bool
```

- `QUALIFY` → `both_teams_set and not is_group`
- `WINNER` → `both_teams_set` (neschimbat)
- `SCORER` → `has_feg` (neschimbat — merge și la meciurile de grupă ale FEG)
- `TOTAL_GOALS`, `BTTS` → `True` (neschimbat)

Toți apelanții (`services/tickets.validate_selections_for_match`,
`services/settlement`, `grade_selection`) trebuie să transmită
`is_group=(match.phase == "GROUP")`. Mesajul de eroare pentru QUALIFY pe grupă:
`„La meciurile din grupe nu se pariază cine merge mai departe — pronosticul e pe grupă."`

### 5.2 Egal fără penalty-uri la meciurile de grupă

În `services/settlement._validate_input`:

- dacă `match.phase == "GROUP"` și scorul e egal → **valid**, fără penalty-uri;
  `penalties_home/away` se forțează la `None` la salvare (chiar dacă adminul le trimite).
- dacă `match.phase == "KNOCKOUT"` → regula actuală rămâne (egal ⇒ penalty-uri
  obligatorii și diferite).

`_winner_team_id()` devine `-> int | None`: la un egal de grupă întoarce `None`.
`Match.winner_team_id` rămâne NULL. Nu se avansează nimic (`next_match_id` e NULL).

`resolve_qualify()` din `scoring.py` **nu se modifică** — nu mai e apelată pentru
meciurile de grupă, pentru că piața nu mai e disponibilă acolo.

### 5.3 Clasamentul unei grupe — `services/groups.py` (funcții PURE, fără DB)

```python
@dataclass(frozen=True)
class GroupResult:      # un meci validat din grupă
    home_team_id: int
    away_team_id: int
    home_score: int
    away_score: int

@dataclass(frozen=True)
class StandingRow:
    team_id: int
    played: int
    won: int
    drawn: int
    lost: int
    goals_for: int
    goals_against: int
    goal_diff: int
    points: int
    rank: int
    tied_with: tuple[int, ...]   # id-urile cu care e complet nedepartajabilă

def standings(team_ids: Sequence[int], results: Sequence[GroupResult]) -> list[StandingRow]
def qualified_team_ids(rows: Sequence[StandingRow], count: int) -> list[int]   # ridică GroupError dacă e ambiguu
```

- Punctaj: **3** victorie, **1** egal, **0** înfrângere. Doar meciuri `is_settled`.
- Departajare, în ordine: **puncte → golaveraj → goluri marcate → rezultatul direct**
  (mini-clasament calculat doar între echipele rămase egale) → **nedepartajabil**.
- Echipele complet egale primesc **același `rank`** și se listează reciproc în
  `tied_with`. `qualified_team_ids` ridică `GroupError` cu mesaj în română dacă tăietura
  de la poziția `count` cade în interiorul unui grup nedepartajabil:
  `„Nu pot departaja X și Y pentru ultimul loc — alege manual echipele calificate."`
- Echipele fără meciuri jucate apar cu 0 peste tot (grupa în curs se afișează corect).

### 5.4 Pronosticul de grupă — reguli

- Un user are **maxim un pronostic per grupă** (unique).
- Trebuie să aleagă **exact `group.qualifiers_count`** echipe, toate **din acea grupă**,
  fără duplicate.
- **Blocare:** pronosticul se poate crea/edita până la **startul primului meci al grupei**
  = `min(scheduled_at)` peste meciurile grupei. Dacă niciun meci n-are `scheduled_at`,
  grupa **nu acceptă încă** pronosticuri (`„Grupa n-are încă program."`), simetric cu
  regula de la bilete. După start: `„Grupa a început — nu mai poți schimba pronosticul."`
- Regula de lock trăiește **server-side**, într-o funcție unică
  (`services/groups.assert_group_open_for_prediction`) — frontend-ul doar ascunde butoane.
- Rate limit `30/minute` pe POST/PUT/DELETE, ca la bilete.

### 5.5 Finalizarea grupei și decontarea pronosticurilor

`POST /api/admin/groups/{group_id}/finalize`, body opțional `{"team_ids": [int, ...]}`:

1. Cere **toate cele 6 meciuri ale grupei validate** (`is_settled`), altfel `400`
   `„Mai sunt N meciuri nevalidate în grupa A."`
2. Fără `team_ids` → ia primele `qualifiers_count` din clasament; dacă `GroupError`
   (ambiguu) → `400` cu mesajul din 5.3.
3. Cu `team_ids` → validează: exact `qualifiers_count`, fără duplicate, toate din grupă.
   Se scrie în audit ca **suprascriere manuală** (`detail.manual = true`).
4. Rescrie `group_qualifiers` (șterge ce era, scrie noul set, `rank` din ordinea
   clasamentului / din ordinea trimisă).
5. **Decontează pronosticurile grupei**, cu același tipar ca `settlement.py`:
   întâi **anulează complet** efectul precedent (`is_correct=None`, `points_awarded=None`,
   `total_points=None`, `status="OPEN"`), apoi recalculează. Re-finalizarea e permisă
   și nu adună puncte peste cele vechi.
   - fiecare pick corect → `pts.group.qualify` puncte
   - toate corecte → în plus `pts.group.perfect` (dacă > 0)
6. **Recalculează `User.points` pentru toți userii** (vezi 5.6).
7. Audit: `admin.group.finalize` cu `before`/`after`, numărul de pronosticuri decontate,
   `manual: bool`.
8. Totul într-o singură tranzacție.

### 5.6 `User.points` = bilete + pronosticuri de grupă

Azi `settlement.py` pasul 4 recalculează `User.points` doar din `Ticket`. Se extrage
într-o funcție comună — **`services/points.recalc_all_user_points(db)`** — care adună:

```
SUM(tickets.total_points WHERE status = 'SETTLED')
+ SUM(group_predictions.total_points WHERE status = 'SETTLED')
```

Apelată din `settle_match` **și** din `finalize_group`. Clasamentul
(`routers/leaderboard.py`) citește `User.points`, deci punctele intră automat; în plus
adaugă în `LeaderboardRow` două câmpuri noi, ca să se vadă de unde vin punctele:

- `group_points: int` — punctele din pronosticuri de grupă
- `correct_qualifiers: int` / `total_qualifiers: int` — picks corecte / total picks decontate

Contoarele existente (`tickets`, `settled_tickets`, `won_tickets`,
`correct_selections`, `total_selections`) rămân **doar despre bilete** — nu le amesteca.

---

## 6. API

### 6.1 Public

| Metodă | Rută | Ce face |
|---|---|---|
| `GET` | `/api/groups` | toate grupele: echipe, clasament calculat, meciuri, `is_complete`, `is_locked`, `qualified` (dacă finalizată), iar dacă cererea e autentificată și `my_prediction` |
| `GET` | `/api/groups/{group_id}` | idem, o singură grupă |
| `GET` | `/api/group-predictions/mine` | pronosticurile mele (auth) |
| `POST` | `/api/group-predictions` | `{group_id, team_ids: [int]}` → 201; `409` dacă există deja |
| `PUT` | `/api/group-predictions/{id}` | `{team_ids: [int]}` — înlocuiește complet picks-urile |
| `DELETE` | `/api/group-predictions/{id}` | șterge pronosticul (doar cât e deschis) |

`GroupOut` (schema):

```
id, name, sort_order, qualifiers_count,
teams: [TeamRef],
standings: [{team_id, team: TeamRef, played, won, drawn, lost,
             goals_for, goals_against, goal_diff, points, rank, tied_with: [int]}],
matches: [MatchOut],          # aceleași MatchOut ca la /api/matches
is_complete: bool,            # toate meciurile validate
is_finalized: bool,           # există group_qualifiers
is_locked: bool,              # a început primul meci → pronosticul e blocat
locks_at: datetime | null,    # min(scheduled_at) din grupă
qualified: [TeamRef],         # gol dacă nefinalizată
my_prediction: GroupPredictionOut | null
```

`GroupPredictionOut`:

```
id, group_id, status, total_points,
picks: [{team_id, team_name, is_correct, points_awarded}],
potential_points,             # nr. picks × pts.group.qualify (+ perfect, dacă e activ)
created_at, updated_at
```

`MatchOut` / `MatchDetailOut` primesc două câmpuri noi: **`phase`** și
**`group_id`** (+ `group_name`, ca frontend-ul să afișeze „Grupa A" fără un al doilea fetch).

`GET /api/bracket` întoarce **doar meciurile `phase == "KNOCKOUT"`**.
`GET /api/matches` le întoarce **pe toate** (grupă + knockout).

### 6.2 Admin

| Metodă | Rută | Ce face |
|---|---|---|
| `GET` | `/api/admin/groups` | grupele cu echipe + clasament + stare |
| `POST` | `/api/admin/groups/generate` | `{groups: [{name, team_ids: [4 id-uri]}, ...]}` → creează grupele, setează `teams.group_id`, generează toate meciurile round-robin |
| `PUT` | `/api/admin/groups/{id}` | `{name?, qualifiers_count?, team_ids?}` — cât timp grupa n-are meciuri validate |
| `DELETE` | `/api/admin/groups/{id}` | doar dacă n-are meciuri validate și niciun pronostic |
| `POST` | `/api/admin/groups/{id}/finalize` | vezi 5.5 |
| `POST` | `/api/admin/bracket/generate-from-groups` | construiește bracket-ul de 8 din echipele calificate |

**Generarea meciurilor de grupă (round-robin, 4 echipe).** Metoda cercului, echipele
indexate 1..4 în ordinea trimisă:

- etapa 1: `1–4`, `2–3`
- etapa 2: `4–3`, `1–2`
- etapa 3: `2–4`, `3–1`

Fiecare pereche apare **exact o dată** (testează asta explicit). `scheduled_at` rămâne
`NULL` — adminul programează meciurile din `/admin/meciuri` ca până acum.

`POST /api/admin/groups/generate` refuză (`400`) dacă există deja meciuri de grupă
**validate** sau pronosticuri plasate. Altfel șterge grupele/meciurile de grupă
existente și regenerează (același tipar ca `generate_bracket`).

**`POST /api/admin/bracket/generate-from-groups`:**

1. Cere **toate grupele finalizate** cu `qualifiers_count == 2` fiecare (dacă
   organizatorul schimbă numărul și totalul nu mai e 4/8/16 → `400` clar:
   `„Din grupe ies N echipe, iar bracket-ul acceptă doar 4, 8 sau 16."`).
2. Împerechere **încrucișată**, ordinea în bracket:
   `1A, 2B, 1C, 2D, 1B, 2A, 1D, 2C`
   → sferturile devin `1A–2B`, `1C–2D`, `1B–2A`, `1D–2C` (nicio echipă nu întâlnește
   în sferturi o echipă din propria grupă).
3. Apelează `generate_bracket(db, 8, team_ids)`.

> ⚠️ **`services/bracket.generate_bracket` trebuie restrâns la faza knockout.** Azi
> șterge **toate** meciurile și refuză dacă există **orice** bilet. Cu grupe, ambele
> ar fi greșite: ar șterge meciurile de grupă și ar refuza pentru că există bilete pe
> grupe. Modifică-l să lucreze doar cu `Match.phase == "KNOCKOUT"`:
> - `existing` = doar meciuri knockout
> - verificarea „există bilete" = doar bilete pe meciuri knockout
> - meciurile create primesc `phase="KNOCKOUT"`
> Testele existente din `test_bracket.py` trebuie să rămână verzi.

---

## 7. Frontend

### 7.1 Fișiere noi

- `src/api/groups.ts` — hook-uri react-query: `useGroups`, `useGroup`,
  `useMyGroupPredictions`, `useSaveGroupPrediction`, `useDeleteGroupPrediction`
- `src/pages/Grupe.tsx` — pagina publică `/grupe`
- `src/components/group/GroupCard.tsx` — un card de grupă: clasament + meciuri
- `src/components/group/GroupStandings.tsx` — tabelul de clasament (mobile-first)
- `src/components/group/QualifyPicker.tsx` — selectorul „ce echipe merg mai departe"
- `src/pages/admin/AdminGroups.tsx` — `/admin/grupe`
- `src/pages/admin/GroupGenerateModal.tsx`, `src/pages/admin/FinalizeGroupModal.tsx`

### 7.2 Pagina `/grupe`

- 4 carduri (A–D). Pe mobil: tab-uri de grupă + un card; pe desktop: grilă 2×2.
- **Clasament**: tabel compact — poziție, echipă, `J V E Î`, `GM:GP`, `+/-`, **P**.
  Primele `qualifiers_count` locuri au fundal verde discret și un mic „→ sferturi";
  echipele nedepartajabile primesc un `Badge` „egale".
- **Meciurile grupei**, grupate pe etape, cu `MatchCard` existent.
- **Blocul de pronostic**, sus în card:
  - deschis → „Cine merge mai departe din grupa A?" + chip-uri cu cele 4 echipe,
    selectezi exact 2, buton „Salvează pronosticul" + „poți câștiga N puncte"
  - blocat, nedecontat → pronosticul afișat read-only + `Countdown`/„Grupa a început"
  - decontat → `TicketStub` + `Stamp` (`CÂȘTIGAT` toate corecte / `PARȚIAL` / `PIERDUT`)
    + confetti la primul afișaj dacă e câștigător (aceeași convenție cu biletele,
    o dată per pronostic, `localStorage`, respectă `prefers-reduced-motion`)
- Fără pronostic salvat și grupa încă deschisă → `EmptyState` cu CTA.

### 7.3 Modificări pe existent

- **Navbar / TabBar** (`components/layout/navItems.ts`): intrare nouă **„Grupe"**
  între „Meciuri" și „Bracket".
- **`/bracket`**: doar knockout. Dacă nu există meciuri knockout →
  `EmptyState` „Bracket-ul se stabilește după grupe."
- **`MarketPicker` / `BetSlip` / `lib/markets.ts`**: piața `QUALIFY` **nu se afișează**
  când `match.phase === 'GROUP'`.
- **`MatchCard` / `/meci/:id`**: `Badge` cu „Grupa A · etapa 2" când e meci de grupă.
- **`SettleModal`** (admin): la un meci de grupă **nu** cere penalty-uri la egal și
  ascunde câmpurile; la knockout rămâne cum e.
- **`/biletele-mele`**: secțiune nouă „Pronosticuri pe grupe" deasupra biletelor.
- **`Home.tsx`**: dacă există grupe deschise fără pronostic → card CTA
  „Ți-ai pus pronosticul pe grupe?".
- **`/clasament`**: sub numele fiecărui user, când `group_points > 0`, un rând mic
  „din care N p. din grupe".
- **`api/types.ts`**: `phase`, `group_id`, `group_name` pe `Match`; tipurile noi de grupă.
- **`KitchenSink`**: adaugă `GroupStandings` și `QualifyPicker` în toate stările.

---

## 8. Teste (TDD — testele întâi)

### Backend (`backend/tests/`)

| Fișier | Ce acoperă |
|---|---|
| `test_groups_standings.py` | funcțiile pure: puncte 3/1/0, ordonare pe golaveraj, pe goluri marcate, departajare prin rezultat direct, egalitate completă → `tied_with` + `GroupError`, grupă fără meciuri jucate |
| `test_groups_admin.py` | generare grupe: 4×4, round-robin (**fiecare pereche exact o dată**, 6 meciuri/grupă, 3 etape), `teams.group_id` setat, refuz la regenerare peste meciuri validate / pronosticuri, `403` pentru non-admin, editare/ștergere grupă |
| `test_group_predictions.py` | creare/editare/ștergere, exact `qualifiers_count` echipe, echipe din altă grupă → 400, duplicate → 400, unique user+grupă → 409, lock la startul primului meci, grupă fără program → 400, `403`/`401` fără token |
| `test_group_finalize.py` | finalizare automată, ambiguitate → 400 cu mesaj, suprascriere manuală validată, **re-finalizare** (undo complet, punctele nu se dublează), `User.points` = bilete + grupe, audit `admin.group.finalize`, pronosticuri decontate corect/parțial/greșit, bonus `pts.group.perfect` |
| `test_group_matches.py` | meci de grupă egal **fără** penalty-uri se validează; `winner_team_id` rămâne NULL; piața `QUALIFY` respinsă la pariere și la decontare pe meci de grupă; `SCORER` funcționează la meciul de grupă al FEG; meciul de knockout egal **cere** în continuare penalty-uri |
| `test_bracket_from_groups.py` | împerecherea încrucișată `1A–2B / 1C–2D / 1B–2A / 1D–2C`; refuz dacă o grupă nu e finalizată; **nu șterge meciurile de grupă**; nu refuză din cauza biletelor pe meciuri de grupă |

Toate testele existente (**272**) rămân verzi. Coverage: **100%** pe `services/groups.py`
și `services/points.py`, ≥ 80% global.

### E2E (`frontend/e2e/`)

`group-flow.spec.ts`, pe ambele proiecte (desktop + iPhone 13):
înregistrare → pronostic pe grupa A → admin validează cele 6 meciuri → admin
finalizează grupa → userul vede ștampila și punctele în clasament.
Actualizează `screenshots.spec.ts` cu `/grupe` și `/admin/grupe`.

---

## 9. Ordinea de lucru

1. Modele + migrare (`models.py`) — verifică `server_default` pe `matches.phase`.
2. `services/groups.py` — funcții pure + testele lor (**RED → GREEN**).
3. `services/points.py` — `recalc_all_user_points`, folosit din `settlement.py`.
4. `scoring.market_available(is_group=...)` + apelanții.
5. `settlement.py` — egal fără penalty la grupe, `_winner_team_id -> int | None`.
6. `bracket.generate_bracket` restrâns la `phase == "KNOCKOUT"`.
7. Scheme + rutele publice de grupe și pronosticuri.
8. Rutele de admin: generate / update / finalize / generate-from-groups.
9. `seed.py`: cheile noi de punctaj.
10. `pytest` verde + coverage.
11. Frontend: tipuri → `api/groups.ts` → `/grupe` → admin → modificările pe existent.
12. `npm run build` verde, apoi `npx playwright test` verde.
13. Actualizează `README.md` (secțiunea „Structură" + „Idei viitoare") și adaugă
    mențiunea grupelor. Commit: `feat: grupe A-D + pronostic de calificare (Faza 9)`.

## 10. Acceptanță

- [ ] Adminul creează 4 grupe × 4 echipe și primește 24 de meciuri, fiecare pereche o dată.
- [ ] Un meci de grupă se validează egal, fără penalty-uri.
- [ ] Pe un meci de grupă nu apare și nu se acceptă piața „Cine merge mai departe".
- [ ] Userul votează 2 echipe per grupă, până la startul primului meci al grupei.
- [ ] Clasamentul grupei respectă puncte → golaveraj → goluri → meci direct.
- [ ] La finalizare, pronosticurile se decontează, punctele intră în clasamentul general.
- [ ] Re-finalizarea nu dublează punctele.
- [ ] Bracket-ul de 8 se generează din calificate, încrucișat, fără să atingă grupele.
- [ ] `pytest` verde, `npm run build` verde, `npx playwright test` verde.
