# FEG BET — demo public

Varianta publică, cu date inventate, a unei aplicații de pariuri pe puncte: se
pariază fără bani, doar pe orgoliu, pe meciurile unui turneu de fotbal de birou.

**Live:** <https://fegbet.mariusivan.ro>

Intri direct, fără cont. Ești logat automat ca `test@mariusivan.ro`, iar din banda
de sus poți comuta oricând pe contul de admin, ca să vezi și partea cealaltă:
validarea meciurilor, formula de punctaj, jurnalul de acțiuni.

---

## Ce vezi înăuntru

Un turneu **încheiat**, cu tot istoricul lui:

- **4 grupe** (A–D) a câte 4 echipe, fiecare cu fiecare — 24 de meciuri, cu clasamente
- **bracket de 8**, din primele două ale fiecărei grupe — sferturi, semifinale, finală
- **31 de meciuri** jucate și validate, unul decis la penalty-uri
- **312 bilete** puse de 14 utilizatori, toate decontate
- **53 de pronosticuri** „cine iese din grupă"
- un clasament final, și o campioană: **FEG**

Punctele nu sunt scrise de mână în bază. Fiecare meci a trecut prin același motor
de decontare pe care îl folosește adminul când validează un scor, deci clasamentul
e coerent cu regulile din `backend/services/scoring.py` — dacă apeși „recalculează"
în panoul de admin, nu se schimbă nimic.

## Cele cinci piețe

| Piață | Unde apare | Ce alegi |
|---|---|---|
| Câștigător | orice meci | gazde / egal / oaspeți |
| Calificare | doar eliminatorii | ce echipă merge mai departe (decis și la penalty-uri) |
| Total goluri | orice meci | peste / sub 0.5, 1.5, 2.5, 3.5 |
| Ambele marchează | orice meci | da / nu |
| Marcator | **doar meciurile FEG** | ce jucător din lot marchează |

„Cine merge mai departe" din grupe nu e pariu pe meci, ci pe grupă: alegi cele două
echipe care ies, până la startul primului meci din grupă.

---

## Stack

| Strat | Tehnologie |
|---|---|
| Backend | FastAPI · uvicorn · SQLAlchemy 2.0 · SQLite |
| Auth | JWT (python-jose) + bcrypt, rate limiting cu slowapi |
| Frontend | React 18 · Vite 5 · TypeScript · Tailwind |
| Data | TanStack Query · axios · react-router |
| Teste | pytest (403 de teste) · Playwright |

Un singur proces servește și API-ul, și frontend-ul: `/api/*` merge la FastAPI,
orice alt path întoarce `index.html`.

Specificația completă e în [`PLAN_SONNET.md`](./PLAN_SONNET.md), iar faza de grupe
în [`PLAN_GRUPE.md`](./PLAN_GRUPE.md).

---

## Rulare locală

```bash
cd backend
python -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env          # completează JWT_SECRET și ADMIN_PASSWORD
.venv/bin/python seed_demo.py --force
.venv/bin/python -m uvicorn main:app --port 8100
```

```bash
cd frontend
npm install
VITE_DEMO_MODE=1 npm run build
```

`VITE_DEMO_MODE=1` e ce aprinde auto-login-ul și banda de demo. Fără variabila asta,
aplicația se comportă exact ca originalul: ecran de login, cont propriu, nimic automat.

Testele backend: `cd backend && .venv/bin/python -m pytest`

---

## Ce e diferit față de aplicația reală

Aplicația din care vine demo-ul e internă și rulează în altă parte. Aici s-au schimbat
patru lucruri, toate ca să poată sta în public:

1. **Datele sunt inventate.** Echipele, cei 11 jucători din lot și cei 15 utilizatori
   nu corespund niciunei persoane reale. Baza se construiește din `backend/seed_demo.py`.
2. **Auto-login** (`frontend/src/demo/`), cu comutator de rol. Un ecran de login într-un
   demo public e un zid, nu o funcționalitate — dar autentificarea reală a rămas
   dedesubt, neatinsă, și o vezi dacă dai Log out.
3. **Parolele conturilor de demo sunt publice** (`demo1234`, ambele conturi). Asta e
   intenția: rostul demo-ului e să poți intra și ca admin. Baza se resetează din oră
   în oră, deci nimic din ce strică cineva nu rămâne stricat.
4. **Ecranul de start știe că turneul s-a terminat** și arată campioana, în loc de
   „revino după ce adminul pune orele".

Ce **nu** s-a schimbat: modelul de date, regulile de punctaj, decontarea, fluxul de
admin, autentificarea, testele.
