# FEG BET — Plan de implementare (prompt pentru Sonnet)

> **Cum se folosește acest fișier:** deschide o sesiune Claude Code cu Sonnet în
> `/Users/mariusivan/Projects/PERSONAL/FEGBet` și dă-i ca prompt:
> *"Citește PLAN_SONNET.md și implementează Faza 0 → Faza 1. Nu trece la faza următoare
> până nu trec toate criteriile de acceptanță ale fazei curente."*
> Fiecare fază are criterii de acceptanță verificabile. Se lucrează fază cu fază.

---

## 0. Context și scop

Aplicație web internă pentru colegii de la **FEG**, în care se pariază (fără bani, doar pe puncte
și orgoliu) pe meciurile unui turneu de fotbal la care participă și echipa FEG.

- Turneul este **knockout (eliminatoriu)**: cine câștigă meciul merge mai departe.
- Cunoaștem **numele echipelor** adverse, dar **NU** avem lista lor de jucători.
- Cunoaștem **doar jucătorii echipei FEG** → piața „Marcator" se aplică **exclusiv la meciurile FEG**.
- Doi utilizatori: **user** (pariază) și **admin** (administrează totul + validează meciurile).
- Punctele se calculează **automat** când adminul validează scorul unui meci.
- **Toate acțiunile** (user + admin) se loghează.

### Ce NU face aplicația
- Nu procesează bani reali, nu are portofel, nu are retrageri. Doar puncte.
- Nu se conectează la niciun API extern de fotbal. Adminul introduce tot manual.
- Nu are jucători pentru echipele adverse.
- Nu are chat, nu are notificări push, nu are aplicație mobilă nativă.

---

## 1. Stack-ul tehnologic

Stack-ul de mai jos este ales pentru că rulează deja în producție pe același server Windows
la un alt proiect intern, deci nu aduce infrastructură nouă de operat: același mod de deploy,
aceleași cunoștințe de administrare, aceeași bază de rulare. **Nu introducem tehnologii noi.**

> **Aplicația se scrie de la zero.** Nu există cod moștenit, nu se copiază fișiere, module,
> modele sau logică din niciun alt proiect. Singurul lucru împrumutat este *lista de
> tehnologii de mai jos*.

| Strat | Tehnologie | Versiune |
|---|---|---|
| Backend | FastAPI | 0.115.x |
| Server | uvicorn[standard] | 0.30.x |
| ORM | SQLAlchemy | 2.0.x |
| DB | SQLite (fișier local) | — |
| Auth | python-jose (JWT) + bcrypt | — |
| Rate limiting | slowapi | 0.1.9 |
| Config | python-dotenv | 1.0.x |
| Teste backend | pytest + httpx | — |
| Frontend | React | 18.3 |
| Build | Vite | 5.4 |
| Limbaj FE | TypeScript | 5.6 |
| CSS | Tailwind CSS | 3.4 |
| Data fetching | @tanstack/react-query | 5.x |
| HTTP | axios | 1.x |
| Routing | react-router-dom | 7.x |
| Teste E2E | Playwright | 1.6x |

### Decizii pe dependințe
- **`alembic`** — NU. Migrările se fac printr-o funcție proprie `_migrate()`, idempotentă
  (verifică schema cu `PRAGMA table_info` și adaugă ce lipsește cu `ALTER TABLE`), scrisă
  în cadrul acestui proiect. Motiv: nu adăugăm încă un tool de operat manual pe server.
- **`framer-motion`** (frontend) — DA. Cerința e „modern, plăcut, haios"; animațiile de bilet,
  ștampilă și confetti au nevoie de el. E doar la build-time, nu afectează serverul.
- **`canvas-confetti`** (frontend) — DA, ~2KB, pentru biletele câștigătoare.
- **`zod`** (frontend) — DA, validare formulare bilet fără librărie grea de forms.
- **`lucide-react`** (frontend) — DA. **Singurul set de iconuri permis.** Nu amesteca cu emoji
  în interfața funcțională (emoji doar în microcopy și stări goale), nu importa alt icon pack,
  nu desena iconuri SVG de mână.

### Ce NU folosim
Postgres, Docker, Next.js, Redis, Prisma, Alembic, shadcn/ui, orice ORM sau framework nou.
Dacă îți vine ideea să adaugi o dependință care nu e în lista de mai sus — **întreabă întâi**.

---

## 2. Reguli de proiect (obligatorii)

1. **Proiect complet independent.** Tot codul se scrie de la zero, în acest repo.
   **Nu deschide, nu citi și nu copia** nimic din `/Users/mariusivan/Projects/PERSONAL/CS2Leaderboard`
   sau din alt proiect existent — nici cod, nici modele, nici structură de fișiere.
   Din secțiunea 1 iei doar numele și versiunile librăriilor.
2. **Repo git nou și independent**: `git init` în `/Users/mariusivan/Projects/PERSONAL/FEGBet`.
   Fără submodule, fără monorepo.
3. **Commit-uri conventional commits** (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`),
   în română sau engleză, consecvent. Fără linie de atribuire în mesaj.
4. **Baza de date, `.env`, `logs/`, `node_modules/`, `dist/` NU intră în git.**
5. **Tot textul vizibil pentru utilizator este în română**, fără diacritice obligatorii în cod
   (poți folosi diacritice în UI — sunt ok, dar fii consecvent; recomandat: CU diacritice în UI).
6. **Datele/orele**: stochezi întotdeauna **UTC timezone-aware**; compari cu
   `datetime.now(timezone.utc)`; afișezi în frontend în `Europe/Bucharest`.
   Niciun `datetime` naiv nu ajunge în DB și nicio comparație nu se face între naiv și aware —
   e sursa clasică de bug-uri la blocarea biletelor.
7. **Fără secrete în cod.** Tot ce e secret vine din `.env`, cu `.env.example` commit-uit.
8. După fiecare fază: rulează testele, rulează `npm run build`, apoi commit.

---

## 3. Structura repo-ului

```
FEGBet/
├── README.md
├── PLAN_SONNET.md              ← fișierul ăsta
├── INSTALARE_SERVER.md         ← ghid deploy Windows (Faza 8)
├── deploy.bat                  ← script deploy pe server (Faza 8)
├── .gitignore
├── backend/
│   ├── main.py                 ← app, middleware, migrări, mount frontend
│   ├── database.py             ← engine, SessionLocal, Base, get_db
│   ├── models.py               ← toate modelele SQLAlchemy
│   ├── log_config.json         ← logging uvicorn + app.* (rotating file)
│   ├── log_utils.py            ← PlainFormatter (strip ANSI)
│   ├── requirements.txt
│   ├── .env.example
│   ├── routers/
│   │   ├── auth.py             ← register, login, me, schimbare parolă
│   │   ├── teams.py            ← public: listă echipe
│   │   ├── players.py          ← public: listă jucători FEG
│   │   ├── matches.py          ← public: meciuri, bracket
│   │   ├── tickets.py          ← user: creare/editare/ștergere bilet
│   │   ├── leaderboard.py      ← clasament utilizatori
│   │   └── admin.py            ← tot ce ține de admin (poate fi împărțit în submodule)
│   ├── services/
│   │   ├── scoring.py          ← REGULILE DE PUNCTAJ (inima aplicației)
│   │   ├── settlement.py       ← validare meci → decontare bilete → puncte
│   │   ├── bracket.py          ← generare/avansare bracket
│   │   ├── audit.py            ← log_action() în DB + fișier
│   │   └── security.py         ← hash, verify, JWT, dependencies de rol
│   ├── schemas/                ← modele Pydantic pe domenii
│   └── tests/
│       ├── conftest.py
│       ├── test_auth.py
│       ├── test_scoring.py     ← cel mai important fișier de teste
│       ├── test_settlement.py
│       ├── test_bracket.py
│       ├── test_tickets_lock.py
│       └── test_admin.py
└── frontend/
    ├── index.html
    ├── package.json
    ├── vite.config.ts          ← proxy /api → http://localhost:8100
    ├── tailwind.config.js      ← design tokens (secțiunea 4)
    ├── src/
    │   ├── main.tsx
    │   ├── App.tsx             ← rute + guard-uri
    │   ├── index.css
    │   ├── api/                ← client axios + hooks react-query
    │   ├── lib/                ← formatare dată, countdown, helpers punctaj
    │   ├── components/
    │   │   ├── layout/         ← Navbar, Footer, Shell
    │   │   ├── ui/             ← Button, Card, Badge, Modal, Toast, Countdown
    │   │   ├── bet/            ← BetSlip, MarketPicker, SelectionRow, Stamp
    │   │   └── bracket/        ← BracketTree, BracketMatch
    │   ├── pages/
    │   └── pages/admin/
    └── e2e/                    ← Playwright
```

---

## 4. Identitate vizuală și UX

Cerința utilizatorului: **modern, plăcut, haios**, cu paleta **roșu + galben + albastru**
(roșu = casa de pariuri, galben = Fortuna, albastru = FEG; FEG deține ambele branduri).
Ordinea nu contează, dar cele trei culori trebuie să se simtă ca **un sistem**, nu ca un semafor.

### Regula de aur a paletei
Nu pui cele trei culori în cantități egale. Raport **60 / 30 / 10**:
- **Albastru** = fundal, structură, navigație, stări neutre (culoarea „casei").
- **Galben** = accentul principal, CTA-uri, evidențieri, puncte câștigate.
- **Roșu** = urgență, „se închide pariul", ștampila de bilet pierdut, ștergere.

### Design tokens (pune-le în `tailwind.config.js` → `theme.extend.colors`)

```js
colors: {
  // Albastru FEG — structura
  navy:   { 950:'#070B1A', 900:'#0B1229', 800:'#101B3D', 700:'#16264F', 600:'#1D3468' },
  feg:    { DEFAULT:'#1E5BFF', 600:'#1747D6', 400:'#4E82FF', 200:'#A9C2FF' },
  // Galben Fortuna — accentul
  fortuna:{ DEFAULT:'#FFC800', 600:'#E0AC00', 400:'#FFD84D', 200:'#FFEEA8' },
  // Roșu casă de pariuri — urgență
  bet:    { DEFAULT:'#F03A2E', 600:'#C92B21', 400:'#FF6A5E', 200:'#FFC1BB' },
  // Neutrale calde peste albastru
  paper:  { DEFAULT:'#FBF7EE', 200:'#F2ECDE' },   // hârtia biletului
  ink:    '#0A0E1C',
}
```

- **Fundal aplicație:** `navy-950` cu un gradient radial discret spre `navy-800` și un
  pattern subtil de romburi la 4% opacitate (senzație de „tapet de agenție de pariuri", modern).
- **Carduri:** `navy-900` cu `border border-white/8`, `rounded-2xl`, umbră joasă.
- **Biletul:** fundal `paper`, text `ink`, font monospace pentru puncte/cote,
  margine de sus/jos cu **zimți de tichet** (mască CSS cu cercuri) și o **linie perforată** punctată.

### Tipografie
- Titluri / numere mari: **Bricolage Grotesque** sau **Archivo Black** (heavy, ușor jucăuș).
- Text: **Inter**.
- Puncte, scoruri, ore: **JetBrains Mono** sau `font-mono` — dă senzația de tichet tipărit.
- **Auto-găzduire obligatorie.** Serverul e intern și poate să nu aibă internet, deci nu
  folosim `<link>` către Google Fonts. Descarci fișierele `.woff2` pe mașina de dezvoltare,
  le pui în `frontend/public/fonts/`, le declari cu `@font-face` în `index.css`
  (`font-display: swap`) și le **commit-ezi în repo**.
- Fiecare familie are stivă de rezervă: `'Bricolage Grotesque', 'Arial Black', sans-serif`,
  `'Inter', system-ui, sans-serif`, `'JetBrains Mono', ui-monospace, monospace`.
  Dacă fonturile lipsesc, aplicația trebuie să arate în continuare decent, nu spartă.

### Momente de „haios" (fă-le, nu sunt opționale — asta cere clientul)
1. **Biletul fizic.** Fiecare bilet arată ca un tichet tipărit: header cu numele aplicației,
   cod bilet (`#FEG-000123`), lista selecțiilor cu punctele lor, total posibil jos, zimți pe margini.
2. **Ștampila.** După decontare, peste bilet cade o ștampilă rotită la -12°, cu animație de
   „impact" (scale 1.4 → 1, 180ms): verde `CÂȘTIGAT` / roșu `PIERDUT` / galben `PARȚIAL`.
3. **Confetti** la deschiderea unui bilet câștigător (o singură dată per bilet, ține în localStorage).
4. **Countdown urgent.** Sub 15 minute până la start, badge-ul devine roșu și pulsează:
   „🔒 SE ÎNCHIDE ÎN 04:12". La 0 → cardul se blochează vizual (grayscale + lacăt) fără refresh.
5. **Microcopy în română, cu umor**, dar niciodată jignitor. Exemple de folosit:
   - buton plasare: „BAG BILETUL"
   - editare: „Mai schimb o dată, că am o presimțire"
   - bilet pierdut: „Fotbalul e imprevizibil. Tu, mai puțin."
   - fără bilet pe un meci: „N-ai pariat. Curaj!"
   - clasament, locul 1: „Regele biletelor 👑"
   - ultimul loc: „Ghinionistul serviciului 🫠"
   - eroare de rețea: „Am pierdut mingea. Mai încearcă."
   - meci început: „Prea târziu, campionule. Meciul a început."
6. **Podium** pe clasament (locurile 1-2-3 cu înălțimi diferite, aur/argint/bronz peste albastru),
   restul ca listă.
7. **Bracket** desenat ca arbore, cu echipele calificate evidențiate în galben și traseul
   câștigătorului îngroșat.

### Reguli de UX care nu se negociază
- **Mobile-first, nu mobile-friendly.** Colegii vor paria de pe telefon, în pauza de masă.
  Scrii clasele Tailwind începând cu varianta de mobil și adaugi `md:`/`lg:` peste ea,
  niciodată invers. Vezi secțiunea „Responsive" de mai jos pentru regulile complete —
  **inclusiv paginile de admin**.
- **Dark mode este singurul mode.** Nu implementa light mode (economisim timp, arată mai bine).
- Orice acțiune are feedback în ≤200ms (optimistic update prin react-query).
- Stările goale au ilustrație/emoji + un rând de text amuzant, niciodată doar „No data".
- Contrast minim WCAG AA: galben pe albastru închis = ok; **niciodată text galben pe alb**
  și **niciodată roșu pe albastru fără fundal separator**.

### Scală de spațiere, colțuri, umbre, mișcare
Nu inventa valori de la componentă la componentă. **Folosești doar astea:**

- **Spacing:** doar multipli din scala Tailwind `2 / 3 / 4 / 6 / 8 / 12 / 16`. Nimic arbitrar
  gen `p-[13px]`. Padding intern card: `p-4` mobil, `p-6` desktop. Gap între carduri: `gap-3`.
- **Colțuri:** `rounded-xl` (12px) pentru butoane/input-uri, `rounded-2xl` (16px) pentru carduri,
  `rounded-full` pentru chips/badge-uri/avatare. Nimic altceva.
- **Borduri:** `border border-white/10` implicit; `border-fortuna/60` pentru starea selectată.
  Fără borduri groase, fără borduri duble.
- **Umbre:** o singură umbră de card (`shadow-[0_2px_24px_rgba(0,0,0,.35)]`) plus un glow
  galben doar pe CTA-ul principal (`shadow-[0_0_28px_rgba(255,200,0,.25)]`). Fără umbre pe text.
- **Mișcare:** durate `150ms` (hover/press), `220ms` (intrare element), `400ms` (ștampilă).
  Easing: `cubic-bezier(.2,.8,.2,1)`. Orice animație respectă `prefers-reduced-motion`
  (dacă e activ: fără confetti, fără pulsații, doar fade simplu).
- **Z-index:** `10` navbar, `20` sticky bet slip mobil, `30` toast, `40` modal.

### Componente de bază — specificații exacte
Le construiești **o singură dată** în `components/ui/` și le refolosești peste tot.
Dacă o pagină are nevoie de o variantă nouă, o adaugi în componentă, **nu** scrii stiluri locale.

**`Button`** — variante:
| Variantă | Fundal | Text | Folosire |
|---|---|---|---|
| `primary` | `fortuna` | `ink` | CTA principal: „BAG BILETUL", „SALVEAZĂ" |
| `secondary` | `transparent` + `border-white/15` | `white` | acțiuni secundare |
| `danger` | `bet` | `white` | ștergere bilet, ștergere entitate |
| `ghost` | `transparent` | `white/70` | acțiuni terțiare, linkuri-acțiune |

Dimensiuni: `sm` (h-9), `md` (h-11, default), `lg` (h-13, doar CTA-ul principal).
Stări obligatorii pentru fiecare: `hover` (luminozitate +6%), `active` (`scale-[.98]`),
`disabled` (opacity 40%, `cursor-not-allowed`), `loading` (spinner + text păstrat, buton blocat),
`focus-visible` (inel `ring-2 ring-fortuna ring-offset-2 ring-offset-navy-950`).
**Înălțime minimă de atingere 44px pe mobil** pentru orice element clicabil.

**`Chip`** (opțiunile de pariere — cea mai folosită componentă din aplicație):
Stări: `default` (fundal `navy-800`, border `white/10`), `hover` (border `white/25`),
`selected` (fundal `fortuna`, text `ink`, border `fortuna`, `scale-[1.02]`),
`disabled` (opacity 35%, fără hover). Afișează pe rândul de jos, mic și `font-mono`,
**punctele pe care le aduce**: `+3p`. Asta face regulile evidente fără să citească nimeni nimic.

**`Card`** — `navy-900`, `rounded-2xl`, `border-white/10`, `p-4 md:p-6`. Are slot de `eyebrow`
(text mic, uppercase, `tracking-wider`, `white/45`), `title`, `body`, `footer`.

**`Badge`** — `rounded-full`, `px-2.5 py-1`, `text-xs font-semibold uppercase tracking-wide`.
Culori după semantică: neutru `white/10`, succes `emerald-500/15` + text `emerald-300`,
urgent `bet/15` + text `bet-400`, info `feg/15` + text `feg-400`.

**`Input` / `Select`** — `h-11`, `bg-navy-800`, `border-white/10`, `rounded-xl`, `px-4`.
Label deasupra, mereu vizibil (nu placeholder-as-label). Eroarea apare **sub** câmp, în `bet-400`,
cu icon, și câmpul primește `border-bet`. Fără validare agresivă în timpul tastării — validezi
la `blur` și la submit.

**`Toast`** — colț dreapta-jos pe desktop, sus pe mobil, auto-dismiss 4s, max 3 simultan.
Succes = accent verde, eroare = accent roșu, info = accent albastru. Textul e din microcopy-ul haios.

**`EmptyState`** — icon `lucide` mare la 20% opacitate + titlu + o linie amuzantă + (opțional) un CTA.

**`Skeleton`** — pentru fiecare listă și card există stare de încărcare cu shimmer,
nu spinner centrat pe ecran gol. Layout-ul nu trebuie să sară când sosesc datele.

### Layout global
- **Navbar** sticky sus, `h-16`, fundal `navy-950/80` + `backdrop-blur`, border-bottom `white/8`.
  Stânga: logo text „FEG **BET**" (BET în galben). Centru (desktop): Meciuri · Bracket ·
  Biletele mele · Clasament. Dreapta: punctele mele într-un chip galben `font-mono` +
  avatar/inițiale cu meniu (Profil, Admin dacă e cazul, Ieșire).
- **Mobil:** navbar-ul păstrează doar logo + puncte + avatar; navigația trece într-o
  **bară de jos cu 4 iconuri** (tab bar), pentru că se pariază de pe telefon.
- **Container:** `max-w-6xl mx-auto px-4 md:px-6`. Pe paginile de admin, `max-w-7xl`.
- **Titlu de pagină:** un `h1` mare (`text-3xl md:text-4xl font-display`) + o linie de subtitlu
  în `white/50`. Consecvent pe toate paginile.

### Ecranul 1 — cardul de meci (4 stări obligatorii)

```
STAREA A — deschis (se poate paria)
┌────────────────────────────────────────────────────┐
│ SFERTURI · SÂM 14 SEPT · 18:30          [ DESCHIS ]│  eyebrow + badge
│                                                    │
│   FEG                    vs                MARKETING│  font-display, 20-24px
│                                                    │
│   ⏱ începe în 2 zile 4 ore                         │  white/50
│   Biletul tău: 4 selecții · poți câștiga 12p       │  sau „N-ai pariat. Curaj!"
│                              [ MODIFICĂ BILETUL → ]│
└────────────────────────────────────────────────────┘

STAREA B — urgent (< 15 min)   → border bet/40, badge roșu care pulsează
│ 🔒 SE ÎNCHIDE ÎN 04:12 │                            ← font-mono, tabular-nums

STAREA C — blocat/în desfășurare → card cu saturate-50, icon lacăt,
   textul „Meciul a început. Biletul e bătut în cuie."   fără buton de editare

STAREA D — validat
┌────────────────────────────────────────────────────┐
│ SFERTURI · SÂM 14 SEPT             [ ÎNCHEIAT ]    │
│   FEG          2  -  1        MARKETING            │  scorul mare, font-mono
│   ⚽ Au marcat: Andrei Mocanu, Vlad Petrescu           │
│   ┌──────────────────────────────────────────────┐ │
│   │  Biletul tău:  +9 PUNCTE   [CÂȘTIGAT]        │ │  bandă verde/roșie
│   └──────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────┘
```

Numele echipei FEG se afișează **întotdeauna** cu accent albastru `feg-400` + un punct colorat,
ca să se vadă din prima „meciul nostru". Scorurile și orele folosesc `tabular-nums`,
ca cifrele să nu danseze la actualizare.

### Ecranul 2 — pagina de pariere (`/meci/:id`)

**Desktop — două coloane, 60/40:**
```
┌─ Piețe (scroll) ──────────────────┐ ┌─ Biletul (sticky) ─────────┐
│ CINE CÂȘTIGĂ                      │ │ ╭┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈╮ │
│ [ FEG +3p ][ EGAL +4p ][ MKT +3p ]│ │ ┊  FEG BET · #FEG-000123 ┊ │
│                                   │ │ ┊  FEG vs Marketing      ┊ │
│ CINE MERGE MAI DEPARTE            │ │ ┊  sâm 14 sept, 18:30    ┊ │
│ [ FEG +2p ][ MARKETING +2p ]      │ │ ┊- - - - - - - - - - - - ┊ │
│                                   │ │ ┊ Câștigător   FEG    +3p┊ │
│ TOTAL GOLURI                      │ │ ┊ Calificare   FEG    +2p┊ │
│ Peste [0,5+1][1,5+2][2,5+3][3,5+4]│ │ ┊ Peste 2,5           +3p┊ │
│ Sub   [0,5+4][1,5+3][2,5+2][3,5+1]│ │ ┊ Ambele marchează DA +2p┊ │
│                                   │ │ ┊ Marcator  V. Petrescu +5p┊ │
│ AMBELE MARCHEAZĂ                  │ │ ┊- - - - - - - - - - - - ┊ │
│ [ DA +2p ][ NU +2p ]              │ │ ┊ POȚI CÂȘTIGA     15p   ┊ │
│                                   │ │ ╰┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈╯ │
│ MARCATOR FEG        (doar la FEG) │ │  [    BAG BILETUL    ]     │
│ [Mocanu][Albu][Neagu][...]   │ │  [ Șterge biletul ]        │
└───────────────────────────────────┘ └────────────────────────────┘
```

**Mobil:** piețele pe toată lățimea; jos o **bară sticky** care arată
`3 selecții · 8p` + buton `BAG BILETUL`; tap pe bară → biletul urcă ca bottom-sheet
(swipe în jos ca să-l închizi). Fiecare piață e un card cu titlu; chips-urile se sparg pe
2 coloane când nu încap.

**Comportamente obligatorii:**
- Selecție = un tap. Al doilea tap pe același chip îl **deselectează** (nu ai nevoie de buton „șterge selecția").
- Piața `MARCATOR FEG` **nu apare deloc** la meciurile fără FEG. Nu o afișa dezactivată.
- Totalul de puncte se recalculează instant, cu o mică animație de numărare.
- Dacă biletul există deja, chips-urile sunt pre-selectate, iar butonul devine
  `ACTUALIZEAZĂ BILETUL`. Salvarea e optimistă, cu rollback + toast dacă serverul refuză.
- Când countdown-ul ajunge la 0 **cât ești pe pagină**: chips-urile se dezactivează singure,
  butonul dispare, apare banda „Meciul a început.". Fără reîncărcare de pagină.

### Responsive — regulile complete pentru mobil

**Aplicația se folosește în primul rând de pe telefon.** Desktop-ul e bonus. Fiecare pagină se
proiectează întâi la 375px și abia apoi se lărgește. Dacă ceva nu încape pe telefon, se
regândește — nu se micșorează fontul.

**Contract de breakpoint-uri** (doar astea, standard Tailwind):
| Prefix | De la | Ce se schimbă |
|---|---|---|
| *(implicit)* | 320-639px | o coloană, tab bar jos, bilet în bottom-sheet |
| `sm:` | 640px | grid 2 coloane pentru chips și carduri mici |
| `md:` | 768px | apare navbar-ul orizontal, dispare tab bar-ul, tabelele devin tabele reale |
| `lg:` | 1024px | pagina de pariere trece pe 2 coloane (60/40), biletul devine sticky lateral |
| `xl:` | 1280px | doar lățimi maxime mai mari, fără rearanjări noi |

Nu inventa breakpoint-uri arbitrare (`min-[437px]`). Testul de bază: **320px** (cel mai mic
telefon realist) nu trebuie să producă scroll orizontal nicăieri.

**Fundamentele pe care se pierde de obicei timpul (fă-le din start):**
- `<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">`
  în `index.html`. `viewport-fit=cover` e obligatoriu pentru safe-area.
- **Safe areas iOS.** Bara sticky de jos și tab bar-ul trebuie să aibă
  `padding-bottom: env(safe-area-inset-bottom)`, altfel butonul „BAG BILETUL" ajunge sub
  indicatorul de home al iPhone-ului și devine imposibil de apăsat. Navbar-ul primește
  `padding-top: env(safe-area-inset-top)`.
- **Folosește `100dvh`, nu `100vh`.** Pe iOS Safari bara de adresă face `100vh` să fie mai
  mare decât ecranul și conținutul de jos rămâne tăiat.
- **Fără scroll orizontal.** `overflow-x: hidden` pe `body` **nu** e soluția — e mascarea
  problemei. Elementele late (bracket, tabele) primesc propriul container cu
  `overflow-x-auto` și `-webkit-overflow-scrolling: touch`.
- **Zone de atingere minim 44×44px**, cu minim 8px între ele. Iconurile de acțiune din liste
  (editează/șterge) nu se pun una lângă alta la 24px.
- **Tastatura mobilă:** `inputMode` și `type` corecte (`type="email"` la email,
  `inputMode="numeric"` la scoruri) ca să apară tastatura potrivită. Când un input primește
  focus, bara sticky de jos **nu** trebuie să acopere câmpul — ascunde bara cât timp
  tastatura e deschisă (detectezi cu `visualViewport`).
- **Fără hover ca singură cale.** Orice informație ascunsă în `:hover` (tooltip cu detalii)
  trebuie să fie accesibilă și la tap.
- **Text minim 16px** pe input-uri, altfel iOS face zoom automat la focus și strică layout-ul.
- Fonturile și imaginile: nimic care blochează randarea; `font-display: swap` deja cerut.

**Cum arată fiecare pagină pe telefon:**

| Pagină | Comportament sub 768px |
|---|---|
| Acasă | secțiuni stivuite: următorul meci (card mare), biletele deschise, top 3 compact |
| Meciuri | listă verticală de carduri; filtrele devin un rând de chips scrollabil orizontal |
| **Meci / pariere** | piețe pe toată lățimea, chips pe 2 coloane; bara sticky jos cu „3 selecții · 8p" + CTA; tap → bilet ca bottom-sheet, închis prin swipe în jos sau tap pe fundal |
| **Bracket** | **nu** micșora arborele. Sus, un rând de tab-uri cu rundele (Optimi · Sferturi · Semi · Finală); dedesubt, meciurile rundei selectate ca listă verticală. Plus un buton „Traseul FEG" care filtrează doar meciurile echipei noastre. Arborele desenat apare de la `md:` în sus, într-un container cu scroll orizontal |
| Biletele mele | carduri-tichet una sub alta, la lățime completă |
| Clasament | podium-ul rămâne (mai scund), restul ca listă cu rang, nume, puncte — fără coloane secundare; detaliile apar la tap |
| Profil | formular pe o coloană |
| **Admin — liste** | tabelele devin **liste de carduri**: titlul rândului mare, restul câmpurilor ca perechi etichetă/valoare, acțiunile ca butoane full-width în subsolul cardului |
| **Admin — loguri** | filtrele intră într-un panou colapsabil („Filtre ▾"); fiecare log e un card cu acțiune, cine, când, iar `detail`-ul JSON într-un `<details>` colapsat |
| **Admin — validare meci** | modalul devine **ecran complet** pe mobil, cu header fix, conținut scrollabil și butoanele de acțiune fixate jos. Scorurile se introduc cu stepper `−/+` plus câmp numeric, nu doar tastatură |

**Regula pentru admin:** faptul că e panou de administrare nu îl scutește de responsive.
Cel mai probabil vei valida un meci de pe telefon, de pe marginea terenului. Modalul de
validare meci + marcatori **trebuie** să fie utilizabil cu o singură mână.

**Scurtătură pe ecranul de start (mic efort, efect mare):** adaugă `manifest.webmanifest`
cu numele aplicației, `theme-color: #070B1A` și icoane 192/512px, plus
`<link rel="apple-touch-icon">`. Nu facem PWA cu service worker și offline — doar atât cât
să arate ca o aplicație când cineva o pune pe ecranul de start.

### Anti-pattern-uri — ce să NU faci
Astea sunt motivele pentru care o interfață arată „generat automat". Evită-le explicit:
- ❌ Gradient mov/violet oriunde. Paleta e roșu/galben/albastru, punct.
- ❌ Text cu gradient, text cu umbră, contururi neon.
- ❌ Glassmorphism peste tot (`backdrop-blur` doar la navbar și modale).
- ❌ Emoji în butoane și în etichete de câmp (emoji doar în microcopy și stări goale).
- ❌ Trei culori în același card. Un card = albastru + **o singură** culoare de accent.
- ❌ Carduri cu bordură galbenă groasă „ca să iasă în evidență".
- ❌ Animații care se repetă la infinit (pulsația e permisă **doar** pe countdown-ul sub 15 min).
- ❌ Spinner-e pe ecran gol în loc de skeleton.
- ❌ Tabele needitate pe mobil — pe sub 768px, orice tabel devine listă de carduri.
- ❌ `alert()`, `confirm()`, `prompt()` — folosești modalele proprii.
- ❌ Texte în engleză scăpate în UI („Loading…", „No results", „Submit").

### Definiția de „gata" pentru orice pagină
O pagină nu e terminată până nu bifează **toate**:
- [ ] Arată corect la **320px, 375px, 768px, 1024px și 1440px**, fără scroll orizontal.
- [ ] Pe mobil: zonele de atingere ≥44px, nimic ascuns sub safe-area, tastatura nu acoperă
      câmpul activ, iar tabelele au devenit carduri.
- [ ] Are stare de **încărcare** (skeleton), stare **goală** și stare de **eroare**.
- [ ] Toate acțiunile au `hover`, `active`, `disabled`, `loading`, `focus-visible`.
- [ ] Se poate parcurge complet cu **Tab**; inelul de focus e vizibil pe fundal închis.
- [ ] Nu folosește nicio culoare, rază sau spațiere în afara token-ilor de mai sus.
- [ ] Toate textele sunt în română și trec „testul colegului": suna a om, nu a formular.
- [ ] Cu `prefers-reduced-motion: reduce` nu se mișcă nimic inutil.

---

## 5. Model de date

Toate tabelele au `created_at`; cele mutabile au și `updated_at`.

### `users`
| câmp | tip | note |
|---|---|---|
| id | int PK | |
| email | str unique index | lowercase, trim |
| password_hash | str | bcrypt |
| display_name | str | default = partea dinaintea lui `@` |
| points | int default 0 | cache, recalculabil din bilete |
| is_admin | bool default false | |
| is_active | bool default true | admin poate dezactiva |
| created_at / updated_at | datetime | |

### `teams`
| câmp | tip | note |
|---|---|---|
| id | int PK | |
| name | str unique | ex. „FEG", „Contabilitate United" |
| short_name | str(3-4) nullable | pentru bracket, ex. „FEG" |
| logo_url | str nullable | opțional |
| is_feg | bool default false | **doar UNA** poate fi true; validat în API |
| is_active | bool default true | |

### `players` (doar jucătorii FEG)
| câmp | tip | note |
|---|---|---|
| id | int PK | |
| team_id | FK teams | trebuie să fie echipa cu `is_feg = true` |
| name | str | ex. „Andrei Mocanu" |
| shirt_number | int nullable | |
| position | str nullable | GK / DEF / MID / ATT |
| is_active | bool default true | ștergerea e **soft** dacă jucătorul apare pe bilete |

**Seed inițial** (Faza 1, echipa FEG): Andrei Mocanu, Cristian Albu, Darius Neagu,
Emil Vâlcu, Florin Barbu, George Lupaș, Horia Șerban, Tudor Dobre, Răzvan Tătaru,
Sorin Anghelache, Vlad Petrescu.

### `matches`
| câmp | tip | note |
|---|---|---|
| id | int PK | |
| round_no | int | 1 = prima rundă, crește spre finală |
| bracket_position | int | poziția în rundă, 0-indexed |
| stage_label | str nullable | „Optimi", „Sferturi", „Semifinală", „Finală" |
| home_team_id / away_team_id | FK teams nullable | NULL = încă nedeterminat (TBD) |
| scheduled_at | datetime UTC | setat de admin; **NULL = nu se poate paria** |
| status | str | `SCHEDULED` / `LIVE` / `FINISHED` / `CANCELLED` |
| home_score / away_score | int nullable | scor la finalul timpului regulamentar |
| penalties_home / penalties_away | int nullable | doar dacă a fost egal |
| winner_team_id | FK teams nullable | câștigătorul meciului (după penalty-uri dacă e cazul) |
| is_settled | bool default false | biletele au fost decontate |
| settled_at | datetime nullable | |
| next_match_id | FK matches nullable | unde avansează câștigătorul |
| next_slot | str nullable | `home` sau `away` |

### `match_scorers`
| câmp | tip | note |
|---|---|---|
| id | int PK | |
| match_id | FK matches | |
| player_id | FK players | doar jucători FEG |
| goals | int default 1 | |

Unique(`match_id`, `player_id`).

### `tickets`
| câmp | tip | note |
|---|---|---|
| id | int PK | |
| user_id | FK users | |
| match_id | FK matches | |
| status | str | `OPEN` / `SETTLED` / `VOID` |
| total_points | int nullable | NULL până la decontare |
| created_at / updated_at | datetime | |

**Unique(`user_id`, `match_id`)** — un singur bilet per user per meci (se editează, nu se dublează).

### `ticket_selections`
| câmp | tip | note |
|---|---|---|
| id | int PK | |
| ticket_id | FK tickets cascade | |
| market | str | `WINNER` / `QUALIFY` / `TOTAL_GOALS` / `BTTS` / `SCORER` |
| pick | str | vezi tabelul de piețe (secțiunea 6) |
| line | float nullable | 0.5 / 1.5 / 2.5 / 3.5 pentru `TOTAL_GOALS` |
| player_id | FK players nullable | doar pentru `SCORER` |
| is_correct | bool nullable | NULL până la decontare |
| points_awarded | int nullable | NULL până la decontare |

Unique(`ticket_id`, `market`) — o singură selecție per piață per bilet.

### `settings`
`key` unique + `value` (text). Aici trăiesc **toate punctajele** (secțiunea 6), ca adminul
să le poată schimba din UI fără redeploy. Valorile default se creează la primul start.

### `activity_logs`
| câmp | tip | note |
|---|---|---|
| id | int PK | |
| actor_user_id | FK users nullable | cine a făcut acțiunea (NULL = sistem) |
| target_user_id | FK users nullable | pe cine s-a acționat |
| action | str index | ex. `ticket.update`, `admin.match.settle` |
| entity_type / entity_id | str / int nullable | `match` / 12 |
| detail | str | JSON serializat: `{"before": {...}, "after": {...}}` |
| ip_address | str nullable | |
| user_agent | str nullable | |
| created_at | datetime index | |

---

## 6. Piețele de pariere și punctajul

### Piețe disponibile pe un bilet (se pot combina liber)

| Piață | Cod | Opțiuni | Disponibilă |
|---|---|---|---|
| Cine câștigă (timp regulamentar) | `WINNER` | `HOME` / `DRAW` / `AWAY` | la orice meci cu ambele echipe stabilite |
| Cine merge mai departe | `QUALIFY` | `HOME` / `AWAY` | la orice meci cu ambele echipe stabilite |
| Total goluri | `TOTAL_GOALS` | `OVER` / `UNDER` × linia 0.5/1.5/2.5/3.5 | întotdeauna |
| Ambele echipe marchează | `BTTS` | `YES` / `NO` | întotdeauna |
| Marcator FEG | `SCORER` | un `player_id` din lotul FEG | **doar dacă una din echipe este FEG** |

Biletul trebuie să aibă **minim 1 selecție**. Nu există constrângere de maxim.

### Punctaj (puncte fixe, adunate — nu se înmulțesc cote)

Punctele sunt **diferențiate pe dificultate**, altfel „Peste 0,5 goluri" ar fi puncte gratis.
Toate valorile sunt în `settings` cu cheile din coloana a treia.

| Selecție corectă | Puncte | Cheie setting |
|---|---|---|
| `WINNER` = HOME sau AWAY | **3** | `pts.winner.side` |
| `WINNER` = DRAW | **4** | `pts.winner.draw` |
| `QUALIFY` corect | **2** | `pts.qualify` |
| `TOTAL_GOALS` OVER 0.5 | **1** | `pts.goals.over.0.5` |
| `TOTAL_GOALS` OVER 1.5 | **2** | `pts.goals.over.1.5` |
| `TOTAL_GOALS` OVER 2.5 | **3** | `pts.goals.over.2.5` |
| `TOTAL_GOALS` OVER 3.5 | **4** | `pts.goals.over.3.5` |
| `TOTAL_GOALS` UNDER 3.5 | **1** | `pts.goals.under.3.5` |
| `TOTAL_GOALS` UNDER 2.5 | **2** | `pts.goals.under.2.5` |
| `TOTAL_GOALS` UNDER 1.5 | **3** | `pts.goals.under.1.5` |
| `TOTAL_GOALS` UNDER 0.5 | **4** | `pts.goals.under.0.5` |
| `BTTS` = YES | **2** | `pts.btts.yes` |
| `BTTS` = NO | **2** | `pts.btts.no` |
| `SCORER` corect | **5** | `pts.scorer` |

Selecție greșită = **0 puncte** (niciodată negativ).
Maxim teoretic pe un meci FEG: 4 + 2 + 4 + 2 + 5 = **17 puncte**.

**Bonus bilet perfect** (`pts.bonus.perfect`, default `0` = dezactivat): dacă adminul îl setează
> 0 și biletul are ≥3 selecții toate corecte, se adaugă bonusul. Implementează-l, dar lasă-l
oprit din default — utilizatorul a ales explicit punctaj fix, fără multiplicatori.

### Cum se determină rezultatul fiecărei piețe

Fie `H` = `home_score`, `A` = `away_score` (timp regulamentar), `P` = penalty-uri.

- **`WINNER`**: `HOME` dacă `H > A`; `AWAY` dacă `A > H`; `DRAW` dacă `H == A`.
  *Penalty-urile NU contează aici* — piața e pe timpul regulamentar.
- **`QUALIFY`**: echipa din `winner_team_id`. Dacă `H == A`, `winner_team_id` se determină din
  `penalties_home` vs `penalties_away`; dacă adminul nu a completat penalty-urile la un meci egal,
  **decontarea este blocată** cu eroare clară („Meci egal — completează penalty-urile").
- **`TOTAL_GOALS`**: `H + A` (fără penalty-uri) comparat cu linia. `OVER 2.5` corect dacă `H+A ≥ 3`.
- **`BTTS`**: `YES` corect dacă `H ≥ 1 și A ≥ 1`; altfel `NO` e corect.
- **`SCORER`**: corect dacă `player_id` apare în `match_scorers` pentru meciul respectiv
  cu `goals ≥ 1`. Autogolurile nu se înregistrează ca marcator FEG.

---

## 7. Reguli de business (le testezi pe toate)

### Înregistrare
- Se acceptă doar emailuri care se termină cu domeniul din `.env` → `ALLOWED_EMAIL_DOMAIN=@mariusivan.ro`.
- **Restricția NU se comunică nicăieri**: nu apare în UI, nu în placeholder, nu în mesajul de eroare,
  nu într-un endpoint public. Mesaj de eroare la domeniu greșit, identic și generic:
  **„Nu am putut crea contul cu acest email."**
- **Important:** același mesaj generic se dă și când emailul e deja înregistrat, ca să nu se poată
  deduce domeniul prin comparație de mesaje.
- Parolă minim 8 caractere. Hash bcrypt.
- Rate limit: `5/minute` pe `/register`, `10/minute` pe `/login`.

### Plasare / editare bilet
- Un bilet se poate plasa **doar dacă meciul nu a început**:
  `scheduled_at` este setat **ȘI** `scheduled_at > now(UTC)` **ȘI** `status == SCHEDULED`.
- Un utilizator își poate **edita sau șterge** biletul **oricând până la ora de start**,
  de câte ori vrea. Fiecare modificare se loghează cu before/after.
- După ora de start: orice POST/PUT/DELETE pe bilet → `400` cu
  „Meciul a început — nu mai poți modifica biletul."
- Nu se poate paria pe meci cu `home_team_id` sau `away_team_id` NULL (TBD).
- `SCORER` se poate alege **doar** dacă una din echipe este echipa FEG; altfel `400`.
- Validarea de timp se face **exclusiv pe server**. Frontend-ul doar ascunde butoane —
  nu se bazează pe el nicio regulă.

### Validarea meciului (admin)
Adminul completează: scor gazde, scor oaspeți, (opțional) penalty-uri, marcatorii FEG.
La salvare, într-o singură tranzacție:
1. Se validează datele (scor ≥ 0; penalty-uri obligatorii dacă `H == A`; marcatorii doar jucători FEG;
   suma golurilor marcatorilor FEG ≤ golurile echipei FEG din acel meci).
2. Se calculează `winner_team_id`.
3. Se decontează **toate** biletele meciului: pentru fiecare selecție se setează `is_correct` și
   `points_awarded`; `ticket.total_points` = suma; `ticket.status = SETTLED`.
4. Se recalculează `users.points` = suma `tickets.total_points` (recalcul complet, nu incremental —
   e mai lent dar imposibil de desincronizat).
5. Se avansează câștigătorul: `matches[next_match_id].{next_slot}_team_id = winner_team_id`.
6. `is_settled = true`, `settled_at = now`.
7. Se scrie în `activity_logs` acțiunea `admin.match.settle` cu tot payload-ul.

### Re-validarea (adminul corectează un scor deja validat)
Trebuie să funcționeze corect — e cel mai ușor loc de generat bug-uri.
1. Se anulează efectul precedent: `points_awarded` și `is_correct` se resetează la NULL.
2. Se rulează din nou pașii 1-7 de mai sus.
3. Dacă se schimbă câștigătorul, echipa avansată în `next_match_id` se **înlocuiește**; dacă
   meciul următor era deja validat, se afișează **avertisment explicit** adminului că trebuie
   revalidat și el (nu deconta în cascadă automat — prea riscant).
4. Se loghează `admin.match.resettle` cu before/after complet.

### Bracket
- Adminul creează bracket-ul alegând numărul de echipe (4, 8 sau 16) și repartizându-le în
  prima rundă. Sistemul generează automat meciurile rundelor următoare cu echipe TBD și
  leagă `next_match_id` / `next_slot`.
- Adminul poate seta/schimba `scheduled_at` pentru orice meci nevalidat.
- Echipele se pot edita/șterge; ștergerea unei echipe folosite într-un meci → **refuz** cu mesaj
  clar (dezactivează în loc să ștergi).

### Roluri
- Adminul poate promova/retrograda alt utilizator la admin. **Nu se poate auto-retrograda**
  și nu se poate retrograda ultimul admin rămas.
- Adminul poate reseta parola oricărui user (setează parola nouă direct, nu trimite email —
  serverul e intern, nu avem SMTP). Parola veche nu e niciodată vizibilă.
- Adminul vede emailul oricărui utilizator. Utilizatorii normali **nu** văd emailurile altora
  (în clasament apare doar `display_name`).

### Logare (audit)
Se loghează în `activity_logs` **și** în fișierul rotativ, cu `actor`, `ip`, `before/after`:

`auth.register`, `auth.login`, `auth.login_failed`, `auth.logout`, `auth.password_change`,
`ticket.create`, `ticket.update`, `ticket.delete`,
`admin.team.create|update|delete`, `admin.player.create|update|delete`,
`admin.match.create|update|delete|schedule|settle|resettle`,
`admin.user.reset_password`, `admin.user.promote`, `admin.user.demote`, `admin.user.deactivate`,
`admin.settings.update`, `admin.bracket.generate`.

Adminul are pagină de loguri cu filtre: după utilizator, după tip de acțiune, după interval de dată,
plus căutare liberă în `detail`. Paginat, 50/pagină, cel mai recent primul.

---

## 8. API

Toate rutele sub `/api`. Auth prin `Authorization: Bearer <JWT>`.
Token user: `{"sub": email, "type": "user", "exp": ...}`, valabil 30 zile.
Rolul de admin **nu** se ia din token — se citește `user.is_admin` din DB la fiecare cerere
(dependency `require_admin`), ca retrogradarea să aibă efect imediat.

### Public / user

| Metodă | Rută | Descriere |
|---|---|---|
| POST | `/api/auth/register` | email + password + display_name |
| POST | `/api/auth/login` | → token + user |
| GET | `/api/auth/me` | userul curent |
| PUT | `/api/auth/password` | schimbare parolă proprie (cere parola veche) |
| GET | `/api/teams` | echipele active |
| GET | `/api/players` | jucătorii FEG activi |
| GET | `/api/matches` | meciuri, cu `my_ticket` inclus dacă e autentificat; `is_locked` calculat server-side |
| GET | `/api/matches/{id}` | detaliu meci + marcatori dacă e validat |
| GET | `/api/bracket` | structura arborelui, grupată pe runde |
| GET | `/api/tickets/mine` | biletele mele, cu selecții și puncte |
| POST | `/api/tickets` | `{match_id, selections: [...]}` — creează sau **înlocuiește** biletul |
| PUT | `/api/tickets/{id}` | actualizează selecțiile |
| DELETE | `/api/tickets/{id}` | șterge biletul |
| GET | `/api/leaderboard` | clasament: display_name, puncte, nr. bilete, rata de reușită |

### Admin (toate cer `require_admin`)

| Metodă | Rută | Descriere |
|---|---|---|
| GET/POST/PUT/DELETE | `/api/admin/teams[/{id}]` | CRUD echipe |
| GET/POST/PUT/DELETE | `/api/admin/players[/{id}]` | CRUD jucători FEG |
| GET/POST/PUT/DELETE | `/api/admin/matches[/{id}]` | CRUD meciuri |
| POST | `/api/admin/bracket/generate` | `{size: 4|8|16, team_ids: [...]}` |
| PUT | `/api/admin/matches/{id}/schedule` | setează `scheduled_at` |
| POST | `/api/admin/matches/{id}/settle` | `{home_score, away_score, penalties_home?, penalties_away?, scorers:[{player_id, goals}]}` |
| GET | `/api/admin/users` | listă cu **email**, puncte, rol, ultima logare |
| PUT | `/api/admin/users/{id}/password` | setează parolă nouă |
| PUT | `/api/admin/users/{id}/role` | `{is_admin: bool}` |
| PUT | `/api/admin/users/{id}/active` | activează/dezactivează |
| GET | `/api/admin/logs` | filtre: `user_id`, `action`, `from`, `to`, `q`, `page` |
| GET/PUT | `/api/admin/settings` | punctajele |
| GET | `/api/admin/stats` | nr. useri, bilete, meciuri validate, piața cea mai jucată |

**Convenție de erori:** întotdeauna `{"detail": "mesaj în română"}`, cod HTTP corect
(400 validare, 401 neautentificat, 403 fără drepturi, 404 inexistent, 409 conflict).

---

## 9. Pagini frontend

| Rută | Pagină | Conținut |
|---|---|---|
| `/` | Acasă | următoarele 3 meciuri cu countdown, biletele mele deschise, top 3 clasament, CTA mare |
| `/login` | Login | |
| `/inregistrare` | Register | fără nicio mențiune despre domeniul de email |
| `/meciuri` | Meciuri | listă cu filtre: toate / deschise / începute / validate |
| `/meci/:id` | Detaliu + bilet | piețele de pariere, biletul live care se construiește, salvare |
| `/bracket` | Arborele turneului | vizual, cu traseul câștigătorilor |
| `/biletele-mele` | Biletele mele | istoric complet, ștampile, total puncte |
| `/clasament` | Clasament | podium + tabel |
| `/profil` | Profil | display name, schimbare parolă, statistici personale |
| `/admin` | Dashboard admin | statistici + acces rapid |
| `/admin/meciuri` | Meciuri | CRUD, programare, buton **Validează meci** (modal cu scor + marcatori) |
| `/admin/echipe` | Echipe | CRUD |
| `/admin/jucatori` | Jucători FEG | CRUD |
| `/admin/utilizatori` | Utilizatori | email, rol, resetare parolă, activare |
| `/admin/loguri` | Loguri | tabel filtrabil |
| `/admin/setari` | Setări | punctaje editabile |

**Guard-uri de rutare:** rutele user cer token; rutele `/admin/*` cer `user.is_admin`,
altfel redirect la `/` cu toast „Zona asta e doar pentru șefi.".

### Componenta cheie: `BetSlip`
Se construiește progresiv. Fiecare piață e un rând cu opțiuni tip „chips". Pe măsură ce
utilizatorul selectează, biletul din dreapta (desktop) / de jos (mobil, sticky) se populează,
arătând fiecare selecție cu punctele ei și **„Poți câștiga: N puncte"** ca sumă.
Butonul e dezactivat cu 0 selecții. Dacă biletul există deja, formularul se pre-populează și
butonul devine „ACTUALIZEAZĂ BILETUL", cu opțiunea „Șterge biletul".

---

## 10. Fazele de implementare

Lucrezi **strict în ordine**. La finalul fiecărei faze: teste verzi + `npm run build` reușit + commit.

### Faza 0 — Schelet (fără features)
- `git init`, `.gitignore`, `README.md`.
- Backend: `database.py`, `main.py` cu `/api/health`, `log_config.json`, `log_utils.py`,
  `.env.example`, `requirements.txt`, plus două middleware-uri scrise de tine:
  (a) **blocare scanere** — respinge cu 404 orice cerere al cărei path conține `.env`, `.git`,
  `wp-admin`, `phpunit`, `/vendor/`, `xmlrpc` sau se termină în `.php`/`.asp`/`.sql`/`.bak`;
  (b) **access log** — o linie per cerere cu IP, emailul din JWT (sau `—` dacă lipsește),
  metodă, path și status, scrisă în consolă (colorat) și în `logs/server.log` (fără ANSI).
- Frontend: Vite + React + TS + Tailwind. **Aici se construiește tot design system-ul
  din secțiunea 4, înainte de orice pagină:** token-ii de culoare/spațiere/rază/umbră/mișcare
  în `tailwind.config.js`, fonturile auto-găzduite cu `@font-face`, și componentele din
  `components/ui/` — `Button`, `Chip`, `Card`, `Badge`, `Input`, `Select`, `Toast`,
  `EmptyState`, `Skeleton`, `Countdown` — fiecare cu toate stările cerute.
  Plus `components/layout/` (Navbar desktop + tab bar mobil, Shell). Proxy `/api` → `:8100`.
- Creezi și o pagină internă `/kitchen-sink` (doar în dev) care afișează toate componentele
  în toate stările. E oglinda design system-ului: dacă o pagină are nevoie de un stil care
  nu există acolo, întâi îl adaugi în componentă, apoi îl folosești.
- **Acceptanță:** `uvicorn main:app --port 8100` pornește; `GET /api/health` → 200;
  `/kitchen-sink` arată fiecare componentă în stările `default/hover/active/disabled/loading/focus`;
  nicio culoare hardcodată în afara token-ilor;
  `npm run dev` pornește și afișează o pagină cu paleta aplicată.

### Faza 1 — Auth + modele + audit
- Toate modelele din secțiunea 5 + `_migrate()` idempotent.
- `services/security.py`, `services/audit.py`.
- `routers/auth.py` complet, cu regula de domeniu ascunsă și mesaj generic.
- Seed: echipa FEG (`is_feg=true`) + cei 11 jucători; primul admin din `.env`
  (`ADMIN_EMAIL`, `ADMIN_PASSWORD`).
- Frontend: `/login`, `/inregistrare`, context de auth, axios interceptor, guard-uri.
- **Acceptanță:** teste pentru: înregistrare reușită cu `@mariusivan.ro`; înregistrare respinsă cu alt
  domeniu **și mesaj identic** cu cel de email duplicat; login corect/greșit; `/api/auth/me`;
  rate limiting; fiecare acțiune apare în `activity_logs`.

### Faza 2 — Echipe, jucători, meciuri, bracket (admin)
- CRUD complet + generator de bracket + programare oră.
- Protecții: nu ștergi echipă folosită, nu ștergi jucător care apare pe bilete (soft delete),
  o singură echipă `is_feg`.
- Frontend admin: `/admin/echipe`, `/admin/jucatori`, `/admin/meciuri`.
- **Acceptanță:** generezi bracket de 8; toate `next_match_id`/`next_slot` sunt corecte;
  rundele au 4/2/1 meciuri; testele de protecție la ștergere trec.

### Faza 3 — Motorul de punctaj (`services/scoring.py`)
**Se scrie cu TDD: testele întâi.** Funcții pure, fără DB, ușor de testat:
`resolve_winner(H, A)`, `resolve_qualify(...)`, `resolve_total_goals(H, A, pick, line)`,
`resolve_btts(H, A)`, `resolve_scorer(player_id, scorers)`, `points_for(selection, settings)`.
- **Acceptanță:** minim **30 de cazuri de test**, inclusiv: 0-0, 1-0, 2-2 cu penalty-uri,
  toate cele 8 combinații de total goluri pe scoruri de graniță (exact 2 goluri vs linia 2.5),
  BTTS la 3-0 și 1-1, marcator corect/greșit, selecție pe piață indisponibilă.

### Faza 4 — Bilete (user)
- POST/PUT/DELETE cu **toate** verificările de lock pe server.
- Un bilet per user per meci; editare nelimitată până la start.
- Frontend: `/meci/:id` cu `BetSlip`, `/biletele-mele`, countdown care blochează UI-ul la 0.
- **Acceptanță:** test care setează `scheduled_at` în trecut și verifică 400 pe create/update/delete;
  test de editare repetată; test că `SCORER` e refuzat pe meci fără FEG; test unique constraint.

### Faza 5 — Decontare + avansare în bracket (`services/settlement.py`)
- Endpoint `settle`, recalcul complet de puncte, avansare câștigător, re-validare corectă.
- Frontend admin: modalul de validare meci (scor, penalty-uri, marcatori FEG cu contor de goluri).
- **Acceptanță:** test end-to-end: 3 useri cu bilete diferite pe același meci → validare →
  punctele fiecăruia sunt exact cele calculate manual în test; **test de re-validare** care schimbă
  scorul și verifică că punctele vechi au dispărut complet și cele noi sunt corecte;
  test că echipa câștigătoare apare în slotul corect al meciului următor;
  test că decontarea e refuzată la egal fără penalty-uri.

### Faza 6 — Clasament, bracket vizual, loguri, setări
- `/clasament` cu podium, `/bracket` vizual, `/admin/loguri` cu filtre, `/admin/setari`.
- **Acceptanță:** clasamentul corespunde sumei bilelor; filtrele de loguri returnează corect;
  modificarea unui punctaj din setări afectează decontările **viitoare** (nu retroactiv,
  decât dacă adminul re-validează manual meciul).

### Faza 7 — Lustruire UI/UX
- Cele 7 momente de „haios" din secțiunea 4: biletul-tichet cu zimți, ștampila, confetti,
  countdown urgent, microcopy, podium, bracket vizual.
- Cele 4 stări ale cardului de meci și cele două layout-uri ale paginii de pariere
  (desktop 60/40, mobil cu bottom-sheet), exact ca în wireframe-uri.
- Treci **fiecare** pagină prin „Definiția de gata" din secțiunea 4 și bifează lista.
- Recitești lista de anti-pattern-uri și elimini tot ce ai scăpat.
- **Acceptanță:** 3 teste Playwright: flux complet register → pariere → editare bilet;
  flux admin validare meci → userul vede ștampila și punctele; blocarea biletului după start.
  În `playwright.config.ts` definești **două proiecte**: `desktop` (1440×900) și
  `mobile` (device `iPhone 13`, 390×844). Cele 3 fluxuri rulează pe **ambele**.
  Plus un test automat care, pe fiecare pagină publică, verifică la 320px și 375px că
  `document.documentElement.scrollWidth <= clientWidth` (zero scroll orizontal),
  și screenshot-uri la 375px / 1440px pentru `/`, `/meci/:id`, `/clasament`, `/bracket`,
  `/admin/meciuri` și `/admin/loguri`.

### Faza 8 — Deploy
- `INSTALARE_SERVER.md` scris de la zero: cerințe, instalare Python/Node, build frontend,
  configurare `.env`, pornire pe portul **8100**, serviciu NSSM `FEGBet`, reverse proxy IIS,
  backup DB, depanare probleme frecvente.
- `deploy.bat` (git pull → oprire proces pe 8100 → npm build → pip install → start).
- **Acceptanță:** documentația e suficientă ca cineva care n-a văzut proiectul să-l pornească.

---

## 11. Testare

- **Backend: pytest**, minim **80% acoperire**, obligatoriu 100% pe `services/scoring.py` și
  `services/settlement.py`. `conftest.py` cu DB SQLite in-memory și fixture-uri:
  `admin_user`, `normal_user`, `feg_team`, `opponent_team`, `players`, `scheduled_match`.
- **Frontend: Playwright** pentru cele 3 fluxuri din Faza 7.
- Rulează testele **înainte** de fiecare commit.
- La orice bug găsit: întâi testul care îl reproduce (roșu), apoi fix-ul (verde).

---

## 12. Deploy pe serverul Windows

Aplicația rulează pe **portul 8100**. Portul 8000 e deja ocupat pe acel server de alt
serviciu — nu-l folosi și nu-l opri. Backend-ul servește build-ul React din `frontend/dist`:
montezi `/assets` ca `StaticFiles`, iar orice path necunoscut întoarce `index.html`
(fallback SPA), **după** toate rutele `/api`.

```
C:\FEGBet\
├── backend\   (venv, .env, fegbet.db, logs\)
└── frontend\dist\
```

Serviciu Windows prin **NSSM**, numit `FEGBet`:
- Path: `C:\FEGBet\backend\venv\Scripts\python.exe`
- Startup dir: `C:\FEGBet\backend`
- Arguments: `-m uvicorn main:app --host 127.0.0.1 --port 8100 --log-config log_config.json`

> `--host 127.0.0.1` pentru că accesul din exterior vine prin reverse proxy, nu direct.

### Reverse proxy pentru `fegbet.mariusivan.ro`
Alegerea utilizatorului: reverse proxy. Documentează în `INSTALARE_SERVER.md` varianta cu
**IIS + ARR + URL Rewrite** (cea mai firească pe Windows Server):

1. Instalează **URL Rewrite** și **Application Request Routing** din Web Platform Installer.
2. În IIS Manager → Server → *Application Request Routing Cache* → *Server Proxy Settings* →
   bifează **Enable proxy**.
3. Creează un site nou `fegbet.mariusivan.ro`, binding pe portul 80 (și 443 după certificat).
4. În `web.config`-ul site-ului, regulă de rewrite:
   ```xml
   <rule name="FEGBet" stopProcessing="true">
     <match url="(.*)" />
     <action type="Rewrite" url="http://127.0.0.1:8100/{R:1}" />
   </rule>
   ```
   Plus `<serverVariables>` pentru `X-Forwarded-For` / `X-Forwarded-Proto`.
5. HTTPS: certificat prin **win-acme** (Let's Encrypt) dacă domeniul e public, sau certificat
   intern dacă e doar în rețea.
6. DNS: `fegbet.mariusivan.ro` → IP-ul serverului (A record).
7. Firewall: deschide 80/443 pentru exterior; **NU** deschide 8100.

**Backend:** citește IP-ul real din `X-Forwarded-For` pentru access log și rate limiting
(altfel toți userii apar ca `127.0.0.1` și rate limiting-ul îi blochează în grup) —
folosește `ProxyHeadersMiddleware` / `--proxy-headers` la uvicorn.

### `.env.example`
```env
JWT_SECRET=genereaza_un_string_random_de_minim_32_caractere
ALLOWED_EMAIL_DOMAIN=@mariusivan.ro
ADMIN_EMAIL=admin@mariusivan.ro
ADMIN_PASSWORD=schimba_parola_asta_imediat
APP_NAME=FEG BET
CORS_ORIGINS=
DATABASE_URL=sqlite:///./fegbet.db
```

### Backup
`fegbet.db` este singurul lucru de neînlocuit. Adaugă în `deploy.bat` o copie a bazei în
`backend\db_backups\fegbet_YYYYMMDD_HHMMSS.db` **înainte** de orice pornire, păstrând ultimele 30.

---

## 13. Securitate (checklist obligatoriu)

- [ ] Parole cu bcrypt, niciodată în loguri, niciodată returnate de API.
- [ ] `JWT_SECRET` din `.env`, minim 32 de caractere, fără fallback în producție —
      dacă lipsește, aplicația **refuză să pornească**.
- [ ] `require_admin` verifică `is_admin` din DB, nu din token.
- [ ] Rate limiting pe `/register`, `/login`, `/tickets`.
- [ ] Toate input-urile validate cu Pydantic; fără f-string-uri în SQL (doar ORM sau
      parametri legați — vezi `_migrate()`, folosește parametri, nu interpolare).
- [ ] Middleware de blocare scanere (vezi Faza 0) activ înaintea rutelor.
- [ ] Regula de domeniu email nu se scurge prin niciun mesaj, header sau timing evident.
- [ ] Userii normali nu pot accesa niciun endpoint `/api/admin/*` — test explicit pentru fiecare.
- [ ] `.env` și `*.db` în `.gitignore` **înainte** de primul commit.
- [ ] CORS gol în producție (frontend-ul e servit de același origin).

---

## 14. Ce faci când ai dubii

- **Nu inventa features** care nu sunt în plan. Dacă îți pare că lipsește ceva, notează în
  `README.md` la secțiunea „Idei viitoare" și mergi mai departe.
- **Nu schimba punctajele** din secțiunea 6 fără să întrebi — sunt calibrate intenționat.
- **Nu adăuga dependințe** în afara listei din secțiunea 1 fără să întrebi.
- **Nu deschide și nu copia din CS2Leaderboard sau alt proiect existent** — scrii totul de la zero.
- Dacă o cerință din plan se bate cap în cap cu alta, oprește-te și întreabă — nu ghici.

---

## 15. Rezumatul deciziilor deja luate (nu le redeschide)

| Întrebare | Decizie |
|---|---|
| Stack | FastAPI + SQLite + React/Vite/TS/Tailwind (aceleași tehnologii care rulează deja pe server) |
| Cod moștenit | Niciunul — totul se scrie de la zero în acest repo |
| Format turneu | Knockout pur — câștigătorul avansează; fără clasament de grupe |
| Marcator | **Per meci**, doar la meciurile echipei FEG |
| Punctaj | Puncte fixe, adunate; diferențiate pe dificultate; fără cote înmulțite |
| Bonus bilet perfect | Implementat, dar **dezactivat** din default |
| Hosting | Același server Windows, port 8100, reverse proxy IIS pe `fegbet.mariusivan.ro` |
| Repo | Nou și independent, `/Users/mariusivan/Projects/PERSONAL/FEGBet` |
| Domeniu email | `@mariusivan.ro`, din `.env`, **niciodată comunicat utilizatorului** |
| Temă | Dark only, roșu/galben/albastru în raport 10/30/60 |
