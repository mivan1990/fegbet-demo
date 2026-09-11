"""Ruta de test E2E — NU face parte din aplicatie decat daca `E2E_TEST_MODE=1`.

Vezi `main.py`: `app.include_router(e2e_router.router)` e in spatele acelui flag —
altfel modulul poate fi importat (definitia rutei exista in Python), dar ruta nu e
inregistrata la nicio adresa, deci un request catre ea intoarce 404 ca oricare alta
cale inexistenta (nu 403 — 403 ar confirma ca ruta EXISTA, doar refuzata).

De ce exista: `services.groups.generate_groups` e un reset global, o singura data
per baza — refuza sa (re)genereze daca exista undeva un meci de grupa validat sau
un pronostic plasat. Suita Playwright ruleaza mai multe fisiere de test pe ACEEASI
baza SQLite in cadrul unei singure invocari `npx playwright test`
(frontend/playwright.config.ts: `reuseExistingServer` + DB stearsa doar la
PORNIREA serverului, nu intre fisiere). `admin-groups-flow.spec.ts` testeaza
efectiv fluxul de admin "Genereaza grupe" (butonul care cheama reset-ul global) —
ca sa treaca indiferent de ordinea specurilor, are nevoie sa garanteze o baza curata
chiar inainte de acel apel, indiferent ce a lasat in urma alt spec (vezi
`group-flow.spec.ts`, care isi creeaza propriile grupe prin ruta ADITIVA
`POST /api/admin/groups`, neafectata de reset-ul global).

Garantii de siguranta (NU optionale):
  1. Ruta nu exista in aplicatie decat cu `E2E_TEST_MODE=1` (main.py).
  2. Chiar si asa, verificam aici ca `DATABASE_URL` contine "e2e" — a doua bariera,
     in caz ca flag-ul de mediu ajunge setat din greseala pe o baza reala.
  3. Ramane in spatele `require_admin` (autentificare + rol admin).

NU seta NICIODATA `E2E_TEST_MODE=1` pe serverul de productie — vezi
INSTALARE_SERVER.md. Sterge NECONDITIONAT tot domeniul grupelor (vezi
`services.groups.reset_all_groups`), inclusiv pronosticuri deja decontate.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models import User
from services.groups import reset_all_groups
from services.security import require_admin

router = APIRouter(prefix="/api/e2e", tags=["e2e-test-only"], dependencies=[Depends(require_admin)])


@router.post("/reset-groups", status_code=200)
def e2e_reset_groups(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> dict[str, bool]:
    if "e2e" not in settings.database_url.lower():
        raise HTTPException(
            status_code=403,
            detail=(
                "Refuzat: DATABASE_URL nu arată a bază de test "
                "(trebuie să conțină „e2e”)."
            ),
        )
    reset_all_groups(db)
    return {"ok": True}
